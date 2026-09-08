#!/usr/bin/env python3
"""tools/workbench/llmgen/capcell.py -- a CAPTURED artifact on the machine, a
band of it cut out as a CELL, the cell's gate table measured with its cut
faces held as open inputs, and the cell tiled back into an artifact.

SYN-2 (`notes/2026-09-07-syn2-comparator-technology-order.md`, OC-D97): the
extraction -> library -> generation loop, closed once on B-??. Until now
the only bridge from a bench capture to the machine lived in
`notes/2026-09-06-mb1/capture_to_machine.py` (MB-1, notes-side, patched
`machine`'s globals at import). This module is that bridge under test, with
three things MB-1 did not have:

  * no global patch. The two rules MB-1 added -- the observer
    (ObserverBlock.java) and the target's dust connection
    (TargetBlock.java:96-99 -> RedstoneWireBlock.connectsTo :380) -- are
    methods of `Bench`, a subclass. `machine.Machine` is untouched, so a
    process that also imports `place` or `gen` keeps the fabric's machine.
  * PINNED cells. A slice is cut from a larger artifact, and the cells on
    the far side of the cut keep powering it: a dust one layer up powers the
    wool under it (RedstoneWireBlock: strong power downward), a gate one
    layer down powers the wool a dust stands on. The neighbour layers are
    handed to the machine as blocks whose state is HELD (`pinned`): read by
    everything, updated by nothing. That is what "the cut face is an open
    input" means mechanically (`circuit-identification-by-calibrated-sweep`).
  * the captured connection props are the machine's, re-derived with the
    target rule (`placement_state_t`), never the rows' -- so a tiled copy
    whose top and bottom layers differ from the capture's gets the props its
    own geometry implies.

WHAT IS TRANSCRIBED, BY NAME (1.20.6-yarn):
  ObserverBlock :92-102   getStrongRedstonePower == getWeakRedstonePower ==
                          15 when POWERED and FACING == direction
  ObserverBlock :66-71    getStateForNeighborUpdate: a blockstate change of
                          the block in FACING, while not POWERED, schedules
  ObserverBlock :73-77    ...only when no tick is queued
  ObserverBlock :55-63    scheduledTick: not powered -> powered + schedule 2;
                          powered -> unpowered (a 2 gt pulse on the back)
  Blocks.java:913         observer = solidBlock(Blocks::never): never relays
  TargetBlock :96-99      emitsRedstonePower() -> true, so
  RedstoneWireBlock :380  connectsTo() connects a dust to it; its weak power
                          is its POWER (0 with no projectile), and it is a
                          full cube, so for relaying it IS a smooth stone
  WallBlock / TrapdoorBlock  NOT transcribed: a wall's post/side shape and a
                          trapdoor's open state are dropped (non-solid, no
                          redstone output -> exactly air to every redstone
                          read, MB-1 section 1.2). The wall-column 0-tick
                          pulse distribution B-?? uses (B-final-director
                          section 5) is therefore modelled ABSTRACTLY by
                          `Bench.prime`: the observers that face a wall are
                          booked in one gt in the order the post chain runs
                          (top to bottom), which is the only thing the wall
                          does to the redstone side.

The block-kind table `MAP` is MB-1's, row for row, with the same solidity
column cross-checked against GAP-7's `data/workbench/physics/solidity.json`
by `test_capcell.py`.

CLI: python tools/workbench/llmgen/capcell.py <tile|census> ...
"""

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import machine as M                                        # noqa: E402
from library import (DUST, COMPARATOR, REPEATER, LEVER, OBSERVER,     # noqa: E402
                     SMOOTH_STONE, OBSERVER_GT, HORIZONTAL)

TARGET = "minecraft:target"
BARREL = "minecraft:barrel"
WALL = "minecraft:stone_brick_wall"

