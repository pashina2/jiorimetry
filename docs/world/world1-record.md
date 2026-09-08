# WORLD-1 -- PLACE-1's full-adder stage in a fresh synthetic world

Worker agent (Opus), 2026-09-07. Non-canonical (`notes/**`). Question: does the
PLACE-1 stage, placed in a void headless 1.20.6 world with no player, produce
the same DC sum/cout levels as the Bench for all 8 input vectors?

Written in two passes: sections 1-4 (predictions) BEFORE the world ran, sections
5-9 after. Nothing above section 5 was edited afterwards.

## 1. What had to be added: physical feeders

The Bench sweep in `tools/checks/bench_sweep.py` PINS the three input
wires at power 0 or 5. A world has no pins, so the three inputs need a physical
source that delivers exactly 5 (or 0) into the wire cell from a lever, built
only from comparator / barrel / redstone block / wire / solid, and touching none
of the cells PLACE-1 marks MUST STAY AIR.

One feeder, three times (positions in the stage's own relative frame; y=0
supports, y=1 parts, y=2 the lever only):

| part | a | cin | b |
|---|---|---|---|
| gate (comparator, mode=compare) | (1,1,-1) facing=north | (3,1,-1) facing=north | (2,1,3) facing=south |
| its support | (1,0,-1) | (3,0,-1) | (2,0,3) |
| level-5 barrel at the gate's BACK, 494 stack-64 items | (1,1,-2) | (3,1,-2) | (2,1,4) |
| side wire the lever drives | (0,1,-1) | (4,1,-1) | (1,1,3) |
| its support | (0,0,-1) | (4,0,-1) | (1,0,3) |
| lever base (solid the wire reads) | (0,1,-2) | (4,1,-2) | (0,1,3) |
| lever, face=floor | (0,2,-2) | (4,2,-2) | (0,2,3) |

Mechanism. `facing=D` puts the BACK at pos+D and the OUTPUT at pos-D, so each
gate's output cell IS the input wire cell PLACE-1 named ((1,1,0) a, (3,1,0) cin,
(2,1,2) b) and its back is the barrel. A barrel holding 494 stack-64 items reads
as comparator level 5. In **compare** mode the gate emits its back level when
back >= side and 0 otherwise, so a side driven to 15 kills it:

* lever ON -> the lever's base solid is strongly powered 15 -> the side wire
  reads 15 -> 15 > 5 -> gate output **0** -> input bit **0**
* lever OFF -> side wire 0 -> 5 >= 0 -> gate output **5** -> input bit **1**

**INVERTED CONVENTION, declared: lever ON = input bit 0, lever OFF = input bit 1.**
The spec's drive values are lever positions, so regime `v_a1b0c1` carries
`lv_a=0, lv_b=1, lv_cin=0`.

Why a side wire and not the lever directly: a comparator SIDE reads only dust,
redstone blocks and gates pointing in -- a lever on the side is invisible to it
(PLACE-1 section 3 says the same). Each side wire is an isolated dot: it touches
its gate's side, its lever base, its support, and air. No wire-to-wire hop is
introduced anywhere, so PLACE-1's isolation property survives.

Cells used by the feeders, checked against PLACE-1's MUST STAY AIR list
(`(0,1,0) (0,1,2) (2,1,0) (1,1,2) (3,1,2) (4,1,0) (5,1,0) (5,1,2) (7,1,1)
(7,1,3) (5,1,5) (4,1,5) (7,1,2) (7,1,4) (6,1,5)` and `(2,1,-1)`): **none is
touched** -- asserted by the generator that wrote `layout_world1.json`, which
raises on any occupied must-air cell and on any coordinate collision. `(3,1,4)`
holds the optional sum readout wire, which PLACE-1 permits. The only y=2 cells
in the world are the three levers, all above feeder bases, none above a stage
relay or support.

The one new adjacency to the stage: the b feeder's barrel `(2,1,4)` sits beside
the sum readout wire `(3,1,4)`. A barrel with nothing powering it emits 0 and a
wire does not connect into a plain solid, so the readout still reads only
`S_sum` -- the same argument PLACE-1 already makes for the K5 barrel at (3,1,3).

Total: 35 stage blocks + 21 feeder blocks = **56 blocks**, 4 barrels of 494,
3 levers.

## 2. Bench prediction (run BEFORE the world)

`bench_sweep_feed.py layout_world1.json` -- same `capcell.Bench`, no pins at
all: the levers are set in the block states and `dc_solve()` resolves the
feeders and the stage together.

