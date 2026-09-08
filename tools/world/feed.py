#!/usr/bin/env python3
"""tools/world/feed.py -- from a layout with pins to a verified
world reading, in one command.

WORLD-1, WORLD-2 and WORLD-4 each spent an LLM seat writing, by hand, the same
three things: the physical feeders that replace the checker's PINS, the void
world that holds them, and the worldprobe spec that drives every row.  All
three are determined by the layout, its pins and the REQUIREMENT the artifact
answers to.  This module derives them.

What it does, in order:

 1. **Feeder search.**  For every pin cell it searches the air around the pin
    for one of the two shapes WORLD-1 calibrated against a real 1.20.6 server:

    * DATA pin (0 / 3): a comparator in COMPARE mode whose BACK is a barrel
      holding 247 stack-64 items (level 3) and whose SIDE is a lever-driven
      wire.  A side driven to 15 kills a level-3 back, so **lever ON = level
      0, lever OFF = level 3** -- an inverted convention, declared.
    * CONTROL pin (0 / 15): a solid block beside the pin wire with a
      `face=floor` lever on top.  **Lever ON = 15.**

    A candidate is accepted only if it (1) collides with no cell of the
    layout or of an already accepted feeder, (2) is no layout gate's back or
    side and touches no layout wire it is not feeding -- tested
    ELECTRICALLY, by solving the layout with and without the feeder and
    demanding that every layout cell hold the same state, (3) stands on
    support, and (4) leaves the whole fed layout reproducing the
    requirement-derived expected values with an empty `dc_solve_both` diff.
    A pin with no candidate is reported WITH ITS REASON (collision / side or
    back / support / electrical / bistable) and no world is built.

    Convention (WORLD-1, against a real server): a comparator or repeater with
    `facing=D` has its BACK at `pos+D` and its OUTPUT at `pos-D`.

 2. **Expected values from the REQUIREMENT, never from the Bench.**  For an
    ALU stage or an n-slice ALU the rows and the answers come from the
    function table (mode x A x B x k -> R, F, carry); for a PLACER-0 problem
    from the `expect` expression over the pin names.  The Bench is the thing
    that gets checked against them.

 3. **The world**, through `worldgen` (the four-line idiom `synthworld`
    spells; `synthworld.build_world` passes an EMPTY block-entity map, and
    these artifacts are defined by barrels whose item counts are their
    constants, so the four lines are spelled here with the map filled in --
    the same deviation WORLD-2 and WORLD-4 declared).

 4. **The spec**, per artifact: two wake regimes (every lever on, then every
    lever off -- a lever that never moves leaves its feeder gate stale), then
    every row as `warm_*` (recorded, not compared), then every row as `v_*`
    (compared).  A regime costs `(max_gt+1) x state reads` rcon roundtrips, so
    when the estimate passes `limits.max_rcon` the rows are split across runs
    by index mod n, each run self-contained.

 5. **The run and the table.**  `worldprobe.py run` per spec, then one row per
    artifact: Bench PASS, world rows, world FAIL, read points, mismatch rate,
    settle gt, block count and the first counterexample at cell level.

Usage:
  feed.py JOB.json --out RUNDIR [--run] [--rcon-port 25598] [--dry-run]
  feed.py LAYOUT.json [LAYOUT2.json ...] --out RUNDIR [--run]

A JOB is `{"name": ..., "artifacts": [entry, ...]}`; an entry is either
`{"name": N, "layout": PATH}` (blocks/barrels plus `pins` or a `slice`
section) or `{"name": N, "problem": PROBLEMS.json, "problem_name": P,
"solution": SOL.json}` (a PLACER-0 pair).  `require` may be given explicitly
(`{"kind": "alu_stage" | "alu_slice" | "expect", ...}`); it is otherwise
inferred from the layout's own shape.  Nothing outside `--out` and the job's
`out_dir` is written.
"""