#: How each captured block kind reaches the machine (MB-1 section 1.2):
#:   solid      -> smooth_stone (isSolidBlock true, emits nothing: same answers)
#:   drop       -> absent (isSolidBlock false, emits nothing: air's answers)
#:   keep       -> handed to the machine as itself
#:   container  -> handed as itself; its level comes from a declared block entity
#:   target     -> smooth_stone for solidity, PLUS the connectsTo rule (Bench)
#: The second column is GAP-7's `solid`, repeated so a reader can check.
MAP = {
    "minecraft:gray_wool":           ("solid", True, "Blocks.java:438 plain Block, full cube"),
    "minecraft:white_stained_glass": ("drop", False, "Blocks.java:569 solidBlock(Blocks::never)"),
    "minecraft:gray_stained_glass":  ("drop", False, "Blocks.java:576 solidBlock(Blocks::never)"),
    "minecraft:stone_brick_wall":    ("drop", False, "WallBlock: collision shape is not a full cube"),
    "minecraft:iron_trapdoor":       ("drop", False, "TrapdoorBlock: not a full cube in any state"),
    "minecraft:spruce_trapdoor":     ("drop", False, "TrapdoorBlock: not a full cube in any state"),
    "minecraft:powered_rail":        ("drop", False, "noCollision; no getWeakRedstonePower override"),
    "minecraft:activator_rail":      ("drop", False, "noCollision; no getWeakRedstonePower override"),
    "minecraft:target":              ("target", True, "full cube AND emitsRedstonePower (TargetBlock.java:96-99)"),
    "minecraft:barrel":              ("container", True, "full cube; hasComparatorOutput (BarrelBlock.java:89-97)"),
    "minecraft:redstone_wire":       ("keep", False, "machine rule"),
    "minecraft:comparator":          ("keep", False, "machine rule (D-2)"),
    "minecraft:repeater":            ("keep", False, "machine rule"),
    "minecraft:lever":               ("keep", False, "machine rule"),
    "minecraft:observer":            ("keep", False, "Bench rule (ObserverBlock.java)"),
}


class CapCellError(ValueError):
    """A capture, band or cell this module refuses, naming why."""


# ----------------------------------------------------------------- captures

def parse_block(spell):
    """`minecraft:foo[a=b,c=d]` -> ("minecraft:foo", {"a": "b", "c": "d"})."""
    if "[" not in spell:
        return spell, {}
    name, rest = spell.split("[", 1)
    if not rest.endswith("]"):
        raise CapCellError("unterminated block state: %r" % spell)
    props = {}
    for kv in rest[:-1].split(","):
        if not kv:
            continue
        k, sep, v = kv.partition("=")
        if not sep:
            raise CapCellError("block state property without '=': %r" % spell)
        props[k] = v
    return name, props


def spell(name, props):
    if not props:
        return name
    return name + "[" + ",".join("%s=%s" % (k, props[k]) for k in sorted(props)) + "]"


def cells_of(capture):
    """{(x, y, z): spelling} from `{scan: {non_air: [[x,y,z,spell], ...]}}`
    (the bench capture shape, also regioncap's)."""
    scan = capture.get("scan", capture)
    rows = scan.get("non_air")
    if not isinstance(rows, list):
        raise CapCellError("capture has no scan.non_air row list")
    return {(int(x), int(y), int(z)): s for x, y, z, s in rows}


def machine_blocks(cells):
    """cells -> ({pos: (name, props)} for the machine, {pos} of targets,
    report). Observers are handed through; `Bench` admits them."""
    blocks, targets = {}, set()
    report = {"dropped": {}, "solid": {}, "kept": {}, "container": {}, "target": 0}
    for pos, s in cells.items():
        name, props = parse_block(s)
        row = MAP.get(name)
        if row is None:
            raise CapCellError("no mapping row for %s at %r" % (name, pos))
        kind = row[0]
        if kind == "drop":
            report["dropped"][name] = report["dropped"].get(name, 0) + 1
        elif kind == "solid":
            report["solid"][name] = report["solid"].get(name, 0) + 1
            blocks[pos] = (SMOOTH_STONE, {})
        elif kind == "target":
            report["target"] += 1
            blocks[pos] = (SMOOTH_STONE, {})
            targets.add(pos)
        elif kind == "container":
            report["container"][name] = report["container"].get(name, 0) + 1
            blocks[pos] = (name, props)
        else:
            report["kept"][name] = report["kept"].get(name, 0) + 1
            blocks[pos] = (name, props)
    return blocks, targets, report


