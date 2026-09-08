# WORLD-4 -- five PLACER-0 solutions and two abutting alu_slice_v9 slices in a fresh synthetic world

Worker seat (Opus), 2026-09-08, DIRECTOR 8 order
`docs/world/world4-order.md`. Non-canonical (`notes/**`).

Question, in a void headless 1.20.6 world with no player, driven by
`tools/world/worldprobe.py` exactly as WORLD-2 was:

* **(A)** do the five solvable PLACER-0 solutions
  (`artifacts/placer0/`, p3 excluded as unsatisfiable), placed as
  problem `fixed` cells + solution cells + feeders, read the output level
  `placer0_check.py -v` expects, for every pin combination (14 rows)?
* **(B)** do two abutting slices of `artifacts/layouts/alu_slice_v9.json`
  (`alu_check_slices.tiled(lay,2)`, 584 cells, pitch 12) reproduce the Bench
  for all 128 rows of n=2 -- r0, r1, f -- plus the slice-1 through-line entry
  levels (12,2,0) and (12,3,12), the intermediate carry (12,2,2), and every
  comparator's `powered`?

Written in two passes, exactly as WORLD-1 and WORLD-2: sections 1-4 BEFORE
the world ran, sections 5-8 after. Nothing above section 5 was edited
afterwards.

## 1. The feeders

Both checkers PIN wire cells at a fixed power. A world has no pins, so each
pin needs a physical source, built only from comparator / barrel / wire /
solid / lever, that delivers exactly the pinned level into the pin cell.
Two kinds, both WORLD-1's and WORLD-2's, unchanged:

**Data feeder** (level 0/3). A comparator in **compare** mode whose BACK is a
barrel holding **247 stack-64 items** (247/64 = 3.86 stacks of 27 slots ->
comparator level **3**) and whose SIDE is a lever-driven wire. In compare mode
the gate emits its back level when back >= side and 0 otherwise, so a side
driven to 15 kills it:

* lever ON  -> the lever's base solid is strongly powered 15 -> side wire 15
  -> 15 > 3 -> gate output **0** -> pin level **0**
* lever OFF -> side wire 0 -> 3 >= 0 -> gate output **3** -> pin level **3**

**INVERTED CONVENTION, declared: data lever ON = level 0, lever OFF = level 3.**

**Control feeder** (level 0/15). A solid block beside the pin wire with a
`face=floor` lever on top: lever ON -> base strongly powered 15 -> the pin
wire reads 15; lever OFF -> 0. Lever ON = 15. No gate, no barrel.

Convention, validated by WORLD-1 against a real 1.20.6 server: a comparator or
repeater with `facing=D` has its BACK at `pos+D` and its OUTPUT at `pos-D`.

Every feeder gate's OUTPUT CELL **is** the pin wire, so no cell of any
artifact under test is substituted or moved -- WORLD-2 had to substitute two
inert floor blocks; WORLD-4 substitutes nothing. Positions are in each
artifact's own relative frame (`layout_world4.json`, written by
`make_layout_world4.py`, which raises on any collision with an artifact cell).

| artifact | pin | kind | pin cell | gate | barrel (back) | side wire | lever base | lever |
|---|---|---|---|---|---|---|---|---|
| p1_sub2side | a | data | (0,1,2) | (-1,1,2) facing=west | (-2,1,2) | (-1,1,1) | (-2,1,1) | (-2,2,1) |
| p1_sub2side | Wn | ctrl | (5,1,2) | -- | -- | -- | (6,1,2) | (6,2,2) |
| p2_copy_into_side | a | data | (0,1,0) | (-1,1,0) facing=west | (-2,1,0) | (-1,1,1) | (-2,1,1) | (-2,2,1) |
| p4_throughline | T | ctrl | (0,1,1) | -- | -- | -- | (-1,1,1) | (-1,2,1) |
| p5_max_merge | a | data | (0,1,0) | (-1,1,0) facing=west | (-2,1,0) | (-1,1,1) | (-2,1,1) | (-2,2,1) |
| p5_max_merge | W3 | data | (0,1,4) | (-1,1,4) facing=west | (-2,1,4) | (-1,1,5) | (-2,1,5) | (-2,2,5) |
| p6_vertical_cap | d | data | (2,1,0) | (2,1,-1) facing=north | (2,1,-2) | (3,1,-1) | (4,1,-1) | (4,2,-1) |
| p6_vertical_cap | N | ctrl | (0,1,2) | -- | -- | -- | (-1,1,2) | (-1,2,2) |
| slice_v9_n2 | P | ctrl | (0,2,0) | -- | -- | -- | (-1,2,0) | (-1,3,0) |
| slice_v9_n2 | Wn | ctrl | (0,3,12) | -- | -- | -- | (-1,3,12) | (-1,4,12) |
| slice_v9_n2 | k | data | (0,2,2) | (-1,2,2) facing=west | (-2,2,2) | (-1,2,3) | (-2,2,3) | (-2,3,3) |
| slice_v9_n2 | b0 | data | (0,3,6) | (-1,3,6) facing=west | (-2,3,6) | (-1,3,7) | (-2,3,7) | (-2,4,7) |
| slice_v9_n2 | b1 | data | (12,3,6) | (11,3,6) facing=west | (10,3,6) | (11,3,7) | (10,3,7) | (10,4,7) |
| slice_v9_n2 | a0 | data | (10,1,13) | (10,1,14) facing=south | (10,1,15) | (11,1,14) | (12,1,14) | (12,2,14) |
| slice_v9_n2 | a1 | data | (22,1,13) | (22,1,14) facing=south | (22,1,15) | (23,1,14) | (24,1,14) | (24,2,14) |

Every gate also gets a support solid under it and every side wire a support
solid under it. Each data feeder is 7 cells, each control feeder 2.

### Why these cells, for the slice

The five slice pins are the awkward ones, because three of them sit inside
the tiled footprint rather than at its edge. Every candidate cell's six
neighbours were enumerated in the tiled n=2 layout before it was chosen:

* **b1 (12,3,6)** is a top-face port in the middle of the tiling. The gate
  goes at **(11,3,6) facing=west** with a support solid at (11,2,6), as the
  order suggests. Both cells are empty, and their only occupied neighbours
  are the pin wire (12,3,6) and the barrel (12,2,6) -- a barrel reads no
  power, so the added support is inert.
