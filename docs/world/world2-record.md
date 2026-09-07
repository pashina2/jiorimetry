# WORLD-2 -- the ALU stage `alu_stage_v7` in a fresh synthetic world

Worker seat (Opus), 2026-09-07/08, DIRECTOR 8 order
`docs/world/world2-order.md`. Non-canonical (`notes/**`).
Question: does the ALU stage `artifacts/layouts/alu_stage_v7.json`
(Bench 32/32 under `alu_check2.py`), placed in a void headless 1.20.6 world
with no player, produce the same DC `r` and `f` levels as the Bench for all 32
rows (ADD/SUB/AND/OR x a,b,k), and are all 23 stage comparators in the state
the Bench puts them in?

Written in two passes, exactly as WORLD-1: sections 1-4 BEFORE the world ran,
sections 5-8 after. Nothing above section 5 was edited afterwards.

## 1. The feeders

`alu_check2.py` PINS eight wire cells at a fixed power. A world has no pins, so
each pin needs a physical source, built only from comparator / barrel / wire /
solid / lever, that delivers exactly the pinned level into the pin cell.

Two kinds, both WORLD-1's (`docs/world/world1-record.md` section 1):

**Data feeder** (level 3, pins `a` x3, `b`, `k`). A comparator in **compare**
mode whose BACK is a barrel holding **247 stack-64 items** (247/64 = 3.86
stacks of 27 slots -> comparator level **3**) and whose SIDE is a lever-driven
wire. In compare mode the gate emits its back level when back >= side and 0
otherwise, so a side driven to 15 kills it:

* lever ON -> the lever's base solid is strongly powered 15 -> side wire 15 ->
  15 > 3 -> gate output **0** -> input bit **0**
* lever OFF -> side wire 0 -> 3 >= 0 -> gate output **3** -> input bit **1**

**INVERTED CONVENTION, declared: data lever ON = bit 0, lever OFF = bit 1.**

**Control feeder** (level 0/15, pins `P` x2, `Wn`). A solid block beside the pin
wire with a `face=floor` lever on top: lever ON -> base strongly powered 15 ->
the pin wire reads 15; lever OFF -> 0. Lever ON = 15. No gate, no barrel.

Convention, validated by WORLD-1 against a real 1.20.6 server: a comparator or
repeater with `facing=D` has its BACK at `pos+D` and its OUTPUT at `pos-D`.

Positions, in the stage's own relative frame (`layout_world2.json`, written by
`make_layout_world2.py`, which raises on any collision with a stage cell):

| pin | cell | gate | barrel (back) | side wire | lever base | lever |
|---|---|---|---|---|---|---|
| k  | (0,1,2)  | (-1,1,2) facing=west  | (-2,1,2) | (-1,1,1) | (-2,1,1) | (-2,2,1) |
| b  | (0,1,4)  | (-1,1,4) facing=west  | (-2,1,4) | (-1,1,5) | (-2,1,5) | (-2,2,5) |
| a1 | (4,1,4)  | (4,0,5) facing=south  | (4,0,6)  | (5,0,5) -> (6,-1,5) -> (7,-2,5) | (8,-2,5) | (8,-1,5) |
| a2 | (8,1,5)  | (8,0,6) facing=south  | (8,0,7)  | (7,0,6) | (7,1,6) | (7,2,6) |
| a3 | (10,1,4) | (11,1,4) facing=east  | (12,1,4) | (11,1,5) | (11,1,6) | (11,2,6) |
| P1 | (0,1,0)  | -- | -- | -- | (0,1,-1) | (0,2,-1) |
| P2 | (0,1,8)  | -- | -- | -- | (-1,1,8) | (-1,2,8) |
| Wn | (4,1,10) | -- | -- | -- | (3,1,10) | (3,2,10) |

`a` is one input driven at three pin cells, so it gets three feeders and three
levers, always set together; `P` gets two levers, always set together.

### Why a1 and a2 are not shaped like the others

For k, b and a3 the gate's OUTPUT CELL *is* the pin wire, as in WORLD-1. For a1
and a2 that is impossible: every horizontal neighbour of the pin is a stage
block.