def barrel_entities(cells, counts, max_count=1):
    """Declared block entities for the barrels: `counts` maps a position (or
    "x,y,z") to the number of single-item stacks it holds. A barrel the
    caller did not count is left undeclared, and the machine then refuses
    the comparator that reads it rather than answering 0."""
    out = {}
    for key, n in counts.items():
        pos = M.parse_pos(key)
        if pos not in cells or parse_block(cells[pos])[0] != BARREL:
            raise CapCellError("no barrel at %r to declare" % (pos,))
        out[pos] = {"items": [{"count": 1, "max_count": max_count} for _ in range(int(n))]}
    return out


# ------------------------------------------------------------- connections

def connects_to_t(blocks, targets, pos, d):
    """RedstoneWireBlock.connectsTo :372-381 with the target's
    emitsRedstonePower (TargetBlock.java:96-99) added."""
    if pos in targets:
        return True
    return M.connects_to(blocks, pos, d)


def connection_t(blocks, targets, pos, d):
    """machine.connection with `connects_to_t`."""
    above_free = not M.is_solid(blocks, M.add(pos, "up"))
    n = M.add(pos, d)
    if above_free and M.is_solid(blocks, n) and blocks.get(M.add(n, "up"), (None,))[0] == DUST:
        return "up"
    if connects_to_t(blocks, targets, n, d):
        return "side"
    if not M.is_solid(blocks, n) and blocks.get(M.add(n, "down"), (None,))[0] == DUST:
        return "side"
    return "none"


def placement_state_t(blocks, targets, pos):
    """machine.placement_state with the target rule."""
    conn = {d: connection_t(blocks, targets, pos, d) for d in HORIZONTAL}
    if all(v == "none" for v in conn.values()):
        return conn
    ns_free = conn["north"] == "none" and conn["south"] == "none"
    ew_free = conn["east"] == "none" and conn["west"] == "none"
    out = dict(conn)
    if ns_free:
        for d in ("west", "east"):
            if conn[d] == "none":
                out[d] = "side"
    if ew_free:
        for d in ("north", "south"):
            if conn[d] == "none":
                out[d] = "side"
    return out


# ------------------------------------------------------------------- Bench

