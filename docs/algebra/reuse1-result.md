# DC full subtractor, {0,3} interface — FINAL (blind derivation agent, 2026-09-08)

Relation: a - b - bin = d - 2*bout, all five signals in {0,3}, decode bit = [level >= 3].
Primitives used: sub(i,j) = max(0, i-j)  (i=back, j=max of sides); cmp(i,j) = i if i >= j else 0; i==0 -> 0. (facts.md :12)

## 1. Arithmetic idea
Let n := (not a) + b + bin, n in {0..3}. Since a - b - bin = 1 - n:
  bout = [n >= 2],   d = [n even]   (n=0: d=1,bout=0; n=1: 0,0; n=2: 1,1; n=3: 0,1).
Levels: A' = 3 - A (NOT a, one subtract). Chain from constant 9: L = 9 - A' - B - C = 9 - 3n in {9,6,3,0}.
  bout = cmp(3, L) = 3*[L <= 3] = 3*[n >= 2].
  d    = sub(L, Y),  Y = 6*[n <= 1] = cmp(6, 12 - L)   (12 - L = 3 + 3n <= 6  iff n <= 1)
        n=0: 9-6=3, n=1: 6-6=0, n=2: 3-0=3, n=3: L=0 -> 0.
Internal levels that appear: 0, 3, 6, 9, 12. (Addition is never needed: "+A" is realised as 9 - (3 - A).)

## 2. Network
| node | mode | BACK | SIDE 1 | SIDE 2 | computes |
|---|---|---|---|---|---|
| c0 | subtract | K3 (barrel lvl 3) | A | - | A' = 3 - A |
| c1 | subtract | K9 (barrel lvl 9) | c0 out | - | 9 - A' |
| c2 | subtract | c1 (gate, direct) | B | - | 9 - A' - B |
| c3 | subtract | c2 (gate, direct) | C (= bin) | - | L = 9 - 3n |
| c4 | compare  | K3' (barrel lvl 3) | L | - | bout = 3*[L <= 3] |
| c5 | subtract | K12 (barrel lvl 12) | L | - | 12 - L = 3 + 3n |
| c6 | compare  | K6 (barrel lvl 6) | c5 out | - | Y = 6*[n <= 1] |
| c7 | subtract | L | c6 out | - | d = L - Y |
No node uses its second side; every second side must be a non-emitting block (j = max of both sides, facts.md :11).

Edges: A->c0.side; K3->c0.back; c0->c1.side; K9->c1.back; c1->c2.back; B->c2.side; c2->c3.back; C->c3.side;
c3->L (fan-out node); L->c4.side; L->c5.side; L->c7.back; K3'->c4.back; c4->bout; K12->c5.back; c5->c6.side; K6->c6.back; c6->c7.side; c7->d.

Constants (barrel, 27 slots, stack-64 items; level k needs n with (k-1)/14 <= n/1728 < k/14, facts.md :16-17):
  K3 = 247 items (247/1728*14 = 2.001 -> 3; 246 gives 2), K6 = 618 (5.007 -> 6; 617 gives 5),
  K9 = 988 (8.005 -> 9; 987 gives 8), K12 = 1358 (11.002 -> 12; 1357 gives 11). No redstone blocks (15 is never needed).

## 3. 8-row check (levels at every node; d,bout decoded; relation)
| a b bin | A B C | c0=A' | c1 | c2 | c3=L | n | c4=bout | c5 | c6=Y | c7=d | bits d,bout | a-b-bin | d-2bout | result |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 0 0 | 0 0 0 | 3 | 6 | 6 | 6 | 1 | 0 | 6  | 6 | 0 | 0,0 |  0 |  0 | PASS |
| 0 0 1 | 0 0 3 | 3 | 6 | 6 | 3 | 2 | 3 | 9  | 0 | 3 | 1,1 | -1 | -1 | PASS |
| 0 1 0 | 0 3 0 | 3 | 6 | 3 | 3 | 2 | 3 | 9  | 0 | 3 | 1,1 | -1 | -1 | PASS |
| 0 1 1 | 0 3 3 | 3 | 6 | 3 | 0 | 3 | 3 | 12 | 0 | 0 | 0,1 | -2 | -2 | PASS |
| 1 0 0 | 3 0 0 | 0 | 9 | 9 | 9 | 0 | 0 | 3  | 6 | 3 | 1,0 |  1 |  1 | PASS |
| 1 0 1 | 3 0 3 | 0 | 9 | 9 | 6 | 1 | 0 | 6  | 6 | 0 | 0,0 |  0 |  0 | PASS |
| 1 1 0 | 3 3 0 | 0 | 9 | 6 | 6 | 1 | 0 | 6  | 6 | 0 | 0,0 |  0 |  0 | PASS |
| 1 1 1 | 3 3 3 | 0 | 9 | 6 | 3 | 2 | 3 | 9  | 0 | 3 | 1,1 | -1 | -1 | PASS |
Row 4 uses the i==0 -> 0 rule at c7 (back L=0). Rows 1,6,7 use cmp(6,6)=6 (j > i is false when equal). 8/8 PASS.