* the b1 side wire is **(11,3,7)**, not (11,3,5): (11,3,5) is the SIDE of the
  slice's own comparator (12,3,5) (facing=south, back = the b1 pin), so a
  lever-driven wire there would drive that gate's side. (11,3,7) has no
  occupied neighbour at all.
* the a0 side wire is **(11,1,14)**, not (9,1,14): (9,1,14) is the SIDE of the
  slice's comparator (9,1,13) (facing=east). Same for a1 at (23,1,14).
* the k side wire is **(-1,2,3)**, not (-1,2,1): (-1,2,1) touches (-1,2,0),
  which is the P control feeder's lever base, so with P=15 the k side would
  read 15 whatever the k lever did.

### The f readout

`f` of the tiled pair is the comparator **(23,2,2)** (slice 1's f, `facing=west`),
whose output cell **(24,2,2)** is air. A wire is added there, plus its support
(24,1,2), so f can be read as a wire power. Its only occupied neighbours are
the comparator itself and its own support. The Bench confirms the addition is
free: **`f_wire == f_cmp` in all 128 rows**, and the sweep stays 128/128.

### The six artifacts, and the world they share

| artifact | cells | of which feeder+readout | barrels | levers | comparators | repeaters | world z |
|---|---|---|---|---|---|---|---|
| p1_sub2side | 56 | 9 | 2 | 2 | 3 | 3 | 100..105 |
| p2_copy_into_side | 62 | 7 | 2 | 1 | 2 | 3 | 120..125 |
| p4_throughline | 69 | 2 | 0 | 1 | 0 | 5 | 140..143 |
| p5_max_merge | 56 | 14 | 2 | 2 | 8 | 0 | 160..165 |
| p6_vertical_cap | 45 | 9 | 3 | 2 | 3 | 1 | 178..184 |
| slice_v9_n2 | 625 | 41 | 19 | 7 | 105 | 34 | 200..215 |

**913 blocks, 28 block entities** in one void world, base `100,64,100`,
bbox `97 63 99 .. 125 69 216`, one region `r.0.0.mca`. The six artifacts are
laid out along z with their origins 20 z apart (the slice at z+100); the
smallest gap between two artifacts' occupied z ranges is **12 cells**
(p5 ends at z=165, p6 starts at z=178), so no artifact is a neighbour of
another. `alu_check2.lint` reports **L1 = 0 and L2 = 0 on every one of the
six fed layouts**.

## 2. Bench prediction (run BEFORE the world)

`bench_sweep_feed4.py layout_world4.json` -- same `capcell.Bench` the two
checkers use, **no pins at all**: the lever states are set in the block
states and `dc_solve()` resolves feeders and artifact together.

### (A) the 14 PLACER-0 rows

`expect` is `placer0_check.py`'s own expression evaluated on the pin levels;
these are the values `placer0_check.py -v` prints.

| artifact | pins | levers ON | Bench O | expect | equal | rounds |
|---|---|---|---|---|---|---|
| p1_sub2side | Wn=0 a=0 | p1_a | 3 | 3 | yes | 2 |
| p1_sub2side | Wn=15 a=0 | p1_a p1_wn | 0 | 0 | yes | 4 |
| p1_sub2side | Wn=0 a=3 | -- | 0 | 0 | yes | 3 |
| p1_sub2side | Wn=15 a=3 | p1_wn | 0 | 0 | yes | 3 |
| p2_copy_into_side | a=0 | p2_a | 3 | 3 | yes | 2 |
| p2_copy_into_side | a=3 | -- | 0 | 0 | yes | 4 |
| p4_throughline | T=0 | -- | 0 | 0 | yes | 1 |
| p4_throughline | T=15 | p4_t | 15 | 15 | yes | 6 |
| p5_max_merge | W3=0 a=0 | p5_a p5_w3 | 0 | 0 | yes | 1 |
| p5_max_merge | W3=3 a=0 | p5_a | 3 | 3 | yes | 4 |
| p5_max_merge | W3=0 a=3 | p5_w3 | 3 | 3 | yes | 4 |
| p5_max_merge | W3=3 a=3 | -- | 3 | 3 | yes | 4 |
| p6_vertical_cap | N=15 d=0 | p6_d p6_n | 0 | 0 | yes | 2 |
| p6_vertical_cap | N=15 d=3 | p6_n | 3 | 3 | yes | 3 |

**PASS 14/14**, every row converged. The feeders reproduce the pinned result
on all five artifacts.

### (B) the 128 slice rows

Levels are wire powers. `r0` = (6,3,9), `r1` = (18,3,9), `f` = the added wire
(24,2,2), `thrP` = (12,2,0), `thrWn` = (12,3,12), `carry` = (12,2,2). `exp`
columns: r0/r1/f from the PINNED Bench (`alu_check_slices.run`) for the same
row, thrP/thrWn from the pin levels, carry from
`alu_check_contract.expected_carry(mode, A, B, k, 1) * 3`.

| mode | A | B | k | r0 | r1 | f | thrP | thrWn | carry | R | F | relation | equal |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ADD | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 15 | 0 | 0 | 0 | ok | yes |
| ADD | 0 | 0 | 1 | 3 | 0 | 0 | 0 | 15 | 0 | 1 | 0 | ok | yes |
| ADD | 0 | 1 | 0 | 3 | 0 | 0 | 0 | 15 | 0 | 1 | 0 | ok | yes |
| ADD | 0 | 1 | 1 | 0 | 3 | 0 | 0 | 15 | 3 | 2 | 0 | ok | yes |
| ADD | 0 | 2 | 0 | 0 | 3 | 0 | 0 | 15 | 0 | 2 | 0 | ok | yes |
| ADD | 0 | 2 | 1 | 3 | 3 | 0 | 0 | 15 | 0 | 3 | 0 | ok | yes |
| ADD | 0 | 3 | 0 | 3 | 3 | 0 | 0 | 15 | 0 | 3 | 0 | ok | yes |
| ADD | 0 | 3 | 1 | 0 | 0 | 3 | 0 | 15 | 3 | 0 | 1 | ok | yes |
| ADD | 1 | 0 | 0 | 3 | 0 | 0 | 0 | 15 | 0 | 1 | 0 | ok | yes |
| ADD | 1 | 0 | 1 | 0 | 3 | 0 | 0 | 15 | 3 | 2 | 0 | ok | yes |
| ADD | 1 | 1 | 0 | 0 | 3 | 0 | 0 | 15 | 3 | 2 | 0 | ok | yes |
| ADD | 1 | 1 | 1 | 3 | 3 | 0 | 0 | 15 | 3 | 3 | 0 | ok | yes |
| ADD | 1 | 2 | 0 | 3 | 3 | 0 | 0 | 15 | 0 | 3 | 0 | ok | yes |
| ADD | 1 | 2 | 1 | 0 | 0 | 3 | 0 | 15 | 3 | 0 | 1 | ok | yes |
| ADD | 1 | 3 | 0 | 0 | 0 | 3 | 0 | 15 | 3 | 0 | 1 | ok | yes |
| ADD | 1 | 3 | 1 | 3 | 0 | 3 | 0 | 15 | 3 | 1 | 1 | ok | yes |
| ADD | 2 | 0 | 0 | 0 | 3 | 0 | 0 | 15 | 0 | 2 | 0 | ok | yes |
| ADD | 2 | 0 | 1 | 3 | 3 | 0 | 0 | 15 | 0 | 3 | 0 | ok | yes |
| ADD | 2 | 1 | 0 | 3 | 3 | 0 | 0 | 15 | 0 | 3 | 0 | ok | yes |
| ADD | 2 | 1 | 1 | 0 | 0 | 3 | 0 | 15 | 3 | 0 | 1 | ok | yes |
| ADD | 2 | 2 | 0 | 0 | 0 | 3 | 0 | 15 | 0 | 0 | 1 | ok | yes |
| ADD | 2 | 2 | 1 | 3 | 0 | 3 | 0 | 15 | 0 | 1 | 1 | ok | yes |
| ADD | 2 | 3 | 0 | 3 | 0 | 3 | 0 | 15 | 0 | 1 | 1 | ok | yes |
| ADD | 2 | 3 | 1 | 0 | 3 | 3 | 0 | 15 | 3 | 2 | 1 | ok | yes |
| ADD | 3 | 0 | 0 | 3 | 3 | 0 | 0 | 15 | 0 | 3 | 0 | ok | yes |
| ADD | 3 | 0 | 1 | 0 | 0 | 3 | 0 | 15 | 3 | 0 | 1 | ok | yes |
| ADD | 3 | 1 | 0 | 0 | 0 | 3 | 0 | 15 | 3 | 0 | 1 | ok | yes |
| ADD | 3 | 1 | 1 | 3 | 0 | 3 | 0 | 15 | 3 | 1 | 1 | ok | yes |
| ADD | 3 | 2 | 0 | 3 | 0 | 3 | 0 | 15 | 0 | 1 | 1 | ok | yes |
| ADD | 3 | 2 | 1 | 0 | 3 | 3 | 0 | 15 | 3 | 2 | 1 | ok | yes |
| ADD | 3 | 3 | 0 | 0 | 3 | 3 | 0 | 15 | 3 | 2 | 1 | ok | yes |
| ADD | 3 | 3 | 1 | 3 | 3 | 3 | 0 | 15 | 3 | 3 | 1 | ok | yes |
| SUB | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | ok | yes |
| SUB | 0 | 0 | 1 | 3 | 3 | 3 | 0 | 0 | 3 | 3 | 1 | ok | yes |
| SUB | 0 | 1 | 0 | 3 | 3 | 3 | 0 | 0 | 3 | 3 | 1 | ok | yes |
| SUB | 0 | 1 | 1 | 0 | 3 | 3 | 0 | 0 | 3 | 2 | 1 | ok | yes |
| SUB | 0 | 2 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 2 | 1 | ok | yes |
| SUB | 0 | 2 | 1 | 3 | 0 | 3 | 0 | 0 | 3 | 1 | 1 | ok | yes |
| SUB | 0 | 3 | 0 | 3 | 0 | 3 | 0 | 0 | 3 | 1 | 1 | ok | yes |
| SUB | 0 | 3 | 1 | 0 | 0 | 3 | 0 | 0 | 3 | 0 | 1 | ok | yes |
| SUB | 1 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | ok | yes |
| SUB | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | ok | yes |
| SUB | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | ok | yes |
| SUB | 1 | 1 | 1 | 3 | 3 | 3 | 0 | 0 | 3 | 3 | 1 | ok | yes |
| SUB | 1 | 2 | 0 | 3 | 3 | 3 | 0 | 0 | 0 | 3 | 1 | ok | yes |
| SUB | 1 | 2 | 1 | 0 | 3 | 3 | 0 | 0 | 0 | 2 | 1 | ok | yes |
| SUB | 1 | 3 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 2 | 1 | ok | yes |
| SUB | 1 | 3 | 1 | 3 | 0 | 3 | 0 | 0 | 3 | 1 | 1 | ok | yes |
| SUB | 2 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 2 | 0 | ok | yes |
| SUB | 2 | 0 | 1 | 3 | 0 | 0 | 0 | 0 | 3 | 1 | 0 | ok | yes |
| SUB | 2 | 1 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 1 | 0 | ok | yes |
| SUB | 2 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | ok | yes |
| SUB | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | ok | yes |
| SUB | 2 | 2 | 1 | 3 | 3 | 3 | 0 | 0 | 3 | 3 | 1 | ok | yes |
| SUB | 2 | 3 | 0 | 3 | 3 | 3 | 0 | 0 | 3 | 3 | 1 | ok | yes |
| SUB | 2 | 3 | 1 | 0 | 3 | 3 | 0 | 0 | 3 | 2 | 1 | ok | yes |
| SUB | 3 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 0 | 3 | 0 | ok | yes |
| SUB | 3 | 0 | 1 | 0 | 3 | 0 | 0 | 0 | 0 | 2 | 0 | ok | yes |
| SUB | 3 | 1 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 2 | 0 | ok | yes |
| SUB | 3 | 1 | 1 | 3 | 0 | 0 | 0 | 0 | 3 | 1 | 0 | ok | yes |
| SUB | 3 | 2 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | ok | yes |
| SUB | 3 | 2 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | ok | yes |
| SUB | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | ok | yes |
| SUB | 3 | 3 | 1 | 3 | 3 | 3 | 0 | 0 | 3 | 3 | 1 | ok | yes |
| AND | 0 | 0 | 0 | 0 | 0 | 0 | 15 | 15 | 0 | 0 | 0 | ok | yes |
| AND | 0 | 0 | 1 | 0 | 0 | 0 | 15 | 15 | 0 | 0 | 0 | ok | yes |
| AND | 0 | 1 | 0 | 0 | 0 | 0 | 15 | 15 | 0 | 0 | 0 | ok | yes |
| AND | 0 | 1 | 1 | 0 | 0 | 0 | 15 | 15 | 0 | 0 | 0 | ok | yes |
| AND | 0 | 2 | 0 | 0 | 0 | 0 | 15 | 15 | 0 | 0 | 0 | ok | yes |
| AND | 0 | 2 | 1 | 0 | 0 | 0 | 15 | 15 | 0 | 0 | 0 | ok | yes |
| AND | 0 | 3 | 0 | 0 | 0 | 0 | 15 | 15 | 0 | 0 | 0 | ok | yes |
| AND | 0 | 3 | 1 | 0 | 0 | 0 | 15 | 15 | 0 | 0 | 0 | ok | yes |
| AND | 1 | 0 | 0 | 0 | 0 | 0 | 15 | 15 | 0 | 0 | 0 | ok | yes |
| AND | 1 | 0 | 1 | 0 | 0 | 0 | 15 | 15 | 0 | 0 | 0 | ok | yes |
| AND | 1 | 1 | 0 | 3 | 0 | 0 | 15 | 15 | 0 | 1 | 0 | ok | yes |
| AND | 1 | 1 | 1 | 3 | 0 | 0 | 15 | 15 | 0 | 1 | 0 | ok | yes |
| AND | 1 | 2 | 0 | 0 | 0 | 0 | 15 | 15 | 0 | 0 | 0 | ok | yes |
| AND | 1 | 2 | 1 | 0 | 0 | 0 | 15 | 15 | 0 | 0 | 0 | ok | yes |
| AND | 1 | 3 | 0 | 3 | 0 | 0 | 15 | 15 | 0 | 1 | 0 | ok | yes |
| AND | 1 | 3 | 1 | 3 | 0 | 0 | 15 | 15 | 0 | 1 | 0 | ok | yes |
| AND | 2 | 0 | 0 | 0 | 0 | 0 | 15 | 15 | 0 | 0 | 0 | ok | yes |
| AND | 2 | 0 | 1 | 0 | 0 | 0 | 15 | 15 | 0 | 0 | 0 | ok | yes |
| AND | 2 | 1 | 0 | 0 | 0 | 0 | 15 | 15 | 0 | 0 | 0 | ok | yes |
| AND | 2 | 1 | 1 | 0 | 0 | 0 | 15 | 15 | 0 | 0 | 0 | ok | yes |
| AND | 2 | 2 | 0 | 0 | 3 | 0 | 15 | 15 | 0 | 2 | 0 | ok | yes |
| AND | 2 | 2 | 1 | 0 | 3 | 0 | 15 | 15 | 0 | 2 | 0 | ok | yes |
| AND | 2 | 3 | 0 | 0 | 3 | 0 | 15 | 15 | 0 | 2 | 0 | ok | yes |
| AND | 2 | 3 | 1 | 0 | 3 | 0 | 15 | 15 | 0 | 2 | 0 | ok | yes |
| AND | 3 | 0 | 0 | 0 | 0 | 0 | 15 | 15 | 0 | 0 | 0 | ok | yes |
| AND | 3 | 0 | 1 | 0 | 0 | 0 | 15 | 15 | 0 | 0 | 0 | ok | yes |
| AND | 3 | 1 | 0 | 3 | 0 | 0 | 15 | 15 | 0 | 1 | 0 | ok | yes |
| AND | 3 | 1 | 1 | 3 | 0 | 0 | 15 | 15 | 0 | 1 | 0 | ok | yes |
| AND | 3 | 2 | 0 | 0 | 3 | 0 | 15 | 15 | 0 | 2 | 0 | ok | yes |
| AND | 3 | 2 | 1 | 0 | 3 | 0 | 15 | 15 | 0 | 2 | 0 | ok | yes |
| AND | 3 | 3 | 0 | 3 | 3 | 0 | 15 | 15 | 0 | 3 | 0 | ok | yes |
| AND | 3 | 3 | 1 | 3 | 3 | 0 | 15 | 15 | 0 | 3 | 0 | ok | yes |
| OR | 0 | 0 | 0 | 0 | 0 | 0 | 15 | 0 | 0 | 0 | 0 | ok | yes |
| OR | 0 | 0 | 1 | 0 | 0 | 0 | 15 | 0 | 0 | 0 | 0 | ok | yes |
| OR | 0 | 1 | 0 | 3 | 0 | 0 | 15 | 0 | 0 | 1 | 0 | ok | yes |
| OR | 0 | 1 | 1 | 3 | 0 | 0 | 15 | 0 | 0 | 1 | 0 | ok | yes |
| OR | 0 | 2 | 0 | 0 | 3 | 0 | 15 | 0 | 0 | 2 | 0 | ok | yes |
| OR | 0 | 2 | 1 | 0 | 3 | 0 | 15 | 0 | 0 | 2 | 0 | ok | yes |
| OR | 0 | 3 | 0 | 3 | 3 | 0 | 15 | 0 | 0 | 3 | 0 | ok | yes |
| OR | 0 | 3 | 1 | 3 | 3 | 0 | 15 | 0 | 0 | 3 | 0 | ok | yes |
| OR | 1 | 0 | 0 | 3 | 0 | 0 | 15 | 0 | 0 | 1 | 0 | ok | yes |
| OR | 1 | 0 | 1 | 3 | 0 | 0 | 15 | 0 | 0 | 1 | 0 | ok | yes |
| OR | 1 | 1 | 0 | 3 | 0 | 0 | 15 | 0 | 0 | 1 | 0 | ok | yes |
| OR | 1 | 1 | 1 | 3 | 0 | 0 | 15 | 0 | 0 | 1 | 0 | ok | yes |
| OR | 1 | 2 | 0 | 3 | 3 | 0 | 15 | 0 | 0 | 3 | 0 | ok | yes |
| OR | 1 | 2 | 1 | 3 | 3 | 0 | 15 | 0 | 0 | 3 | 0 | ok | yes |
| OR | 1 | 3 | 0 | 3 | 3 | 0 | 15 | 0 | 0 | 3 | 0 | ok | yes |
| OR | 1 | 3 | 1 | 3 | 3 | 0 | 15 | 0 | 0 | 3 | 0 | ok | yes |
| OR | 2 | 0 | 0 | 0 | 3 | 0 | 15 | 0 | 0 | 2 | 0 | ok | yes |
| OR | 2 | 0 | 1 | 0 | 3 | 0 | 15 | 0 | 0 | 2 | 0 | ok | yes |
| OR | 2 | 1 | 0 | 3 | 3 | 0 | 15 | 0 | 0 | 3 | 0 | ok | yes |
| OR | 2 | 1 | 1 | 3 | 3 | 0 | 15 | 0 | 0 | 3 | 0 | ok | yes |
| OR | 2 | 2 | 0 | 0 | 3 | 0 | 15 | 0 | 0 | 2 | 0 | ok | yes |
| OR | 2 | 2 | 1 | 0 | 3 | 0 | 15 | 0 | 0 | 2 | 0 | ok | yes |
| OR | 2 | 3 | 0 | 3 | 3 | 0 | 15 | 0 | 0 | 3 | 0 | ok | yes |
| OR | 2 | 3 | 1 | 3 | 3 | 0 | 15 | 0 | 0 | 3 | 0 | ok | yes |
| OR | 3 | 0 | 0 | 3 | 3 | 0 | 15 | 0 | 0 | 3 | 0 | ok | yes |
| OR | 3 | 0 | 1 | 3 | 3 | 0 | 15 | 0 | 0 | 3 | 0 | ok | yes |
| OR | 3 | 1 | 0 | 3 | 3 | 0 | 15 | 0 | 0 | 3 | 0 | ok | yes |
| OR | 3 | 1 | 1 | 3 | 3 | 0 | 15 | 0 | 0 | 3 | 0 | ok | yes |
| OR | 3 | 2 | 0 | 3 | 3 | 0 | 15 | 0 | 0 | 3 | 0 | ok | yes |
| OR | 3 | 2 | 1 | 3 | 3 | 0 | 15 | 0 | 0 | 3 | 0 | ok | yes |
| OR | 3 | 3 | 0 | 3 | 3 | 0 | 15 | 0 | 0 | 3 | 0 | ok | yes |
| OR | 3 | 3 | 1 | 3 | 3 | 0 | 15 | 0 | 0 | 3 | 0 | ok | yes |

**PASS 128/128**: every row converged, every r/f is exactly 0 or 3, the
ADD/SUB/AND/OR relation holds in all 128, `f_wire == f_cmp` in all 128, the
two through-line entries equal their pin levels in all 128, and the
intermediate carry equals `3 * expected_carry` in all 128. The 105
comparators (100 slice + 5 feeder) carry their own per-row expectation:
`cmp_out > 0`, which the Bench's own `powered` block state equals in every
row of both parts (checked, `powered_agrees` true everywhere).

## 3. What the world is asked, and what a match means

Four specs, one world, `tick freeze`, lever drive, `step` 1 gt at a time to
`max_gt=40` with `settle_gt=10`, rcon port 25598, `java_xmx 3G`, template
`<host-path>/carpet-work`. Relative (x,y,z) of
an artifact with origin z0 is world (100+x, 64+y, 100+z0+z).

**Why four specs and not one.** `run_regime` steps to `max_gt`
unconditionally, so a regime costs `(max_gt+1) x (state reads)` rcon
roundtrips. Part B reads 117 state points (12 levels + 105 comparators),
about 5,039 roundtrips per regime measured against the order's own formula;
256 regimes would be ~1.29 M, four times past the 600,000 ceiling the order
sets on `limits.max_rcon`. **Deviation, declared:** part B is cut into three
runs over the same built world (`worldprobe` copies the world into its run
dir and never writes the source), each carrying a third of the 128 rows
(43/43/42, assigned by row index mod 3 so every chunk spans all four ops and
all A, B, k). Each run is self-contained: two wake regimes, then that chunk's
warm pass, then that chunk's recorded pass. The order's `warm 128 -> v 128`
is preserved row for row; only the world reload between chunks is added.

| spec | reads | regimes | est. rcon | rows |
|---|---|---|---|---|
| world4a | 39 | 28 | ~50400 | 14 (A) |
| world4b1 | 118 | 88 | ~443432 | 43 (B) |
| world4b2 | 118 | 88 | ~443432 | 43 (B) |
| world4b3 | 118 | 86 | ~433354 | 42 (B) |

**Part A**, `world4a.spec.json`: 39 read points. 10 carry bits -- one per
(output cell, candidate level) pair, so a third level shows up as a reading
(both bits 0) instead of being folded silently into "not 3":

| bit | read | cell (relative) | match |
|---|---|---|---|
| 0 | p1_O_0 | world (102, 65, 105) | `minecraft:redstone_wire[power=0]` |
| 1 | p1_O_3 | world (102, 65, 105) | `minecraft:redstone_wire[power=3]` |
| 2 | p2_O_0 | world (103, 65, 123) | `minecraft:redstone_wire[power=0]` |
| 3 | p2_O_3 | world (103, 65, 123) | `minecraft:redstone_wire[power=3]` |
| 4 | p4_O_0 | world (107, 65, 141) | `minecraft:redstone_wire[power=0]` |
| 5 | p4_O_15 | world (107, 65, 141) | `minecraft:redstone_wire[power=15]` |
| 6 | p5_O_0 | world (105, 65, 162) | `minecraft:redstone_wire[power=0]` |
| 7 | p5_O_3 | world (105, 65, 162) | `minecraft:redstone_wire[power=3]` |
| 8 | p6_O_0 | world (102, 66, 183) | `minecraft:redstone_wire[power=0]` |
| 9 | p6_O_3 | world (102, 66, 183) | `minecraft:redstone_wire[power=3]` |

29 more reads take `powered` on every comparator (16) and every repeater (13)
of the five artifacts and their feeders, with the Bench's `cmp_out > 0` /
`powered` as the expectation; one `nbt` read takes `Items[3]` of the p1
feeder barrel, where a wrongly written 247 = 3*64 + 55 would show. 28
regimes: for each artifact in turn, its whole pin sweep as `warm_*`, then the
same sweep as `v_*`. Every `v_*` regime carries a FULL expectation over all
39 reads -- the four artifacts that are not sweeping are held at their first
combination, whose Bench answer is equally known -- so part A compares
14 x 38 = 532 read points on its recorded rows.

**Part B**, `world4b{1,2,3}.spec.json`: 118 read points. 12 carry bits:

| bit | read | cell (relative) | match |
|---|---|---|---|
| 0 | s_carry_0 | world (112, 66, 202) | `minecraft:redstone_wire[power=0]` |
| 1 | s_carry_3 | world (112, 66, 202) | `minecraft:redstone_wire[power=3]` |
| 2 | s_f_0 | world (124, 66, 202) | `minecraft:redstone_wire[power=0]` |
| 3 | s_f_3 | world (124, 66, 202) | `minecraft:redstone_wire[power=3]` |
| 4 | s_r0_0 | world (106, 67, 209) | `minecraft:redstone_wire[power=0]` |
| 5 | s_r0_3 | world (106, 67, 209) | `minecraft:redstone_wire[power=3]` |
| 6 | s_r1_0 | world (118, 67, 209) | `minecraft:redstone_wire[power=0]` |
| 7 | s_r1_3 | world (118, 67, 209) | `minecraft:redstone_wire[power=3]` |
| 8 | s_thrP_0 | world (112, 66, 200) | `minecraft:redstone_wire[power=0]` |
| 9 | s_thrP_15 | world (112, 66, 200) | `minecraft:redstone_wire[power=15]` |
| 10 | s_thrWn_0 | world (112, 67, 212) | `minecraft:redstone_wire[power=0]` |
| 11 | s_thrWn_15 | world (112, 67, 212) | `minecraft:redstone_wire[power=15]` |

105 more reads take `comparator[powered=true]` on every comparator of the
tiled pair (100) and of its five data feeders (5); one `nbt` read takes
`Items[3]` of the a1 feeder barrel. Over the 128 recorded rows that is
**128 x 105 = 13,440 comparator comparisons**, of which **12,800 are on the
slice's own gates**, plus 128 x 12 = 1,536 level predicates.

## 4. The warm-up sweep, and why every row is driven twice

A world written straight into region files carries whatever states the writer
put in the palette, and no redstone update ever runs over it. Every
comparator loads `powered=false` with output signal 0 and every wire loads
`power=0` -- a lie everywhere a back is a barrel. A gate recomputes only when
a neighbour's block state changes, so a gate whose stale state happens to
equal the answer for the row under test is never woken, and one stale gate
upstream poisons every reading downstream of it. WORLD-2 measured this
biting: its second warm-up regime read `final_value` 10 where the Bench said
9, i.e. a run without the warm-up pass would have recorded a wrong `r`.

So every row is driven **twice**: once as a `warm_*` regime whose readings are
recorded but not compared against the Bench, then once as `v_*`. No Bench
answer is written into the world -- the warm-up is lever flips only, and its
readings stay in the result file so the discarded pass is auditable.

Each part-B run additionally opens with two wake regimes, `wake_on` (all 15
levers ON) and `wake_off` (all 15 OFF). Inside a chunk of 43 rows some lever
may never have to change -- and a lever that never changes delivers no
neighbour update, so its feeder gate could stay stale through the whole run.
The two wake regimes make every lever change state twice before that chunk's
warm pass begins. Their readings are recorded and not compared.

Prediction for the warm-up passes themselves: the early warm rows may read
anything; the late ones should already agree with section 2. WORLD-1 found
the hazard did not bite, WORLD-2 found it did, in exactly its first two
regimes. Here the two wake regimes precede every part-B warm pass, so the
prediction is that part B's `warm_*` rows agree with their `v_*`
counterparts throughout, and that part A -- which has no wake regimes -- may
disagree in its first regime or two.

## 5. The world runs

`tools/world/worldprobe.py run` five times over the SAME void
world built by `build_world4.py` (`worldprobe` copies the world into its own
run dir and never writes the source), template
`<host-path>/carpet-work`, rcon 25598, exit 0
and `completed: true` every time. `tick query` answered "The game is frozen"
and the scarpet probe answered `= 5` in all five.

| run | spec sha256 (head) | utc | regimes | rcon of 600,000 | wall |
|---|---|---|---|---|---|
| world4a | `98af6dfd` | 2026-09-08T09:58:10Z | 28 | 51859 | ~2 min |
| world4b1 | `d2563f93` | 2026-09-08T10:04:53Z | 88 | 443356 | 4 min 18 s |
| world4b2 | `91a7134c` | 2026-09-08T10:09:11Z | 88 | 443226 | 4 min 11 s |
| world4b3 | `02994f36` | 2026-09-08T10:13:23Z | 86 | 432819 | 4 min 31 s |
| world4x | `d3affa21` | 2026-09-08T10:18:09Z | 5 | 5977 | ~1 min |

The world is the void save `build_world4.py` wrote into the scratchpad: **913
blocks, 28 block entities**, one region `r.0.0.mca`, DataVersion 3839
(template also 3839), no player, no terrain. Both nbt reads came back
identical before and after every sweep:

```
data get block 98 65 102 Items[3]     (p1 feeder barrel)
-> 98, 65, 102 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}
data get block 122 65 215 Items[3]    (slice a1 feeder barrel)
-> 122, 65, 215 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}
```

3 x 64 + 55 = 247, in the 1.20.5+ item spelling (`count`, int), and the game
parsed it -- which is what makes the ten data feeders emit 3 at all.

`world4x` is a follow-up spec (`make_diag4.py`) that asks the same world one
extra question about `p4_throughline`; it is described in section 7 and
carries no expectation.

## 6. Table

Astra's four items per artifact. **Bench PASS** is section 2. **world rows**
are the recorded (`v_*`) regimes in which that artifact was the one being
swept; **world FAIL** counts those whose whole expectation did not hold.
**read pts / mismatched / rate** count individual read points on that
artifact's own cells over those rows (output levels + comparator/repeater
`powered`). **settle gt** is `first_stable_gt` -- the first gt after which
every read predicate held for 10 gt. **blocks** is what was placed: the
artifact's own cells plus its feeders and readout.