class Bench(M.Machine):
    """The machine plus the observer and target rules, `containers` (levels
    of cells OUTSIDE the capture that a gate reads: a calibrated parameter,
    never a silent zero), `pinned` cells whose state is held, and `floors`:
    dust cells that a source outside the capture drives to a level -- the
    cell reads max(its neighbours, the floor), so the circuit can raise it
    (a held pin cannot be raised, and a solution that feeds its own input
    back through a strongly powered block passes a held pin and latches in
    the world: WORLD-4 `v_p4_T0`, 2026-09-08)."""

    def __init__(self, blocks, targets=(), containers=None, block_entities=None,
                 pinned=(), pinned_signals=None, floors=None):
        observers = {p: v for p, v in blocks.items() if v[0] == OBSERVER}
        rest = {p: v for p, v in blocks.items() if v[0] != OBSERVER}
        self.containers = {tuple(k): int(v) for k, v in (containers or {}).items()}
        self.targets = set(targets)
        self.pinned = set(pinned)
        self.floors = {tuple(k): int(v) for k, v in (floors or {}).items()}
        M.Machine.__init__(self, rest, block_entities=block_entities)
        for pos, (name, props) in observers.items():
            self.blocks[pos] = (name, dict(props))
        # connection props: the artifact's own geometry, target rule included
        for pos, (name, props) in self.blocks.items():
            if name == DUST:
                props.update(placement_state_t(self.blocks, self.targets, pos))
        self._observers = [p for p in observers if p not in self.pinned]
        self._watch = {}
        for p in self._observers:
            self._watch.setdefault(M.add(p, self.blocks[p][1]["facing"]), []).append(p)
        self._seen = {p: self._state_key(p) for p in self._watch}
        # pinned cells are read by everything and updated by nothing
        self._dust = [p for p in self._dust if p not in self.pinned]
        self._parts = [p for p in self._parts if p not in self.pinned]
        self._lamps = [p for p in self._lamps if p not in self.pinned]
        self._near = {}
        self._dirty = set(self._dust)
        for pos, sig in (pinned_signals or {}).items():
            self.cmp_out[tuple(pos)] = sig

    # -- reads -------------------------------------------------------------
    def _state_key(self, pos):
        entry = self.blocks.get(pos)
        if entry is None:
            return None
        return (entry[0], tuple(sorted(entry[1].items())))

    def weak(self, e, d):
        entry = self.blocks.get(e)
        if entry is not None and entry[0] == OBSERVER:
            props = entry[1]
            return 15 if props["powered"] == "true" and props["facing"] == d else 0
        return M.Machine.weak(self, e, d)

    def strong(self, e, d):
        if self._name(e) == OBSERVER:
            return self.weak(e, d)
        return M.Machine.strong(self, e, d)

    def _emitted_side(self, e, d):
        if self._name(e) == OBSERVER:
            return self.strong(e, d)
        return M.Machine._emitted_side(self, e, d)

    def gate_back(self, pos):
        back = M.add(pos, self.blocks[pos][1]["facing"])
        if back in self.containers:
            return self.containers[back]
        return M.Machine.gate_back(self, pos)

    def dust_input(self, pos):
        value = M.Machine.dust_input(self, pos)
        floor = self.floors.get(pos)
        return value if floor is None else max(value, floor)

    # -- dynamics ----------------------------------------------------------
    def _settle_sync(self):
        M.Machine._settle_sync(self)
        self._observe_changes()

    def _observe_changes(self):
        for faced, watchers in self._watch.items():
            key = self._state_key(faced)
            if key == self._seen[faced]:
                continue
            self._seen[faced] = key
            for op in watchers:
                if self.blocks[op][1]["powered"] == "false" and op not in self.pending:
                    self.schedule(op, self.gt + OBSERVER_GT, M.PRIORITY_NORMAL)

    def _fire(self, pos):
        name, props = self.blocks[pos]
        if name != OBSERVER:
            return M.Machine._fire(self, pos)
        self._dirty.update(self._dust_near(pos))
        if props["powered"] == "true":
            props["powered"] = "false"
        else:
            props["powered"] = "true"
            self.schedule(pos, self.gt + OBSERVER_GT, M.PRIORITY_NORMAL)
        return None

    def prime(self, observers):
        """The wall column's one-gt pulse distribution, abstracted: book the
        given observers NOW, in the given order (B-final-director section 6:
        the post chain runs top to bottom in one setBlockState chain, and the
        observers along it are queued in that order -- OrderedTick fires them
        by subTickOrder). Only the ObserverBlock :66-77 conditions apply:
        not POWERED, not already queued. Returns how many were booked."""
        n = 0
        for op in observers:
            if self.blocks[op][1]["powered"] == "false" and op not in self.pending:
                self.schedule(op, self.gt + OBSERVER_GT, M.PRIORITY_NORMAL)
                n += 1
        return n

    def dc_solve(self, limit=200, seed=None):
        """The tickless fixpoint (MB-1): dust to its fixpoint, every gate's
        stored signal and POWERED set to what its inputs say, repeated until
        nothing moves; then the schedule is emptied and the observers'
        memory re-seeded. A circuit with feedback may have more than one DC
        solution; this returns the one the iteration walks to from the
        current state, or from the all-on state when `seed="hot"` (every
        unpinned dust 15, every gate powered, every torch out, every lamp
        lit). `dc_solve_both` runs cold and hot and reports the cells on
        which the two solutions differ."""
        if seed == "hot":
            self._seed_hot()
        elif seed is not None:
            raise M.MachineError("unknown seed %r" % (seed,))
        rounds = 0
        for rounds in range(1, limit + 1):
            self._dirty = set(self._dust)
            M.Machine._settle_sync(self)
            changed = False
            for pos in self._parts:
                name, props = self.blocks[pos]
                if name == COMPARATOR:
                    value = self.cmp_output(pos)
                    if value != self.cmp_out[pos]:
                        self.cmp_out[pos] = value
                        changed = True
                    want = "true" if self.cmp_has_power(pos) else "false"
                    if want != props["powered"]:
                        props["powered"] = want
                        changed = True
                elif name == REPEATER:
                    want = "true" if self.repeater_has_power(pos) else "false"
                    if want != props["powered"]:
                        props["powered"] = want
                        changed = True
                elif name in (M.TORCH, M.WALL_TORCH):
                    want = "false" if self.torch_should_unpower(pos) else "true"
                    if want != props["lit"]:
                        props["lit"] = want
                        changed = True
                elif name == M.LAMP:
                    want = "true" if self.lamp_receiving(pos) else "false"
                    if want != props["lit"]:
                        props["lit"] = want
                        changed = True
            if not changed:
                break
        else:
            self._reseed()
            return rounds, False
        self._reseed()
        return rounds, True

    def _reseed(self):
        self.pending.clear()
        self._dirty = set()
        self._seen = {p: self._state_key(p) for p in self._watch}

    def _seed_hot(self):
        for pos in self._dust:
            self.blocks[pos][1]["power"] = "15"
        for pos in self._parts:
            name, props = self.blocks[pos]
            if name == COMPARATOR:
                props["powered"] = "true"
                self.cmp_out[pos] = 15
            elif name == REPEATER:
                props["powered"] = "true"
            elif name in (M.TORCH, M.WALL_TORCH):
                props["lit"] = "false"
        for pos in self._lamps:
            self.blocks[pos][1]["lit"] = "true"
        self._dirty = set(self._dust)

    def _snapshot(self):
        out = {}
        for pos, (name, props) in self.blocks.items():
            if name == DUST:
                out[pos] = ("power", props["power"])
            elif name == COMPARATOR:
                out[pos] = ("powered", props["powered"], self.cmp_out.get(pos))
            elif name in (REPEATER, OBSERVER, LEVER):
                out[pos] = ("powered", props["powered"])
            elif name in (M.TORCH, M.WALL_TORCH, M.LAMP):
                out[pos] = ("lit", props["lit"])
        return out

    def _restore(self, snap):
        for pos, rec in snap.items():
            props = self.blocks[pos][1]
            props[rec[0]] = rec[1]
            if len(rec) == 3:
                self.cmp_out[pos] = rec[2]
        self._reseed()

    def dc_solve_both(self, limit=200):
        """Cold solve, then hot solve; returns (rounds_cold, conv_cold,
        conv_hot, diff) where diff = {pos: (cold, hot)} over every cell whose
        DC state differs between the two. An empty diff is the evidence that
        the DC solution is unique on this bench (two seeds, not a proof). The
        bench is left in the COLD solution."""
        rounds, conv = self.dc_solve(limit)
        cold = self._snapshot()
        _, conv_hot = self.dc_solve(limit, seed="hot")
        hot = self._snapshot()
        diff = {p: (cold[p], hot[p]) for p in cold if cold[p] != hot[p]}
        self._restore(cold)
        return rounds, conv, conv_hot, diff

    def set_levers(self, values):
        """{pos: bool}, one settle for the lot (a vector is one edit)."""
        for pos, on in values.items():
            name, props = self.blocks[pos]
            if name != LEVER:
                raise M.MachineError("%r is %s, not a lever" % (pos, name))
            props["powered"] = "true" if on else "false"
            self._dirty.update(self._dust_near(pos))
        self.settle()

    def run_settle(self, watch, limit=400):
        """Step until nothing is scheduled. Returns (gt, rested, last change
        gt of the watched dust powers)."""
        seen = self.dust_powers(watch)
        last = 0
        for _ in range(limit):
            if not self.pending:
                return self.gt, True, last
            self.step()
            now = self.dust_powers(watch)
            if now != seen:
                last, seen = self.gt, now
        return self.gt, False, last

    def dust_powers(self, positions):
        return tuple(int(self.blocks[p][1]["power"]) if self.blocks.get(p, (None,))[0] == DUST else -1
                     for p in positions)

    def layer_state(self, positions):
        """{pos: state} for pinning: a dust's power, a gate's powered and
        stored signal, an observer's powered."""
        out = {}
        for p in positions:
            entry = self.blocks.get(p)
            if entry is None:
                continue
            name, props = entry
            if name == DUST:
                out[p] = {"power": props["power"]}
            elif name == COMPARATOR:
                out[p] = {"powered": props["powered"], "signal": self.cmp_out[p]}
            elif name in (REPEATER, OBSERVER, LEVER):
                out[p] = {"powered": props["powered"]}
        return out


