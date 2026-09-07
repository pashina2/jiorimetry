#!/usr/bin/env python3
"""tools/llmgen/cell_to_program.py -- a `cellsearch` cell as a
`program.v0` placement program, so the operator can put it in the world with
one line of chat and look at it.

XORW-1 (`notes/2026-09-06-xorw1-reference-cells-in-world-order.md`, OC-D100:
'cell内生成の実物を見ていないので良い回路か判断しかねる'). REF-1 already
carried these cells into world coordinates and measured them
(`cell_to_world.py`, `notes/2026-09-06-ref1-record.md`); it did so through a
lane harness, at coordinates the lane chose. This module does the other half:
it writes the cell as an ARTIFACT -- a named program with a relative frame --
so the placing act belongs to the operator and the coordinates are theirs.

WHAT IS NOT DUPLICATED. The blocks come from `cell_to_world.rest_blocks`, the
same call REF-1 measured through, not from a second reading of the genome.
There is exactly one description of what a cell's blocks ARE in this
repository, and a program is a re-framing of it, never a second opinion. The
test pins that as a set equality against `cell_to_world`'s own world plan.

THREE DECISIONS, SAID OUT LOUD.

(1) THE FRAME IS SHIFTED SO THE BOUNDING BOX STARTS AT (0, 0, 0), WHICH MOVES
THE FLOOR. `Space.floor` sits at cell y = -1, one layer under the circuit, and
a program's coordinates are relative to where the operator places it. Leaving
y = -1 in the file would mean `/aiwb place ... 128 ...` puts a block at 127 --
the operator would be typing the circuit's height and getting the floor's. So
every cell is shifted by +1 in y (and by nothing in x/z, which already start
at 0), and the contract stated in each program's own description is: THE Y YOU
TYPE IS THE FLOOR; THE CIRCUIT IS ONE ABOVE IT. The shift is computed from the
blocks, never typed, so a cell whose floor moves moves this with it.

(2) THE LEVERS AND THE LAMP ARE DECLARED AS PORTS, NOT ONLY DESCRIBED. The
operator has to know which two blocks to flip and which one to watch, and a
sentence in a description is not addressable. `ports` is the schema's own key
for exactly this (OC-A7), so the offsets travel machine-readably AND in prose;
the prose is what a person reads in `/aiwb list`, the offsets are what a net
or a later checker reads.

(3) THE SCORES IN THE DESCRIPTION ARE COMPUTED AND CITED, NEVER TYPED. The
machine's score is `cellsearch.evaluate`, run here; the world's score belongs
to whichever lane ran the world, and is carried as a citation of the record
that holds it, because this module runs no Minecraft and may not claim a world
reading of its own. The citation travels WITH the cell (`Cell.record`) rather
than as one module-wide constant: REF-1 measured the first five and REF-2 the
two SPIKE-2 cells, and a program citing the wrong record would be exactly the
fabrication this decision exists to prevent. A number with
no source in the description would be exactly the fabrication the claim/evidence
model forbids.
"""

import argparse
import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import cell_to_world as W                                  # noqa: E402
import cellsearch as C                                     # noqa: E402

#: The records holding the WORLD readings quoted in the descriptions. This
#: module runs no Minecraft, so every world number in a description is a
#: citation of one of these.
WORLD_RECORD = "notes/2026-09-06-ref1-record.md"
REF2_RECORD = "notes/2026-09-07-ref2-record.md"

#: The seed payloads SPIKE-1b produced, relative to the repository root. A
#: source that is already a path is taken as it stands, so a cell out of
#: another lane's directory needs no second constant here.
SEED_DIR = "notes/2026-09-06-spike1b-live"

#: One row. `world` is a CITATION of `record` and `lane` is who read it;
#: the machine score is not here because it is computed at write time.
Cell = collections.namedtuple("Cell", "name source world lane record")

