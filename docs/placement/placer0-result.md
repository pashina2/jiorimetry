# PLACER-0 — results (Opus-class implementer, 2026-09-08)

One program, `placer0.py`, no problem-specific coordinates anywhere in it.
Input = `problems.json` + a problem name. Oracle = `placer0_check.check()` (the Bench).

```
python placer0.py problems.json <name> [--timeout 600] [-v]
```

## What the program is

A* / IDA* over **(partial layout, list of open requirements)**.

A *requirement* is "this port must present this level-vector", where the vector has
one entry per pin combination and each entry is an interval `[lo,hi]`
(exact when `lo==hi`, "at least k" as `[k,15]`, "don't care" as `[0,15]`).
The initial requirement comes straight from the problem file: the output wire must
read `eval(expect)` exactly, in every combination.

Expanding a requirement applies the DC rules **backwards** — these are the only
placement rules the program knows, and none of them mentions a coordinate:

| requirement | rewrites |
|---|---|
| `wire` at c reads V | wire hop from a horizontal neighbour (`-1`, inverted: `V+1`, `0 -> {0,1}`) / a gate whose **front** is c (lossless) / a **strongly powered solid** on any of c's 6 faces (lossless, this is the only vertical move) |
| `strong` at s = V | 1 or 2 gates whose front is s; with 2, the lower bounds are **split across the combinations** (`max` of the two fronts) |
| `side` of gate g = V | dust at a side cell, or a gate whose front is the side cell; again `max` over the 2 side cells with a split |
| `back` of gate g = V | dust / strongly powered solid / **container constant** (barrel, item count computed from the level) / a chained gate with the same facing |
| `gateout` at g = V | repeater (`0/15`, so V must be `{0,15}`-shaped) / `sub(K, side)` with a barrel constant K behind it / a copy gate (`out = back`, sides 0) |

Placement legality is applied while expanding (bbox, `forbidden`, no overlap,
supports auto-added under every wire/gate) and the two lints the checker rejects
(L1 support, L2 diagonal wire link) are repaired by two general rewrites before the
oracle is called: *cap the lower wire* / *fill the air cell beside the upper wire*.

**Heuristic** (the thing that made it work): a relaxed forward Dijkstra over states
`(cell, level)` seeded from the pins, whose moves are the same DC rules
(hop `-1` = 1 block, gate relay = 2, gate→solid→any of 6 faces = 3). It answers
"how many blocks, at least, to make cell c carry level ≥ k" while respecting the
walls and the forbidden cells. One table per pin as well: a requirement that is
non-zero in a combination where only pin X is on **must** be fed by X, so the
heuristic sums a penalty for every additional source that is forced.

## Measurements (final code, one consistent sweep; per-problem timeout 600 s)

| problem | solved | wall time | nodes | oracle checks | blocks (max) | checker line |
|---|---|---|---|---|---|---|
| p1_sub2side | yes | 9.9 s | 51 248 | 1 | 8 (18) | `PASS p1_sub2side blocks 8` |
| p2_copy_into_side | yes | 0.1 s | 313 | 8 | 5 (14) | `PASS p2_copy_into_side blocks 5` |
| p3_pkill_bridge | **no — infeasible** | 600 s (timeout) | 1 177 146 | 32 048 | — | (no candidate passed; see below) |
| p4_throughline | yes | 0.9 s | 4 489 | 1 | 17 (22) | `PASS p4_throughline blocks 17` |
| p5_max_merge | yes | 5.8 s | 38 409 | 1 | 9 (16) | `PASS p5_max_merge blocks 9` |
| p6_vertical_cap | yes | 0.5 s | 4 752 | 19 | 6 (12) | `PASS p6_vertical_cap blocks 6` |

"nodes" = requirement expansions; "oracle checks" = complete candidate layouts handed
to `placer0_check.check()`. Note how few candidates reach the oracle: the propagation
does the work, the oracle only confirms (p1/p4/p5: the **first** complete candidate passed).

Solutions are in `sol_<problem>.json`.

### What the program found (it was not told any of this)

