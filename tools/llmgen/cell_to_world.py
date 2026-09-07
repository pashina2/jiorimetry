#!/usr/bin/env python3
"""tools/llmgen/cell_to_world.py -- carry a cell or a generated
program out of the machine and into world coordinates, mechanically.

TWO SHAPES, ONE ENTRY (RL-2). It began as the exit for a `cellsearch` cell and
now takes `gen.py`'s programs too, because the shipping path needs the same
translation for the artifact the toolchain actually generates. The shape is
decided by a KEY -- `space` for a cell, `layout` for a program -- and the two
come back in one entry shape, so the world builder never asks which it got.
The differences that survive that merge are named on `program_entry`, and the
larger of the two is that a program does not carry the lever that drives it.

REF-1 (`notes/2026-09-06-ref1-reference-xor-world-check-order.md`, OC-D92).
Everything said about a cell so far has been said by the machine alone:
`cellref`'s two hand-built XORs score 4/4 and the search's best cells score
3/4 against a transcription of the 1.20.6 source, and no Minecraft has ever
been asked. This module is the bridge that lets one ask -- it turns a cell
into world positions and blockstate text, and nothing else. It runs no
server, opens no save, and has no redstone opinion of its own: every block it
hands out came from `machine`.

THREE DECISIONS, SAID OUT LOUD.

(1) THE STATE WRITTEN IS THE MACHINE'S REST STATE, NOT THE VOCABULARY'S
DEFAULT. `power`, `lit`, `powered` and a dust's four connection properties
are COMPUTED, never typed (`machine`'s own docstring, DESIGN section 2). A
cell written with `power=0` dust and `lit=true` torches would be a world that
is not at rest, and redstone does not re-settle without a block update, so
the first reading would be of a state nobody designed. So the blocks handed
out here are the snapshot of `Machine(...).run_to_rest()` under a chosen rest
vector -- which makes the first world reading a check of the machine's
fixpoint too, not only of its truth table.

(2) THE FLOOR IS EXACTLY THE MACHINE'S FLOOR. `Space.floor` is nx by nz
smooth stone one layer down and NOTHING else; the machine models every other
cell around the box as air. A world with terrain under or beside a cell is a
DIFFERENT circuit, so these placements belong in a void world, and cells must
stand far enough apart that neither can read the other. `separation` is the
measurement of that, and `STRIDE` is chosen to keep it large.

(3) A COMPARATOR'S STORED SIGNAL IS BLOCK-ENTITY STATE AND IS NOT CARRIED.
`ComparatorBlockEntity.outputSignal` is not a blockstate property, so a
placed comparator starts at 0 whatever the machine's `cmp_out` said. That is
why `SWEEP` opens with a warm-up vector: the first lever flip makes the world
recompute every gate's stored signal, and the readings that count come after
it. The warm-up is driven and read like any other vector, so comparing it
with the second reading of the same vector says whether the gap moved
anything.
"""

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
for _p in (str(HERE), str(HERE.parent / "bridge")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import cellref                                             # noqa: E402
import cellsearch as C                                     # noqa: E402
import gen                                                 # noqa: E402
import library                                             # noqa: E402
import machine as M                                        # noqa: E402
# The inverse of `blockstate` already exists, in the module whose whole job is
# inverting this spelling; a second parser here would be a second place for the
# two to disagree about `[a=b,c=d]`. `litematic_writer` is stdlib-only, so this
# costs an import and nothing else.
from litematic_writer import parse_block_string            # noqa: E402


#: The vector a cell is WRITTEN at rest in.
REST_VECTOR = (False, False)

#: The drive order. The leading (True, True) is the warm-up of decision (3);
#: the trailing (False, False) repeats the opening reading, so a cell that
#: remembers an earlier vector shows up as a disagreement between the two.
SWEEP = ((True, True), (False, False), (False, True), (True, False),
         (True, True), (False, False))

#: Cells stand this far apart on x. The widest cell is 7 wide, so the gap
#: between two cells' blocks is at least 32 - 7 = 25 -- past the 16 the order
#: asks for, and far past any read the machine performs (Chebyshev 2).
STRIDE = 32


def vector_key(vector):
    """`(False, True)` -> `"01"`. One name for a vector, in the tables and in
    the machine column, so a world row can be looked up by the same key
    whatever order it was driven in."""
    return "".join("1" if v else "0" for v in vector)


#: The four vector keys, taken from the spec rather than typed, so a spec with
#: other vectors renames these by itself.
VECTOR_KEYS = tuple(vector_key(v) for v, _want in C.SPEC_XOR)


def blockstate(name, props):
    """`minecraft:repeater[delay=1,facing=west,...]` -- the setblock spelling.
    Properties are sorted, so one block always spells one way."""
    if not props:
        return name
    inner = ",".join("%s=%s" % (k, props[k]) for k in sorted(props))
    return "%s[%s]" % (name, inner)


def space_from_payload(payload):
    """The `Space` a `cellsearch` payload describes. `cellsearch.describe`
    writes dims, inputs and output, which is all `Space` needs."""
    described = payload["space"]
    return C.Space(tuple(described["dims"]),
                   [tuple(p) for p in described["inputs"]],
                   tuple(described["output"]))


def load_cell(source):
    """(label, space, genome) for one cell.

    `source` is a reference design's name (a key of `cellref.DESIGNS`) or the
    path of a `cellsearch` payload."""
    if source in cellref.DESIGNS:
        space, genome = cellref.reference(source)
        return source, space, genome
    payload = json.loads(Path(source).read_text(encoding="utf-8"))
    space = space_from_payload(payload)
    return Path(source).stem, space, tuple(payload["best"]["genome"])


def rest_blocks(space, genome, vector=REST_VECTOR, limit=C.REST_LIMIT):
    """The machine's rest state under `vector`, as {pos: (name, props)}.

    Decision (1). `machine.MachineError` propagates: a cell with no rest state
    has no placement, and inventing one would be inventing the answer."""
    m = M.Machine(space.blocks(genome, vector))
    m.run_to_rest(limit=limit)
    return m.snapshot()


def to_world(blocks, origin):
    """Cell coordinates to world coordinates. The floor's y = -1 travels with
    them, so `origin` is where the cell's (0, 0, 0) lands."""
    ox, oy, oz = origin
    return {(ox + x, oy + y, oz + z): (name, dict(props))
            for (x, y, z), (name, props) in blocks.items()}


def lever_positions(space, origin):
    """The input levers in world coordinates, in the order a vector names."""
    ox, oy, oz = origin
    return [(ox + x, oy + y, oz + z) for x, y, z in space.inputs]


def lamp_position(space, origin):
    ox, oy, oz = origin
    x, y, z = space.output
    return (ox + x, oy + y, oz + z)


def lever_props(space, genome, on):
    """The lever blockstate the machine places, with `powered` set. Read back
    out of `Space.blocks` rather than typed, so the two cannot drift."""
    vector = tuple(on for _ in space.inputs)
    return space.blocks(genome, vector)[space.inputs[0]][1]


def machine_table(space, genome, spec=C.SPEC_XOR):
    """What the machine says the lamp does on each vector -- the column the
    world is compared against."""
    _hits, _parts, trace = C.evaluate(space, spec, genome)
    out = {}
    for row in trace:
        out[vector_key(row["vector"])] = {"lamp": row["lamp"],
                                          "want": row["want"],
                                          "rest_gt": row["rest_gt"]}
    return out


# --- the generated-program shape -------------------------------------------
#
# Everything above this line is about a `cellsearch` cell: a small box the
# search ran in, which carries its own levers and its one lamp INSIDE the
# blocks the machine settled. `llmgen/gen.py` writes a different document -- a
# `program.v0` file whose blocks are the artifact and nothing else -- and the
# two shapes meet here, in one entry shape the world builder can consume
# without asking which kind it was handed.


def payload_shape(payload):
    """`"cell"` or `"program"`, decided by a KEY and never by a filename.

    A `cellsearch` payload describes the box the search ran in, so it carries
    `space`; a program declares the generator family that built it, so it
    carries `layout` -- the one key `schema/workbench/program.v0.schema.json`
    makes required, which is what makes it a safe discriminator rather than a
    convenient one. A document with both keys, or neither, is REFUSED: guessing
    which half to believe is how a world ends up answering about a circuit
    nobody asked for."""
    has_space = "space" in payload
    has_layout = "layout" in payload
    if has_space and has_layout:
        raise ValueError("payload carries both `space` (a cellsearch cell) and "
                         "`layout` (a program); which one it is has to be said "
                         "by the writer, not guessed here")
    if has_space:
        return "cell"
    if has_layout:
        return "program"
    raise ValueError("payload is neither a cellsearch cell (no `space`) nor a "
                     "program (no `layout`); keys present: %s"
                     % (", ".join(sorted(payload)) or "none"))


def program_blocks(payload):
    """`{(x, y, z): (name, props)}` for a `layout: blocks` program.

    The program's own frame, untranslated. Only the `blocks` family is read:
    the other layouts name a generator that has to RUN to have blocks at all,
    and this module places what it is handed rather than building anything."""
    if payload.get("layout") != "blocks":
        raise ValueError("cell_to_world reads `layout: blocks` programs -- the "
                         "shape `llmgen/gen.py` writes; this one is %r, whose "
                         "blocks only exist once its generator has run"
                         % (payload.get("layout"),))
    out = {}
    for i, row in enumerate(payload["blocks"]):
        pos = (int(row[0]), int(row[1]), int(row[2]))
        if pos in out:
            raise ValueError("blocks[%d]: %s is placed twice" % (i, list(pos)))
        name, props = parse_block_string(row[3])
        out[pos] = (name, props)
    return out


def program_ports(payload):
    """`{port name: [(x, y, z), ...]}` from the program's declared ports.

    `offsets` are in the program's own frame (the schema says so in as many
    words), which is the frame `program_blocks` returns, so the two need no
    reconciling."""
    out = {}
    for port in payload.get("ports", []):
        cells = [tuple(int(v) for v in off) for off in port["offsets"]]
        if len(cells) != port["width"]:
            raise ValueError("port %r declares width %d but lists %d offsets"
                             % (port["name"], port["width"], len(cells)))
        out[port["name"]] = cells
    return out


def program_machine_table(predict, out_cells):
    """The machine's column for a program, keyed by vector.

    Read out of `gen.predict`'s own document rather than recomputed: the
    generator already ran the machine on every vector of the truth table and
    refused to emit anything that disagreed with the spec, so re-deriving it
    here would only add a second opinion to disagree with. `bits` is the
    settled lamps in DECLARED OUTPUT ORDER, which is the order the spec's own
    truth table is written in, and `expected` is that table's entry."""
    lamp_ids = [gen.point_id(pos, library.LAMP) for pos in out_cells]
    table = {}
    for vector, row in predict["vectors"].items():
        settled = row["settled_lamps_at_hold"]
        missing = [i for i in lamp_ids if i not in settled]
        if missing:
            raise ValueError("prediction has no settled lamp for %s -- the "
                             "predict file and the program disagree about "
                             "where the outputs are" % ", ".join(missing))
        lamps = [settled[i] == "true" for i in lamp_ids]
        table[vector] = {"bits": "".join("1" if v else "0" for v in lamps),
                         "expected": row["expected"],
                         "lamps": lamps}
    return table


def program_entry(payload, predict, origin=(0, 0, 0), label=None, source=None):
    """The entry shape `layout` builds, for a generated program.

    THE TWO PLACES THE SHAPES DIFFER, SAID OUT LOUD.

    (1) A CELL CARRIES ITS DRIVE RIG; A PROGRAM DOES NOT. The search's cell has
    its two levers and its lamp inside the box the machine settled -- the
    one-cell pin counts them: 25 floor + 14 parts + 2 levers + 1 lamp. A
    program's blocks are the circuit alone, and the igniter its own prediction
    was computed against is built outside it, in `gen.drive_rig`. So this adds
    that rig, IMPORTED and never retyped: a world driven by a different rig is
    a different circuit, and its readings would answer a question nobody asked.

    (2) A CELL HAS ONE LAMP; A PROGRAM HAS ONE PER DECLARED OUTPUT. So a
    program entry carries `lamps`, a list in declared order, and deliberately
    has NO `lamp` key -- a consumer that wants a single lamp out of a two-output
    adder has to say which one, rather than silently getting the first."""
    blocks = program_blocks(payload)
    ports = program_ports(payload)
    for role in ("in", "out"):
        if role not in ports:
            raise ValueError("program declares no %r port; there is nothing to "
                             "%s" % (role, "drive" if role == "in" else "read"))
    rig, levers = gen.drive_rig(ports["in"])
    overlap = sorted(set(rig) & set(blocks))
    if overlap:
        raise ValueError("the drive rig would overwrite the artifact at %s"
                         % ", ".join(str(list(p)) for p in overlap))
    lever_off = dict(rig[levers[0]][1])
    lever_on = dict(lever_off, powered="true")
    every = dict(blocks)
    every.update(rig)
    lo = [min(p[i] for p in every) for i in range(3)]
    hi = [max(p[i] for p in every) for i in range(3)]
    return {
        "label": label or payload.get("name") or "program",
        "source": source,
        "shape": "program",
        "origin": list(origin),
        "dims": [hi[i] - lo[i] + 1 for i in range(3)],
        "parts": len(blocks),
        "rig": len(rig),
        "blocks": to_world(every, origin),
        "levers": [tuple(o + p for o, p in zip(origin, lv)) for lv in levers],
        "lamps": [tuple(o + p for o, p in zip(origin, c)) for c in ports["out"]],
        "lever_off": lever_off,
        "lever_on": lever_on,
        "machine": program_machine_table(predict, ports["out"]),
    }


def load_program(source, predict=None):
    """`(payload, prediction)` for a program path.

    `gen.py` writes `<name>.program.json` and `<name>.predict.json` side by
    side in one call, so the prediction is looked for beside the program when
    it is not named -- and its absence is an error rather than a shrug, because
    a program with no machine column has nothing for the world to be compared
    WITH."""
    path = Path(source)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if predict is None:
        predict = path.with_name(path.name.replace(".program.json",
                                                   ".predict.json"))
        if predict == path or not Path(predict).exists():
            raise ValueError("no prediction beside %s; pass one explicitly -- a "
                             "program without its machine column can be placed "
                             "but not judged" % path)
    prediction = json.loads(Path(predict).read_text(encoding="utf-8"))
    return payload, prediction


def entry_of(source, origin=(0, 0, 0), predict=None):
    """One entry for one source, whichever of the two shapes it is.

    A `cellref` design name is a cell by definition; a path is opened and asked
    which shape it is."""
    if source in cellref.DESIGNS:
        return cell_entry(source, origin)
    payload = json.loads(Path(source).read_text(encoding="utf-8"))
    if payload_shape(payload) == "cell":
        return cell_entry(source, origin)
    payload, prediction = load_program(source, predict)
    return program_entry(payload, prediction, origin=origin,
                         label=Path(source).stem.replace(".program", ""),
                         source=str(source))


def cell_entry(source, origin):
    """One `cellsearch` cell as an entry."""
    label, space, genome = load_cell(source)
    lamp = lamp_position(space, origin)
    return {
        "label": label,
        "source": source,
        "shape": "cell",
        "dims": list(space.dims),
        "origin": list(origin),
        "parts": space.parts(genome),
        "blocks": to_world(rest_blocks(space, genome), origin),
        "levers": lever_positions(space, origin),
        "lamp": lamp,
        "lamps": [lamp],
        "lever_off": lever_props(space, genome, False),
        "lever_on": lever_props(space, genome, True),
        "machine": machine_table(space, genome),
    }


def layout(sources, base=(0, 0, 0), stride=STRIDE):
    """One entry per `sources` entry, laid out along x.

    Cells and generated programs may be mixed in one call: they come back in
    the same shape, and `placements`, `bbox` and `separation` below read only
    `blocks`, which both of them have."""
    out = []
    bx, by, bz = base
    for i, source in enumerate(sources):
        out.append(entry_of(source, (bx + i * stride, by, bz)))
    return out


def separation(cells):
    """The smallest Chebyshev distance between blocks of DIFFERENT cells.
    Decision (2) holds only while this stays large; `None` for one cell."""
    best = None
    for i, a in enumerate(cells):
        for b in cells[i + 1:]:
            for pa in a["blocks"]:
                for pb in b["blocks"]:
                    d = max(abs(pa[0] - pb[0]), abs(pa[1] - pb[1]),
                            abs(pa[2] - pb[2]))
                    if best is None or d < best:
                        best = d
    return best


def placements(cells):
    """{world pos: (name, props)} for every cell at once -- the shape
    `tools/world/worldgen.py` takes. Two cells may not claim one
    position; `STRIDE` is what keeps that true, and this checks it."""
    out = {}
    for cell in cells:
        for pos, entry in cell["blocks"].items():
            if pos in out:
                raise ValueError("two cells both place %s" % (list(pos),))
            out[pos] = entry
    return out


def bbox(cells, margin=1):
    """(min, max) enclosing every block, grown by `margin` so the forceload
    covers the air a cell reads into."""
    every = [pos for cell in cells for pos in cell["blocks"]]
    lo = [min(p[i] for p in every) - margin for i in range(3)]
    hi = [max(p[i] for p in every) + margin for i in range(3)]
    return lo, hi


def placement_lines(cells):
    """`x y z blockstate`, sorted -- the human-readable table. The machine
    never spells air, so no line here is air."""
    lines = []
    for cell in cells:
        for pos in sorted(cell["blocks"]):
            name, props = cell["blocks"][pos]
            lines.append("%d %d %d %s"
                         % (pos[0], pos[1], pos[2], blockstate(name, props)))
    return lines


def plan(sources, base=(0, 0, 0), stride=STRIDE):
    """The whole job as one JSON-able dict: where every block goes, which
    levers to drive, which lamps to read, and what the machine predicts."""
    cells = layout(sources, base=base, stride=stride)
    lo, hi = bbox(cells)
    rows = []
    for cell in cells:
        row = {
            "label": cell["label"], "source": cell["source"],
            "shape": cell["shape"],
            "dims": cell["dims"], "origin": cell["origin"],
            "parts": cell["parts"], "blocks": len(cell["blocks"]),
            "levers": [list(p) for p in cell["levers"]],
            "lamps": [list(p) for p in cell["lamps"]],
            "lever_face": cell["lever_off"]["face"],
            "lever_facing": cell["lever_off"]["facing"],
            "lever_off": blockstate(M.LEVER, cell["lever_off"]),
            "lever_on": blockstate(M.LEVER, cell["lever_on"]),
            "lamp_lit_match": blockstate(M.LAMP, {"lit": "true"}),
            "machine": cell["machine"],
        }
        if "lamp" in cell:
            row["lamp"] = list(cell["lamp"])
        rows.append(row)
    return {
        "base": list(base), "stride": stride,
        "rest_vector": [bool(v) for v in REST_VECTOR],
        "sweep": [[bool(v) for v in vec] for vec in SWEEP],
        "sweep_keys": [vector_key(vec) for vec in SWEEP],
        "vector_keys": list(VECTOR_KEYS),
        "separation": separation(cells),
        "bbox": {"min": lo, "max": hi},
        "cells": rows,
        "placements": placement_lines(cells),
    }


def machine_row(cell_row):
    """The machine's four lamp readings as `0101`, in `VECTOR_KEYS` order."""
    return "".join("1" if cell_row["machine"][key]["lamp"] else "0"
                   for key in VECTOR_KEYS)


def machine_summary(row):
    """The machine's column for either shape, as `vector=bits` in vector order.

    A cell answers one bit per vector and its vectors are the XOR spec's four;
    a program answers one bit per declared output and its vectors are its own
    truth table's, which may be eight or sixteen. So this reads the keys the
    entry actually has instead of the four this module knows by name."""
    table = row["machine"]
    return " ".join(
        "%s=%s" % (key, table[key]["bits"] if "bits" in table[key]
                   else ("1" if table[key]["lamp"] else "0"))
        for key in sorted(table))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("sources", nargs="+",
                    help="a cellref design name, a cellsearch payload path, or "
                         "a generated <name>.program.json (its prediction is "
                         "read from beside it)")
    ap.add_argument("--base", default="0,0,0",
                    help="world coordinates of the first cell's (0,0,0)")
    ap.add_argument("--stride", type=int, default=STRIDE)
    ap.add_argument("--out", help="write the plan as JSON here")
    args = ap.parse_args(argv)

    base = tuple(int(v) for v in args.base.split(","))
    payload = plan(args.sources, base=base, stride=args.stride)
    if args.out:
        Path(args.out).write_bytes(
            (json.dumps(payload, indent=2, sort_keys=False) + "\n").encode("utf-8"))
    print("cells %d separation %s blocks %d bbox %s %s"
          % (len(payload["cells"]), payload["separation"],
             len(payload["placements"]), payload["bbox"]["min"],
             payload["bbox"]["max"]))
    for row in payload["cells"]:
        print("  %-11s %-7s dims %s origin %s parts %3d machine %s"
              % (row["label"], row["shape"], row["dims"], row["origin"],
                 row["parts"], machine_summary(row)))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(errors="backslashreplace")
    raise SystemExit(main())
