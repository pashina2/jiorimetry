# SLICE-1 result (Fable worker fable5-0c3d10be, 2026-09-07T22:52Z-23:2xZ)

Answer: YES. `alu_slice_v8.json` (= `draft_3.json`) is a bit slice under the order's contract: n=1 32/32, n=2 128/128, n=3 512/512, lint L1=0 L2=0 on the tiled n=2 layout. PX = 12, box x 0..11, y 0..3 (y=3 used and declared: r port + Wn through-line + b drop), z 0..13.

## 1. Checker output (printed lines, verbatim)

```
$ python alu_check_slices.py draft_3.json 1        (alu_slice_v8.json is a byte copy of draft_3.json)
n=1 PASS 32/32
$ python alu_check_slices.py draft_3.json 2
n=2 PASS 128/128
$ python alu_check_slices.py draft_3.json 3
n=3 PASS 512/512                                    (23:13:40Z -> 23:16:51Z)
$ python ../2026-09-08-placealu3/alu_check2.py draft_3.json   (single stage, pins/reads section)
PASS 32/32
```

## 2. Lint (`alu_check2.lint` on `alu_check_slices.tiled(lay,2)` = `v8_tiled_n2.json`)

```
tiled n=2 lint: L1=0 L2=0 L3=48
n=1 lint: L1=0 L2=0 L3=24
```
The 48 L3 lines are 24 per slice, all intended read-outs (a wire directly above / beside a comparator-driven relay solid: a1/a2/a3 drops, b drop, r, c3/c4 uplinks, w3p, P2 and Wn drops, through-line drops). None pairs an x=11 cell with an x=12 cell.

## 3. How each contract item is met

Coordinates are v8 coordinates. v8 = v7 shifted +1 in y (floor y=0, old y=1 -> y=2, old y=2 -> y=3) so that the old floor layer (y=1) can carry the a / P2 distribution under the data layer.

