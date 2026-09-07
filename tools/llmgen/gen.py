#!/usr/bin/env python3
"""tools/llmgen/gen.py -- spec.json -> a placed, audited, self-
predicted artifact: program.json + ports + cell-decl row + STA description +
netlist + prediction.

Usage:
    python tools/llmgen/gen.py --spec SPEC.json --out DIR
        [--map nor|timing|material|footprint] [--fabric sparse|dense|auto]
        [--hold-gt 24] [--steps 20]

`--map` (D-2, DESIGN section 8) picks the cost profile of the technology
mapper; the default is `nor` -- the D-1 path, byte-identical -- unless the
spec carries a `timing` key, which makes `timing` the default. `--fabric`
picks the placer's density (DESIGN 8.4); `auto` places both and keeps the
one with fewer repeaters that audits clean.

DESIGN: notes/2026-09-06-d1-llm-generator/DESIGN.md. Layers, in order:
library (parts) -> netlist (NOR synthesis) -> place (fabric) -> machine (rest
state + prediction). The outputs are what the repository's own checkers
read -- schemacheck, celldecl (CD-3 project row), sta, dynharness -- and
this tool never runs those checkers itself: generation and verification
are separate acts.

Emits under DIR (name = spec name):
    <name>.program.json    layout: blocks + ports (program.v0 schema)
    <name>.ports.json      wavegen.cellports.v0 (in/out cells)
    <name>.absorb.json     the absorb-record shape a CD-3 project row cites
    cells/<name>.json      wavelogic.cell-decl.v0 project row (celldecl.load wants <name>.json)
    <name>.sta.json        sta.py description with the arcs inline
    <name>.netlist.json    the NOR netlist and its levels
    <name>.predict.json    machine prediction per truth-table vector
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import library                                  # noqa: E402
import netlist as nl                            # noqa: E402
import place                                    # noqa: E402
import map as mapper                            # noqa: E402
from machine import Machine                     # noqa: E402

TORCH_SOURCE_REF = "minecraft-src 1.20.6-yarn RedstoneTorchBlock.java:35,98"
COMPARATOR_SOURCE_REF = "minecraft-src 1.20.6-yarn ComparatorBlock.java:53-54,154"


class GenError(ValueError):
    pass


def celldecl_row(name, spec, netlist, arc_table, absorb_rel, absorb_sha):
    inputs, outputs = netlist["inputs"], list(netlist["outputs"])
    source_ref = (COMPARATOR_SOURCE_REF if any(g.get("kind") in ("cmp_sub", "cmp_inv") for g in netlist["gates"])
                  else TORCH_SOURCE_REF)
    port_map = [{"port": f"in[{i}]", "part": name, "family": n, "family_index": 0}
                for i, n in enumerate(inputs)]
    port_map += [{"port": f"out[{j}]", "part": name, "family": n, "family_index": 0}
                 for j, n in enumerate(outputs)]
    arcs = []
    for i, iname in enumerate(inputs):
        for j, oname in enumerate(outputs):
            a = arc_table.get((iname, oname))
            if a is None:
                # no structural path (a multi-bit cell: a1 never reaches s0).
                # CD-3 demands every pair and has no 'no path' word, so the
                # pair is filed as a null delay under declared_uncalibrated --
                # the only shape the row accepts for 'no number' (D-2, decided
                # and disclosed; the right word would be a dead arc)
                arcs.append({"from": f"in[{i}]", "to": f"out[{j}]", "delay_gt": None,
                             "stages": 0, "chain_depth": None, "confluent": None,
                             "provenance": "declared_uncalibrated", "source_ref": None})
                continue
            arcs.append({"from": f"in[{i}]", "to": f"out[{j}]",
                         "delay_gt": {"lo": a["lo"], "hi": None},
                         "stages": a["stages"], "chain_depth": None, "confluent": None,
                         "provenance": "source_lower_bound",
                         "source_ref": source_ref})
    return {
        "kind": "wavelogic.cell-decl.v0", "name": name, "cell_class": "combinational",
        "function": dict(spec["function"]), "function_provenance": "declared",
        "function_note": ("declared from the spec; the NOR netlist is synthesised "
                          "from this table and is checked against it, never copied"),
        "ports": {"ref": "workbench.classes.v0", "in_part": name, "out_part": name,
                  "in_record": absorb_rel, "out_record": absorb_rel,
                  "in_record_sha256": absorb_sha, "out_record_sha256": absorb_sha,
                  "rail": None, "map": port_map},
        "time": {"unit": "gt", "arcs": arcs,
                 "note": ("lo = shortest torch/repeater path from the machine's own "
                          "delay table; hi is unmeasured (source_lower_bound). The "
                          "full [lo, hi] the generator computes is in the .sta.json")},
    }


def point_id(pos, block):
    prefix = {library.WALL_TORCH: "torch", library.TORCH: "torch", library.LAMP: "lamp",
              library.REPEATER: "rep", library.COMPARATOR: "cmp", library.LEVER: "lever"}.get(block)
    return None if prefix is None else f"{prefix}_x{pos[0]}_y{pos[1]}_z{pos[2]}"


def drive_rig(cells):
    """The igniter rig for a run of dust ports: `({pos: (block, props)}, [lever])`.

    The igniter lever is modelled where measure_compose puts a dust-port
    igniter: the first free horizontal neighbour, which on this fabric is
    always the cell WEST of the port dust. Each lever stands on a block of its
    own, because a floor lever with nothing under it is not a placement.

    THIS RIG IS NOT PART OF THE ARTIFACT. `place.program` writes the circuit
    alone, so a generated program's block list contains no lever at all -- the
    rig exists only inside the prediction below. Anything that carries a
    program into a world therefore has to ADD it, and has to add exactly this
    one: a world driven by a rig the prediction was not computed against is a
    different circuit, and its readings would answer a question nobody asked.
    That is why this is a function rather than four lines inside `predict`, and
    why `harness/synthworld.py` imports it instead of spelling it again."""
    blocks, levers = {}, []
    for cell in cells:
        lever = (cell[0] - 1, cell[1], cell[2])
        blocks[lever] = (library.LEVER, {"face": "floor", "facing": "north", "powered": "false"})
        blocks[(lever[0], lever[1] - 1, lever[2])] = (library.SMOOTH_STONE, {})
        levers.append(lever)
    return blocks, levers


def predict(pl, netlist, spec, hold_gt, steps):
    """The machine run for every truth-table vector, in dynharness's step
    vocabulary: load (levers on, 0 gt), h1..h<hold>, c0 (levers off), t1..t<steps>."""
    blocks = dict(pl.blocks)
    rig, levers = drive_rig(pl.ports["in"])
    blocks.update(rig)
    points = [(pos, b) for pos, (b, _p) in sorted(blocks.items())
              if point_id(pos, b) is not None]
    ids = {pos: point_id(pos, b) for pos, b in points}
    vectors = sorted(spec["function"])
    out = {"kind": "llmgen.predict.v0", "hold_gt": hold_gt, "steps": steps,
           "points": [{"id": ids[p], "pos": list(p), "block": b} for p, b in points],
           "vectors": {}}
    for vector in vectors:
        m = Machine(blocks)
        m.run_to_rest()
        m.gt = 0
        trace = {}
        def sweep(label):
            trace[label] = {ids[p]: v for p, v in m.observe([p for p, _b in points]).items()}
        for lever, bit in zip(levers, vector):
            if bit == "1":
                m.set_lever(lever, True)
        sweep("load")
        for i in range(1, hold_gt + 1):
            m.step()
            sweep(f"h{i}")
        settled_lamps = {ids[p]: m.observe([p])[p] for p, b in points if b == library.LAMP}
        for lever in levers:
            m.set_lever(lever, False)
        sweep("c0")
        for i in range(1, steps + 1):
            m.step()
            sweep(f"t{i}")
        out["vectors"][vector] = {"expected": spec["function"][vector],
                                  "settled_lamps_at_hold": settled_lamps,
                                  "trace": trace}
    return out


def default_profile(spec, profile):
    if profile is not None:
        return profile
    return "timing" if "timing" in spec else "nor"


def generate(spec_path, out_dir, hold_gt=24, steps=20, profile=None, fabric="sparse"):
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    profile = default_profile(spec, profile)
    net = mapper.map_spec(spec, profile, fabric if fabric != "auto" else "sparse")
    name = spec["name"]
    lv = nl.levels(net)
    if fabric == "auto":
        pl, fabric = place.place_auto(net)
    else:
        pl = place.place(net, fabric)
    problems = place.audit(pl)
    if problems:
        raise GenError("audit refused the placemen<host-path>  " + "\n  ".join(problems))
    # the netlist must implement the table (a synthesis check, not a copy)
    for vector, want in spec["function"].items():
        val = nl.evaluate(net, vector)
        got = "".join(str(val[net["outputs"][o]]) for o in net["outputs"])
        if got != want:
            raise GenError(f"synthesis disagrees with the spec at {vector}: {got} != {want}")
    arc_table = nl.arcs(net, edge_repeaters=pl.edge_repeaters)
    if hold_gt is None:
        hold_gt = max((a["hi"] for a in arc_table.values()), default=0) + 6
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    def write(suffix, doc):
        # celldecl.load() requires the row's filename to be <name>.json, so
        # the cell-decl row lives in a cells/ subdirectory under its bare name
        p = (out_dir / "cells" / f"{name}.json") if suffix == "celldecl" else out_dir / f"{name}.{suffix}.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(place.dumps(doc).encode("utf-8"))
        return p
    absorb = place.absorb_record(pl, name, net["inputs"], list(net["outputs"]))
    absorb_path = write("absorb", absorb)
    absorb_sha = hashlib.sha256(absorb_path.read_bytes()).hexdigest()
    try:
        absorb_rel = absorb_path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        absorb_rel = absorb_path.resolve().as_posix()
    counts = {}
    for b, _p in pl.blocks.values():
        counts[b] = counts.get(b, 0) + 1
    kinds = net.get("mapping", {}).get("kinds", ["nor"])
    if kinds == ["nor"]:
        description = (f"llmgen v0 {name}: NOR-basis netlist ({len(net['gates'])} torches) on the "
                       f"two-layer fabric; rest state computed by the machine; inputs are dust "
                       f"cells driven by a lever beside them, outputs are lamps (lit = 1). "
                       f"Generated, never hand-placed; semantics are judged by the checkers.")
    else:
        parts = ", ".join(f"{counts.get(b, 0)} {b.split(':')[1]}" for b in
                          (library.COMPARATOR, library.WALL_TORCH, library.REPEATER))
        description = (f"llmgen v1 {name}: technology-mapped netlist (profile {profile}, kinds "
                       f"{'/'.join(kinds)}; {parts}) on the {fabric} two-layer fabric; rest state "
                       f"computed by the machine; inputs are dust cells driven by a lever beside "
                       f"them, outputs are lamps (lit = 1). Generated, never hand-placed; "
                       f"semantics are judged by the checkers.")
    written = {
        "program": write("program", place.program(pl, name, description)),
        "ports": write("ports", place.ports_doc(pl, name, net["inputs"], list(net["outputs"]))),
        "absorb": absorb_path,
        "celldecl": write("celldecl", celldecl_row(name, spec, net, arc_table, absorb_rel, absorb_sha)),
        "sta": write("sta", place.sta_description(name, net, arc_table)),
        "netlist": write("netlist", dict(net, levels=lv, gate_x=pl.gate_x, rows=pl.rows,
                                         segments=pl.segments)),
    }
    # the machine (the library's rules, executable) must agree with the spec
    # at the hold: a placement the machine already sees failing never leaves
    # the generator (D-2: the ramp repeater of iteration 0 was caught here)
    prediction = predict(pl, net, spec, hold_gt, steps)
    lamps = [point_id(p, library.LAMP) for p in pl.ports["out"]]
    for vector, want in sorted(spec["function"].items()):
        got = "".join("1" if prediction["vectors"][vector]["settled_lamps_at_hold"][l] == "true" else "0"
                      for l in lamps)
        if got != want:
            raise GenError(f"machine prediction disagrees with the spec at {vector}: {got} != {want} "
                           f"(hold {hold_gt} gt)")
    written["predict"] = write("predict", prediction)
    return {"name": name, "gates": len(net["gates"]), "blocks": len(pl.blocks),
            "profile": profile, "fabric": fabric, "kinds": kinds,
            "fallback_outputs": net.get("mapping", {}).get("fallback_outputs", []),
            "parts": {b.split(":")[1]: n for b, n in sorted(counts.items())},
            "rows": len(pl.rows), "hold_gt": hold_gt,
            "arcs": {f"{a}->{b}": v for (a, b), v in sorted(arc_table.items())},
            "files": {k: str(v) for k, v in written.items()}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--hold-gt", type=int, default=24,
                        help="hold gt in the prediction; 0 = arrival hi + 6")
    parser.add_argument("--steps", type=int, default=20)
    parser.add_argument("--map", dest="profile", default=None, choices=sorted(mapper.PROFILES),
                        help="cost profile (default: nor, or timing when the spec has a timing key)")
    parser.add_argument("--fabric", default="sparse", choices=("sparse", "dense", "auto"))
    args = parser.parse_args(argv)
    try:
        result = generate(args.spec, args.out, args.hold_gt or None, args.steps,
                          args.profile, args.fabric)
    except (GenError, nl.NetlistError, place.PlaceError, mapper.MapError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(errors="backslashreplace")
    sys.exit(main())