#: The cells this module writes: XORW-1's five, then the two XOR cells the
#: netlist search found (SPIKE-2) and REF-2 measured in a synthetic world.
CELLS = (
    Cell("ref_xor_cmp", "comparator", "4/4", "REF-1", WORLD_RECORD),
    Cell("ref_xor_torch", "torch", "4/4", "REF-1", WORLD_RECORD),
    Cell("or_seed1", "seed1", "3/4", "REF-1", WORLD_RECORD),
    Cell("or_seed2", "seed2", "3/4", "REF-1", WORLD_RECORD),
    Cell("or_seed3", "seed3", "3/4", "REF-1", WORLD_RECORD),
    Cell("xor_k2", "notes/2026-09-06-spike2-live/k2.json", "4/4",
         "REF-2", REF2_RECORD),
    Cell("xor_k3", "notes/2026-09-06-spike2-live/k3-s2.json", "4/4",
         "REF-2", REF2_RECORD),
)

BY_NAME = {cell.name: cell for cell in CELLS}

#: Cells stand this far apart on x when the operator places all five. The
#: widest is 7, so the gap is at least 9 -- past the Chebyshev 2 any block in
#: `machine` reads, which is the property decision (2) of `cell_to_world`
#: needs. `cell_to_world.STRIDE` (32) is the lane's own, larger choice; this
#: is the order's 16 and is checked against the read radius, not assumed.
STRIDE = 16

#: The largest Chebyshev distance at which `machine` lets one block read
#: another. `separation` must stay above it for two cells to be independent.
READ_RADIUS = 2


def source_path(source, root=None):
    """The `cell_to_world` source string for one cell: a `cellref` design name
    passes through, a repository-relative payload path is resolved against the
    root, and a bare seed name becomes its payload under `SEED_DIR`."""
    if source in W.cellref.DESIGNS:
        return source
    root = Path(root) if root else HERE.parents[2]
    if source.endswith(".json"):
        return str(root / source)
    return str(root / SEED_DIR / ("%s.json" % source))


def machine_score(space, genome, spec=C.SPEC_XOR):
    """`"4/4"` -- the machine's own score for this cell, computed here so a
    cell that stops scoring 4/4 renames itself in the description."""
    hits, _parts, _trace = C.evaluate(space, spec, genome)
    return "%d/%d" % (hits, len(spec))


def relativise(blocks):
    """`(shift, {pos: entry})` -- `blocks` moved so its bounding box starts at
    (0, 0, 0). Decision (1): the shift is measured from the blocks."""
    lo = tuple(min(p[i] for p in blocks) for i in range(3))
    shift = tuple(-v for v in lo)
    moved = {(p[0] + shift[0], p[1] + shift[1], p[2] + shift[2]): entry
             for p, entry in blocks.items()}
    return shift, moved


def block_rows(blocks):
    """The `blocks` key: `[x, y, z, blockstate]`, sorted, so one cell has one
    spelling and two runs produce byte-identical files."""
    return [[p[0], p[1], p[2], W.blockstate(*blocks[p])]
            for p in sorted(blocks)]


def describe(cell, source, space, genome, shift, levers, lamp, n_blocks):
    """The program's `description`: what it is, the two scores with their
    sources, and where to press. Decision (3). The world score and the record
    that holds it come off `cell`, so a cell with no world reading of its own
    cannot borrow another lane's."""
    return (
        "%s -- one %dx%dx%d `cellsearch` cell (%s) placed as raw blocks. "
        "machine %s (cellsearch.evaluate over SPEC_XOR, computed at write "
        "time); world %s (%s's reading, %s -- this program measures no "
        "world of its own). "
        "THE Y YOU TYPE IS THE FLOOR: the smooth-stone floor is the y=0 layer "
        "and the circuit is y=1. "
        "Levers at %s and %s (relative, on the floor, both off as written); "
        "lamp at %s. Flip exactly one lever and the lamp lights; flip both or "
        "neither and it stays dark. "
        "%d blocks. Place in empty space -- a cell with terrain within 2 "
        "blocks is a different circuit (cell_to_world decision 2)."
        % (cell.name, space.dims[0], space.dims[1], space.dims[2], source,
           machine_score(space, genome), cell.world, cell.lane, cell.record,
           list(levers[0]), list(levers[1]), list(lamp), n_blocks))


