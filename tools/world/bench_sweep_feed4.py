#!/usr/bin/env python3
"""docs/world/bench_sweep_feed4.py -- every row WORLD-4 will drive
in the world, solved FIRST on the Bench with the harness PINS replaced by the
physical lever feeders of layout_world4.json.

A world has no pins.  This is the question the world can actually be asked, and
it is asked of the same `capcell.Bench` the two checkers use:
  (A) the 14 pin combinations of the five solvable PLACER-0 problems -- the
      output wire must read what `placer0_check.py -v` prints in its `expect`
      column;
  (B) the 128 rows of `alu_check_slices.py alu_slice_v9.json 2` -- r0, r1 and
      the added f wire must equal the PINNED Bench's r and f, the 128/128
      relation must still hold, the slice-1 through-line entries must equal the
      P / Wn pin levels and the slice-1 k wire must equal
      3 * alu_check_contract.expected_carry(mode, A, B, k, 1).

Convention: data lever ON = input bit 0 (side 15 kills the level-3 compare
gate), OFF = bit 1; control lever ON = 15.

Usage: bench_sweep_feed4.py [layout_world4.json] [rows_out.json]
"""
import itertools
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ART = HERE.parents[1] / "artifacts"   # export layout: artifacts/placer0, artifacts/layouts
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "llmgen"))
sys.path.insert(0, str(HERE.parents[0] / "checks"))
import capcell as CC                                         # noqa: E402
import alu_check_slices as CS                                # noqa: E402
import alu_check_contract as CT                              # noqa: E402

PLACER0 = ART / "placer0"
SLICE = ART / "layouts"

ALIAS = {"minecraft:stone": "minecraft:smooth_stone",
         "minecraft:gray_wool": "minecraft:smooth_stone",
         "minecraft:white_wool": "minecraft:smooth_stone"}


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


def levers_for(art, pin_values):
    """{lever name: bool powered} for one assignment of pin levels."""
    st = {}
    for pin, lv in pin_values.items():
        if pin in art["data_levers"]:
            for nm in art["data_levers"][pin]:
                st[nm] = (int(lv) == 0)
        elif pin in art["ctrl_levers"]:
            for nm in art["ctrl_levers"][pin]:
                st[nm] = (int(lv) == 15)
        else:
            raise SystemExit("pin %s has no lever" % pin)
    missing = set(art["levers"]) - set(st)
    if missing:
        raise SystemExit("levers not set: %s" % sorted(missing))
    return st


def build(art, levers_on):
    blocks = {}
    for r in art["blocks"]:
        blocks[tuple(r[:3])] = parse(r[3])
    for nm, pos in art["levers"].items():
        pos = tuple(pos)
        assert blocks[pos][0] == "minecraft:lever", (nm, pos, blocks[pos][0])
        blocks[pos][1]["powered"] = "true" if levers_on[nm] else "false"
    be = {}
    for key, n in art["barrels"].items():
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


def gate_states(bench, art):
    """{read name: (cmp_out>0 for a comparator, powered for a repeater)}.

    For a comparator the order asks for `cmp_out > 0`; the Bench also carries
    its own `powered` block state, and `powered_agrees` records whether the two
    ever part company."""
    out, agree = {}, True
    for nm, pos in art["gates"].items():
        pos = tuple(pos)
        name, props = bench.blocks[pos]
        if name == CC.COMPARATOR:
            on = bool(bench.cmp_out.get(pos, 0) > 0)
            if on != (props["powered"] == "true"):
                agree = False
        else:
            on = props["powered"] == "true"
        out[nm] = on
    return out, agree


# ------------------------------------------------------------------- part A

def sweep_placer0(lay):
    probs = {p["name"]: p for p in json.loads(
        (PLACER0 / "problems.json").read_text(encoding="utf-8"))}
    rows = []
    for name in ("p1_sub2side", "p2_copy_into_side", "p4_throughline",
                 "p5_max_merge", "p6_vertical_cap"):
        art = lay["artifacts"][name]
        prob = probs[name]
        pin_names = list(prob["pins"].keys())
        for combo in itertools.product(*[prob["pins"][n]["levels"]
                                         for n in pin_names]):
            env = dict(zip(pin_names, combo))
            on = levers_for(art, env)
            bench = build(art, on)
            rounds, conv = bench.dc_solve()
            gates, agree = gate_states(bench, art)
            outs = {}
            for oname, o in art["outputs"].items():
                got = read(bench, o["cell"])
                exp = int(eval(o["expect"], {"max": max, "min": min}, dict(env)))
                outs[oname] = {"got": got, "expect": exp, "equal": got == exp}
            rows.append({"part": "A", "artifact": name, "pins": env,
                         "levers_on": on, "outputs": outs,
                         "gates": gates, "powered_agrees": agree,
                         "rounds": rounds, "converged": bool(conv),
                         "ok": bool(conv and all(o["equal"] for o in outs.values()))})
    return rows


