# PLACE-ALU2 draft v2 (19:00Z, at cap) - north half CONVERGED (k->f path, c1/c2/c3, Qg2, P injection), south half (c4..c7, c4g, r, XOR, Wn) NOT closed
Axes +x east, +z south, +y up. facing=D: back = pos+D, output = pos-D. y=0 supports under every y=1 gate/wire; y=1 working layer; y=2 used ONLY for the P bridge (section 0). Coordinates (x,z) are y=1 unless written (x,y,z). PX = 9 (k at (0,2), f at (9,2)). Names: S2b = copy relay of S2; Qg2 = the gate pointing into c2.

## 0. KEY FINDING (the assumption shared by both previous collapses and my first 25 min)
The k->f data path is forced to be a contiguous wall in rows 2-3 across the WHOLE stage width:
k(0,2) kg(1,2) w_kg(2,2) c2(2,3) S2(3,3) c2c(4,3) S2b(5,3) c3p(6,3) S3p(7,3) w3p(8,3) F(8,2) f(9,2).
Every cell is a gate, relay or data wire; nothing may pass through it in one layer; column 0 / column PX-1 are k / F.
P lives north of the wall (row 0); c4..c7, c4g, r, Qg1, x1/x2 and Wn live south. So P (needed by nP1, nP2 and the arithmetic-leg kill) cannot reach the south half in ONE layer. This is why every one-layer packing collapsed.
FIX (decided): a P BRIDGE at y=2 over the wall using repeaters standing on relays (gates read only horizontally, so a repeater on a strongly powered solid neither reads it nor leaks into it):
  P row (5,0) -> repeater (5,1,1) facing north -> S_sup (5,1,2) smooth_stone, strongly powered 15 -> wire (5,2,2) on top (lossless, vertical rule) -> repeater (5,2,3) facing north standing on S2b (5,1,3) -> repeater (5,2,4) facing north on S_sup2 (5,1,4) (unpowered post) -> y=2 repeater chain on solids until it descends: repeater -> S_down (x,2,z) solid strongly powered 15 -> wire (x,1,z) BELOW it (lossless) -> feeds south-side repeater injectors (repeater back reads the wire; output 15 exactly).
  Checked: S_sup (5,1,2) neighbours (4,2) air, (6,2) air, (5,3)=S2b solid (strong does not propagate solid->solid), no gate back adjacent (c2c back=(3,3), c3p back=(5,3)); c3p side (6,2) air; c2c side (4,2) air.
Two more mechanism changes that made the north half close:
  A. P is injected only by REPEATERS pointing into the consumer side (exact 15 when P>0, 0 when P=0); no P spur wires. Repeater sides read gates only, so repeaters may sit beside relays.
  B. Qg is split: Qg2 = subtract(back = S_L, no live side) points into c2; S_L = front of Qg1 = subtract(back = K3q, sides = [nP1 gate pointing in, WnRep repeater pointing in]) = 3 iff (P=15 and Wn=0). Same truth table as Qg. W3 (level-3 W) is then needed only by x1/x2.

## 1. Relay map
| relay | pos | source | readers | forbidden-for-wire neighbours (state) |
|---|---|---|---|---|
| S1 | (1,3) | c1 front (1,4) fS | c2 back (2,3) | (0,3) air; (1,2)=kg (kg side reads solid = 0) |
| S2 | (3,3) | c2 front | c2c back (4,3); c3 back (3,4) | (3,2) air |
| S2b | (5,3) | c2c front | c3p back (6,3) | (5,2)=S_sup solid; (5,4)=S_sup2 solid; top (5,2,3)=repeater (no leak) |
| S3p | (7,3) | c3p front | w3p wire (8,3) -> F side | (7,2)=K3F barrel; (7,4) air |
| S_L | (2,5) | Qg1 front (2,6) fS | Qg2 back (2,4) | (1,5)=K9 barrel; (3,5)=S3 solid |
| S3 | (3,5) | c3 front (3,4) fN | cc3 back (4,5) | (2,5)=S_L solid; (3,6)= Qg1 injector gate (faces east, does not read S3) |
| S3b | (5,5) | cc3 front (4,5) fW | south half: c4/c5 side wire | (5,4)=S_sup2; (6,5)=S_x solid; (5,6) OPEN CONFLICT (section 7) |
| S_sup | (5,2) | repeater (5,1) fN (15) | wire (5,2,2) on top | (4,2),(6,2) air |
| S_sup2 | (5,4) | none (unpowered post) | repeater (5,2,4) on top | (4,4)=a touches it: harmless (unpowered solid) |

