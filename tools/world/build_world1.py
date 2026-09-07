#!/usr/bin/env python3
"""tools/world/build_world1.py -- WORLD-1's one-off: PLACE-1's stage
plus three lever feeders into a void synthetic world, and the worldprobe spec
that drives all 8 input vectors.

Non-canonical, this lane only.

WHY NOT `synthworld.build_world` VERBATIM. `tools/world/synthworld.py`
is the shipped joint and this file follows it line for line -- except one:
`build_world` spells `worldgen.build_region_files(placements, {}, version)`, so a
world it writes can hold no block entities, and PLACE-1's stage is defined by a
barrel holding exactly 494 stack-64 items (the level-5 constant behind the
compare comparator), plus one such barrel behind each of the three feeders. So
the four worldgen lines are spelled here with the block-entity map filled in.
Nothing under `tools/` is changed; `synthworld` is imported for its sys.path
setup and its settle constants so there is still one description of the idiom.

WHY A WARM-UP SWEEP. A world written straight into region files is loaded with
whatever block states the writer put in the palette and NO redstone update ever
runs over it: `setblock` updates only its own neighbours. Every comparator here
is loaded `powered=false` with no block entity, i.e. output signal 0, and every
wire `power=0` -- which is a lie for c1..c3, whose backs are redstone blocks. A
gate only recomputes when a neighbour's state changes, so a gate whose stale
state happens to equal the answer for the vector under test is never woken, and
a stale gate upstream of a live one poisons the reading. The cure is to drive
the levers through all 8 vectors ONCE and throw the readings away: by the vector
where input a first rises, c1 changes, and the cascade from c1 reaches and wakes
every gate in the stage. The recorded sweep then starts from a world that is
live everywhere. No machine answer is written into the world; the warm-up is
lever flips only, and its readings are kept in the result under `warm_*` names
so the discarded pass is auditable rather than invisible.

Usage:
  build_world1.py --out <dir that must not exist> --rcon-port N [--base x,y,z]
"""

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for _p in (str(HERE), str(ROOT / "tools" / "checks")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import synthworld as SW                                     # noqa: E402
import worldgen                                             # noqa: E402  (via SW's sys.path)
import bench_sweep_feed as BSF                              # noqa: E402

bridge = worldgen.bridge

#: The 8 input vectors, in the order they are driven. Consecutive vectors
#: differ, so every regime begins with at least one lever actually changing.
VECTORS = [(a, b, c) for a in (0, 1) for b in (0, 1) for c in (0, 1)]

#: The seven stage comparators, read for `powered` as a diagnostic.
STAGE_GATES = {"c1": (1, 1, 1), "c2": (2, 1, 1), "c3": (3, 1, 1),
               "c4": (4, 1, 3), "c5": (6, 1, 1), "c6": (6, 1, 3),
               "c7": (5, 1, 4)}
#: The three feeder comparators, same.
FEED_GATES = {"fa": (1, 1, -1), "fcin": (3, 1, -1), "fb": (2, 1, 3)}


def item_list(total, max_count=64, item="minecraft:cobblestone"):
    """`Items` for a container holding `total` stack-64 items.

    1.20.5 replaced `Count: <byte>` with `count: <int>` on an item stack
    (DataVersion 3839 is 1.20.6), so this is the post-component spelling."""
    entries, slot, left = [], 0, int(total)
    while left > 0:
        n = min(max_count, left)
        entries.append({"Slot": (bridge.TAG_BYTE, slot),
                        "id": (bridge.TAG_STRING, item),
                        "count": (bridge.TAG_INT, n)})
        left -= n
        slot += 1
    return entries


def barrel_entity(pos, total):
    x, y, z = pos
    return {"id": (bridge.TAG_STRING, "minecraft:barrel"),
            "x": (bridge.TAG_INT, x), "y": (bridge.TAG_INT, y),
            "z": (bridge.TAG_INT, z),
            "Items": (bridge.TAG_LIST,
                      (bridge.TAG_COMPOUND, item_list(total)))}


def world_of(layout, base):
    """layout (relative frame) -> (placements, block_entities) in world coords."""
    bx, by, bz = base
    placements, entities = {}, {}
    for r in layout["blocks"]:
        pos = (bx + r[0], by + r[1], bz + r[2])
        placements[pos] = BSF.parse(r[3])
    for key, count in layout["barrels"].items():
        rel = tuple(int(v) for v in key.split(","))
        pos = (bx + rel[0], by + rel[1], bz + rel[2])
        if placements[pos][0] != "minecraft:barrel":
            raise SystemExit("%s is %s, not a barrel" % (pos, placements[pos][0]))
        entities[pos] = barrel_entity(pos, count)
    return placements, entities


def build_world(placements, entities, out_dir, name):
    """`synthworld.build_world`, with the block-entity map actually used."""
    out_dir = Path(out_dir)
    if out_dir.exists():
        raise SystemExit("refusing to overwrite %s" % out_dir)
    version = worldgen.DEFAULT_DATA_VERSION
    level_dat = worldgen.build_level_dat(name, version)
    regions = worldgen.build_region_files(placements, entities, version)
    tsv = worldgen.render_blocks_tsv(placements).encode("utf-8")
    world_dir = out_dir / "world"
    (world_dir / "region").mkdir(parents=True)
    (world_dir / "level.dat").write_bytes(level_dat)
    for (rx, rz), data in regions.items():
        (world_dir / "region" / ("r.%d.%d.mca" % (rx, rz))).write_bytes(data)
    (out_dir / "blocks.tsv").write_bytes(tsv)
    return world_dir, sorted(regions), version


def spec_of(layout, bench_rows, base, world_dir, out_dir, template, rcon_port,
            max_gt, settle_gt):
    bx, by, bz = base

    def w(rel):
        return [bx + rel[0], by + rel[1], bz + rel[2]]

    drives = {}
    for name, pos in layout["levers"].items():
        drives["lv_" + name] = {"kind": "lever", "pos": w(pos),
                                "face": "floor", "facing": "north"}

    reads = [
        {"name": "cout5", "pos": w(layout["outputs"]["cout"]), "bit": 0,
         "match": "minecraft:redstone_wire[power=5]"},
        {"name": "cout0", "pos": w(layout["outputs"]["cout"]), "bit": 1,
         "match": "minecraft:redstone_wire[power=0]"},
        {"name": "sum5", "pos": w(layout["outputs"]["sum"]), "bit": 2,
         "match": "minecraft:redstone_wire[power=5]"},
        {"name": "sum0", "pos": w(layout["outputs"]["sum"]), "bit": 3,
         "match": "minecraft:redstone_wire[power=0]"},
    ]
    for gname, pos in list(STAGE_GATES.items()) + list(FEED_GATES.items()):
        reads.append({"name": gname + "_on", "pos": w(pos),
                      "match": "minecraft:comparator[powered=true]"})
    reads.append({"name": "k5_slot7", "kind": "nbt",
                  "pos": w([3, 1, 3]), "path": "Items[7]"})

    by_vector = {(r["a"], r["b"], r["cin"]): r for r in bench_rows}
    regimes = []
    for label, expect_it in (("warm", False), ("v", True)):
        for a, b, c in VECTORS:
            row = by_vector[(a, b, c)]
            # INVERTED drive: lever ON == input bit 0.
            inputs = {"lv_a": int(a == 0), "lv_b": int(b == 0),
                      "lv_cin": int(c == 0)}
            regime = {"name": "%s_a%db%dc%d" % (label, a, b, c),
                      "inputs": inputs, "max_gt": max_gt, "settle_gt": settle_gt}
            if expect_it:
                value = ((1 if row["cout_power"] == 5 else 0)
                         | (2 if row["cout_power"] == 0 else 0)
                         | (4 if row["sum_power"] == 5 else 0)
                         | (8 if row["sum_power"] == 0 else 0))
                final = {"cout5": row["cout_power"] == 5,
                         "cout0": row["cout_power"] == 0,
                         "sum5": row["sum_power"] == 5,
                         "sum0": row["sum_power"] == 0}
                for gname, pos in list(STAGE_GATES.items()) + list(FEED_GATES.items()):
                    final[gname + "_on"] = bool(row["cmp_out"]["%d,%d,%d" % pos] > 0)
                regime["expect"] = {"final_value": value, "final_reads": final}
            regimes.append(regime)

    lo = [min(p[i] for p in [w(r[:3]) for r in layout["blocks"]]) - 1
          for i in range(3)]
    hi = [max(p[i] for p in [w(r[:3]) for r in layout["blocks"]]) + 1
          for i in range(3)]
    return {"name": "world1",
            "world": {"template": str(template), "world_dir": str(world_dir),
                      "bbox": {"min": lo, "max": hi}},
            "server": {"host": "127.0.0.1", "rcon_port": int(rcon_port),
                       "java_xmx": "3G"},
            "drives": drives, "reads": reads, "regimes": regimes,
            "limits": {"max_rcon": 60000},
            "out_dir": str(out_dir)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--rcon-port", type=int, required=True)
    ap.add_argument("--base", default="100,64,100")
    ap.add_argument("--template",
                    default="runtime/carpet-work")
    ap.add_argument("--max-gt", type=int, default=40)
    ap.add_argument("--settle-gt", type=int, default=10)
    ap.add_argument("--layout", default=str(HERE / "layout_world1.json"))
    args = ap.parse_args(argv)

    layout = json.loads(Path(args.layout).read_text(encoding="utf-8"))
    base = tuple(int(v) for v in args.base.split(","))
    placements, entities = world_of(layout, base)
    world_dir, regions, version = build_world(placements, entities,
                                              Path(args.out), "world1")

    bench_rows = BSF.sweep(layout)
    for r in bench_rows:
        r["cmp_out"] = {}
    # re-derive the per-gate signals the spec needs, from the same Bench build
    for r in bench_rows:
        lever_on = r["levers_on"]
        b = BSF.build(layout, lever_on)
        b.dc_solve()
        for _n, pos in list(STAGE_GATES.items()) + list(FEED_GATES.items()):
            r["cmp_out"]["%d,%d,%d" % pos] = b.cmp_out.get(tuple(pos), 0)

    spec = spec_of(layout, bench_rows, base, world_dir, HERE, args.template,
                   args.rcon_port, args.max_gt, args.settle_gt)
    spec_path = HERE / "world1.spec.json"
    spec_path.write_bytes((json.dumps(spec, indent=1) + "\n").encode("utf-8"))
    (HERE / "bench_feed_rows.json").write_bytes(
        (json.dumps(bench_rows, indent=1) + "\n").encode("utf-8"))

    print("world %s blocks %d block_entities %d regions %s dv %d"
          % (world_dir, len(placements), len(entities), regions, version))
    print("bbox %s %s" % (spec["world"]["bbox"]["min"], spec["world"]["bbox"]["max"]))
    print("drives %d reads %d regimes %d (8 warm + 8 recorded) rcon %d"
          % (len(spec["drives"]), len(spec["reads"]), len(spec["regimes"]),
             args.rcon_port))
    for reg in spec["regimes"]:
        if "expect" in reg:
            print("  %-12s levers %s expect final_value %d"
                  % (reg["name"], reg["inputs"], reg["expect"]["final_value"]))
    print("spec %s" % spec_path)
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    raise SystemExit(main())
