# RIG-1 -- result (Fable worker `0c3d10be`, 2026-09-07T21:41Z..22:0xZ, DIRECTOR 8 order `RIG-1-order.md`)

Non-canonical (`notes/**`). Bench only; no world, no aiwb, no git touched.

## 0. Answer

Yes. `rig1.program.json` (93 blocks, rig only, origin-relative) places a 5-lever feeder + 2 lamps around the standing `alu_stage_v7`
in ONE `/aiwb place`, after the operator airs 2 inert floor cells. Bench (`build_rig1.py`, lever states only, no pins):

```
PASS 32/32  (r,f identical to pinned alu_check2 rows: 32/32)
```

Lint (`alu_check2.lint`, stage + demo + rig): **L1 = 0, L2 = 0**; L3 (info) = 14 lines, of which 9 are the stage-own relays
and 5 are the rig-intended relays: (4,1,4)<-(4,0,4)<-(4,0,5); (8,1,5)<-(8,0,5)<-(8,0,6); (5,0,5)<-(5,-1,5)<-(5,-1,6);
(7,0,6)<-(7,-1,6)<-(7,-1,7); (12,-1,8)<-(12,0,8)<-(12,0,7). Full output: `sweep.log`.

## 1. Place line (absolute, anchor = program bbox min = origin (6005,133,-4113) + rig min offset (-4,-2,-1))

```
/aiwb place alu_stage_v7_rig1 6001 131 -4114
```

Program bbox abs (6001,131,-4114)..(6017,135,-4103). The bbox contains the stage; the gate refuses only payload-cell conflicts
(`tools/workbench/bridge/flows.py:5216-5240`) -- after step 2 the payload has 0 conflicts and the 176 stage + 5 demo cells are
"coexisting". Program cells in stage = exactly the 2 cells of step 2; program cells in demo cells = 0 (checked by script).

## 2. Cells the operator airs FIRST (stage floor, support nothing in v7; the program then puts the a2 feeder there)

```
/setblock 6012 133 -4107 air     (rel (7,0,6)  -> becomes redstone_wire, a2 side)
/setblock 6013 133 -4106 air     (rel (8,0,7)  -> becomes composter[level=3], a2 back)
```

Why 2 and not 0: a2 pin (8,1,5) is boxed in at y=1 ((7,1,5) cmp, (9,1,5) rep, (8,1,4) solid) and every feed from above fails:
a comparator with front (8,2,5) needs a side wire at (7,2,6) [reads the stage relay (6,2,6) and would power it into the back of (5,2,6)]
or (9,2,6) [its support would be the stage wire (9,1,6)]; a powered solid at (8,1,6) has no gate front that is not a stage cell.
So the only feed is the WORLD-2 one: strongly power the floor (8,0,5) from a comparator at (8,0,6) fS, whose back and side are these two cells.

## 3. Levers (absolute; all `lever[face=floor]` on a smooth_stone base one below)

| signal | lever abs | rel | base | meaning |
|---|---|---|---|---|
| a | (6017,135,-4108) | (12,2,5) | (12,1,5) | data: **ON = a 0, off = a 1** (drives pins (4,1,4),(8,1,5),(10,1,4) together) |
| b | (6003,135,-4108) | (-2,2,5) | (-2,1,5) | data: **ON = b 0, off = b 1** |
| k | (6003,135,-4112) | (-2,2,1) | (-2,1,1) | data: **ON = k 0, off = k 1** (side of the standing k comparator (-1,1,2)) |
| P | (6001,135,-4109) | (-4,2,4) | (-4,1,4) | control: **ON = 15 = logic (AND/OR), off = arithmetic (ADD/SUB)**; pins (0,1,0),(0,1,8) together |
| Wn | (6009,135,-4102) | (4,2,11) | (4,1,11) | control (standing): **ON = 15 = ADD/AND, off = SUB/OR** |

Mode: ADD = P off, Wn ON; SUB = P off, Wn off; AND = P ON, Wn ON; OR = P ON, Wn off.
Convention kept from WORLD-1/2: data lever ON = bit 0 (side 15 > back 3 kills the compare gate), lever OFF = bit 1.

Lamps: r = (6011,135,-4103) rel (6,2,10) next to r wire (6,2,9); f = (6014,134,-4111) rel (9,1,2), front of F (8,1,2).
LIT = output 3 = bit 1.

