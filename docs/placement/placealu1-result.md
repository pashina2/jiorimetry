# PLACE-ALU1 draft v1 (18:05Z, at cap) - interface fixed, packing PARTIAL (not converged)
Axes +x east, +z south, +y up. facing=D: back = pos+D, output = pos-D. y=0 supports, y=1 working layer.

## A. Verified from source (opened: RedstoneTorchBlock.java 62-108, AbstractRedstoneGateBlock.java 128-152, RedstoneView.java 30-75, WallRedstoneTorchBlock.java 88-103, RedstoneWireBlock.java 342-363)
1. Comparator SIDE -> RedstoneView.getEmittedRedstonePower(pos,dir,false) -> for a torch getStrongRedstonePower(pos,dir); RedstoneTorchBlock:103-108 returns 0 unless dir==DOWN. A torch beside a comparator side reads 0 (facts-dc L11 "torch strong power" is literally true but horizontally zero). The network's torch nP (-> Qg.side, c4g.side) is NOT buildable in one layer; the y=2 route (torch -> block above -> wire) also fails when that block is beside any P-carrying wire (feedback: the wire reads the block's 15).
2. Gate at a SIDE is read only if its FACING == direction from reader to gate (AbstractRedstoneGateBlock:81-88): a gate whose output points INTO the reader is read; any other orientation reads 0 (safe filler for unused side cells).
3. Wire strongly powers its support and blocks it points at (RedstoneWireBlock:351-363); a solid a wire points at is read by a gate BACK at the wire's level.

## B. Interface (decided)
| cell | position (stage-relative) | kind | note |
|---|---|---|---|
| k | (0,2) | redstone_wire | = front cell of F(i-1); in the test pinned 0/3; read by kg.back only |
| kg | (1,2) comparator facing=west subtract | back=k, side (1,1)=P spur, side (1,3)=air/solid |
| f = F front | (PX,2) | redstone_wire | F at (PX-1,2) facing west, back K3 at (PX-2,2), sides (PX-1,1)=P spur, (PX-1,3)=c3p output wire |
| P | row z=0, cells (0..PX-1,0) | redstone_wire + one repeater[facing=west] | level 15 restored per stage; spurs at (x,1) give 14 to kg/nP/c7/F sides (needs >=4/>0/>=7/>=4) |
| Wn = NOT W {0,15} | row z=Z, cells (0..PX-1,Z) | redstone_wire + one repeater | W3 = sub(back=K3, side=Wn spur) = 3 iff Wn=0. sub(W15,K12) as proposed is unbuildable (a side cannot read a container, facts-dc L11); the 1-comparator conversion needs inverted polarity: Wn=15 -> ADD/AND, Wn=0 -> SUB/OR |
| a, b | wire cells inside | | each touching only its readers |
| r | wire cell = common front of c7 and c4g | | consumer reads its POWER |
Pitch vector (PX,0,0): k(i+1) = (PX,2) = F(i) front (gate->wire, lossless). P and Wn lines continue as straight rows through the joint (wire cell (PX-1,0) of stage i is adjacent to (PX,0) = (0,0) of stage i+1; same for row Z). PX not fixed (packing unfinished; estimate 9-10).
nP DECISION: nP = comparator subtract, back = redstone_block(15), side = P spur -> 15-P (15/0, >=6 if P=9). Replaces torch+solid (+1 comparator +1 redstone_block). Same truth table.

