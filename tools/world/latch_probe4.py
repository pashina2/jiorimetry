#!/usr/bin/env python3
"""docs/world/latch_probe4.py -- does a fed PLACER-0 layout have a
SECOND DC solution?

`capcell.dc_solve`'s docstring says it plainly: "A circuit with feedback may
have more than one DC solution; this returns the one the iteration walks to."
Both checkers start the iteration cold, so a latch that only exists once the
circuit has been lit is invisible to them.  This runs each of the 14 (A) rows
twice on the same Bench -- once from the cold start the checkers use, once
seeded from a fully lit state (every repeater `powered=true`, every non-lever
dust at 15) with the levers set for the row -- and prints the rows where the
two fixpoints differ.

Written AFTER the world run, as the diagnosis of `v_p4_T0` (record.md 7.3).
Usage: latch_probe4.py [layout_world4.json]
"""
import itertools
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "llmgen"))
import bench_sweep_feed4 as BSF                              # noqa: E402
import capcell as CC                                         # noqa: E402

PLACER0 = HERE.parents[1] / "artifacts" / "placer0"


def solve(art, levers_on, latched):
    blocks = {}
    for r in art["blocks"]:
        name, props = BSF.parse(r[3])
        blocks[tuple(r[:3])] = (name, props)
    lever_cells = {tuple(v) for v in art["levers"].values()}
    for nm, pos in art["levers"].items():
        blocks[tuple(pos)][1]["powered"] = "true" if levers_on[nm] else "false"
    if latched:
        for pos, (name, props) in blocks.items():
            if name == "minecraft:repeater":
                props["powered"] = "true"
            elif name == "minecraft:redstone_wire" and pos not in lever_cells:
                props["power"] = "15"
    be = {}
    for key, n in art["barrels"].items():
        pos = tuple(int(t) for t in key.split(","))
        n, items = int(n), []
        while n > 0:
            c = min(64, n)
            items.append({"id": "minecraft:cobblestone", "count": c,
                          "max_count": 64})
            n -= c
        be[pos] = {"items": items}
    bench = CC.Bench(blocks, block_entities=be)
    rounds, conv = bench.dc_solve()
    return bench, rounds, conv


def main(argv):
    path = argv[1] if len(argv) > 1 else str(HERE / "layout_world4.json")
    lay = json.loads(Path(path).read_text(encoding="utf-8"))
    probs = {p["name"]: p for p in json.loads(
        (PLACER0 / "problems.json").read_text(encoding="utf-8"))}
    n_diff = 0
    for name in ("p1_sub2side", "p2_copy_into_side", "p4_throughline",
                 "p5_max_merge", "p6_vertical_cap"):
        art, prob = lay["artifacts"][name], probs[name]
        pins = list(prob["pins"])
        cell = tuple(prob["outputs"][0]["cell"])
        for combo in itertools.product(*[prob["pins"][n]["levels"] for n in pins]):
            env = dict(zip(pins, combo))
            on = BSF.levers_for(art, env)
            cold = solve(art, on, False)[0].blocks[cell][1]["power"]
            b, rounds, _ = solve(art, on, True)
            hot = b.blocks[cell][1]["power"]
            same = cold == hot
            n_diff += not same
            print("%-19s %-18s cold O=%-3s latched O=%-3s (%d round%s) %s"
                  % (name, env, cold, hot, rounds, "" if rounds == 1 else "s",
                     "same fixpoint" if same else "SECOND FIXPOINT"))
    print("rows with a second DC solution: %d of 14" % n_diff)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