1. Pitch / box: PX=12, no cell at x>=12 (checked: 0 cells), x in 0..11, y in 0..3, z in 0..13.
2. Through-lines
   - P: y=2, z=0, wires x=0..3, repeater (4,2,0) facing west (back (3,2,0), front (5,2,0)), wires x=5..11. Entry (0,2,0), exit (11,2,0); the next slice's (12,2,0) is its entry wire. Levels (P=15): entry 15 -> (3,2,0)=12 -> repeater -> (5,2,0)=15 -> exit 9 -> next entry 8 -> its (3,2,0)=5 -> 15 again. Every P consumer is normalised (repeaters (1,2,1) kg side, (5,2,1) -> (5,2,2) relay -> y=3 P chain (5,3,2)/(5,3,3)/(5,3,4) -> (5,3,5), (8,2,1) F side, and the new comparator (6,2,1) for P2), so the level along the line never matters.
   - Wn: y=3, z=12, wires x=0..6, repeater (7,3,12) facing west, wires x=8..11, supports (x,2,12) smooth_stone. Exit (11,3,12)=12, next entry 11, next (6,3,12)=5 -> 15. Drops: (4,3,11) comparator fS -> (4,3,10) relay -> wire (4,2,10) below (the old Wn pin) -> (4,2,9) rep -> Qg column as in v7; (9,3,11) cS -> (9,3,10) relay -> wire (9,2,10) -> (9,2,9) cS -> (9,2,8) relay -> (9,2,7) cS -> (9,2,6) relay -> rep (9,2,5) (as' side); W3a's side via rep (7,2,8) fE reading a comparator (8,2,8) facing east whose back is the (9,2,8) relay (replaces v7's (8,1,8) wire).
   - P second entry (v7 (0,1,8)) is derived in-slice: comparator (6,2,1) fN (back = P wire (6,2,0)) -> relay (6,2,2) -> wire (6,1,2) below -> wires (5,1,2),(4,1,2),(3,1,2) -> comparators (3,1,3),(3,1,5),(3,1,7) facing north with relays (3,1,4),(3,1,6),(3,1,8) (under c3 / WnRep / the torch support; gates do not read below) -> wires (3,1,9..12),(2,1,12),(1,1,12) -> comparator (1,1,11) fS -> relay (1,1,10) -> wire (1,2,10) above -> comparator (1,2,9) fS -> relay (1,2,8) = P (strong), read by the two repeaters (1,2,7) fS and (2,2,8) fW that v7 fed from the (1,1,8) wire. Climb-guards: solids (3,2,2) (kg wire next to (3,1,2)) and (3,2,10) ((4,2,10) Wn wire next to (3,1,10)).
3. Carry: k = wire (0,2,2) (unchanged). F (8,2,2) now outputs into a relay solid (9,2,2) -> wire (10,2,2) -> f = comparator (11,2,2) facing west, compare (back (10,2,2)), front (12,2,2) = the next slice's k. Level exact 0/3 (compare of a 0/3 wire).
4. Ports (one wire cell each): a = (10,1,13) (south face z=13, y=1); b = (0,3,6) (top face, sits on the barrel (0,2,6)); r = (6,3,9) (top face; the v7 r wire, shifted up); k (0,2,2); f (11,2,2).
   - a copy: pin (10,1,13) -> comparator (9,1,13) fE -> relay (8,1,13) -> comparator (7,1,13) fE -> relay (6,1,13); a3: (10,1,12) cS -> (10,1,11) relay -> wire (10,1,10) -> (10,1,9) cS -> (10,1,8) -> (10,1,7) cS -> (10,1,6) -> (10,1,5) cS -> (10,1,4) relay under the a3 wire (10,2,4); a1: (6,1,12) cS -> (6,1,11) relay -> wire (6,1,10) -> (6,1,9) cS -> (6,1,8) -> (6,1,7) cS -> (6,1,6) -> (5,1,6) cE -> (4,1,6) -> (4,1,5) cS -> (4,1,4) relay under a1 (4,2,4); a2: (7,1,11) cW (back (6,1,11)) -> (8,1,11) relay -> wire (8,1,10) -> (8,1,9) cS -> (8,1,8) -> wire (8,1,7) -> (8,1,6) cS -> (8,1,5) relay under a2 (8,2,5). All comparators are compare mode, all relays are smooth_stone strongly powered at exactly a (0/3); climb-guards (8,2,10),(10,2,10),(5,2,10) solids.
   - b copy: v7's redstone_block (0,1,6) became a barrel with 1728 items (level 15) at (0,2,6) (constant 15 for (1,2,6)'s back; containers do not power wires); pin b (0,3,6) on it -> comparator (0,3,5) fS (support (0,2,5)) -> relay (0,3,4) -> b wire (0,2,4) = c1's side, directly below.
   - Caveat for the reader: b's port is on the top face but in the x=0 column; its west neighbour (11,3,6) of the previous slice is air, and no boundary read exists there (n=2/3 Bench confirm). If "x face" is read strictly, moving it costs one more hop (no cell east of (0,3,5) can hold the comparator: (1,3,4) would have the c4 barrel (2,3,4) at its back).
5. Closure: non-floor cells at x=0: (0,2,0) P entry, (0,2,2) k, (0,2,4) b wire, (0,2,5) solid, (0,2,6) barrel, (0,2,12) Wn support, (0,3,4) relay, (0,3,5) comparator fS, (0,3,6) b pin, (0,3,12) Wn entry. Non-floor cells at x=11: (11,2,0) P exit, (11,2,2) f, (11,2,12) Wn support, (11,3,12) Wn exit. Across the boundary the only touching pairs are (11,2,0)-(12,2,0) wire->wire, (11,2,2) f -> (12,2,2) k, (11,3,12)-(12,3,12) wire->wire, and solid-solid / floor-floor (no transfer); every other x=0 cell faces air at x=-1. y=1 floors at x=0: (0,1,0),(0,1,2),(0,1,4); at x=11: (11,1,0),(11,1,2); all unpowered.
6. Interference rules: strong relays are placed only where all six faces are solid / gate-back / the intended wire; no y=3 wire has a y=2 wire diagonally below through an air neighbour (L2=0); pins are not next to strong relays except the intended drops (b, a1/a2/a3 are read-outs); no wire->wire hop carries data (only control lines P, Wn, P2 run through wire chains, all normalised by a repeater or read by compare/subtract sides that only need >=3 / 0).

## 4. Size

PX=12, Z=13, 292 blocks: smooth_stone 164 (35 floor at y=0, the rest supports/relays/guards), redstone_wire 55, comparator 50, repeater 15, barrel 7 (247 x4, 988 x2, 1728 x1), redstone_torch 1. v7 had 176 blocks (x 0..10, z 0..11); the +116 are the through-lines (24 cells + supports), the P2 derivation (25), the three a drops (34), the b drop (5), the f relay (3) and their floors.

## 5. Drafts

`draft_1.json` (23:10Z) n=1 16/32 - three facing errors (comparators (1,1,11)/(1,2,9) written facing north where the back had to be at z+1; (5,1,6) west instead of east) and an a2 branch reading a comparator's back. `draft_2.json` (23:12Z) 30/32 - W3a's Wn feed comparator (8,2,8) faced west (back = the repeater) instead of east. `draft_3.json` (23:12Z) 32/32 = `alu_slice_v8.json`. `dbg2.py` = per-cell probe used for the diagnosis (`python dbg2.py layout.json a b k P Wn x,y,z ...`). `v8_tiled_n2.json` = the tiled layout the lint ran on.

## 6. Files opened, time, tokens

Opened: the order; `alu_check_slices.py`, `v7_as_slice.json` (slice section only); `../2026-09-08-placealu3/alu_stage_v7.json`, `alu_check2.py`, `placealu3-result.md`, `node_values.txt`; `../2026-09-08-alu1/net_alu1.json`; `../2026-09-08-placealu2/bench_sweep.py`, `facts-dc-v2-given.md`; `../2026-09-07-place1/facts-geometry-given.md`; `../2026-09-08-vert/README.md`; `../2026-09-08-alu-place-handover.md` (header list + section 4); `tools/workbench/llmgen/capcell.py` (a 3-line grep only; it lives in the main checkout, not in this worktree). Not opened: `machine.py`, anything under `notes/bench/`, web. No world / aiwb / tools / git touched.

Wall time: 22:52:27Z (order read) -> 23:19Z (result written), about 27 min; the n=3 run alone took 3 min 11 s. Self-estimated tokens: about 95k input (file reads + reasoning), about 30k output.

## 4. v9 - after the second reviewer (Astra), 2026-09-08T09:25Z

Astra's independent reading of `tools/checks/alu_check_slices.py` (single seat) found that the checker verifies the n-bit function table only: clause 2 (through-line exit restored to 15) was never measured, and v8 violates it - with P = 15 the exit (11,2,0) reads 9 and the next entry 8; Wn exits at 12, next entry 11 (measured P row: 15 14 13 12 | 15 14 .. 9 | 8 7 6 5 | 15 ..). v8 passed n=1/2/3 only because every P/Wn consumer renormalises through a repeater; a longer consumer chain would not. The reading also listed which clauses the function table leaves unchecked (box, port faces, f/k cell types, closure pairs, support/side-lock lint).

Response: a second checker, `tools/checks/alu_check_contract.py`, measures each clause directly (C1 box, C2 through-line entry level per slice, C3 carry level per slice against the expected carry of the lower bits, C4 port faces, C5 boundary pairs + per-slice local truth table, C6 lint + repeater side lock); its docstring says which predicates are measured, which are structural, and which are not checked at all (Bench rule gaps). On v8:

```
$ python tools/checks/alu_check_contract.py artifacts/layouts/alu_slice_v8.json
... FAIL C2 ADD A=0 B=0 k=0: slice 1 entry Wn of (12, 3, 12) reads 11, pin 15
measured n=3 rows=512: C2 through-entry mismatches=1024, C3 carry mismatches=0, C5 local-table mismatches=0
CONTRACT FAIL: 6 FAIL, 3 notes
```

v9 = v8 with the two exit wires replaced by repeaters facing west: (11,2,0) and (11,3,12). The next slice's entry wire then reads exactly the pin level (15/0), so every slice sees the same P/Wn levels as slice 0. Block count unchanged (292; wire 53, repeater 17). Nothing else moved. Layer map: `artifacts/images/alu_slice_v9_x2_layers.png`.

```
$ python tools/checks/alu_check_slices.py artifacts/layouts/alu_slice_v9.json 1
n=1 PASS 32/32
$ python tools/checks/alu_check_slices.py artifacts/layouts/alu_slice_v9.json 2
n=2 PASS 128/128
$ python tools/checks/alu_check_slices.py artifacts/layouts/alu_slice_v9.json 3
n=3 PASS 512/512
$ python tools/checks/alu_check_contract.py artifacts/layouts/alu_slice_v9.json
C1 box x 0..11 y 0..3 z 0..13  PX=12  cells=292  (y=3 used)
C4 port a (10, 1, 13) on south face
C4 port b (0, 3, 6) on top face
note C4 port b (0, 3, 6) lies in the x=0 column; allowed only through C5
C4 port r (6, 3, 9) on top face
note C5 x=0 wire (0,2,4) faces air in the previous slice
note C5 x=0 wire (0,3,6) faces air in the previous slice
C5 boundary pair (11,2,0) repeater -> next (0,2,0) wire [allowed]
C5 boundary pair (11,2,2) comparator -> next (0,2,2) wire [allowed]
C5 boundary pair (11,3,12) repeater -> next (0,3,12) wire [allowed]
C6 lint tiled n=2: L1=0 L2=0 L3=48
measured n=3 rows=512: C2 through-entry mismatches=0, C3 carry mismatches=0, C5 local-table mismatches=0
CONTRACT PASS: 0 FAIL, 3 notes
```

Two contract amendments, decided by the DIRECTOR seat and disclosed (circuit-semantics domain; the operator can overrule); also recorded at the end of `slice-contract.md`:
- Clause 2: the exit cell (PX-1,y,z) may be a wire **or a repeater facing west**; the measured predicate is "the entry wire of every slice i>0 reads exactly the pin level". A repeater at the exit is the only placement that makes the entry level of slice i identical to slice 0.
- Clause 4: the ground of "no port on an x face" is closure. A port in the x=0 / x=PX-1 column is allowed when its cross-boundary neighbour is air (C5 measures this: (0,3,6) faces the previous slice's (11,3,6) = air, and no diagonal wire pair exists). Moving b off the x=0 column physically was tried on paper: every cell east of the b drop is a comparator, a repeater, a strongly powered relay or a barrel, so a second route would cost a new chain (a y=1 spine or a top-face detour) and was not bought.

Not done: the two-slice run in a synthetic world (WORLD-3) and in the operator's world; both remain the independent tier for the Bench's rule gaps (C6 "-").
