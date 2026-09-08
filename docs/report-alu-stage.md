# The 1-stage ALU — from zero base to your world (report, 2026-09-08)

> 日本語: [report-alu-stage.ja.md](report-alu-stage.ja.md)

DIRECTOR 8 (Fable 5.1 `0c3d10be`). The first half (DERIVE-2 → PLACE-1 → WORLD-1 → the full adder in your world, REUSE-1, ALU-1, PLACE-ALU-1/2, T6 30/32) was the work of DIRECTOR 7 (`f9d66fa1`); this document takes that over and is the record of closing 32/32 → the synthetic world → your world → the feeder rig. Non-canonical (`notes/**`). Times are UTC.

---

## 0. In one sentence

**A 1-bit ALU slice (ADD / SUB / AND / OR) was derived by a machine from nothing but a rule table written out of the Minecraft 1.20.6 source and the algebra, checked in three stages — the Bench (a replica of the rules) → a synthetic vanilla world → your world — and brought to a state where you can verify all 32 rows by hand with 5 levers.** Neither existing redstone circuits nor your own experience entered the premises of the design (§1 records what was handed over and what was not).

---

## 1. What "zero base" means (what was handed over / what was not)

| agent | kind | handed over | withheld | record |
|---|---|---|---|---|
| DERIVE-2 (the full adder algebra) | a **blind** Fable agent (zero context) | the DC rule sheet `docs/rules/facts-dc.md` (the rules for comparator / container / wire / solid, written by DIRECTOR 7 out of the 1.20.6-yarn source. **Contains no circuit shapes**) + the question | the operator's existing reference circuit (not included in this export), the web, every other file in the development repository | `docs/algebra/derive2.md`, `derive2-blind-result.md`, `net_derive2.json`, `dc_eval.py` (this agent's independent evaluator) 8/8 |
| PLACE-1 (the full adder placement) | a blind Fable agent | the placement rule sheet `docs/rules/facts-geometry.md` + DERIVE-2's network | the same | `docs/placement/place1.md` Bench 8/8 |
| REUSE-1 (full subtractor) | a blind Fable agent | a rule table **byte-identical** to DERIVE-2's (sha256 e6001fed…), with only the question swapped | the same | `docs/algebra/reuse1.md` 8/8 |
| ALU-1 (the ALU algebra) | a Fable agent, **not blind** | the rule table + the {0,3} adder network derived in this development (`given-adder03.json`) + the subtractor network + the mux suggestion from Astra | existing circuits, the source (the agent never opened it) | `docs/algebra/alu1.md`, `net_alu1.json`, `dc_eval_alu.py` 32/32 |
| PLACE-ALU-3 (the ALU placement, this document) | a Fable agent, not blind | the rule table v2 `docs/rules/facts-dc-v2.md`, the placement rule sheet, the VERT-1 rules `docs/rules/facts-vertical.md`, T6 (30/32), this agent's analysis (§3) | the operator's existing reference circuit, the web | `docs/placement/placealu3-result.md` 32/32 |
| RIG-1 (the feeder rig) | a Fable agent | the above + the feeder shape from WORLD-1/2 | the same | `docs/placement/rig1.md` 32/32 |

The substance of "zero base" is three things: **the rule tables come from the source and contain no circuit shapes**, **the first stage of the algebra came out blind**, and **every stage after that reused only what had been verified inside this development**. B-?? (your existing circuit) is a calibration point for the Bench and was never handed to an agent (the line, §8.4, `notes/2026-09-07-rebuild-line.md`).

The origin of the policy: the operator and Astra (second-model reviewer) (2026-09-08 19:01Z) set it — do not take the solutions of existing circuits or the operator's experience as premises of the design, settle things with rules and experiments, reuse of verified constructions is allowed, and an unknown connection is verified in the small rather than put to the operator as a question (`docs/alu-place-handover.md`, opening).

---

## 2. The algebra (ALU-1, `docs/algebra/alu1-result.md`)

- Data a / b / k / r / f ∈ {0, 3} (bit = level ≥ 3). Two control lines: **P ∈ {0, 15}** (0 = arithmetic, 15 = logic) and **W ∈ {0, 3}** (ADD/AND = 0, SUB/OR = 3). In the physical circuit, **Wn ∈ {0,15}** (15 = ADD/AND) is distributed instead of W and converted locally by W3 = sub(K3, [Wn]) (the source checks of PLACE-ALU-1: a torch is 0 from the side, and the side cannot read a container).
- Three identities: (i) r_SUB = r_ADD = parity(a, b, k), (ii) f = maj(a ⊕ W, b, k) (carry and borrow on one wire), (iii) AND = carry(a, b, 0), OR = carry(a, b, 1) (the logic operations *are* the carry comparator).
- The network (16 comparators + 1 torch + the constants K3 / K9):

