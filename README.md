# Jiorimetry

> 日本語: [README.ja.md](README.ja.md)

An experimental toolchain that **derives** Minecraft 1.20.6 redstone circuits from rule
sheets written out of the game source, rather than transcribing circuits a human already
knows. The rules it starts from are the DC signal-strength rules: comparators, containers,
dust attenuation, strongly-powered solids. Every result is read on three surfaces — a Bench
(a replica of the rules), a synthetic vanilla world (a headless server), and the live world
the operator plays in. *Jiorimetry — 自織 (jiori, "self-weaving") + -metry.*

Sections: [1 Thesis](#1-thesis) · [2 The toolchain](#2-the-toolchain) · [3 Facts](#3-facts) ·
[4 Failures](#4-failures) · [5 Reference](#5-reference) · [6 Unproven](#6-unproven) ·
[7 Versioning](#7-versioning) · [8 Credits](#8-credits)

---

## 1. Thesis

What this repository holds is not a circuit. It is a derivation.

A copied circuit cannot say why it works. Change one part and it has to be rebuilt, and
nothing carries over to the next circuit. Here the order is reversed. The rules the game
computes with are read out of the source and written as a table a person can read. The table
is applied to a question, and one chain leads from the question to a placed artifact. The
table contains no circuit shapes. A table with a shape in it has written the answer first.
What happens downstream of it is not a derivation; it is a check of something already known.

There are three reading surfaces. The rule replica is cheap and runs on every candidate. Its
correctness cannot exceed the correctness of the person who read the source. The synthetic
world runs the game's own code, but it is not a save anyone plays in. The live world is the
only place where the artifact has to stand among chunks and neighbours nobody arranged. The
first two surfaces exist to make failure cheap. A reading on a cheap surface is a prediction
about the last surface. A prediction does not replace the last surface.

The judge should differ from the world in speed and in nothing else. If anything else
differs, the judge is answering for its own convenience, not for the world. Every shortcut
that makes judging cheap is a convenience of the instrument, not a property of the game. A
fixed point without time. An input held instead of driven. One starting state. The failures
this repository reports are failures of conveniences, not of rules. None of them was visible
until the world was asked. A convenience stays only while it is shown to hide nothing. The
moment it hides something, it is retired.

The requirement keeps one shape: a sequence of inputs and a table of the outputs expected
from it. Building a new checker for every new property makes the instrument grow faster than
the circuits. An instrument that grows that way does not pay for itself.

Leaving derivation to a language model pays a cost and a risk on every run. What can be
inverted is inverted. Forward rules read backwards give the candidate moves a search needs.
A decomposition that worked is stored with the conditions under which it may be reused, and
knowledge moves from the model into the machine. What stays with the model is the
decomposition. Even that is being shrunk towards a finite search over a derived vocabulary.

The order of work follows from the same reasoning. Question the requirement. Delete what it
does not need. Simplify what is left. Shorten the loop. Then automate. In that order, so
that nothing is automated which should have been deleted.

The measure is the whole chain. A stage is built when it shortens the cycle from a question
to a verified reading. A correction is paid for when it widens the range of circuits that can
be derived next. Any other improvement has only moved a cost somewhere else in the chain.

---

## 2. The toolchain

Six steps, from the rules to a placed artifact. Each names the files that carry it.

1. **A rule sheet.** A human-readable table of DC behaviour, written by reading the
   decompiled 1.20.6 source and citing line numbers — comparators, composters, torches,
   wire, and the solidity predicates. It contains no circuit shapes.
   [`docs/rules/`](docs/rules).
2. **Algebra.** An agent — one model instance working from a written order — is given the
   rule sheet and a question, and returns a *network* of comparator, torch and constant
   nodes with an explicit level encoding; not a layout. Evaluators written separately from
   the network check it: `tools/checks/dc_eval.py`, `dc_eval_sub.py`, `dc_eval_alu.py`.
   Records in [`docs/algebra/`](docs/algebra).
3. **Placement.** Coordinates for that network, under a geometry rule sheet (adjacency,
   dust shapes, diagonal reads, vertical hand-off). Derived by an agent in
   [`docs/placement/`](docs/placement), and, for small problems, by the rule-driven placer
   `tools/placer0/placer0.py` with its judge `tools/placer0/placer0_check.py`.
4. **Bench.** `tools/llmgen/capcell.py` re-implements the DC rules over the machine and
   part tables `tools/llmgen/machine.py` and `library.py`, solves a block list to a fixed
   point from a cold and a hot seed, and steps it in game ticks for settle questions. It is
   calibrated against a pre-existing reference circuit that no design agent is shown. The
   layout checkers `tools/checks/alu_check2.py`, `alu_check_slices.py` and
   `alu_check_contract.py` all ask this one oracle.
5. **The synthetic world.** `tools/world/feed.py` takes a layout and its requirement,
   searches for physical feeder cells to replace pinned inputs, builds a void 1.20.6 world
   (`tools/world/synthworld.py`, `worldgen.py`), drives every row over RCON with
   freeze/step (`tools/world/worldprobe.py`) and writes the result table from the run's own
   output. Records in [`docs/world/`](docs/world).
6. **The live world.** The same block list is emitted as a placement program
   (`tools/llmgen/cell_to_program.py`), placed in the save, and read back out of the region
   files without a server by `tools/world/regioncap.py`.

`tools/check_tables.py` sits beside the chain: it verifies that every row of the two tables
below cites a file in this repository and that the cited string is in it.
[`tools/README.md`](tools/README.md) lists every file and what it needs.

---

## 3. Facts

One table, in [`docs/facts.md`](docs/facts.md) ([日本語](docs/facts.ja.md)). A row exists only
if a file in this repository shows the number; each row carries the file, the literal string
in it, and either a command that reproduces it here or the reason it cannot run here.
Readings that are stated only in prose are listed under the table instead of being folded
into it, and `tools/check_tables.py` re-checks every citation.

Below are that table's rows for the two world surfaces, copied unchanged. The Bench rows and
the unbacked assertions are in the file.

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

---

## 4. Failures

One table, in [`docs/failures.md`](docs/failures.md) ([日本語](docs/failures.ja.md)), the same
shape: a row exists only if a file here shows it. Each row names what the instruments were
built to believe, the file that showed otherwise, what changed in this repository because of
it, and how to reproduce the failure. Failures whose evidence was never exported are named
under the table and nothing more is claimed about them.

The first four rows, copied unchanged; the rest are in the file.

| what was believed | evidence | what changed | how to reproduce |
|---|---|---|---|
| A pinned input cell holds its level, so no solution can drive its own input and a pin is a safe way to ask the rule replica a question. | `docs/world/world4-record.md` - `the through-line is latched` | A pin became a floor (the maximum of the pinned source and the neighbours) in `tools/llmgen/capcell.py`; the corrected judge rejects the solution that passed before, which is kept as `artifacts/placer0/sol_p4_throughline.latched.json`. | `cd tools/placer0 && python placer0_check.py ../../artifacts/placer0/problems.json p4_throughline ../../artifacts/placer0/sol_p4_throughline.latched.json` (prints BISTABLE and FAIL) |
| One cold-start iteration of the rule replica finds the circuit's DC answer. | `docs/world/world4-record.md` - `in none of the other 13` | Every DC solve now runs from a cold and a hot seed and reports the cells on which the two answers differ; the behaviour is pinned by unit tests in `tools/llmgen/test_capcell.py`. | `cd tools/llmgen && python -m unittest test_capcell` |
| The judge, the placer and the world would agree on the re-solved through-line: the prediction, written before the run, was 2 of 2. | `docs/world/feed1-record.md` - `FALSIFIED` | The conflict was traced to time, not to DC: a settle bound entered the Bench (`set_floors`, `settle_after`), the placer's judge drives every ordered pair of pin vectors, and the contract checker gained a time clause. The decaying solution is kept as `artifacts/placer0/sol_p4_throughline.decay.json`. | `cd tools/placer0 && python placer0_check.py ../../artifacts/placer0/problems.json p4_throughline ../../artifacts/placer0/sol_p4_throughline.decay.json` (prints TIME and FAIL) |
| A 40 game-tick observation window is long enough to call a regime settled, so a value still standing at the end of it is a latch. | `docs/world/p4-decay-trace.md` - `14 rounds = 56 gt` | A regime whose last change lands on the bound is recorded as truncated, never as a settled final value; the time clause bounds the settle instead of the observer. | recorded only: the trace needs a server. The Bench side of the same verdict is the row above. |

### Records

The per-round accounts, kept as they were written.

- [`docs/records/`](docs/records) — index of every record, and the README's earlier per-round
  text (results by round, provenance, failures in prose, measured costs, repository layout).
- [`docs/world/world1-record.md`](docs/world/world1-record.md) — the adder in a synthetic world.
- [`docs/world/world2-record.md`](docs/world/world2-record.md) — the ALU stage in a synthetic world.
- [`docs/world/world4-record.md`](docs/world/world4-record.md) — two slices and the placer's solutions, and the latch.
- [`docs/world/feed1-record.md`](docs/world/feed1-record.md) — the world stage as one command.
- [`docs/world/p4-decay-trace.md`](docs/world/p4-decay-trace.md) — the per-tick trace that separated a decay from a latch.
- [`docs/world/live-alu-record.md`](docs/world/live-alu-record.md) — the placement and readings in the live world.
- [`docs/placement/slice1-result.md`](docs/placement/slice1-result.md) and [`slice-contract.md`](docs/placement/slice-contract.md) — the slice contract and the layouts measured against it.
- [`docs/placement/placer0-result.md`](docs/placement/placer0-result.md) — the rule-driven placer pilot.
- [`docs/placement/xcheck-second-reviewer-slice-search.md`](docs/placement/xcheck-second-reviewer-slice-search.md) — cross-check of the second reviewer's search.
- [`docs/report-alu-stage.md`](docs/report-alu-stage.md) — the narrative record of the ALU stage.

---

## 5. Reference

Python 3.11+, standard library only, run from the repository root. Nothing to install for
the Bench path.

```
git clone https://github.com/pashina2/jiorimetry.git && cd jiorimetry
```

Without git: [download the repository as a ZIP](https://github.com/pashina2/jiorimetry/archive/refs/heads/main.zip),
unpack it, and run the commands from the unpacked directory.

| tool | command | in / out | what a pass prints |
|---|---|---|---|
| Bench, full-adder sweep | `python tools/checks/bench_sweep.py artifacts/layouts/layout_place1.json` | a layout JSON in; nothing written | one line per input vector, then `ALL PASS` |
| Bench, ALU stage | `python tools/checks/alu_check2.py artifacts/layouts/alu_stage_v7.json` | a layout JSON in; writes `LAYOUT.rows.json` beside it | `LINT L3 …` informational lines, then `PASS 32/32`; the hard lints `L1` (vanilla support) and `L2` (diagonal dust reads) print nothing when they are clean |
| Bench, slice function table | `python tools/checks/alu_check_slices.py artifacts/layouts/alu_slice_v9.json 3` | a layout JSON and a tiling count; nothing written | `n=3 PASS 512/512` (n=1 and n=2 take seconds; n=3 takes minutes) |
| Bench, slice contract | `python tools/checks/alu_check_contract.py artifacts/layouts/alu_slice_v9.json` | a layout JSON; nothing written | one line per clause C1–C7 with its measurement, then `CONTRACT PASS` with no FAIL (minutes) |
| Bench, the documented negative | `python tools/checks/alu_check_slices.py artifacts/layouts/v7_as_slice.json 1` | as above | expected to fail: `FAIL` lines and `n=1 PASS 20/32`. The stage is not a slice, and this is the measurement that says so |
| Algebra evaluators (independent of the Bench) | `python tools/checks/dc_eval.py artifacts/layouts/net_derive2.json`, `dc_eval_sub.py artifacts/layouts/net_reuse1.json`, `dc_eval_alu.py artifacts/layouts/net_alu1.json` | a network JSON in; nothing written | `ALL PASS` for the first two, `PASS 32/32` for the ALU network |
| The rule-driven placer | `cd tools/placer0 && python placer0.py ../../artifacts/placer0/problems.json p2_copy_into_side` | a problem file and a problem name; prints a placement | the placement it found and its block count; `UNKNOWN` at the bound for the infeasible problem |
| The placer's judge | `cd tools/placer0 && python placer0_check.py ../../artifacts/placer0/problems.json p4_throughline ../../artifacts/placer0/sol_p4_throughline.json` | a problem, a name and a solution JSON | `PASS`; a rejected solution prints its reason, `BISTABLE` or `TIME`, and `FAIL` |
| The feeder rig | `python tools/world/build_rig1.py` | writes two JSON files beside itself | one line per row, then `PASS 32/32  (r,f identical to pinned alu_check2 rows: 32/32)` |
| Layout regeneration | `python tools/world/make_layout_world1.py && python tools/world/make_layout_world2.py` | writes the world layouts beside the scripts | nothing; the files match the committed ones — check with `git status --porcelain` and `cmp` |
| The world stage | `python tools/world/feed.py JOB.json --out RUNDIR --run` | a job JSON naming a layout and its requirement; writes the world, the probe spec, the run results and a table under `RUNDIR` | the feeder cells it found, then one table row per artifact: Bench rows, world rows, world failures, read points, settle bound and block count. Requires software this repository does not ship — see [`tools/README.md`](tools/README.md) |
| Table checker | `python tools/check_tables.py` | reads the four fact and failure tables; nothing written | one line per row and `100 OK, 0 MISSING`, exit 0 |
| Unit tests, the Bench | `cd tools/llmgen && python -m unittest test_capcell test_strength` | — | `Ran 37 tests`, `OK (skipped=3)`. The three skips need the reference circuit, which is not part of this export |
| Unit tests, the world tool | `cd tools/world && python -m unittest test_feed` | — | `OK`; these need no server |

Two corrections to older printed lines. The unit-test line used to show 34 tests; the suite
here runs 37 with 3 skipped, the added tests being the pin-as-floor and settle-time cases,
and the count above was measured by running it. And the pinned rig line used to show
`python tools/checks/alu_check2.py artifacts/layouts/rig1_full_bench.json` at `PASS 32/32`;
run today it prints `PASS 12/32`, because a pinned input became a floor rather than a held
value, so pinning an input to 0 no longer overrides the physical feeder that the same layout
already carries. That command is not the rig's instrument. The instrument is
`tools/world/build_rig1.py` above, which drives the circuit from lever states only and still
prints `PASS 32/32`.

---

## 6. Unproven

What no file here shows. These are not softened claims; they are absences.

- **The slices in the live world.** `alu_slice_v9` and the pitch-14 slice have been read on
  the Bench and in a synthetic world only. Nothing has been placed in the live world beyond
  the single ALU stage and its rig.
- **The adder in the live world.** It is mentioned in prose, but no table, capture or
  per-cell reading of that placement is in this repository; `docs/facts.md` lists it under
  the assertions with no file.
- **Anything multi-bit.** No multi-bit adder or ALU has been built, in any world.
- **Timing.** Everything here is the DC steady state plus a settle bound measured in game
  ticks. There is no timing model, and no instrument here for tick-order behaviour — the
  priming of comparators by queued ticks, pulses, or anything that depends on the order
  within a tick. Those rules are not in the rule sheets this chain derives from.
- **Density or speed against hand-built circuits.** Never measured. Costs are reported in
  absolute numbers only.
- **The models' prior exposure to redstone.** Not claimed either way. The checkable claim is
  narrower: the rule sheets are source-derived and contain no circuit shapes, the first
  algebra stage was produced with no project context, and later stages reused only artifacts
  verified inside this development.
- **The failures listed as not exported.** `docs/failures.md` names them under its table:
  the hand-written inverse rules that missed a threshold gate, the netlist-style synthesis
  that reached 27,103 blocks, the fragment search said to have found two placer defects, the
  coordinate table typed with a minus sign the game rejects, and the rejected rig and slice
  drafts. Their records were not exported, so only the descriptions can be cited.
- **The measured-cost table and the human cost** of the closing stage: read off session
  counters at the time, with no instrument output behind them. Kept in
  [`docs/records/`](docs/records) as written, not as a fact row.

---

## 7. Versioning

The version mark is `w<surface>.r<round>` followed by the commit the reader has checked out.
`w` is the strongest surface on which a row of the facts table stands — 0 the Bench, 1 the
synthetic world, 2 the live world. `r` is the number of completed rounds in which an
independent reviewer's findings were answered by a file in this repository, counted from
[`PUBLICATION_CHECKLIST.md`](PUBLICATION_CHECKLIST.md) section 7 and the reviewer records
under `docs/`: the publication reading of the four key documents, answered in the checklist's
sections 5 and 6 and in both READMEs; the reading of the slice checker, answered by
`tools/checks/alu_check_contract.py`, `artifacts/layouts/alu_slice_v9.json` and the amended
`docs/placement/slice-contract.md`; the round that asked for the placer's solutions to be
replayed in a world, answered by `tools/llmgen/capcell.py`, `tools/placer0/` and
`docs/world/world4-record.md`; and the round that followed the world stage becoming a tool,
answered by `tools/world/feed.py`, `artifacts/world/feed1/`,
`artifacts/layouts/reviewer_slice_p14_relocated.json`,
`docs/placement/xcheck-second-reviewer-slice-search.md` and `docs/world/p4-decay-trace.md`.
The current mark is therefore **`w2.r4`**, plus the commit — `git rev-parse --short HEAD`.
Nothing is tagged.

---

## 8. Credits

- **Astra** — second-model reviewer (GPT-6, OpenAI). Design critique of the orders, independent re-checks of the derived networks, the 2,990-case mux check, and the review that reshaped the placement and the algorithmisation proposal.
- **pashina** — operator: circuit semantics rulings, in-world verification, and the
  reference circuit used to calibrate the Bench. [@pashina_2](https://x.com/pashina_2)
- Derivations, placements and tooling by LLM agents (Claude Fable 5.1 / Opus 5) under the
  operator's direction.

MIT licensed — see [LICENSE](LICENSE).

Not affiliated with Mojang or Microsoft. Minecraft is a trademark of Mojang Studios. No
game code, jar, world save, or mod is distributed in this repository.
