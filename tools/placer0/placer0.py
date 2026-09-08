#!/usr/bin/env python3
"""placer0.py -- PLACER-0 (DIRECTOR 8 pilot, 2026-09-08).

Does the "think of the coordinates" part of a redstone placement need an LLM?
This program takes problems.json + a problem name and SEARCHES for a placement
using the DC rules as backward constraints, then verifies every candidate with
placer0_check.check() (the oracle Bench).

No problem-specific coordinates appear anywhere below: the only inputs are the
problem file and the general rule set encoded in expand().

Method: A* over (partial layout, open requirement list).
  A requirement is "this cell/port must present this level-vector (one entry per
  pin combination, each an interval [lo,hi])".
  Expanding a requirement applies the general DC rewrites:
    wire   <- wire hop (-1)  |  gate front (lossless)  |  strongly powered solid
    strong <- 1 or 2 gate fronts (max)                    [lossless vertical/merge]
    side   <- wire at the side cell | gate whose front is the side cell (max of 2)
    back   <- wire | strongly powered solid | container constant | chained gate
    gateout<- repeater (0/15) | sub(const K, side) | copy(back) with sides 0
  Cost = blocks added.  Heuristic = BFS distance to the nearest pin (y-moves
  cost 3: a level change needs gate+solid+wire).

usage: python placer0.py problems.json <name> [--timeout 600] [--nodes 400000]
"""
import argparse
import heapq
import itertools
import json
import os
import sys
import time
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import placer0_check as PC                                          # noqa: E402
A = PC.A                                                            # alu_check2 (lint)

DIRS = {"north": (0, 0, -1), "south": (0, 0, 1), "east": (1, 0, 0), "west": (-1, 0, 0)}
PERP = {"north": ("east", "west"), "south": ("east", "west"),
        "east": ("north", "south"), "west": ("north", "south")}
FULL = A.FULL
STONE = "minecraft:smooth_stone"
WIRE = "minecraft:redstone_wire"
BARREL = "minecraft:barrel[facing=up,open=false]"


def add(p, d):
    v = DIRS[d]
    return (p[0] + v[0], p[1] + v[1], p[2] + v[2])


def up(p):
    return (p[0], p[1] + 1, p[2])


def down(p):
    return (p[0], p[1] - 1, p[2])


def nb6(p):
    x, y, z = p
    return [(x + 1, y, z), (x - 1, y, z), (x, y, z + 1), (x, y, z - 1), (x, y + 1, z), (x, y - 1, z)]


# ---------------------------------------------------------------- containers
def barrel_level(n, slots=27, maxc=64):
    """ScreenHandler.calculateComparatorOutput on a barrel of `n` cobblestone."""
    f = (n / maxc) / slots
    return int(f * 14) + (1 if f > 0 else 0)


def items_for_level(k):
    if k <= 0:
        return None
    for n in range(1, 27 * 64 + 1):
        if barrel_level(n) == k:
            return n
    return None


# ---------------------------------------------------------------- level specs
# a spec is a tuple of (lo, hi) intervals, one per pin combination
ANY = (0, 15)


def spec_ok(vec, spec):
    return all(lo <= v <= hi for v, (lo, hi) in zip(vec, spec))


def spec_sat(spec):
    return all(lo <= hi for lo, hi in spec)


def spec_trivial(spec):
    return all(lo == 0 for lo, _ in spec)


def spec_const_value(spec):
    """The single level that satisfies every combination, or None."""
    lo = max(l for l, _ in spec)
    hi = min(h for _, h in spec)
    return lo if lo <= hi else None


def inv_hop(spec):
    """What the neighbouring wire must carry so that this wire (= max(0,j-1))
    lands in `spec`."""
    out = []
    for lo, hi in spec:
        nlo = lo + 1 if lo > 0 else 0
        nhi = min(15, hi + 1)
        out.append((nlo, nhi))
    return tuple(out)


def sub_side_spec(K, spec):
    """out = K - j (j<=K) else 0.  What must the side max be?"""
    out = []
    for lo, hi in spec:
        if lo > 0:
            a, b = K - hi, K - lo
            a = max(a, 0)
            if b < 0 or a > K:
                return None
            out.append((a, min(b, K)))
        else:
            # out may be 0..hi : j >= K-hi is enough (j>=K gives 0)
            out.append((max(0, K - hi), 15))
    return tuple(out)


