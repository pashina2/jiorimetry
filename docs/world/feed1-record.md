# FEED-1 -- feeder search, world and table without an LLM in the loop

Worker seat (Opus), 2026-09-08, DIRECTOR 8 order
`docs/world/feed1-spec.md`. Non-canonical (`notes/**`).
Question: can the real-hardware stage (WORLD-1/2/4) be run by a tool instead of
by a seat -- feeders searched, world built, spec written, run driven, table
copied -- and does it reproduce what the hand-written lanes measured, generalise
to a layout it has never seen, and refuse with a reason when a pin cannot be fed?

Written in two passes, as WORLD-2 and WORLD-4 were: sections 1-4 BEFORE any
world was built or driven, sections 5-12 after. Nothing above section 5 was
edited afterwards.

Deliverable: `tools/world/feed.py` + `tools/world/test_feed.py`.
Nothing else under `tools/` was touched; no layout under test was edited.

## 1. What the tool derives, and from what

`feed.py JOB.json --out DIR [--run]`. A JOB names artifacts; an artifact is
either a layout JSON (`blocks` / `barrels` plus `pins` or a `slice` section) or
a PLACER-0 (problem, solution) pair. From that alone the tool derives:

1. **The feeders.** For every pin CELL it searches the air around the pin for
   one of WORLD-1's two calibrated shapes -- data pin (0/3) = compare gate +
   back barrel 247 + lever-driven side wire (**lever ON = 0, OFF = 3**),
   control pin (0/15) = solid base + `face=floor` lever (**ON = 15**) -- over
   two targets (the pin wire itself, and the SUPPORT BLOCK under it, which a
   comparator front strongly powers, WORLD-2's a1/a2), four gate directions,
   both gate sides, direct lever bases and diagonal-down wire runs
   (WORLD-2's a1 drop). A candidate is accepted only if it
   (1) collides with no layout cell and no accepted feeder,
   (2) leaves every layout cell in exactly the state the CHECKER's pinned
   layout has -- measured, not eyeballed, which is what "touches no wire, no
   gate side, no gate back" means operationally,
   (3) stands on support, and
   (4) leaves the fed layout reproducing the requirement over every row with
   an empty `dc_solve_both` diff.
   A layout cell may be substituted only if it is an INERT floor block
   (smooth stone, nothing above it, no redstone neighbour) -- WORLD-2's a2
   substitution, stated as a rule; substitutions are listed in the report, and
   a feeder that needs none is always preferred (two passes).
   A pin with no candidate is reported with its reason
   (collision / side_or_back / support / electrical / bistable) and NO WORLD IS
   BUILT.

2. **The expected values, from the requirement.** ALU stage and n-slice ALU:
   the function table (mode x A x B x k -> R, F and the carry into each slice),
   computed in `feed.py` from the relation, never read off a Bench. PLACER-0:
   the `expect` expression over the pin names. The Bench is what gets checked.

3. **The world**: `worldgen`'s four-line idiom (the one `synthworld.build_world`
   spells, with the block-entity map filled in, because these artifacts are
   defined by barrel counts -- the deviation WORLD-2 and WORLD-4 declared).
   Artifacts are packed along z with a 12-cell gap.

4. **The spec**, per artifact: `wake_on`, `wake_off` (every lever on, then off,
   so no lever is constant and no feeder gate stays stale), then every row as
   `warm_*` (recorded, not compared), then every row as `v_*` (compared).
   Reads: both candidate levels at every read cell (a third level then shows up
   as a reading, not as "not 3"), `powered` on every comparator and repeater of
   the fed layout, and one `nbt` read of a feeder barrel `Items[3]`. When
   `(max_gt+1) x state reads x regimes` passes `limits.max_rcon = 600,000`, the
   rows are split across runs by index mod n, each run self-contained.
   An artifact is read ONLY in its own spec: WORLD-4 section 8.2 measured that
   an artifact merely held while another sweeps has not been warmed.

## 2. The Bench stage, run BEFORE any world (the tool's own output)

| job | artifact | artifact cells | rows | feeders | substitutions | fed cells | Bench |
|---|---|---|---|---|---|---|---|
| feed_v7 | alu_stage_v7 | 176 | 32 | 8 | 3 | 218 | **32/32** |
| feed_world4 | p1_sub2side | 47 | 4 | 2 | 0 | 54 | **4/4** |
| feed_world4 | p2_copy_into_side | 55 | 2 | 1 | 0 | 62 | **2/2** |
| feed_world4 | p4_throughline (new) | 67 | 2 | 1 | 0 | 69 | **2/2** |
| feed_world4 | p5_max_merge | 42 | 4 | 2 | 0 | 55 | **4/4** |
| feed_world4 | p6_vertical_cap | 36 | 2 | 2 | 0 | 45 | **2/2** |
| feed_world4 | slice_v9_n2 | 584 | 128 | 7 | 0 | 625 | **128/128** |
| feed_p14 | p14_n2 (pitch 14) | 622 | 128 | 7 | 0 | 663 | **128/128** |

Worlds: `feed_v7` 218 blocks / 11 block entities, bbox `97 61 99 .. 112 67 113`;
`feed_world4` 910 blocks / 28 block entities, bbox `97 63 99 .. 125 69 209`
(WORLD-4 built 913 / 28 by hand); `feed_p14` 663 blocks / 19 block entities,
bbox `98 63 99 .. 129 69 117`. Base `100,64,100` in all three.

Two placements are worth naming because a seat chose exactly the same cells by
hand and the searcher did not see that work: the `f` readout wire for
`alu_stage_v7` at (9,1,2) with its support (9,0,2) (WORLD-2 section 1), and for
`slice_v9_n2` at (24,2,2) with (24,1,2) (WORLD-4 section 1). The a2 feeder of
`alu_stage_v7` again needs the under-the-pin target and again substitutes inert
floor blocks -- three of them, where WORLD-2 substituted two.

## 3. The two refusals asked for, both already answered here

**Old p4 (`sol_p4_throughline.latched.json`), acceptance 1.** Predicted before
running: it stops at the Bench, as BISTABLE, before a world is built.
Observed, with no world built and exit code 2:

```
p4_throughline_latched cells   67 rows   2 pins T
REFUSED p4_throughline_latched: no feeder for T
  T at [0, 1, 1]: 8 candidates, bistable x4, collision x4
     bistable     cold and hot DC differ at [[0, 1, 1], [0, 1, 2], [1, 1, 2]] (T=0)
```

That is WORLD-4 section 7's latch, caught at the Bench by the feeder's own
`dc_solve_both`: with a physical control feeder the cold and the hot DC solution
of the T=0 row disagree at the pin cell itself.

**The blocked variant, acceptance 3.** The order asks for a variant of v7 with
the three cells west of the b pin (0,1,4) filled with solid, and predicts a
refusal. `alu_stage_v7_blocked.json` fills (-1,1,4), (-2,1,4), (-3,1,4).
Result, stated before the runs and NOT what the order predicted: the tool does
NOT refuse. It routes under the pin instead --
`b0 [0,1,4] under gate [0,0,5] facing=south` -- and reaches Bench 32/32 again.
The west approach is not the only approach: the support block (0,0,4) under the
b pin is a second target, and its own neighbourhood is empty. The order's
predicate is answered honestly as FAILED-AS-WRITTEN, and section 10 reports a
second variant (`alu_stage_v7_walled.json`) that closes every approach to the
pin, to exercise the reason path itself.

## 4. Predictions for the world runs (written before the first server started)

* `feed_v7`: 32 recorded rows, **0 world FAIL**, mismatch 0 of all compared read
  points -- i.e. WORLD-2's r/f 32/32 and its 23 stage comparators reproduced
  unattended. The feeder cells are NOT WORLD-2's (the searcher picked its own),
  so the reproduced quantity is the reading, not the layout.
* `feed_world4`: the slice **128/128** in the world, and the five PLACER-0
  artifacts at their full row counts, the NEW p4 included at **2/2** -- that
  row is the one WORLD-4 measured wrong on the old solution, and it has never
  been driven in a world on the new one.
* `feed_p14`: **128/128** in the world, a pitch-14 slice the tool has never
  seen, its `Wn` terminal moved.
* Settling: `max_gt=40`, `settle_gt=10`; the deep ADD/SUB carry rows of a
  2-slice ALU took 24-28 gt in WORLD-4 and 13 of 128 never closed a 10-gt
  window, so a handful of unsettled rows here is expected and is reported as
  unsettled, not rounded.
* Warm-up: with two wake regimes in front of every chunk, WORLD-4 saw 0 of 128
  warm rows differ from their v counterpart; the same is expected here.

## 5. The runs

Thirteen completed `worldprobe run` invocations over three void worlds -- plus
five that failed and were re-run, section 8 -- one server at a time, rcon 25598, `java_xmx 3G`, template
`<host-path>/carpet-work`, `max_gt=40`,
`settle_gt=10`, `limits.max_rcon=600,000`. Two of them failed on the host and
one whole job failed on a defect in `feed.py` itself; both are in section 8,
with what was changed.

Run table, from `summary.py` (which reads the `worldprobe` result files):

| job | spec | spec sha256 (head) | utc | regimes | rcon of 600,000 | wall s | rc | completed |
|---|---|---|---|---|---|---|---|---|
| feed_v7 | alu_stage_v7 | `808bab61` | 2026-09-08T11:22:38Z | 66 | 143773 | 184.5 | 0 | True |
| feed_world4 | p1_sub2side | `9f5818bb` | 2026-09-08T11:26:47Z | 10 | 6723 | reused | 0 | True |
| feed_world4 | p2_copy_into_side | `6c5cda14` | 2026-09-08T11:28:04Z | 6 | 3901 | reused | 0 | True |
| feed_world4 | p4_throughline | `df77e6b8` | 2026-09-08T11:29:13Z | 6 | 3834 | reused | 0 | True |
| feed_world4 | p5_max_merge | `515f47b9` | 2026-09-08T11:30:21Z | 10 | 7457 | reused | 0 | True |
| feed_world4 | p6_vertical_cap | `27851b99` | 2026-09-08T11:31:43Z | 6 | 3645 | reused | 0 | True |
| feed_world4 | slice_v9_n2_1 | `e1c54753` | 2026-09-08T11:55:09Z | 88 | 564655 | 263.6 | 0 | True |
| feed_world4 | slice_v9_n2_2 | `b36d0ab2` | 2026-09-08T11:59:32Z | 88 | 564649 | 246.0 | 0 | True |
| feed_world4 | slice_v9_n2_3 | `f7642923` | 2026-09-08T11:33:25Z | 86 | 551896 | reused | 0 | True |
| feed_p14 | p14_n2_1 | `38e0af13` | 2026-09-08T12:04:54Z | 66 | 449634 | 204.7 | 0 | True |
| feed_p14 | p14_n2_2 | `f41324d3` | 2026-09-08T12:08:19Z | 66 | 449408 | 196.6 | 0 | True |
| feed_p14 | p14_n2_3 | `450db18e` | 2026-09-08T12:11:35Z | 66 | 449303 | 191.7 | 0 | True |
| feed_p14 | p14_n2_4 | `832e6204` | 2026-09-08T12:14:47Z | 66 | 449514 | 196.2 | 0 | True |
| **total** | 13 runs | | | | **3648392** | **1483.3** | | |

`reused` is a run kept from the first pass by `--resume` (section 8); its rcon
and readings are the ones its own result file records.

## 6. The table

Copied from the tool's own output, `out_v7/feed_v7.feed.md` and
`out_world4/feed_world4.feed.md`:

| artifact | kind | Bench | world rows | world FAIL | read points | mismatch | settle gt | blocks | rcon |
|---|---|---|---|---|---|---|---|---|---|
| alu_stage_v7 | alu_stage | 32/32 | 32 | 0 | 1472 | 0/1472 | 2..14 (0 unsettled) | 218 | 143773 |

| artifact | kind | Bench | world rows | world FAIL | read points | mismatch | settle gt | blocks | rcon |
|---|---|---|---|---|---|---|---|---|---|
| p1_sub2side | placer0 | 4/4 | 4 | 0 | 32 | 0/32 | 4..8 (0 unsettled) | 54 | 6723 |
| p2_copy_into_side | placer0 | 2/2 | 2 | 0 | 14 | 0/14 | 10..10 (0 unsettled) | 62 | 3901 |
| p4_throughline | placer0 | 2/2 | 2 | 1 | 14 | 7/14 | 0..0 (0 unsettled) | 69 | 3834 |
| p5_max_merge | placer0 | 4/4 | 4 | 0 | 40 | 0/40 | 6..10 (0 unsettled) | 55 | 7457 |
| p6_vertical_cap | placer0 | 2/2 | 2 | 0 | 12 | 0/12 | 8..8 (0 unsettled) | 45 | 3645 |
| slice_v9_n2 | alu_slice_n2 | 128/128 | 128 | 0 | 19328 | 0/19328 | 4..28 (13 unsettled) | 625 | 1681200 |

first counterexample, p4_throughline: `{"regime": "v_T0", "read": "O_0", "cell": [107, 65, 139], "expected": true, "got": false, "other_reads": ["O_15", "c0_1_2", "c1_1_2", "d2_2_1", "d4_3_1"]}`

and `out_p14_final/feed_p14.feed.md`:

| artifact | kind | Bench | world rows | world FAIL | read points | mismatch | settle gt | blocks | rcon |
|---|---|---|---|---|---|---|---|---|---|
| p14_n2 | alu_slice_n2 | 128/128 | 128 | 0 | 20608 | 0/20608 | 4..30 (19 unsettled) | 663 | 1797859 |

Warm-versus-recorded and settling, per run (`summary.py`):

```
warm vs v, per artifact (a warm row that differs from its v row is the stale-gate hazard biting):
  alu_stage_v7           v rows  32  warm != v 0 []  unsettled 0 []
  p1_sub2side            v rows   4  warm != v 0 []  unsettled 0 []
  p2_copy_into_side      v rows   2  warm != v 0 []  unsettled 0 []
  p4_throughline         v rows   2  warm != v 1 ['T0']  unsettled 0 []
  p5_max_merge           v rows   4  warm != v 0 []  unsettled 0 []
  p6_vertical_cap        v rows   2  warm != v 0 []  unsettled 0 []
  slice_v9_n2_1          v rows  43  warm != v 0 []  unsettled 4 ['v_ADD_A1B0k1', 'v_ADD_A2B1k0', 'v_SUB_A1B1k0', 'v_SUB_A3B0k1']
  slice_v9_n2_2          v rows  43  warm != v 0 []  unsettled 4 ['v_ADD_A1B1k0', 'v_ADD_A3B0k1', 'v_SUB_A2B0k1', 'v_SUB_A3B1k0']
  slice_v9_n2_3          v rows  42  warm != v 0 []  unsettled 5 ['v_ADD_A0B1k0', 'v_ADD_A2B0k1', 'v_ADD_A3B1k0', 'v_SUB_A1B0k1']
  p14_n2_1               v rows  32  warm != v 0 []  unsettled 1 ['v_ADD_A0B0k0']
  p14_n2_2               v rows  32  warm != v 0 []  unsettled 8 ['v_ADD_A0B0k1', 'v_ADD_A1B0k1', 'v_ADD_A2B0k1', 'v_ADD_A3B0k1']
  p14_n2_3               v rows  32  warm != v 0 []  unsettled 8 ['v_ADD_A0B1k0', 'v_ADD_A1B1k0', 'v_ADD_A2B1k0', 'v_ADD_A3B1k0']
  p14_n2_4               v rows  32  warm != v 0 []  unsettled 2 ['v_ADD_A0B1k1', 'v_SUB_A0B1k1']
```

Corroboration against the two hand-written lanes, which the tool never read:

* **WORLD-2.** All 32 rows' `r` and `f` are identical to
  `docs/world/bench_feed2_rows.json` (32 identical, 0 differing).
  Of the 42 gate reads, **23 sit on stage comparators** -- WORLD-2's 23 -- plus
  5 feeder comparators and 14 stage repeaters, which WORLD-2 did not read.
* **WORLD-4.** The slice's **13 unsettled rows out of 128** is the number
  WORLD-4 reported (its section 8.1), and the unsettled rows are ADD and SUB
  rows in both. 0 of 128 `warm_*` rows differ from their `v_*` row, as WORLD-4
  found once wake regimes were in front of every chunk.

## 7. The one artifact that differs, again: `p4_throughline`

**The prediction in section 4 is FALSIFIED.** The NEW p4 solution
(`sol_p4_throughline.json`) does not read 2/2 in the world. Its `v_T0` row --
the lever turned OFF after the row before it held T=15 -- reads the output
wire at **15 where the requirement says 0**, and five of the artifact's gates
are on with it. The tool's own first counterexample, verbatim:

```
first counterexample, p4_throughline: {"regime": "v_T0", "read": "O_0",
 "cell": [107, 65, 139], "expected": true, "got": false,
 "other_reads": ["O_15", "c0_1_2", "c1_1_2", "d2_2_1", "d4_3_1"]}
```

It is a LATCH, not a stale gate: `warm_T0`, which ran from the cold world,
read the output as 0 (`final_bits 1000000`), then `warm_T15` turned it on, and
`v_T0` could not turn it off (`final_bits 0111111`, `settle_gt 0` -- nothing
moved at all). This is WORLD-4 section 7's finding, on the solution that was
written to fix it.

**And the Bench does not see it.** `p4_hysteresis.py` asks the same fed layout
three ways:

```
cold+hot  T=0   O=0   converged True/True  bistable cells []
cold+hot  T=15  O=15  converged True/True  bistable cells []
sequential T=15 -> O=15
sequential then T=0 -> O=0   (the world read this cell as 15)
```

so neither the cold solve, nor the hot seed (`dc_solve_both`, which DOES catch
the old solution at the same feeder cell -- section 3), nor a sequential drive
that reproduces the world's own history, reproduces the latch. On the old
solution the same script refuses at the feeder stage with `bistable`.

**This is a spec-vs-observation conflict and it is left open** (AGENTS.md
"Conflict"): the Bench rule replica and the world disagree about the same
cells, and this lane does not have the evidence to say which of
generator bug / spec error / runtime-or-environment / underdefined concept it
is. Two things are worth putting on the record for whoever arbitrates:

1. The feeder cell is NOT the same one WORLD-4 used. `feed.py` put p4's control
   base at (0,1,0); WORLD-4 put it at (-1,1,1). WORLD-4 saw the latch on the
   old solution with ITS cell, this run sees it on the new solution with a
   different cell, so "the feeder causes it" and "the artifact causes it" are
   both still live, and separating them costs one more world run (the same
   solution, a feeder forced to the other cell).
2. `feed.py`'s Bench gate is therefore **not sufficient** to predict a world
   for a circuit that can hold its own input up. It caught one latch (the old
   p4) and missed another (the new p4). The world run is what caught the
   second, at cell level, unattended -- which is the case for keeping the world
   stage rather than trusting the Bench alone.

## 8. What went wrong in the tool, and what was changed

Both defects were found by the runs themselves; both are fixed in `feed.py`,
and every number above was produced by the fixed tool except where the table
says `reused`.

1. **The rcon estimate had no margin.** `p14_n2_1` and `p14_n2_2` (the 3-way
   split) tripped `max_rcon` on their LAST regime -- estimate 596,616 against
   an actual >600,000, i.e. 0.7% low, and a run that trips the ceiling is
   thrown away whole. Measured against the two runs: the estimate was 0.25%
   HIGH on `slice_v9_n2_3` (553,302 vs 551,896) and low on p14, because the
   drive phase costs more than `8 x drives` when many levers move. The
   estimate is now taken at **+5%**, which split p14 into 4 chunks.
2. **A failed run could not be retried cheaply, and one crashed the table.**
   `slice_v9_n2_1` and `_2` died in the first pass with
   `There is insufficient memory for the Java Runtime Environment to continue`
   -- a host-side JVM allocation failure, not a spec or a circuit -- and the
   table builder then raised `KeyError: regimes` on their empty result files,
   losing the whole job's table. `feed.py` now (a) tolerates a result file from
   a run that never measured, and (b) takes `--resume`, which reuses the world
   already built under `--out` and skips every spec whose result file says
   `completed`, so a transient host failure costs only the run that failed.
   The retry also takes the next free run-dir name, because
   `worldprobe.provision` refuses an existing one.

Neither defect touched a reading: every row reported above comes from a run
whose own result file says `completed: true`.

## 9. Cost

| what | wall | rcon | Opus tokens |
|---|---|---|---|
| the runs themselves (12 worldprobe runs, 3 worlds) | see section 5 | see section 5 | **0** |
| writing `feed.py`, `test_feed.py`, the jobs and this record | one seat, one session | -- | the session's |

The runs were driven by two shell scripts (`runall.sh`, `runfix.sh`) that call
`feed.py` and nothing else; no model was in the loop while a server was up.
That is the point of the lane: the next real-hardware stage costs a job file
and wall time.

## 10. The impossibility report, second variant (acceptance 3)

`alu_stage_v7_walled.json` fills every free horizontal neighbour of the b pin
(0,1,4) AND of its support (0,0,4): (-1,1,4), (-2,1,4), (-3,1,4) as the order
asks, plus (0,1,3), (0,1,5), (-1,0,4), (0,0,3), (0,0,5). The tool feeds the
other four pins, refuses at b, prints the reason, exits 2, and creates no world
directory:

```
alu_stage_v7_walled cells  184 rows  32 pins P,Wn,a0,b0,k
  P      [0, 1, 0]      base [0, 1, -1]
  P      [0, 1, 8]      base [0, 1, 7]
  Wn     [4, 1, 10]     base [3, 1, 10]
  a0     [4, 1, 4]      under gate [4, 0, 5] facing=south
  a0     [8, 1, 5]      under gate [8, 0, 6] facing=south subst [[7,0,6],[7,0,7],[8,0,7]]
  a0     [10, 1, 4]     direct gate [10, 1, 5] facing=south
  k      [0, 1, 2]      direct gate [-1, 1, 2] facing=west
REFUSED alu_stage_v7_walled: no feeder for b0
  b0 at [0, 1, 4]: 606 candidates, collision x606
     collision    [0, 1, 3] holds minecraft:smooth_stone
```

`collision` is the whole reason here, and correctly so: a gate can only stand
in a horizontal neighbour of the pin or of its support, and all eight are
taken. The `support` and `side_or_back` reasons are exercised by
`test_feed.py` (`Refusal.test_walled_pin_is_refused_with_a_reason`) and by the
`bistable` refusal of section 3.

## 11. The four acceptance predicates, answered

| # | predicate | answer |
|---|---|---|
| 1 | v7 reproduces WORLD-2 (r/f 32/32, comparators 23) unattended | **PASS** -- 32 world rows, 0 FAIL, 1472/1472 read points equal, all 32 rows' r/f identical to WORLD-2's, 23 of the gate reads on stage comparators |
| 1 | the six WORLD-4 artifacts reproduce, (B) 128/128 | **PASS for five of six** -- slice_v9_n2 128/128 with 19328/19328 read points, p1 4/4, p2 2/2, p5 4/4, p6 2/2 |
| 1 | old p4 stops at the Bench as BISTABLE before a world | **PASS** -- exit 2, no world, reason `bistable` (section 3) |
| 1 | new p4 predicted 2/2 in the world | **FALSIFIED** -- 1 of 2 rows, 7 of 14 read points wrong; the latch, and the Bench does not reproduce it (section 7). Prediction written before the run. |
| 2 | p14 (pitch 14, never seen) as two slices, all 128 rows, matches | **PASS** -- Bench 128/128 and world 128/128, 20608/20608 read points equal, 0 FAIL |
| 3 | a blocked variant makes the tool refuse with a reason and build no world | **PASS with a correction**: the order's own three-cell variant does NOT refuse (the tool routes under the pin, section 3); the walled variant does, with `collision`, exit 2, no world (section 10) |
| 4 | cost table: wall, rcon, Opus tokens 0 for the runs | **PASS** -- sections 5 and 9; 13 runs, 3,648,392 rcon, 1483.3 s of measured wall time, 0 model tokens while any server was up |

## 12. Files

* `record.md` (this file); `FEED-1-spec.md` -- the order
* `tools/world/feed.py`, `tools/world/test_feed.py`
  (14 tests, no server) -- the only two files added under `tools/`
* `job_v7.json`, `job_world4.json`, `job_p14.json`, `job_p4old.json`,
  `job_v7_blocked.json`, `job_v7_walled.json` -- the jobs, one command each
* `alu_stage_v7_blocked.json`, `alu_stage_v7_walled.json` -- the two variants
  of acceptance 3 (the artifacts under test were not edited)
* `out_v7/`, `out_world4/`, `out_p14_final/` -- the specs `feed.py` wrote, the
  `worldprobe` results and tables (`writer: worldprobe`,
  `report_kind: bench_trace`), and `feed.py`'s own report and table, all
  untouched
* `out_p14/` -- the 3-way split whose two runs tripped the rcon ceiling
  (`completed: false`), kept as the evidence for section 8
* `out_p4old/`, `out_v7blocked/`, `out_v7walled/` -- the refusal reports
* `summary.py` -- the run and warm-versus-recorded tables above
* `p4_hysteresis.py` -- the three ways section 7 asks the Bench about p4
* worlds and run dirs: the seat's scratchpad, not the repository