## 2. Block list - CONVERGED part (rows 0-7, PX=9). Supports: smooth_stone at (x,0,z) under every y=1 wire and gate listed; relays/barrels/redstone_block need none.
| x | y | z | block | role |
|---|---|---|---|---|
| 0,1,2,3,5,6,7,8 | 1 | 0 | redstone_wire | P row (enters (0,0) from stage i-1, leaves (8,0)->(9,0)) |
| 4 | 1 | 0 | repeater[facing=west] | P row repeater (back (3,0), out (5,0)); no injector under it |
| 1 | 1 | 1 | repeater[facing=north] | P injector -> kg side |
| 8 | 1 | 1 | repeater[facing=north] | P injector -> F side |
| 5 | 1 | 1 | repeater[facing=north] | P bridge start (back (5,0) wire = 15) |
| 0 | 1 | 2 | redstone_wire | k = F(i-1) front |
| 1 | 1 | 2 | comparator[facing=west,mode=subtract] | kg: back k, sides (1,1) rep, (1,3)=S1 solid -> 0 |
| 2 | 1 | 2 | redstone_wire | w_kg = kg front; neighbours (3,2) air, (2,1) air |
| 5 | 1 | 2 | smooth_stone | S_sup (bridge post, 15) |
| 5 | 2 | 2 | redstone_wire | bridge wire on S_sup (15) |
| 7 | 1 | 2 | barrel (247 stack-64 items, level 3) | K3F = F back |
| 8 | 1 | 2 | comparator[facing=west,mode=compare] | F: back K3F, sides (8,1) rep(P), (8,3) w3p; out (9,2) = f = k(i+1) |
| 1 | 1 | 3 | smooth_stone | S1 |
| 2 | 1 | 3 | comparator[facing=west,mode=subtract] | c2: back S1, sides (2,2) w_kg, (2,4) Qg2 gate; out S2 |
| 3 | 1 | 3 | smooth_stone | S2 |
| 4 | 1 | 3 | comparator[facing=west,mode=compare] | c2c copy: back S2, sides (4,2) air, (4,4)=a (harmless: a <= c2 on all rows, compare passes); out S2b |
| 5 | 1 | 3 | smooth_stone | S2b |
| 5 | 2 | 3 | repeater[facing=north] | bridge, standing on S2b |
| 6 | 1 | 3 | comparator[facing=west,mode=subtract] | c3p: back S2b, sides (6,2) air, (6,4) xm gate; out S3p |
| 7 | 1 | 3 | smooth_stone | S3p |
| 8 | 1 | 3 | redstone_wire | w3p (neighbours (9,3)=next (0,3) air, (8,4) air) |
| 0 | 1 | 4 | redstone_wire | b (neighbours (0,3),(0,5) air, (-1,4)=prev (8,4) air) |
| 1 | 1 | 4 | comparator[facing=south,mode=subtract] | c1: back K9 (1,5), sides (0,4) b, (2,4)=Qg2 (faces south, direction east -> 0); out S1 |
| 2 | 1 | 4 | comparator[facing=south,mode=subtract] | Qg2: back S_L (2,5), sides (1,4)=c1 -> 0, (3,4)=c3 -> 0; out (2,3) = c2 side |
| 3 | 1 | 4 | comparator[facing=north,mode=subtract] | c3: back S2, sides (2,4)=Qg2 -> 0, (4,4)=a; out S3 (3,5) |
| 4 | 1 | 4 | redstone_wire | a (neighbours (4,3)=c2c side harmless, (5,4)=S_sup2 unpowered, (4,5)=cc3 gate, (3,4)=c3 side) |
| 5 | 1 | 4 | smooth_stone | S_sup2 (unpowered post) |
| 5 | 2 | 4 | repeater[facing=north] | bridge, standing on S_sup2 |
| 6 | 1 | 4 | comparator[facing=south,mode=compare] | xm: back (6,5)=S_x, sides (5,4) solid, (7,4) air; out (6,3) = c3p side |
| 1 | 1 | 5 | barrel (988 stack-64 items, level 9) | K9 = c1 back |
| 2 | 1 | 5 | smooth_stone | S_L |
| 3 | 1 | 5 | smooth_stone | S3 |
| 4 | 1 | 5 | comparator[facing=west,mode=compare] | cc3 copy: back S3, sides (4,4)=a (harmless: c3 >= a or c3 = 0 on all rows), (4,6) gate-only; out S3b (5,5) |
| 5 | 1 | 5 | smooth_stone | S3b (level c3) |
| 5 | 2 | 5 | repeater[facing=north] | bridge, standing on S3b |
| 6 | 1 | 5 | smooth_stone | S_x (max of x1, x2 fronts; sources NOT placed) |
| 2 | 1 | 6 | comparator[facing=south,mode=subtract] | Qg1: back K3q (2,7), sides (1,6)=nP1 gate, (3,6)=WnRep gate; out S_L |
| 2 | 1 | 7 | barrel (247 items) | K3q |
| 1 | 1 | 6 | comparator[facing=west,mode=subtract] | nP1: back RB (0,6), side (1,5)=K9 -> 0, side (1,7)= repeater[facing=south] (P injector, back (1,8)); out (2,6) = Qg1 side |
| 1 | 1 | 7 | repeater[facing=south] | P injector for nP1 (back (1,8) = P wire from the bridge descent - OPEN) |
| 0 | 1 | 6 | redstone_block | RB for nP1 ((0,5),(0,7),(-1,6) must be air) |
| 3 | 1 | 6 | repeater[facing=east] | WnRep -> Qg1 side; back (4,6) must carry Wn (repeater facing east or corner wire) - OPEN |
MUST STAY AIR: (0,3) (3,2) (4,2) (6,2) (2,1) (3,1) (4,1) (6,1) (7,1) (0,5) (0,7) (7,4) (8,4) (9,3), all y=2 cells except the bridge, row z=-1 entirely.