def rep_back_spec(spec):
    """A repeater outputs 15 or 0.  Which, per combination?"""
    out = []
    for lo, hi in spec:
        can_on = lo <= 15 <= hi
        can_off = lo <= 0 <= hi
        if can_on and can_off:
            out.append(ANY)
        elif can_on:
            out.append((1, 15))
        elif can_off:
            out.append((0, 0))
        else:
            return None
    return tuple(out)


def split_specs(spec, n_slots):
    """max(e1..ek) must land in spec -> ways to share the lower bounds.
    Yields lists of sub-specs (one per used slot)."""
    must = [i for i, (lo, _) in enumerate(spec) if lo > 0]
    hi_only = tuple((0, hi) for _, hi in spec)
    yield [spec]                                     # one emitter does it all
    if n_slots < 2 or not must:
        return
    for r in range(1, len(must)):
        for sub in itertools.combinations(must, r):
            s1 = tuple(spec[i] if i in sub else hi_only[i] for i in range(len(spec)))
            s2 = tuple(spec[i] if i not in sub else hi_only[i] for i in range(len(spec)))
            yield [s1, s2]


# ---------------------------------------------------------------- the problem
class Problem:
    def __init__(self, prob):
        self.p = prob
        self.name = prob["name"]
        (self.x0, self.y0, self.z0), (self.x1, self.y1, self.z1) = prob["bbox"]
        self.fixed = {tuple(r[:3]): r[3] for r in prob["fixed"]}
        self.forbidden = {tuple(c) for c in prob.get("forbidden", [])}
        self.max_blocks = prob["max_blocks"]
        self.fixed_barrels = dict(prob.get("barrels") or {})
        self.pin_names = list(prob["pins"].keys())
        self.pin_cells = {tuple(prob["pins"][n]["cell"]): n for n in self.pin_names}
        self.combos = list(itertools.product(*[prob["pins"][n]["levels"] for n in self.pin_names]))
        self.pin_vec = {}
        for n in self.pin_names:
            i = self.pin_names.index(n)
            self.pin_vec[tuple(prob["pins"][n]["cell"])] = tuple(c[i] for c in self.combos)
        self.goals = []
        for o in prob["outputs"]:
            vec = tuple(int(eval(o["expect"], {"max": max, "min": min}, dict(zip(self.pin_names, c))))
                        for c in self.combos)
            self.goals.append((tuple(o["cell"]), vec))
        self.dist = self._pin_distance()
        self.mc = self._relax()
        # one relaxation per pin: a requirement that is non-zero in a combination
        # where only pin X is on can only be supplied by X
        self.mc_pin = {n: self._relax(only=n) for n in self.pin_names}
        self.on_pins = [frozenset(n for n, v in zip(self.pin_names, c) if v > 0)
                        for c in self.combos]

    def inside(self, p):
        return (self.x0 <= p[0] <= self.x1 and self.y0 <= p[1] <= self.y1
                and self.z0 <= p[2] <= self.z1)

    def free(self, p):
        """A cell the solver may write to."""
        return self.inside(p) and p not in self.forbidden and p not in self.fixed

    def _pin_distance(self):
        """BFS from the pins over usable cells; a y move costs 3 (gate+solid+wire)."""
        d = {}
        pq = [(0, c) for c in self.pin_cells]
        for _, c in pq:
            d[c] = 0
        heapq.heapify(pq)
        while pq:
            cost, p = heapq.heappop(pq)
            if cost > d.get(p, 1 << 30):
                continue
            for q in nb6(p):
                if not self.inside(q) or q in self.forbidden:
                    continue
                if q in self.fixed and A.name(self.fixed[q]) not in FULL and q not in self.pin_cells:
                    pass
                step = 3 if q[1] != p[1] else 1
                if cost + step < d.get(q, 1 << 30):
                    d[q] = cost + step
                    heapq.heappush(pq, (cost + step, q))
        return d

    def support_possible(self, p):
        b = down(p)
        if not self.inside(b):
            return False
        if b in self.fixed:
            return A.name(self.fixed[b]) in FULL
        return b not in self.forbidden

    def usable_wire(self, p):
        if not self.inside(p) or p in self.forbidden or not self.support_possible(p):
            return False
        if p in self.fixed:
            return A.name(self.fixed[p]) == WIRE
        return True

    def usable_gate(self, p):
        """A cell that could hold a comparator/repeater (a solid cell cannot)."""
        if not self.inside(p) or p in self.forbidden or not self.support_possible(p):
            return False
        if p in self.fixed:
            return A.name(self.fixed[p]) in ("minecraft:comparator", "minecraft:repeater")
        return True

    def usable_solid(self, p):
        if not self.inside(p) or p in self.forbidden:
            return False
        if p in self.fixed:
            return A.name(self.fixed[p]) in FULL
        return True

    def _relax(self, only=None):
        """Relaxed cost (in blocks) of making a wire at `cell` carry `level`,
        sourced from a pin.  Ignores collisions between routes; keeps the DC
        arithmetic (-1 per hop, gates regenerate, a gate->solid->wire relay
        moves a level to any of the solid's 6 faces).  Used as the A* heuristic
        for every requirement whose spec varies with the pins."""
        best = {}
        pq = []
        for c, n in self.pin_cells.items():
            if only is not None and n != only:
                continue
            L = max(self.p["pins"][n]["levels"])
            if L > 0:
                best[(c, L)] = 0
                pq.append((0, c, L))
        heapq.heapify(pq)
        while pq:
            cost, c, L = heapq.heappop(pq)
            if cost > best.get((c, L), 1 << 30):
                continue
            outs = []
            for d in DIRS:                                  # wire hop
                n = add(c, d)
                if L - 1 >= 1 and self.usable_wire(n):
                    outs.append((cost + 1, n, L - 1))
            for d in DIRS:                                  # gate with its back here
                g = add(c, d)
                f = add(g, d)
                if not (self.usable_gate(g) and self.inside(f)):
                    continue
                for lvl in (L, 15):
                    if self.usable_wire(f):                 # front -> wire
                        outs.append((cost + 2, f, lvl))
                    if self.usable_solid(f):                # front -> solid -> any face
                        for n2 in nb6(f):
                            if self.usable_wire(n2):
                                outs.append((cost + 3, n2, lvl))
            for nc, n, lvl in outs:
                if nc < best.get((n, lvl), 1 << 30):
                    best[(n, lvl)] = nc
                    heapq.heappush(pq, (nc, n, lvl))
        return best

    def _mc_min(self, table, cell, need):
        return min([table.get((cell, L), 1 << 30) for L in range(max(1, need), 16)] or [1 << 30])

    def h_cell(self, cell, need=1, spec=None):
        req = set()
        if spec is not None:
            for i, (lo, _) in enumerate(spec):
                if lo > 0 and len(self.on_pins[i]) == 1:
                    req |= self.on_pins[i]
        if req:
            v = max(self._mc_min(self.mc_pin[n], cell, need) for n in req)
            extra = 2 * (len(req) - 1)      # a second source costs at least a gate + a cell
        else:
            v = self._mc_min(self.mc, cell, need)
            extra = 0
        if v >= 1 << 30:
            return 99
        return max(0, v - 1) + extra


