#!/usr/bin/env python3
"""docs/world/make_diag4.py -- the follow-up spec `world4x`, which
asks the SAME world one extra question: where in p4_throughline the world and
the Bench part company.

Part A found `v_p4_T0` reading 15 where the Bench says 0, and the Bench itself
shows why it can: the fed p4 layout has TWO DC fixpoints at T=0 (a cold one and
a latched one), and `capcell.dc_solve` walks to the cold one from a cold start.
This spec drives T 0 -> 15 -> 0 -> 15 -> 0 with a read on EVERY wire of the
through-line, so the world can say for itself which cell holds the latch.

No expectation is written: this run measures, it does not judge.
Usage: make_diag4.py --world-dir <the world build_world4.py wrote>
"""
import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = (100, 64, 100)
Z0 = 40                       # p4_throughline's origin z, from make_layout_world4

#: every wire of the through-line, in p4's own frame, source first
WIRES = [("T", (0, 1, 1)), ("w113", (1, 1, 3)), ("w121", (1, 2, 1)),
         ("w331", (3, 3, 1)), ("w521", (5, 2, 1)), ("O", (7, 1, 1))]
REPEATERS = [("d0", (0, 1, 2)), ("d1", (1, 1, 2)), ("d2", (2, 2, 1)),
             ("d4", (4, 3, 1)), ("d6", (6, 2, 1))]
#: the wire cells of the suspected feedback path, read at every level the
#: through-line can carry, so an intermediate level is visible as "no bit"
LEVELS = (0, 15)


def w(rel):
    return [BASE[0] + rel[0], BASE[1] + rel[1], BASE[2] + Z0 + rel[2]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--world-dir", required=True)
    ap.add_argument("--rcon-port", type=int, default=25598)
    ap.add_argument("--template",
                    default=r"<host-path>/carpet-work")
    args = ap.parse_args()

    lay = json.loads((HERE / "layout_world4.json").read_text(encoding="utf-8"))
    drives = {}
    for art in lay["artifacts"].values():
        for name, pos in art["levers"].items():
            drives[name] = {"kind": "lever",
                            "pos": [BASE[0] + art["origin"][0] + pos[0],
                                    BASE[1] + art["origin"][1] + pos[1],
                                    BASE[2] + art["origin"][2] + pos[2]],
                            "face": "floor", "facing": "north"}

    reads, bit = [], 0
    for name, rel in WIRES:
        for lv in LEVELS:
            reads.append({"name": "%s_%d" % (name, lv), "pos": w(rel), "bit": bit,
                          "match": "minecraft:redstone_wire[power=%d]" % lv})
            bit += 1
    for name, rel in REPEATERS:
        reads.append({"name": name, "pos": w(rel),
                      "match": "minecraft:repeater[powered=true]"})
        reads.append({"name": name + "_locked", "pos": w(rel),
                      "match": "minecraft:repeater[locked=true]"})

    base_inputs = {k: 0 for k in drives}
    base_inputs["p6_n"] = 1
    regimes = []
    for i, t in enumerate((0, 1, 0, 1, 0)):
        inputs = dict(base_inputs)
        inputs["p4_t"] = t
        regimes.append({"name": "x%d_T%d" % (i, 15 * t), "inputs": inputs,
                        "max_gt": 40, "settle_gt": 10})

    cells = []
    for name, art in lay["artifacts"].items():
        for r in art["blocks"]:
            cells.append([BASE[0] + art["origin"][0] + r[0],
                          BASE[1] + art["origin"][1] + r[1],
                          BASE[2] + art["origin"][2] + r[2]])
    lo = [min(p[i] for p in cells) - 1 for i in range(3)]
    hi = [max(p[i] for p in cells) + 1 for i in range(3)]

    spec = {"name": "world4x",
            "world": {"template": args.template, "world_dir": args.world_dir,
                      "bbox": {"min": lo, "max": hi}},
            "server": {"host": "127.0.0.1", "rcon_port": args.rcon_port,
                       "java_xmx": "3G"},
            "drives": drives, "reads": reads, "regimes": regimes,
            "limits": {"max_rcon": 600000}, "out_dir": str(HERE)}
    p = HERE / "world4x.spec.json"
    p.write_bytes((json.dumps(spec, indent=1) + "\n").encode("utf-8"))
    print("reads %d regimes %d -> %s" % (len(reads), len(regimes), p))


if __name__ == "__main__":
    main()