* **a1 (4,1,4)** is boxed in by (3,1,4), (4,1,3), (5,1,4), (4,1,5) and a barrel
  above at (4,2,4).
* **a2 (8,1,5)** has (7,1,5), (9,1,5), (8,1,4) taken. Its one free neighbour is
  (8,1,6) -- but a gate there would make the pin dust connect along z, and a
  dust that connects along z weakly powers (8,1,4), which is the BACK of stage
  comparator (7,1,4). That is a change to the stage, not a feed into it.

So for those two the gate's output cell is the SUPPORT BLOCK UNDER the pin
dust -- (4,0,4) and (8,0,5). A comparator whose front is a solid block strongly
powers that block at its own output level, and dust adjacent to a strongly
powered block reads that level, so the dust above reads exactly 3 or 0. This is
not a new trick: the stage itself already runs on it, at (8,1,4), (5,1,2),
(3,1,5), (4,2,7), (5,2,9), (6,2,8), (2,2,6), (8,1,4) (the `L3` lines
`alu_check2.py` prints).

Two consequences, both stated as deviations:

1. **Two stage floor blocks are substituted.** (8,0,7) `smooth_stone` ->
   `barrel` (247) is the a2 gate's back; (7,0,6) `smooth_stone` -> `redstone_wire`
   is the a2 gate's side. Both are y=0 floor blocks that support nothing (the
   cells above them, (8,1,7) and (7,1,6), are air in `alu_stage_v7`) and touch
   no dust and no relay front. Everything else in the stage is verbatim.
