#!/usr/bin/env python3
"""Emit layout_world1.json = PLACE-1's 35-block stage + three physical lever
feeders, in the stage's own relative frame. LF bytes only."""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # export repo root
src = json.loads((ROOT / "artifacts/layouts/layout_place1.json").read_text(encoding="utf-8"))

CMP = "minecraft:comparator[facing=%s,mode=compare]"
BARREL = "minecraft:barrel[facing=up,open=false]"
SOLID = "minecraft:smooth_stone"
WIRE = "minecraft:redstone_wire"
LEVER = "minecraft:lever[face=floor,facing=north,powered=false]"

# one feeder = gate + its support, the level-5 barrel behind it, the side wire
# + its support, the lever base the wire reads, and the lever on top of it.
FEEDERS = {
    # name: (gate pos, gate facing, barrel pos, side wire pos, base pos, lever pos)
    "a":   ((1, 1, -1), "north", (1, 1, -2), (0, 1, -1), (0, 1, -2), (0, 2, -2)),
    "cin": ((3, 1, -1), "north", (3, 1, -2), (4, 1, -1), (4, 1, -2), (4, 2, -2)),
    "b":   ((2, 1, 3),  "south", (2, 1, 4),  (1, 1, 3),  (0, 1, 3),  (0, 2, 3)),
}

blocks = [list(r) for r in src["blocks"]]
barrels = dict(src["barrels"])
levers = {}
for name, (gate, facing, barrel, wire, base, lever) in FEEDERS.items():
    blocks.append(list(gate) + [CMP % facing])
    blocks.append([gate[0], 0, gate[2], SOLID])
    blocks.append(list(barrel) + [BARREL])
    barrels["%d,%d,%d" % barrel] = 494
    blocks.append(list(wire) + [WIRE])
    blocks.append([wire[0], 0, wire[2], SOLID])
    blocks.append(list(base) + [SOLID])
    blocks.append(list(lever) + [LEVER])
    levers[name] = list(lever)

seen = {}
for r in blocks:
    k = tuple(r[:3])
    if k in seen:
        raise SystemExit("collision at %s: %s vs %s" % (k, seen[k], r[3]))
    seen[k] = r[3]

MUST_AIR = [(0,1,0),(0,1,2),(2,1,0),(1,1,2),(3,1,2),(4,1,0),(5,1,0),(5,1,2),
            (7,1,1),(7,1,3),(5,1,5),(4,1,5),(7,1,2),(7,1,4),(6,1,5),(2,1,-1)]
bad = [p for p in MUST_AIR if p in seen]
if bad:
    raise SystemExit("must-stay-air occupied: %s" % (bad,))

out = {"blocks": blocks, "barrels": barrels, "levers": levers,
       "inputs": src["inputs"], "outputs": src["outputs"],
       "convention": "lever OFF (powered=false) = input bit 1; lever ON = bit 0"}
p = ROOT / "artifacts/layouts/layout_world1.json"
p.write_bytes((json.dumps(out, indent=1) + "\n").encode("utf-8"))
print("blocks %d barrels %d levers %s -> %s" % (len(blocks), len(barrels), levers, p))