* **p1** — `sub(K,side)` at (2,1,3) facing north, with a barrel it filled itself
  (**247 items**, computed from the level it needed through the container formula);
  a into one side through a repeater, Wn into the other through a two-repeater chain
  (a plain wire chain cannot arrive at >= 3 from a level-3 pin), and a **copy
  comparator** at (2,1,4) to carry the result to O losslessly past the forbidden cells.
  8 blocks. (An earlier heuristic setting produced a different 8-block answer that
  over-shot the constant to **level 4 = 371 items** and let one wire hop pay the `-1`;
  the rewrite set allows that trick and the program found it unaided.)
* **p2** — repeater into the **fixed wall block**: the wall becomes a strongly powered
  solid, the wire on the far side reads 15 losslessly, two more repeaters carry it into
  the comparator's side. 5 blocks.
* **p4** — a full 3D route: repeater → solid → repeater → solid → wire at y=2 →
  repeater whose front is the **wall's own block at y=2** → wire on the roof (y=3) →
  repeater → solid → wire down at y=2 → repeater → solid at (7,2,1) → O reads it
  **from below**, exactly 15. 17 blocks, found in 0.9 s.
* **p5** — two `copy` comparators, one per pin, whose fronts point at the **same**
  smooth stone at (2,1,2): the solid holds `max(a,W3)` losslessly, two more copy
  comparators carry it to O exactly. 9 blocks (my own hand-derived shape was 11).
* **p6** — a **double inversion**: `sub(K=1, side=d)` inverts d, a repeater normalises
  it to 0/15, `sub(K=3, side=that)` re-inverts, and its front is the *fixed* solid
  under the y=2 output, so O reads 3/0 through the vertical relay. 6 blocks — and it
  dodged the diagonal-read trap by never placing a y=2 wire at all, which is the
  cheapest way to satisfy the L2 rule rather than the cap the note suggests.

## p3 is infeasible — and that is a property of the problem, not of the search

The program reports UNKNOWN (timeout), which is the honest verdict from the search
alone: it **exhausted every block budget from 9 to 15** (`bound 15 exhausted
nodes=947287 checks=25277 t=402.6`) and ran out of time inside budget 16 = `max_blocks`,
having handed 32 048 complete candidates to the oracle, none of which passed.
The infeasibility itself is proved from the rule replica, not from the search:

1. O = (3,2,4) is the **front** of the fixed comparator c at (3,2,3), so
   `power(O) >= out(c)` always.
