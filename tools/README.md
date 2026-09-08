# tools/

> 日本語: [README.ja.md](README.ja.md)

Everything here is standard-library Python 3.11+. Run it from the repository root; the
`sys.path` lines resolve relative to each file, so no installation and no `PYTHONPATH` are
needed.

```
tools/llmgen/   the Bench and the rule machine
tools/checks/   sweeps, checkers, evaluators   (no external requirements)
tools/world/    synthetic world build + live world observation (needs software you supply)
```

## tools/llmgen — the Bench

| file | what it is |
|---|---|
| `machine.py` | the DC rule model: what each part reads, what it emits, how dust attenuates, which faces a gate sees, what counts as solid. Written from the 1.20.6 source. |
| `library.py` | the part table `machine.py` is indexed by. No imports. |
| `capcell.py` | `Bench` — loads a block list, solves it to a DC fixed point, reads any cell back. This is the oracle every checker in `tools/checks/` calls. |
| `cellref.py`, `cellsearch.py`, `gen.py`, `netlist.py`, `place.py`, `map.py` | the search and generation layers around the machine; present because `cell_to_world.py` imports them. |
| `cell_to_world.py`, `cell_to_program.py`, `litematic_writer.py` | translate a cell into world placements or into a placement program. |
| `test_capcell.py`, `test_strength.py` | unit tests: `cd tools/llmgen && python -m unittest test_capcell test_strength` |

The Bench is **calibrated**, not assumed correct: it was run against a pre-existing
reference circuit and its per-cell readings compared to the real world's. That circuit is
not part of this export.

## tools/checks — everything that needs no server

| file | usage |
|---|---|
| `bench_sweep.py LAYOUT` | full-adder sweep, 8 vectors. `ALL PASS` / `FAIL`. |
| `alu_check2.py LAYOUT [-v]` | ALU stage: 32 rows + placement lint `L1` (vanilla support), `L2` (diagonal dust reads), `L3` (informational). Writes `LAYOUT.rows.json` next to the layout. |
| `alu_check_slices.py LAYOUT [n] [-v]` | tiles the layout `n` times along its declared pitch and checks `n`-bit ADD/SUB/AND/OR. A layout is a slice only if `n = 1, 2, 3` all pass. |
| `check_alu_stage.py LAYOUT` | the older, simpler ALU stage check (used on the 30/32 predecessor). |
| `dc_eval.py NET`, `dc_eval_sub.py NET`, `dc_eval_alu.py NET` | evaluate a *network* (not a layout) directly from the algebra. Written independently of the Bench so that agreement means something. |
| `bench_sweep_feed.py`, `bench_sweep_feed2.py` | the same sweeps, but driving the circuit through physical feeders and lever states instead of pinned inputs — this is what makes the synthetic-world comparison apples-to-apples. |

## tools/world — needs software this repository does not ship

These drive a real Minecraft server. **You must supply:**

1. **A Minecraft 1.20.6 server jar.** Not distributed here. Put it in a server directory of
   your own with `eula.txt` accepted.
2. **A Java 21 runtime** on `PATH`.
3. **RCON enabled** in that server's `server.properties`, with the password in
   `rcon-password.txt` in the server directory.
4. The build scripts take that directory as `--template`; the default is the repo-relative
   `runtime/carpet-work`, which is **not** in this repository — point it at yours.

| file | what it does |
|---|---|
| `worldgen.py`, `_deps/tplgen.py`, `_deps/litematic_to_nbt.py` | write region files and `level.dat` directly. The only writer that can put an arbitrary block list into a fresh world. |
| `synthworld.py` | wraps the above into "block list in, playable void world out". |
| `worldprobe.py` | runs the server headless, freezes the tick loop, steps it, and reads every named cell back over RCON. Produces the `*.run.result.json` files in `artifacts/world/`. |
| `regioncap.py` | reads block states straight out of `.mca` region files, with no server running. Used to observe the operator's own world without touching it. |
| `build_world1.py`, `build_world2.py` | build the full-adder and ALU synthetic worlds. |
| `make_layout_world1.py`, `make_layout_world2.py` | derive the world layouts (stage + feeders) from the stage layouts. These need no server and reproduce the committed JSON byte-for-byte. |
| `build_rig1.py` | build and Bench-sweep the 5-lever feeder rig. Needs no server. |

`rcon.py` is a minimal RCON client (stdlib sockets).

## A note on dangling references

Docstrings in `tools/llmgen/` cite paths like `notes/2026-09-06-…`. Those are provenance
pointers into the private development repository and are not resolvable here. They are left
in place rather than stripped, because they record where a rule came from.

Absolute host paths, user names and session identifiers have been replaced with
`<host-path>`, `<user>`, `<session-id>` and `<dev-repo>` throughout, including inside the
recorded run metadata. The measured block data in `artifacts/world/*.json` is untouched.