```
a=0 b=0 cin=0 | feed a/b/cin=0/0/0 in=0/0/0 | sum=0 cout=0 -> 00 | arith=True clean=True rounds=3 conv=True
a=0 b=0 cin=1 | feed a/b/cin=0/0/5 in=0/0/5 | sum=5 cout=0 -> 01 | arith=True clean=True rounds=4 conv=True
a=0 b=1 cin=0 | feed a/b/cin=0/5/0 in=0/5/0 | sum=5 cout=0 -> 01 | arith=True clean=True rounds=4 conv=True
a=0 b=1 cin=1 | feed a/b/cin=0/5/5 in=0/5/5 | sum=0 cout=5 -> 10 | arith=True clean=True rounds=5 conv=True
a=1 b=0 cin=0 | feed a/b/cin=5/0/0 in=5/0/0 | sum=5 cout=0 -> 01 | arith=True clean=True rounds=4 conv=True
a=1 b=0 cin=1 | feed a/b/cin=5/0/5 in=5/0/5 | sum=0 cout=5 -> 10 | arith=True clean=True rounds=5 conv=True
a=1 b=1 cin=0 | feed a/b/cin=5/5/0 in=5/5/0 | sum=0 cout=5 -> 10 | arith=True clean=True rounds=5 conv=True
a=1 b=1 cin=1 | feed a/b/cin=5/5/5 in=5/5/5 | sum=5 cout=5 -> 11 | arith=True clean=True rounds=5 conv=True
clean arithmetic rows 8/8
```

Every vector: both outputs land on exactly 0 or exactly 5, and
`2*cout + sum == a+b+cin`. The feeders reproduce the pinned result -- the same
8/8 that `docs/placement/place1.mdbench_sweep_output.txt` recorded with pins.

## 3. What the world is asked, and what a match means

`world1.spec.json`, driven by `tools/world/worldprobe.py run`:
`tick freeze`, set the three levers, step 1 gt at a time to `max_gt=40`, with
`settle_gt=10`.

15 read points. Four carry bits and fold into `final_value`:

| bit | read | position (world) | match |
|---|---|---|---|
| 0 | cout5 | 105 65 103 | `minecraft:redstone_wire[power=5]` |
| 1 | cout0 | 105 65 103 | `minecraft:redstone_wire[power=0]` |
| 2 | sum5  | 103 65 104 | `minecraft:redstone_wire[power=5]` |
| 3 | sum0  | 103 65 104 | `minecraft:redstone_wire[power=0]` |

Reading both `power=5` and `power=0` at each output means a third level shows up
as a reading (both bits 0), instead of being folded silently into "not 5".

Ten more reads take `powered` on every comparator (c1..c7 and the three
feeders); one `nbt` read takes `Items[7]` of the K5 barrel at (3,1,3), which is
where a wrongly written 494 would show. These carry no bit.

Predicted `final_value` per vector (bit0 cout5 | bit1 cout0 | bit2 sum5 | bit3 sum0):

| a b cin | Bench sum | Bench cout | levers (a,b,cin) | expected final_value |
|---|---|---|---|---|
| 0 0 0 | 0 | 0 | ON ON ON    | 10 |
| 0 0 1 | 5 | 0 | ON ON OFF   | 6 |
| 0 1 0 | 5 | 0 | ON OFF ON   | 6 |
| 0 1 1 | 0 | 5 | ON OFF OFF  | 9 |
| 1 0 0 | 5 | 0 | OFF ON ON   | 6 |
| 1 0 1 | 0 | 5 | OFF ON OFF  | 9 |
| 1 1 0 | 0 | 5 | OFF OFF ON  | 9 |
| 1 1 1 | 5 | 5 | OFF OFF OFF | 5 |

Comparator `powered` expectations are in the spec too, one per gate per vector,
taken from the Bench's `cmp_out > 0`.

## 4. The warm-up sweep, and why the run is 16 regimes and not 8

A world written straight into region files carries whatever states the writer
put in the palette, and no redstone update ever runs over it. Every comparator
loads `powered=false` with no block entity (output signal 0) and every wire
loads `power=0` -- a lie for c1..c3, whose backs are redstone blocks. A gate
recomputes only when a neighbour's block state changes, so a gate whose stale
state happens to equal the answer for the vector under test is never woken, and
one stale gate upstream poisons every reading downstream of it.

So the 8 vectors are driven **twice**: once as `warm_*` regimes whose readings
are recorded but not compared against the Bench, then once as `v_*`. The wake-up
is guaranteed by the vector where a first rises: c1's side changes, c1 goes
0 -> 10, and that cascade runs the length of the stage, so by the end of the
warm-up pass every gate has recomputed from live inputs at least once. No Bench
answer is written into the world -- the warm-up is lever flips only, and its
readings stay in the result file so the discarded pass is auditable.

Prediction for the warm-up pass itself: the early warm-up rows (before a first
rises) may read anything; the late ones should already agree with section 3.

Deviation from `synthworld.build_world`: it spells
`worldgen.build_region_files(placements, {}, version)`, so a world it writes can
hold no block entities, and this artifact is defined by four barrels holding 494
items. `build_world1.py` spells those four worldgen lines itself with the
block-entity map filled. Nothing under `tools/` is changed.

## 5. The world run