## C. Packing - what converged and what did not
Core chain row z=4 (flow east): K9 barrel(0,4,988 items) -> c1(1,4,fw,sub; side (1,5)=b wire, (1,3) air) -> S1(2,4) smooth_stone relay [(2,3),(2,5) air] -> c2(3,4,fw,sub) -> S2(4,4) relay.
c2's two sides fed by GATES pointing into it (no wires, avoids wire-wire adjacency): kg at (3,3) facing north (output south into c2; back (3,2)=k wire), Qg at (3,5) facing south (output north into c2; back (3,6)=S_W). Their sides (2,3),(2,5) air; (4,3),(4,5) = c3 / c3p (facing north/... read 0, rule A2).
Readers of S2: c3 at (4,3) facing north (back S2, side (5,3)=a wire, side (3,3)=kg reads 0) and c3p at (4,5) facing north?? -> c3p back would be (4,6) not S2: c3p must face SOUTH at (4,5)?? facing south back=(4,6) - wrong; facing north back=(4,4)=S2 OK, output (4,6)... wait output = pos-D = (4,5)-(0,-1) = (4,6). c3p side (5,5) = Wx wire = merge of x1, x2 fronts (dust max), other side (3,5)=Qg reads 0. F must then read c3p's output: F side needs c3p output at (4,6) wire.
CONFLICTS FOUND (why not converged): (i) c3 output cell (4,2) as relay S3 is adjacent to k (3,2) -> k picks up c3 level; needs k moved off row 2 or c3 output turned; (ii) with k at (3,2), kg.back = k, k(i+1) must be F(i) front => F sits at (2,2) of the NEXT stage's frame, i.e. F/K3 are hosted by the next stage's columns, and F's side (2,3) would need c3p's output routed across the joint - not resolved; (iii) c4 fan-out (S4 -> c6.side, c7.side, c4g.back) and a fan-out (c3.side, x1.back, x2.side around one wire cell) sketched, not placed.
Sketch for the rest (unplaced): c3 front -> S3 -> wires to c4.side and c5.side; c4 = cmp(K3,...) front -> S4 -> c4g.back direct, wires to c6.side, c7.side (c7 turned 90 deg so one wire touches c6 and c7 sides, as in place1); c5 = sub(K9,[c3]) front -> c6 back direct; c6 front -> c7 back direct; c7 sides (S4 wire, P spur); c7 front and c4g front -> the same wire cell r.

## D. Counts (per stage, projected; NOT a verified list)
comparators 16 = 14 network + nP(replaces torch) + W3 | barrels 2 (K9 988 items, K3 247 items; K3 faces: c4, F, W3) | redstone_block 1 | repeaters 2 (P, Wn) | solid relays ~6 (S1,S2,S3,S4,S_W,S_nP) | wire cells ~16 (a,b,k,r,f/k', P row ~PX-1, P spurs 4, Wn row ~PX-1, Wn spur 1, Wkg?,Wx, S3->c4/c5 2, S4->c6/c7 1, S_W->x1 1, S_nP->Qg/c4g 2) | supports ~1 per gate/wire. Total ~50 + supports, bounding box est. PX x 2 x 10.

## E. Unresolved
1. Full block list not produced within the cap; the 3 conflicts in C. 2. Whether the harness accepts an inverted W line (Wn) - else +torch route (needs y=2). 3. PX. 4. P/Wn repeater positions (any cell of the row with air on both z-neighbours except intended spurs... a spur wire beside a repeater is NOT read by it (repeater sides read gates only) but the spur would not connect to the repeater either - spurs must hang off wire cells, not the repeater cell).
Files opened: placealu/facts-dc.md, facts-geometry.md, alu1-network.md, net_alu1.json, example-place1-adder.md; minecraft-src 1.20.6-yarn: RedstoneTorchBlock.java, AbstractRedstoneGateBlock.java, RedstoneView.java, WallRedstoneTorchBlock.java, RedstoneWireBlock.java (grep + cited lines). Nothing under the development repository/, no web. ~45k tokens, 30 min (17:35Z-18:05Z).

## F. Second packing iteration (x-shifted frame, k at (0,3)) - also not closed
k(0,3) wire; kg(1,3) fw sub [back k, sides (1,2)=P spur 2nd cell (13), (1,4)=S1 -> 0]; Wkg(2,3) wire; c2(2,4) fw sub [back S1(1,4), sides Wkg (2,3) and Qg gate at (2,5) facing south pointing into c2]; c1(1,5) facing south sub [back K9(1,6), output S1, sides (0,5)=b, (2,5)=Qg -> 0 by A2]; Qg sides (1,5)=c1 -> 0, (3,5)=nP wire; S2(3,4).
Blocker: S2's only free reader cells are (4,4) [facing west] and (3,5)/(3,3); (3,5) is needed for Qg's nP wire and any wire at (3,5) or (3,3) is ADJACENT to S2 and takes c2's level (facts-geometry L5: strongly powered solid -> adjacent wire, all 6 faces). => c2 fan-out (c3, c3p) and the Qg nP side cannot share the S2 neighbourhood; needs a c2 copy comparator (cmp mode, +1) or nP delivered to Qg from the south side (Qg turned so its free side faces away from S2). Not done within the cap.
Lesson for the next seat: every solid relay forbids wires on ALL 6 faces except the intended ones; sketch the relay neighbourhoods (S1, S2, S3, S4, S_W, S_nP) FIRST, then the gates; with 6 relays in a 10-wide stage that is the real constraint, not the gate count.