| artifact | blocks (artifact + feeders) | Bench PASS | world rows | world FAIL | read pts | mismatched | mismatch rate | settle gt |
|---|---|---|---|---|---|---|---|---|
| p1_sub2side | 56 (47 + 9) | 4/4 | 4 | **0** | 32 | 0 | 0.000 | 4..8 |
| p2_copy_into_side | 62 (55 + 7) | 2/2 | 2 | **0** | 14 | 0 | 0.000 | 10..10 |
| p4_throughline | 69 (67 + 2) | 2/2 | 2 | **1** | 14 | 7 | 0.500 | 0..0 |
| p5_max_merge | 56 (42 + 14) | 4/4 | 4 | **0** | 40 | 0 | 0.000 | 6..10 |
| p6_vertical_cap | 45 (36 + 9) | 2/2 | 2 | **0** | 12 | 0 | 0.000 | 8..8 |
| slice_v9_n2 (n=2) | 625 (584 + 41) | 128/128 | 128 | **0** | 14976 | 0 | 0.000 | 4..28 (13 rows unsettled) |

**(A) 4 of the 5 PLACER-0 solutions reproduce the Bench in the world for
every pin combination; `p4_throughline` does not.** 13 of the 14 recorded
rows match at every read point -- 98 of 98 on p1, p2, p5 and p6, and 7 of 7
on p4's `v_p4_T15` -- and one does not: `v_p4_T0`, where all 7 of p4's read
points disagree (section 7). Counting read points over all 14 rows, part A
is 105 of 112 equal.

