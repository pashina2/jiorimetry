#!/usr/bin/env python3
"""tools/llmgen/cellref.py -- reference XOR cells built BY HAND from
the machine's rules, so the box `cellsearch` searches is KNOWN to contain a
4/4 answer before the search runs (SPIKE-1b, `notes/2026-09-06-spike1b-cell-
search-box-order.md` section 1-1).

THIS MODULE IS HUMAN DESIGN AND `cellsearch` MUST NEVER IMPORT IT. That is why
it is a separate file: SPIKE-1's claim is that the search reaches its cells
from the machine's rules alone, with no redstone design in the loop, and
`test_llmgen.py` pins `cellsearch`'s import list to keep that true. The
direction of the dependency is cellref -> cellsearch, never the reverse. What
these references buy is a different thing: they separate 'the box holds no
answer' from 'the search cannot find the answer the box holds', which is the
question SPIKE-1 left open when 3x3x3 turned out to be too small for the two
comparator form.

Both designs are expressed as `cellsearch` genomes, not as free block dicts:
that is the point. A reference the search's own alphabet cannot spell would
not prove the box contains anything the search could find.

Design (i) TWO COMPARATORS, |A-B| = (A and not B) or (B and not A). Each
comparator takes a lever on its back and the OTHER lever, repeated to 15, on
one side, in subtract mode; the two outputs meet at the lamp. The crossing
SPIKE-1 could not fit in 3x3x3 is dodged, not solved: C1 is fed from its
south side and C2 from its north side, so A's line runs along one edge row
and B's along the other and they never share a cell. The side feed must be a
REPEATER, not dust: subtract needs side >= back when both levers are on, and
dust attenuates 1 per cell, so a dust side would leave 15 - 12 = 3 and light
the lamp on the (1,1) vector.

Design (ii) FOUR TORCHES, out = (A and not B) or (B and not A) as four NOR
gates. A NOR here is one solid block with the inputs' dust pointing into it
and a WALL torch attached to it -- planar, because a dust strong-powers the
block it points into and a wall torch reads its support. T1 = not A, T2 = not
B; S1 takes T1 and B, S2 takes T2 and A; the two output torches sit on either
side of the lamp and each lights it alone. Same dodge: A's long line runs
along one edge row, B's along the other.
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import cellsearch as C                                     # noqa: E402
import machine as M                                        # noqa: E402


def vocab_index(name, props):
    """The alphabet index of one block state, or ValueError. The reference is
    only a reference if the search could spell it."""
    for i, entry in enumerate(C.VOCABULARY):
        if entry is None:
            continue
        if entry[0] == name and entry[1] == props:
            return i
    raise ValueError("%s %s is not in the search alphabet" % (name, props))


def stone():
    return vocab_index(M.SMOOTH_STONE, {})


def dust():
    return vocab_index(M.DUST, {"power": "0"})


def wall_torch(facing):
    return vocab_index(M.WALL_TORCH, {"lit": "true", "facing": facing})


def repeater(facing, delay="1"):
    return vocab_index(M.REPEATER, {"facing": facing, "delay": delay,
                                    "locked": "false", "powered": "false"})


def comparator(facing, mode="subtract"):
    return vocab_index(M.COMPARATOR, {"facing": facing, "mode": mode,
                                      "powered": "false"})


def genome_of(space, parts):
    """A genome from {pos: alphabet index}. Every named cell must be editable."""
    unknown = [p for p in parts if p not in space.editable]
    if unknown:
        raise ValueError("not editable: %s" % (sorted(unknown),))
    return tuple(parts.get(pos, 0) for pos in space.editable)


# ------------------------------------------------------------------ designs
def design_comparator(nx=5, nz=5, z=2):
    """Design (i) in an nx x 1 x nz box, levers on row z, lamp on the mirror
    plane. Returns (space, {pos: alphabet index})."""
    xa, xb = 0, nx - 1
    xm = nx // 2
    space = C.Space((nx, 1, nz), [(xa, 0, z), (xb, 0, z)], (xm, 0, z))
    c1x, c2x = xa + 1, xb - 1
    parts = {
        (c1x, 0, z): comparator("west"),
        (c2x, 0, z): comparator("east"),
        (c1x, 0, z + 1): repeater("south"),
        (c2x, 0, z - 1): repeater("north"),
    }
    for x in range(c1x + 1, xm):
        parts[(x, 0, z)] = dust()
    for x in range(xm + 1, c2x):
        parts[(x, 0, z)] = dust()
    parts[(xa, 0, z - 1)] = dust()
    for x in range(xa, c2x + 1):
        parts[(x, 0, z - 2)] = dust()
    parts[(xb, 0, z + 1)] = dust()
    for x in range(c1x, xb + 1):
        parts[(x, 0, z + 2)] = dust()
    return space, parts


def design_torch(nx=7, nz=5, z=2):
    """Design (ii) in an nx x 1 x nz box."""
    xa, xb = 0, nx - 1
    xm = nx // 2
    space = C.Space((nx, 1, nz), [(xa, 0, z), (xb, 0, z)], (xm, 0, z))
    n, s = z - 2, z + 2
    parts = {
        (xa, 0, z - 1): dust(),
        (xa, 0, n): stone(),
        (xa + 1, 0, n): wall_torch("east"),
        (xb, 0, z + 1): dust(),
        (xb, 0, s): stone(),
        (xb - 1, 0, s): wall_torch("west"),
        (xm, 0, n): stone(),
        (xm, 0, n + 1): wall_torch("south"),
        (xm, 0, s): stone(),
        (xm, 0, s - 1): wall_torch("north"),
    }
    for x in range(xa + 2, xm):
        parts[(x, 0, n)] = dust()
    for x in range(xm + 1, xb + 1):
        parts[(x, 0, n)] = dust()
    parts[(xb, 0, z - 1)] = dust()
    for x in range(xm + 1, xb - 1):
        parts[(x, 0, s)] = dust()
    for x in range(xa, xm):
        parts[(x, 0, s)] = dust()
    parts[(xa, 0, z + 1)] = dust()
    return space, parts


DESIGNS = {"comparator": design_comparator, "torch": design_torch}

#: The box SPIKE-1b searches: the SMALLEST box measured to hold BOTH designs
#: (`shrink` below is the measurement). The comparator form needs 5x1x5 and
#: the torch form 7x1x5, and 7x1x5 dominates 5x1x5 in every dimension, so the
#: comparator form fits inside it too -- `reference("comparator", SEARCH_BOX)`
#: is 4/4 there as well, with two extra dust cells carrying the outputs the
#: extra width put between the comparators and the lamp.
SEARCH_BOX = (7, 1, 5)


def reference(name, dims=None):
    """(space, genome) for one reference design, in `dims` or its own
    smallest box."""
    nx, _ny, nz = dims or SMALLEST[name]
    space, parts = DESIGNS[name](nx=nx, nz=nz, z=nz // 2)
    return space, genome_of(space, parts)


#: The smallest box each design was measured to reach 4/4 in (see `shrink`).
SMALLEST = {"comparator": (5, 1, 5), "torch": (7, 1, 5)}


def single_removals(name, dims=None):
    """Every cell of the reference emptied one at a time, scored.

    The negative control for 'this cell is the reference': a part the design
    does not need would come back still 4/4, and the count of parts whose
    removal costs a hit is what the pin asserts. Yields (pos, hits, parts)."""
    nx, _ny, nz = dims or SMALLEST[name]
    space, parts = DESIGNS[name](nx=nx, nz=nz, z=nz // 2)
    for pos in sorted(parts):
        cut = dict(parts)
        del cut[pos]
        hits, count, _trace = C.evaluate(space, C.SPEC_XOR, genome_of(space, cut))
        yield pos, hits, count


def check(name, space, parts, spec=C.SPEC_XOR):
    genome = genome_of(space, parts)
    legal = space.legal(genome)
    hits, count, trace = C.evaluate(space, spec, genome)
    return {"design": name, "dims": list(space.dims),
            "cells": len(space.cells), "editable": len(space.editable),
            "legal": legal, "hits": hits, "parts": count, "trace": trace,
            "inputs": [list(p) for p in space.inputs],
            "output": list(space.output),
            "blocks": [{"pos": list(p), "block": C.VOCABULARY[parts[p]][0],
                        "state": dict(C.VOCABULARY[parts[p]][1])}
                       for p in sorted(parts)]}


#: The boxes tried when looking for the smallest one each design fits in.
#: An even nx is refused by hand, not measured: the mirror the search dedups
#: on needs the output on a plane of cells, which only an odd width has.
SHRINK = {
    "comparator": [(3, 1, 3), (5, 1, 3), (3, 1, 5), (5, 1, 5), (7, 1, 5)],
    "torch": [(5, 1, 5), (7, 1, 3), (7, 1, 5), (9, 1, 5)],
}


def shrink(name):
    """Build the design in each candidate box and report what the machine
    says. A box the design cannot even be spelled in reports its exception."""
    rows = []
    for dims in SHRINK[name]:
        nx, _ny, nz = dims
        try:
            space, parts = DESIGNS[name](nx=nx, nz=nz, z=nz // 2)
            row = check(name, space, parts)
            rows.append({"dims": list(dims), "editable": row["editable"],
                         "legal": row["legal"], "hits": row["hits"],
                         "parts": row["parts"]})
        except Exception as exc:                           # noqa: BLE001
            rows.append({"dims": list(dims), "refused": "%s: %s"
                         % (type(exc).__name__, exc)})
    return rows


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    want = argv[0] if argv else "all"
    if want == "shrink":
        for name in sorted(DESIGNS):
            for row in shrink(name):
                print(name, json.dumps(row, sort_keys=True))
        return 0
    for name, fn in sorted(DESIGNS.items()):
        if want not in ("all", name):
            continue
        space, parts = fn()
        row = check(name, space, parts)
        print(json.dumps({k: row[k] for k in ("design", "dims", "editable",
                                              "legal", "hits", "parts")},
                         sort_keys=True))
        for t in row["trace"]:
            print("   ", json.dumps(t, sort_keys=True))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(errors="backslashreplace")
    raise SystemExit(main())
