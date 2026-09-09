# The README's per-round text, as it was written

> 日本語: [readme-rounds.ja.md](readme-rounds.ja.md) · Index: [README.md](README.md)

The sections below were the README's account of the work round by round up to 2026-09-08:
the results, the provenance table, the failures in prose, the measured costs and the
repository layout. They are kept here word for word. Only the relative links were repointed
to this directory, and the section numbers and cross-references are the ones the README
carried at the time, not the current ones.

The current statements of the project are the two tables, [`facts.md`](../facts.md) and
[`failures.md`](../failures.md). Where this text and a table disagree, the table is the later
reading: in particular the unit-test count and the pinned-rig line printed in the old
reproduction section were superseded, and that section is not reproduced here — the current
commands are in the README's reference section.

---

## 2. Results

### 1-bit full adder (PLACE-1 / WORLD-1)

Level encoding {0, 5}. Seven comparators. The algebra was produced by an agent with **zero
project context** — it was given only the DC rule sheet and the question.

- Bench: `ALL PASS` over all 8 input vectors — [`docs/placement/place1-bench-output.txt`](../placement/place1-bench-output.txt)
- Synthetic world: 8/8, every read matched the Bench prediction, settle 2–10 game ticks —
  [`docs/world/world1-tables.md`](../world/world1-tables.md), raw
  [`artifacts/world/world1.run.result.json`](../../artifacts/world/world1.run.result.json)
- Operator's world: placed and read back, 8/8.

### 1-bit ALU stage (`alu_stage_v7`)

Data lines carry {0, 3}. Two control lines: `P` ∈ {0, 15} selects arithmetic vs. logic,
`Wn` ∈ {0, 15} selects ADD/AND vs. SUB/OR. Three identities do the work:

- `r_SUB = r_ADD = parity(a, b, k)`
- `f = maj(a ⊕ W, b, k)` — carry and borrow on one wire
- `AND = carry(a, b, 0)`, `OR = carry(a, b, 1)` — the logic ops *are* the carry comparator

176 blocks: 23 comparators, 14 repeaters, 35 dust, 6 containers (four level-3 constants,
two level-9), 1 redstone block, 1 torch, 96 smooth stone. Box 11 × 3 × 12.

- Bench: `PASS 32/32`, `r` and `f` land on exactly {0, 3} —
  [`artifacts/rows/alu_stage_v7.json.rows.json`](../../artifacts/rows/alu_stage_v7.json.rows.json)
- Synthetic world: **32/32 rows, 1024/1024 individual cell reads matched**, settle 2–14 gt —
  [`docs/world/world2-record.md`](../world/world2-record.md), raw
  [`artifacts/world/world2.run.result.json`](../../artifacts/world/world2.run.result.json)
- Operator's world: 176/176 blocks placed, 23/23 static comparators matched, and three
  driven states read out of the region files —
  [`docs/world/live-alu-record.md`](../world/live-alu-record.md)
- A 93-block feeder rig (5 levers, 4 composter constants, 2 lamps) makes all 32 rows
  operable by hand — [`docs/placement/rig1-result.md`](../placement/rig1-result.md)

---

### Update (2026-09-07, later the same day): a bit slice that abuts

The stage v7 above is a working 1-bit stage but not a bit slice: its `a` input needed three cells (one outside the pitch), the second `P` entry and the `Wn` row were not through-lines, and its east edge was not closed. The operator ruled that bit-slice abutment and pitch alignment had to be met before any second stage. A slice contract was written (`docs/placement/slice-contract.md`) and an n-slice checker (`tools/checks/alu_check_slices.py`) that tiles a layout by its pitch and solves the n-bit ALU function for all inputs and modes. Result `artifacts/layouts/alu_slice_v8.json` (pitch 12, box 12x4x14, 292 blocks: comparator 50, repeater 15, wire 55, barrel 7): n=1 32/32, n=2 128/128, n=3 512/512, placement lint 0 on the tiled layout. Details and the boundary cell list: `docs/placement/slice1-result.md`; two-slice layer map: `artifacts/images/alu_slice_v8_x2_layers.png`. Not yet done: the two-slice run in a synthetic world and in the operator's world.

