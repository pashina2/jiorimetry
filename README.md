# Jiorimetry

> 日本語: [README.ja.md](README.ja.md)

A toolchain for deriving Minecraft 1.20.6 redstone circuits from rule tables written out of the
game's source, rather than copying circuits that are already known. The rules covered so far
are the DC signal-strength arithmetic — comparator, container, dust decay, strongly powered
solids. A derived layout is read in three places: the Bench, which is a replica of the rules;
a synthetic vanilla world on a headless server; and the world the operator actually plays in.
Only the last of these counts as a result.
*Jiorimetry — jiori (self-weaving) + -metry.*

## Approach

A copied circuit carries no account of itself, so every change to a part or a requirement
means rebuilding it, and nothing learned transfers to the next circuit. A circuit derived from
a rule table can be re-derived for exactly the rules that changed, and the derivation itself
becomes material for the next search. For that reason the rule tables contain no circuit
shapes at all: a shape in the table is an answer given in advance, and everything downstream
of it becomes a check of a known circuit rather than a derivation.

The Bench is a re-implementation of the rules, cheap enough to run over every candidate, but
it can be no more correct than the reading of the source behind it. The synthetic world runs
the game's own code, but it is not a save anyone plays in. The cheap stages exist to make
failure cheap; they predict the last stage and do not replace it. That is the standing
assumption behind every number in this repository.

The judge should differ from the world in speed and nothing else. A shortcut that makes
judging cheap is a property of the instrument, not of the game, and every failure reported
here turned out to be a hole in a shortcut rather than an error in a rule: a fixed point with
no notion of time, an input held rather than driven, a single starting state. A shortcut is
kept only while it can be shown to hide nothing, and is removed the moment it does.

## Layout of the toolchain

Six stages connect the rules to a placed artifact.

1. **Rule tables** — the decompiled 1.20.6 source rendered as human-readable tables with line
   references: comparator, composter, torch, wire and the solidity predicate. No circuit
   shapes. [`docs/rules/`](docs/rules)
2. **Algebra** — an LLM agent is given the tables and a question and returns a network of
   comparator / torch / constant nodes with explicit level encodings. The network is not a
   layout; it is checked by evaluators written independently of it: `tools/checks/dc_eval.py`,
   `dc_eval_sub.py`, `dc_eval_alu.py`. Records in [`docs/algebra/`](docs/algebra)
3. **Placement** — coordinates for the network. Layouts the agent derived under the geometric
   rule table (adjacency, dust shape, diagonal reads, vertical hand-off) are in
   [`docs/placement/`](docs/placement); small problems are handled by the rule-driven placer
   `tools/placer0/placer0.py` and its checker `placer0_check.py`
4. **Bench** — `tools/llmgen/capcell.py` re-implements the DC rules (rule machine in
   `machine.py`, part table in `library.py`), solves a block list to a fixed point from a cold
   and a hot seed, and steps game ticks when settling is in question. Calibrated against a
   reference circuit the agent never sees. The layout checkers `tools/checks/alu_check2.py`,
   `alu_check_slices.py` and `alu_check_contract.py` all consult this one Bench
5. **Synthetic world** — `tools/world/feed.py` takes a layout and a requirement, searches for
   physical feeder cells to replace pinned inputs, generates a void 1.20.6 world
   (`synthworld.py`, `worldgen.py`), drives every row over RCON while freezing and stepping
   (`worldprobe.py`), and writes the tables from the run's own output. Records in
   [`docs/world/`](docs/world)
6. **Live world** — the same block list is written out as a placement program
   (`tools/llmgen/cell_to_program.py`), placed in the save, and read back from the region files
   with `tools/world/regioncap.py`, without a server

The file list and the requirements for running are in [`tools/README.md`](tools/README.md).

## Running

Python 3.11 or later, standard library only. Run from the repository root.

```
git clone https://github.com/pashina2/jiorimetry.git && cd jiorimetry
```