**(B) the two abutting slices reproduce the Bench in all 128 rows, at every
read point: 14,976 comparisons, 0 unequal.** That is 128 x 12 = 1,536 level
predicates -- r0 (6,3,9), r1 (18,3,9), the added f wire (24,2,2), the
through-line entries (12,2,0) and (12,3,12), the intermediate carry (12,2,2),
each read at both candidate levels -- plus 128 x 105 = 13,440 comparator
`powered` comparisons, of which **12,800 are on the slice's own 100 gates**.
Every `warm_*` row also has `final_bits` identical to its `v_*` counterpart,
in all 128.

## 7. The difference, and the first counterexample

### 7.1 The one artifact that differs: `p4_throughline` at T = 0

Chronologically the first mismatched read point of the whole run is
`p2_O_0` in `v_p1_Wn0a0` -- but that is the warm-up hazard, not a difference
of the artifact (section 8.2), and it is gone the moment p2's own warm pass
runs. **The first mismatch on an artifact under its own sweep, and the only
one in either part, is `v_p4_T0`.**

Cell by cell, in p4's own frame (world = (100+x, 64+y, 140+z)):

| cell | block | Bench says (T=0) | world reads (`v_p4_T0`) |
|---|---|---|---|
| (0,1,1) | `redstone_wire` -- the **T pin** | power 0 | **power 15** |
| (0,1,2) | `repeater[facing=north]` | powered=false | **powered=true** (locked=false) |
| (1,1,2) | `repeater[facing=south]` | powered=false | **powered=true** (locked=false) |
| (2,2,1) | `repeater[facing=west]` | powered=false | **powered=true** (locked=false) |
| (4,3,1) | `repeater[facing=west]` | powered=false | **powered=true** (locked=false) |
| (6,2,1) | `repeater[facing=west]` | powered=false | **powered=true** (locked=false) |
| (1,1,3), (1,2,1), (3,3,1), (5,2,1) | `redstone_wire` (the chain) | power 0 | **power 15** |
| (7,1,1) | `redstone_wire` -- the **output O** | power 0 | **power 15** |

