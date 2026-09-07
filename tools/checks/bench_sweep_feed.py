#!/usr/bin/env python3
"""tools/checks/bench_sweep_feed.py -- tools/checks/bench_sweep.py
with the harness's state-write PINS replaced by PHYSICAL feeders driven by levers.

Why a second sweep script and not a flag on the first: `bench_sweep.py` answers
"what does the stage do when a wire is HELD at 0/5", which is a question about
the stage alone. This one answers "what does the stage do when three levers,
three barrels and three comparators try to hold that wire at 0/5", which is the
question the world can be asked -- a world has no pins. The stage block list is
the same file's; only the feeders and the drive are new.

Convention (INVERTED, and this is the whole reason it is stated here): the
feeder is a comparator in compare mode whose BACK is a level-5 barrel and whose
SIDE is a lever-driven wire. side 15 > back 5 -> output 0; side 0 -> output 5.
So lever ON = input bit 0 and lever OFF = input bit 1.

Usage: bench_sweep_feed.py layout_world1.json
"""
import json
import sys
import itertools
import re
from pathlib import Path

import os as _os
sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), "..", "llmgen"))
import capcell as CC                                        # noqa: E402

ALIAS = {"minecraft:stone": "minecraft:smooth_stone"}


def parse(s):
    m = re.match(r'(minecraft:[a-z_]+)(?:\[(.*)\])?$', s)
    name = m.group(1)
    props = {}
    if m.group(2):
        for kv in m.group(2).split(','):
            k, v = kv.split('=')
            props[k] = v
    name = ALIAS.get(name, name)
    if name == "minecraft:comparator":
        props.setdefault("powered", "false")
        props.setdefault("mode", "compare")
    if name == "minecraft:lever":
        props.setdefault("powered", "false")
        props.setdefault("face", "floor")
        props.setdefault("facing", "north")
    return name, props


def build(layout, lever_on):
    """lever_on: {input name: bool}. A fresh Bench per vector -- DC only."""
    blocks = {}
    for r in layout["blocks"]:
        blocks[tuple(r[:3])] = parse(r[3])
    for name, pos in layout["levers"].items():
        pos = tuple(pos)
        assert blocks[pos][0] == "minecraft:lever", (name, pos, blocks[pos][0])
        blocks[pos][1]["powered"] = "true" if lever_on[name] else "false"
    be = {}
    for k, n in layout["barrels"].items():
        pos = tuple(int(v) for v in k.split(','))
        n = int(n)
        items = []
        while n > 0:
            c = min(64, n)
            items.append({"id": "minecraft:cobblestone", "count": c, "max_count": 64})
            n -= c
        be[pos] = {"items": items}
    return CC.Bench(blocks, block_entities=be)


def wire_power(b, pos):
    entry = b.blocks.get(tuple(pos))
    if entry is None or entry[0] != CC.DUST:
        return None
    return int(entry[1]["power"])


def sweep(layout, lvl=5):
    rows = []
    for a, bb, c in itertools.product((0, 1), repeat=3):
        bits = {"a": a, "b": bb, "cin": c}
        # INVERTED drive: lever ON == bit 0.
        lever_on = {k: (v == 0) for k, v in bits.items()}
        b = build(layout, lever_on)
        rounds, converged = b.dc_solve()
        s = wire_power(b, layout["outputs"]["sum"])
        co = wire_power(b, layout["outputs"]["cout"])
        feeds = {k: b.cmp_out.get(tuple(p)) for k, p in
                 (("a", (1, 1, -1)), ("cin", (3, 1, -1)), ("b", (2, 1, 3)))}
        ins = {k: wire_power(b, layout["inputs"][k]) for k in ("a", "b", "cin")}
        ds = int(s is not None and s >= lvl)
        dc = int(co is not None and co >= lvl)
        rows.append({"a": a, "b": bb, "cin": c, "levers_on": lever_on,
                     "feed_out": feeds, "input_wire_power": ins,
                     "sum_power": s, "cout_power": co,
                     "sum_bit": ds, "cout_bit": dc,
                     "arith_ok": bool(a + bb + c == ds + 2 * dc),
                     "levels_clean": bool(s in (0, lvl) and co in (0, lvl)),
                     "rounds": rounds, "converged": bool(converged)})
    return rows


def main(argv):
    layout = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    rows = sweep(layout)
    for r in rows:
        print("a=%d b=%d cin=%d | feed a/b/cin=%s/%s/%s in=%s/%s/%s | "
              "sum=%s cout=%s -> %d%d | arith=%s clean=%s rounds=%d conv=%s"
              % (r["a"], r["b"], r["cin"],
                 r["feed_out"]["a"], r["feed_out"]["b"], r["feed_out"]["cin"],
                 r["input_wire_power"]["a"], r["input_wire_power"]["b"],
                 r["input_wire_power"]["cin"],
                 r["sum_power"], r["cout_power"], r["cout_bit"], r["sum_bit"],
                 r["arith_ok"], r["levels_clean"], r["rounds"], r["converged"]))
    n = sum(1 for r in rows if r["arith_ok"] and r["levels_clean"] and r["converged"])
    print("clean arithmetic rows %d/8" % n)
    if len(argv) > 2:
        Path(argv[2]).write_bytes((json.dumps(rows, indent=1) + "\n").encode("utf-8"))
        print("wrote %s" % argv[2])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
