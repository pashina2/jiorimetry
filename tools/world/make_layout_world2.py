#!/usr/bin/env python3
"""tools/world/make_layout_world2.py -- alu_stage_v7 + physical lever
feeders, in the stage's own relative frame.  Non-canonical, this lane only.

Feeder idiom is WORLD-1's (docs/world/world1-record.md section 1):
a comparator in COMPARE mode whose BACK is a barrel and whose SIDE is a
lever-driven wire.  side > back kills it, so lever ON = bit 0, lever OFF = bit 1.
Here the constant is level 3 (247 stack-64 items), not WORLD-1's 5.

Convention (validated by WORLD-1 against a real 1.20.6 server): a comparator or
repeater with facing=D has its BACK at pos+D and its OUTPUT at pos-D.

Two of the eight pins cannot be reached by a gate whose output cell IS the pin
wire, because every horizontal neighbour of the pin is a stage block:
  a1 (4,1,4)  -- boxed in by (3,1,4) (4,1,3) (5,1,4) (4,1,5) and a barrel above
  a2 (8,1,5)  -- (7,1,5) (9,1,5) (8,1,4) taken; the one free neighbour (8,1,6)
                 would make the pin dust connect along z and so weakly power
                 (8,1,4), which is the BACK of stage comparator (7,1,4).
For those two the gate's output cell is the SUPPORT BLOCK under the pin dust,
which the comparator strongly powers at its own output level (the same
mechanism the stage itself already uses at (8,1,4), (5,1,2), (3,1,5), ...),
so the dust above reads exactly 3 or 0.  This costs two substitutions of INERT
stage floor blocks -- see SUBSTITUTIONS below.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SRC = ROOT / "artifacts" / "layouts" / "alu_stage_v7.json"

STONE = "minecraft:smooth_stone"
DUST = "minecraft:redstone_wire"
BARREL = "minecraft:barrel[facing=up,open=false]"
LEVER = "minecraft:lever[face=floor,facing=north,powered=false]"
L3 = 247            # stack-64 items in a 27-slot barrel -> comparator level 3

#: (8,0,7) and (7,0,6) are y=0 floor blocks of the stage that support nothing
#: (the cells above them, (8,1,7) and (7,1,6), are air) and touch no dust.
#: They become the a2 feeder's barrel and side wire.
SUBSTITUTIONS = {(8, 0, 7): BARREL, (7, 0, 6): DUST}

#: New blocks, grouped per feeder.  Each entry: (pos, state).
FEEDERS = {
    # ---- data feeders (compare gate + level-3 barrel + lever-driven side wire)
    "k": [((-1, 1, 2), "minecraft:comparator[facing=west,mode=compare]"),
          ((-1, 0, 2), STONE),
          ((-2, 1, 2), BARREL),
          ((-1, 1, 1), DUST), ((-1, 0, 1), STONE),
          ((-2, 1, 1), STONE), ((-2, 2, 1), LEVER)],
    "b": [((-1, 1, 4), "minecraft:comparator[facing=west,mode=compare]"),
          ((-1, 0, 4), STONE),
          ((-2, 1, 4), BARREL),
          ((-1, 1, 5), DUST), ((-1, 0, 5), STONE),
          ((-2, 1, 5), STONE), ((-2, 2, 5), LEVER)],
    # a1: output cell is (4,0,4), the support under the pin dust (4,1,4).
    # The gate's -x side (3,0,5) must stay AIR: (3,1,5) directly above it is
    # strongly powered by stage comparator (3,1,4), so a wire there reads the
    # stage, not the lever (measured: 9 with the lever off).  The +x side
    # (5,0,5) is clean -- (5,1,5) is no relay's front -- and the lever escapes
    # to the empty space below by two diagonal-down hops, because every y=1
    # cell above the free y=0 cells here is a stage block.
    "a1": [((4, 0, 5), "minecraft:comparator[facing=south,mode=compare]"),
           ((4, -1, 5), STONE),
           ((4, 0, 6), BARREL),
           ((5, 0, 5), DUST), ((5, -1, 5), STONE),
           ((6, -1, 5), DUST), ((6, -2, 5), STONE),
           ((7, -2, 5), DUST), ((7, -3, 5), STONE),
           ((8, -2, 5), STONE), ((8, -1, 5), LEVER)],
    # a2: output cell is (8,0,5), the support under the pin dust (8,1,5).
    "a2": [((8, 0, 6), "minecraft:comparator[facing=south,mode=compare]"),
           ((8, -1, 6), STONE),
           ((7, -1, 6), STONE),                    # support for the substituted dust
           ((7, 1, 6), STONE), ((7, 2, 6), LEVER)],
    "a3": [((11, 1, 4), "minecraft:comparator[facing=east,mode=compare]"),
           ((11, 0, 4), STONE),
           ((12, 1, 4), BARREL),
           ((11, 1, 5), DUST), ((11, 0, 5), STONE),
           ((11, 1, 6), STONE), ((11, 2, 6), LEVER)],
    # ---- control feeders: lever base solid beside the pin wire, lever on top
    "p1": [((0, 1, -1), STONE), ((0, 2, -1), LEVER)],
    "p2": [((-1, 1, 8), STONE), ((-1, 2, 8), LEVER)],
    "wn": [((3, 1, 10), STONE), ((3, 2, 10), LEVER)],
}

NEW_BARRELS = {(-2, 1, 2): L3, (-2, 1, 4): L3, (4, 0, 6): L3,
               (8, 0, 7): L3, (12, 1, 4): L3}

LEVERS = {"k": (-2, 2, 1), "b": (-2, 2, 5), "a1": (8, -1, 5), "a2": (7, 2, 6),
          "a3": (11, 2, 6), "p1": (0, 2, -1), "p2": (-1, 2, 8),
          "wn": (3, 2, 10)}

#: which lever kills which pin, and what kind of pin it is
DATA_LEVERS = {"a": ["a1", "a2", "a3"], "b": ["b"], "k": ["k"]}
CTRL_LEVERS = {"P": ["p1", "p2"], "Wn": ["wn"]}

#: the f readout: F (8,1,2) is a comparator; its output cell is (9,1,2), which
#: is otherwise air and also the output cell of the always-0 dummy (9,1,3).
READOUT = [((9, 1, 2), DUST), ((9, 0, 2), STONE)]


def build_layout():
    stage = json.loads(SRC.read_text(encoding="utf-8"))
    blocks = {tuple(r[:3]): r[3] for r in stage["blocks"]}
    for pos, state in SUBSTITUTIONS.items():
        if pos not in blocks:
            raise SystemExit("substitution target %s is not a stage block" % (pos,))
        if blocks[pos] != STONE:
            raise SystemExit("substitution target %s is %s" % (pos, blocks[pos]))
        blocks[pos] = state
    added = list(READOUT)
    for name in FEEDERS:
        added += FEEDERS[name]
    for pos, state in added:
        if pos in blocks:
            raise SystemExit("feeder cell %s collides with %s" % (pos, blocks[pos]))
        blocks[pos] = state
    barrels = dict(stage["barrels"])
    for pos, n in NEW_BARRELS.items():
        barrels["%d,%d,%d" % pos] = n
    for key in barrels:
        pos = tuple(int(v) for v in key.split(","))
        if not blocks[pos].startswith("minecraft:barrel"):
            raise SystemExit("%s is not a barrel" % (pos,))
    out = {"blocks": [[p[0], p[1], p[2], s] for p, s in sorted(blocks.items())],
           "barrels": barrels,
           "pins": stage["pins"], "reads": stage["reads"],
           "levers": {k: list(v) for k, v in LEVERS.items()},
           "readout": {"r": stage["reads"]["r"], "f_wire": [9, 1, 2],
                       "f_cmp": stage["reads"]["f"]},
           "data_levers": DATA_LEVERS, "ctrl_levers": CTRL_LEVERS,
           "substitutions": {"%d,%d,%d" % p: s for p, s in SUBSTITUTIONS.items()},
           "convention": ("data lever ON = bit 0 (side 15 kills the level-3 "
                          "compare gate), OFF = bit 1; control lever ON = 15")}
    return out


if __name__ == "__main__":
    lay = build_layout()
    p = HERE / "layout_world2.json"
    p.write_bytes((json.dumps(lay, indent=1) + "\n").encode("utf-8"))
    print("blocks %d barrels %d levers %d -> %s"
          % (len(lay["blocks"]), len(lay["barrels"]), len(lay["levers"]), p))