## 3. Per-comparator table (placed)
| node | pos | facing | mode | back | side- | side+ | out |
|---|---|---|---|---|---|---|---|
| kg | (1,2) | W | sub | k wire (0,2) | (1,1) rep(P) 15/0 | (1,3) S1 solid = 0 | (2,2) w_kg |
| c1 | (1,4) | S | sub | K9 barrel (1,5) = 9 | (0,4) b | (2,4) Qg2 gate not facing east = 0 | (1,3) S1 |
| c2 | (2,3) | W | sub | S1 (= c1) | (2,2) w_kg | (2,4) Qg2 facing south = read | (3,3) S2 |
| c2c | (4,3) | W | cmp | S2 (= c2) | (4,2) air | (4,4) a (<= c2, passes) | (5,3) S2b |
| c3 | (3,4) | N | sub | S2 (= c2) | (2,4) Qg2 = 0 | (4,4) a | (3,5) S3 |
| cc3 | (4,5) | W | cmp | S3 (= c3) | (4,4) a (harmless) | (4,6) must be non-reading gate/air | (5,5) S3b |
| c3p | (6,3) | W | sub | S2b (= c2) | (6,2) air | (6,4) xm facing south = read | (7,3) S3p |
| xm | (6,4) | S | cmp | S_x (6,5) = max(x1,x2) | (5,4) solid = 0 | (7,4) air | (6,3) c3p |
| F | (8,2) | W | cmp | K3F (7,2) = 3 | (8,1) rep(P) | (8,3) w3p | (9,2) f |
| Qg2 | (2,4) | S | sub | S_L (= Qg1) | (1,4) c1 = 0 | (3,4) c3 = 0 | (2,3) c2 |
| Qg1 | (2,6) | S | sub | K3q (2,7) = 3 | (1,6) nP1 facing west = read | (3,6) WnRep facing east = read | (2,5) S_L |
| nP1 | (1,6) | W | sub | RB (0,6) = 15 | (1,5) K9 barrel = 0 | (1,7) rep(P) facing south | (2,6) Qg1 |

