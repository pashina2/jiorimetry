#!/usr/bin/env python3
"""tools/world/synthworld.py -- the void world a generated program
is measured in, and the worldprobe spec that drives it.

THE JOINT THAT WAS MISSING (RL-2, OC-D93/OC-D103). The toolchain could turn a
spec into a program, and could probe a world that already held one, but the two
were not connected: the four lines that write blocks into `.mca` + `level.dat`,
and the function that turns a placement into a worldprobe spec, existed only as
a lane's one-off under `notes/` (`notes/2026-09-06-ref1-live/build_ref1_world.py`,
whose own docstring calls itself deliberately dumb), and `notes/` is not
shipped. RL-1 measured the consequence: `worldprobe run` died inside
`provision` with `FileNotFoundError` on a world directory that nothing in
`tools/` could write. This module is those two halves raised into the
toolchain, unchanged in substance -- the idiom is still the one
`dynharness.synthesize_world` uses, and the spec is still the one REF-1 drove
five cells with.

WHY A VOID WORLD. The machine models everything outside the artifact as air.
Terrain beside a circuit is a different circuit, so the only world in which the
world's answer and the machine's answer are answers about the same thing is one
holding the artifact and nothing else. It also means no save is ever opened:
the world here is BUILT from the program, never copied from anywhere.

WHAT THIS MODULE DOES NOT DO. It runs no server and reads no world back -- that
is `worldprobe.py`'s half. It decides no redstone: every block it writes came
from `cell_to_world`, which got it from `machine`, and every expectation it
writes into a spec came from `gen.py`'s own prediction document.
"""

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for _p in (str(ROOT / "tools" / "llmgen"),
           # `worldgen` is the only writer in the repository that can put an
           # arbitrary block list into region files, and it lives OUTSIDE the
           # decision layer. Importing it is what makes "one command" true; it
           # is also why "one command" is not yet "one layer", which is the
           # operator's call (RL-1's TODO 6) and not this module's.
           str(HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import cell_to_world as ctw                                # noqa: E402
import worldgen                                            # noqa: E402

#: The lamp state a read counts as a 1.
LAMP_LIT = ctw.blockstate("minecraft:redstone_lamp", {"lit": "true"})

#: The run of equal readings `first_stable` wants before it calls a series
#: settled.
SETTLE_GT = 10

#: Added on top of the generator's own `hold_gt`. That number is the MACHINE's
#: settling time for this program; giving the world exactly the machine's
#: budget would beg the question this run exists to ask, so the world gets
#: room to be slower and still be seen to agree.
SETTLE_MARGIN_GT = 16


def build_world(placements, out_dir, name="synth"):
    """placements -> `<out_dir>/world` holding them and nothing else.

    The four-line worldgen idiom. The lines read like a quotation because they
    are one: `dynharness.synthesize_world` and `rom16gen` spell it the same
    way, and `notes/2026-09-06-ref1-live/build_ref1_world.py` spelled it a
    third time, which is the duplication this module exists to end."""
    out_dir = Path(out_dir)
    if out_dir.exists():
        raise ValueError("refusing to overwrite %s" % out_dir)
    version = worldgen.DEFAULT_DATA_VERSION
    level_dat = worldgen.build_level_dat(name, version)
    regions = worldgen.build_region_files(placements, {}, version)
    tsv = worldgen.render_blocks_tsv(placements).encode("utf-8")
    world = worldgen.World(name, placements, level_dat, regions, tsv)

    world_dir = out_dir / "world"
    (world_dir / "region").mkdir(parents=True)
    (world_dir / "level.dat").write_bytes(world.level_dat)
    for (rx, rz), data in world.regions.items():
        (world_dir / "region" / ("r.%d.%d.mca" % (rx, rz))).write_bytes(data)
    (out_dir / "blocks.tsv").write_bytes(world.tsv)
    return {"world_dir": str(world_dir), "blocks": len(placements),
            "regions": ["r.%d.%d.mca" % rz for rz in sorted(world.regions)],
            "data_version": version, "name": name}


def world_from_program(program, predict, out_dir, base=(0, 0, 0), name=None):
    """A generated program -> a void world holding it, on disk.

    Returns `(entry, info)`: the `cell_to_world` entry (blocks in world
    coordinates, the levers that drive it, the lamps that answer, and the
    machine's column) and a record of what was written. The entry is exactly
    what `spec_of` needs, so no caller ever re-derives where anything landed."""
    entry = ctw.program_entry(program, predict, origin=tuple(base),
                              label=name or program.get("name"))
    info = build_world(entry["blocks"], out_dir, name=entry["label"] or "synth")
    info["origin"] = list(base)
    return entry, info


def drive_names(entry, inputs=None):
    """One drive name per lever, in declared order.

    The spec's own input names are used when the caller has them -- `sum`
    reads better than `out0` in a table a human checks -- and positional names
    are the fallback, because a program declares port WIDTH, not port names."""
    if inputs and len(inputs) == len(entry["levers"]):
        return list(inputs)
    return ["in%d" % i for i in range(len(entry["levers"]))]


def read_names(entry, outputs=None):
    """One read name per lamp, in declared order. See `drive_names`."""
    if outputs and len(outputs) == len(entry["lamps"]):
        return list(outputs)
    return ["out%d" % i for i in range(len(entry["lamps"]))]


def spec_of(entry, world_dir, out_dir, template, rcon_port,
            inputs=None, outputs=None, max_gt=None, settle_gt=SETTLE_GT,
            hold_gt=None, name=None):
    """The worldprobe spec that drives one generated program.

    drives  -- one lever per declared input, at the rig's own position and
               with the rig's own face and facing, both of which worldprobe
               needs in order to issue the attachment update after a setblock.
    reads   -- one `state` read per declared output, matching a LIT lamp,
               carrying `bit` i so worldprobe folds them into one
               `final_value`.
    regimes -- one per vector of the truth table, in vector order, carrying the
               MACHINE's answer as `expect`.

    worldprobe records an expectation and never fails on it. That is the
    property which makes this a measurement rather than an assertion: a
    disagreement has to be read off the table, and cannot be inferred from an
    exit code that is 0 either way."""
    lo = [min(p[i] for p in entry["blocks"]) - 1 for i in range(3)]
    hi = [max(p[i] for p in entry["blocks"]) + 1 for i in range(3)]
    names = drive_names(entry, inputs)
    rnames = read_names(entry, outputs)
    off = entry["lever_off"]

    drives = {}
    for drive_name, pos in zip(names, entry["levers"]):
        drives[drive_name] = {"kind": "lever", "pos": list(pos),
                              "face": off["face"], "facing": off["facing"]}
    reads = []
    for i, (read_name, pos) in enumerate(zip(rnames, entry["lamps"])):
        reads.append({"name": read_name, "pos": list(pos), "bit": i,
                      "match": LAMP_LIT})

    if max_gt is None:
        max_gt = (hold_gt or 24) + SETTLE_MARGIN_GT
    regimes = []
    for vector in sorted(entry["machine"]):
        row = entry["machine"][vector]
        if len(vector) != len(names):
            raise ValueError("vector %r does not name all %d input(s)"
                             % (vector, len(names)))
        if len(row["lamps"]) != len(rnames):
            # Both lists come from the program's `out` port, so they agree by
            # construction -- and `zip` would quietly drop the odd one if they
            # ever stopped, writing an expectation for a read nobody takes.
            raise ValueError("the machine answers %d lamp(s) at %r but %d "
                             "read(s) are declared"
                             % (len(row["lamps"]), vector, len(rnames)))
        want_reads = {n: bool(v) for n, v in zip(rnames, row["lamps"])}
        want_value = 0
        for i, v in enumerate(row["lamps"]):
            want_value |= (1 if v else 0) << i
        regimes.append({
            "name": "v%s" % vector,
            "inputs": {n: int(b) for n, b in zip(names, vector)},
            "max_gt": max_gt, "settle_gt": settle_gt,
            "expect": {"final_value": want_value, "final_reads": want_reads},
        })

    return {
        "name": name or entry["label"] or "synth",
        "world": {"template": str(template), "world_dir": str(world_dir),
                  "bbox": {"min": lo, "max": hi}},
        "server": {"host": "127.0.0.1", "rcon_port": int(rcon_port),
                   "java_xmx": "3G"},
        "drives": drives,
        "reads": reads,
        "regimes": regimes,
        "limits": {"max_rcon": 60000},
        "out_dir": str(out_dir),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--program", required=True,
                    help="a generated <name>.program.json")
    ap.add_argument("--predict",
                    help="its <name>.predict.json (default: beside it)")
    ap.add_argument("--out", required=True,
                    help="directory to write world/ and the spec into "
                         "(must not exist)")
    ap.add_argument("--template", required=True,
                    help="a worldprobe server template directory")
    ap.add_argument("--rcon-port", type=int, default=25585)
    ap.add_argument("--base", default="100,0,100")
    args = ap.parse_args(argv)

    program, predict = ctw.load_program(args.program, args.predict)
    base = tuple(int(v) for v in args.base.split(","))
    entry, info = world_from_program(program, predict, Path(args.out),
                                     base=base)
    spec = spec_of(entry, info["world_dir"], args.out, args.template,
                   args.rcon_port, hold_gt=predict.get("hold_gt"))
    spec_path = Path(args.out) / ("%s.spec.json" % spec["name"])
    spec_path.write_bytes(
        (json.dumps(spec, indent=1, sort_keys=False) + "\n").encode("utf-8"))
    print("world %s blocks %d regions %s"
          % (info["world_dir"], info["blocks"], info["regions"]))
    print("drives %d reads %d regimes %d rcon %d"
          % (len(spec["drives"]), len(spec["reads"]), len(spec["regimes"]),
             args.rcon_port))
    print("spec %s" % spec_path)
    return 0


if __name__ == "__main__":                                 # pragma: no cover
    # `tools/test_console_encoding.py` rule: this CLI prints paths and program
    # names read out of files, which is the case a scan of this source cannot
    # see.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(errors="backslashreplace")
    raise SystemExit(main())