## 4. The 32 rows (Bench, lever states -> r / f level -> lamps)

| op | a b k | a | b | k | P | Wn | r | f | r lamp | f lamp |
|---|---|---|---|---|---|---|---|---|---|---|
| ADD | 0 0 0 | ON | ON | ON | off | ON | 0 | 0 | dark | dark |
| ADD | 0 0 1 | ON | ON | off | off | ON | 3 | 0 | LIT | dark |
| ADD | 0 1 0 | ON | off | ON | off | ON | 3 | 0 | LIT | dark |
| ADD | 0 1 1 | ON | off | off | off | ON | 0 | 3 | dark | LIT |
| ADD | 1 0 0 | off | ON | ON | off | ON | 3 | 0 | LIT | dark |
| ADD | 1 0 1 | off | ON | off | off | ON | 0 | 3 | dark | LIT |
| ADD | 1 1 0 | off | off | ON | off | ON | 0 | 3 | dark | LIT |
| ADD | 1 1 1 | off | off | off | off | ON | 3 | 3 | LIT | LIT |
| SUB | 0 0 0 | ON | ON | ON | off | off | 0 | 0 | dark | dark |
| SUB | 0 0 1 | ON | ON | off | off | off | 3 | 3 | LIT | LIT |
| SUB | 0 1 0 | ON | off | ON | off | off | 3 | 3 | LIT | LIT |
| SUB | 0 1 1 | ON | off | off | off | off | 0 | 3 | dark | LIT |
| SUB | 1 0 0 | off | ON | ON | off | off | 3 | 0 | LIT | dark |
| SUB | 1 0 1 | off | ON | off | off | off | 0 | 0 | dark | dark |
| SUB | 1 1 0 | off | off | ON | off | off | 0 | 0 | dark | dark |
| SUB | 1 1 1 | off | off | off | off | off | 3 | 3 | LIT | LIT |
| AND | 0 0 0 | ON | ON | ON | ON | ON | 0 | 0 | dark | dark |
| AND | 0 0 1 | ON | ON | off | ON | ON | 0 | 0 | dark | dark |
| AND | 0 1 0 | ON | off | ON | ON | ON | 0 | 0 | dark | dark |
| AND | 0 1 1 | ON | off | off | ON | ON | 0 | 0 | dark | dark |
| AND | 1 0 0 | off | ON | ON | ON | ON | 0 | 0 | dark | dark |
| AND | 1 0 1 | off | ON | off | ON | ON | 0 | 0 | dark | dark |
| AND | 1 1 0 | off | off | ON | ON | ON | 3 | 0 | LIT | dark |
| AND | 1 1 1 | off | off | off | ON | ON | 3 | 0 | LIT | dark |
| OR | 0 0 0 | ON | ON | ON | ON | off | 0 | 0 | dark | dark |
| OR | 0 0 1 | ON | ON | off | ON | off | 0 | 0 | dark | dark |
| OR | 0 1 0 | ON | off | ON | ON | off | 3 | 0 | LIT | dark |
| OR | 0 1 1 | ON | off | off | ON | off | 3 | 0 | LIT | dark |
| OR | 1 0 0 | off | ON | ON | ON | off | 3 | 0 | LIT | dark |
| OR | 1 0 1 | off | ON | off | ON | off | 3 | 0 | LIT | dark |
| OR | 1 1 0 | off | off | ON | ON | off | 3 | 0 | LIT | dark |
| OR | 1 1 1 | off | off | off | ON | off | 3 | 0 | LIT | dark |

Levels seen at the feeder sides (all rows): a1 (5,0,5) / a2 (7,0,6) / a3 (11,1,5) = 15 with lever ON, 0 off; k (-1,1,1), b (-1,1,5) = 15/0;
P pins read 6 and 8 (repeaters need > 0); Wn pin 15/0. Pins are exactly 3/0 at all 5 a/b/k cells in every row.

## 5. Construction (rig only; every wire has a solid below, no diagonal wire links)