## 4. Interface
k (0,2); f (9,2) = F front; a (4,4); b (0,4); P row z=0: entry (0,0), exit (8,0)->(9,0), repeater (4,0); Wn row z=Z (Z >= 10, not fixed): entry (0,Z), exit (8,Z); r = NOT PLACED; PX = 9. Cells of the next stage assumed: (9,3) air, (9,0) wire, (9,2) wire.

## 5. Counts (placed part only)
comparators 12 (kg,c1,c2,c2c,c3,cc3,c3p,xm,F,Qg2,Qg1,nP1) | repeaters 9 (P row 1; injectors (1,1),(8,1),(1,7),(3,6); bridge (5,1),(5,2,3),(5,2,4),(5,2,5)) | barrels 3 (K9, K3F, K3q) | redstone_block 1 | relays/posts 10 (S1,S2,S2b,S3p,S_L,S3,S3b,S_x,S_sup,S_sup2) | wires 14 (P row 8, k, w_kg, w3p, b, a, bridge (5,2,2)) | supports ~24 | placed total ~73. Bounding box so far x 0..8, y 0..2, z 0..7.

## 6. Network changes vs net_alu1.json
- nP torch -> nP1 = sub(RB, rep(P)) (and nP2 for c4g, unplaced); P delivered only by repeaters pointing into sides.
- Qg -> Qg1 = sub(K3q, [nP1, WnRep]) + Qg2 = sub(S_L) pointing into c2 (one extra copy stage; same function).
- c2 fan-out via compare copy c2c (S2 -> S2b); c3 fan-out via compare copy cc3 (S3 -> S3b); both copies have a harmless a on one side (compare passes because a <= c2 and (c3 >= a or c3 = 0) on all 32 rows of the table in alu1-network.md).
- XOR merge: x1 and x2 fronts both onto ONE solid S_x (received strong power = max), read by xm = cmp(S_x) pointing into c3p (x1, x2 unplaced). Alternative (not used): split c3p into c3p1 = sub(c2,[x2]) -> c3p2 = sub(c3p1,[x1]) collinear (max = sum since at most one is nonzero), each with one gate-in side.
- W3 for x1/x2: W3a/W3b = sub(K3, [WnRep]) per reader (unplaced). Simpler legal option: 15-level controls only: x1 = sub(a, [W15 gate]) with W15 = sub(RB, [WnRep]); x2 = sub(S_3a, [WnRep]) with S_3a = front of sub(K3, [a]) - no level-3 W anywhere.
- P kill of the arithmetic leg may move from c7 to c5 (rep(P)=15 > 9) or c6 (15 > 6): c5 = 0 forces c6 = c7 = 0 in logic mode; choose the gate nearest the bridge descent.

