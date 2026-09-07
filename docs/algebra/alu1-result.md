# ALU1 slice - DC derivation (final, 2026-09-07 ~17:31Z). NOT BLIND: adder03 / subtractor_03 / selector were given and read.

## 1. Encodings and operation selection
- Data a, b, k, r, f in {0,3} (as adder03; r and f come out at exactly {0,3}, so f chains into the next slice k with no conversion).
- Control: two lines. P in {0,15}: 0 = arithmetic, 15 = logic. W in {0,3}: ADD 0 / SUB 3 / AND 0 / OR 3. Pbar = torch(P) in {0,15}, derived locally.
- Three identities carry the design (all verified by the 32-row table):
  (i) r_SUB = r_ADD = parity(a,b,k) since a-b-k == a+b+k (mod 2): ONE sum path serves ADD and SUB.
  (ii) f_ADD = maj(a,b,k), f_SUB = borrow = maj(NOT a,b,k), so f = maj(a XOR W, b, k): one level-XOR on a; no b/k inversion, no carry inversion, no carry/borrow selector.
  (iii) AND = carry(a,b,0), OR = carry(a,b,1): in logic mode k is replaced by W and the existing carry comparator c4 IS the logic result.
- Selection: P (15) kills the arithmetic outputs by sitting on a spare side of c7 and F (side 15 exceeds any back level, so output 0); Pbar kills the logic leg (c4g) and the W-into-k path (Qg); P kills k (kg). Two of the four gates are free (absorbed into second sides).

## 2. Network (sub = subtract mode, cmp = compare mode; side value = max of the two sides)
| node | part | back | sides | level computed |
|---|---|---|---|---|
| nP | torch | input P (solid powered by P) | - | 15 iff P=0 |
| kg | comparator sub | k | [P] | k in arith, 0 in logic |
| Qg | comparator sub | W | [nP] | W in logic, 0 in arith |
| c1 | comparator sub | K9 | [b] | 9-b |
| c2 | comparator sub | c1 | [kg, Qg] | 9-b-kp (kp = k or W) = 9-3U |
| c3 | comparator sub | c2 | [a] | 9-3T, T = a+b+kp |
| c4 | comparator cmp | K3 | [c3] | 3 iff T>=2 (carry; AND when W=0, OR when W=3) |
| c5 | comparator sub | K9 | [c3] | 3T |
| c6 | comparator sub | c5 | [c4] | 3T-c4 |
| c7 | comparator sub | c6 | [c4, P] | 3(T mod 2) in arith; 0 in logic |
| c4g | comparator sub | c4 | [nP] | c4 in logic; 0 in arith |
| r | dust cell (max) | sources c7, c4g | - | result bit x3 |
| x1 | comparator sub | a | [W] | max(a-W,0) |
| x2 | comparator sub | W | [a] | max(W-a,0); max(x1,x2) = a XOR W, merged at the two sides of c3p |
| c3p | comparator sub | c2 | [x1, x2] | 9-3(a XOR W + b + kp) |
| F = f | comparator cmp | K3 | [c3p, P] | 3 iff (a XOR W)+b+kp >= 2 in arith; 0 in logic |
Edges: P->nP, kg.side, c7.side, F.side; nP->Qg.side, c4g.side; k->kg.back; W->Qg.back, x1.side, x2.back; b->c1.side; a->c3.side, x1.back, x2.side; K9->c1.back, c5.back; K3->c4.back, F.back; c1->c2.back; kg,Qg->c2.sides; c2->c3.back, c3p.back; c3->c4.side, c5.side; c4->c6.side, c7.side, c4g.back; c5->c6.back; c6->c7.back; c7,c4g->r; x1,x2->c3p.sides; c3p->F.side.
Constants: K9 = barrel, 988 stack-64 items (988/1728*14 = 8.005 -> floor 8 + 1 = 9); K3 = barrel, 247 items (facts example). Each barrel feeds two comparator backs from two faces.

