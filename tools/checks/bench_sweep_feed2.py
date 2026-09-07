#!/usr/bin/env python3
"""tools/checks/bench_sweep_feed2.py -- the 32 ALU rows of
tools/checks/alu_check2.py, with the harness PINS replaced by the
physical lever feeders of layout_world2.json.  A world has no pins; this is the
question the world can actually be asked.

Convention: data lever ON = input bit 0, OFF = bit 1.  Control lever ON = 15.
Usage: bench_sweep_feed2.py [layout_world2.json] [rows_out.json]
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

HERE = Path(__file__).resolve().parent
ALIAS = {"minecraft:stone": "minecraft:smooth_stone",
         "minecraft:gray_wool": "minecraft:smooth_stone",
         "minecraft:white_wool": "minecraft:smooth_stone"}

OPS = {"ADD": (0, 15, "a + b + k == r + 2*f"),
       "SUB": (0, 0, "a - b - k == r - 2*f"),
       "AND": (15, 15, "r == (a and b) and f == 0"),
       "OR": (15, 0, "r == (a or b) and f == 0")}


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
    if name == "minecraft:repeater":
        props.setdefault("powered", "false")
        props.setdefault("delay", "1")
        props.setdefault("locked", "false")
    if name == "minecraft:lever":
        props.setdefault("powered", "false")
        props.setdefault("face", "floor")
        props.setdefault("facing", "north")
    return name, props


def lever_state(lay, a, b, k, P, Wn):
    """{lever name: bool powered}.  Data: ON == bit 0.  Control: ON == 15."""
    st = {}
    for pin, bit in (("a", a), ("b", b), ("k", k)):
        for nm in lay["data_levers"][pin]:
            st[nm] = (bit == 0)
    for pin, lvl in (("P", P), ("Wn", Wn)):
        for nm in lay["ctrl_levers"][pin]:
            st[nm] = (lvl == 15)
    return st


def build(lay, levers_on):
    blocks = {}
    for r in lay["blocks"]:
        blocks[tuple(r[:3])] = parse(r[3])
    for nm, pos in lay["levers"].items():
        pos = tuple(pos)
        assert blocks[pos][0] == "minecraft:lever", (nm, pos, blocks[pos][0])
        blocks[pos][1]["powered"] = "true" if levers_on[nm] else "false"
    be = {}
    for key, n in lay["barrels"].items():
        pos = tuple(int(v) for v in key.split(","))
        n = int(n)
        items = []
        while n > 0:
            c = min(64, n)
            items.append({"id": "minecraft:cobblestone", "count": c,
                          "max_count": 64})
            n -= c
        be[pos] = {"items": items}
    return CC.Bench(blocks, block_entities=be)


def read(bench, pos):
    pos = tuple(pos)
    e = bench.blocks.get(pos)
    if e is None:
        return None
    if e[0] == CC.DUST:
        return int(e[1]["power"])
    if e[0] == CC.COMPARATOR:
        return bench.cmp_out.get(pos)
    return None


def sweep(lay):
    rows = []
    for op, (P, Wn, rel) in OPS.items():
        for a, b, k in itertools.product((0, 1), repeat=3):
            on = lever_state(lay, a, b, k, P, Wn)
            bench = build(lay, on)
            rounds, conv = bench.dc_solve()
            r = read(bench, lay["readout"]["r"])
            fw = read(bench, lay["readout"]["f_wire"])
            fc = read(bench, lay["readout"]["f_cmp"])
            dr, df = int((r or 0) >= 3), int((fw or 0) >= 3)
            ok = bool(conv and r in (0, 3) and fw in (0, 3) and fw == fc
                      and eval(rel, {}, {"a": a, "b": b, "k": k,
                                         "r": dr, "f": df}))
            cmp_out = {"%d,%d,%d" % p: v for p, v in bench.cmp_out.items()}
            rows.append({"op": op, "a": a, "b": b, "k": k, "P": P, "Wn": Wn,
                         "levers_on": on, "r": r, "f_wire": fw, "f_cmp": fc,
                         "r_bit": dr, "f_bit": df, "ok": ok,
                         "rounds": rounds, "converged": bool(conv),
                         "cmp_out": cmp_out})
    return rows


def main(argv):
    path = argv[1] if len(argv) > 1 else str(HERE / "layout_world2.json")
    lay = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = sweep(lay)
    for x in rows:
        print("%-3s a=%d b=%d k=%d | r=%-4s f=%-4s (cmp %-4s) -> r%d f%d | %s "
              "rounds=%d conv=%s"
              % (x["op"], x["a"], x["b"], x["k"], x["r"], x["f_wire"],
                 x["f_cmp"], x["r_bit"], x["f_bit"],
                 "ok  " if x["ok"] else "FAIL", x["rounds"], x["converged"]))
    n = sum(1 for x in rows if x["ok"])
    print("PASS %d/32" % n)
    out = argv[2] if len(argv) > 2 else str(HERE / "bench_feed2_rows.json")
    Path(out).write_bytes((json.dumps(rows, indent=1) + "\n").encode("utf-8"))
    print("wrote %s" % out)
    return 0 if n == 32 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
