# JioΣetry

> 日本語: [README.ja.md](README.ja.md)

*Jiorimetry — 自織 (jiori, "self-weaving") + -metry.*

An experimental toolchain that **derives** Minecraft 1.20.6 redstone circuits from rule
sheets written out of the game source, rather than transcribing circuits a human already
knows. The rules it starts from are the DC signal-strength rules: comparators, containers,
dust attenuation, strongly-powered solids. The result is checked three times — on a Bench
(a replica of the rules), then in a synthetic vanilla world, then in a real world the
operator plays in.

Two artifacts exist so far:

| artifact | Bench | synthetic vanilla world | operator's world |
|---|---|---|---|
| 1-bit full adder | 8/8 | 8/8, all reads matched | placed and read, 8/8 |
| 1-bit ALU slice (ADD / SUB / AND / OR) | 32/32 | 32/32, 1024/1024 reads | placed, 23/23 static comparators, driven by a 5-lever rig with two lamps |

---

## 1. What the method actually is

1. **A rule sheet.** A human-readable table of DC behaviour, written by reading the
   decompiled 1.20.6 source and citing line numbers — `ComparatorBlock`, `ComposterBlock`,
   `RedstoneTorchBlock`, `RedstoneWireBlock`, and the solidity predicates. The sheet
   contains **no circuit shapes**. It is in [`docs/rules/`](docs/rules).