The world never moved: `v_p4_T0` has `settle_gt = 0` and
`last_change_gt = 0`, i.e. the reading at gt 0 was already the reading at
gt 40, and `levers_changed = 1` records that the T lever WAS written to
`powered=false` and the attachment update WAS delivered. Turning the source
off changes nothing: the through-line is latched.

### 7.2 The mechanism, measured

`world4x.spec.json` (`make_diag4.py`) drives the same world T = 0, 15, 0, 15,
0 with a read on every wire of the through-line and on `locked` of every
repeater. Final readings:

| regime | T (0,1,1) | (1,1,3) | (1,2,1) | (3,3,1) | (5,2,1) | O (7,1,1) | repeaters | any locked |
|---|---|---|---|---|---|---|---|---|
| x0_T0 | 0 | 0 | 0 | 0 | 0 | 0 | 0/5 on | 0 |
| x1_T15 | 15 | 15 | 15 | 15 | 15 | 15 | 5/5 on | 0 |
| x2_T0 | 15 | 15 | 15 | 15 | 15 | 15 | 5/5 on | 0 |
| x3_T15 | 15 | 15 | 15 | 15 | 15 | 15 | 5/5 on | 0 |
| x4_T0 | 15 | 15 | 15 | 15 | 15 | 15 | 5/5 on | 0 |