## 3. 32-row check (alu1/alu_check.py; comparator: i==0->0, j>i->0, sub i-j, cmp i; torch 15 iff input 0; dust = max of sources)
| op | a b k | P W | c2 c3 c4 c7 c4g | x1 x2 c3p | r | f | rd fd | chk |
|---|---|---|---|---|---|---|---|---|
| ADD | 0 0 0 | 0 0 | 9 9 0 0 0 | 0 0 9 | 0 | 0 | 0 0 | PASS |
| ADD | 0 0 1 | 0 0 | 6 6 0 3 0 | 0 0 6 | 3 | 0 | 1 0 | PASS |
| ADD | 0 1 0 | 0 0 | 6 6 0 3 0 | 0 0 6 | 3 | 0 | 1 0 | PASS |
| ADD | 0 1 1 | 0 0 | 3 3 3 0 0 | 0 0 3 | 0 | 3 | 0 1 | PASS |
| ADD | 1 0 0 | 0 0 | 9 6 0 3 0 | 3 0 6 | 3 | 0 | 1 0 | PASS |
| ADD | 1 0 1 | 0 0 | 6 3 3 0 0 | 3 0 3 | 0 | 3 | 0 1 | PASS |
| ADD | 1 1 0 | 0 0 | 6 3 3 0 0 | 3 0 3 | 0 | 3 | 0 1 | PASS |
| ADD | 1 1 1 | 0 0 | 3 0 3 3 0 | 3 0 0 | 3 | 3 | 1 1 | PASS |
| SUB | 0 0 0 | 0 3 | 9 9 0 0 0 | 0 3 6 | 0 | 0 | 0 0 | PASS |
| SUB | 0 0 1 | 0 3 | 6 6 0 3 0 | 0 3 3 | 3 | 3 | 1 1 | PASS |
| SUB | 0 1 0 | 0 3 | 6 6 0 3 0 | 0 3 3 | 3 | 3 | 1 1 | PASS |
| SUB | 0 1 1 | 0 3 | 3 3 3 0 0 | 0 3 0 | 0 | 3 | 0 1 | PASS |
| SUB | 1 0 0 | 0 3 | 9 6 0 3 0 | 0 0 9 | 3 | 0 | 1 0 | PASS |
| SUB | 1 0 1 | 0 3 | 6 3 3 0 0 | 0 0 6 | 0 | 0 | 0 0 | PASS |
| SUB | 1 1 0 | 0 3 | 6 3 3 0 0 | 0 0 6 | 0 | 0 | 0 0 | PASS |
| SUB | 1 1 1 | 0 3 | 3 0 3 3 0 | 0 0 3 | 3 | 3 | 1 1 | PASS |
| AND | 0 0 0 | 15 0 | 9 9 0 0 0 | 0 0 9 | 0 | 0 | 0 0 | PASS |
| AND | 0 0 1 | 15 0 | 9 9 0 0 0 | 0 0 9 | 0 | 0 | 0 0 | PASS |
| AND | 0 1 0 | 15 0 | 6 6 0 0 0 | 0 0 6 | 0 | 0 | 0 0 | PASS |
| AND | 0 1 1 | 15 0 | 6 6 0 0 0 | 0 0 6 | 0 | 0 | 0 0 | PASS |
| AND | 1 0 0 | 15 0 | 9 6 0 0 0 | 3 0 6 | 0 | 0 | 0 0 | PASS |
| AND | 1 0 1 | 15 0 | 9 6 0 0 0 | 3 0 6 | 0 | 0 | 0 0 | PASS |
| AND | 1 1 0 | 15 0 | 6 3 3 0 3 | 3 0 3 | 3 | 0 | 1 0 | PASS |
| AND | 1 1 1 | 15 0 | 6 3 3 0 3 | 3 0 3 | 3 | 0 | 1 0 | PASS |
| OR | 0 0 0 | 15 3 | 6 6 0 0 0 | 0 3 3 | 0 | 0 | 0 0 | PASS |
| OR | 0 0 1 | 15 3 | 6 6 0 0 0 | 0 3 3 | 0 | 0 | 0 0 | PASS |
| OR | 0 1 0 | 15 3 | 3 3 3 0 3 | 0 3 0 | 3 | 0 | 1 0 | PASS |
| OR | 0 1 1 | 15 3 | 3 3 3 0 3 | 0 3 0 | 3 | 0 | 1 0 | PASS |
| OR | 1 0 0 | 15 3 | 6 3 3 0 3 | 0 0 6 | 3 | 0 | 1 0 | PASS |
| OR | 1 0 1 | 15 3 | 6 3 3 0 3 | 0 0 6 | 3 | 0 | 1 0 | PASS |
| OR | 1 1 0 | 15 3 | 3 0 3 0 3 | 0 0 3 | 3 | 0 | 1 0 | PASS |
| OR | 1 1 1 | 15 3 | 3 0 3 0 3 | 0 0 3 | 3 | 0 | 1 0 | PASS |
PASS 32 / 32

