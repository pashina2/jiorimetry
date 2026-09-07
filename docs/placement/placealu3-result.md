# PLACE-ALU-3 result (Fable worker, 2026-09-07T20:13Z–20:2xZ)

## 1. Checker output: `python alu_check2.py alu_stage_v7.json`

```
LINT L3 wire touches strongly-powered relay (5, 2, 7) relay (4, 2, 7) driven by (3, 2, 7)
LINT L3 wire touches strongly-powered relay (8, 1, 3) relay (7, 1, 3) driven by (6, 1, 3)
LINT L3 wire touches strongly-powered relay (8, 1, 3) relay (8, 1, 4) driven by (9, 1, 4)
LINT L3 wire touches strongly-powered relay (6, 2, 9) relay (5, 2, 9) driven by (5, 2, 8)
LINT L3 wire touches strongly-powered relay (6, 2, 9) relay (6, 2, 8) driven by (6, 2, 7)
LINT L3 wire touches strongly-powered relay (2, 2, 7) relay (2, 2, 6) driven by (2, 2, 5)
LINT L3 wire touches strongly-powered relay (8, 1, 5) relay (8, 1, 4) driven by (9, 1, 4)
LINT L3 wire touches strongly-powered relay (5, 2, 2) relay (5, 1, 2) driven by (5, 1, 1)
LINT L3 wire touches strongly-powered relay (3, 2, 5) relay (3, 1, 5) driven by (3, 1, 4)
PASS 32/32
```

L1 = 0, L2 = 0. Stop condition reached (32/32 + L1/L2 = 0). Of the 9 L3 lines, 7 are the intended read-outs already present in T6 (uplinks / r / w3p / w4b / S4). The two new ones are the AS relay (8,1,4) touching w3p (8,1,3) and a2 (8,1,5); both are harmless by value (see §3).

## 2. Design (two algebra swaps from the order's fact 4)

- **XOR leg = fact 4(b)**: S_x (6,1,5) = max(a, W3) (x1 (7,1,5) fE now a pure copy of a2, x2 (6,1,6) fS a pure copy of W3 — the copy gate (7,1,6) between them is removed so both sides read 0); xm (6,1,4) becomes **subtract** with side `as` = sub(a, [Wn]) = a·[Wn=0]. xm = max(a,W3) − as = a XOR W. This removes the need for `a` at (5,1,6) (fact 2), so the y=2 cluster is untouched.
- **P kill = fact 4(c)**: P now enters the side of c5 (4,2,5) and c6 (5,2,6) at the shared free cell (5,2,5) instead of c7's side. With P=15: c5 = 0 → c6 = 0 → c7 = 0, r = c4g = c4 as before. This lets the whole x=9 P line, the (7,1,1) bridge, the three lids and the (7,2,7) repeater go — which is what removed the L1 at (8,2,7) (wire on top of comparator W3b) and freed x=7..10, z=4..7 for the `as` gate.

### Cells changed vs `T6_with_pins.json` (all coordinates x,y,z)

Removed (17): (7,1,1) rep fN bridge; (7,2,2) w, (7,2,3) rep fN, (7,2,4) w, (8,2,4) w, (9,2,4..7) w, (8,2,7) w, (7,2,7) rep fE — the y=2 P line; (8,2,3) (8,2,5) (8,2,8) lids; (8,1,7) W3b comparator (+ its barrel (9,1,7) → now a wire); (7,1,6) copy gate; (7,1,7) W3 relay solid.

Added (11):
- P chain: (5,2,2) wire (on the dead-bridge solid (5,1,2), which (5,1,1) rep fN strongly powers = 15·[P]); (5,2,3) rep fN; (5,2,4) rep fN; (5,2,5) wire = P → side of c5 and c6; (5,1,5) smooth_stone (support of (5,2,5); unpowered).
- `as` leg: (10,1,4) wire = **new pin a3** (+ floor (10,0,4)); (9,1,8) wire (Wn, + floor (9,0,8)); (9,1,3) comparator fS compare = **dummy connector** (see §3) (+ floor (9,0,3)).

Changed (6):
- (6,1,4) xm: compare → **subtract** (back S_x, side (7,1,4)).
- (7,1,4) solid → comparator **fE compare** = relay gate: back (8,1,4) AS solid, front (6,1,4) xm side. (Its sides (7,1,3) = c3p relay solid and (7,1,5) = x1 gate facing away read 0.)
- (9,1,4) solid → comparator **fE subtract** = as' = sub(a3 (10,1,4), [Wn]); front (8,1,4) solid = AS relay. Sides: (9,1,3) dummy gate facing away (0), (9,1,5) rep facing it (Wn).
- (9,1,5) solid → repeater **fS**: back (9,1,6) Wn wire, front (9,1,4).
- (9,1,6), (9,1,7) → Wn wires: chain (8,1,8)=7 → (9,1,8)=6 → (9,1,7)=5 → (9,1,6)=4 (≥ 1 suffices for the repeater; the bench levels were read at Wn=15: (8,1,8) is 7 because the T6 Wn route already loses 8 along x=5..8, z=8..11).

