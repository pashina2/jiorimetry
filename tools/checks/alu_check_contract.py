"""Slice-contract checker (DIRECTOR 8, 2026-09-08). Measures each clause of the slice contract (SLICE-1 order) directly,
instead of inferring it from the n-bit function table (alu_check_slices.py checks that table and, as the second reviewer
showed, passes layouts whose through-lines exit below 15).
usage: python alu_check_contract.py layout.json
Clauses (M = measured on the Bench, S = structural on the layout, - = not checked here):
 C1 pitch/box   S  PX <= 12, every cell in x 0..PX-1, y 0..3, z 0..13; y=3 use reported; duplicate coordinates and
                   barrel counts on non-barrel cells are FAILs (2026-09-08, after the second reviewer's reading of this file)
 C2 through     S  entry (0,y,z) is a wire; exit (PX-1,y,z) is a wire or a repeater facing west
                M  n=3, all rows: the entry wire of slices 1 and 2 reads exactly the pin level (15 stays 15, 0 stays 0)
 C3 carry       S  k = wire (0,yk,zk); f = comparator facing west at (PX-1,yk,zk)
                M  n=3, all 512 rows: the k wire of slices 1 and 2 reads exactly 3*carry expected from the lower bits
                   (ADD carry, SUB borrow, AND/OR 0), and the final f reads 3*carry-out of the top slice
 C4 ports       S  a, b, r are single wire cells on the south face (z = Zmax) or the top face (y = 3); a port in the x=0 /
                   x=PX-1 column is reported and must pass C5 (its cross-boundary neighbour is air) -- the ground of the
                   x-face rule is closure, which C5 measures
 C5 closure     S  every x=PX-1 cell is paired with the cell (0,y,z) of the next slice; a pair is allowed only if it is the
                   through exit->entry, f->k, or has no signal carrier on either side (solid/air/barrel); diagonal wire
                   pairs across the boundary (y +- 1) are forbidden
                M  n=3, all 512 rows: every slice's r equals the 1-bit function of (a_i, b_i, measured k_i) for the mode
                   (the local table is unchanged by the neighbours)
 C7 time        M  n=2, the 128 rows driven forward and then backward on ONE bench: after each input change the tiled circuit must
                   rest within T_BOUND (40) gt at the DC solution of the new row (r cells, f, intermediate k). A latch
                   rests at the wrong value, a slow decay does not rest in time (FEED-1 p4: 56 gt), both FAIL
 C6 rules       S  lint L1 (support) / L2 (diagonal wire link) / L3 (wire beside a strongly powered relay, info) on the
                   tiled n=2 layout; repeater side lock on the tiled n=2 layout (a repeater/comparator facing into either
                   side of a repeater, neighbours included)
                M  every measured row must converge, and the DC solution must be the same from a cold and a hot seed
                   (alu_check_slices.run folds Bench.dc_solve_both into conv)
                -  Bench rule gaps are shared with every Bench-based check; the world stages are the independent tier
"""
import sys, json, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import alu_check_slices as CS
import alu_check2 as C2
W = "minecraft:redstone_wire"
T_BOUND = 40


def facing(state):
    return state.split("facing=")[1].split(",")[0].split("]")[0] if "facing=" in state else None


def kind(state):
    if state == W:
        return "wire"
    if state.startswith("minecraft:comparator"):
        return "comparator"
    if state.startswith("minecraft:repeater"):
        return "repeater"
    if state.startswith("minecraft:redstone_torch"):
        return "torch"
    if "barrel" in state:
        return "barrel"
    return "solid"


def carrier(state):
    return kind(state) in ("wire", "comparator", "repeater", "torch")


def expected_carry(mode, A, B, k, i):
    """carry into bit i (i = 0 -> k) for the mode."""
    c = k
    for j in range(i):
        a = (A >> j) & 1
        b = (B >> j) & 1
        if mode == "ADD":
            c = int(a + b + c >= 2)
        elif mode == "SUB":
            c = int(a - b - c < 0)
        else:
            c = 0
    return c


def bit_fn(mode, a, b, c):
    if mode == "ADD":
        return (a + b + c) & 1
    if mode == "SUB":
        return (a - b - c) & 1
    if mode == "AND":
        return a & b
    return a | b