# ------------------------------------------------------------------- part B

def sweep_slice(lay):
    art = lay["artifacts"]["slice_v9_n2"]
    src = json.loads((SLICE / "alu_slice_v9.json").read_text(encoding="utf-8"))
    n, PX = art["n"], art["pitch"]
    rows = []
    for mode, (P, Wn) in CS.MODES.items():
        for A in range(2 ** n):
            for B in range(2 ** n):
                for k in (0, 1):
                    env = {"P": P, "Wn": Wn, "k": 3 * k,
                           "a0": 3 * (A & 1), "a1": 3 * ((A >> 1) & 1),
                           "b0": 3 * (B & 1), "b1": 3 * ((B >> 1) & 1)}
                    on = levers_for(art, env)
                    bench = build(art, on)
                    rounds, conv = bench.dc_solve()
                    gates, agree = gate_states(bench, art)
                    got = {nm: read(bench, r["cell"])
                           for nm, r in art["reads"].items()}
                    got["f_cmp"] = read(bench, art["f_cmp"])
                    # the PINNED Bench, for the same row
                    prs, pf, pconv, _ = CS.run(src, n, A, B, k, P, Wn)
                    exp = {"r0": prs[0], "r1": prs[1], "f": pf,
                           "thrP": P, "thrWn": Wn,
                           "carry": 3 * CT.expected_carry(mode, A, B, k, 1)}
                    R = sum(((got["r%d" % i] or 0) >= 3) << i for i in range(n))
                    F = int((got["f"] or 0) >= 3)
                    if mode == "ADD":
                        rel = (A + B + k) == (R + (2 ** n) * F)
                    elif mode == "SUB":
                        rel = (A - B - k) == (R - (2 ** n) * F)
                    elif mode == "AND":
                        rel = (R == (A & B) and F == 0)
                    else:
                        rel = (R == (A | B) and F == 0)
                    clean = (conv and all(got["r%d" % i] in (0, 3)
                                          for i in range(n))
                             and got["f"] in (0, 3))
                    equal = {key: got[key] == exp[key] for key in exp}
                    rows.append({"part": "B", "artifact": "slice_v9_n2",
                                 "mode": mode, "A": A, "B": B, "k": k,
                                 "pins": env, "levers_on": on,
                                 "got": got, "expect": exp, "equal": equal,
                                 "f_wire_eq_f_cmp": got["f"] == got["f_cmp"],
                                 "R": R, "F": F, "rel": bool(rel),
                                 "pinned_converged": bool(pconv),
                                 "gates": gates, "powered_agrees": agree,
                                 "rounds": rounds, "converged": bool(conv),
                                 "ok": bool(clean and rel and all(equal.values())
                                            and got["f"] == got["f_cmp"])})
    return rows


def main(argv):
    path = argv[1] if len(argv) > 1 else str(HERE / "layout_world4.json")
    lay = json.loads(Path(path).read_text(encoding="utf-8"))
    a = sweep_placer0(lay)
    for x in a:
        print("%-18s %-28s O got %-3s expect %-3s %s rounds=%d conv=%s"
              % (x["artifact"], x["pins"],
                 list(x["outputs"].values())[0]["got"],
                 list(x["outputs"].values())[0]["expect"],
                 "ok  " if x["ok"] else "FAIL", x["rounds"], x["converged"]))
    na = sum(1 for x in a if x["ok"])
    print("part A PASS %d/%d" % (na, len(a)))

    b = sweep_slice(lay)
    for x in b:
        if not x["ok"]:
            print("FAIL %s A=%d B=%d k=%d got %s expect %s"
                  % (x["mode"], x["A"], x["B"], x["k"], x["got"], x["expect"]))
    nb = sum(1 for x in b if x["ok"])
    print("part B PASS %d/%d" % (nb, len(b)))
    print("powered==cmp_out>0 on every comparator in every row: %s"
          % all(x["powered_agrees"] for x in a + b))
    out = argv[2] if len(argv) > 2 else str(HERE / "bench_feed4_rows.json")
    Path(out).write_bytes((json.dumps(a + b, indent=1) + "\n").encode("utf-8"))
    print("wrote %s" % out)
    return 0 if (na == len(a) and nb == len(b)) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