# ---------------------------------------------------------------- layout ops
class Layout:
    """The cells the solver has added (immutable use: always copy before edit)."""
    __slots__ = ("cells", "barrels", "_key")

    def __init__(self, cells=None, barrels=None):
        self.cells = cells or {}
        self.barrels = barrels or {}
        self._key = None

    def copy(self):
        return Layout(dict(self.cells), dict(self.barrels))

    def key(self):
        if self._key is None:
            self._key = (tuple(sorted(self.cells.items())), tuple(sorted(self.barrels.items())))
        return self._key


def block_at(prob, lay, p):
    return lay.cells.get(p) or prob.fixed.get(p)


def is_full(prob, lay, p):
    s = block_at(prob, lay, p)
    return s is not None and A.name(s) in FULL


def put(prob, lay, p, state, need_support=False):
    """Place `state` at p (or accept an identical block already there).
    Returns a NEW layout, or None when the cell is unusable."""
    cur = block_at(prob, lay, p)
    if cur is not None:
        if cur == state:
            lay2 = lay
        elif A.name(cur) == A.name(state) and A.name(state) in FULL:
            lay2 = lay
        else:
            return None
    else:
        if not prob.free(p):
            return None
        lay2 = lay.copy()
        lay2.cells[p] = state
    if need_support:
        b = down(p)
        if not is_full(prob, lay2, b):
            if not prob.free(b) or not prob.inside(b):
                return None
            lay2 = lay2.copy() if lay2 is lay else lay2
            lay2.cells[b] = STONE
    return lay2


def gate_state(kind, facing, mode="subtract"):
    if kind == "repeater":
        return "minecraft:repeater[facing=%s]" % facing
    return "minecraft:comparator[facing=%s,mode=%s]" % (facing, mode)