2. **The a1 lever escapes downwards.** The gate's -x side (3,0,5) must stay
   AIR: (3,1,5) directly above it is strongly powered by stage comparator
   (3,1,4), so a wire there reads the stage and not the lever -- measured, in
   the first Bench build of this layout, as side power **9 with the lever off**,
   which cost 8 of the 32 rows. The +x side (5,0,5) is clean ((5,1,5) is no
   relay's front), but every y=1 cell above the free y=0 cells here is a stage
   block, so no lever fits at y=2. The side wire therefore drops two
   diagonal-down hops into the empty space below the artifact,
   (5,0,5) -> (6,-1,5) -> (7,-2,5), to a lever base at (8,-2,5) with the lever
   at (8,-1,5). Level along it: base 15 -> 15 -> 14 -> 13 at the gate side,
   which is >= 4 and so kills a level-3 back.

### The f readout

`f` is comparator F at (8,1,2), whose output cell (9,1,2) is air in the stage.
A wire is added there (plus its support (9,0,2)) so `f` can be read as a wire
power. (9,1,2) is also the output cell of the dummy comparator (9,1,3), which is
a compare gate whose back (9,1,4) is a comparator not pointing into it -- back
input 0, output 0 in all 32 rows -- so the wire reads F alone. The Bench
confirms it: **`f_wire == f_cmp` in all 32 rows**, and adding the wire leaves
the sweep at 32/32.

`r` at (6,2,9) is already a wire in the stage and needs nothing.

Totals: 176 stage blocks (2 substituted) + 43 new blocks + 2 readout blocks =
**221 blocks**, 11 barrels, 8 levers, 28 comparators (23 stage + 5 feeder).

## 2. Bench prediction (run BEFORE the world)

`bench_sweep_feed2.py layout_world2.json` -- same `capcell.Bench`, **no pins at
all**: the lever states are set in the block states and `dc_solve()` resolves
the feeders and the stage together.

Result: **PASS 32/32**, every row converged (max 10 rounds), every `r` and `f`
exactly 0 or 3, and -- checked row by row against
`artifacts/rows/alu_stage_v7.json.rows.json` --
**the feeder-driven r and f are identical to the pinned r and f in all 32
rows**. The feeders reproduce the pinned result.

## 3. What the world is asked, and what a match means

`world2.spec.json`, driven by `tools/world/worldprobe.py run`:
`tick freeze`, set the eight levers, step 1 gt at a time to `max_gt=40`, with
`settle_gt=10`, `limits.max_rcon=200000`, rcon port 25598, `java_xmx 3G`.

33 read points. Four carry bits and fold into `final_value`:

| bit | read | cell (relative) | match |
|---|---|---|---|
| 0 | r3 | (6,2,9) | `minecraft:redstone_wire[power=3]` |
| 1 | r0 | (6,2,9) | `minecraft:redstone_wire[power=0]` |
| 2 | f3 | (9,1,2) | `minecraft:redstone_wire[power=3]` |
| 3 | f0 | (9,1,2) | `minecraft:redstone_wire[power=0]` |

Reading both `power=3` and `power=0` at each output means a third level shows up
as a reading (both bits 0) instead of being folded silently into "not 3".

28 more reads take `powered` on every comparator -- 23 stage gates (`c*`) and
the 5 feeder gates (`g*`) -- with the Bench's `cmp_out > 0` as the expectation.
One `nbt` read takes `Items[3]` of the a3 feeder barrel at (12,1,4), where a
wrongly written 247 = 3*64 + 55 would show. These carry no bit.

Base is `100,64,100`, so relative (x,y,z) is world (100+x, 64+y, 100+z);
bbox 97 60 98 .. 113 67 112.

Predicted `final_value` per row (bit0 r3 | bit1 r0 | bit2 f3 | bit3 f0):

| op | a b k | P Wn | levers a,b,k / P,Wn | Bench r | Bench f | expected final_value |
|---|---|---|---|---|---|---|
| ADD | 0 0 0 | 0 15 | 111 / 01 | 0 | 0 | 10 |
| ADD | 0 0 1 | 0 15 | 110 / 01 | 3 | 0 | 9 |
| ADD | 0 1 0 | 0 15 | 101 / 01 | 3 | 0 | 9 |
| ADD | 0 1 1 | 0 15 | 100 / 01 | 0 | 3 | 6 |
| ADD | 1 0 0 | 0 15 | 011 / 01 | 3 | 0 | 9 |
| ADD | 1 0 1 | 0 15 | 010 / 01 | 0 | 3 | 6 |
| ADD | 1 1 0 | 0 15 | 001 / 01 | 0 | 3 | 6 |
| ADD | 1 1 1 | 0 15 | 000 / 01 | 3 | 3 | 5 |
| SUB | 0 0 0 | 0 0 | 111 / 00 | 0 | 0 | 10 |
| SUB | 0 0 1 | 0 0 | 110 / 00 | 3 | 3 | 5 |
| SUB | 0 1 0 | 0 0 | 101 / 00 | 3 | 3 | 5 |
| SUB | 0 1 1 | 0 0 | 100 / 00 | 0 | 3 | 6 |
| SUB | 1 0 0 | 0 0 | 011 / 00 | 3 | 0 | 9 |
| SUB | 1 0 1 | 0 0 | 010 / 00 | 0 | 0 | 10 |
| SUB | 1 1 0 | 0 0 | 001 / 00 | 0 | 0 | 10 |
| SUB | 1 1 1 | 0 0 | 000 / 00 | 3 | 3 | 5 |
| AND | 0 0 0 | 15 15 | 111 / 11 | 0 | 0 | 10 |
| AND | 0 0 1 | 15 15 | 110 / 11 | 0 | 0 | 10 |
| AND | 0 1 0 | 15 15 | 101 / 11 | 0 | 0 | 10 |
| AND | 0 1 1 | 15 15 | 100 / 11 | 0 | 0 | 10 |
| AND | 1 0 0 | 15 15 | 011 / 11 | 0 | 0 | 10 |
| AND | 1 0 1 | 15 15 | 010 / 11 | 0 | 0 | 10 |
| AND | 1 1 0 | 15 15 | 001 / 11 | 3 | 0 | 9 |
| AND | 1 1 1 | 15 15 | 000 / 11 | 3 | 0 | 9 |
| OR | 0 0 0 | 15 0 | 111 / 10 | 0 | 0 | 10 |
| OR | 0 0 1 | 15 0 | 110 / 10 | 0 | 0 | 10 |
| OR | 0 1 0 | 15 0 | 101 / 10 | 3 | 0 | 9 |
| OR | 0 1 1 | 15 0 | 100 / 10 | 3 | 0 | 9 |
| OR | 1 0 0 | 15 0 | 011 / 10 | 3 | 0 | 9 |
| OR | 1 0 1 | 15 0 | 010 / 10 | 3 | 0 | 9 |
| OR | 1 1 0 | 15 0 | 001 / 10 | 3 | 0 | 9 |
| OR | 1 1 1 | 15 0 | 000 / 10 | 3 | 0 | 9 |

(levers: `a,b,k` then `P,Wn`; 1 = ON. Data ON = bit 0, control ON = 15.)

Comparator `powered` expectations are in the spec too, one per gate per row,
taken from the Bench's `cmp_out > 0`: between 5 and 22 of the 28 gates are
powered depending on the row, 28 x 32 = **896 comparator comparisons**, of which
23 x 32 = **736 are on the stage's own gates**.

## 4. The warm-up sweep, and why the run is 64 regimes and not 32

A world written straight into region files carries whatever states the writer
put in the palette, and no redstone update ever runs over it. Every comparator
loads `powered=false` with output signal 0 and every wire loads `power=0` -- a
lie everywhere a back is a redstone block (0,1,6) or a barrel. A gate
recomputes only when a neighbour's block state changes, so a gate whose stale
state happens to equal the answer for the row under test is never woken, and one
stale gate upstream poisons every reading downstream of it.

So the 32 rows are driven **twice**: once as `warm_*` regimes whose readings are
recorded but not compared against the Bench, then once as `v_*`. Every lever
changes at least once during the warm-up pass (all four ops and all eight
(a,b,k) combinations are visited), so every gate has recomputed from live
inputs before the recorded pass starts. No Bench answer is written into the
world -- the warm-up is lever flips only, and its readings stay in the result
file so the discarded pass is auditable.

Prediction for the warm-up pass itself: the early warm-up rows may read
anything; the late ones should already agree with section 3. WORLD-1 found the
hazard did not in fact bite; this is a bigger and deeper artifact (three levels,
a 15-wide dust ring, 28 gates), so no prediction is made either way.

Deviation from `synthworld.build_world`: it spells
`worldgen.build_region_files(placements, {}, version)`, so a world it writes can
hold no block entities, and this artifact is defined by eleven barrels whose
item counts ARE its constants. `build_world2.py` spells those four worldgen
lines itself with the block-entity map filled. `worldprobe.py` is used
unmodified. Nothing under `tools/` is changed.

## 5. The world run

`tools/world/worldprobe.py run --spec artifacts/world/world2.spec.json --run-dir <scratchpad>/w2run`,
2026-09-07T20:44:15Z, template `<host-path> development runtime/carpet-work`,
rcon 25598, **103,169 roundtrips of a 200,000 limit**, exit 0, `completed: true`,
3 minutes wall. Result: `world2.run.result.json` (untouched, `writer: worldprobe`,
`report_kind: bench_trace`, spec sha256 `aedc992a...`), tables
`world2.run.tables.md` (untouched). The world is the void save built by
`build_world2.py` into the scratchpad: 221 blocks, 11 block entities, one region
`r.0.0.mca`, DataVersion 3839 (template also 3839), no player, no terrain.
`tick query` answered "The game is frozen" and the scarpet probe answered
`= 5 (12ms)`.

The barrel was read back through the probe, not assumed, before and after the
sweep, identically:

```
data get block 112 65 104 Items[3]
-> 112, 65, 104 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}
```

3 x 64 + 55 = 247, in the 1.20.5+ item spelling (`count`, int), and the game
parsed it -- which is also what makes the five data feeders emit 3 at all.

## 6. Table

Bench = section 2 (`bench_feed2_rows.json`). World = `final_reads` of the `v_*`
regimes; `3` means `redstone_wire[power=3]` matched at that cell, `0` means
`power=0` matched; neither matching would have read as `other`. The `28 cmp`
column is the per-row count of comparator `powered` reads that equalled the
Bench's `cmp_out > 0` (23 stage gates + 5 feeder gates).

| op | a b k | Bench r | Bench f | world r | world f | final_value exp/got | settle_gt | 28 cmp | match |
|---|---|---|---|---|---|---|---|---|---|
| ADD | 0 0 0 | 0 | 0 | 0 | 0 | 10/10 | 14 | 28/28 | match |
| ADD | 0 0 1 | 3 | 0 | 3 | 0 | 9/9 | 14 | 28/28 | match |
| ADD | 0 1 0 | 3 | 0 | 3 | 0 | 9/9 | 4 | 28/28 | match |
| ADD | 0 1 1 | 0 | 3 | 0 | 3 | 6/6 | 14 | 28/28 | match |
| ADD | 1 0 0 | 3 | 0 | 3 | 0 | 9/9 | 12 | 28/28 | match |
| ADD | 1 0 1 | 0 | 3 | 0 | 3 | 6/6 | 14 | 28/28 | match |
| ADD | 1 1 0 | 0 | 3 | 0 | 3 | 6/6 | 4 | 28/28 | match |
| ADD | 1 1 1 | 3 | 3 | 3 | 3 | 5/5 | 14 | 28/28 | match |
| SUB | 0 0 0 | 0 | 0 | 0 | 0 | 10/10 | 12 | 28/28 | match |
| SUB | 0 0 1 | 3 | 3 | 3 | 3 | 5/5 | 14 | 28/28 | match |
| SUB | 0 1 0 | 3 | 3 | 3 | 3 | 5/5 | 4 | 28/28 | match |
| SUB | 0 1 1 | 0 | 3 | 0 | 3 | 6/6 | 14 | 28/28 | match |
| SUB | 1 0 0 | 3 | 0 | 3 | 0 | 9/9 | 12 | 28/28 | match |
| SUB | 1 0 1 | 0 | 0 | 0 | 0 | 10/10 | 14 | 28/28 | match |
| SUB | 1 1 0 | 0 | 0 | 0 | 0 | 10/10 | 4 | 28/28 | match |
| SUB | 1 1 1 | 3 | 3 | 3 | 3 | 5/5 | 14 | 28/28 | match |
| AND | 0 0 0 | 0 | 0 | 0 | 0 | 10/10 | 14 | 28/28 | match |
| AND | 0 0 1 | 0 | 0 | 0 | 0 | 10/10 | 2 | 28/28 | match |
| AND | 0 1 0 | 0 | 0 | 0 | 0 | 10/10 | 2 | 28/28 | match |
| AND | 0 1 1 | 0 | 0 | 0 | 0 | 10/10 | 2 | 28/28 | match |
| AND | 1 0 0 | 0 | 0 | 0 | 0 | 10/10 | 14 | 28/28 | match |
| AND | 1 0 1 | 0 | 0 | 0 | 0 | 10/10 | 2 | 28/28 | match |
| AND | 1 1 0 | 3 | 0 | 3 | 0 | 9/9 | 14 | 28/28 | match |
| AND | 1 1 1 | 3 | 0 | 3 | 0 | 9/9 | 2 | 28/28 | match |
| OR | 0 0 0 | 0 | 0 | 0 | 0 | 10/10 | 10 | 28/28 | match |
| OR | 0 0 1 | 0 | 0 | 0 | 0 | 10/10 | 2 | 28/28 | match |
| OR | 0 1 0 | 3 | 0 | 3 | 0 | 9/9 | 14 | 28/28 | match |
| OR | 0 1 1 | 3 | 0 | 3 | 0 | 9/9 | 2 | 28/28 | match |
| OR | 1 0 0 | 3 | 0 | 3 | 0 | 9/9 | 10 | 28/28 | match |
| OR | 1 0 1 | 3 | 0 | 3 | 0 | 9/9 | 2 | 28/28 | match |
| OR | 1 1 0 | 3 | 0 | 3 | 0 | 9/9 | 8 | 28/28 | match |
| OR | 1 1 1 | 3 | 0 | 3 | 0 | 9/9 | 2 | 28/28 | match |

**matches 32/32 for r, 32/32 for f, 32/32 on `final_value`.**

Beyond the two outputs, every gate: **896 comparator `powered` comparisons over
the 32 recorded rows, 0 unequal**, of which **736 are on the stage's own 23
comparators, 0 unequal**. Counting all read points, `final_reads` was
**1024/1024 equal**. So the agreement is not only at `r` and `f`; every gate in
the stage is in the state the Bench put it in, in every row.

## 7. The warm-up was needed here

WORLD-1 found its warm-up pass redundant -- all 8 discarded rows already agreed
with their recorded counterparts. **This one was not.** 30 of the 32 `warm_*`
rows have `final_bits` identical to their `v_*` counterpart; the two that differ
are exactly the first two regimes driven against the freshly loaded world:

| regime | warm final_value | v final_value | reads that differ |
|---|---|---|---|
| `warm_ADD_a0b0k0` | 10 | 10 | c1_1_4, c2_1_3, c3_1_4, c4_1_3, c6_1_3 (`powered`) |
| `warm_ADD_a0b0k1` | 10 | **9** | r3, r0, and c1_1_4, c2_1_3, c3_1_4, c4_1_3, c4_2_5, c5_2_6, c6_1_3, c6_2_7 |

That is precisely the hazard section 4 was built against: on a world written
straight into region files every comparator loads `powered=false` with output 0,
and gates whose backs are barrels ((1,1,5)=988, (7,1,2)=247, (2,1,7)=247,
(2,2,4)=247, (4,2,4)=988, (6,1,9)=247) or the redstone block at (0,1,6) are
lying until something wakes them. The second row shows it reaching `r` itself
(`final_value` 10 where the Bench says 9), i.e. a run WITHOUT the warm-up pass
would have recorded a wrong `r` in at least one row and called it a mismatch of
the artifact. By the third regime the world is live everywhere and never
disagrees again.

## 8. Readings worth stating

* Settle. `settle_gt` (the first gt after which the 32 read predicates hold for
  10 gt) over the 32 recorded rows ranged **2..14** -- 2 (9 rows), 4 (4), 8 (1),
  10 (2), 12 (3), 14 (13) -- with `last_change_gt` equal to `first_stable_gt` in
  all 64 regimes (`plateau: false` everywhere) and nothing `truncated` at
  `max_gt=40`. The longest, 14 gt, is the full chain: `v_ADD_a0b0k0` moved at
  gt 0, 2, 4, 6, 8, 10, 12, 14. The rows at 2 are transitions where only the
  `k` lever moved and the previous row already held the same outputs.
* The reads are PREDICATES, not levels. A wire at power 9 reads 0 on both
  `power=3` and `power=0`, so intermediate levels inside the stage are invisible
  here by construction. That is deliberate -- the question was the DC output
  levels -- but these series are not a timing trace and must not be read as one.
* No timing claim is made. The run is DC: freeze, set levers, step, read. The
  gt numbers above are settling counts under a frozen tick loop, not a
  propagation-delay measurement of the instant circuit.
* The stage was placed verbatim except the two inert y=0 floor blocks named in
  section 1 ((8,0,7) -> barrel 247, (7,0,6) -> wire) and the added f readout
  wire (9,1,2) with its support. Every redstone-carrying cell of
  `alu_stage_v7.json` is unchanged, and `alu_check2.py`'s L1 (no-support) lint
  is clean on the combined layout.

## 9. Files

* `record.md` (this file)
* `make_layout_world2.py` -> `layout_world2.json` -- stage + feeders + levers
* `bench_sweep_feed2.py` -> `bench_feed2_rows.json` -- the 32 lever-driven Bench
  rows, incl. per-gate `cmp_out`
* `build_world2.py` -> the void world (scratchpad) and `world2.spec.json`
  (8 drives, 33 reads, 64 regimes)
* `world2.run.result.json`, `world2.run.tables.md` -- worldprobe output, untouched