Gate roles unchanged: everything north of z=4 west of x=8, the whole y=2 r cluster, Qg1 block, Wn column (4,1,6..10), W3a (6,1,8) fS + rep (7,1,8) fE, x1 (7,1,5), x2 (6,1,6), F, k.

## 3. Pins and reads

- pins: a = (4,1,4), (8,1,5), **(10,1,4) added** (a3, back of as'); b (0,1,4), k (0,1,2), P (0,1,0) (0,1,8), Wn (4,1,10) — unchanged. reads: r (6,2,9), f (8,1,2) — unchanged.
- Why a3: `as` needs `a` on a gate's back and Wn on its side; no cell adjacent to the existing a pins had a free side for Wn without polluting x1/w3p. In a real placement a3 is one more branch of the a bus (a2 and a3 are 2 cells apart across the gate; a wire between them would lose 1, so it must stay a separate branch or come from a copy gate).
- Fact 7 check (pin next to a strongly powered solid): a2 (8,1,5) touches the AS relay (8,1,4). In vanilla a2 would read max(a, as); since as = a·[Wn=0] ≤ a, a2 = a for all 32 rows — no function change. a3 (10,1,4) has no solid neighbours.
- w3p (8,1,3) also touches the AS relay: w3p = max(c3p, as); F = compare(3, [w3p, P]) = 3 iff max(c3p, as, P) ≤ 3, and as ≤ 3, so F is unchanged (this is the L3 line "(8,1,3) relay (8,1,4)").
- The dummy comparator (9,1,3) fS (back = as' gate facing away → 0, output 0 into air (9,1,2)) exists only to give w3p an east connection: a wire with a single connection (north to F) becomes a N–S line and powers the block on its south side (8,1,4) — the AS relay then read max(as, c3p) and the count fell to 24/32 with non-convergence (draft_2). With N+E connections the wire's south side is NONE and (8,1,4) carries as only. Any other connector at (9,1,3) that does not feed as' would do the same; a wire there is not allowed (as' side would read it).

## 4. Files opened, time, tokens

Opened: `PLACE-ALU-3-order.md`, `alu_check2.py`, `T6_with_pins.json`, `node_values.txt`, `../2026-09-08-placealu2/facts-dc-v2-given.md`, `../2026-09-07-place1/facts-geometry-given.md`, `../2026-09-08-vert/README.md`, `../2026-09-08-alu-place-handover.md` (§2 and §4 only, plus the `## ` header list), `../2026-09-08-alu1/net_alu1.json`. Not opened: `capcell.py`, `machine.py`, `bench_sweep.py` (imported by the checker only), anything from the operator's reference-circuit material, web.

Wall time: 20:13:34Z (first command) → 20:25:33Z (final check) ≈ 12 min; drafts `draft_1.json` (30/32, L1/L2 clean), `draft_2.json` (24/32, (7,1,4) facing fixed, AS relay polluted by w3p), `draft_3.json` (32/32 = `alu_stage_v7.json`).
Self-estimated tokens: ~75k input (mostly the file reads and my own reasoning), ~15k output.

## 5. Dead ends (for the record)

- `as` at (5,1,4) fE (back a (4,1,4)) needs Wn on (5,1,5): a wire there reads S_x; a gate there needs (5,1,6) strongly powered, and every cell that could power (5,1,6) is either the w4b support (5,1,7), the WnRep (3,1,6), or the x2 gate (6,1,6).
- Combining W3b and x2 into sub(K3,[Wn,a]) (fact 4a): every cell with `a` on one side and Wn on the other either shares the side cell with x1 (7,1,5) or with W3a; both then read the wrong value.
- AS relay at (8,1,4) without the (9,1,3) connector: w3p points south into it (draft_2, 24/32).

## 6. Not verified here

Bench only. Vanilla-specific points the reader should re-check in world: (a) the dummy comparator at (9,1,3) does change w3p's shape to N+E (vanilla `getDefaultWireState`), (b) a2 reads the AS relay (harmless by value), (c) the P chain repeaters (5,2,3)/(5,2,4) sit on (5,1,3)/(5,1,4), which are strongly powered relays of c2 / unpowered solid — repeaters do not read the block below, so no interaction.