# ---------------------------------------------------------------- requirements
# ("wire", cell, spec)              the dust at cell must read spec
# ("strong", cell, spec)            the solid at cell must RECEIVE strong power spec
# ("gateout", cell, facing, spec)   a gate at cell facing `facing` must output spec
# ("back", cell, facing, spec)      the back cell of that gate must present spec
# ("side", cell, facing, spec)      the side max of that gate must be spec

def supply_cells(task):
    """Where the signal for this requirement has to ARRIVE -- the cell itself for
    a wire, the back cell / side cells for a gate port, the gate slots for a
    strongly powered solid."""
    kind = task[0]
    if kind == "wire":
        return [task[1]]
    if kind == "back":
        return [add(task[1], task[2])]
    if kind == "gateout":
        g, f = task[1], task[2]
        return [add(g, f)] + [add(g, d) for d in PERP[f]]
    if kind == "side":
        g, f = task[1], task[2]
        return [add(g, d) for d in PERP[f]]
    if kind == "strong":
        return [add(task[1], d) for d in DIRS]
    return [task[1]]


def req_cell(task):
    return task[1]


def expand(prob, lay, task, budget):
    """All general rewrites of one requirement.  Yields (layout, [subtasks])."""
    kind = task[0]
    out = []

    if kind == "wire":
        _, cell, spec = task
        if not spec_sat(spec):
            return out
        if spec_trivial(spec):
            # nothing has to arrive here; the upper bounds are the oracle's job
            out.append((lay, []))
            return out
        # terminal: a pin holds a known vector
        if cell in prob.pin_cells:
            if spec_ok(prob.pin_vec[cell], spec):
                out.append((lay, []))
            return out
        lay0 = put(prob, lay, cell, WIRE, need_support=True)
        if lay0 is None:
            return out
        # (1) a wire hop from a horizontal neighbour  (-1 per hop)
        src = inv_hop(spec)
        if spec_sat(src) and max(h for _, h in src) > 0:
            for d in DIRS:
                n = add(cell, d)
                if not prob.inside(n) or n in lay0.cells:
                    continue
                out.append((lay0, [("wire", n, src)]))
        # (2) a gate whose FRONT is this cell (lossless)
        for d in DIRS:
            g = add(cell, d)                    # front = g - facing = cell  ->  facing = d
            if not prob.inside(g):
                continue
            out.append((lay0, [("gateout", g, d, spec)]))
        # (3) a strongly powered solid on any of the 6 faces (lossless, vertical)
        for s in nb6(cell):
            if not prob.inside(s):
                continue
            out.append((lay0, [("strong", s, spec)]))
        return out

    if kind == "strong":
        _, cell, spec = task
        if not spec_sat(spec):
            return out
        if spec_trivial(spec):
            out.append((lay, []))
            return out
        lay0 = put(prob, lay, cell, STONE)
        if lay0 is None:
            return out
        slots = [(add(cell, d), d) for d in DIRS if prob.inside(add(cell, d))]
        for parts in split_specs(spec, len(slots)):
            for chosen in itertools.permutations(slots, len(parts)):
                if len(parts) == 2 and chosen[0][0] > chosen[1][0]:
                    continue                    # unordered pair
                out.append((lay0, [("gateout", g, d, sp) for (g, d), sp in zip(chosen, parts)]))
        return out

    if kind == "side":
        _, cell, facing, spec = task
        if not spec_sat(spec):
            return out
        if spec_trivial(spec):
            out.append((lay, []))
            return out
        slots = [add(cell, d) for d in PERP[facing] if prob.inside(add(cell, d))]
        for parts in split_specs(spec, len(slots)):
            for chosen in itertools.permutations(slots, len(parts)):
                if len(parts) == 2 and chosen[0] > chosen[1]:
                    continue
                subs = []
                for s, sp in zip(chosen, parts):
                    subs.append((s, sp))
                # each side emitter is either a dust or a gate pointing its front in
                opts = []
                for s, sp in subs:
                    fac = None
                    for d in DIRS:
                        if add(cell, d) == s:
                            fac = d              # the gate at s faces d, its front is the gate cell
                    kinds = [("wire", s, sp)]
                    if fac is not None:
                        kinds.append(("gateout", s, fac, sp))
                    opts.append(kinds)
                for combo in itertools.product(*opts):
                    out.append((lay, list(combo)))
        return out

    if kind == "gateout":
        _, cell, facing, spec = task
        if not spec_sat(spec):
            return out
        cur = block_at(prob, lay, cell)
        back = add(cell, facing)
        if not prob.inside(back):
            return out
        curname = A.name(cur) if cur else None
        curfacing = A.facing(cur) if cur else None
        if cur is not None and (curname not in ("minecraft:comparator", "minecraft:repeater")
                                or curfacing != facing):
            return out
        # (a) repeater: normalises to 0/15
        if cur is None or curname == "minecraft:repeater":
            bs = rep_back_spec(spec)
            if bs is not None:
                lay1 = put(prob, lay, cell, gate_state("repeater", facing), need_support=True)
                if lay1 is not None:
                    out.append((lay1, [("back", cell, facing, bs)]))
        # (b) comparator
        if cur is None or curname == "minecraft:comparator":
            mode = cur.split("mode=")[1].rstrip("]") if cur and "mode=" in cur else None
            backblk = block_at(prob, lay, back)
            backname = A.name(backblk) if backblk else None
            # (b1) subtract with a CONSTANT behind it: out = K - side
            if mode in (None, "subtract"):
                ks = set()
                if backname == "minecraft:barrel":
                    n = prob.fixed_barrels.get("%d,%d,%d" % back) or lay.barrels.get("%d,%d,%d" % back)
                    if n:
                        ks.add(barrel_level(int(n)))
                else:
                    for lo, hi in spec:
                        if lo > 0:
                            ks.add(lo)
                    ks.add(max(max(l for l, _ in spec), 1))
                for K in sorted(ks):
                    if not 1 <= K <= 15:
                        continue
                    sp = sub_side_spec(K, spec)
                    if sp is None or not spec_sat(sp):
                        continue
                    lay1 = put(prob, lay, cell, gate_state("comparator", facing, "subtract"),
                               need_support=True)
                    if lay1 is None:
                        continue
                    if backname != "minecraft:barrel":
                        n = items_for_level(K)
                        lay1 = put(prob, lay1, back, BARREL)
                        if lay1 is None:
                            continue
                        lay1 = lay1.copy()
                        lay1.barrels["%d,%d,%d" % back] = n
                    out.append((lay1, [("side", cell, facing, sp)]))
            # (b2) a copy gate: sides 0, out = back
            if backname != "minecraft:barrel":
                for m in (("subtract",) if mode is None else (mode,)):
                    lay1 = put(prob, lay, cell, gate_state("comparator", facing, m),
                               need_support=True)
                    if lay1 is not None:
                        out.append((lay1, [("back", cell, facing, spec)]))
        return out

    if kind == "back":
        _, cell, facing, spec = task
        if not spec_sat(spec):
            return out
        b = add(cell, facing)
        if not prob.inside(b):
            return out
        cur = block_at(prob, lay, b)
        curname = A.name(cur) if cur else None
        # (a) a container constant
        k = spec_const_value(spec)
        if k is not None and k > 0:
            if curname == "minecraft:barrel":
                n = prob.fixed_barrels.get("%d,%d,%d" % b) or lay.barrels.get("%d,%d,%d" % b)
                if n and barrel_level(int(n)) == k:
                    out.append((lay, []))
            elif cur is None:
                lay1 = put(prob, lay, b, BARREL)
                if lay1 is not None:
                    n = items_for_level(k)
                    lay1 = lay1.copy()
                    lay1.barrels["%d,%d,%d" % b] = n
                    out.append((lay1, []))
        if spec_trivial(spec) and cur is None:
            out.append((lay, []))
        # (b) a dust behind the gate
        out.append((lay, [("wire", b, spec)]))
        # (c) a strongly powered solid behind the gate
        out.append((lay, [("strong", b, spec)]))
        # (d) a chained gate behind this one (same facing)
        out.append((lay, [("gateout", b, facing, spec)]))
        return out

    raise ValueError(task)


