# DERIVE-2 — DC full-adder stage from comparators + constants only (final, blind seat, 2026-09-07)

## 1. Encoding
- a, b, cin, sum, cout: all in {0, 5}. Decode rule (one rule for every signal): bit = 1 iff level >= 5; level 0 = bit 0.
- Why: unit u = 5 is the largest unit with 3u <= 15, so the analog total T = a+b+cin in {0,5,10,15} never overflows,
  and one uniform alphabet lets cout feed the next stage's cin unchanged. A comparator can only SUBTRACT (i-j) or
  MAX (two sides), never add, so the total is formed as U = 15-a-b-cin (three subtractions) and T = 15-U.

## 2. Network — 7 comparators, 1 container, 2 redstone blocks
Constants: R1, R2 = redstone_block (15). K5 = barrel at container level 5 = 494 stack-64 items in 27 slots
(f = (494/64)/27 = 0.28588, floor(14f)+1 = 5; 493 items give 4). (Fact-sheet formula reproduces its own examples 1/124/247.)

| node | mode | BACK | SIDE(s) | computes |
|---|---|---|---|---|
| c1 | subtract | R1 (15) | a | 15 - a |
| c2 | subtract | c1 (gate strong power, c2 directly in front of c1) | b | 15 - a - b |
| c3 | subtract | c2 | cin | U = 15 - a - b - cin |
| c4 | compare  | K5 (container 5) | c3 = U | cout = 5 iff U <= 5 (iff T >= 10), else 0 |
| c5 | subtract | R2 (15) | c3 = U | T = 15 - U |
| c6 | subtract | c5 = T | c4 = cout | T - cout |
| c7 | subtract | c6 | c4 = cout | sum = T - 2*cout |

Edges: R1->c1.back; a->c1.side; c1.front->c2.back; b->c2.side; c2.front->c3.back; cin->c3.side;
K5->c4.back; c3.front->wire->c4.side; c3.front->wire->c5.side; R2->c5.back; c5.front->c6.back;
c4.front->wire->c6.side; c4.front->wire->c7.side; c6.front->c7.back; c4 = cout (stage output); c7 = sum (stage output).
Guard conditions (never violated on the 8 rows): no back is 0 where a nonzero output is needed
(c2.back >= 10, c3.back >= 5, c6.back = T >= 10 whenever cout = 5, c7.back >= 5 whenever cout = 5); no side exceeds its back.

## 3. 8-row check (levels; decoded bits in the last columns) — recomputed by script with the fact-sheet output rule
| a b cin | c1 | c2 | c3=U | c4=cout | c5=T | c6 | c7=sum | sum,cout bits | a+b+cin = sum+2cout | result |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 0 0 | 15 | 15 | 15 | 0 | 0  | 0  | 0 | 0,0 | 0 = 0+0 | PASS |
| 5 0 0 | 10 | 10 | 10 | 0 | 5  | 5  | 5 | 1,0 | 1 = 1+0 | PASS |
| 0 5 0 | 15 | 10 | 10 | 0 | 5  | 5  | 5 | 1,0 | 1 = 1+0 | PASS |
| 0 0 5 | 15 | 15 | 10 | 0 | 5  | 5  | 5 | 1,0 | 1 = 1+0 | PASS |
| 5 5 0 | 10 | 5  | 5  | 5 | 10 | 5  | 0 | 0,1 | 2 = 0+2 | PASS |
| 5 0 5 | 10 | 10 | 5  | 5 | 10 | 5  | 0 | 0,1 | 2 = 0+2 | PASS |
| 0 5 5 | 15 | 10 | 5  | 5 | 10 | 5  | 0 | 0,1 | 2 = 0+2 | PASS |
| 5 5 5 | 10 | 5  | 0  | 5 | 15 | 10 | 5 | 1,1 | 3 = 1+2 | PASS |
Edge cases exercised: c5 with side 0 -> 15 (row 8); c6 with back 0 -> 0 (row 1); c4 with side 0 -> 5 (row 8). 8/8 PASS.

## 4. Unresolved physical connections (listed, not placed)
1. Fan-out of c3 (U) to two SIDES (c4, c5). Source check: a side reads a wire's POWER directly regardless of wire shape
   (RedstoneView.java:53-54 via AbstractRedstoneGateBlock.java:146), and a wire in front of a gate takes the gate level
   (fact sheet). So ONE wire block in front of c3 that is adjacent to both c4's side and c5's side is lossless; if a
   second wire block is needed, U arrives as U-1 (c4 threshold still correct, but T = 15-(U-1) shifts sum to {1,6};
   fact-sheet remedy: subtract a constant 1 on a side). Geometry not resolved here.
2. Fan-out of c4 (cout) to two sides (c6, c7) AND the stage output — same wire-block adjacency question.
3. R1/R2 may be one shared redstone block (a block can back several comparators); counted as 2.
4. Inputs a, b, cin must arrive as wire or gate output at level exactly 5 (a lever gives 15; a level-5 input source,
   e.g. lever -> comparator with K5 back, is outside this derivation).
5. c2/c3/c6/c7 read their predecessor's strong power through the BACK — this is the standard in-line comparator chain
   (fact sheet: "front の先の comparator はそれを back で読める"); it requires the two gates to be collinear and co-facing.
6. No wire-merge (max on a wire) is used anywhere; all max/threshold operations happen inside comparators.

## 5. Count, files, cost
- Count: 7 comparators (6 subtract, 1 compare), 1 container (level 5), 2 redstone blocks (1 if shared). A count, not a minimum
  (exhaustive depth-2 search from {U, cout, constants} found no 2-comparator sum, so 3 after U+cout is what this seat could do).
- Files opened: scratchpad derive2/facts.md; minecraft-src/1.20.6-yarn/net/minecraft/block/AbstractRedstoneGateBlock.java
  (lines 128-149); minecraft-src/1.20.6-yarn/net/minecraft/world/RedstoneView.java (lines 40-65). Nothing under the development repository/, no web.
- Written: scratchpad derive2/check.py (recheck script), this draft.
- Approx cost: ~20 min wall, ~25k tokens.