import argparse
import itertools
import json
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for _p in (str(ROOT / "tools" / "llmgen"),
           str(ROOT / "tools" / "m9-worldgen"), str(HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import capcell as CC                                          # noqa: E402
import machine as M                                           # noqa: E402
import synthworld as SW                                       # noqa: E402
import worldgen                                               # noqa: E402

bridge = worldgen.bridge

STONE = "minecraft:smooth_stone"
DUST = "minecraft:redstone_wire"
BARREL = "minecraft:barrel[facing=up,open=false]"
LEVER = "minecraft:lever[face=floor,facing=north,powered=false]"
#: stack-64 items in a 27-slot barrel -> comparator level 3
L3 = 247
HORIZ = ("north", "south", "east", "west")
#: (P, Wn) per ALU mode, the checkers' own table
MODES = {"ADD": (0, 15), "SUB": (0, 0), "AND": (15, 15), "OR": (15, 0)}
ALIAS = {"minecraft:stone": STONE, "minecraft:gray_wool": STONE,
         "minecraft:white_wool": STONE}
GATES = ("minecraft:comparator", "minecraft:repeater")


class FeedError(ValueError):
    """A job this module refuses to turn into a world."""


# --- block states -----------------------------------------------------------

def parse(s):
    """`minecraft:name[k=v,...]` -> (name, props), defaults filled in."""
    m = re.match(r'(minecraft:[a-z_]+)(?:\[(.*)\])?$', s)
    if m is None:
        raise FeedError("unparsable block state %r" % (s,))
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
    if name == "minecraft:redstone_lamp":
        props.setdefault("lit", "false")
    return name, props


def add(pos, d):
    v = M.FACES[d]
    return (pos[0] + v[0], pos[1] + v[1], pos[2] + v[2])


def below(pos):
    return (pos[0], pos[1] - 1, pos[2])


def above(pos):
    return (pos[0], pos[1] + 1, pos[2])


def sides_of(d):
    """The two horizontal side directions of a gate facing `d`."""
    cw = M.CLOCKWISE[d]
    return (cw, M.OPPOSITE[cw])


def item_list(total, max_count=64, item="minecraft:cobblestone"):
    """Items for a container holding `total` stack-64 items (1.20.5+ spelling:
    `count` as an int, not `Count` as a byte)."""
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


def bench_items(count):
    n, items = int(count), []
    while n > 0:
        c = min(64, n)
        items.append({"id": "minecraft:cobblestone", "count": c,
                      "max_count": 64})
        n -= c
    return items


def bench_of(blocks, barrels, floors=None, levers=None):
    """A `capcell.Bench` over `{pos: state string}` + `{pos: item count}`."""
    parsed = {pos: parse(s) for pos, s in blocks.items()}
    for pos, on in (levers or {}).items():
        name, props = parsed[pos]
        if name != "minecraft:lever":
            raise FeedError("%s is %s, not a lever" % (pos, name))
        props["powered"] = "true" if on else "false"
    be = {pos: {"items": bench_items(n)} for pos, n in barrels.items()}
    return CC.Bench(parsed, block_entities=be, floors=floors or {})


def level_at(bench, pos):
    pos = tuple(pos)
    e = bench.blocks.get(pos)
    if e is None:
        return None
    if e[0] == CC.DUST:
        return int(e[1]["power"])
    if e[0] == CC.COMPARATOR:
        return bench.cmp_out.get(pos)
    return None


def state_map(bench, cells):
    """The comparable DC state of `cells`: what a reading could ever see."""
    out = {}
    for pos in cells:
        e = bench.blocks.get(pos)
        if e is None:
            out[pos] = None
            continue
        name, props = e
        if name == CC.DUST:
            out[pos] = ("power", props["power"])
        elif name == CC.COMPARATOR:
            out[pos] = ("cmp", props["powered"], bench.cmp_out.get(pos))
        elif name in (CC.REPEATER, CC.LEVER):
            out[pos] = ("powered", props["powered"])
        elif name in (M.TORCH, M.WALL_TORCH, M.LAMP):
            out[pos] = ("lit", props["lit"])
        else:
            out[pos] = ("solid",)
    return out


# --- the requirement --------------------------------------------------------

def expected_carry(mode, A, B, k, i):
    """Carry INTO bit i (i = 0 -> k).  The requirement, not a measurement."""
    c = k
    for j in range(i):
        a, b = (A >> j) & 1, (B >> j) & 1
        if mode == "ADD":
            c = int(a + b + c >= 2)
        elif mode == "SUB":
            c = int(a - b - c < 0)
        else:
            c = 0
    return c


def expected_rf(mode, A, B, k, n):
    """(R, F) for an n-bit ALU word, from the mode's relation."""
    if mode == "ADD":
        s = A + B + k
        return s % (2 ** n), s // (2 ** n)
    if mode == "SUB":
        d = A - B - k
        return d % (2 ** n), (1 if d < 0 else 0)
    if mode == "AND":
        return A & B, 0
    if mode == "OR":
        return A | B, 0
    raise FeedError("unknown mode %r" % (mode,))


def rows_alu(n):
    """Every row of an n-bit ALU, with the answers the requirement fixes.

    A row is `{name, pins {pin: level}, expect {read: level}}`; `pins` names
    the LEVELS the feeders must deliver, `expect` the levels the reads must
    show.  Nothing here has seen a Bench."""
    rows = []
    for mode, (P, Wn) in MODES.items():
        for A in range(2 ** n):
            for B in range(2 ** n):
                for k in (0, 1):
                    pins = {"P": P, "Wn": Wn, "k": 3 * k}
                    for i in range(n):
                        pins["a%d" % i] = 3 * ((A >> i) & 1)
                        pins["b%d" % i] = 3 * ((B >> i) & 1)
                    R, F = expected_rf(mode, A, B, k, n)
                    exp = {"f": 3 * F, "thrP": P, "thrWn": Wn}
                    for i in range(n):
                        exp["r%d" % i] = 3 * ((R >> i) & 1)
                    for i in range(1, n):
                        exp["carry%d" % i] = 3 * expected_carry(mode, A, B, k, i)
                    rows.append({"name": "%s_A%dB%dk%d" % (mode, A, B, k),
                                 "pins": pins, "expect": exp,
                                 "key": {"mode": mode, "A": A, "B": B, "k": k}})
    return rows


def rows_expect(pins, outputs):
    """PLACER-0 rows: the product of the pin levels, answered by `expect`."""
    names = list(pins)
    rows = []
    for combo in itertools.product(*[pins[n]["levels"] for n in names]):
        env = dict(zip(names, combo))
        exp = {o["name"]: int(eval(o["expect"], {"max": max, "min": min},
                                   dict(env)))
               for o in outputs}
        tail = "".join("%s%d" % (k, v) for k, v in sorted(env.items()))
        rows.append({"name": tail, "pins": dict(env), "expect": exp,
                     "key": dict(env)})
    return rows


# --- artifacts --------------------------------------------------------------

class Artifact(object):
    """One layout under test: its cells, its pins, its reads, its rows."""

    def __init__(self, name, blocks, barrels, pins, reads, rows, kind):
        self.name = name
        self.blocks = dict(blocks)             # {pos: state string}
        self.barrels = dict(barrels)           # {pos: item count}
        self.pins = pins                       # {pin: {cells, kind, levels}}
        self.reads = reads                     # {read: {cell, levels}}
        self.rows = rows
        self.kind = kind
        self.n_artifact_cells = len(blocks)
        self.feeders = {}                      # {pin: [feeder, ...]}
        self.levers = {}                       # {lever name: pos}
        self.origin = [0, 0, 0]

    # -- geometry the search needs
    def gate_backs_sides(self):
        backs, sides = {}, {}
        for pos, s in self.blocks.items():
            name, props = parse(s)
            if name not in GATES:
                continue
            d = props["facing"]
            backs[add(pos, d)] = pos
            if name == "minecraft:comparator":
                for sd in sides_of(d):
                    sides[add(pos, sd)] = pos
        return backs, sides

    def solid(self, pos):
        s = self.blocks.get(pos)
        if s is None:
            return False
        return M.is_solid({pos: parse(s)}, pos)


def _tuple_cells(blocks):
    return {tuple(r[:3]): r[3] for r in blocks}


def _barrel_map(d):
    return {tuple(int(v) for v in k.split(",")): int(n)
            for k, n in (d or {}).items()}


def tiled(blocks, barrels, pitch, n):
    b, ba = {}, {}
    for i in range(n):
        for pos, s in blocks.items():
            b[(pos[0] + i * pitch, pos[1], pos[2])] = s
        for pos, c in barrels.items():
            ba[(pos[0] + i * pitch, pos[1], pos[2])] = c
    return b, ba


def artifact_from_slice(name, lay, n):
    S = lay["slice"]
    px = int(S["pitch"])
    blocks, barrels = tiled(_tuple_cells(lay["blocks"]),
                            _barrel_map(lay.get("barrels")), px, n)
    ports = S["ports"]

    def shift(cell, i):
        return (cell[0] + i * px, cell[1], cell[2])

    pins = {"P": {"cells": [tuple(c) for c in S["through"]["P"]],
                  "kind": "ctrl", "levels": [0, 15]},
            "Wn": {"cells": [tuple(c) for c in S["through"]["Wn"]],
                   "kind": "ctrl", "levels": [0, 15]},
            "k": {"cells": [tuple(ports["k"])], "kind": "data",
                  "levels": [0, 3]}}
    for i in range(n):
        pins["a%d" % i] = {"cells": [shift(ports["a"], i)], "kind": "data",
                           "levels": [0, 3]}
        pins["b%d" % i] = {"cells": [shift(ports["b"], i)], "kind": "data",
                           "levels": [0, 3]}
    reads = {"f": {"cell": shift(ports["f"], n - 1), "levels": [0, 3]},
             "thrP": {"cell": shift(S["through"]["P"][0], 1), "levels": [0, 15]},
             "thrWn": {"cell": shift(S["through"]["Wn"][0], 1),
                       "levels": [0, 15]}}
    for i in range(n):
        reads["r%d" % i] = {"cell": shift(ports["r"], i), "levels": [0, 3]}
    for i in range(1, n):
        reads["carry%d" % i] = {"cell": shift(ports["k"], i), "levels": [0, 3]}
    return Artifact(name, blocks, barrels, pins, reads, rows_alu(n),
                    "alu_slice_n%d" % n)


def artifact_from_stage(name, lay):
    blocks = _tuple_cells(lay["blocks"])
    barrels = _barrel_map(lay.get("barrels"))
    pins = {}
    for pin, cells in lay["pins"].items():
        cells = [tuple(c) for c in cells]
        if pin in ("P", "Wn"):
            pins[pin] = {"cells": cells, "kind": "ctrl", "levels": [0, 15]}
        else:
            key = {"a": "a0", "b": "b0"}.get(pin, pin)
            pins[key] = {"cells": cells, "kind": "data", "levels": [0, 3]}
    reads = {"r0": {"cell": tuple(lay["reads"]["r"]), "levels": [0, 3]},
             "f": {"cell": tuple(lay["reads"]["f"]), "levels": [0, 3]}}
    rows = []
    for row in rows_alu(1):
        exp = {"r0": row["expect"]["r0"], "f": row["expect"]["f"]}
        rows.append({"name": row["name"], "pins": row["pins"], "expect": exp,
                     "key": row["key"]})
    return Artifact(name, blocks, barrels, pins, reads, rows, "alu_stage")


def artifact_from_placer0(name, prob, sol):
    blocks = _tuple_cells(prob["fixed"])
    for r in sol["blocks"]:
        p = tuple(r[:3])
        if p in blocks:
            raise FeedError("%s: solution cell %s overlaps a fixed cell"
                            % (name, p))
        blocks[p] = r[3]
    barrels = _barrel_map(prob.get("barrels"))
    barrels.update(_barrel_map(sol.get("barrels")))
    pins = {}
    for pin, d in prob["pins"].items():
        levels = [int(v) for v in d["levels"]]
        kind = "ctrl" if max(levels) > 3 else "data"
        pins[pin] = {"cells": [tuple(d["cell"])], "kind": kind,
                     "levels": levels}
    rows = rows_expect(prob["pins"], prob["outputs"])
    reads = {}
    for o in prob["outputs"]:
        seen = sorted({row["expect"][o["name"]] for row in rows})
        reads[o["name"]] = {"cell": tuple(o["cell"]), "levels": seen}
    return Artifact(name, blocks, barrels, pins, reads, rows, "placer0")


def load_artifact(entry, job_dir):
    def rel(p):
        p = Path(p)
        return p if p.is_absolute() else (job_dir / p)

    req = entry.get("require") or {}
    if "problem" in entry:
        probs = {p["name"]: p for p in
                 json.loads(rel(entry["problem"]).read_text(encoding="utf-8"))}
        pname = entry.get("problem_name") or entry["name"]
        if pname not in probs:
            raise FeedError("no problem named %r in %s" % (pname, entry["problem"]))
        sol = json.loads(rel(entry["solution"]).read_text(encoding="utf-8"))
        return artifact_from_placer0(entry["name"], probs[pname], sol)
    lay = json.loads(rel(entry["layout"]).read_text(encoding="utf-8"))
    kind = req.get("kind")
    if kind is None:
        kind = "alu_slice" if "slice" in lay else "alu_stage"
    if kind == "alu_slice":
        n = int(req.get("n", entry.get("n", 2)))
        return artifact_from_slice(entry["name"], lay, n)
    if kind == "alu_stage":
        return artifact_from_stage(entry["name"], lay)
    if kind == "expect":
        prob = {"fixed": lay["blocks"], "barrels": lay.get("barrels"),
                "pins": req["pins"], "outputs": req["outputs"]}
        return artifact_from_placer0(entry["name"], prob, {"blocks": []})
    raise FeedError("unknown require.kind %r" % (kind,))


# --- the readout wire in front of an output comparator ----------------------

def add_readout(art):
    """Every read that lands on a comparator gets a wire in its output cell.

    A world reads block states; a comparator's output level is not one.  The
    wire (and its support, if that cell is air) is added and the read moved on
    to it.  Whether the addition is free is settled by the same global check
    as everything else."""
    added = {}
    for name, r in sorted(art.reads.items()):
        cell = tuple(r["cell"])
        s = art.blocks.get(cell)
        if s is None:
            raise FeedError("%s: read %s at %s is not a layout cell"
                            % (art.name, name, list(cell)))
        bname, props = parse(s)
        if bname == CC.DUST:
            continue
        if bname != CC.COMPARATOR:
            raise FeedError("%s: read %s at %s is %s, neither wire nor "
                            "comparator" % (art.name, name, list(cell), bname))
        front = add(cell, M.OPPOSITE[props["facing"]])
        if front in art.blocks:
            raise FeedError("%s: the output cell %s of read %s holds %s, so no "
                            "readout wire fits" % (art.name, list(front), name,
                                                   art.blocks[front]))
        art.blocks[front] = DUST
        added[front] = DUST
        sup = below(front)
        if sup not in art.blocks:
            art.blocks[sup] = STONE
            added[sup] = STONE
        elif not art.solid(sup):
            raise FeedError("%s: readout wire %s has no support"
                            % (art.name, list(front)))
        r["cell"] = front
        r["comparator"] = list(cell)
    return added


# --- feeder search ----------------------------------------------------------

class Candidate(object):
    def __init__(self, kind, cells, lever, pin, cell, note):
        self.kind = kind                  # "data" / "ctrl"
        self.cells = cells                # [(pos, state)] -- the NEW cells
        self.lever = lever                # pos of the lever
        self.pin = pin
        self.cell = cell                  # the pin cell it feeds
        self.note = note                  # how it reaches the pin
        self.subst = ()                   # layout cells this feeder takes over

    def barrels(self):
        return {pos: L3 for pos, s in self.cells if s == BARREL}

    def as_json(self):
        return {"pin": self.pin, "cell": list(self.cell), "kind": self.kind,
                "note": self.note, "lever": list(self.lever),
                "cells": [[list(p), s] for p, s in self.cells],
                "substitutions": [list(p) for p in sorted(self.subst)]}


def _need(cells, pos, state, out):
    """Ask for `state` at `pos`; a cell asked for twice must agree."""
    if pos in cells and cells[pos] != state:
        return False
    cells[pos] = state
    out.append(pos)
    return True


def data_candidates(art, cell, occupied, max_drop=2):
    """Every data feeder shape that could deliver into `cell`, best first.

    Two targets: the pin wire itself (the gate's output cell IS the pin), and
    -- when every horizontal neighbour of the pin is taken -- the SUPPORT
    BLOCK under the pin, which a comparator's front strongly powers at its own
    output level, so the dust above reads it (WORLD-2's a1 / a2)."""
    targets = [(cell, "direct")]
    sup = below(cell)
    if art.solid(sup):
        targets.append((sup, "under"))
    for target, note in targets:
        for d in HORIZ:
            gate = add(target, d)
            back = add(gate, d)
            for sd in sides_of(d):
                side = add(gate, sd)
                for wires, base in _lever_paths(art, side, gate, occupied,
                                                max_drop):
                    cells = {}
                    order = []
                    ok = (_need(cells, gate,
                                "minecraft:comparator[facing=%s,mode=compare]" % d,
                                order)
                          and _need(cells, back, BARREL, order))
                    for w in wires:
                        ok = ok and _need(cells, w, DUST, order)
                    ok = ok and _need(cells, base, STONE, order)
                    ok = ok and _need(cells, above(base), LEVER, order)
                    if not ok:
                        continue
                    for p in [gate] + list(wires):
                        s = below(p)
                        if s in cells:
                            continue
                        if not art.solid(s) and s not in art.blocks:
                            cells[s] = STONE
                            order.append(s)
                    yield Candidate("data", [(p, cells[p]) for p in order],
                                    above(base), None, cell,
                                    "%s gate %s facing=%s" % (note, list(gate), d))


def _lever_paths(art, side, gate, occupied, max_drop):
    """Wire runs from the gate's side cell to a lever base.

    Shortest first: the side cell with a base beside it.  Then runs that drop
    diagonally away (WORLD-2's a1, where every y+1 cell above the free floor
    was a stage block and no lever fitted at the gate's level).  A dust reads
    a strongly powered base at 15 and loses one level per cell, so any run of
    at most 11 cells still delivers >= 4 and kills a level-3 back."""
    for b in HORIZ:
        base = add(side, b)
        if base != gate:
            yield ([side], base)
    seen = {side}
    frontier = [[side]]
    for _ in range(max_drop):
        nxt = []
        for path in frontier:
            last = path[-1]
            for h in HORIZ:
                step = below(add(last, h))
                if step in seen or add(last, h) in art.blocks:
                    continue          # the cell it drops past must be air
                run = path + [step]
                nxt.append(run)
                for b in HORIZ:
                    base = add(step, b)
                    if base != last:
                        yield (run, base)
        frontier = nxt
        seen |= {p[-1] for p in frontier}


def ctrl_candidates(art, cell, occupied):
    """A solid base beside the pin wire with a `face=floor` lever on top."""
    for d in HORIZ:
        base = add(cell, d)
        yield Candidate("ctrl", [(base, STONE), (above(base), LEVER)],
                        above(base), None, cell, "base %s" % (list(base),))


def substitutable(art, pos):
    """May a feeder cell take over this layout cell?

    Only an INERT solid floor block: it supports nothing (the cell above is
    air) and it touches no redstone at all, so nothing in the layout can tell
    the difference.  This is WORLD-2's a2 substitution, stated as a rule
    instead of as a hand-picked pair of cells; every substitution is listed in
    the report and the fed layout is checked as a whole afterwards."""
    s = art.blocks.get(pos)
    if s is None or not art.solid(pos) or parse(s)[0] != STONE:
        return False
    if above(pos) in art.blocks:
        return False
    for d in M.FACES:
        n = art.blocks.get(add(pos, d))
        if n is not None and parse(n)[0] != STONE:
            return False
    return True


def geometric_reject(art, cand, occupied, backs, sides, allow_subst=False):
    """None if the candidate clears conditions (1)-(3), else (reason, detail)."""
    placed = {pos for pos, _ in cand.cells}
    subst = set()
    for pos, state in cand.cells:
        if pos in art.blocks:
            if allow_subst and substitutable(art, pos):
                subst.add(pos)
                continue
            return ("collision", "%s holds %s" % (list(pos), art.blocks[pos]))
        if pos in occupied:
            return ("collision", "%s is taken by feeder %s"
                    % (list(pos), occupied[pos]))
        if pos in backs:
            return ("side_or_back", "%s is the BACK of the gate at %s"
                    % (list(pos), list(backs[pos])))
        if pos in sides:
            return ("side_or_back", "%s is a SIDE of the comparator at %s"
                    % (list(pos), list(sides[pos])))
    final = dict(cand.cells)
    for pos, state in cand.cells:
        if state in (DUST, LEVER) or state.startswith("minecraft:comparator"):
            s = below(pos)
            got = final.get(s, art.blocks.get(s))
            if got is None or not M.is_solid({s: parse(got)}, s):
                return ("support", "%s (%s) stands on %s"
                        % (list(pos), state.split("[")[0], got or "air"))
    cand.subst = tuple(sorted(subst))
    return None


class Searcher(object):
    """The feeder search over one artifact, with its reference solutions."""

    def __init__(self, art, verbose=False):
        self.art = art
        self.verbose = verbose
        self.backs, self.sides = art.gate_backs_sides()
        self.occupied = {}
        self._ref = {}
        self.blocks = dict(art.blocks)       # the layout plus accepted feeders
        self.barrels = dict(art.barrels)
        self.fed = {}                        # {pin cell: accepted candidate}
        self.subst = set()
        self.envs = self._probe_envs()

    def _probe_envs(self):
        """The pin environments a candidate is judged in.

        One feeder can disturb the layout only in some rows -- WORLD-2's a1
        side wire read 9 from a stage comparator, and only when that gate was
        lit.  So a candidate is judged with the other pins at their lowest, at
        their highest, and at the first row's values, and the whole fed layout
        is checked over EVERY row afterwards."""
        pins = self.art.pins
        lo = {p: min(d["levels"]) for p, d in pins.items()}
        hi = {p: max(d["levels"]) for p, d in pins.items()}
        envs, seen = [], set()
        for env in (dict(self.art.rows[0]["pins"]), lo, hi):
            key = tuple(sorted(env.items()))
            if key not in seen:
                seen.add(key)
                envs.append(env)
        return envs

    def _floors(self, env, skip=()):
        floors = {}
        for pin, d in self.art.pins.items():
            for c in d["cells"]:
                c = tuple(c)
                if c in self.fed or c in skip:
                    continue                 # this cell has a feeder now
                floors[c] = int(env[pin])
        return floors

    def _levers(self, env, extra=None):
        out = {}
        for cell, cand in self.fed.items():
            level = int(env[cand.pin])
            out[cand.lever] = ((level == 0) if cand.kind == "data"
                               else (level != 0))
        if extra:
            out.update(extra)
        return out

    def reference(self, env):
        """The layout as the CHECKER sees it: every unfed pin cell pinned, every
        accepted feeder in place and set for this row."""
        key = (tuple(sorted(env.items())), len(self.fed))
        if key not in self._ref:
            b = bench_of(self.blocks, self.barrels, floors=self._floors(env),
                         levers=self._levers(env))
            b.dc_solve()
            cells = [p for p in sorted(self.art.blocks) if p not in self.subst]
            self._ref[key] = (cells, state_map(b, cells))
        return self._ref[key]

    def electrical_reject(self, cand, pin):
        """Solve the layout WITH the candidate, at both of the pin's levels.

        The pin cell must read exactly the level the convention promises, and
        every other layout cell must hold exactly the state it holds when the
        checker PINS that cell instead -- which is what "touches no layout
        wire, no gate side and no gate back" means when it is measured rather
        than eyeballed."""
        art = self.art
        levels = art.pins[pin]["levels"]
        blocks = dict(self.blocks)
        for pos, s in cand.cells:
            blocks[pos] = s
        barrels = dict(self.barrels)
        barrels.update(cand.barrels())
        benches = []
        for env0 in self.envs:
            for level in levels:
                env = dict(env0)
                env[pin] = level
                cells, ref = self.reference(env)
                floors = self._floors(env, skip=(tuple(cand.cell),))
                on = (level == 0) if cand.kind == "data" else (level != 0)
                b = bench_of(blocks, barrels, floors=floors,
                             levers=self._levers(env, {cand.lever: on}))
                # cold first: a candidate that already disagrees is rejected
                # for one solve; only a survivor pays for the hot seed
                rounds, conv = b.dc_solve()
                if not conv:
                    return ("electrical", "did not converge at %s=%d"
                            % (pin, level))
                got = level_at(b, cand.cell)
                if got != level:
                    return ("electrical", "pin cell %s reads %s, wanted %d "
                            "(lever %s, %s)" % (list(cand.cell), got, level,
                                                "ON" if on else "OFF", env))
                now = state_map(b, [p for p in cells if p not in cand.subst])
                for pos in cells:
                    if pos in cand.subst:
                        continue
                    if now[pos] != ref[pos]:
                        return ("electrical", "%s becomes %s where the pinned "
                                "layout has %s (%s=%d, %s)"
                                % (list(pos), now[pos], ref[pos], pin, level,
                                   env))
                benches.append((level, b))
        for level, b in benches:
            rounds, conv, conv_hot, diff = b.dc_solve_both()
            if not conv or not conv_hot:
                return ("electrical", "did not converge at %s=%d" % (pin, level))
            if diff:
                return ("bistable", "cold and hot DC differ at %s (%s=%d)"
                        % ([list(p) for p in sorted(diff)][:3], pin, level))
        return None

    def accept(self, cand):
        for pos, s in cand.cells:
            if pos in self.art.blocks:
                self.subst.add(pos)
            self.blocks[pos] = s
        self.barrels.update(cand.barrels())
        self.fed[tuple(cand.cell)] = cand
        self._ref.clear()

    def search_cell(self, pin, cell, limit=400):
        """Accept the first candidate that clears all four conditions.

        Two passes: first refusing to touch any layout cell at all, and only
        then allowing an INERT floor block to be substituted (`substitutable`).
        A layout that can be fed without being touched always is."""
        art = self.art
        kind = art.pins[pin]["kind"]
        reasons, tried = [], 0
        for allow_subst in (False, True):
            gen = (data_candidates(art, cell, self.occupied) if kind == "data"
                   else ctrl_candidates(art, cell, self.occupied))
            for cand in gen:
                cand.pin = pin
                bad = geometric_reject(art, cand, self.occupied, self.backs,
                                       self.sides, allow_subst)
                if bad is None:
                    tried += 1
                    bad = self.electrical_reject(cand, pin)
                    if bad is None:
                        return cand, reasons
                reasons.append({"cells": [list(p) for p, _ in cand.cells],
                                "note": cand.note, "reason": bad[0],
                                "detail": bad[1], "subst": allow_subst})
                if tried >= limit:
                    reasons.append({"cells": [], "note": "search stopped",
                                    "reason": "limit",
                                    "detail": "%d candidates solved" % tried})
                    return None, reasons
        return None, reasons

    def run(self):
        art = self.art
        failures = {}
        for pin in sorted(art.pins):
            art.feeders[pin] = []
            for i, cell in enumerate(art.pins[pin]["cells"]):
                cell = tuple(cell)
                cand, reasons = self.search_cell(pin, cell)
                if cand is None:
                    summary = {}
                    for r in reasons:
                        summary[r["reason"]] = summary.get(r["reason"], 0) + 1
                    failures[pin] = {"cell": list(cell), "tried": len(reasons),
                                     "reasons": summary,
                                     "examples": reasons[:8]}
                    break
                name = "%s_%d" % (pin, i)
                self.occupied.update({p: name for p, _ in cand.cells})
                art.levers[name] = cand.lever
                cand.lever_name = name
                art.feeders[pin].append(cand)
                self.accept(cand)
                if self.verbose:
                    print("  %-6s %-14s %s%s"
                          % (pin, list(cell), cand.note,
                             (" subst %s" % [list(p) for p in cand.subst])
                             if cand.subst else ""))
        return failures


def apply_feeders(art):
    """The fed layout: the artifact plus every accepted feeder."""
    blocks = dict(art.blocks)
    barrels = dict(art.barrels)
    for pin in art.feeders:
        for cand in art.feeders[pin]:
            for pos, s in cand.cells:
                blocks[pos] = s
            barrels.update(cand.barrels())
    return blocks, barrels


def lever_values(art, pins):
    """{lever name: bool ON} for one row.  Data ON = 0; control ON = 15."""
    out = {}
    for pin, cands in art.feeders.items():
        level = int(pins[pin])
        for cand in cands:
            out[cand.lever_name] = ((level == 0) if cand.kind == "data"
                                    else (level != 0))
    return out


# --- global Bench verification ---------------------------------------------

def verify(art, blocks, barrels):
    """Every row of the requirement, solved on the fed layout."""
    gates = {}
    for pos, s in sorted(blocks.items()):
        name, props = parse(s)
        if name in GATES:
            gates["%s%d_%d_%d" % ("c" if name == CC.COMPARATOR else "d",
                                  pos[0], pos[1], pos[2])] = pos
    art.gates = gates
    out = []
    for row in art.rows:
        levers = {art.levers[nm]: on
                  for nm, on in lever_values(art, row["pins"]).items()}
        b = bench_of(blocks, barrels, levers=levers)
        rounds, conv, conv_hot, diff = b.dc_solve_both()
        got = {nm: level_at(b, r["cell"]) for nm, r in art.reads.items()}
        equal = {nm: got[nm] == row["expect"][nm] for nm in row["expect"]}
        gs = {}
        for nm, pos in gates.items():
            name, props = b.blocks[pos]
            gs[nm] = (bool(b.cmp_out.get(pos, 0) > 0) if name == CC.COMPARATOR
                      else props["powered"] == "true")
        out.append({"row": row["name"], "key": row["key"], "pins": row["pins"],
                    "levers_on": lever_values(art, row["pins"]),
                    "got": got, "expect": row["expect"], "equal": equal,
                    "gates": gs, "rounds": rounds,
                    "converged": bool(conv and conv_hot),
                    "bistable": [list(p) for p in sorted(diff)][:4],
                    "ok": bool(conv and conv_hot and not diff
                               and all(equal.values()))})
    return out


# --- the world --------------------------------------------------------------

def pack(arts, gap=12):
    """Lay the artifacts out along z, `gap` empty cells between them."""
    z = 0
    for art in arts:
        blocks, _ = apply_feeders(art)
        zs = [p[2] for p in blocks]
        art.origin = [0, 0, z - min(zs)]
        z = art.origin[2] + max(zs) + 1 + gap
    return z


def world_cells(arts, base):
    placements, entities, owner = {}, {}, {}
    for art in arts:
        blocks, barrels = apply_feeders(art)
        art.fed_blocks, art.fed_barrels = blocks, barrels
        for pos, s in blocks.items():
            w = world_pos(base, art, pos)
            if w in placements:
                raise FeedError("%s: world cell %s is already %s's"
                                % (art.name, list(w), owner[w]))
            placements[w] = parse(s)
            owner[w] = art.name
        for pos, n in barrels.items():
            w = world_pos(base, art, pos)
            if placements[w][0] != "minecraft:barrel":
                raise FeedError("%s: %s is %s, not a barrel"
                                % (art.name, list(w), placements[w][0]))
            entities[w] = barrel_entity(w, n)
    return placements, entities


def world_pos(base, art, rel):
    o = art.origin
    return (base[0] + o[0] + rel[0], base[1] + o[1] + rel[1],
            base[2] + o[2] + rel[2])


def build_world(placements, entities, out_dir, name):
    """The four-line worldgen idiom, with the block-entity map filled in.

    `synthworld.build_world` passes `{}` there, and every artifact here is
    defined by barrels whose item counts ARE its constants."""
    out_dir = Path(out_dir)
    if out_dir.exists():
        raise FeedError("refusing to overwrite %s" % out_dir)
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
    return {"world_dir": str(world_dir), "blocks": len(placements),
            "block_entities": len(entities),
            "regions": ["r.%d.%d.mca" % k for k in sorted(regions)],
            "data_version": version}


# --- specs ------------------------------------------------------------------

def est_rcon(n_state, n_nbt, n_drives, max_gt, n_regimes):
    per = ((max_gt + 1) * n_state + 3 * max_gt + 8 * n_drives + 2 * n_nbt)
    return per, per * n_regimes + 64


def specs_for(art, arts, base, world_dir, out_dir, template, port, max_gt,
              settle_gt, max_rcon):
    """One or more worldprobe specs driving every row of ONE artifact.

    Every other artifact is held at its own first row: it is not read here, so
    whether it is warm is not this spec's question (WORLD-4 section 8.2: an
    artifact that is merely held while another sweeps has NOT been warmed, so
    it is never read from another artifact's spec)."""
    drives, defaults = {}, {}
    for other in arts:
        for nm, pos in other.levers.items():
            key = "%s__%s" % (other.name, nm)
            drives[key] = {"kind": "lever",
                           "pos": list(world_pos(base, other, pos)),
                           "face": "floor", "facing": "north"}
        if other is not art:
            for nm, on in lever_values(other, other.rows[0]["pins"]).items():
                defaults["%s__%s" % (other.name, nm)] = int(on)

    reads, bit = [], 0
    for nm in sorted(art.reads):
        r = art.reads[nm]
        for lv in r["levels"]:
            reads.append({"name": "%s_%d" % (nm, lv),
                          "pos": list(world_pos(base, art, r["cell"])),
                          "bit": bit,
                          "match": "minecraft:redstone_wire[power=%d]" % lv})
            bit += 1
    for gname in sorted(art.gates):
        block = ("minecraft:comparator[powered=true]" if gname.startswith("c")
                 else "minecraft:repeater[powered=true]")
        reads.append({"name": gname,
                      "pos": list(world_pos(base, art, art.gates[gname])),
                      "match": block})
    n_nbt = 0
    for pos, n in sorted(art.fed_barrels.items()):
        if n == L3 and pos not in art.barrels:
            reads.append({"name": "barrel_slot3", "kind": "nbt",
                          "pos": list(world_pos(base, art, pos)),
                          "path": "Items[3]"})
            n_nbt = 1
            break

    n_state = len(reads) - n_nbt
    rows = art.verified
    per, _ = est_rcon(n_state, n_nbt, len(drives), max_gt, 1)
    # MARGIN, calibrated 2026-09-08 against two runs of this same shape: the
    # estimate was 0.25% high on `slice_v9_n2_3` (553,302 vs 551,896) and 0.7%
    # LOW on `p14_n2_1`, which tripped the ceiling on its last regime and threw
    # the whole run away -- the drive phase costs more than `8 x drives` when
    # many levers move. A run that trips the limit is a total loss, an extra
    # chunk costs one world load, so the estimate is taken at +5%.
    per = int(per * 1.05) + 1
    chunks = 1
    while True:
        biggest = max(len([r for i, r in enumerate(rows) if i % chunks == c])
                      for c in range(chunks))
        if per * (2 * biggest + 2) + 64 <= max_rcon or chunks > 32:
            break
        chunks += 1

    specs = []
    for c in range(chunks):
        mine = [r for i, r in enumerate(rows) if i % chunks == c]
        regimes = []
        for wake, on in (("wake_on", 1), ("wake_off", 0)):
            regimes.append({"name": wake, "inputs": {k: on for k in drives},
                            "max_gt": max_gt, "settle_gt": settle_gt})
        for label, compare in (("warm", False), ("v", True)):
            for row in mine:
                inputs = dict(defaults)
                inputs.update({"%s__%s" % (art.name, nm): int(on)
                               for nm, on in row["levers_on"].items()})
                reg = {"name": "%s_%s" % (label, row["row"]), "inputs": inputs,
                       "max_gt": max_gt, "settle_gt": settle_gt}
                if compare:
                    reg["expect"] = expect_of(art, reads, row)
                regimes.append(reg)
        name = art.name if chunks == 1 else "%s_%d" % (art.name, c + 1)
        specs.append({"name": name,
                      "world": {"template": str(template),
                                "world_dir": str(world_dir),
                                "bbox": {"min": BBOX[0], "max": BBOX[1]}},
                      "server": {"host": "127.0.0.1", "rcon_port": int(port),
                                 "java_xmx": "3G"},
                      "drives": drives, "reads": reads, "regimes": regimes,
                      "limits": {"max_rcon": int(max_rcon)},
                      "out_dir": str(out_dir)})
    return specs, per


def expect_of(art, reads, row):
    final, value = {}, 0
    for r in reads:
        if r.get("kind") == "nbt":
            continue
        nm = r["name"]
        if nm in art.gates:
            final[nm] = bool(row["gates"][nm])
            continue
        base, lv = nm.rsplit("_", 1)
        on = (row["got"][base] == int(lv))
        final[nm] = on
        if on and "bit" in r:
            value |= 1 << r["bit"]
    return {"final_value": value, "final_reads": final}


# --- running ----------------------------------------------------------------

def run_spec(spec_path, run_dir, python=None):
    # `worldprobe.provision` refuses an existing run dir, so a retry after a
    # host-side failure (a JVM that could not get its memory, 2026-09-08) takes
    # the next free name instead of stepping on the evidence of the first try.
    run_dir = Path(run_dir)
    n, base = 1, run_dir
    while run_dir.exists():
        n += 1
        run_dir = base.parent / ("%s_try%d" % (base.name, n))
    cmd = [python or sys.executable, str(HERE / "worldprobe.py"), "run",
           "--spec", str(spec_path), "--run-dir", str(run_dir)]
    t0 = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return {"cmd": cmd, "returncode": proc.returncode,
            "wall_s": round(time.time() - t0, 1),
            "stdout": proc.stdout[-4000:], "stderr": proc.stderr[-4000:]}


def table_row(art, pairs):
    """One artifact's reading, from the worldprobe results only.

    `pairs` is [(spec path, result path)]; every number below is read out of
    the result file, and the counterexample's cell out of the spec that asked
    for it."""
    n_bench_ok = sum(1 for r in art.verified if r["ok"])
    rows = fails = points = bad_points = rcon = 0
    settle, unsettled, first = [], 0, None
    for spec_path, res_path in pairs:
        spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
        cells = {r["name"]: r["pos"] for r in spec["reads"]}
        res = json.loads(Path(res_path).read_text(encoding="utf-8"))
        rcon += res.get("rcon", {}).get("roundtrips", 0)
        for rec in res.get("regimes", []):
            if not rec["name"].startswith("v_"):
                continue
            rows += 1
            fr = (rec.get("expect") or {}).get("final_reads") or {}
            bad = sorted(k for k, v in fr.items() if not v["equal"])
            points += len(fr)
            bad_points += len(bad)
            if bad:
                fails += 1
                if first is None:
                    k = bad[0]
                    first = {"regime": rec["name"], "read": k,
                             "cell": cells.get(k),
                             "expected": fr[k]["expected"], "got": fr[k]["got"],
                             "other_reads": bad[1:6]}
            if rec.get("first_stable_gt") is None:
                unsettled += 1
            else:
                settle.append(rec["first_stable_gt"])
    return {"artifact": art.name, "kind": art.kind,
            "bench": "%d/%d" % (n_bench_ok, len(art.verified)),
            "world_rows": rows, "world_fail": fails, "read_points": points,
            "mismatch": ("--" if points == 0
                         else "%d/%d" % (bad_points, points)),
            "settle_gt": ("%s..%s (%d unsettled)"
                          % (min(settle) if settle else "-",
                             max(settle) if settle else "-", unsettled)),
            "blocks": len(art.fed_blocks), "rcon": rcon,
            "first_counterexample": first}


def tables_md(job_name, report):
    lines = ["# feed.py -- %s" % job_name, "",
             "Readings copied from `worldprobe` result files; nothing retyped.",
             "", "## artifacts", "",
             "| artifact | kind | Bench | world rows | world FAIL | read points"
             " | mismatch | settle gt | blocks | rcon |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for r in report["table"]:
        lines.append("| %s | %s | %s | %d | %d | %d | %s | %s | %d | %d |"
                     % (r["artifact"], r["kind"], r["bench"], r["world_rows"],
                        r["world_fail"], r["read_points"], r["mismatch"],
                        r["settle_gt"], r["blocks"], r["rcon"]))
    lines.append("")
    for r in report["table"]:
        if r["first_counterexample"]:
            lines += ["first counterexample, %s: `%s`"
                      % (r["artifact"], json.dumps(r["first_counterexample"])),
                      ""]
    if report.get("runs"):
        lines += ["## runs", "", "| spec | wall s | rcon | returncode |",
                  "|---|---|---|---|"]
        for run in report["runs"]:
            lines.append("| %s | %s | %s | %d |"
                         % (run["spec"], run["wall_s"], run.get("rcon", "--"),
                            run["returncode"]))
        lines.append("")
    return "\n".join(lines)


# --- driver -----------------------------------------------------------------

def load_job(paths, out_dir):
    """A JOB file, or bare layout paths turned into a one-entry job each."""
    if len(paths) == 1 and paths[0].lower().endswith(".json"):
        raw = json.loads(Path(paths[0]).read_text(encoding="utf-8"))
        if isinstance(raw, dict) and "artifacts" in raw:
            return raw, Path(paths[0]).resolve().parent
    arts = [{"name": Path(p).stem, "layout": str(Path(p).resolve())}
            for p in paths]
    return {"name": "feed", "artifacts": arts}, Path.cwd()


def main(argv=None):
    global BBOX
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("job", nargs="+", help="a JOB json, or layout json(s)")
    ap.add_argument("--out", required=True, help="run directory (must not exist)")
    ap.add_argument("--run", action="store_true", help="drive the world too")
    ap.add_argument("--rcon-port", type=int, default=25598)
    ap.add_argument("--base", default="100,64,100")
    ap.add_argument("--template",
                    default=r"<host-path>/carpet-work")
    ap.add_argument("--max-gt", type=int, default=40)
    ap.add_argument("--settle-gt", type=int, default=SW.SETTLE_GT)
    ap.add_argument("--max-rcon", type=int, default=600000)
    ap.add_argument("--out-dir", default=None,
                    help="where the specs and results go (default: --out)")
    ap.add_argument("--dry-run", action="store_true",
                    help="search and verify, write no world")
    ap.add_argument("--resume", action="store_true",
                    help="reuse the world already under --out and skip every "
                         "spec whose result file says completed")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    job, job_dir = load_job(args.job, args.out)
    out = Path(args.out)
    reports = Path(args.out_dir) if args.out_dir else out
    base = tuple(int(v) for v in args.base.split(","))
    report = {"job": job.get("name", "feed"), "artifacts": [], "runs": [],
              "table": [], "refused": None}

    arts = []
    for entry in job["artifacts"]:
        art = load_artifact(entry, job_dir)
        added = add_readout(art)
        print("%-16s cells %4d rows %3d pins %s"
              % (art.name, art.n_artifact_cells, len(art.rows),
                 ",".join(sorted(art.pins))))
        s = Searcher(art, verbose=args.verbose)
        failures = s.run()
        rec = {"name": art.name, "kind": art.kind,
               "artifact_cells": art.n_artifact_cells,
               "readout_added": [[list(p), v] for p, v in added.items()],
               "rows": len(art.rows),
               "feeders": [c.as_json() for pin in sorted(art.feeders)
                           for c in art.feeders[pin]],
               "levers": {k: list(v) for k, v in art.levers.items()}}
        if failures:
            rec["refused"] = failures
            report["artifacts"].append(rec)
            report["refused"] = {"artifact": art.name, "pins": failures}
            print("REFUSED %s: no feeder for %s"
                  % (art.name, ", ".join(sorted(failures))))
            for pin, info in sorted(failures.items()):
                print("  %s at %s: %d candidates, %s"
                      % (pin, info["cell"], info["tried"],
                         ", ".join("%s x%d" % kv
                                   for kv in sorted(info["reasons"].items()))))
                for ex in info["examples"][:4]:
                    print("     %-12s %s" % (ex["reason"], ex["detail"]))
            write_report(reports, job, report)
            return 2
        blocks, barrels = apply_feeders(art)
        art.fed_blocks, art.fed_barrels = blocks, barrels
        art.verified = verify(art, blocks, barrels)
        n_ok = sum(1 for r in art.verified if r["ok"])
        rec["bench_pass"] = "%d/%d" % (n_ok, len(art.verified))
        bad = [r for r in art.verified if not r["ok"]]
        print("  feeders %d levers %d cells %d -> Bench %s"
              % (len(rec["feeders"]), len(art.levers), len(blocks),
                 rec["bench_pass"]))
        if bad:
            rec["refused"] = {"bench": [
                {"row": r["row"], "got": r["got"], "expect": r["expect"],
                 "bistable": r["bistable"], "converged": r["converged"]}
                for r in bad[:8]]}
            report["artifacts"].append(rec)
            report["refused"] = {"artifact": art.name,
                                 "bench_fail": len(bad),
                                 "first": rec["refused"]["bench"][0]}
            first = bad[0]
            print("REFUSED %s: Bench %s; first %s %s got %s expect %s%s"
                  % (art.name, rec["bench_pass"], first["row"],
                     "BISTABLE" if first["bistable"] else "",
                     first["got"], first["expect"],
                     (" at %s" % first["bistable"]) if first["bistable"] else ""))
            write_report(reports, job, report)
            return 3
        report["artifacts"].append(rec)
        arts.append(art)

    pack(arts)
    placements, entities = world_cells(arts, base)
    BBOX = ([min(p[i] for p in placements) - 1 for i in range(3)],
            [max(p[i] for p in placements) + 1 for i in range(3)])
    report["world"] = {"bbox": [BBOX[0], BBOX[1]],
                       "origins": {a.name: a.origin for a in arts}}
    if args.dry_run:
        print("dry run: %d blocks, %d block entities, bbox %s %s"
              % (len(placements), len(entities), BBOX[0], BBOX[1]))
        write_report(reports, job, report)
        return 0

    out.mkdir(parents=True, exist_ok=True)
    built = out / "world_build"
    if args.resume and built.exists():
        info = {"world_dir": str(built / "world"), "blocks": len(placements),
                "block_entities": len(entities), "reused": True,
                "regions": sorted(p.name for p in
                                  (built / "world" / "region").glob("*.mca")),
                "data_version": worldgen.DEFAULT_DATA_VERSION}
    else:
        info = build_world(placements, entities, built,
                           job.get("name", "feed"))
    report["world"].update(info)
    print("world %s blocks %d block_entities %d regions %s"
          % (info["world_dir"], info["blocks"], info["block_entities"],
             info["regions"]))

    reports.mkdir(parents=True, exist_ok=True)
    all_specs = []
    for art in arts:
        specs, per = specs_for(art, arts, base, info["world_dir"], reports,
                               args.template, args.rcon_port, args.max_gt,
                               args.settle_gt, args.max_rcon)
        for spec in specs:
            path = reports / (spec["name"] + ".spec.json")
            path.write_bytes((json.dumps(spec, indent=1) + "\n").encode("utf-8"))
            _, tot = est_rcon(len([r for r in spec["reads"]
                                   if r.get("kind", "state") == "state"]),
                              len([r for r in spec["reads"]
                                   if r.get("kind") == "nbt"]),
                              len(spec["drives"]), args.max_gt,
                              len(spec["regimes"]))
            print("%-20s reads %3d regimes %3d rcon/regime ~%d total ~%d of %d"
                  % (spec["name"], len(spec["reads"]), len(spec["regimes"]),
                     per, tot, args.max_rcon))
            all_specs.append((art, path, tot))
    report["specs"] = [{"artifact": a.name, "spec": str(p), "est_rcon": t}
                       for a, p, t in all_specs]

    if not args.run:
        write_report(reports, job, report)
        return 0

    results = {}
    for art, path, _ in all_specs:
        stem = json.loads(path.read_text(encoding="utf-8"))["name"]
        rpath = reports / ("%s.run.result.json" % stem)
        done = False
        if args.resume and rpath.exists():
            done = bool(json.loads(rpath.read_text(encoding="utf-8"))
                        .get("completed"))
        if done:
            print("keeping %s (already completed)" % rpath.name, flush=True)
            run = {"spec": stem, "returncode": 0, "wall_s": "reused",
                   "cmd": None, "stdout": "", "stderr": ""}
        else:
            print("running %s ..." % path.name, flush=True)
            run = run_spec(path,
                           out / ("run_" + path.stem.replace(".spec", "")))
        run["spec"] = stem
        if rpath.exists():
            res = json.loads(rpath.read_text(encoding="utf-8"))
            run["rcon"] = res["rcon"]["roundtrips"]
            run["completed"] = res.get("completed")
            results.setdefault(art.name, []).append((str(path), str(rpath)))
        report["runs"].append(run)
        print("  rc %d wall %ss rcon %s" % (run["returncode"], run["wall_s"],
                                            run.get("rcon", "--")))
        if run["returncode"] != 0:
            print(run["stdout"][-1500:])
            print(run["stderr"][-1500:])
    for art in arts:
        report["table"].append(table_row(art, results.get(art.name, [])))
    write_report(reports, job, report)
    print(tables_md(job.get("name", "feed"), report))
    return 0


def write_report(reports, job, report):
    reports = Path(reports)
    reports.mkdir(parents=True, exist_ok=True)
    stem = job.get("name", "feed")
    (reports / ("%s.feed.json" % stem)).write_bytes(
        (json.dumps(report, indent=1) + "\n").encode("utf-8"))
    (reports / ("%s.feed.md" % stem)).write_bytes(
        (tables_md(stem, report) + "\n").encode("utf-8"))


if __name__ == "__main__":                                     # pragma: no cover
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    raise SystemExit(main())