def to_program(cell, root=None):
    """The `program.v0` document for one cell -- a `Cell` or the name of one.

    Exactly the four keys `route.build_program` writes, plus the schema's
    optional `ports` (decision 2). `layout` is `blocks`, so the placement path
    translates these coordinates to the operator's anchor and does nothing
    else to them."""
    if not isinstance(cell, Cell):
        cell = BY_NAME[cell]
    label, space, genome = W.load_cell(source_path(cell.source, root))
    shift, blocks = relativise(W.rest_blocks(space, genome))
    levers = [tuple(p[i] + shift[i] for i in range(3)) for p in space.inputs]
    lamp = tuple(space.output[i] + shift[i] for i in range(3))
    rows = block_rows(blocks)
    return {
        "layout": "blocks",
        "name": cell.name,
        "description": describe(cell, label, space, genome, shift,
                                levers, lamp, len(rows)),
        "blocks": rows,
        "ports": [
            {"name": "a", "role": "drive", "width": 1,
             "offsets": [list(levers[0])],
             "note": "input lever A -- right-click it to toggle"},
            {"name": "b", "role": "drive", "width": 1,
             "offsets": [list(levers[1])],
             "note": "input lever B -- right-click it to toggle"},
            {"name": "out", "role": "tap", "width": 1,
             "offsets": [list(lamp)],
             "note": "the redstone lamp: lit means 1"},
        ],
    }


def programs(root=None, only=None):
    """Every cell by name, or only the named ones. Deterministic: the same
    input gives the same bytes."""
    chosen = CELLS if only is None else tuple(BY_NAME[k] for k in only)
    return {cell.name: to_program(cell, root) for cell in chosen}


def place_lines(base=(6000, 128, -3710), stride=STRIDE):
    """The `/aiwb place` lines the operator types, one per cell, spread on x."""
    bx, by, bz = base
    return ["/aiwb place %s %d %d %d" % (cell.name, bx + i * stride, by, bz)
            for i, cell in enumerate(CELLS)]


def separation(docs, base=(0, 0, 0), stride=STRIDE):
    """The smallest Chebyshev distance between blocks of DIFFERENT cells when
    the cells in `docs` are placed on `place_lines`' grid. Must stay above
    `READ_RADIUS` or two cells are one circuit. A cell absent from `docs`
    keeps its slot on the grid rather than letting its neighbours close up."""
    laid = []
    for i, cell in enumerate(CELLS):
        if cell.name not in docs:
            continue
        ox = base[0] + i * stride
        laid.append({(ox + r[0], base[1] + r[1], base[2] + r[2])
                     for r in docs[cell.name]["blocks"]})
    best = None
    for i, a in enumerate(laid):
        for b in laid[i + 1:]:
            for pa in a:
                for pb in b:
                    d = max(abs(pa[j] - pb[j]) for j in range(3))
                    if best is None or d < best:
                        best = d
    return best


def write(directory, root=None, only=None):
    """Write `<name>.json` for the chosen cells. Bytes are LF and UTF-8
    (opscheck C11 refuses CRLF), and written whole rather than appended."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    out = {}
    for name, doc in programs(root, only).items():
        path = directory / ("%s.json" % name)
        path.write_bytes(
            (json.dumps(doc, indent=2, sort_keys=False) + "\n").encode("utf-8"))
        out[name] = path
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", action="append", default=[],
                    help="a directory to write the programs into (repeatable)")
    ap.add_argument("--only", action="append", default=[],
                    choices=[cell.name for cell in CELLS],
                    help="write and report just this cell (repeatable); the "
                         "default is every cell")
    ap.add_argument("--root", help="repository root (for the seed payloads)")
    args = ap.parse_args(argv)

    only = args.only or None
    docs = programs(args.root, only)
    print("cells %d separation %s (read radius %d, stride %d)"
          % (len(docs), separation(docs), READ_RADIUS, STRIDE))
    for cell in CELLS:
        if cell.name not in docs:
            continue
        doc = docs[cell.name]
        print("  %-14s blocks %2d ports %d world %s (%s, %s)"
              % (cell.name, len(doc["blocks"]), len(doc["ports"]),
                 cell.world, cell.lane, cell.record))
    for directory in args.out:
        for name, path in write(directory, args.root, only).items():
            print("  wrote %s" % path)
    for line, cell in zip(place_lines(), CELLS):
        if cell.name in docs:
            print("  %s" % line)
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(errors="backslashreplace")
    raise SystemExit(main())