**Second reviewer's correction (2026-09-08).** Astra read the checker and found that it verifies the n-bit function table only: clause 2 of the contract (the through-line exit restored to 15 inside each slice) was never measured, and `v8` violates it (P exits at 9, Wn at 12). A second checker, `tools/checks/alu_check_contract.py`, now measures every clause directly (box, through-line entry level per slice, carry level per slice, port faces, boundary pairs and per-slice local truth table, lint and repeater side lock) and states in its docstring what it does not check. `v8` fails it (1024 through-line mismatches over 512 rows). `artifacts/layouts/alu_slice_v9.json` replaces the two exit wires with repeaters facing west (block count unchanged) and passes both checkers: n=1 32/32, n=2 128/128, n=3 512/512, contract 0 FAIL. Two contract clauses were amended and the amendment is recorded in `docs/placement/slice-contract.md`; details in `docs/placement/slice1-result.md` section 4.

**Two slices in the synthetic world (WORLD-4, 2026-09-08).** Two abutting `v9` slices, 41 feeder blocks, all 128 rows of n=2 driven by levers in a headless 1.20.6 world: r0, r1, f, the slice-1 through-line entries, the intermediate carry and every comparator's powered state agree with the Bench at all 14,976 read points. Record `docs/world/world4-record.md`, raw `artifacts/world/world4b1..b3.run.result.json` (three runs because of the rcon budget).

### PLACER-0: a rule-driven placer, and the latch the world found