So the world says it plainly: **once the chain is lit, the T PIN CELL ITSELF
holds 15 with the lever off**, and no repeater is `locked`. It is not a
repeater lock; it is a feedback loop through the pin.

The path, all of it inside the solution `sol_p4_throughline.json` plus the
problem's own fixed cells:

```
T (0,1,1) --back--> repeater (0,1,2) --out--> (0,1,3) solid
   ^                                              |
   |                                       dust (1,1,3)
   |                                              |
   |                                     back--> repeater (1,1,2)
   |                                              |
   +----- dust beside a strongly powered  <--out--+  (1,1,1) solid
          block reads 15                              (x-adjacent to T)
```

`repeater[facing=south]` at (1,1,2) has its output cell at (1,1,1) -- a
`smooth_stone` the solution placed -- and a relay strongly powers the block in
front of it. (1,1,1) and the pin (0,1,1) differ by one in x, and dust beside a
strongly powered block reads 15. So the second stage of the through-line
re-powers the cell that feeds the first stage. The circuit is a latch.

### 7.3 Why neither checker sees it, and why the Bench is not wrong

This is the blind spot Astra named, in one concrete cell:

1. **`placer0_check.py` cannot see it, structurally.**
   `bench_sweep.build(lay, pins)` ends in
   `CC.Bench(blocks, block_entities=be, pinned=list(pins.keys()))`, and
   `capcell.Bench` drops pinned cells from `self._dust`. A pinned cell is
   HELD at the pin level and no solution can raise it. The judge nails T to 0,
   the feedback has nowhere to land, and O reads 0. The rule the solver
   searched under and the rule the judge scored under share the same hole:
   *a solution may drive its own input cell, and the pin hides it.*
