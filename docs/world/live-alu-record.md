# LIVE-ALU — the record of ALU stage v7 running in the operator's world (DIRECTOR 8 `0c3d10be`, 2026-09-07T21:1x–21:27Z)

> 日本語: [live-alu-record.ja.md](live-alu-record.ja.md)

A D4.1 observation (the operator's world, regioncap = reading the region files, with 3 untouched captures included). Not promotion-grade (`notes/**`).

## Placement
- The program `alu_stage_v7_nobarrel` (170 blocks; `artifacts/programs/alu_stage_v7_nobarrel.program.json` was put into the host's programs dir) was placed **by the operator** with `/aiwb place alu_stage_v7_nobarrel 6005 133 -4113` (after the worldsnap snapshot at 20:56Z; the first attempt was refused as backup_stale).
- The 6 barrels are block entities, so the operator placed them by hand and put bows into them (level 3 = 5 bows ×4, level 9 = 16 bows ×2). The first read (21:13Z) showed that the two level-9 barrels held 15 bows (level 8), which was corrected by adding one bow each.
- The capture at 21:17Z: 176/176 placements matched, 6/6 barrels correct, and **23/23 comparators matched the Bench's steady state (SUB 0,0,0)**.

## Demonstration (only k is fed; Wn is switched with a lever)
The feeder: comparator (6004,134,-4111) facing west, back = the barrel (6003,134,-4111) with 5 bows → the k pin (6005,134,-4111) = 3. Wn: solid (6009,134,-4102) + lever (6009,135,-4102).

| state | k | Wn | r (6011,135,-4104) | f (6013,134,-4111) | Bench | comparators |
|---|---|---|---|---|---|---|
| lever ON = ADD 0+0+1 | 3 | 15 | **3** | **0** | r 3 f 0 | 24/24 matched |
| lever OFF = SUB 0−0−1 | 3 | 0 | **3** | **3** (borrow) | r 3 f 3 | 24/24 matched |

A miss that was caught: twice in a row a feeder barrel was reported as filled while it was still empty (the items had gone into a different barrel; the wording is paraphrased in this text). A barrel's contents in a region file are only updated when the chunk is saved, but this time autosave was fast enough (at each read the mtime was within a minute).

## The scope of the claim
A 1-bit ALU slice (ADD/SUB/AND/OR, data on {0,3}), in a placement that a machine derived from the rule sheets and the algebra (PLACE-ALU-3, Bench 32/32) → the synthetic world 32/32 → the operator's world, where 1 steady state + 2 driven states matched the Bench. Not all 32 rows have been run in the world (placing the 8 points of the feeder rig is an act of the operator's hand, so today it was 3 states). 8 stages, speed and tiling have not been started.