The operator asked for the LLM-derived part to be algorithmised, and later ruled the direction outright: shrink what the LLM occupies, and end with the derivation itself as an algorithm. The first stage removed was the world stage: `tools/world/feed.py` (FEED-1) takes a layout, searches the feeder cells for every pin, checks the fed layout on the Bench against expected values computed from the requirement (not from the Bench), builds the world and the worldprobe spec, runs it, and writes the table from the tool's own output. It reproduced WORLD-2 and WORLD-4 unattended and ran a slice it had never seen (the reviewer's pitch-14 slice) at 128/128; the 13 world runs after it cost no model tokens. Record: `docs/world/feed1-record.md`; spec: `docs/world/feed1-spec.md`. PLACER-0 (`tools/placer0/`, `docs/placement/placer0.md`) is a small pilot: six placement problems cut from the ALU fragments (pins, output cells, forbidden cells, a block budget; `artifacts/placer0/problems.json`), a Bench-oracle judge, and an IDA* search over (partial layout, unresolved requirements) whose moves are the DC rules read backwards. It solved 5 of the 5 satisfiable problems with no human coordinates (p3 was unsatisfiable by the problem author's mistake). The second reviewer (Astra) then pointed out that the searcher and the judge share the Bench's rule gaps, and asked for the five solutions to be replayed in a world before anything larger was built. WORLD-4 did that: 13 of the 14 rows matched, and the one that did not (`p4_throughline`, T = 0) is a latch — see section 6. The Bench was corrected (pins are floors, and every DC solve now runs from a cold and a hot seed), the corrected judge rejects the old p4 solution, and the placer re-solved p4 in 0.9 s with a loop whose gain decays instead (`artifacts/placer0/sol_p4_throughline.json`; the latched one is kept as `sol_p4_throughline.latched.json`).

![Two abutting slices of `alu_slice_v9`, layer by layer (pitch 12; n=2 Bench 128/128; contract C1-C6 PASS).](../../artifacts/images/alu_slice_v9_x2_layers.png)


## 3. What is **not** claimed

- **It is not a bit slice yet.** The operator assessed the bit-slice work — abutment of
  neighbouring slices and pitch alignment — as not met, and ruled that it must be met
  before a second stage is attempted. `v7` works as one stage; it is not a slice. A formal
  slice contract (pitch ≤ 12 in +x, through-lines restored to 15 inside each slice, carry
  hand-off exactly 0/3, ports on the south or top face only, and closure under tiling) is
  written down in [`docs/placement/slice-contract.md`](../placement/slice-contract.md),
  and reading `v7` against that contract scores **20/32** — see the reproduction below.
- **No 8-bit anything.** No multi-bit adder or ALU has been built.
- **No timing claims.** Everything here is DC / steady state. Settle times are reported as
  observations, not as a model.
- **No density or speed comparison** against hand-built circuits. Costs are reported in
  absolute numbers only.
- **No claim that the models had no prior exposure to redstone.** The claim is narrower and
  checkable: the rule sheets are source-derived and contain no circuit shapes, the first
  algebra stage was produced blind, and later stages reused only artifacts verified inside
  this development. See §4.

---

## 4. Provenance (what each agent was given)

| stage | context | given | withheld |
|---|---|---|---|
| DERIVE-2 (adder algebra) | blind, zero context | DC rule sheet + the question | the reference circuit, the web, every other file |
| PLACE-1 (adder placement) | blind | geometry rule sheet + DERIVE-2's network | same |
| REUSE-1 (full subtractor) | blind | a **byte-identical** rule sheet (sha256 `e6001fed…`), only the question swapped | same |
| ALU-1 (ALU algebra) | not blind | rule sheet + the {0,3} adder and subtractor networks derived above + a mux suggestion from Astra (second-model reviewer, GPT-6) | the reference circuit; the source was not opened |
| PLACE-ALU-3 (ALU placement) | not blind | rule sheets v2 + the failing 30/32 predecessor + this session's analysis | the reference circuit, the web |
| RIG-1 (feeder) | not blind | the above + the synthetic-world feeder shape | same |

The operator's own pre-existing reference circuit was used **only** to calibrate the Bench.
It was never shown to any agent that produced a design.

---

## 6. Failures worth reporting

- **Netlist-style synthesis, 27,103 blocks.** An earlier approach borrowed the EDA pipeline
  wholesale — cut the arithmetic into a gate netlist, then hand it to a placer. The placer
  could not carry signal strength through the net, so it spent about 158 dust per
  comparator and produced a 27,103-block artifact that was larger than the naive baseline.
  The correction was to stop cutting: derive the algebra and the placement together, in
  signal-strength terms, and never lower to a boolean netlist.
- **T6 at 30/32, fixed by changing the algebra rather than the coordinates.** Two SUB rows
  failed because the `a` input had no cell it could legally reach on the `x2` comparator's
  side. Every geometric fix collided with a support cell already in use. The fix was to
  rewrite that part of the algebra — `S_x = max(a, W3)`, `as = sub(a, [Wn])`,
  `xm = sub(S_x, [as])` — and to move the `P` kill from one comparator's side to a shared
  side. That deleted a whole column of the layout and the impossible cell with it.
  See [`docs/placement/placealu3-result.md`](../placement/placealu3-result.md).
- **Rig drafts caught on the Bench, not in the world.** `draft_1` scored 32/32 but carried
  14 diagonal dust links and was rejected against the L2 constraint; `draft_2` scored 20/32
  because one repeater's back cell was air. And one feeder cell had to be left as air
  because the cell above it is a strongly-powered stage relay — a rule learned in the
  synthetic world and applied before any block reached the operator's save. Three separate
  world builds were avoided at zero cost.
- **Operational misses recorded in the notes**, including a container reported as filled
  that was not (twice), and a table of coordinates typed with U+2212 instead of
  hyphen-minus, which the game rejected.

---

- **A held pin hides a latch (WORLD-4, `p4_throughline` at T = 0).** The PLACER-0 solution
  passed the Bench judge and the placer's oracle (the same Bench) and latched in the world:
  a solution relay strongly powered the pin dust, so after T had been 15 the pin held
  itself at 15. The Bench could not see it because a pinned cell was a HELD value that the
  circuit could not raise, and because a cold-start iteration walks to the 0 fixed point even
  when a second one exists. Both are fixed in `tools/llmgen/capcell.py`: a pin is now a
  floor (max of neighbours and source), and `dc_solve_both` solves from a cold and a hot
  seed and reports the cells on which the two solutions differ (`test_capcell.py`,
  `FloorAndLatchTests`). Under the corrected Bench the old p4 is BISTABLE at T = 0 exactly
  where the world latched, and every other layout in this repository still passes. The class
  of failure had been predicted by the second reviewer before the run; the world supplied the
  instance. Record: `docs/world/world4-record.md` sections 7.1-7.3.

- **A decay of 56 gt read as a latch (FEED-1, the re-solved `p4`).** After the Bench was corrected, the placer
  re-solved `p4` with a loop that loses one level per round. In the world it still read O = 15 at T = 0 in three runs,
  the Bench said O = 0 from every seed, and the case was filed as a spec-vs-observation conflict. A per-gt trace of
  the loop cells (`docs/world/p4-decay-trace.md`) showed the loop decaying exactly as the algebra says — one level
  per wire hop, four game ticks per round, 56 ticks from 14 to 0 — while every run had cut the regime at 40 ticks.
  The DC judge was right; what it lacked was a time clause (a settle bound), which the second reviewer had named as
  the third condition of a boundary contract. It is now in: `Bench.set_floors` / `settle_after` step the ticked
  circuit from one input vector to the next, `placer0_check` drives every ordered pair of pin vectors and
  `alu_check_contract` clause C7 sweeps the 128 rows of n=2 forward and back; a row must rest within 40 gt at its DC
  solution. Under it the decaying p4 fails exactly where the world did (T 15 -> 0, not rested at 40 gt), v9 passes with
  a worst settle of 26 gt, and the placer re-solved p4 once more without a loop (16 blocks, worst settle 8 gt), which
  `feed.py` then ran in the world: `p4_throughline_v3 / placer0 / 2/2 / 2 / 0 / 12 / 0/12 / 8..8 (0 unsettled) / 68 / 3261` (`artifacts/world/feed1/out_p4v3/`).

## 7. Measured costs

Agent time and tokens for the **closing stage only** (2026-09-07: 32/32 → synthetic world →
operator's world → feeder rig). Earlier stages are not instrumented to the same standard.

| stage | model class | wall clock | tokens |
|---|---|---|---|
| PLACE-ALU-3 (the 32/32 layout) | Fable | 12 min | 145k |
| WORLD-2 (synthetic world run) | Opus | 21 min | 187k |
| PLACER-0 (rule-driven placer pilot) | Opus | 50 min | 232k |
| WORLD-4 (five PLACER-0 solutions + two v9 slices in a synthetic world) | Opus | 46 min | 296k |
| FEED-1 (`feed.py`: the world stage as one command; built once) | Opus | 2 h 20 min | 337k |
| PLACER-1a (fragment search at pitch 11; BUDGET x3, two placer defects found) | Opus | 1 h 17 min | 290k |
| every world run after FEED-1 (13 runs, 3.6 M rcon calls, 25 min wall) | none | — | 0 |
| in-world marker investigation | Sonnet | 3.4 min | 108k |
| in-world marker fix | Opus | 35 min | 111k |
| RIG-1 (one aborted attempt + the real one) | Fable | 9 + 15.5 min | 75k + 192k |
| **total** | | **≈ 1.6 h of agent time** | **≈ 820k** |

Astra's review is not in this table: it ran outside this instrumentation, and its wall
clock and tokens were not measured. The table is therefore the cost of the deriving and
placing agents only, not of every agent that shaped the result.

Human cost over the same stage: three placement commands, filling six containers by hand,
two client restarts, and flipping levers.

---

## 8. Repository layout

```
docs/rules/        source-derived rule sheets (DC, DC v2, geometry, vertical hand-off)
docs/algebra/      the derived networks and their independent evaluators
docs/placement/    layout derivations, the 30/32 predecessor, the rig, the slice contract
docs/world/        synthetic-world and live-world records with per-cell tables
docs/report-alu-stage.md   the narrative record of the ALU stage
artifacts/layouts/ block lists and node networks (JSON)
artifacts/programs/ placement programs
artifacts/rows/    per-row truth tables and node value tables
artifacts/world/   worldprobe specs and results (measured values unchanged; run metadata redacted — PUBLICATION_CHECKLIST.md section 3), and region captures
artifacts/placer0/ the six PLACER-0 problems and the solutions the placer found
tools/placer0/     the rule-driven placer and its Bench-oracle judge
tools/world/feed.py the world stage as one command: feeder search, Bench check against the requirement, world, spec, run, table
artifacts/world/feed1/ the feed.py outputs of the runs cited above (specs, worldprobe results, tables; run metadata redacted)
artifacts/images/  layer maps and network diagrams
tools/llmgen/      the Bench (capcell) and the rule machine it runs on
tools/checks/      the sweeps, checkers and evaluators used above
tools/world/       synthetic world build, RCON probe, region capture
```

**Language convention.** Bilingual documents follow one rule: the English original is
`name.md`, the Japanese is `name.ja.md`, and each links to the other on its first lines.
That covers this README, the four rule sheets in `docs/rules/`, the slice contract, the
block-coverage table, the ALU stage report, the live-world record, and `tools/README.md`.
The result notes and world tables the agents produced — `docs/algebra/*-result.md`,
`docs/placement/*-result.md`, `docs/placement/placealu2-partial.md`,
`docs/world/world*-record.md`, `world*-tables.md`, `PUBLICATION_CHECKLIST.md` — are English
originals and carry no translation. The remaining short order notes (the questions under
`docs/algebra/` and `docs/placement/`, and `docs/alu-place-handover.md`) are the Japanese
working records as they were written and have no English counterpart. Quotations and
private material have been removed throughout, and one term was normalised (one model
instance working from a written order is called an **agent**); the numbers, coordinates,
file references and tables are unchanged, both between the two files of a pair and against
the original records.

**The name.** *Jiorimetry — 自織 (jiori, "self-weaving") + -metry.*