def bench_of(cells, block_entities=None, containers=None, pinned=(), pinned_state=None):
    """cells (+ declared barrels, cut-face levels, pinned positions with
    their held state) -> a Bench at the capture's own state (not yet
    DC-solved)."""
    blocks, targets, _report = machine_blocks(cells)
    signals = {}
    for pos, st in (pinned_state or {}).items():
        pos = tuple(pos)
        if pos not in blocks:
            continue
        name, props = blocks[pos]
        if name == DUST and "power" in st:
            props["power"] = str(st["power"])
        elif "powered" in st:
            props["powered"] = st["powered"]
        if name == COMPARATOR and "signal" in st:
            signals[pos] = st["signal"]
    return Bench(blocks, targets=targets, containers=containers, block_entities=block_entities,
                 pinned=pinned, pinned_signals=signals)


# ------------------------------------------------------------------- slices

def band(cells, y0, y1):
    return {p: s for p, s in cells.items() if y0 <= p[1] <= y1}


def neighbour_layers(cells, y0, y1):
    return {p: s for p, s in cells.items() if p[1] in (y0 - 1, y1 + 1)}


def shift(cells, dx=0, dy=0, dz=0):
    return {(p[0] + dx, p[1] + dy, p[2] + dz): s for p, s in cells.items()}