## 4. Unresolved physical connections (not resolved by placement here)
U1 Fan-out of L (c3 output) to three consumers: c4.side, c5.side, c7.back. A gate emits only into its front block (:13).
   Option A: c3.front = one wire block W; W read at c7.back (:24 wire readable at back) and at c4/c5 sides (:11 wire power).
   Option B: c3.front = solid S (strong-powered to L); c7.back = S (:9); a wire next to S takes L with no loss (:24); c4/c5 sides read that wire.
   Solid alone is NOT enough: sides cannot read a solid's received power (:11). Either option is a 3-consumer geometry problem.
U2 Gate output into a consumer SIDE (c0->c1, c5->c6, c6->c7, L->c4, L->c5): the source's front must be the consumer block (perpendicular gate) or a single wire block; every wire-to-wire hop costs 1 and 3->2 decodes as 0, so no path may contain two wire blocks in series.
U3 Second-side contamination: c4 (bout) has its own front; if it lands on c7's side, j = max(Y, bout) and d fails at n=2 (3-3=0). Same for any gate front touching a side; orientation must be chosen per node.
U4 Constants at backs: five barrel-backs (c0, c1, c4, c5, c6). K3 and K3' may be one barrel if both comparators can have it as their back block. Hazard: a comparator whose back is a solid reads a container one block beyond it (:10) — no node here has a solid back except Option B's c7, whose beyond-block is c3 (a gate), fine.
U5 Interface inputs at exactly 3: a lever is 15 (:28). In a chained stage bout(prev) = gate output at 3 feeds C directly (gate front or one wire); for a bench test a 15->3 conversion is needed (out of scope).
U6 Direct gate-to-gate reads c1->c2->c3 rely on :13 ("front の先の comparator は back で読める"); no wire needed.

## 5. Counts, dead ends, files
Comparators: 8 (c0..c7; 5 subtract, 3 compare). Constants: 5 barrel levels (3, 9, 3, 12, 6) -> 4 barrels if K3 is shared; 0 redstone blocks. Wire: 1 block (U1) or 1 solid + 1 wire.
Dead ends / rejected alternatives (results, with reason):
 - Ascending count x = 3n via double inversion (9-B-C, then 12-that, then -A): 4 comparators like the chain, but bout from x costs 2 (no single-comparator 3*[x>=6]); total 9.
 - NOT a by torch: 15/0 amplitude; 9-15 clips to 0 and destroys the count -> unusable in the level chain.
 - d as wire-OR of [n=0]=sub(L,6) and [n=2]=sub(L,cmp(L,6)): also 3 comparators but needs a two-source wire max merge that the fact sheet does not state; the chosen form has a single gate output.
 - d by XOR cascades over sub/NOR/AND: >= 6 comparators.
 - Hypothesis (not proven): no 2-comparator d from L exists; every one-comparator function of L is a ramp, a step, or L-gated (monotone or L/0), and d needs the non-monotone pattern {3,0,3,0}.
The fixed {0,3} encoding did not dead-end. Zero margin note: the encoding tolerates no wire attenuation (3 -> 2 = false).
Files read: scratchpad/reuse1/facts.md only. No 1.20.6 source file was opened (no unresolved point needed it). Nothing under the development repository read.
Approx: ~25 min, ~25k tokens.