# ---------------------------------------------------------------- lint repair
def repair(prob, lay):
    """General rewrites for the two placement lints the checker rejects:
       L2 diagonal-down  -> block the air cell beside the upper wire
       L2 diagonal-up    -> cap the lower wire with a full block."""
    lay = lay.copy()
    for _ in range(8):
        blocks = {**prob.fixed, **lay.cells}
        bad = [w for w in A.lint({"blocks": [[*p, s] for p, s in blocks.items()]})
               if w[0].startswith("L2")]
        if not bad:
            return lay
        fixed_any = False
        for w in bad:
            p, q = w[1], w[3]
            if w[0].startswith("L2 diagonal-down"):
                cand = (q[0], q[1] + 1, q[2])       # the air cell beside the upper wire
            else:
                cand = up(p)                        # cap over the lower wire
            if prob.free(cand) and cand not in lay.cells:
                lay.cells[cand] = STONE
                fixed_any = True
                break
        if not fixed_any:
            return None
    return None


# ---------------------------------------------------------------- the search
class Stats:
    def __init__(self):
        self.nodes = 0
        self.checks = 0
        self.pushed = 0


def hcost(prob, tasks):
    h = 0
    for t in tasks:
        sp = t[-1]
        if spec_trivial(sp):
            continue
        if spec_const_value(sp) is not None and t[0] in ("back", "gateout"):
            h += 1
            continue
        need = max(lo for lo, _ in sp)
        h += min(prob.h_cell(c, need, sp) for c in supply_cells(t))
    return h