r and f are exactly {0,3} on every row. First run, no fixes needed.

## 4. Cost estimate (blocks)
| part | count | note |
|---|---|---|
| comparator | 14 | arithmetic core 9 (c1..c7, c3p, F); control 5 (kg, Qg, c4g, x1, x2) |
| barrel (constants) | 2 | K9 (988 items), K3 (247 items), each read from 2 faces |
| torch + its solid | 1+1 | Pbar |
| dust cells | ~12 | a, b, k, W entry cells (4); P run to 3 readers (~3); Pbar to 2 readers (~2); c2 / c3 / c4 fan-out cells (3); r merge cell (1). Gate->gate links are direct (front = next back, or gate at a side). |
| fan-out relief | ~2 | compare-mode copy comparators if the 4-neighbour cells in section 6 cannot be placed |
| total | ~32 | floor/support solids not counted |
Dominant: the arithmetic core (9 comparators + 2 barrels + ~5 dust, ~16 blocks, ~50%). Control (gates, XOR, torch, P/Pbar dust) ~12 blocks (~37%); it would be 4 comparators larger without the side-absorption of P into c7/F and identities (i)-(iii). A binary torch/dust alternative was judged more expensive (a torch full adder alone is 15+ torches plus solids, before SUB, AND/OR and selection); binary logic is used only where cheapest: the P inverter is one torch, and P/Pbar at {0,15} have attenuation margin for dust distribution.

## 5. Disclosure
- Reused verbatim: adder03 (c1..c7, constants 9 and 3) with ONE change: chain order b, kp, a instead of a, b, cin so c2 = 9-b-kp is shared with the flag chain; every intermediate level follows the same algebra (9 minus partial sum, never below 0).
- Not reused: net_subtractor_03 (its 8 comparators are replaced by identity (ii): its chain 6+a-b-bin is the adder chain with a replaced by 3-a, which x1/x2 + c3p + F compute with a controllable inversion); the 5-comparator selector (replaced by per-leg gating: one subtract with the complementary control on a side, two of them absorbed into spare sides of c7 and F, plus one dust merge).
- Derived new: level XOR by two mutual subtracts merged at the two sides of a comparator (x1, x2 -> c3p); kp mux via the two sides of c2 (kg, Qg); logic ops as the carry comparator (iii); output-leg gating; torch-derived Pbar.
- Control vs arithmetic: 5 of 14 comparators + 1 torch, i.e. control ~55% of the arithmetic comparator count; ~12 vs ~16 blocks.

## 6. Unresolved physical points
1. Zero-margin fan-out cells (data {0,3} cannot cross a second dust cell): a (source + x1.back + x2.side + c3.side = 4 neighbours), W (source + x1.side + x2.back + Qg.back = 4), c4 (source + c6.side + c7.side + c4g.back = 4). Geometrically 4 horizontal neighbours of one cell (two back-readers on opposite faces + side-readers): tight. Relief = compare-mode copy comparator (+1 block, level preserved). Hypothesis (not scripted): c4g could instead be cmp(K3, sides=[c3 via one extra dust cell, nP]) since c3 in {0,3,6,9} attenuated to {0,2,5,8} keeps the <=3 threshold ordering.
2. Two-sided comparators (c2, c7, c3p, F) need both side positions occupied by the named sources; c2 back must then be fed directly by the c1 front. No 3D placement done.
3. Which side carries which source is free (max is symmetric).
4. P at 15 must stay >= the back levels it kills (6 on c7, 9 on F, 3 on kg): P may attenuate to 9 (6 dust cells). Pbar must stay >= 3 at Qg and c4g (12 cells). P must power the torch solid (any level > 0).
5. Torch readable at a comparator side per facts.md line 11; the attached face gives no power, so the Qg/c4g sides must not be on that face.
6. W in {0,3} is an interface assumption (zero margin; from a 15-level lever add sub(lever, K12), K12 = 1358 items, +2 blocks). a, b, k must arrive as gate outputs or single dust cells at exactly 3.
7. r is a dust cell fed directly by the fronts of c7 and c4g; the consumer must read that cell directly.
8. Barrel item counts follow the facts formula, not measured.
Files read: alu1/facts.md, alu1/adder03.json, alu1/net_subtractor_03.json, alu1/dc_eval.py (the four given). No 1.20.6 source opened; nothing under the development repository opened. Written: alu1/draft.md, alu1/alu_check.py. Approx 45k tokens, 28 min (17:04Z-17:32Z).