| node | expression | meaning |
|---|---|---|
| kg | sub(k, [P]) | k, and 0 in logic |
| Qg | sub(W, [nP]) | W, and 0 in arithmetic (in logic W goes in instead of k) |
| c1 / c2 / c3 | sub(K9,[b]) / sub(c1,[kg,Qg]) / sub(c2,[a]) | 9 − 3·(a + b + k') |
| c4 | cmp(K3, [c3]) | carry (= the logic result) |
| c5 / c6 / c7 | sub(K9,[c3]) / sub(c5,[c4]) / sub(c6,[c4,P]) | r_arith = 3·[c3 ∈ {0,6}] |
| c4g / r | sub(c4,[nP]) / max(c7, c4g) | the logic r / the merge |
| x1 / x2 / c3p / F | sub(a,[W]) / sub(W,[a]) / sub(c2,[x1,x2]) / cmp(K3,[c3p,P]) | the carry/borrow that goes through a ⊕ W |

The node values for the 32 rows: `artifacts/rows/node_values.txt`. 32/32 on this agent's independent evaluator `dc_eval_alu.py`.

---

## 3. The placement (v7, `artifacts/layouts/alu_stage_v7.json`)

- **176 blocks**: comparator 23 / repeater 14 / wire 35 / barrel 6 (K3 ×4 = 247 items = level 3, K9 ×2 = 988 items = level 9) / redstone_block 1 / torch 1 / smooth_stone 96 (including the support floor at y=0). Box x 0..10, y 0..2, z 0..11. The layer map is `alu_stage_v7_layers.png` (with the rig, `artifacts/images/alu_v7_rig1_layers.png`).
- The pins (wire cells): a = (4,1,4) (8,1,5) (10,1,4), b = (0,1,4), k = (0,1,2), P = (0,1,0) (0,1,8), Wn = (4,1,10). The reads: r = the wire (6,2,9), f = the output of comparator F (8,1,2) (its front (9,1,2)).
- Structure: y=1 is the main layer (the k → f wall at z=2..3, the Qg1 cluster to the west, the XOR legs at x=6..10), y=2 is the r cluster (c4–c7, c4g, the nP torch) and the injection bridge for P. The vertical hand-off is comparator → strongly powered solid → the wire directly above (VERT-1; losslessness confirmed on the Bench, and it holds on real hardware).
- **The design changes from T6 (30/32) to v7 (32/32)** (PLACE-ALU-3, `placealu3-result.md`): the 2 failing rows are f=3 under SUB when a=1 (there is no `a` on x2's side). The cell (5,1,6) where `a` could be brought in is the support for c6 of the r cluster, and the proposal in handover §3 (move c6 to (4,2,7)) does not hold because the support (4,1,7) is the feeding repeater for Wn (this agent's analysis, `notes/2026-09-08-director-8-registrations.md`). What solved it was the algebra side:
  1. **S_x = max(a, W3), xm = sub(S_x, [as]), as = sub(a, [Wn])** (x1 / x2 turned into copies; the copy gate, W3b and one K3 removed, one `as` added).
  2. **The P kill moved from c7's side to the shared side of c5 / c6 at (5,2,5)** (15 > 9). The P line at x=9, the bridge and 3 caps disappear, and so does (8,2,7) (a wire above a comparator), which could not be placed.
  3. The dummy comparator (9,1,3): it makes the wire shape of w3p (8,1,3) N+E so that it does not leak into the relay to the south (a Bench shape rule; it holds on real hardware).
- The lint (`alu_check2.py`): L1 support (the vanilla placement conditions), L2 diagonal reads (VERT-1), L3 a wire touching a strongly powered relay (informational). v7 = L1/L2 0.

---

## 4. The three stages of checking

| stage | instrument | result | primary record |
|---|---|---|---|
| Bench | the `Bench` in `tools/llmgen/capcell.py` (a replica of the rules, calibrated on B-??), pins fixed | **32/32**, r/f land exactly on {0,3} | `artifacts/rows/alu_stage_v7.json.rows.json` |
| synthetic world (WORLD-2) | headless vanilla 1.20.6, void world, lever feeding (compare gate + barrel 247 + side wire, lever ON = bit 0), freeze/step with worldprobe, a regime of 32 warm-up + 32 real | **r/f 32/32, all reads 1024/1024** (comparator 23 + the powered state of the feeders), settle 2..14 gt, rcon 103,169 | `artifacts/world/world2.run.result.json` (untouched), `record.md` (a two-part structure in which the prediction was written first) |
| your world (LIVE-ALU) | `/aiwb place alu_stage_v7_nobarrel 6005 133 -4113` + 6 barrels (5 / 16 bows), reading the region files (regioncap) | 176/176 placed, **23/23** comparators at rest, ADD 0+0+1 → r 3 / f 0, SUB 0−0−1 → r 3 / f 3, **24/24** | `docs/world/live-alu-record.md`, 3 captures |
| the feeder rig (RIG-1) | 5 levers, composter[level=3] ×4 (no block entity), 2 lamps, 93 blocks, `/aiwb place alu_stage_v7_rig1 6001 131 -4114` | Bench 32/32 (from the lever states alone), and in the world SUB 1−0−0 → r 3 lit / f 0 dark, comparators 23/23 | `docs/placement/rig1.md`, `rig1-result.md`, a capture |

Three things the Bench hid and the world showed (all of them since confirmed in the world): the wire shape of the dummy comparator; the strongly powered relay next to a pin (as ≤ a, and with as ≤ 3 the value is unchanged); and the absence of a block update immediately after placement (a warm-up is needed = the same mechanism as WORLD-1/2).

---

## 5. Operating instructions (your world)

Origin (6005,133,−4113); y=133 is the floor, 134 the main layer, 135 the cluster.

| lever (y=135) | coordinates | ON | OFF |
|---|---|---|---|
| a | 6017 135 -4108 | a = 0 | a = 1 |
| b | 6003 135 -4108 | b = 0 | b = 1 |
| k | 6003 135 -4112 | k = 0 | k = 1 |
| P | 6001 135 -4109 | logic (AND/OR) | arithmetic (ADD/SUB) |
| Wn | 6009 135 -4102 | ADD / AND | SUB / OR |

The lamps: r = 6011 135 -4103, f = 6014 134 -4111 (lit = 1). The 10 marks (IN a×3 / b / k / P×2 / Wn, OUT r / f) now stack up (`_mark_put` in `flows.py` was made a union; ruling A of 2026-09-08). The 32-row expectation table is in `docs/placement/rig1-result.md` §4.

Example: all OFF = SUB 1−1−1 → r lit, f lit. Wn ON = ADD 1+1+1 = 3 → the same. Then k ON (k=0) = 1+1 = 2 → r dark, f lit.

---

## 6. Costs (measured, harness tokens)

| stage | agent | time | tokens |
|---|---|---|---|
| PLACE-ALU-3 | Fable | 12 min | 145k |
| WORLD-2 | Opus | 21 min | 187k |
| marker investigation | Sonnet | 3.4 min | 108k |
| marker fix | Opus | 35 min | 111k |
| RIG-1 (an aborted attempt + the real one) | Fable | 9 + 15.5 min | 75k + 192k |
| total | | ≈ 1.6 h of agent time | ≈ 820k |

Your acts: 3 placements, filling 6 barrels by hand, 2 restarts, the levers. This agent's misses: guiding you to a flag `--no-backup-gate` that does not exist in game; a `/data merge` line over 256 characters; using U+2212 in the coordinates of a table, which brought on `Expected integer` (recorded to memory); and an order whose write failed on permissions, which cost one Fable agent an aborted stage.

---

## 7. The scope of the claim, and what is not claimed

- **Claimed**: a 1-bit ALU slice, in a placement that a machine derived from the rule tables and the algebra (Bench 32/32) → the synthetic world 32/32 → your world (23/23 at rest + 3 driven states), agrees throughout and can be operated with levers. It is the second artifact after the full adder (8/8 in all three tiers).
- **Not claimed**: 8 stages; tiling (the a3 pin sticks out at x=10, so either pitch ≥ 11 or a fold-back); speed; a density comparison against an existing reference circuit (the policy is to report costs in absolute numbers); and immunity from rework under a change of specification (the 3 conditions of R0).
- There is still no record of all 32 rows having been run in your world (the feeding is by lever, so either you run them, or the rig is placed in a copy of the world and swept automatically with worldprobe = brush-up D).

---

## 8. Brush-up candidates

- **A** the 3 pin cells of `a` → 1 cell (a rework of the placement; the premise for tiling)
- **B** barrels → composters (the 4 K3 are possible; the 2 K9 are not, since a composter tops out at 8, so it needs a change of algebra that rebuilds around the constant 8)
- **C** lamps on the input side too (visible by level rather than by lever orientation)
- **D** an automatic sweep of the 32 rows with the rig included (a copy of the world + worldprobe)
- **E** the joining of a second stage (f(i) → k(i+1), passing P / Wn through) — awaiting your go

---

## 9. References

- The line (policy and history): `notes/2026-09-07-rebuild-line.md` (§8.2 OC-D110 = the foundation is signal-strength arithmetic, §8.4 the position of B-??, §8.5 the first round)
- Handover: `docs/alu-place-handover.md` (§2 the 2 failing rows, §4 the interference rules)
- Rule tables: `docs/rules/facts-dc.md`, `docs/rules/facts-dc-v2.md`, `docs/rules/facts-geometry.md`, `docs/rules/facts-vertical.md`
- Algebra: `docs/algebra/derive2.md`, `docs/algebra/reuse1.md`, `docs/algebra/alu1.md`
- Placement: `docs/placement/placealu2.md` (T6, partial), `docs/placement/placealu3-result.md` (v7, the checker, the program, the layer map)
- Worlds: `docs/world/world1-record.md`, `docs/world/world2-record.md`, `docs/world/live-alu-record.md`, `docs/placement/rig1.md`
- Registrations (chronological): `notes/2026-09-07-director-7-registrations.md`, `notes/2026-09-08-director-8-registrations.md`
- Instruments: `tools/llmgen/capcell.py` (the Bench), `tools/world/worldprobe.py` (observing a copy of the world), `tools/world/regioncap.py` (reading the region files), `tools/workbench/bridge/flows.py` (the aiwb flows, the mark fix `3ef098ad`)