def tile(cell_cells, y0, y1, n, top_y):
    """`n` copies of the band `y0..y1`, stacked DOWNWARD from `top_y` at the
    band's own height: copy k occupies y = top_y - k*h - (h-1) .. top_y - k*h
    (h = y1 - y0 + 1). Copy 0 is the top. Refuses an overlap."""
    h = y1 - y0 + 1
    out = {}
    for k in range(n):
        dy = (top_y - k * h) - y1
        for p, s in cell_cells.items():
            q = (p[0], p[1] + dy, p[2])
            if q in out:
                raise CapCellError("tile overlap at %r" % (q,))
            out[q] = s
    return out


def identity(reference, observed):
    """regioncap's selftest vocabulary over two cell maps: identical /
    property_diff / id_diff / only_reference / only_observed."""
    same = prop = idd = 0
    only_ref = [p for p in reference if p not in observed]
    only_obs = [p for p in observed if p not in reference]
    for p, s in reference.items():
        t = observed.get(p)
        if t is None:
            continue
        if s == t:
            same += 1
        elif parse_block(s)[0] == parse_block(t)[0]:
            prop += 1
        else:
            idd += 1
    return {"reference": len(reference), "observed": len(observed), "identical": same,
            "property_diff": prop, "id_diff": idd,
            "only_reference": len(only_ref), "only_observed": len(only_obs),
            "identity": not only_ref and not only_obs and prop == 0 and idd == 0}