## 7. NOT COMPLETE - exact remaining conflicts and what was tried
(a) Bridge descent cell: at (5,5) the descended wire is the front cell of cc3 (c3 pours into P); at (5,6) the wire is adjacent to relay S3b (takes c3); at (5,7) it needs post (5,6), and then the WnRep back chain (4,6)->(5,6) reads an unpowered solid (0). Next try: descend at (5,8) with posts (5,6),(5,7); swap nP1 and WnRep on Qg1 (WnRep at (1,6) facing west, back (0,6) = corner wire fed by a south-facing repeater column at x=0 from the Wn row; nP1 at (3,6) facing east, back RB (4,6), P injector at (3,7) facing south with back (3,8) = wire fed (5,8)->(4,8)->(3,8), all lateral neighbours air). Not verified.
(b) c4/c5 from S3b (5,5): the only free face is (5,6) (west = cc3, east = S_x, north = post). A wire w3 at (5,6) collides with the bridge post. RECOMMENDED: move the bridge to column 7: (7,1,1) repeater facing north -> K3F (7,1,2) barrel becomes a strongly powered post (F back still reads the container value: ComparatorBlock.getPower prefers hasComparatorOutput; the barrel emits 15 only to (6,2)=air and (7,3)=S3p solid, no propagation) -> wire (7,2,2) on K3F -> repeater (7,2,3) on S3p -> repeater (7,2,4) on a post (7,1,4) -> ... Column 5 is then free of posts; S_sup/S_sup2 disappear; w3 at (5,6) becomes legal.
(c) With w3 at (5,6): readers must be N/S-facing gates at (4,6) and (6,6). c4 at (4,6) facing south, back K3c (4,7), side (5,6) = w3, side (3,6) = WnRep (faces east, direction from c4 = west -> 0), output (4,5) = cc3: cc3 side (4,6) then reads c4 (facing south = direction from cc3) -> cmp(c3, [a, c4]) still passes (c4 = 3 only when c3 <= 3: c3 = 3 passes, c3 = 0 gives 0 anyway) - harmless. c5 at (6,6) facing south: back K9b (6,7), output (6,5) = S_x -> would strongly power S_x with 3T. UNRESOLVED: both readers of w3 need backs at rows 5/7 in columns 4/6; row 5 is taken by cc3 and S_x; S_x is pinned by xm (6,4), xm is pinned by the c3p side (6,4). Circular at the cap. Candidate: use the c3p1/c3p2 split (section 6) so (6,4) becomes x2 pointing in and (6,5) frees for K9b.
(d) Not placed: x1, x2, S_W/W3 (or the 15-level variant), ca (a copy for the x2 side; a has NO free face now: (4,3) c2c, (3,4) c3, (5,4) post, (4,5) cc3 - with the bridge moved to column 7, (5,4) frees up, but ca = cmp(back = a) at (5,4) facing west needs its output at (6,4) = xm: conflict again unless the c3p split is used), c6, c7, c4g, nP2, r, Wn row and its conduit.

## 8. Files read / cost
placealu2/: placealu1-partial.md, facts-dc-v2.md, facts-geometry.md, alu1-network.md, net_alu1.json, example-place1-adder.md. No minecraft-src lines opened this run (rules taken from the two facts files and placealu1-partial A1-A3). Nothing under the development repository/, no web. ~70k tokens, 40 min (18:20Z-19:00Z).