# repeater/comparator "facing" = input side; output goes the opposite way
SIDES = {"north": ((1, 0), (-1, 0)), "south": ((1, 0), (-1, 0)), "east": ((0, 1), (0, -1)), "west": ((0, 1), (0, -1))}
OUT = {"north": (0, 1), "south": (0, -1), "east": (-1, 0), "west": (1, 0)}


def main(path):
    lay = json.load(open(path, encoding="utf-8"))
    S = lay["slice"]
    PX = S["pitch"]
    M = {}
    dups = []
    for b in lay["blocks"]:
        if (b[0], b[1], b[2]) in M:
            dups.append((b[0], b[1], b[2]))
        M[(b[0], b[1], b[2])] = b[3]
    fails = []
    notes = []

    def fail(c, msg):
        fails.append((c, msg))
        print("FAIL %s %s" % (c, msg))

    def note(c, msg):
        notes.append((c, msg))
        print("note %s %s" % (c, msg))

    # C1
    xs = [p[0] for p in M]
    ys = [p[1] for p in M]
    zs = [p[2] for p in M]
    Z = max(zs)
    if PX > 12:
        fail("C1", "pitch %d > 12" % PX)
    if min(xs) < 0 or max(xs) > PX - 1:
        fail("C1", "cells outside x 0..%d: %s" % (PX - 1, [p for p in M if p[0] < 0 or p[0] > PX - 1][:5]))
    if min(ys) < 0 or max(ys) > 3:
        fail("C1", "cells outside y 0..3")
    if Z > 13:
        fail("C1", "z max %d > 13" % Z)
    if dups:
        fail("C1", "duplicate coordinates in blocks (later entry silently wins): %s" % dups[:5])
    for key in (lay.get("barrels") or {}):
        c = tuple(int(t) for t in key.split(","))
        if kind(M.get(c, "")) != "barrel":
            fail("C1", "barrel count at %s but the block there is %s" % (key, M.get(c)))
    print("C1 box x 0..%d y %d..%d z 0..%d  PX=%d  cells=%d%s" % (max(xs), min(ys), max(ys), Z, PX, len(M), "  (y=3 used)" if max(ys) == 3 else ""))
    # C2 structural
    for name, cells in S["through"].items():
        for c in cells:
            x, y, z = c
            e = M.get((0, y, z))
            ex = M.get((PX - 1, y, z))
            if x != 0 or e != W:
                fail("C2", "%s entry %s is not a wire at x=0 (%s)" % (name, c, e))
            if not (ex == W or (ex and kind(ex) == "repeater" and facing(ex) == "west")):
                fail("C2", "%s exit (%d,%d,%d) is %s, need wire or repeater facing west" % (name, PX - 1, y, z, ex))
    # C3 structural
    k = S["ports"]["k"]
    f = S["ports"]["f"]
    if not (k[0] == 0 and M.get(tuple(k)) == W):
        fail("C3", "k %s is not a wire at x=0" % k)
    fe = M.get(tuple(f))
    if not (f[0] == PX - 1 and (f[1], f[2]) == (k[1], k[2]) and fe and kind(fe) == "comparator" and facing(fe) == "west"):
        fail("C3", "f %s is not a comparator facing west at (PX-1,yk,zk) (%s)" % (f, fe))
    # C4
    for p in ("a", "b", "r"):
        c = tuple(S["ports"][p])
        e = M.get(c)
        if e != W:
            fail("C4", "port %s %s is not a wire (%s)" % (p, c, e))
            continue
        face = []
        if c[2] == Z:
            face.append("south")
        if c[1] == 3:
            face.append("top")
        if not face:
            fail("C4", "port %s %s is on neither the south face (z=%d) nor the top face (y=3)" % (p, c, Z))
        else:
            print("C4 port %s %s on %s face" % (p, c, "+".join(face)))
        if c[0] in (0, PX - 1):
            note("C4", "port %s %s lies in the x=%d column; allowed only through C5" % (p, c, c[0]))
    # C5 structural
    allowed = set()
    for name, cells in S["through"].items():
        for c in cells:
            allowed.add((PX - 1, c[1], c[2]))
    allowed.add(tuple(f))
    for (x, y, z), e in sorted(M.items()):
        if x == PX - 1:
            other = M.get((0, y, z))
            if (x, y, z) in allowed:
                print("C5 boundary pair (%d,%d,%d) %s -> next (0,%d,%d) %s [allowed]" % (x, y, z, kind(e), y, z, kind(other) if other else "air"))
                continue
            if other is not None and (carrier(e) or carrier(other)):
                fail("C5", "boundary pair (%d,%d,%d) %s <-> next (0,%d,%d) %s" % (x, y, z, e, y, z, other))
            elif kind(e) == "wire" and other is None:
                note("C5", "x=%d wire (%d,%d,%d) faces air in the next slice" % (x, x, y, z))
            if kind(e) == "wire":
                for dy in (-1, 1):
                    if M.get((0, y + dy, z)) == W:
                        fail("C5", "diagonal wire pair (%d,%d,%d) <-> next (0,%d,%d)" % (x, y, z, y + dy, z))
        if x == 0:
            other = M.get((PX - 1, y, z))
            if (PX - 1, y, z) in allowed:
                continue
            if other is None and kind(e) == "wire":
                note("C5", "x=0 wire (0,%d,%d) faces air in the previous slice" % (y, z))
            if kind(e) == "wire":
                for dy in (-1, 1):
                    if M.get((PX - 1, y + dy, z)) == W:
                        fail("C5", "diagonal wire pair (0,%d,%d) <-> previous (%d,%d,%d)" % (y, z, PX - 1, y + dy, z))
    # C6 structural
    T = CS.tiled(lay, 2)
    lint = C2.lint(T)
    l1 = [w for w in lint if w[0].startswith("L1")]
    l2 = [w for w in lint if w[0].startswith("L2")]
    l3 = [w for w in lint if w[0].startswith("L3")]
    print("C6 lint tiled n=2: L1=%d L2=%d L3=%d" % (len(l1), len(l2), len(l3)))
    if l1:
        fail("C6", "L1 support: %s" % l1[:5])
    if l2:
        fail("C6", "L2 diagonal wire link: %s" % l2[:5])
    MT = {(b[0], b[1], b[2]): b[3] for b in T["blocks"]}   # side lock is checked on the tiled n=2 layout (a neighbour slice can lock a boundary repeater)
    for (x, y, z), e in MT.items():
        if kind(e) != "repeater":
            continue
        for dx, dz in SIDES[facing(e)]:
            o = MT.get((x + dx, y, z + dz))
            if o and kind(o) in ("repeater", "comparator"):
                ox, oz = OUT[facing(o)]
                if (x + dx + ox, z + dz + oz) == (x, z):
                    fail("C6", "repeater (%d,%d,%d) side-locked by %s at (%d,%d,%d)" % (x, y, z, o, x + dx, y, z + dz))
    # measured, n=3
    n = 3
    c2bad = c3bad = c5bad = rows = 0
    convbad = fbad = 0
    for mode, (P, Wn) in CS.MODES.items():
        for A in range(2 ** n):
            for B in range(2 ** n):
                for kk in (0, 1):
                    rs, fo, conv, bench = CS.run(lay, n, A, B, kk, P, Wn)
                    rows += 1
                    if not conv:
                        convbad += 1
                        if convbad <= 3:
                            fail("C6", "%s A=%d B=%d k=%d: Bench did not converge, or the DC solution is not unique (BISTABLE)" % (mode, A, B, kk))
                    fexp = 3 * expected_carry(mode, A, B, kk, n)
                    if fo != fexp:
                        fbad += 1
                        if fbad <= 3:
                            fail("C3", "%s A=%d B=%d k=%d: final f reads %s, expected %d" % (mode, A, B, kk, fo, fexp))
                    for i in (1, 2):
                        for name, lv in (("P", P), ("Wn", Wn)):
                            for c in S["through"][name]:
                                cell = (c[0] + i * PX, c[1], c[2])
                                got = CS.read(bench, cell)
                                if got != lv:
                                    c2bad += 1
                                    if c2bad <= 6:
                                        fail("C2", "%s A=%d B=%d k=%d: slice %d entry %s of %s reads %s, pin %d" % (mode, A, B, kk, i, name, cell, got, lv))
                        got = CS.read(bench, (k[0] + i * PX, k[1], k[2]))
                        exp = 3 * expected_carry(mode, A, B, kk, i)
                        if got != exp:
                            c3bad += 1
                            if c3bad <= 6:
                                fail("C3", "%s A=%d B=%d k=%d: slice %d k reads %s, expected %d" % (mode, A, B, kk, i, got, exp))
                    for i in range(n):
                        ki = kk if i == 0 else int((CS.read(bench, (k[0] + i * PX, k[1], k[2])) or 0) >= 3)
                        exp = 3 * bit_fn(mode, (A >> i) & 1, (B >> i) & 1, ki)
                        if rs[i] != exp:
                            c5bad += 1
                            if c5bad <= 6:
                                fail("C5", "%s A=%d B=%d k=%d: slice %d r=%s, local table says %d (k_i=%d)" % (mode, A, B, kk, i, rs[i], exp, ki))
    print("measured n=3 rows=%d: C2 through-entry mismatches=%d, C3 carry mismatches=%d (final f mismatches=%d), C5 local-table mismatches=%d, non-converged/bistable rows=%d" % (rows, c2bad, c3bad, fbad, c5bad, convbad))
    # C7 time, n=2 in sweep order on one bench
    n2 = 2
    T2 = CS.tiled(lay, n2)
    order = [(mode, A, B, kk) for mode in CS.MODES for A in range(2 ** n2) for B in range(2 ** n2) for kk in (0, 1)]
    order = order + order[-2::-1]   # forward sweep, then back to the start: every input falls as well as rises
    def pins_for(mode, A, B, kk):
        P, Wn = CS.MODES[mode]
        pins = {}
        for key, lv in (("P", P), ("Wn", Wn)):
            for c in S["through"][key]:
                pins[tuple(c)] = lv
        pins[tuple(k)] = 3 * kk
        for i in range(n2):
            for key, val in (("a", (A >> i) & 1), ("b", (B >> i) & 1)):
                c = S["ports"][key]
                pins[(c[0] + i * PX, c[1], c[2])] = 3 * val
        return pins
    watch = [(S["ports"]["r"][0] + i * PX, S["ports"]["r"][1], S["ports"]["r"][2]) for i in range(n2)] + [(k[0] + PX, k[1], k[2])]
    first = pins_for(*order[0])
    bench = CS.BS.build(T2, {p: {"power": v} for p, v in first.items()})
    bench.dc_solve()
    worst = 0
    tbad = 0
    for mode, A, B, kk in order[1:]:
        gt, rested, last = bench.settle_after(pins_for(mode, A, B, kk), watch, limit=T_BOUND)
        worst = max(worst, gt)
        exp = [3 * bit_fn(mode, (A >> i) & 1, (B >> i) & 1, expected_carry(mode, A, B, kk, i)) for i in range(n2)] + [3 * expected_carry(mode, A, B, kk, 1)]
        got = [int(bench.blocks[c][1]["power"]) for c in watch]
        fcell = (S["ports"]["f"][0] + PX, S["ports"]["f"][1], S["ports"]["f"][2])
        fgot = bench.cmp_out.get(fcell)
        if not rested or got != exp or fgot != 3 * expected_carry(mode, A, B, kk, n2):
            tbad += 1
            if tbad <= 4:
                fail("C7", "%s A=%d B=%d k=%d: rested=%s after %d gt, r/k=%s expected %s, f=%s" % (mode, A, B, kk, rested, gt, got, exp, fgot))
    print("C7 time n=2: %d transitions, worst settle %d gt (bound %d), failures %d" % (len(order) - 1, worst, T_BOUND, tbad))
    print("CONTRACT %s: %d FAIL, %d notes" % ("PASS" if not fails else "FAIL", len(fails), len(notes)))
    return not fails


if __name__ == "__main__":
    sys.exit(0 if main(sys.argv[1]) else 1)
