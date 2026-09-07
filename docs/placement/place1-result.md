# PLACE-1 - DC full-adder stage (net.json, 7 comparators) as a concrete block structure
Blind seat, 2026-09-07. Single working layer y=1, supports y=0. DC only, no timing.

Axes: +x = east, -x = west, +z = south, -z = north, +y = up.
FACING convention (verified: AbstractRedstoneGateBlock.java:131-133, pos.offset(FACING) is the input):
facing=D means the BACK (input) cell is pos+D and the OUTPUT cell is pos-D. Sides = pos +/- the perpendicular.
powered is derived by the game; omitted. Mode strings: compare / subtract.

## 1. Block list (x, y, z, block)
| x | y | z | block | role |
|---|---|---|---|---|
| 0 | 1 | 1 | redstone_block | R1 (15, back of c1) |
| 1 | 1 | 1 | comparator[facing=west,mode=subtract] | c1 |
| 2 | 1 | 1 | comparator[facing=west,mode=subtract] | c2 |
| 3 | 1 | 1 | comparator[facing=west,mode=subtract] | c3 |
| 4 | 1 | 1 | smooth_stone | S_U relay: strongly powered = U by c3 |
| 1 | 1 | 0 | redstone_wire | INPUT a |
| 3 | 1 | 0 | redstone_wire | INPUT cin |
| 2 | 1 | 2 | redstone_wire | INPUT b |
| 4 | 1 | 2 | redstone_wire | Wu1 = U (lossless from S_U) |
| 5 | 1 | 1 | redstone_wire | Wu2 = U (lossless from S_U) |
| 3 | 1 | 3 | barrel (494 stack-64 items: 7x64 + 46, level 5) | K5 (back of c4) |
| 4 | 1 | 3 | comparator[facing=west,mode=compare] | c4 |
| 5 | 1 | 3 | redstone_wire | W_C = cout, OUTPUT cout |
| 6 | 1 | 0 | redstone_block | R2 (15, back of c5) |
| 6 | 1 | 1 | comparator[facing=north,mode=subtract] | c5 |
| 6 | 1 | 2 | smooth_stone | S5 relay: strongly powered = T by c5 |
| 6 | 1 | 3 | comparator[facing=north,mode=subtract] | c6 |
| 6 | 1 | 4 | smooth_stone | S6 relay: strongly powered = T-cout by c6 |
| 5 | 1 | 4 | comparator[facing=east,mode=subtract] | c7 |
| 4 | 1 | 4 | smooth_stone | S_sum: strongly powered = sum by c7, OUTPUT sum |
| 1 | 0 | 1 | smooth_stone | support c1 |
| 2 | 0 | 1 | smooth_stone | support c2 |
| 3 | 0 | 1 | smooth_stone | support c3 |
| 4 | 0 | 3 | smooth_stone | support c4 |
| 6 | 0 | 1 | smooth_stone | support c5 |
| 6 | 0 | 3 | smooth_stone | support c6 |
| 5 | 0 | 4 | smooth_stone | support c7 |
| 1 | 0 | 0 | smooth_stone | support a |
| 2 | 0 | 2 | smooth_stone | support b |
| 3 | 0 | 0 | smooth_stone | support cin |
| 4 | 0 | 2 | smooth_stone | support Wu1 |
| 5 | 0 | 1 | smooth_stone | support Wu2 |
| 5 | 0 | 3 | smooth_stone | support W_C |

Optional (+2): sum readout wire at (3,1,4) redstone_wire (lossless from S_sum; the barrel at (3,1,3) is inert to it) + support (3,0,4).

MUST STAY AIR (y=1 unless noted): (0,1,0) (0,1,2) (2,1,0) (1,1,2) (3,1,2) (4,1,0) (5,1,0) (5,1,2) (7,1,1) (7,1,3) (5,1,5) (4,1,5) (3,1,4 unless readout) (7,1,2) (7,1,4) (6,1,5); the whole y=2 layer above the structure (no wire on top of S_U / S5 / S6 / S_sum / supports).
Reasons: (5,1,2) would take T from S5 and couple Wu1/Wu2/W_C; (4,1,0) would take U from S_U and couple cin; (0,1,0)/(5,1,0) would take 15 from R1/R2; (2,1,0),(1,1,2),(3,1,2),(7,1,1),(7,1,3),(5,1,5) are the unused SIDE cells of c2,c1,c3,c5,c6,c7; (4,1,4)=S_sum is the unused side of c4 (solid: a side reads 0).

Layer y=1 map (z rows north to south, x 0..7; . = air):
z=0:  .   a   .   cin  .     .    R2  .
z=1:  R1  c1  c2  c3   S_U   Wu2  c5  .
z=2:  .   .   b   .    Wu1   .    S5  .
z=3:  .   .   .   K5   c4    W_C  c6  .
z=4:  .   .   .   (rd) S_sum c7   S6  .

