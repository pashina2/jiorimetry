#!/usr/bin/env python3
"""docs/world/build_world4.py -- WORLD-4's one-off: the five
solvable PLACER-0 solutions and two abutting slices of alu_slice_v9, each with
its lever feeders, into ONE void synthetic 1.20.6 world, plus the worldprobe
specs that drive them.

This is docs/world/build_world2.py with the layout, the constants
and the regime list changed; the deviation it documents is the same one:
synthworld.build_world spells worldgen.build_region_files(placements, {},
version), so a world it writes can hold NO block entities, and these artifacts
are defined by barrels whose item counts ARE their constants.  The four
worldgen lines are therefore spelled here with the block-entity map filled in.
Nothing under tools/ is changed; worldprobe.py is used unmodified.

WHY A WARM-UP SWEEP (WORLD-1 section 4, WORLD-2 section 4, unchanged): a world
written straight into region files loads with whatever states the writer put in
the palette and no redstone update ever runs over it -- every comparator loads
powered=false with output 0, every wire power=0, which is a lie wherever a back
is a barrel.  A gate recomputes only when a neighbour's state changes, so a
stale gate that happens to match the row under test is never woken and poisons
everything downstream.  So every row is driven twice: warm_*, recorded but not
compared, then v_*, compared against the Bench.

WHY MORE THAN ONE SPEC.  `run_regime` steps to `max_gt` unconditionally, so a
regime costs (max_gt+1) x (state reads) rcon roundtrips.  Part B reads 117
points (12 levels + 105 comparators), i.e. ~4,900 roundtrips per regime, and
256 regimes would need ~1.25 M -- past the 600,000 ceiling the order sets on
`limits.max_rcon`.  Part B is therefore cut into `--b-chunks` runs, each a
self-contained world load: two wake regimes that flip every lever on and off
(so no lever that happens to be constant inside a chunk is left stale), then
that chunk's warm rows, then the same rows recorded.  Part A is one run.

Usage: build_world4.py --out <dir that must not exist> [--b-chunks 3]
"""

