#!/usr/bin/env python3
"""tools/world/build_world2.py -- WORLD-2's one-off: the ALU stage
alu_stage_v7 plus eight lever feeders into a void synthetic 1.20.6 world, and
the worldprobe spec that drives all 32 ALU rows.

This is tools/world/build_world1.py with the layout, the constants
and the regime list changed; the deviation it documents is the same one:
synthworld.build_world spells worldgen.build_region_files(placements, {},
version), so a world it writes can hold NO block entities, and this artifact is
defined by eleven barrels whose item counts ARE the circuit's constants. The
four worldgen lines are therefore spelled here with the block-entity map filled
in. Nothing under tools/ is changed; worldprobe.py is used unmodified.

WHY A WARM-UP SWEEP (WORLD-1 section 4, unchanged): a world written straight
into region files loads with whatever states the writer put in the palette and
no redstone update ever runs over it -- every comparator loads powered=false
with output 0, every wire power=0, which is a lie wherever a back is a redstone
block or a barrel. A gate recomputes only when a neighbour's state changes, so
a stale gate that happens to match the row under test is never woken and
poisons everything downstream. So the 32 rows are driven twice: warm_*,
recorded but not compared, then v_*, compared against the Bench.

Usage: build_world2.py --out <dir that must not exist> --rcon-port N
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

import synthworld as SW                                     # noqa: E402,F401
import worldgen                                             # noqa: E402
import bench_sweep_feed2 as BSF                             # noqa: E402

bridge = worldgen.bridge

#: the barrel whose Items are read back through the probe, and the slot that
#: shows the remainder of 247 = 3*64 + 55
NBT_BARREL = (12, 1, 4)
NBT_PATH = "Items[3]"

STAGE_SRC = ROOT / "artifacts" / "layouts" / "alu_stage_v7.json"


def item_list(total, max_count=64, item="minecraft:cobblestone"):
    """Items for a container holding `total` stack-64 items (1.20.5+ spelling:
    count as an int, not Count as a byte)."""
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


def gate_names(layout):
    """{read name: relative pos} for every comparator in the layout.

    A stage comparator is named c<x>_<y>_<z>, a feeder gate g<x>_<y>_<z>, so the
    23 stage gates the order asks about can be counted off the read names."""
    src = json.loads(STAGE_SRC.read_text(encoding="utf-8"))
    src_cmp = {tuple(b[:3]) for b in src["blocks"]
               if b[3].startswith("minecraft:comparator")}
    out = {}
    for r in sorted(layout["blocks"]):
        if not r[3].startswith("minecraft:comparator"):
            continue
        pos = (r[0], r[1], r[2])
        tag = "c" if pos in src_cmp else "g"
        out["%s%d_%d_%d" % (tag, pos[0], pos[1], pos[2])] = list(pos)
    return out, len(src_cmp)


def spec_of(layout, rows, base, world_dir, out_dir, template, rcon_port,
            max_gt, settle_gt, max_rcon):
    bx, by, bz = base

    def w(rel):
        return [bx + rel[0], by + rel[1], bz + rel[2]]

    drives = {}
    for name, pos in layout["levers"].items():
        drives["lv_" + name] = {"kind": "lever", "pos": w(pos),
                                "face": "floor", "facing": "north"}

    r_pos, f_pos = layout["readout"]["r"], layout["readout"]["f_wire"]
    reads = [
        {"name": "r3", "pos": w(r_pos), "bit": 0,
         "match": "minecraft:redstone_wire[power=3]"},
        {"name": "r0", "pos": w(r_pos), "bit": 1,
         "match": "minecraft:redstone_wire[power=0]"},
        {"name": "f3", "pos": w(f_pos), "bit": 2,
         "match": "minecraft:redstone_wire[power=3]"},
        {"name": "f0", "pos": w(f_pos), "bit": 3,
         "match": "minecraft:redstone_wire[power=0]"},
    ]
    gates, n_stage = gate_names(layout)
    for gname, pos in gates.items():
        reads.append({"name": gname + "_on", "pos": w(pos),
                      "match": "minecraft:comparator[powered=true]"})
    reads.append({"name": "barrel_slot3", "kind": "nbt",
                  "pos": w(list(NBT_BARREL)), "path": NBT_PATH})

    regimes = []
    for label, compare in (("warm", False), ("v", True)):
        for row in rows:
            inputs = {"lv_" + nm: int(v) for nm, v in row["levers_on"].items()}
            name = "%s_%s_a%db%dk%d" % (label, row["op"], row["a"], row["b"],
                                        row["k"])
            regime = {"name": name, "inputs": inputs,
                      "max_gt": max_gt, "settle_gt": settle_gt}
            if compare:
                value = ((1 if row["r"] == 3 else 0)
                         | (2 if row["r"] == 0 else 0)
                         | (4 if row["f_wire"] == 3 else 0)
                         | (8 if row["f_wire"] == 0 else 0))
                final = {"r3": row["r"] == 3, "r0": row["r"] == 0,
                         "f3": row["f_wire"] == 3, "f0": row["f_wire"] == 0}
                for gname, pos in gates.items():
                    key = "%d,%d,%d" % tuple(pos)
                    final[gname + "_on"] = bool(row["cmp_out"].get(key, 0) > 0)
                regime["expect"] = {"final_value": value, "final_reads": final}
            regimes.append(regime)

    cells = [w(r[:3]) for r in layout["blocks"]]
    lo = [min(p[i] for p in cells) - 1 for i in range(3)]
    hi = [max(p[i] for p in cells) + 1 for i in range(3)]
    spec = {"name": "world2",
            "world": {"template": str(template), "world_dir": str(world_dir),
                      "bbox": {"min": lo, "max": hi}},
            "server": {"host": "127.0.0.1", "rcon_port": int(rcon_port),
                       "java_xmx": "3G"},
            "drives": drives, "reads": reads, "regimes": regimes,
            "limits": {"max_rcon": int(max_rcon)},
            "out_dir": str(out_dir)}
    return spec, n_stage


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--rcon-port", type=int, default=25598)
    ap.add_argument("--base", default="100,64,100")
    ap.add_argument("--template",
                    default="runtime/carpet-work")
    ap.add_argument("--max-gt", type=int, default=40)
    ap.add_argument("--settle-gt", type=int, default=10)
    ap.add_argument("--max-rcon", type=int, default=200000)
    ap.add_argument("--layout", default=str(HERE / "layout_world2.json"))
    args = ap.parse_args(argv)

    layout = json.loads(Path(args.layout).read_text(encoding="utf-8"))
    base = tuple(int(v) for v in args.base.split(","))
    placements, entities = world_of(layout, base)

    rows = BSF.sweep(layout)
    n_ok = sum(1 for r in rows if r["ok"])
    if n_ok != 32:
        raise SystemExit("bench sweep is %d/32, refusing to build" % n_ok)

    world_dir, regions, version = build_world(placements, entities,
                                              Path(args.out), "world2")
    spec, n_stage = spec_of(layout, rows, base, world_dir, HERE, args.template,
                            args.rcon_port, args.max_gt, args.settle_gt,
                            args.max_rcon)
    spec_path = HERE / "world2.spec.json"
    spec_path.write_bytes((json.dumps(spec, indent=1) + "\n").encode("utf-8"))
    (HERE / "bench_feed2_rows.json").write_bytes(
        (json.dumps(rows, indent=1) + "\n").encode("utf-8"))

    n_gate_reads = len([r for r in spec["reads"] if r["name"].startswith("g")])
    print("world %s blocks %d block_entities %d regions %s dv %d"
          % (world_dir, len(placements), len(entities), regions, version))
    print("bbox %s %s" % (spec["world"]["bbox"]["min"], spec["world"]["bbox"]["max"]))
    print("bench sweep %d/32; stage comparators %d, feeder gates %d"
          % (n_ok, n_stage, n_gate_reads))
    print("drives %d reads %d regimes %d (32 warm + 32 recorded) rcon %d"
          % (len(spec["drives"]), len(spec["reads"]), len(spec["regimes"]),
             args.rcon_port))
    est = len(spec["regimes"]) * (args.max_gt + 1) * len(
        [r for r in spec["reads"] if r.get("kind", "state") == "state"])
    print("state-read roundtrips at most %d of max_rcon %d" % (est, args.max_rcon))
    for reg in spec["regimes"]:
        if "expect" in reg:
            print("  %-22s expect final_value %d"
                  % (reg["name"], reg["expect"]["final_value"]))
    print("spec %s" % spec_path)
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    raise SystemExit(main())