* k: wire (-1,1,1) on (-1,0,1), base (-2,1,1), lever (-2,2,1). Uses the standing comparator (-1,1,2) fW + barrel (-2,1,2) (5 bows = level 3).
* b: comparator (-1,1,4) fW on (-1,0,4), back composter[level=3] (-2,1,4), side wire (-1,1,5) on (-1,0,5), base (-2,1,5), lever (-2,2,5).
* a (one lever): base (12,1,5) strongly powers the a3 side (11,1,5) and the wire (12,0,5) under the base.
  a3: comparator (11,1,4) fE on (11,0,4), back composter (12,1,4), front = pin (10,1,4).
  Down without diagonals: (12,0,5) -> (12,0,6) -> repeater (12,0,7) fN -> solid (12,0,8) strong -> wire (12,-1,8) under it;
  y=-1 run (12..5,-1,8) on y=-2 supports.
  a2: repeater (7,-1,7) fS -> solid (7,-1,6) strong -> side wire (7,0,6) above it; comparator (8,0,6) fS on (8,-1,6), back composter (8,0,7),
  front = stage floor (8,0,5) -> pin (8,1,5).
  a1: wire (5,-1,7), repeater (5,-1,6) fS -> solid (5,-1,5) strong -> side wire (5,0,5) above it; comparator (4,0,5) fS on (4,-1,5),
  back composter (4,0,6), front = stage floor (4,0,4) -> pin (4,1,4). (3,0,5) stays air (WORLD-2: (3,1,5) above it is a stage relay).
* P (one lever): base (-4,1,4), lever (-4,2,4); y=1 wires x=-4 z=-1..3 and 5..8 (each end 15 at the base), rows z=-1 x=-3..0 into pin (0,1,0)
  and z=8 x=-3..-1 into pin (0,1,8); supports at y=0. x=-4 keeps one air cell between the line and the k/b bases and composter.
* Lamps: redstone_lamp (6,2,10), (9,1,2).
* Counts: smooth_stone 44, redstone_wire 32, lever 4, composter 4, comparator 4, repeater 3, redstone_lamp 2 = 93. y range -2..2.

## 6. Bench substitutions (declared, `rig1_full_bench.json` "substitutions")

* composter[level=3] at (-2,1,4), (4,0,6), (8,0,7), (12,1,4) -> barrel with 247 cobblestone (level 3). The machine refuses a composter
  outright ("no solidity rule for minecraft:composter", machine.py:569) -- checked, so the substitution is the only way to run it.
  Difference to the world: composter is not a full cube. No wire is horizontally adjacent to any composter (checked on the 4 cells:
  their neighbours are gate backs, bases, air), so the solid/non-solid difference changes no dust connection.
* The standing barrel (-2,1,2) with 5 bows (level 3) is declared as barrel 247 (level 3).
* redstone_lamp at (6,2,10), (9,1,2) -> smooth_stone (full-cube conductor, same neighbour connectivity). The sweep shows no leak
  into the stage from either (32/32 identical to the pinned rows). Lamp column in section 4 = output > 0 by rule
  (RedstoneLampBlock lights on any received power; the r wire points into (6,2,10), the F output strongly powers (9,1,2)).
* composter level source (given by the previous agent, not re-derived here): ComposterBlock.java:307-313 hasComparatorOutput /
  getComparatorOutput return LEVEL; ComparatorBlock.java:103-109 reads it at the back. composter[level=3] is a blockstate, no block entity.

## 7. Bookkeeping

* Files opened: RIG-1-order.md; alu_stage_v7.json, alu_check2.py, alu_stage_v7.json.rows.json (placealu3); bench_sweep.py,
  facts-dc-v2-given.md (placealu2); layout_world2.json, bench_sweep_feed2.py, record.md (world2); facts-geometry-given.md (place1);
  vert/README.md; alu-place-handover.md section 4; flows.py:5190-5300; capcell.py (lines 60-140, 240-300, 350-440, greps);
  machine.py (160-215, 480-495, 820-840, greps). capcell.py/machine.py were read from the main checkout
  (<host-path><dev-repo>/tools/workbench/llmgen) because the worktree has no capcell.py; the sweep imports from there too.
* Drafts: draft_1.json (32/32 but 14 L2 diagonal links -- rejected against constraint L1/L2 = 0), draft_2.json (20/32: a1 repeater
  back was air), draft_3.json (32/32, L1/L2 = 0) = final.
* Wall clock: 21:41:39Z start, 21:52:51Z final pass, report written ~22:02Z. Token self-estimate: ~105k in / ~30k out.
* Not done: a Bench run with real composter/lamp blocks (machine refuses composter). Not done: any world act.