2. **Algebra.** A model seat is given the rule sheet and a question ("build a full adder
   out of these parts") and returns a *network* of comparator/torch/constant nodes with an
   explicit level encoding — not a layout. Verified by an independent evaluator written
   separately from the network. See [`docs/algebra/`](docs/algebra).
3. **Placement.** A second seat is given a geometry rule sheet (adjacency, dust shapes,
   diagonal reads, vertical hand-off) and the network, and returns coordinates. See
   [`docs/placement/`](docs/placement).
4. **Bench.** `tools/llmgen/capcell.py` is a re-implementation of the DC rules that solves
   a block list to a fixed point. It is calibrated against a pre-existing reference circuit
   the seats never see. Running the layout through it costs nothing and takes a second.
5. **Synthetic world.** The layout is written into region files of a fresh void 1.20.6
   world with physical feeders instead of pinned inputs, a headless server ticks it, and
   every dust and comparator is read back over RCON with freeze/step. See
   [`docs/world/`](docs/world).
6. **The operator's world.** The same block list is placed in a live save and read back
   out of the region files.

The Bench is the cheap oracle; the synthetic world is the honest one; the operator's world
is the one that counts.

---

## 2. Results

### 1-bit full adder (PLACE-1 / WORLD-1)

Level encoding {0, 5}. Seven comparators. The algebra was produced by a seat with **zero
project context** — it was given only the DC rule sheet and the question.

- Bench: `ALL PASS` over all 8 input vectors — [`docs/placement/place1-bench-output.txt`](docs/placement/place1-bench-output.txt)
- Synthetic world: 8/8, every read matched the Bench prediction, settle 2–10 game ticks —
  [`docs/world/world1-tables.md`](docs/world/world1-tables.md), raw
  [`artifacts/world/world1.run.result.json`](artifacts/world/world1.run.result.json)
- Operator's world: placed and read back, 8/8.

### 1-bit ALU slice (`alu_stage_v7`)

Data lines carry {0, 3}. Two control lines: `P` ∈ {0, 15} selects arithmetic vs. logic,
`Wn` ∈ {0, 15} selects ADD/AND vs. SUB/OR. Three identities do the work:

- `r_SUB = r_ADD = parity(a, b, k)`
- `f = maj(a ⊕ W, b, k)` — carry and borrow on one wire
- `AND = carry(a, b, 0)`, `OR = carry(a, b, 1)` — the logic ops *are* the carry comparator

176 blocks: 23 comparators, 14 repeaters, 35 dust, 6 containers (four level-3 constants,
two level-9), 1 redstone block, 1 torch, 96 smooth stone. Box 11 × 3 × 12.

- Bench: `PASS 32/32`, `r` and `f` land on exactly {0, 3} —
  [`artifacts/rows/alu_stage_v7.json.rows.json`](artifacts/rows/alu_stage_v7.json.rows.json)
- Synthetic world: **32/32 rows, 1024/1024 individual cell reads matched**, settle 2–14 gt —
  [`docs/world/world2-record.md`](docs/world/world2-record.md), raw
  [`artifacts/world/world2.run.result.json`](artifacts/world/world2.run.result.json)
- Operator's world: 176/176 blocks placed, 23/23 static comparators matched, and three
  driven states read out of the region files —
  [`docs/world/live-alu-record.md`](docs/world/live-alu-record.md)
- A 93-block feeder rig (5 levers, 4 composter constants, 2 lamps) makes all 32 rows
  operable by hand — [`docs/placement/rig1-result.md`](docs/placement/rig1-result.md)

---

### Update (2026-09-08, later the same day): a bit slice that abuts

The stage v7 above is a working 1-bit stage but not a bit slice: its `a` input needed three cells (one outside the pitch), the second `P` entry and the `Wn` row were not through-lines, and its east edge was not closed. The operator ruled that bit-slice abutment and pitch alignment had to be met before any second stage. A slice contract was written (`docs/placement/slice-contract.md`) and an n-slice checker (`tools/checks/alu_check_slices.py`) that tiles a layout by its pitch and solves the n-bit ALU function for all inputs and modes. Result `artifacts/layouts/alu_slice_v8.json` (pitch 12, box 12x4x14, 292 blocks: comparator 50, repeater 15, wire 55, barrel 7): n=1 32/32, n=2 128/128, n=3 512/512, placement lint 0 on the tiled layout. Details and the boundary cell list: `docs/placement/slice1-result.md`; two-slice layer map: `artifacts/images/alu_slice_v8_x2_layers.png`. Not yet done: the two-slice run in a synthetic world and in the operator's world.


## 3. What is **not** claimed

- **It is not a bit slice yet.** The operator assessed the bit-slice work — abutment of
  neighbouring slices and pitch alignment — as not met, and ruled that it must be met
  before a second stage is attempted. `v7` works as one stage; it is not a slice. A formal
  slice contract (pitch ≤ 12 in +x, through-lines restored to 15 inside each slice, carry
  hand-off exactly 0/3, ports on the south or top face only, and closure under tiling) is
  written down in [`docs/placement/slice-contract.md`](docs/placement/slice-contract.md),
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

## 4. Provenance (what each seat was given)

| stage | seat | given | withheld |
|---|---|---|---|
| DERIVE-2 (adder algebra) | blind, zero context | DC rule sheet + the question | the reference circuit, the web, every other file |
| PLACE-1 (adder placement) | blind | geometry rule sheet + DERIVE-2's network | same |
| REUSE-1 (full subtractor) | blind | a **byte-identical** rule sheet (sha256 `e6001fed…`), only the question swapped | same |
| ALU-1 (ALU algebra) | not blind | rule sheet + the {0,3} adder and subtractor networks derived above + a mux suggestion from Astra (second-model reviewer) | the reference circuit; the source was not opened |
| PLACE-ALU-3 (ALU placement) | not blind | rule sheets v2 + the failing 30/32 predecessor + this session's analysis | the reference circuit, the web |
| RIG-1 (feeder) | not blind | the above + the synthetic-world feeder shape | same |

The operator's own pre-existing reference circuit was used **only** to calibrate the Bench.
It was never shown to any seat that produced a design.

---

## 5. Reproduction

Python 3.11+, standard library only. No packages to install for the Bench path.

```
git clone <this repo> && cd jiorimetry
```

### Bench — the ALU slice, 32 rows

```
$ python tools/checks/alu_check2.py artifacts/layouts/alu_stage_v7.json
LINT L3 wire touches strongly-powered relay (5, 2, 7) relay (4, 2, 7) driven by (3, 2, 7)
LINT L3 wire touches strongly-powered relay (8, 1, 3) relay (7, 1, 3) driven by (6, 1, 3)
LINT L3 wire touches strongly-powered relay (8, 1, 3) relay (8, 1, 4) driven by (9, 1, 4)
LINT L3 wire touches strongly-powered relay (6, 2, 9) relay (5, 2, 9) driven by (5, 2, 8)
LINT L3 wire touches strongly-powered relay (6, 2, 9) relay (6, 2, 8) driven by (6, 2, 7)
LINT L3 wire touches strongly-powered relay (2, 2, 7) relay (2, 2, 6) driven by (2, 2, 5)
LINT L3 wire touches strongly-powered relay (8, 1, 5) relay (8, 1, 4) driven by (9, 1, 4)
LINT L3 wire touches strongly-powered relay (5, 2, 2) relay (5, 1, 2) driven by (5, 1, 1)
LINT L3 wire touches strongly-powered relay (3, 2, 5) relay (3, 1, 5) driven by (3, 1, 4)
PASS 32/32
```

`L1` (vanilla placement support) and `L2` (diagonal dust reads) are hard lints and are 0.
`L3` is informational.

### Bench — the full adder, 8 rows

```
$ python tools/checks/bench_sweep.py artifacts/layouts/layout_place1.json
(0, 0, 0, 'sum', 0, 'cout', 0, 'dec', 0, 0, 'rounds', 3, True, True)
(0, 0, 1, 'sum', 5, 'cout', 0, 'dec', 1, 0, 'rounds', 4, True, True)
(0, 1, 0, 'sum', 5, 'cout', 0, 'dec', 1, 0, 'rounds', 4, True, True)
(0, 1, 1, 'sum', 0, 'cout', 5, 'dec', 0, 1, 'rounds', 3, True, True)
(1, 0, 0, 'sum', 5, 'cout', 0, 'dec', 1, 0, 'rounds', 4, True, True)
(1, 0, 1, 'sum', 0, 'cout', 5, 'dec', 0, 1, 'rounds', 3, True, True)
(1, 1, 0, 'sum', 0, 'cout', 5, 'dec', 0, 1, 'rounds', 3, True, True)
(1, 1, 1, 'sum', 5, 'cout', 5, 'dec', 1, 1, 'rounds', 3, True, True)
ALL PASS
```

### The documented negative — `v7` read as a slice

This is expected to **fail**. It is the measurement that keeps the slice claim honest.

```
$ python tools/checks/alu_check_slices.py artifacts/layouts/v7_as_slice.json 1
FAIL OR A 1 B 0 k 0 r [0] f 0 conv True
FAIL OR A 1 B 0 k 1 r [0] f 0 conv True
n=1 PASS 20/32
```

(Twelve rows fail; the two shown are the last of them. At `n=2` the same layout scores
38/128.)

### Algebra evaluators (independent of the Bench)

```
$ python tools/checks/dc_eval.py     artifacts/layouts/net_derive2.json   # ALL PASS
$ python tools/checks/dc_eval_sub.py artifacts/layouts/net_reuse1.json    # ALL PASS
$ python tools/checks/dc_eval_alu.py artifacts/layouts/net_alu1.json      # PASS 32/32
```

### The 30/32 predecessor, and the rig

```
$ python tools/checks/check_alu_stage.py artifacts/layouts/alu_stage_T6_30of32.json
FAIL SUB (1, 0, 1) r 0 f 3 conv True
FAIL SUB (1, 1, 0) r 0 f 3 conv True
PASS 30/32

$ python tools/checks/alu_check2.py artifacts/layouts/rig1_full_bench.json
PASS 32/32
```

The rig sweep drives the circuit from **lever states only** — no pinned inputs — and
reproduces the pinned rows exactly.

### Unit tests

The Bench and its strength model carry unit tests; they were copied with it.

```
$ cd tools/llmgen && python -m unittest test_capcell test_strength
.......s....s............s........
----------------------------------------------------------------------
Ran 34 tests in 16.768s

OK (skipped=3)
```

(The three skips are fixture-dependent tests whose fixtures are not part of this export.)

### Layout regeneration

`tools/world/make_layout_world1.py` and `make_layout_world2.py` regenerate
`artifacts/layouts/layout_world1.json` and `layout_world2.json` from the stage layouts.
Both reproduce the committed files byte-for-byte.

### World stages (requires software you must supply)

`tools/world/` drives a real server. It is included for completeness; it will not run out of
the box. See [`tools/README.md`](tools/README.md) for what you must supply (a Minecraft
1.20.6 server jar, a Java 21 runtime, an RCON-enabled server directory). No jar, save, or
mod is distributed here.

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
  See [`docs/placement/placealu3-result.md`](docs/placement/placealu3-result.md).
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

## 7. Measured costs

Seat time and tokens for the **closing stage only** (2026-09-08: 32/32 → synthetic world →
operator's world → feeder rig). Earlier stages are not instrumented to the same standard.

| shipment | seat class | wall clock | tokens |
|---|---|---|---|
| PLACE-ALU-3 (the 32/32 layout) | Fable | 12 min | 145k |
| WORLD-2 (synthetic world run) | Opus | 21 min | 187k |
| in-world marker investigation | Sonnet | 3.4 min | 108k |
| in-world marker fix | Opus | 35 min | 111k |
| RIG-1 (one aborted attempt + the real one) | Fable | 9 + 15.5 min | 75k + 192k |
| **total** | | **≈ 1.6 h of seat time** | **≈ 820k** |

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
artifacts/world/   untouched worldprobe specs and results, and region captures
artifacts/images/  layer maps and network diagrams
tools/llmgen/      the Bench (capcell) and the rule machine it runs on
tools/checks/      the sweeps, checkers and evaluators used above
tools/world/       synthetic world build, RCON probe, region capture
```

**Language convention.** Bilingual documents follow one rule: the English original is
`name.md`, the Japanese is `name.ja.md`, and each links to the other on its first lines.
That covers this README, the four rule sheets in `docs/rules/`, the slice contract, the
block-coverage table, the ALU stage report, the live-world record, and `tools/README.md`.
The result notes and world tables the seats produced — `docs/algebra/*-result.md`,
`docs/placement/*-result.md`, `docs/placement/placealu2-partial.md`,
`docs/world/world*-record.md`, `world*-tables.md`, `PUBLICATION_CHECKLIST.md` — are English
originals and carry no translation. The remaining short order notes (the questions under
`docs/algebra/` and `docs/placement/`, and `docs/alu-place-handover.md`) are the Japanese
working records as they were written and have no English counterpart. Quotations and
private material have been removed throughout; the numbers, coordinates, file references
and tables are unchanged, both between the two files of a pair and against the original
records.

---

## 9. Credits

- **Astra** — second-model reviewer (design critique of the orders, independent re-checks of the derived networks, the 2,990-case mux check, and the review that reshaped the placement and the algorithmisation proposal).
- **pashina** — operator: circuit semantics rulings, in-world verification, and the
  reference circuit used to calibrate the Bench.
- Derivations, placements and tooling by LLM seats (Claude Fable 5.1 / Opus 5) under the
  operator's direction.

MIT licensed — see [LICENSE](LICENSE).

Not affiliated with Mojang or Microsoft. Minecraft is a trademark of Mojang Studios. No
game code, jar, world save, or mod is distributed in this repository.

---

---