def verify(prob, lay, st):
    """The oracle: repair the two placement lints, then run the Bench sweep."""
    st.checks += 1
    fin = repair(prob, lay)
    if fin is None:
        return None
    sol = {"blocks": [[*p, s] for p, s in sorted(fin.cells.items())], "barrels": fin.barrels}
    if len(sol["blocks"]) > prob.max_blocks:
        return None
    _so = sys.stdout
    sys.stdout = open(os.devnull, "w")
    try:
        ok, info = PC.check(prob.p, sol)
    except Exception:
        ok = False
    finally:
        sys.stdout.close()
        sys.stdout = _so
    return sol if ok else None


def solve(prob, timeout=600.0, node_limit=2000000, verbose=False):
    """IDA*: cost = blocks placed, bound raised until a candidate passes."""
    st = Stats()
    t0 = time.time()
    tasks0 = tuple(("wire", cell, tuple((v, v) for v in vec)) for cell, vec in prob.goals)

    class Stop(Exception):
        pass

    def dfs(lay, tasks, bound, seen):
        if time.time() - t0 > timeout or st.nodes > node_limit:
            raise Stop()
        st.nodes += 1
        if not tasks:
            return verify(prob, lay, st)
        task, rest = tasks[0], tasks[1:]
        kids = []
        for lay2, subs in expand(prob, lay, task, prob.max_blocks - len(lay.cells)):
            if len(lay2.cells) > prob.max_blocks:
                continue
            nt = tuple(subs) + rest
            f = len(lay2.cells) + hcost(prob, nt)
            if f > bound:
                continue
            kids.append((f, len(lay2.cells), lay2, nt))
        kids.sort(key=lambda k: (k[0], k[1]))
        for f, _, lay2, nt in kids:
            k = (lay2.key(), nt)
            if k in seen:
                continue
            if len(seen) < 3000000:
                seen.add(k)
            got = dfs(lay2, nt, bound, seen)
            if got is not None:
                return got
        return None

    bound = hcost(prob, tasks0)
    while bound <= prob.max_blocks:
        try:
            got = dfs(Layout(), tasks0, bound, set())
        except Stop:
            return None, st, time.time() - t0
        if got is not None:
            return got, st, time.time() - t0
        if verbose:
            print("   bound %d exhausted  nodes=%d checks=%d t=%.1f"
                  % (bound, st.nodes, st.checks, time.time() - t0))
        bound += 1
    return None, st, time.time() - t0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("problems")
    ap.add_argument("name")
    ap.add_argument("--timeout", type=float, default=600.0)
    ap.add_argument("--nodes", type=int, default=2000000)
    ap.add_argument("-v", action="store_true")
    args = ap.parse_args()
    probs = {p["name"]: p for p in json.load(open(args.problems))}
    if args.name == "all":
        names = list(probs)
    else:
        names = [args.name]
    for nm in names:
        prob = Problem(probs[nm])
        sol, st, el = solve(prob, timeout=args.timeout, node_limit=args.nodes, verbose=args.v)
        if sol is None:
            print("UNKNOWN %s  nodes=%d checks=%d time=%.1fs" % (nm, st.nodes, st.checks, el))
            continue
        path = os.path.join(HERE, "sol_%s.json" % nm)
        with open(path, "wb") as fh:
            fh.write(json.dumps(sol, indent=1).encode())
        ok, info = PC.check(prob.p, sol)
        print("SOLVED %s  blocks=%d nodes=%d checks=%d time=%.1fs  recheck=%s"
              % (nm, len(sol["blocks"]), st.nodes, st.checks, el, "PASS" if ok else "FAIL"))


if __name__ == "__main__":
    main()
