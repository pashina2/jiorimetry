# Facts

One table. A row is one predicate that a **file in this repository** shows. If no file in this
repository states the number, the row is not in the table: it is listed under
[Asserted without a file](#asserted-without-a-file) instead, unsoftened.

Columns:

* **predicate** - one sentence; numbers only where a file states them.
* **surface** - which of the three oracles produced the reading: the operator's world (a live save),
  the synthetic vanilla world (a headless 1.20.6 server), or the Bench (the rule replica in
  `tools/llmgen/capcell.py`).
* **evidence** - the file, then the literal string in that file that carries the number.
* **how to regenerate** - a command that runs inside this repository, or a statement of why it
  cannot run here.

Rows are ordered by surface, strongest first. `tools/check_tables.py` verifies every evidence path
and every cited literal in this file and in `docs/failures.md`.

| predicate | surface | evidence | how to regenerate |
|---|---|---|---|
| The ALU stage `v7` was placed in a live save and 176 of 176 block placements matched the block list, with 6 of 6 containers holding the declared counts. | operator's world | `docs/world/live-alu-record.md` - `176/176 placements matched` | not regenerable here: the save is not distributed; the untouched region captures of that session are `artifacts/world/capture.rest-20260907T2117Z.json`, `capture.add001-20260907T2125Z.json` and `capture.sub001-20260907T2126Z.json` |
| At rest, 23 of 23 comparators of the placed stage were in the state the Bench put them in. | operator's world | `docs/world/live-alu-record.md` - `23/23 comparators matched the Bench` | not regenerable here: same save |
| Two driven states read out of the region files matched the Bench, 24 of 24 comparators in each: with the control lever on, r = 3 and f = 0; with it off, r = 3 and f = 3. | operator's world | `docs/world/live-alu-record.md` - `24/24 matched` | not regenerable here: same save |
| The 1-bit full adder reproduced the Bench in a synthetic vanilla world over all 8 input vectors, settling in 2 to 10 game ticks. | synthetic world | `docs/world/world1-record.md` - `matches 8/8.` | not regenerable here: a world run needs a 1.20.6 server jar, a Java 21 runtime and an RCON server directory, none of which are distributed (`tools/README.md`); the recorded run is `artifacts/world/world1.run.result.json` |
| Beyond the two outputs of the adder, 112 comparator state comparisons over the 8 recorded vectors were equal, 0 unequal. | synthetic world | `docs/world/world1-record.md` - `112 read comparisons over the 8 recorded vectors, 0 unequal` | not regenerable here: same reason |
| The ALU stage `v7` reproduced the Bench in a synthetic vanilla world in all 32 rows, on r, on f and on the folded output value. | synthetic world | `docs/world/world2-record.md` - `matches 32/32 for r, 32/32 for f` | not regenerable here: same reason; the recorded run is `artifacts/world/world2.run.result.json` |
| Counting every read point of that run, 1024 of 1024 were equal, of which 736 comparator state comparisons are on the stage's own 23 comparators. | synthetic world | `docs/world/world2-record.md` - `1024/1024 equal` | not regenerable here: same reason |
| Two abutting `alu_slice_v9` slices reproduced the Bench in all 128 rows of n=2 at 14976 read points, 0 unequal. | synthetic world | `docs/world/world4-record.md` - `14976` | not regenerable here: same reason; the recorded runs are `artifacts/world/world4b1.run.result.json`, `world4b2` and `world4b3` |
| In that run 13 of the 128 rows never closed a 10 game-tick stability window inside the fixed bound of 40, and are reported as unsettled rather than rounded. | synthetic world | `docs/world/world4-record.md` - `13 rows never closed a 10-gt window` | not regenerable here: same reason |
| Of the five placer solutions driven in a synthetic world, 13 of the 14 rows matched at every read point and one did not; over all rows 105 of 112 read points were equal. | synthetic world | `docs/world/world4-record.md` - `105 of 112 equal` | not regenerable here: same reason |
| Driven by the world tool with no model in the loop, the ALU stage `v7` gave 32 world rows, 0 failures and 1472 of 1472 read points equal, on feeder cells the tool searched for itself. | synthetic world | `artifacts/world/feed1/out_v7/feed_v7.feed.md` - `0/1472` | not regenerable here: same reason; the job is `artifacts/world/feed1/job_v7.json` |
| The same tool gave the two `v9` slices 128 world rows, 0 failures and 19328 of 19328 read points equal, 13 rows unsettled. | synthetic world | `artifacts/world/feed1/out_world4/feed_world4.feed.md` - `0/19328` | not regenerable here: same reason; the job is `artifacts/world/feed1/job_world4.json` |
| A pitch-14 slice the tool had never seen, found by the second reviewer's search with `v9`'s interior fixed, gave 128 world rows, 0 failures and 20608 of 20608 read points equal. | synthetic world | `artifacts/world/feed1/out_p14_final/feed_p14.feed.md` - `0/20608` | not regenerable here: same reason; the job is `artifacts/world/feed1/job_p14.json` |
| The loop-free third solution of the through-line problem gave 2 world rows, 0 failures, 12 of 12 read points equal and a worst settle of 8 game ticks over 68 blocks. | synthetic world | `docs/world/p4-decay-trace.md` - `p4_throughline_v3` | not regenerable here: same reason; the outputs are under `artifacts/world/feed1/out_p4v3/` |
| A per-game-tick trace of the decaying loop shows one level lost per wire hop and 4 game ticks per round, so 56 ticks from level 14 to 0. | synthetic world | `docs/world/p4-decay-trace.md` - `14 rounds = 56 gt` | not regenerable here: same reason; the recorded run is `artifacts/world/feed1/out_p4trace/p4_trace.run.result.json` |
| The 13 world runs driven by the tool cost 3648392 RCON calls and 1483.3 seconds of measured wall time, and 0 model tokens while any server was up. | synthetic world | `docs/world/feed1-record.md` - `3648392` | not regenerable here: same reason |
| The ALU stage `v7` passes the Bench in all 32 rows with the two hard lints at 0. | Bench | `docs/placement/placealu3-result.md` - `PASS 32/32` | `python tools/checks/alu_check2.py artifacts/layouts/alu_stage_v7.json` |
| The 1-bit full adder passes the Bench over all 8 input vectors. | Bench | `docs/placement/place1-bench-output.txt` - `ALL PASS` | `python tools/checks/bench_sweep.py artifacts/layouts/layout_place1.json` |
| The bit slice `alu_slice_v9`, tiled by its own pitch, solves the n-bit ALU function for every input and mode at n=1, n=2 and n=3. | Bench | `docs/placement/slice1-result.md` - `n=3 PASS 512/512` | `python tools/checks/alu_check_slices.py artifacts/layouts/alu_slice_v9.json 3` (about 3 minutes; n=1 and n=2 take seconds) |
| `alu_slice_v9` passes every measured clause of the slice contract, including the time clause: 254 transitions of n=2 driven forward and back, worst settle 26 game ticks, 0 failures. | Bench | `docs/world/p4-decay-trace.md` - `worst settle 26 gt` | `python tools/checks/alu_check_contract.py artifacts/layouts/alu_slice_v9.json` (about 5 minutes) |
| Its predecessor `alu_slice_v8` fails the through-line clause with 1024 entry-level mismatches over 512 rows, although it passes the function table. | Bench | `docs/placement/slice1-result.md` - `C2 through-entry mismatches=1024` | `python tools/checks/alu_check_contract.py artifacts/layouts/alu_slice_v8.json` |
| Read against the slice contract, the stage `v7` scores 20 of 32 at n=1 and 38 of 128 at n=2. | Bench | `docs/placement/slice-contract.md` - `n=1 20/32, n=2 38/128` | `python tools/checks/alu_check_slices.py artifacts/layouts/v7_as_slice.json 1` |
| The documented predecessor layout of the stage scores 30 of 32 on the Bench. | Bench | `docs/alu-place-handover.md` - `PASS 30/32` | `python tools/checks/check_alu_stage.py artifacts/layouts/alu_stage_T6_30of32.json` |
| The 93-block feeder rig drives all 32 rows from lever states only, with no pinned inputs, and reproduces the pinned rows exactly. | Bench | `docs/placement/rig1-result.md` - `PASS 32/32  (r,f identical to pinned alu_check2 rows: 32/32)` | `python tools/world/build_rig1.py` (it writes two JSON files beside itself; the committed copy is `artifacts/layouts/rig1_full_bench.json`) |
| The derived networks pass evaluators written separately from them: the adder and the subtractor on every row, the ALU network on 32. | Bench | `docs/algebra/alu1-eval-output.txt` - `PASS 32/32` | `python tools/checks/dc_eval.py artifacts/layouts/net_derive2.json`, `python tools/checks/dc_eval_sub.py artifacts/layouts/net_reuse1.json`, `python tools/checks/dc_eval_alu.py artifacts/layouts/net_alu1.json` |
| The rule-driven placer solved 5 of the 5 satisfiable placement problems with no human coordinates, and on two of them found a smaller placement than the hand-derived one. | Bench | `docs/placement/placer0-result.md` - `PASS p5_max_merge blocks 9` | `cd tools/placer0 && python placer0_check.py ../../artifacts/placer0/problems.json p5_max_merge ../../artifacts/placer0/sol_p5_max_merge.json` |
| The sixth problem is infeasible, and the infeasibility is proved from the rule replica rather than from the search failing. | Bench | `docs/placement/placer0-result.md` - `p3 is infeasible` | `cd tools/placer0 && python placer0.py ../../artifacts/placer0/problems.json p3_pkill_bridge -v` (reports UNKNOWN at the 600 s bound) |
| After the time clause was added, the placer re-solved the through-line problem without a loop in 16 blocks with a worst settle of 8 game ticks. | Bench | `docs/world/p4-decay-trace.md` - `16 blocks, no loop` | `cd tools/placer0 && python placer0_check.py ../../artifacts/placer0/problems.json p4_throughline ../../artifacts/placer0/sol_p4_throughline.json` |
| The second reviewer's pitch-14 slice, checked here by instruments written independently of the reviewer's judge, passes the function table at n=1 and n=2. | Bench | `docs/placement/xcheck-second-reviewer-slice-search.md` - `== relocated p14 function` | `python tools/checks/alu_check_slices.py artifacts/layouts/reviewer_slice_p14_relocated.json 2` |
| The Bench pins its two corrected behaviours in unit tests: a pin is a floor, and a decaying loop is distinguished from a true latch by a settle bound. | Bench | `tools/llmgen/test_capcell.py` - `FloorAndLatchTests` | `cd tools/llmgen && python -m unittest test_capcell test_strength` |
| The world tool carries 14 tests that need no server. | Bench | `docs/world/feed1-record.md` - `14 tests, no server` | `cd tools/world && python -m unittest test_feed` |
| The two world layouts are regenerated from the stage layouts by their own scripts, and reproduce the committed files byte for byte. | Bench | `tools/world/make_layout_world1.py` - `artifacts/layouts/layout_world1.json` | `python tools/world/make_layout_world1.py && python tools/world/make_layout_world2.py`, then `git status --porcelain` and `cmp tools/world/layout_world2.json artifacts/layouts/layout_world2.json` |

## Asserted without a file

These are stated in this repository's prose, but no file here carries the reading, so they are not
rows. They are kept visible rather than folded into the table.

* **The 1-bit full adder in the operator's world, 8 of 8.** The only mention is a summary sentence;
  no table, no capture and no per-cell reading of that placement is in this repository. The adder's
  Bench and synthetic-world rows above are unaffected.
* **A netlist-style synthesis that reached 27,103 blocks at about 158 dust per comparator.** No
  record of that approach was exported; the number appears only in the README's failure list.
* **The second reviewer's 2,990-case check of a mux.** The result is credited but the check itself is
  not in this repository.
* **The measured-cost table** (wall clock and tokens per stage, and the totals). No instrument output
  backs those numbers here; they were read off session counters at the time.
* **The fragment search at pitch 11 that is said to have found two placer defects.** It appears only
  as a line in the cost table; no record, no candidate layout and no defect list was exported.
* **The human cost of the closing stage** (placement commands, containers filled by hand, client
  restarts, lever flips). Prose only.

Two counts printed in the README's reproduction section no longer match what this repository
produces, because the instruments changed after those lines were printed:

* The unit-test line shows 34 tests; the suite here now runs 37 (3 skipped, OK), the three added
  tests being the pin-as-floor and settle-time cases.
* The rig line shows the pinned stage checker scoring 32 of 32 on `artifacts/layouts/rig1_full_bench.json`.
  Since a pin became a floor rather than a held value, that checker scores 12 of 32 on that layout:
  pinning an input to 0 no longer overrides the physical feeder the same layout already carries. The
  rig's own instrument is the lever-driven sweep in the table above, which still passes 32 of 32.