import argparse
import itertools
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for _p in (str(ROOT / "tools" / "m9-worldgen"), str(HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import worldgen                                              # noqa: E402
import bench_sweep_feed4 as BSF                              # noqa: E402

bridge = worldgen.bridge

A_ARTIFACTS = ("p1_sub2side", "p2_copy_into_side", "p4_throughline",
               "p5_max_merge", "p6_vertical_cap")
TAG = {"p1_sub2side": "p1", "p2_copy_into_side": "p2", "p4_throughline": "p4",
       "p5_max_merge": "p5", "p6_vertical_cap": "p6"}

#: the barrel whose Items are read back through the probe, and the slot that
#: shows the remainder of 247 = 3*64 + 55
NBT_BARREL = {"a": ("p1_sub2side", (-2, 1, 2)),
              "b": ("slice_v9_n2", (22, 1, 15))}
NBT_PATH = "Items[3]"


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


def world_pos(base, art, rel):
    o = art["origin"]
    return (base[0] + o[0] + rel[0], base[1] + o[1] + rel[1],
            base[2] + o[2] + rel[2])


def world_of(lay, base):
    placements, entities = {}, {}
    for name, art in lay["artifacts"].items():
        for r in art["blocks"]:
            pos = world_pos(base, art, r[:3])
            if pos in placements:
                raise SystemExit("%s: world cell %s already taken" % (name, pos))
            placements[pos] = BSF.parse(r[3])
        for key, count in art["barrels"].items():
            rel = tuple(int(v) for v in key.split(","))
            pos = world_pos(base, art, rel)
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


# --------------------------------------------------------------- spec pieces

def all_drives(lay, base):
    drives = {}
    for art in lay["artifacts"].values():
        for name, pos in art["levers"].items():
            drives[name] = {"kind": "lever",
                            "pos": list(world_pos(base, art, pos)),
                            "face": "floor", "facing": "north"}
    return drives


def bit_reads(lay, base, art_names, next_bit=0):
    """One `state` read per (output cell, candidate level), each carrying a bit.

    Reading BOTH candidate levels at a cell means a third level shows up as a
    reading (both bits 0) instead of being folded silently into "not 3"."""
    reads, bit = [], next_bit
    for name in art_names:
        art = lay["artifacts"][name]
        points = (art["outputs"] if art["kind"] == "placer0" else art["reads"])
        for oname in sorted(points):
            o = points[oname]
            for lv in o["levels"]:
                reads.append({"name": "%s_%s_%d" % (TAG.get(name, "s"), oname, lv),
                              "pos": list(world_pos(base, art, o["cell"])),
                              "bit": bit,
                              "match": "minecraft:redstone_wire[power=%d]" % lv})
                bit += 1
    return reads, bit


def gate_reads(lay, base, art_names, comparators_only):
    reads = []
    for name in art_names:
        art = lay["artifacts"][name]
        for gname in sorted(art["gates"]):
            if comparators_only and not gname.startswith("c"):
                continue
            block = ("minecraft:comparator[powered=true]" if gname.startswith("c")
                     else "minecraft:repeater[powered=true]")
            reads.append({"name": "%s_%s" % (TAG.get(name, "s"), gname),
                          "pos": list(world_pos(base, art, art["gates"][gname])),
                          "match": block})
    return reads


def expectation(lay, reads, rows_by_key, lever_state):
    """{read name: bool} for every state read, from the Bench rows."""
    final = {}
    for r in reads:
        if r.get("kind") == "nbt":
            continue
        final[r["name"]] = None
    value = 0
    for r in reads:
        if r.get("kind") == "nbt":
            continue
        tag, rest = r["name"].split("_", 1)
        row = rows_by_key[tag]
        if rest.startswith(("c", "d")) and "_" in rest and rest in row["gates"]:
            final[r["name"]] = bool(row["gates"][rest])
            continue
        oname, lv = rest.rsplit("_", 1)
        lv = int(lv)
        got = (row["outputs"][oname]["got"] if row.get("outputs")
               else row["got"][oname])
        on = (got == lv)
        final[r["name"]] = on
        if "bit" in r and on:
            value |= 1 << r["bit"]
    if any(v is None for v in final.values()):
        raise SystemExit("unmatched reads: %s"
                         % [k for k, v in final.items() if v is None][:5])
    return {"final_value": value, "final_reads": final}


def bbox_of(placements):
    lo = [min(p[i] for p in placements) - 1 for i in range(3)]
    hi = [max(p[i] for p in placements) + 1 for i in range(3)]
    return lo, hi


def spec_shell(name, world_dir, template, lo, hi, rcon_port, drives, reads,
               regimes, max_rcon):
    return {"name": name,
            "world": {"template": str(template), "world_dir": str(world_dir),
                      "bbox": {"min": lo, "max": hi}},
            "server": {"host": "127.0.0.1", "rcon_port": int(rcon_port),
                       "java_xmx": "3G"},
            "drives": drives, "reads": reads, "regimes": regimes,
            "limits": {"max_rcon": int(max_rcon)},
            "out_dir": str(HERE)}


def est_rcon(spec, max_gt):
    n_state = len([r for r in spec["reads"] if r.get("kind", "state") == "state"])
    n_nbt = len([r for r in spec["reads"] if r.get("kind") == "nbt"])
    per = ((max_gt + 1) * n_state          # read points
           + 3 * max_gt                    # gametime / tick step / gametime
           + 8 * len(spec["drives"])       # is_block + setblock + 6 updates
           + 2 * n_nbt)
    return per, per * len(spec["regimes"]) + 64


# ------------------------------------------------------------------ part A

def part_a(lay, base, rows, world_dir, template, port, max_gt, settle_gt,
           max_rcon):
    drives = all_drives(lay, base)
    reads, _ = bit_reads(lay, base, A_ARTIFACTS)
    reads += gate_reads(lay, base, A_ARTIFACTS, comparators_only=False)
    art, pos = NBT_BARREL["a"]
    reads.append({"name": "barrel_slot3", "kind": "nbt",
                  "pos": list(world_pos(base, lay["artifacts"][art], pos)),
                  "path": NBT_PATH})

    a_rows = [r for r in rows if r["part"] == "A"]
    by_art = {}
    for r in a_rows:
        by_art.setdefault(r["artifact"], []).append(r)
    default = {name: rs[0] for name, rs in by_art.items()}
    slice_row = [r for r in rows if r["part"] == "B"][0]

    regimes = []
    for name in A_ARTIFACTS:
        for label, compare in (("warm", False), ("v", True)):
            for row in by_art[name]:
                active = dict(default)
                active[name] = row
                inputs = {}
                for other in A_ARTIFACTS:
                    inputs.update({k: int(v)
                                   for k, v in active[other]["levers_on"].items()})
                inputs.update({k: int(v)
                               for k, v in slice_row["levers_on"].items()})
                tail = "".join("%s%d" % (k, v) for k, v in sorted(row["pins"].items()))
                reg = {"name": "%s_%s_%s" % (label, TAG[name], tail),
                       "inputs": inputs, "max_gt": max_gt, "settle_gt": settle_gt}
                if compare:
                    keys = {TAG[o]: active[o] for o in A_ARTIFACTS}
                    reg["expect"] = expectation(lay, reads, keys, inputs)
                regimes.append(reg)
    lo, hi = BBOX
    return spec_shell("world4a", world_dir, template, lo, hi, port, drives,
                      reads, regimes, max_rcon)


# ------------------------------------------------------------------ part B

def part_b(lay, base, rows, world_dir, template, port, max_gt, settle_gt,
           max_rcon, chunks):
    drives = all_drives(lay, base)
    reads, _ = bit_reads(lay, base, ("slice_v9_n2",))
    reads += gate_reads(lay, base, ("slice_v9_n2",), comparators_only=True)
    art, pos = NBT_BARREL["b"]
    reads.append({"name": "barrel_slot3", "kind": "nbt",
                  "pos": list(world_pos(base, lay["artifacts"][art], pos)),
                  "path": NBT_PATH})

    b_rows = [r for r in rows if r["part"] == "B"]
    a_rows = [r for r in rows if r["part"] == "A"]
    a_default = {}
    for r in a_rows:
        if r["artifact"] not in a_default:
            a_default[r["artifact"]] = r
    a_inputs = {}
    for r in a_default.values():
        a_inputs.update({k: int(v) for k, v in r["levers_on"].items()})

    specs = []
    for c in range(chunks):
        mine = [r for i, r in enumerate(b_rows) if i % chunks == c]
        regimes = []
        for wake, on in (("wake_on", 1), ("wake_off", 0)):
            regimes.append({"name": wake,
                            "inputs": {k: on for k in drives},
                            "max_gt": max_gt, "settle_gt": settle_gt})
        for label, compare in (("warm", False), ("v", True)):
            for row in mine:
                inputs = dict(a_inputs)
                inputs.update({k: int(v) for k, v in row["levers_on"].items()})
                reg = {"name": "%s_%s_A%dB%dk%d" % (label, row["mode"], row["A"],
                                                    row["B"], row["k"]),
                       "inputs": inputs, "max_gt": max_gt, "settle_gt": settle_gt}
                if compare:
                    reg["expect"] = expectation(lay, reads, {"s": row}, inputs)
                regimes.append(reg)
        lo, hi = BBOX
        specs.append(spec_shell("world4b%d" % (c + 1), world_dir, template, lo,
                                hi, port, drives, reads, regimes, max_rcon))
    return specs


def main(argv=None):
    global BBOX
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--rcon-port", type=int, default=25598)
    ap.add_argument("--base", default="100,64,100")
    ap.add_argument("--template",
                    default=r"<host-path>/carpet-work")
    ap.add_argument("--max-gt", type=int, default=40)
    ap.add_argument("--settle-gt", type=int, default=10)
    ap.add_argument("--max-rcon", type=int, default=600000)
    ap.add_argument("--b-chunks", type=int, default=3)
    ap.add_argument("--layout", default=str(HERE / "layout_world4.json"))
    ap.add_argument("--rows", default=str(HERE / "bench_feed4_rows.json"))
    args = ap.parse_args(argv)

    lay = json.loads(Path(args.layout).read_text(encoding="utf-8"))
    rows = json.loads(Path(args.rows).read_text(encoding="utf-8"))
    n_a = sum(1 for r in rows if r["part"] == "A" and r["ok"])
    n_b = sum(1 for r in rows if r["part"] == "B" and r["ok"])
    if (n_a, n_b) != (14, 128):
        raise SystemExit("bench sweep is A %d/14 B %d/128, refusing to build"
                         % (n_a, n_b))

    base = tuple(int(v) for v in args.base.split(","))
    placements, entities = world_of(lay, base)
    BBOX = bbox_of(placements)

    world_dir, regions, version = build_world(placements, entities,
                                              Path(args.out), "world4")

    specs = [part_a(lay, base, rows, world_dir, args.template, args.rcon_port,
                    args.max_gt, args.settle_gt, args.max_rcon)]
    specs += part_b(lay, base, rows, world_dir, args.template, args.rcon_port,
                    args.max_gt, args.settle_gt, args.max_rcon, args.b_chunks)

    print("world %s blocks %d block_entities %d regions %s dv %d"
          % (world_dir, len(placements), len(entities), regions, version))
    print("bbox %s %s" % (BBOX[0], BBOX[1]))
    for name, art in lay["artifacts"].items():
        zs = [art["origin"][2] + r[2] for r in art["blocks"]]
        print("  %-18s origin z %3d  cells %4d  world z %d..%d"
              % (name, art["origin"][2], len(art["blocks"]),
                 base[2] + min(zs), base[2] + max(zs)))
    for spec in specs:
        per, tot = est_rcon(spec, args.max_gt)
        path = HERE / (spec["name"] + ".spec.json")
        path.write_bytes((json.dumps(spec, indent=1) + "\n").encode("utf-8"))
        print("%-10s drives %2d reads %3d regimes %3d  rcon/regime ~%d  "
              "total ~%d of %d  -> %s"
              % (spec["name"], len(spec["drives"]), len(spec["reads"]),
                 len(spec["regimes"]), per, tot, args.max_rcon, path.name))
        if tot > args.max_rcon:
            print("  WARNING: estimate exceeds max_rcon")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    raise SystemExit(main())