2. `out(c) = 0` needs `back == 0` or `side >= back`. The back is the fixed barrel at
   (3,2,2) (988 items = level 9); its output is a constant, so `back = 9` in both rows.
   (Even the checker's barrel-merge loophole — a solution may re-declare a *fixed*
   barrel's contents without spending a block — only replaces one constant by another.)
3. `gate_sides` reads **only** the two cells (4,2,3) and (2,2,3), and only a
   redstone_block / dust / comparator / repeater / torch / lever there emits anything
   (a solid feeds a side nothing).
4. dust, comparator, repeater and torch all fail lint L1 at those cells: the support
   cell below each of them is **(4,1,3) and (2,1,3), both in `forbidden`**.
   A redstone_block is outside the allowed block set, and being a constant 15 it would
   also break the `P=0` row.
5. Therefore `side = 0` in both rows, `out(c) = 9` in both rows, and the row `P=15`
   (expect 0) cannot pass.

Empirical corroboration (`the same shape with the two support blocks placed anyway`):
the Bench sweep gives `P=0 -> O=9`, `P=15 -> O=0`, i.e. electrically correct, and the
checker rejects it with `[('forbidden', (2,1,3)), ('forbidden', (1,1,3))]`.

So p3 needs one of: the support cells removed from `forbidden`, a redstone_block in the
allowed set, or a second output path that can pull O down — none of which exist.
If the intent was "climb elsewhere and arrive at y=2", the two cells the signal has to
arrive at are exactly the two whose floor is forbidden.

## Honest account: what I hand-encoded, and where a human still helped

**Hand-encoded rules** (all general, all in `placer0.py`, transcribed from
`machine.py` / `capcell.py` and the two fact sheets):

1. gate geometry: `facing` points at the **back**; `back = pos+facing`,
   `front = pos-facing`, sides = the two perpendicular neighbours.
2. comparator arithmetic: `0` if back is 0 or side > back, `back-side` (subtract),
   `back` (compare) — and its inverse, `sub_side_spec`.
3. repeater: `15` iff back > 0 — and its inverse, `rep_back_spec`.
4. what a **side** can read (dust power, gate strong output) and what it cannot
   (solids, containers, torches).
5. what a **back** can read (dust, strongly powered solid, container, gate).
6. wire: `max(6-face emitted, best horizontal neighbour - 1)`; gate fronts and
   strongly powered solids are lossless — and its inverse, `inv_hop`.
7. a gate's front strongly powers a solid on **all 6 faces**; several fronts → `max`
   (this is both the vertical relay and the merge).
8. support under every wire/gate (checker lint L1) and the barrel level formula
   `floor(f*14) + (f>0)` with its inverse.
9. the two L2 lint repairs (cap / fill).

**Where the human was still in the loop** — the honest list:

* I chose the **decomposition** (goal = "the output wire reads this vector", requirements
  are ports, not cells). A different framing would need a different program.
* The **max-split** is only implemented for a strongly powered solid and for a gate's two
  side cells. A wire also reads the max of its 6 faces, and I did **not** implement a
  2-source split there (branching); p5 happened to be solvable through the solid.
* The **copy gate** branch assumes its sides end up at 0 instead of asserting it; the
  oracle catches the cases where that is false. Likewise every kind of route-to-route
  interference is caught only by the final check, not by the propagation.
* The **constant K** candidates are taken from the requirement's own lower bounds; a
  problem needing a K that nothing in the requirement mentions would not be found.
* Two heuristic tunings were mine, not derived: the `-1` slack in `h_cell`, and the
  `2*(sources-1)` penalty. Both are safety valves against over-estimating; getting them
  wrong made p2 return a 10-block answer instead of the 5-block one (observed, then fixed).
* Solver libraries: none available (`ortools`, `z3` not importable), so the constraint
  search is the hand-written IDA* above.
* I supplied the **rule replica** by reading `machine.py`/`capcell.py`; the program does
  not read the Java or the fact sheets itself.

**Verdict for the pilot question.** For this class of artifact — a handful of gates,
levels that must be exact, walls and forbidden cells in the way — the coordinate part
does *not* need an LLM. 5 of 6 problems were solved by the program with the first or
near-first complete candidate reaching the oracle, three of them under a second, and on
two of them the program found a *better* placement than the one I derived by hand.
The remaining problem is infeasible, and the same rule table that drives the search is
what proves it. What the LLM was needed for was the **modelling** (which rules, which
ports, which decomposition) and the **debugging of the heuristic** — one-time work, not
per-invocation work, which is exactly the ADR-0059 split.

## Reproduce

```
cd <this directory>
python placer0.py problems.json p1_sub2side      # 8 blocks,  ~10 s
python placer0.py problems.json p2_copy_into_side #  5 blocks,  ~0.1 s
python placer0.py problems.json p4_throughline    # 17 blocks,  ~1 s
python placer0.py problems.json p5_max_merge      #  9 blocks,  ~6 s
python placer0.py problems.json p6_vertical_cap   #  6 blocks,  ~0.5 s
python placer0.py problems.json p3_pkill_bridge -v  # UNKNOWN at 600 s (infeasible)
python placer0_check.py problems.json <name> sol_<name>.json   # the oracle's own PASS line
```

Machine: this session's host, CPython 3.11.9, single process, no solver library
(`ortools` and `z3` are not importable here; `networkx` is, and was not needed).

## Cost of this pilot

* wall time: 50 min from reading `problems.json` to this file (budget was 3 h);
  of that, ~25 min was compute (the two 600 s p3 runs and the search re-runs).
* tokens (this session, measured from the context counter): ~227 k.
