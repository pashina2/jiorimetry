#!/usr/bin/env python3
"""docs/world/make_layout_world4.py -- the six artifacts WORLD-4
asks about, each with the physical lever feeders that replace the Bench PINS.

Six artifacts in one void world:
  the five solvable PLACER-0 problems (artifacts/placer0/problems.json
  + sol_*.json; p3 is unsatisfiable and is not here) placed as
  fixed cells + solution cells, and
  artifacts/layouts/alu_slice_v9.json tiled twice by
  alu_check_slices.tiled(lay, 2) -- 584 cells, pitch 12.

Feeder idiom is WORLD-1's and WORLD-2's (docs/world/world2-record.md
section 1), unchanged:
  DATA pin (0/3): a comparator in COMPARE mode whose BACK is a barrel holding
  247 stack-64 items (level 3) and whose SIDE is a lever-driven wire.  A side
  driven to 15 kills a level-3 back, so LEVER ON = bit 0, LEVER OFF = bit 1.
  CONTROL pin (0/15): a solid block beside the pin wire with a face=floor lever
  on top.  LEVER ON = 15.
Convention (validated by WORLD-1 against a real 1.20.6 server): a comparator or
repeater with facing=D has its BACK at pos+D and its OUTPUT at pos-D.

Nothing under tools/ and none of the artifacts under test is edited.  Every
feeder cell is asserted to be empty in the artifact and, for the slice, its
neighbours were enumerated before the cells were chosen (see record.md 1).
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ART = HERE.parents[1] / "artifacts"   # export layout: artifacts/placer0, artifacts/layouts
sys.path.insert(0, str(HERE.parents[0] / "checks"))
import alu_check_slices as CS                                # noqa: E402
import alu_check2 as A2                                      # noqa: E402

PLACER0 = ART / "placer0"
SLICE = ART / "layouts"

STONE = "minecraft:smooth_stone"
DUST = "minecraft:redstone_wire"
BARREL = "minecraft:barrel[facing=up,open=false]"
LEVER = "minecraft:lever[face=floor,facing=north,powered=false]"
L3 = 247            # stack-64 items in a 27-slot barrel -> comparator level 3


def cmp_(facing):
    return "minecraft:comparator[facing=%s,mode=compare]" % facing


def data_feeder(gate, facing, barrel, side, side_support, base, lever,
                gate_support):
    """The seven cells of a data feeder, as (pos, state) pairs."""
    return [(gate, cmp_(facing)), (gate_support, STONE), (barrel, BARREL),
            (side, DUST), (side_support, STONE), (base, STONE), (lever, LEVER)]


def ctrl_feeder(base, lever):
    return [(base, STONE), (lever, LEVER)]


# --------------------------------------------------------------- the five p*

#: per problem: feeder cells, the barrels they add, lever positions, and which
#: lever drives which pin.  Cell choices are justified in record.md section 1.
P_FEEDERS = {
    "p1_sub2side": {
        "cells": (data_feeder((-1, 1, 2), "west", (-2, 1, 2), (-1, 1, 1),
                              (-1, 0, 1), (-2, 1, 1), (-2, 2, 1), (-1, 0, 2))
                  + ctrl_feeder((6, 1, 2), (6, 2, 2))),
        "barrels": {(-2, 1, 2): L3},
        "levers": {"p1_a": (-2, 2, 1), "p1_wn": (6, 2, 2)},
        "data": {"a": ["p1_a"]}, "ctrl": {"Wn": ["p1_wn"]},
    },
    "p2_copy_into_side": {
        "cells": data_feeder((-1, 1, 0), "west", (-2, 1, 0), (-1, 1, 1),
                             (-1, 0, 1), (-2, 1, 1), (-2, 2, 1), (-1, 0, 0)),
        "barrels": {(-2, 1, 0): L3},
        "levers": {"p2_a": (-2, 2, 1)},
        "data": {"a": ["p2_a"]}, "ctrl": {},
    },
    "p4_throughline": {
        "cells": ctrl_feeder((-1, 1, 1), (-1, 2, 1)),
        "barrels": {},
        "levers": {"p4_t": (-1, 2, 1)},
        "data": {}, "ctrl": {"T": ["p4_t"]},
    },
    "p5_max_merge": {
        "cells": (data_feeder((-1, 1, 0), "west", (-2, 1, 0), (-1, 1, 1),
                              (-1, 0, 1), (-2, 1, 1), (-2, 2, 1), (-1, 0, 0))
                  + data_feeder((-1, 1, 4), "west", (-2, 1, 4), (-1, 1, 5),
                                (-1, 0, 5), (-2, 1, 5), (-2, 2, 5), (-1, 0, 4))),
        "barrels": {(-2, 1, 0): L3, (-2, 1, 4): L3},
        "levers": {"p5_a": (-2, 2, 1), "p5_w3": (-2, 2, 5)},
        "data": {"a": ["p5_a"], "W3": ["p5_w3"]}, "ctrl": {},
    },
    "p6_vertical_cap": {
        "cells": (data_feeder((2, 1, -1), "north", (2, 1, -2), (3, 1, -1),
                              (3, 0, -1), (4, 1, -1), (4, 2, -1), (2, 0, -1))
                  + ctrl_feeder((-1, 1, 2), (-1, 2, 2))),
        "barrels": {(2, 1, -2): L3},
        "levers": {"p6_d": (4, 2, -1), "p6_n": (-1, 2, 2)},
        "data": {"d": ["p6_d"]}, "ctrl": {"N": ["p6_n"]},
    },
}

#: z offset of each artifact's origin inside the world frame.  Every gap
#: between two artifacts' occupied z ranges is at least 10 cells.
Z_ORIGIN = {"p1_sub2side": 0, "p2_copy_into_side": 20, "p4_throughline": 40,
            "p5_max_merge": 60, "p6_vertical_cap": 80, "slice_v9_n2": 100}


def placer0_artifact(name):
    probs = {p["name"]: p for p in json.loads(
        (PLACER0 / "problems.json").read_text(encoding="utf-8"))}
    prob = probs[name]
    sol = json.loads((PLACER0 / ("sol_%s.json" % name)).read_text(encoding="utf-8"))
    blocks = {tuple(r[:3]): r[3] for r in prob["fixed"]}
    for r in sol["blocks"]:
        p = tuple(r[:3])
        if p in blocks:
            raise SystemExit("%s: solution cell %s overlaps a fixed cell" % (name, p))
        blocks[p] = r[3]
    barrels = dict(prob.get("barrels") or {})
    barrels.update(sol.get("barrels") or {})
    fd = P_FEEDERS[name]
    for pos, state in fd["cells"]:
        if pos in blocks:
            raise SystemExit("%s: feeder cell %s collides with %s"
                             % (name, pos, blocks[pos]))
        blocks[pos] = state
    for pos, n in fd["barrels"].items():
        barrels["%d,%d,%d" % pos] = n
    outputs = {}
    for o in prob["outputs"]:
        outputs[o["name"]] = {
            "cell": list(o["cell"]), "expect": o["expect"],
            "levels": [0, 15] if "15" in o["expect"] else [0, 3]}
    return {"kind": "placer0", "problem": name,
            "blocks": [[p[0], p[1], p[2], s] for p, s in sorted(blocks.items())],
            "barrels": barrels,
            "levers": {k: list(v) for k, v in fd["levers"].items()},
            "data_levers": fd["data"], "ctrl_levers": fd["ctrl"],
            "pins": {k: {"cell": list(v["cell"]), "levels": list(v["levels"])}
                     for k, v in prob["pins"].items()},
            "outputs": outputs,
            "origin": [0, 0, Z_ORIGIN[name]]}


# --------------------------------------------------------------- the slice

SLICE_FEEDERS = (
    ctrl_feeder((-1, 2, 0), (-1, 3, 0))                       # P   entry (0,2,0)
    + ctrl_feeder((-1, 3, 12), (-1, 4, 12))                   # Wn  entry (0,3,12)
    + data_feeder((-1, 2, 2), "west", (-2, 2, 2), (-1, 2, 3),
                  (-1, 1, 3), (-2, 2, 3), (-2, 3, 3), (-1, 1, 2))      # k
    + data_feeder((-1, 3, 6), "west", (-2, 3, 6), (-1, 3, 7),
                  (-1, 2, 7), (-2, 3, 7), (-2, 4, 7), (-1, 2, 6))      # b0
    + data_feeder((11, 3, 6), "west", (10, 3, 6), (11, 3, 7),
                  (11, 2, 7), (10, 3, 7), (10, 4, 7), (11, 2, 6))      # b1
    + data_feeder((10, 1, 14), "south", (10, 1, 15), (11, 1, 14),
                  (11, 0, 14), (12, 1, 14), (12, 2, 14), (10, 0, 14))  # a0
    + data_feeder((22, 1, 14), "south", (22, 1, 15), (23, 1, 14),
                  (23, 0, 14), (24, 1, 14), (24, 2, 14), (22, 0, 14))  # a1
)
SLICE_BARRELS = {(-2, 2, 2): L3, (-2, 3, 6): L3, (10, 3, 6): L3,
                 (10, 1, 15): L3, (22, 1, 15): L3}
SLICE_LEVERS = {"s_p": (-1, 3, 0), "s_wn": (-1, 4, 12), "s_k": (-2, 3, 3),
                "s_b0": (-2, 4, 7), "s_b1": (10, 4, 7), "s_a0": (12, 2, 14),
                "s_a1": (24, 2, 14)}
#: the f comparator of slice 1 is (23,2,2); its output cell (24,2,2) is air, so
#: a wire (with its support) is added there to read f as a wire power.
SLICE_READOUT = [((24, 2, 2), DUST), ((24, 1, 2), STONE)]


def slice_artifact():
    lay = json.loads((SLICE / "alu_slice_v9.json").read_text(encoding="utf-8"))
    T = CS.tiled(lay, 2)
    S = lay["slice"]
    PX = S["pitch"]
    blocks = {tuple(r[:3]): r[3] for r in T["blocks"]}
    n_art = len(blocks)
    barrels = dict(T["barrels"])
    for pos, state in list(SLICE_FEEDERS) + SLICE_READOUT:
        if pos in blocks:
            raise SystemExit("slice: feeder cell %s collides with %s"
                             % (pos, blocks[pos]))
        blocks[pos] = state
    for pos, n in SLICE_BARRELS.items():
        barrels["%d,%d,%d" % pos] = n
    ports = S["ports"]
    reads = {
        "r0": {"cell": list(ports["r"]), "levels": [0, 3]},
        "r1": {"cell": [ports["r"][0] + PX, ports["r"][1], ports["r"][2]],
               "levels": [0, 3]},
        "f": {"cell": [24, 2, 2], "levels": [0, 3]},
        "thrP": {"cell": [PX, 2, 0], "levels": [0, 15]},
        "thrWn": {"cell": [PX, 3, 12], "levels": [0, 15]},
        "carry": {"cell": [PX, 2, 2], "levels": [0, 3]},
    }
    return {"kind": "slice", "n": 2, "pitch": PX,
            "blocks": [[p[0], p[1], p[2], s] for p, s in sorted(blocks.items())],
            "barrels": barrels,
            "levers": {k: list(v) for k, v in SLICE_LEVERS.items()},
            "data_levers": {"k": ["s_k"], "a0": ["s_a0"], "a1": ["s_a1"],
                            "b0": ["s_b0"], "b1": ["s_b1"]},
            "ctrl_levers": {"P": ["s_p"], "Wn": ["s_wn"]},
            "pins": {"P": {"cell": list(S["through"]["P"][0]), "levels": [0, 15]},
                     "Wn": {"cell": list(S["through"]["Wn"][0]), "levels": [0, 15]},
                     "k": {"cell": list(ports["k"]), "levels": [0, 3]},
                     "a0": {"cell": list(ports["a"]), "levels": [0, 3]},
                     "a1": {"cell": [ports["a"][0] + PX, ports["a"][1],
                                     ports["a"][2]], "levels": [0, 3]},
                     "b0": {"cell": list(ports["b"]), "levels": [0, 3]},
                     "b1": {"cell": [ports["b"][0] + PX, ports["b"][1],
                                     ports["b"][2]], "levels": [0, 3]}},
            "reads": reads, "f_cmp": [23, 2, 2],
            "artifact_cells": n_art,
            "origin": [0, 0, Z_ORIGIN["slice_v9_n2"]]}


def build():
    arts = {}
    for name in ("p1_sub2side", "p2_copy_into_side", "p4_throughline",
                 "p5_max_merge", "p6_vertical_cap"):
        arts[name] = placer0_artifact(name)
    arts["slice_v9_n2"] = slice_artifact()
    for name, art in arts.items():
        art["gates"] = {}
        for r in art["blocks"]:
            if r[3].startswith("minecraft:comparator"):
                art["gates"]["c%d_%d_%d" % (r[0], r[1], r[2])] = [r[0], r[1], r[2]]
            elif r[3].startswith("minecraft:repeater"):
                art["gates"]["d%d_%d_%d" % (r[0], r[1], r[2])] = [r[0], r[1], r[2]]
        lint = A2.lint({"blocks": art["blocks"], "barrels": art["barrels"]})
        art["lint"] = {"L1": [w for w in lint if w[0].startswith("L1")],
                       "L2": [w for w in lint if w[0].startswith("L2")]}
    return {"artifacts": arts,
            "convention": ("data lever ON = bit 0 (side 15 kills the level-3 "
                           "compare gate), OFF = bit 1; control lever ON = 15")}


if __name__ == "__main__":
    lay = build()
    for name, art in lay["artifacts"].items():
        print("%-18s cells %4d barrels %d levers %d comparators %d L1 %d L2 %d"
              % (name, len(art["blocks"]), len(art["barrels"]),
                 len(art["levers"]),
                 len([k for k in art["gates"] if k.startswith("c")]),
                 len(art["lint"]["L1"]), len(art["lint"]["L2"])))
        for w in art["lint"]["L1"] + art["lint"]["L2"]:
            print("   ", w)
    p = HERE / "layout_world4.json"
    p.write_bytes((json.dumps(lay, indent=1) + "\n").encode("utf-8"))
    print("wrote %s" % p)
