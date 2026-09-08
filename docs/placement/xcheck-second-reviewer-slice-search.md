# Cross-check of Astra's slice-search candidates with the DIRECTOR's checkers (2026-09-08T11:11Z)

Astra (second model, reviewer; WORKER Codex) searched pitch / boundary / feed routes with v9's interior fixed
(`(the reviewer's own experiment directory, not included in this export)/`). Their judge (`verify.py`) and these checkers share the Bench but were written
independently. Both candidates that Astra reports as FOUND pass here, and the pitch-11 geometry Astra reports as
rejected fails here on the same boundary pair. Bench = main after landing #49 (pins as floors, two-seed DC solve).

## Astra's pitch-14 candidates under `tools/checks/alu_check_slices.py` (function table)

```
== relocated p14 function
n=1 PASS 32/32
n=2 PASS 128/128
== plain p14 function n=2
n=2 PASS 128/128
```

## Astra's pitch-11 geometry (rebuilt with `search.setup/compose(source, 11, 0)`) under `tools/checks/alu_check_contract.py`

Astra's first counterexample: ADD A=1 B=0 k=0, expected [3,0], measured [3,2], wires (10,2,4)-(11,2,4).
Here the same pair is a structural C5 failure before any row is solved, and the measured clauses fail as well:

```
== p11 candidate 0 under the DIRECTOR contract checker
C1 box x 0..10 y 0..3 z 0..13  PX=11  cells=286  (y=3 used)
C4 port a (10, 1, 13) on south face
note C4 port a (10, 1, 13) lies in the x=10 column; allowed only through C5
C4 port b (0, 3, 6) on top face
note C4 port b (0, 3, 6) lies in the x=0 column; allowed only through C5
C4 port r (6, 3, 9) on top face
note C5 x=0 wire (0,3,6) faces air in the previous slice
note C5 x=10 wire (10,1,10) faces air in the next slice
note C5 x=10 wire (10,1,13) faces air in the next slice
C5 boundary pair (10,2,0) repeater -> next (0,2,0) wire [allowed]
C5 boundary pair (10,2,2) comparator -> next (0,2,2) wire [allowed]
FAIL C5 boundary pair (10,2,4) minecraft:redstone_wire <-> next (0,2,4) minecraft:redstone_wire
C5 boundary pair (10,3,12) repeater -> next (0,3,12) wire [allowed]
C6 lint tiled n=2: L1=0 L2=0 L3=46
measured n=3 rows=512: C2 through-entry mismatches=0, C3 carry mismatches=42 (final f mismatches=13), C5 local-table mismatches=128, non-converged/bistable rows=0
CONTRACT FAIL: 16 FAIL, 5 notes
```

## v9 under the patched `tools/checks/alu_check_contract.py`

Astra's reading of the checker named three holes (convergence and final f not asserted, side lock checked on one
slice only, duplicate coordinates silently overwritten). All three are closed in this version (see the docstring);
v9 still passes:

```
== v9 contract with the patched checker
C5 boundary pair (11,3,12) repeater -> next (0,3,12) wire [allowed]
C6 lint tiled n=2: L1=0 L2=0 L3=48
measured n=3 rows=512: C2 through-entry mismatches=0, C3 carry mismatches=0 (final f mismatches=0), C5 local-table mismatches=0, non-converged/bistable rows=0
CONTRACT PASS: 0 FAIL, 3 notes
```
