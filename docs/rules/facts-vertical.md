# VERT-1 — a micro-test of the vertical hand-off (Bench only, DIRECTOR 7, 2026-09-08 19:01:51Z)

> 日本語: [facts-vertical.ja.md](facts-vertical.ja.md)

Policy (the second-model reviewer, with the operator's agreement): an unknown connection is verified in the small rather than put to the operator as a question. The Bench (a replica of the rules, calibrated on B-??) and the confirmation on real hardware are recorded separately. **This test is Bench only; the real hardware is unconfirmed.**

Shape: a pinned wire L → comparator cA (compare, back = the wire) → the solid S at its front (strongly powered = L) → **the wire directly above S** → comparator cB at y=2.

| test | reader | result (L = 0 / 3 / 5 / 9 / 15) |
|---|---|---|
| T1 | cB's back = the wire above | the wire above = L, cB's output = L (lossless, at all 5 values) |
| T2 | cB's side = the wire above, back = redstone_block (subtract) | 15 − L (0 → 15, 3 → 12, 5 → 10, 9 → 6) = exact |
| T3 | **interference**: at y=1, place P's wire (15) at (2,1,1), next to S | the wire above reads **14** (a wire at y=2 reads the wire below its horizontal neighbour when that neighbour is air = the diagonal-downward connection, −1) |

Hence the rules that can be used (Bench): (1) comparator → strongly powered solid → the wire directly above is lossless, and readable from the back as well as from the side. (2) **If the 4 cells horizontally adjacent to a wire at y=2 are air, no wire may be placed directly below it (at y=1)** (it leaks through the diagonal-downward connection). To place one anyway, block the neighbour on the y=2 side with a solid (a wire on top of a solid is not read: when the neighbour is solid it is the wire above that neighbour that is seen, so making (2,2,1) solid makes (2,3,1) the cell seen, and that is air). Put the other way round: a control line at y=2 and a data line at y=1 must either **be stacked in the same column or be separated by a solid**.