Without git, unpack the [ZIP](https://github.com/pashina2/jiorimetry/archive/refs/heads/main.zip)
and run inside that directory.

| target | command | output on pass |
|---|---|---|
| Bench, full-adder sweep | `python tools/checks/bench_sweep.py artifacts/layouts/layout_place1.json` | one line per vector, then `ALL PASS` |
| Bench, one ALU stage | `python tools/checks/alu_check2.py artifacts/layouts/alu_stage_v7.json` | `LINT L3 …` followed by `PASS 32/32`; writes `LAYOUT.rows.json` beside the layout |
| Bench, n slices tiled | `python tools/checks/alu_check_slices.py artifacts/layouts/alu_slice_v9.json 3` | `n=3 PASS 512/512` (n=3 takes minutes) |
| Bench, slice contract | `python tools/checks/alu_check_contract.py artifacts/layouts/alu_slice_v9.json` | one line per clause C1–C7, then `CONTRACT PASS` (minutes) |
| Bench, a failing case | `python tools/checks/alu_check_slices.py artifacts/layouts/v7_as_slice.json 1` | `FAIL` lines and `n=1 PASS 20/32`; the measurement that says a stage is not a slice |
| Algebra evaluators | `python tools/checks/dc_eval.py artifacts/layouts/net_derive2.json`, `dc_eval_sub.py artifacts/layouts/net_reuse1.json`, `dc_eval_alu.py artifacts/layouts/net_alu1.json` | `ALL PASS` for the first two, `PASS 32/32` for the ALU network |
| Placer | `cd tools/placer0 && python placer0.py ../../artifacts/placer0/problems.json p2_copy_into_side` | the placement found and its block count; `UNKNOWN` at the budget for unsolvable problems |
| Placer checker | `cd tools/placer0 && python placer0_check.py ../../artifacts/placer0/problems.json p4_throughline ../../artifacts/placer0/sol_p4_throughline.json` | `PASS`; a rejected solution prints the reason (`BISTABLE` / `TIME`) and `FAIL` |
| Feeder rig | `python tools/world/build_rig1.py` | ends with `PASS 32/32  (r,f identical to pinned alu_check2 rows: 32/32)`; writes two JSON files beside the script |
| Layout regeneration | `python tools/world/make_layout_world1.py && python tools/world/make_layout_world2.py` | no output; byte-identical to the committed files |
| Synthetic world | `python tools/world/feed.py JOB.json --out RUNDIR --run` | the feeder cells found, then one line per artifact (Bench rows, world rows, failures, read points, settle bound, blocks). Needs a 1.20.6 server jar and Java 21, neither distributed here ([`tools/README.md`](tools/README.md)) |
| Table checker | `python tools/check_tables.py` | one line per row, then `100 OK, 0 MISSING` |
| Unit tests | `cd tools/llmgen && python -m unittest test_capcell test_strength` | `Ran 37 tests`, `OK (skipped=3)`; the three skips need a reference circuit that is not exported |
| Unit tests, world tools | `cd tools/world && python -m unittest test_feed` | `OK`; no server needed |

Note that `python tools/checks/alu_check2.py artifacts/layouts/rig1_full_bench.json` now prints
`PASS 12/32`. Pins changed from held values to floors (the max of the pin and its neighbours),
so pinning an input to 0 no longer overrides the feeder already present in that layout; the
instrument for the rig is `build_rig1.py` above.

## Results

Every number below is copied from a row of [`docs/facts.md`](docs/facts.md)
([日本語](docs/facts.ja.md)). Each row cites the file that shows the number and the string in
that file, and `tools/check_tables.py` verifies that the citations exist. Claims without a file
are listed under the table, not in it.

**Live world** — ALU stage `v7` was placed in the save: 176 of 176 blocks matched the list and
6 of 6 containers held what was declared. At rest 23 of 23 comparators matched the Bench, and
with the lever in both states 24 of 24 did
([`docs/world/live-alu-record.md`](docs/world/live-alu-record.md); raw captures in `artifacts/world/`).

**Synthetic world** — the server and Java are not distributed, so these are followed through
the records and the run result JSON.

- 1-bit full adder: all 8 inputs matched the Bench, settling in 2–10 ticks, 112 comparator
  comparisons with 0 unequal ([`docs/world/world1-record.md`](docs/world/world1-record.md)).
- ALU stage `v7`: all 32 rows matched, 1024 of 1024 read points
  ([`docs/world/world2-record.md`](docs/world/world2-record.md)). Re-driven by the tools alone:
  1472 of 1472, with 0 model tokens spent meanwhile (`artifacts/world/feed1/out_v7/`).
- Two `alu_slice_v9` slices: all 128 rows matched, 14976 read points with 0 unequal; 13 rows
  did not close a 10-tick stable window inside the 40-tick bound and are recorded as unsettled
  ([`docs/world/world4-record.md`](docs/world/world4-record.md)). Tools alone: 19328 of 19328
  (`artifacts/world/feed1/out_world4/`).
- The pitch-14 slice found by the second reviewer, unseen by the tools until then: all 128 rows
  matched, 20608 of 20608 (`artifacts/world/feed1/out_p14_final/`).
- Five placer solutions: 13 of 14 rows matched and one did not (105 of 112 points). That row is
  the first item in the next section.
- The loop-free solution of the through-line problem: both rows matched, settling in 8 ticks,
  68 blocks ([`docs/world/p4-decay-trace.md`](docs/world/p4-decay-trace.md)).
- Cost of the 13 tool-driven world runs: 3648392 RCON calls, 1483.3 seconds, 0 model tokens
  ([`docs/world/feed1-record.md`](docs/world/feed1-record.md)).

Bench-only rows (v9 at n=1/2/3 with 32/128/512, the contract C1–C7, the algebra evaluators
and more) are in the table.

## Failures

All of them are in [`docs/failures.md`](docs/failures.md) ([日本語](docs/failures.ja.md)), each
with the file that showed it, what changed as a result, and a command to reproduce it. The main
ones:

- **Pinned inputs were assumed safe.** A solution drove its own input hard enough to pass the
  pin and latched in the world. Bench pins became floors (the max of the pin and its
  neighbours), and the solution that used to pass is now rejected
  (`artifacts/placer0/sol_p4_throughline.latched.json`).
- **A single iteration from a cold start was assumed to yield the DC solution.** It missed
  bistable circuits. The Bench now solves from a cold and a hot seed and reports the cells on
  which they differ.
- **The re-solved solution was predicted to pass in the world — 2/2, written before the run.**
  It did not. The cause was time rather than DC: the Bench gained a settling bound
  (`set_floors`, `settle_after`) and the checker now drives every ordered pair of pin vectors
  (`sol_p4_throughline.decay.json`).
- **A value standing at the end of a 40-tick window was read as a latch.** It was decaying at
  1 level per hop, 4 ticks per round, 56 ticks in all. A change touching the bound is now
  recorded as cut off, not settled.
- **One ALU stage was called a slice.** Tiled, it fails (`v7_as_slice.json`, `20/32`). The slice
  conditions became the contract checker C1–C7, which `alu_slice_v9` at pitch 12 passes.
- **Pitch 11 failed at the same boundary in all six searches.** Record:
  [`docs/placement/xcheck-second-reviewer-slice-search.md`](docs/placement/xcheck-second-reviewer-slice-search.md).

The round-by-round write-ups are kept as written in [`docs/records/`](docs/records).

## Not done

What no file here shows, stated as absence rather than as a softened claim.

- Slices (`v9`, pitch 14) placed in the live world. Bench and synthetic world only.
- A placement record of the full adder in the live world; it appears in prose, with no table
  and no capture.
- Anything multi-bit.
- Rules about time. Comparator priming (the order of scheduled ticks), pulses and in-tick
  ordering are not in the rule tables and have no instrument. What exists is DC steady state
  plus a settling bound measured in ticks.
- Density or speed comparisons against hand-built circuits; costs are reported in absolute
  terms only.
- Records of the failures that were not exported: the hand-written inverse rules that missed
  the threshold gate, the netlist approach that reached 27,103 blocks, two placer defects
  attributed to a fragment search, a coordinate table typed with a minus sign the game
  rejects, and rejected drafts. Only their names appear under the table in `docs/failures.md`.
- Backing for the cost table and the human-side cost: read off session counters, with no
  instrument output behind them.

## Version

The mark is `w<surface>.r<round>` plus the commit. `w` is the strongest surface with a row
under "Results": 0 Bench, 1 synthetic world, 2 live world. `r` is the number of times an
independent reviewer's findings were answered by files in this repository, counted from
[`PUBLICATION_CHECKLIST.md`](PUBLICATION_CHECKLIST.md) §7 and the reviewer records under
`docs/`. Currently **`w2.r4`** + `git rev-parse --short HEAD`. No tags.

## Credits and license

- **pashina** — operator: circuit semantics rulings, in-world verification, and the reference
  circuit used to calibrate the Bench. [@pashina_2](https://x.com/pashina_2)
- Derivations, placements and tooling by LLM agents (Claude Fable 5.1 / Opus 5) under the
  operator's direction.
- **Astra** — second-model reviewer (GPT-6, OpenAI). Design critique of the orders, independent
  re-checks of the derived networks, the 2,990-case mux check, and the review that reshaped the
  placement and the algorithmisation proposal.

MIT licensed — see [LICENSE](LICENSE).

Not affiliated with Mojang or Microsoft. Minecraft is a trademark of Mojang Studios. No game
code, jar, world save, or mod is distributed in this repository.