2. **The fed Bench of section 2 does not see it either, but for a different
   reason.** With no pins the T cell is a free dust and the latch IS
   representable -- `dc_solve`'s own docstring says "A circuit with feedback
   may have more than one DC solution; this returns the one the iteration
   walks to." Started cold it walks to the 0 fixpoint. Seeded from the
   latched state (every repeater `powered=true`, every dust 15) with the
   lever OFF, it converges in **1 round** to T = 15, O = 15 -- the world's
   answer exactly. Both fixpoints are the Bench's; only one is reachable from
   a cold start.
3. The same seeded test over all 14 (A) rows (`latch_probe4.py`, written
   AFTER the run as the diagnosis) finds a second fixpoint in **exactly one
   row -- `p4_throughline` at T=0** -- and in none of the other 13. The Bench
   could have named the row the world would disagree on before the world ran,
   had anything asked it that question; nothing did, in either checker.

No spec, checker, rule sheet, layout or world was edited to reach this. The
conflict is recorded, not arbitrated: whether `p4_throughline`'s solution is
wrong, or `problems.json` under-specifies the through-line (nothing forbids a
solution cell from powering the pin cell), or `placer0_check` must stop
pinning, is a ruling, not a measurement.

## 8. Readings worth stating

### 8.1 Settling

