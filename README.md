# Jiorimetry

> 日本語: [README.ja.md](README.ja.md)

A toolchain that derives Minecraft 1.20.6 redstone circuits from rule tables written out of
the game's source, instead of copying circuits people already know. The rules so far are the
DC signal-strength arithmetic (comparator, container, dust decay, strongly powered solids).
Results are read in three places: the Bench (a replica of the rules), a synthetic vanilla
world (headless server), and the world the operator actually plays in.
*Jiorimetry — jiori (self-weaving) + -metry.*

## Why this way

A copied circuit has to be rebuilt when a part or the requirement changes, and nothing
carries over to the next one. Derived from a rule table, it can be re-derived for exactly
the rules that changed. The table contains no circuit shapes; a shape in the table is the
answer written in advance. The Bench keeps judging cheap, but it cannot be more correct than
the person who read the source, so the last reading is taken in the world.

## What is here

Six stages from the rules to a placed artifact.

1. **Rule tables** — the decompiled 1.20.6 source written as tables with line numbers. No
   circuit shapes. [`docs/rules/`](docs/rules)
2. **Algebra** — an LLM agent is given the tables and a question and returns a network of
   comparator / torch / constant nodes with explicit level encodings. Independent evaluators
   check the network: `tools/checks/dc_eval.py`, `dc_eval_sub.py`, `dc_eval_alu.py`.
   Records in [`docs/algebra/`](docs/algebra)
3. **Placement** — coordinates for the network. Agent-derived layouts are in
   [`docs/placement/`](docs/placement); small problems go through the rule-driven placer
   `tools/placer0/placer0.py` and its checker `placer0_check.py`
4. **Bench** — `tools/llmgen/capcell.py` re-implements the DC rules (rule machine in
   `machine.py`, part table in `library.py`), solves a block list to a fixed point from a
   cold and a hot seed, and steps game ticks when settling is the question. The layout
   checkers `tools/checks/alu_check2.py`, `alu_check_slices.py`, `alu_check_contract.py` all
   ask it
5. **Synthetic world** — `tools/world/feed.py` takes a layout and a requirement, searches
   for feeder cells, builds a void 1.20.6 world (`synthworld.py`, `worldgen.py`), drives
   every row over RCON (`worldprobe.py`) and writes the tables. Records in
   [`docs/world/`](docs/world)
6. **Live world** — the same block list is written as a placement program
   (`tools/llmgen/cell_to_program.py`), placed in the save, and read back from the region
   files with `tools/world/regioncap.py`

File list and requirements: [`tools/README.md`](tools/README.md).

## Running it

Python 3.11 or later, standard library only. Run from the repository root.

```
git clone https://github.com/pashina2/jiorimetry.git && cd jiorimetry
```