## 9. Addendum (18:58Z) - south half, second pass with the bridge moved to column 7 (partial, NOT verified as a whole)
Bridge column 7: (7,1,1) repeater fN [back (7,0) P] -> K3F (7,1,2) strongly powered 15 (F back still reads the container value - UNVERIFIED against ComparatorBlock.getPower; (6,2) must stay air) -> wire (7,2,2) on K3F -> repeater (7,2,3) fN on S3p -> repeater (7,2,4) fN on post (7,1,4) -> repeater (7,2,5) fN on post (7,1,5) (post is beside S_x (6,5): solid-solid, fine) -> S_down (7,2,6) solid 15 -> P_s wire (7,1,6) below it [(6,6)=K9b barrel inert, (8,6) air, (7,7)=repeater]. Column 5 posts S_sup/S_sup2 removed; (5,2),(5,4) air.
Tail cells that then close:
| cell | block | role / check |
|---|---|---|
| (5,6) | comparator[facing=north,mode=compare] cc4 | back S3b (5,5) = c3; sides (4,6)=K3c barrel -> 0, (6,6)=K9b barrel -> 0; out (5,7) |
| (5,7) | redstone_wire w3b | = c3; neighbours (4,7) c4 side, (6,7) c5 side, (5,8) AIR |
| (4,6) | barrel 247 K3c | c4 back; also cc3 side cell (barrel -> 0) |
| (4,7) | comparator[facing=north,mode=subtract->compare] c4 | mode COMPARE; back K3c (4,6); sides (3,7)=? must be air/non-reading, (5,7) w3b; out (4,8) = S4 relay |
| (6,6) | barrel 988 K9b | c5 back |
| (6,7) | comparator[facing=north,mode=subtract] c5 | back K9b; sides (5,7) w3b, (7,7) rep(P) -> c5 = 3T in arithmetic, 0 in logic (P kill moved here); out (6,8) = S5 relay |
| (7,7) | repeater[facing=north] | P injector into c5 side (back (7,6) P_s) |
| (4,8) | smooth_stone S4 | = c4; readers c4g back, c6/c7 side wire - OPEN |
| (6,8) | smooth_stone S5 | = c5; reader c6 back - OPEN |
RESIDUAL CONFLICT (the one that stopped this pass): c6 = sub(S5, [c4]) needs a cell adjacent to S5 (6,8) as its back AND a wire adjacent to S4 (4,8) as its side; S4 and S5 are two columns apart with (5,8) forced air (w3b neighbour). Candidates: c6 at (6,9) fN (back S5) with side (5,9) = wire fed by S4 via (4,9)? (4,9)-(5,9) would be wire-wire (-1) - illegal for data. => either move c5 so S5 lands at (5,8)... impossible (w3b at (5,7) forbids a relay at (5,8)), or copy c4 once more: cc4b = cmp(back S4) at (4,9) fS -> out (4,10) = S4b, and build c6/c7/c4g/r around S4b and a copy of S5 (cc5 at (6,9) fN -> S5b (6,10)): c6 at (5,10) facing east (back S5b? no, (6,10) is east of (5,10): facing east -> back (6,10) = S5b OK), sides (5,9) and (5,11): wire from S4b at (5,11)? S4b is at (4,10): (5,11) not adjacent. c6 at (5,10) sides need a wire adjacent to S4b: (5,10) itself is adjacent to S4b (4,10) - a comparator cannot read a solid on its side. => put the S4b wire at (4,11) and c6 at (5,11) facing east with back (6,11) = S5b moved one row (cc5 output at (6,11) needs cc5 at (6,10) fN with back (6,9)=S5? no, back of a north-facing gate at (6,10) is (6,9), which must be S5 -> S5 at (6,9) -> c5 at (6,8) -> shift c5/K9b one row south: c5 (6,8) fN back K9b (6,7)?? then c5 side (5,8) is not w3b. Circular; not closed at the cap.
Remaining unplaced after this pass: c6, c7, c4g, nP2 (+RB), r, x1, x2, S_W/W3 (or 15-level variant), ca/a-copy, Wn row (z >= 12) and its repeater column, the Wn corner for WnRep (3,6) [back (4,6) is now K3c barrel -> reads 0!! => WnRep must move to the west side of Qg1: WnRep (1,6) fW with back (0,6) = corner wire fed by a south-facing repeater column at x=0; nP1 then at (3,6) fE with back RB (4,6) - conflicts with K3c at (4,6) => K3c must go to (3,7)?? that is c4 side cell (barrel -> 0, fine) but c4 back must be (4,6)... => c4 faces south at (4,7) with back (4,8)=K3c and output (4,6)=RB cell ✗. UNRESOLVED].