## 2. Comparators
| node | pos | facing | mode | BACK cell / mechanism | SIDE(-) | SIDE(+) | output cell |
|---|---|---|---|---|---|---|---|
| c1 | (1,1,1) | west | subtract | (0,1,1) R1 redstone_block gives 15 | (1,1,0) wire a | (1,1,2) air 0 | (2,1,1) = c2 back |
| c2 | (2,1,1) | west | subtract | (1,1,1) c1 gate output (FACING == query dir, AbstractRedstoneGateBlock:85-86) | (2,1,0) air 0 | (2,1,2) wire b | (3,1,1) = c3 back |
| c3 | (3,1,1) | west | subtract | (2,1,1) c2 gate output | (3,1,0) wire cin | (3,1,2) air 0 | (4,1,1) S_U solid, strong = U |
| c4 | (4,1,3) | west | compare | (3,1,3) barrel K5 gives 5 (hasComparatorOutput override, ComparatorBlock:108) | (4,1,2) wire Wu1 = U | (4,1,4) S_sum solid reads 0 (a side cannot read solids) | (5,1,3) wire W_C = cout |
| c5 | (6,1,1) | north | subtract | (6,1,0) R2 gives 15 | (5,1,1) wire Wu2 = U | (7,1,1) air 0 | (6,1,2) S5 solid, strong = T |
| c6 | (6,1,3) | north | subtract | (6,1,2) S5: received strong power = c5 output (c5 FACING north == query dir) | (5,1,3) wire W_C = cout | (7,1,3) air 0 | (6,1,4) S6 solid, strong = T-cout |
| c7 | (5,1,4) | east | subtract | (6,1,4) S6: received strong = c6 output | (5,1,3) wire W_C = cout | (5,1,5) air 0 | (4,1,4) S_sum solid, strong = sum |

Undiminished fan-out: S_U (4,1,1) is strongly powered by c3 only (while a wire computes its level, wires give no power: wiresGivePower=false, RedstoneWireBlock:252 and :344); Wu1 and Wu2 each receive U losslessly (a solid emits its received strong power to an adjacent wire). W_C (5,1,3) is the front of c4 (gate to wire, lossless) and is the SIDE cell of both c6 and c7 (c7 is turned 90 degrees via relay S6 so one wire cell touches both sides). No wire-to-wire hop anywhere; all six wires are isolated (no two wires adjacent, no step-diagonal wires, y=2 empty).
Relay purity: S5 neighbours = c5 (source), c6 (facing away, 0), air above/below/east; S6 = c6 (source), c7 (facing away, 0), air; S_U = c3 (source), Wu1/Wu2 (never read by any back), air. No gate BACK is adjacent to a wire-touched solid (RedstoneWireBlock:359 hazard: a wire strongly powers its support and any solid it connects into, from the point of view of a gate back), and redstone blocks never strongly power solids (RedstoneBlock overrides weak power only, line 32).

## 3. Inputs / outputs
Inputs (wire cells, harness pins 0 or 5): a = (1,1,0); b = (2,1,2); cin = (3,1,0). Each touches exactly one comparator (its SIDE) and three air cells. If the harness pins by a physical feed instead of a state write, the free feed cells are: a from (1,1,-1), cin from (3,1,-1), b from (2,1,3) (e.g. a comparator facing away from the input wire with a level-5 back); (2,1,-1) must stay air; a feed gate at (2,1,3) sees the barrel on one side (reads 0).
Outputs: cout = wire W_C (5,1,3), read its POWER. sum = S_sum (4,1,4), read the received strong power of the solid (getReceivedStrongRedstonePower); or place the optional readout wire at (3,1,4) and read its POWER (lossless).

## 4. Counts
comparators 7 (6 subtract, 1 compare) | barrels 1 | redstone_blocks 2 | wire cells 6 (3 inputs + Wu1 + Wu2 + W_C) | solid relays 4 (S_U, S5, S6, S_sum) | supports 13 (7 gates + 6 wires) | TOTAL 33 (35 with the optional sum readout wire + its support).

## 5. Bounding box / tiling
Bounding box x 0..6, y 0..1, z 0..4 = 7 x 2 x 5 (feed cells for a/cin would extend z to -1).
Tiling: NOT resolved. The four horizontal neighbours of W_C are c4, c6, c7 and (5,1,2) (must stay air), so cout cannot be tapped a fourth time losslessly in this layout. Hint only (unverified): make the front of c4 a solid S_C and put the cin wire of the next stage on top of it at y=2 (lossless from a strongly powered solid, facts-geometry vertical rule), i.e. stagger stages by +1 in y; but then c6/c7 need their own wire cells from S_C, so the cout branch must be re-laid; not done within the cap.

## 6. Unresolved / files / cost
Unresolved: (1) tiling pitch (above); (2) how the harness pins a wire (state write vs physical feed): cells given for both; (3) barrel item layout assumed 8 slots (7x64 + 46); any distribution totalling 494 stack-64 items gives level 5 (formula is on the total); (4) the auto-computed wire connection shapes are irrelevant to DC levels here (sides read POWER, no wire-wire hops), not re-derived per cell.
Files read: place1/facts-dc.md, place1/facts-geometry.md, place1/network.md, place1/net.json; minecraft-src/1.20.6-yarn/net/minecraft/block/AbstractRedstoneGateBlock.java (lines 70-154), ComparatorBlock.java (70-124), RedstoneWireBlock.java (251-276, 342-363, plus a grep for method lines), RedstoneBlock.java (grep only: lines 27, 32). Nothing under the development repository/, no web.
Cost: ~27 min wall, ~35k tokens.