Without git: download the [ZIP](https://github.com/pashina2/jiorimetry/archive/refs/heads/main.zip),
unpack it and run inside that directory.

| what | command | output when it passes |
|---|---|---|
| Bench, full-adder sweep | `python tools/checks/bench_sweep.py artifacts/layouts/layout_place1.json` | one line per vector, then `ALL PASS` |
| Bench, one ALU stage | `python tools/checks/alu_check2.py artifacts/layouts/alu_stage_v7.json` | `LINT L3 …` then `PASS 32/32`; writes `LAYOUT.rows.json` next to the layout |
| Bench, n slices tiled | `python tools/checks/alu_check_slices.py artifacts/layouts/alu_slice_v9.json 3` | `n=3 PASS 512/512` (n=3 takes minutes) |
| Bench, slice contract | `python tools/checks/alu_check_contract.py artifacts/layouts/alu_slice_v9.json` | C1–C7 one line each, then `CONTRACT PASS` (minutes) |
| Bench, a failing case | `python tools/checks/alu_check_slices.py artifacts/layouts/v7_as_slice.json 1` | `FAIL` lines and `n=1 PASS 20/32`; a stage is not a slice |
| Algebra evaluators | `python tools/checks/dc_eval.py artifacts/layouts/net_derive2.json`, `dc_eval_sub.py artifacts/layouts/net_reuse1.json`, `dc_eval_alu.py artifacts/layouts/net_alu1.json` | `ALL PASS` for the first two, `PASS 32/32` for the ALU |
| Placer | `cd tools/placer0 && python placer0.py ../../artifacts/placer0/problems.json p2_copy_into_side` | the placement found and its block count; `UNKNOWN` at the budget for unsolvable problems |
| Placer checker | `cd tools/placer0 && python placer0_check.py ../../artifacts/placer0/problems.json p4_throughline ../../artifacts/placer0/sol_p4_throughline.json` | `PASS`; rejected solutions print the reason (`BISTABLE` / `TIME`) and `FAIL` |
| Feeder rig | `python tools/world/build_rig1.py` | ends with `PASS 32/32  (r,f identical to pinned alu_check2 rows: 32/32)`; writes two JSON files next to the script |
| Layout regeneration | `python tools/world/make_layout_world1.py && python tools/world/make_layout_world2.py` | no output; matches the committed files |
| Synthetic world | `python tools/world/feed.py JOB.json --out RUNDIR --run` | the feeder cells found, then one line per artifact (Bench rows, world rows, world failures, read points, settle bound, blocks). Needs a 1.20.6 server jar and Java 21 that are not distributed here ([`tools/README.md`](tools/README.md)) |
| Table checker | `python tools/check_tables.py` | one line per row and `100 OK, 0 MISSING` |
| Unit tests | `cd tools/llmgen && python -m unittest test_capcell test_strength` | `Ran 37 tests`, `OK (skipped=3)`; the three skips need a reference circuit that is not exported |
| Unit tests, world tools | `cd tools/world && python -m unittest test_feed` | `OK`; no server needed |

`python tools/checks/alu_check2.py artifacts/layouts/rig1_full_bench.json` now prints
`PASS 12/32`. Pins became floors (the max of the pin and its neighbours), so pinning an input
to 0 no longer overrides the feeder that is already in that layout. The rig is measured by
`build_rig1.py` above.

## What it has produced

Every number below is copied from a row of [`docs/facts.md`](docs/facts.md)
([日本語](docs/facts.ja.md)). Each row names the file that shows it and the string in that
file, and `tools/check_tables.py` re-checks them. Claims without a file are listed under the
table, not in it.

In the world the operator plays in:

- ALU stage `v7` placed in the save: 176 of 176 blocks matched the list, 6 of 6 containers
  held what was declared. At rest 23 of 23 comparators matched the Bench; with the lever in
  both states, 24 of 24 ([`docs/world/live-alu-record.md`](docs/world/live-alu-record.md);
  raw captures in `artifacts/world/`).

In the synthetic vanilla world (the server and Java are not distributed, so these are
followed through the records and the run result JSON):

- 1-bit full adder: all 8 inputs matched the Bench, settling in 2–10 ticks, 112 comparator
  comparisons with 0 unequal ([`docs/world/world1-record.md`](docs/world/world1-record.md)).
- ALU stage `v7`: all 32 rows matched, 1024 of 1024 read points
  ([`docs/world/world2-record.md`](docs/world/world2-record.md)). Re-driven by the tools
  alone: 1472 of 1472, 0 model tokens (`artifacts/world/feed1/out_v7/`).
- Two `alu_slice_v9` slices: all 128 rows matched, 14976 read points with 0 unequal; 13 rows
  did not close a 10-tick stable window inside the 40-tick bound and are recorded as
  unsettled ([`docs/world/world4-record.md`](docs/world/world4-record.md)). Tools alone:
  19328 of 19328 (`artifacts/world/feed1/out_world4/`).
- The pitch-14 slice found by the second reviewer, never seen by the tools before: all 128
  rows matched, 20608 of 20608 (`artifacts/world/feed1/out_p14_final/`).
- Five placer solutions: 13 of 14 rows matched, one did not (105 of 112 points). That one row
  is the first item under "What broke".
- The loop-free solution of the through-line problem: both rows matched, settling in 8
  ticks, 68 blocks ([`docs/world/p4-decay-trace.md`](docs/world/p4-decay-trace.md)).
- Cost of the 13 tool-driven world runs: 3648392 RCON calls, 1483.3 seconds, 0 model tokens
  ([`docs/world/feed1-record.md`](docs/world/feed1-record.md)).

Bench-only rows (v9 at n=1/2/3 with 32/128/512, the contract C1–C7, the algebra evaluators
and more) are in the table.

## What broke

All of it is in [`docs/failures.md`](docs/failures.md) ([日本語](docs/failures.ja.md)), each row
with the file that showed it, what changed, and a command to reproduce it. The main ones:

- **Pinned inputs were assumed safe.** A solution drove its own input hard enough to pass the
  pin and latched in the world. Bench pins became floors (the max of the pin and its
  neighbours) and the solution that used to pass is now rejected
  (`artifacts/placer0/sol_p4_throughline.latched.json`).
- **One cold-start iteration was assumed to give the DC solution.** It missed bistable
  circuits. The Bench now solves from a cold and a hot seed and reports the cells that differ.
- **The re-solved solution was predicted to pass in the world, 2/2, in writing.** It did not.
  The cause was time, not DC: the Bench gained a settling bound (`set_floors`,
  `settle_after`) and the checker now drives every ordered pair of pin vectors
  (`sol_p4_throughline.decay.json`).
- **A value standing at the end of a 40-tick window was taken for a latch.** It was decaying
  at 1 level per hop, 4 ticks per round, 56 ticks in all. A change touching the bound is now
  recorded as cut off, not settled.
- **One ALU stage was called a slice.** Tiled, it fails (`v7_as_slice.json`, `20/32`). The
  slice conditions became the contract checker C1–C7, and `alu_slice_v9` at pitch 12 passes it.
- **Pitch 11 failed at the same boundary in all six searches.** Record:
  [`docs/placement/xcheck-second-reviewer-slice-search.md`](docs/placement/xcheck-second-reviewer-slice-search.md).

The round-by-round write-ups are kept as written in [`docs/records/`](docs/records).

## What is not here

- Slices (`v9`, pitch 14) placed in the live world. Bench and synthetic world only.
- A placement record of the full adder in the live world (it appears in prose; no table, no
  capture).
- Anything multi-bit.
- Rules about time. Comparator priming (the order of scheduled ticks), pulses and in-tick
  ordering are not in the rule tables and have no instrument. What exists is DC steady state
  plus a settling bound measured in ticks.
- Density or speed comparisons against hand-built circuits.
- Records of the failures that were not exported (the hand-written inverse rules that missed
  the threshold gate, the 27,103-block netlist, two placer defects found by a fragment search,
  a coordinate table typed with a minus sign the game rejects, rejected drafts). Only their
  names are listed under `docs/failures.md`.
- Backing for the cost table and the human-side cost: read off session counters, no
  instrument output behind them.

## Version

The mark is `w<surface>.r<round>` plus the commit. `w` is the strongest surface with a row
under "What it has produced": 0 Bench, 1 synthetic world, 2 live world. `r` is the number of
times an independent reviewer's findings were answered by files in this repository (counted
from [`PUBLICATION_CHECKLIST.md`](PUBLICATION_CHECKLIST.md) §7 and the reviewer records
under `docs/`). Currently **`w2.r4`** + `git rev-parse --short HEAD`. No tags.

## Credits and license

- **pashina** — operator: circuit semantics rulings, in-world verification, and the
  reference circuit used to calibrate the Bench. [@pashina_2](https://x.com/pashina_2)
- Derivations, placements and tooling by LLM agents (Claude Fable 5.1 / Opus 5) under the
  operator's direction.
- **Astra** — second-model reviewer (GPT-6, OpenAI). Design critique of the orders,
  independent re-checks of the derived networks, the 2,990-case mux check, and the review
  that reshaped the placement and the algorithmisation proposal.

MIT licensed — see [LICENSE](LICENSE).

Not affiliated with Mojang or Microsoft. Minecraft is a trademark of Mojang Studios. No
game code, jar, world save, or mod is distributed in this repository.
