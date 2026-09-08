# SLICE-1 — the order (DIRECTOR 8 `0c3d10be`, 2026-09-07T22:5xZ)

> 日本語: [slice-contract.ja.md](slice-contract.ja.md)

The operator ruled that bit-slice construction, the abutment of one slice against another, and pitch alignment were not met, and that they must be met before proceeding to a second stage. `v7` works as one stage, but it is not a slice.

## The question (one)
Can ALU stage v7 (`artifacts/layouts/alu_stage_v7.json`, Bench 32/32) be rebuilt into a placement v8 that satisfies the **slice contract** below and that passes **n = 1 (32 rows) / n = 2 (128 rows) / n = 3 (512 rows), all of them**, under `tools/checks/alu_check_slices.py`?

## The slice contract (hard)
1. **The pitch is along +x, PX ≤ 12** (smaller is better). The slice box is x ∈ [0, PX−1], y ∈ [0, 2] (declare it if y=3 is used), z ∈ [0, Z], Z ≤ 13. **Not one cell may have x ≥ PX.**
2. **Through-lines (P, Wn)**: the entry is a wire cell at x=0, the exit is the cell at x=PX−1 with the same (y,z). The east neighbour of the exit, (PX,y,z), is the entry cell of the next slice itself (a wire→wire connection), so **inside each slice the exit level must be restored to 15 through a repeater** (P and Wn are 0/15 control lines; 0 stays 0). If a second entry for P is needed, it too must be a through-line or be derived inside the slice (do not power two places from outside).
3. **carry**: k = the wire cell (0, yk, zk). f = a comparator at (PX−1, yk, zk) facing west, whose front (PX, yk, zk) = the next slice's k cell. The level is exactly 0/3.
4. **Ports per slice**: a, b (inputs, one wire cell each) and r (output, one wire cell). Place them on the **south face (z = Z) or the top face (y=3)**. Do not place them on an x face. `a` is one cell (v7's distribution over 3 cells is to be copied inside the slice).
5. **Closure**: the cells of slice i touch the cells of slice i±1 only at the through-line exit→entry and at f→k. Wires and gates at x=0 / x=PX−1 do not couple with the cells beyond the boundary (beyond is either solid or air, or a gate not facing this way). The judgement is the n=2/3 Bench (the table of one slice does not change when a neighbouring slice is present).
6. The interference rules are the same as for v7 (`docs/rules/facts-dc-v2.md`, `docs/rules/facts-geometry.md`, `docs/rules/facts-vertical.md`, `docs/alu-place-handover.md` §4). The 6-face leak of a strongly powered solid, the diagonal read at y=2, no strongly powered solid next to a pin, and wire→wire is −1 (fatal for data).

## The given
- v7 and the PLACE-ALU-3 design (`docs/placement/placealu3-result.md`: S_x = max(a,W3) − a·[Wn=0], the P kill on the side of c5/c6, the shape of the dummy comparator), the node value table `node_values.txt`, and the network `artifacts/layouts/net_alu1.json`.
- The instruments: `tools/checks/alu_check_slices.py` (reads the layout's `slice` section = pitch / through / ports, lays out n copies and solves them), `tools/checks/alu_check2.py` (32 rows for one stage + lint L1/L2/L3; the lint can also be applied to a tiled n=2 layout = write `alu_check_slices.tiled(lay,2)` to JSON and run `lint`). Bench = `tools/llmgen/capcell.py`.
- What falls over when v7 is read against the contract (this seat's own measurement): `v7_as_slice.json` (pitch 11, `a` only at (10,1,4)) gives n=1 20/32, n=2 38/128. The 3 cells of `a`, P's second entry (0,1,8), the Wn row (x=4..8 only) and the parts at the east end (9..10) all violate the contract.

## What to return (`docs/placement/slice-contract.md`)
- `alu_slice_v8.json` (with a `slice` section) and `draft_<n>.json` (every 10 minutes).
- `slice1-result.md`: (1) the PASS lines for n=1/2/3 (printed verbatim), (2) the lint lines, (3) how each clause of the contract was satisfied (the route of the through-lines and the position of the repeaters, the copy of `a`, the f→k cells, the list of cells at x=0 / x=PX−1 and the cells beyond the boundary), (4) PX, the block count, the breakdown by part, (5) if it is not met, the last draft and the location of the collision, (6) the files opened, the time, the tokens.
The limit is 45 minutes. No web; referring to the operator's existing reference circuit is forbidden; do not touch world / aiwb / tools / git.
