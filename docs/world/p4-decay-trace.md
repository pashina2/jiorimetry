# The new p4 "latch" is a slow decay, not a second fixed point (DIRECTOR 8 `0c3d10be`, 2026-09-08)

FEED-1 (section 7 of `record.md`) reported the re-solved `sol_p4_throughline.json` as latching in the world at T=0
(O stays 15) while the Bench finds a unique DC solution (O = 0) from cold, hot and sequential seeds, and left it as a
spec-vs-observation conflict. Two more world runs, both LLM-free (feed.py and a worldprobe spec), settle it.

## 1. Separation: feeder cell or artifact?

`job_p4sep.json` / `problems_p4sep.json`: the problem's fixed cells gain a `smooth_stone` at (0,1,0), the cell feed.py had
chosen for the T control feeder base, so feed.py must place the feeder elsewhere. Result (`out_p4sep/feed_p4sep.feed.md`,
copied): Bench 2/2, world rows 2, world FAIL 1, first counterexample `v_T0` read `O_0` expected true got false. The
behaviour does not depend on the feeder cell: it belongs to the artifact.

## 2. Trace: every loop cell, every gt (`p4_trace.spec.json`, `out_p4trace/p4_trace.run.result.json`)

Cells (world = layout + (100,64,100)): pin (0,1,1); the comparator (0,1,2) facing north (back = pin); its output wire
(0,1,3); the wire (1,1,3); the subtract comparator (1,1,2) facing south (back = (1,1,3)); its output relay (1,1,1),
which touches the pin; the tap wire (1,2,1) on the relay; O (7,1,1). Levels per gt after the lever goes OFF (`v_T0`):

```
gt  pin  w(0,1,3)  w(1,1,3)  w(1,2,1)  O
 0   14     15        14        14     15
 2   14     14        13        14     15
 4   13     14        13        13     15
 6   13     13        12        13     15
 8   12     13        12        12     15
10   12     12        11        12     15
12   11     12        11        11     15
13   11     12        11        11     15      (series continues; last_change_gt = 40, settle_gt = None)
```

The loop loses exactly one level per round (the wire hop (0,1,3) -> (1,1,3)), and a round costs 4 gt (two comparator
delays). From 14 that is 14 rounds = 56 gt, and the regime's `max_gt` is 40, so every run so far cut the regime while the
pin was still at ~5: `settle_gt=None`, `last_change_gt=40`. O stays 15 throughout because the through-line's repeaters
renormalise anything above 0. The old p4 (`sol_p4_throughline.latched.json`) is different: its loop has no wire hop, the
level never drops, and the Bench's hot seed finds the second fixed point (WORLD-4 section 7, FloorAndLatchTests).

## 3. What this settles, and what it opens

- The Bench's DC answer is right: the DC solution is unique and O = 0. The judge and the placer were not wrong on DC.
- The judge is blind to TIME. A transient of 56 gt on a "through-line" is a real defect for an instant circuit, and the
  second reviewer's point (a boundary contract needs a time condition, not only geometry and signal) is confirmed by
  measurement. Neither `placer0_check` nor `alu_check_contract` bounds the settle time.
- Consequence for the instruments (not yet done): add a settle-time clause. Cheapest form on the Bench: solve T=15,
  flip to T=0, `Bench.run_settle` with a limit (e.g. 20 gt), require the ticked state to reach the DC solution. In the
  world: `max_gt` must exceed the bound, and a regime that ends with `last_change_gt == max_gt` is truncated, never
  settled, and must not be compared as a final value.
- The counterexample is kept as `sol_p4_throughline.json` (DC-correct, 56 gt decay) beside the latched one.
## 4. The time clause, and the third p4 (2026-09-08T13:02Z)

Done after section 3 was written. `capcell.Bench` gained `set_floors` (an input vector changes behind floored pins,
with the synchronous settle a lever flip gets) and `settle_after` (step the ticked circuit until it rests or a bound
of gt passes; returns elapsed gt, rested, last change). `test_capcell.py` pins both cases on two rigs: the decaying
loop is not rested at 40 gt and rests at 0 by 120 gt; the true latch rests at once at the wrong value.

- `placer0_check.py`: after the DC pass, every ORDERED pair of pin vectors is driven on the Bench (DC-solve the
  source vector, then `settle_after` to the target); the target must rest within 40 gt at its expected outputs. The
  first version swept the vectors in one direction only and missed 15 -> 0; the pair form covers both directions.
  Results: p1/p2/p5/p6 pass with worst settles 6..10 gt; the decaying p4 fails at T 15 -> 0 (not rested at 40 gt,
  O = 15) - the same transition and value the world showed.
- `alu_check_contract.py` clause C7: the 128 rows of n=2 are driven forward and then backward on one bench (254
  transitions); r cells, the intermediate k and the top f must rest within 40 gt at the row's DC solution. v9: 254
  transitions, worst settle 26 gt, 0 failures; the whole contract still PASS.
- The placer, with this judge as its oracle, re-solved p4 in 1.2 s: 16 blocks, no loop (a barrel-backed subtract
  comparator chain instead), worst settle 8 gt (`sol_p4_throughline.json`; the decaying one is kept as
  `sol_p4_throughline.decay.json`, the latched one as `sol_p4_throughline.latched.json`).
- `feed.py` ran it in the world, prediction written first (Bench 2/2, world 2/2, both transitions rest within 8 gt):

```
| p4_throughline_v3 | placer0 | 2/2 | 2 | 0 | 12 | 0/12 | 8..8 (0 unsettled) | 68 | 3261 |
```

The judge (DC + two seeds + time), the placer and the world now agree on all three p4 solutions: latch (bistable),
slow decay (time), and the loop-free one (pass). `out_p4v3/` holds the feed.py outputs untouched.