def census(cells):
    out = {}
    for s in cells.values():
        k = parse_block(s)[0].split(":", 1)[1]
        out[k] = out.get(k, 0) + 1
    return dict(sorted(out.items()))


def bbox(cells):
    xs = [p[0] for p in cells]
    ys = [p[1] for p in cells]
    zs = [p[2] for p in cells]
    return {"min": [min(xs), min(ys), min(zs)], "max": [max(xs), max(ys), max(zs)],
            "volume": (max(xs) - min(xs) + 1) * (max(ys) - min(ys) + 1) * (max(zs) - min(zs) + 1)}


# ------------------------------------------------------------- cell document

def cell_doc(name, cell_cells, y0, y1, ports, gate_table, source, notes=None):
    """The library-cell document (`llmgen.capcell.v0`): the blocks of the
    band in the capture's own frame, its ports, the measured gate table and
    the attribution `source` (frame `notes/2026-09-06-metrics-frame.md`
    section 2: technique / design / tool are separate lines)."""
    return {"kind": "llmgen.capcell.v0", "name": name,
            "source": dict(source),
            "band": {"y0": y0, "y1": y1, "height": y1 - y0 + 1},
            "bbox": bbox(cell_cells), "cells": len(cell_cells),
            "census": census(cell_cells),
            "ports": ports, "gate_table": gate_table,
            "blocks": [[p[0], p[1], p[2], cell_cells[p]] for p in sorted(cell_cells)],
            "notes": notes or []}


def cells_of_doc(doc):
    return {(int(x), int(y), int(z)): s for x, y, z, s in doc["blocks"]}


def dumps(doc):
    return json.dumps(doc, indent=1, sort_keys=True) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("tile", help="stack a cell document n times and write the cells")
    t.add_argument("--cell", required=True, type=Path)
    t.add_argument("--n", type=int, required=True)
    t.add_argument("--top-y", type=int, required=True)
    t.add_argument("--out", required=True, type=Path)
    c = sub.add_parser("census", help="block census and bbox of a capture")
    c.add_argument("--capture", required=True, type=Path)
    args = ap.parse_args(argv)
    if args.cmd == "tile":
        doc = json.loads(args.cell.read_bytes().decode("utf-8"))
        cells = tile(cells_of_doc(doc), doc["band"]["y0"], doc["band"]["y1"], args.n, args.top_y)
        payload = {"kind": "llmgen.capcell.tile.v0", "cell": doc["name"], "n": args.n,
                   "top_y": args.top_y, "cells": len(cells), "census": census(cells),
                   "bbox": bbox(cells),
                   "scan": {"non_air": [[p[0], p[1], p[2], cells[p]] for p in sorted(cells)]}}
        args.out.write_bytes(dumps(payload).encode("utf-8"))
        print("tiled %d x %s -> %d cells, bbox %s" % (args.n, doc["name"], len(cells), payload["bbox"]))
        return 0
    cells = cells_of(json.loads(args.capture.read_bytes().decode("utf-8")))
    print(json.dumps({"cells": len(cells), "census": census(cells), "bbox": bbox(cells)}, indent=1))
    return 0


if __name__ == "__main__":
    # cp932: stdout is strict by default and one unencodable
    # character costs the whole run. Why `errors=` and not
    # `encoding=`: tools/test_console_encoding.py.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(errors="backslashreplace")
    raise SystemExit(main())