Part A: `first_stable_gt` over the 14 recorded rows was 0, 4, 6, 8 or 10 --
0 only for the two `v_p4_*` rows, which never moved at all. Part B: over the
128 recorded rows, **4 (9 rows), 10 (9), 16 (38), 18 (8), 20 (1), 22 (2),
24 (18), 26 (28), 28 (2)**, and **13 rows never closed a 10-gt window inside
`max_gt=40`**: their `last_change_gt` is 34 or 36, so the reading was stable
for only the last 4-6 gt. All 13 are ADD or SUB rows (the deep carry path);
all 13 matched the Bench, and all 13 have `final_bits` identical to their
`warm_*` counterpart, so the reading is the same one twice. `plateau` is
false and `truncated` false in every regime of every run. A larger `max_gt`
would turn those 13 numbers into real settle counts; the order fixed
`max_gt=40`, so they are reported as unsettled rather than quietly rounded.

The two `wake_*` regimes settled at 22 and 26 gt in all three part-B runs,
identically -- which is itself a small reproducibility check across three
independent world loads.

### 8.2 The warm-up was needed, and it is per-artifact

Part B: **0 of 128** `warm_*` rows differ from their `v_*` counterpart. The
two wake regimes did their job -- by the time a chunk's warm pass starts,
every lever has changed twice and no gate is stale.

Part A, which has no wake regimes, shows the hazard: **3 of 14** `warm_*`
rows differ from their `v_*` counterpart (`p1_Wn0a0`, `p2_a0`, `p4_T0`), and
the four `v_p1_*` rows read p2's output as 0 where the Bench says 3, with
p2's barrel-backed comparator (4,1,3) reading `powered=false`. That is
exactly WORLD-2 section 7's finding: a comparator whose back is a barrel
loads `powered=false` with output 0 and stays a lie until a neighbour moves.
p2's levers do not move during p1's sweep, so p2 stays stale for all four of
them and is correct from its own warm pass onward. **The lesson for the next
multi-artifact world: a warm-up pass is per-artifact, and an artifact that is
merely held while another sweeps has not been warmed.** The order's
"artifact by artifact" regime plan already contains the fix; the held-artifact
readings are recorded here as evidence, not as a verdict on p2 (p2's own
sweep is 2/2 with 14/14 read points equal).

The p4 latch is NOT this. p4's five repeaters were all woken in
`warm_p4_T15`; `v_p4_T0` then flipped the lever off, delivered the update,
and the circuit held 15 for 40 gt -- and `world4x` reproduced it from a cold
world in a separate run.

### 8.3 What this run does not say

* The reads are PREDICATES, not levels. A wire at power 9 reads 0 on both
  `power=3` and `power=0`, so intermediate levels inside an artifact are
  invisible here by construction. No read point ever landed in that state:
  every level predicate that was compared matched one of its two candidates.
* No timing claim. The run is DC -- freeze, set levers, step, read. The gt
  numbers are settling counts under a frozen tick loop, not a
  propagation-delay measurement of an instant circuit.
* Every artifact was placed VERBATIM. Unlike WORLD-2, not one cell of any
  artifact under test was substituted or moved; the only additions are the
  feeders (all outside or in provably empty cells) and the f readout wire
  (24,2,2) with its support. `alu_check2.lint` L1 and L2 are 0 on all six fed
  layouts.
* Part B was cut into three world loads for the rcon ceiling (section 3).
  Each load re-warmed independently and the three agree with each other on
  the wake regimes; no row was compared across a load boundary.

## 9. Files

* `record.md` (this file)
* `WORLD-4-order.md` -- the order
* `make_layout_world4.py` -> `layout_world4.json` -- the six artifacts +
  feeders, with the collision and lint checks
* `bench_sweep_feed4.py` -> `bench_feed4_rows.json` -- the 14 + 128
  lever-driven Bench rows, incl. per-gate `cmp_out`
* `build_world4.py` -> the void world (scratchpad) and `world4a.spec.json`,
  `world4b1.spec.json`, `world4b2.spec.json`, `world4b3.spec.json`
* `make_diag4.py` -> `world4x.spec.json` -- the p4 follow-up
* `latch_probe4.py` -- the cold-start vs latched-seed DC comparison of
  section 7.3 (no output file; it prints the 14 rows)
* `world4a.run.result.json` / `.tables.md`, `world4b1..b3.run.result.json` /
  `.tables.md`, `world4x.run.result.json` / `.tables.md` -- worldprobe output,
  untouched (`writer: worldprobe`, `report_kind: bench_trace`)