`tools/world/worldprobe.py run --spec artifacts/world/world1.spec.json`,
2026-09-07T14:20:03Z, template `<host-path> development runtime/carpet-work`,
rcon 25597, 13996 roundtrips of a 60000 limit, exit 0, `completed: true`.
Result: `world1.run.result.json` (untouched, `writer: worldprobe`,
`report_kind: bench_trace`, spec sha256 `ce105227...`), tables
`world1.run.tables.md`. The world is the void save built by `build_world1.py`
into the scratchpad: 56 blocks, 4 block entities, one region `r.0.0.mca`,
DataVersion 3839, no player, no terrain.

The barrel was read back through the probe, not assumed:

```
data get block 103 65 103 Items[7]
-> 103, 65, 103 has the following block data: {count: 46, Slot: 7b, id: "minecraft:cobblestone"}
```

7 x 64 + 46 = 494, in the 1.20.5+ item spelling (`count`, int), and the game
parsed it -- which is also what makes the three feeders emit 5 at all.

## 6. Table

Bench = section 2 (`bench_feed_rows.json`). World = `final_reads` of the `v_*`
regimes; `5` means `redstone_wire[power=5]` matched at that cell, `0` means
`power=0` matched. Neither matching would have read as `other`.

| a b cin | Bench sum | Bench cout | world sum | world cout | settle_gt | match |
|---|---|---|---|---|---|---|
| 0 0 0 | 0 | 0 | 0 | 0 | 8 | match |
| 0 0 1 | 5 | 0 | 5 | 0 | 10 | match |
| 0 1 0 | 5 | 0 | 5 | 0 | 2 | match |
| 0 1 1 | 0 | 5 | 0 | 5 | 8 | match |
| 1 0 0 | 5 | 0 | 5 | 0 | 8 | match |
| 1 0 1 | 0 | 5 | 0 | 5 | 8 | match |
| 1 1 0 | 0 | 5 | 0 | 5 | 2 | match |
| 1 1 1 | 5 | 5 | 5 | 5 | 10 | match |

**matches 8/8.**

Beyond the two outputs, the spec also carried a Bench expectation for `powered`
on all ten comparators (c1..c7 and the three feeders) in every vector:
**112 read comparisons over the 8 recorded vectors, 0 unequal.** So the
agreement is not only at the two output cells; every gate in the stage is in the
state the Bench put it in.

The 8 discarded `warm_*` rows came out with `final_bits` identical to their
`v_*` counterparts in all 8 vectors, i.e. the stale-load hazard section 4 was
built against did not in fact bite in this world -- the wake-up cascade had
already reached every gate during the first pass. The warm-up is kept in the
record as a guard that turned out not to be needed here, not as a correction.

## 7. Readings worth stating

* Settle. `settle_gt` (the first gt after which the 14 read predicates hold for
  10 gt) ranged 2..10, `last_change_gt` equal to it in all 16 regimes
  (`plateau: false` everywhere), and nothing was `truncated` at `max_gt=40`. The
  two rows at 2 are transitions where the previous vector already held the same
  output pair, e.g. `v_a0b1c0` moved once, at gt 2, and only in one comparator
  bit: `01101110111010 -> 01101110111001`. The longest, 10 gt, is the full chain
  e.g. `v_a1b1c1`: changes at gt 0, 2, 4 and 10.
* The reads are PREDICATES, not levels. A wire at power 10 reads 0 on both
  `power=5` and `power=0`, so intermediate levels inside the stage (Wu1/Wu2 run
  15/10/5/0) are invisible here by construction. That is deliberate -- the
  question was the DC output levels -- but it means these series are not a
  timing trace and must not be read as one.
* No timing claim is made. The run is DC: freeze, set levers, step, read.

## 8. Deviation from the layout

`layout_place1.json` was used verbatim: all 35 blocks (the 33-block stage plus
the optional sum readout wire at (3,1,4) and its support), same coordinates,
same states, same 494-item barrel at (3,1,3). `layout_world1.json` is that file
plus the 21 feeder blocks of section 1 and nothing else; the generator asserts
the must-stay-air list and coordinate uniqueness. The only non-layout choice
inside the stage's own bounding box is the b feeder's barrel at `(2,1,4)`, whose
adjacency to the readout wire is argued in section 1.

One tooling deviation, stated in section 4: `synthworld.build_world` cannot
write a world with block entities, so `build_world1.py` spells its four worldgen
lines itself with the barrel map filled in. `worldprobe.py` is used unmodified.
Nothing under `tools/` was changed.

## 9. Files

* `record.md` (this file)
* `layout_world1.json` -- stage + feeders + levers, relative frame
* `bench_sweep_feed.py` -- the pinned sweep extended to lever-driven feeders
* `bench_feed_rows.json` -- its 8 rows, incl. per-gate `cmp_out`
* `make_layout_world1.py` -- writes layout_world1.json from layout_place1.json
* `build_world1.py` -- void world + spec builder
* `world1.spec.json` -- the worldprobe spec (3 drives, 15 reads, 16 regimes)
* `world1.run.result.json`, `world1.run.tables.md` -- worldprobe output, untouched
