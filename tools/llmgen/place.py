#!/usr/bin/env python3
"""tools/llmgen/place.py -- netlist -> blocks on the two-layer
Manhattan fabric, audited, with the rest state computed by the machine.

DESIGN section 4 (fabric) and 8.4 (dense option, I7). The fabric is a
two-layer PCB: horizontal tracks at y=2 (one row per input port and per
gate, pitch ROW_PITCH along z), vertical tracks at y=4 on y=3 supports
(columns at x = 0 mod COL_PITCH), and a 'dip' wherever a vertical track has
to join a horizontal one -- the V-track comes down to the row cell through
a diagonal step on each side and climbs back, which is the only
crossing-free junction plain dust has. A vertical track that merely
CROSSES a row stays at y=4 with its support directly above the row dust:
two blocks apart, and the support block cuts the row dust's upward
diagonal (RedstoneWireBlock.java:200-201) while conducting nothing to it
(:252-254, wiresGivePower=false).

Every gate is a ROW whose shape is its kind's, and every fanin is a PIN
with a landing mode (D-2):

    diode   V column west of the gate, repeater at z-/+1 onto the row's
            OR-dust (D-1's NOR input; the or_merge's inputs)
    direct  V column dips onto the row; the row dust IS the net and runs
            east into the cell (a NOT; a comparator's back, through the
            strength-15 repeater at xb-1)
    side    V column AT the gate's own x, repeater at z-1 whose front is
            the comparator itself (its side pin, strength 15)
    face    V column at the gate's own x, dust at z-1 pointing into B
            (dense fabric: B's north face, no diode)

Row shapes, west to east on the gate's z:
    nor / not   [OR-dust or the input's dust] [B smooth stone] [wall torch
                east] [output dust ... lamp when primary output]
    cmp_sub     [back dust] [repeater west] [comparator west, subtract]
                [output dust ...]
    or_merge    [OR-dust from the westmost diode to the last junction ...]

Columns are handed out by the left-edge rule over z-intervals (two nets
share a column only when their intervals are COL_GAP apart); the x of a
level is fixed AFTER its inputs' columns are known, so every input column
lies west of its gate and every output column east of its driver by
construction. A gate whose pins need its own column (side / face) gets its
own x within the level, so two such gates never fight over one column.

`audit()` then checks what construction promised (I1 support, I2/I3 one
net per dust component, I4 dust run <= 15, no foreign dust on a torch
face, I7 nothing but the pin's net on a comparator's back / sides and on
B's north and south faces) and refuses with the cell named. Nothing in
this module carries a coordinate that came from a human: the geometry is
a function of the netlist. The sparse NOR geometry is D-1's, byte for
byte (pinned by test against the D-1 half adder fixture).
"""

import json

import library
from library import (DUST, REPEATER, COMPARATOR, WALL_TORCH, LAMP, SMOOTH_STONE, LEVER,
                     POWERED_RAIL, OBSERVER, REDSTONE_BLOCK, IDIOMS,
                     FACES, HORIZONTAL, OPPOSITE, DUST_MAX_RUN)
from machine import Machine, add, connection, placement_state
import netlist as nl

ROW_PITCH = 6
COL_PITCH = 4
COL_GAP = 3          # z cells kept free between two nets on one column
RUN_RESET = 9        # dust cells after which an inline repeater is placed (I4)
Y_ROW, Y_RAMP, Y_V = 2, 3, 4
FABRICS = ("sparse", "dense")


class PlaceError(ValueError):
    """A placement this module refuses, naming the cell."""


def _ceil_col(x):
    """Smallest column (multiple of COL_PITCH) that is >= x."""
    return ((x + COL_PITCH - 1) // COL_PITCH) * COL_PITCH


class Placement:
    def __init__(self):
        self.blocks = {}      # pos -> (block, props)
        self.net_of = {}      # dust / repeater pos -> net name
        self.ports = {"in": [], "out": []}
        self.segments = []    # disclosure: every vertical segment placed
        self.rows = {}        # row owner -> z
        self.gate_x = {}      # gate id -> X_B (or the comparator's x)
        self.edge_repeaters = {}   # (net, gate) -> repeaters on that fanin path
        self.cells = {}       # pos of B / comparator -> gate id
        self.pins = {}        # gate id -> [{net, mode, col}]
        self.fabric = "sparse"

    def put(self, pos, block, props=None, net=None):
        if pos in self.blocks:
            raise PlaceError(f"cell {pos} placed twice ({self.blocks[pos][0]} then {block})")
        self.blocks[pos] = (block, dict(props or {}))
        if net is not None:
            self.net_of[pos] = net


def _support(pl, pos):
    below = (pos[0], pos[1] - 1, pos[2])
    if below not in pl.blocks:
        pl.put(below, SMOOTH_STONE)


def _dust(pl, pos, net):
    pl.put(pos, DUST, {"power": "0"}, net)
    _support(pl, pos)


def _rep(pl, pos, facing, net):
    pl.put(pos, REPEATER, {"delay": "1", "facing": facing, "locked": "false", "powered": "false"}, net)
    _support(pl, pos)


def gate_kind(g):
    kind = g.get("kind", "nor")
    return "not" if kind == "nor" and len(g["fanin"]) == 1 else kind


def plan_pins(g, fabric):
    """The landing mode of every fanin (DESIGN 8.4)."""
    kind, fan = gate_kind(g), list(g["fanin"])
    if kind == "cmp_sub":
        return [{"net": fan[0], "mode": "direct"}, {"net": fan[1], "mode": "side"}]
    if kind == "cmp_inv":
        # SYN-2: the back is a redstone block (15), the input is the side pin
        return [{"net": fan[0], "mode": "side"}]
    if kind in ("or_merge", "dust_max"):
        return [{"net": n, "mode": "diode"} for n in fan]
    if kind == "not":
        return [{"net": fan[0], "mode": "direct"}]
    if fabric == "dense":
        pins = [{"net": fan[0], "mode": "face"}]
        rest = fan[1:]
        if len(rest) == 1:
            pins.append({"net": rest[0], "mode": "direct"})
        else:
            pins += [{"net": n, "mode": "diode"} for n in rest]
        return pins
    return [{"net": n, "mode": "diode"} for n in fan]


def place(netlist, fabric="sparse"):
    """netlist -> Placement (DESIGN section 4 / 8.4)."""
    if fabric not in FABRICS:
        raise PlaceError(f"unknown fabric {fabric!r} (have {FABRICS})")
    lv = nl.levels(netlist)
    gates = {g["out"]: g for g in netlist["gates"]}
    inputs = list(netlist["inputs"])
    outputs = dict(netlist["outputs"])
    pl = Placement()
    pl.fabric = fabric

    # rows: inputs first, then gates by (level, id)
    order = list(inputs) + sorted(gates, key=lambda n: (lv[n], n))
    for r, owner in enumerate(order):
        pl.rows[owner] = ROW_PITCH * r

    x_out = {name: 0 for name in inputs}        # first output dust cell of a driver
    columns = {}                                 # col -> [(zlo, zhi, net)]
    segs = []                                    # (net, gate, col, mode, zd, zs)
    max_level = max(lv.values()) if lv else 0
    prev_x = 0

    def interval(mode, zd, zs):
        if zd < zs:
            return zd, {"direct": zs, "diode": zs - 2, "side": zs - 2, "face": zs - 1}[mode]
        return {"direct": zs, "diode": zs + 2, "side": zs + 2, "face": zs + 1}[mode], zd

    def free(col, zlo, zhi, taken):
        return col not in taken and all(hi + COL_GAP < zlo or zhi + COL_GAP < lo
                                        for lo, hi, _n in columns.get(col, []))

    for level in range(1, max_level + 1):
        level_gates = [n for n in order if n in gates and lv[n] == level]
        used = []
        deferred = []
        for gname in level_gates:
            pins = plan_pins(gates[gname], fabric)
            pl.pins[gname] = pins
            taken_here = set()
            for pin in pins:
                net, mode = pin["net"], pin["mode"]
                zd, zs = pl.rows[net], pl.rows[gname]
                if mode in ("side", "face"):
                    if zd > zs:
                        raise PlaceError(f"pin {net}->{gname} lands from the south; the fabric orders rows by level")
                    deferred.append((gname, pin))
                    continue
                zlo, zhi = interval(mode, zd, zs)
                col = _ceil_col(x_out[net] + 1)
                while not free(col, zlo, zhi, taken_here):
                    col += COL_PITCH
                columns.setdefault(col, []).append((zlo, zhi, net))
                taken_here.add(col)
                used.append(col)
                pin["col"] = col
                segs.append((net, gname, col, mode, zd, zs))
        xb = _ceil_col(max(used + [prev_x + COL_PITCH]) + 1)
        own = 0
        level_x_out = []
        for gname in level_gates:
            kind = gate_kind(gates[gname])
            pins = pl.pins[gname]
            if any(p["mode"] in ("side", "face") for p in pins):
                x = xb + COL_PITCH * own
                own += 1
            else:
                x = xb
            if kind in ("or_merge", "dust_max"):
                cols = [p["col"] for p in pins]
                pl.gate_x[gname] = max(cols)
                x_out[gname] = max(cols) + 1
            else:
                pl.gate_x[gname] = x
                x_out[gname] = x + (1 if kind in ("cmp_sub", "cmp_inv") else 2)
            level_x_out.append(x_out[gname])
        for gname, pin in deferred:
            net, mode = pin["net"], pin["mode"]
            zd, zs = pl.rows[net], pl.rows[gname]
            zlo, zhi = interval(mode, zd, zs)
            col = pl.gate_x[gname]
            if not free(col, zlo, zhi, set()):
                raise PlaceError(f"column {col} for the {mode} pin {net}->{gname} is taken on z {zlo}..{zhi}")
            columns.setdefault(col, []).append((zlo, zhi, net))
            pin["col"] = col
            segs.append((net, gname, col, mode, zd, zs))
        prev_x = max(level_x_out + [prev_x])

    # horizontal extent of every driver: max junction column, and the lamp
    x_end = {}
    for net in order:
        cols = [s[2] for s in segs if s[0] == net]
        x_end[net] = max(cols + [x_out[net]])
        if cols and net in outputs.values():
            x_end[net] = max(x_end[net], max(cols) + 1)

    # --- horizontal tracks. A track carries an inline repeater (facing
    # west: input from the west) whenever the dust run since the last source
    # reaches RUN_RESET, never on a junction / landing column and never on
    # the last cell (I4 by construction). `run0` carries a run in from a
    # landing so a NOT's row continues the count of its input path.
    junctions = {}
    for net, gname, col, mode, zd, zs in segs:
        junctions.setdefault(net, set()).add(col)
    h_run = {}            # (label, x) -> dust cells since the last source at x
    reps_at = {}          # label -> [x of inline repeaters on that track]

    def h_track(label, x0, x1, z, keep, run0=0):
        run = run0
        for x in range(x0, x1 + 1):
            if run >= RUN_RESET and x not in keep and x != x1:
                _rep(pl, (x, Y_ROW, z), "west", label)
                reps_at.setdefault(label, []).append(x)
                run = 0
                continue
            _dust(pl, (x, Y_ROW, z), label)
            h_run[(label, x)] = run
            run += 1

    # (1) driver tracks: input rows, and every gate's cell + output track
    for name in inputs:
        h_track(name, 0, x_end[name], pl.rows[name], junctions.get(name, ()))
        pl.ports["in"].append((0, Y_ROW, pl.rows[name]))
    for gname in order:
        if gname not in gates:
            continue
        z, xb, kind = pl.rows[gname], pl.gate_x[gname], gate_kind(gates[gname])
        if kind in ("nor", "not"):
            pl.put((xb, Y_ROW, z), SMOOTH_STONE)
            pl.cells[(xb, Y_ROW, z)] = gname
            pl.put((xb + 1, Y_ROW, z), WALL_TORCH, {"facing": "east", "lit": "true"})
            h_track(gname, xb + 2, x_end[gname], z, junctions.get(gname, ()))
        elif kind == "cmp_sub":
            _rep(pl, (xb - 1, Y_ROW, z), "west", gates[gname]["fanin"][0])
            pl.put((xb, Y_ROW, z), COMPARATOR, {"facing": "west", "mode": "subtract", "powered": "false"})
            _support(pl, (xb, Y_ROW, z))
            pl.cells[(xb, Y_ROW, z)] = gname
            h_track(gname, xb + 1, x_end[gname], z, junctions.get(gname, ()))
        elif kind == "cmp_inv":
            # [redstone block] [comparator west, subtract] [output dust ...]:
            # RedstoneBlock.java:26-34 gives the back 15, the side pin's
            # repeater lands at z-1 (same as cmp_sub's side)
            pl.put((xb - 1, Y_ROW, z), REDSTONE_BLOCK)
            pl.put((xb, Y_ROW, z), COMPARATOR, {"facing": "west", "mode": "subtract", "powered": "false"})
            _support(pl, (xb, Y_ROW, z))
            pl.cells[(xb, Y_ROW, z)] = gname
            h_track(gname, xb + 1, x_end[gname], z, junctions.get(gname, ()))
        elif kind in ("or_merge", "dust_max"):
            cols = {p["col"] for p in pl.pins[gname]}
            h_track(gname, min(cols), x_end[gname], z, cols | junctions.get(gname, set()))
        else:
            raise PlaceError(f"no row shape for gate kind {kind!r} ({gname})")
    for oname, net in outputs.items():
        lamp = (x_end[net] + 1, Y_ROW, pl.rows[net])
        pl.put(lamp, LAMP, {"lit": "false"})
        pl.ports["out"].append(lamp)

    # (2) vertical segments, with inline repeaters on the y=4 run by the
    # same RUN_RESET rule (a ramp cell can never host one: a slope joins
    # dust to dust only).
    edge_repeaters = {}   # (net, gate) -> repeaters on the path incl. the diode
    landing_run = {}      # (net, gate) -> run carried onto the sink row
    for net, gname, col, mode, zd, zs in segs:
        step = 1 if zd < zs else -1
        facing = "north" if step > 0 else "south"      # input side of the V run
        run = h_run[(net, col)] + 1
        reps = len([x for x in reps_at.get(net, []) if x < col])
        pl.put((col, Y_ROW, zd + step), SMOOTH_STONE)
        pl.put((col, Y_RAMP, zd + step), DUST, {"power": "0"}, net)
        run += 1
        if mode == "direct":
            pl.put((col, Y_ROW, zs - step), SMOOTH_STONE)
            pl.put((col, Y_RAMP, zs - step), DUST, {"power": "0"}, net)
            v_from, v_to = zd + 2 * step, zs - 2 * step
        elif mode in ("diode", "side"):
            land = zs - 2 * step
            _dust(pl, (col, Y_ROW, land), net)
            _rep(pl, (col, Y_ROW, zs - step), facing, net)
            pl.put((col, Y_ROW, land - step), SMOOTH_STONE)
            pl.put((col, Y_RAMP, land - step), DUST, {"power": "0"}, net)
            v_from, v_to = zd + 2 * step, land - 2 * step
            reps += 1
        else:   # face: dust at zs-step points into B; ramp at zs-2step
            _dust(pl, (col, Y_ROW, zs - step), net)
            pl.put((col, Y_ROW, zs - 2 * step), SMOOTH_STONE)
            pl.put((col, Y_RAMP, zs - 2 * step), DUST, {"power": "0"}, net)
            v_from, v_to = zd + 2 * step, zs - 3 * step
        z = v_from
        while (z - v_to) * step <= 0:
            pl.put((col, Y_RAMP, z), SMOOTH_STONE)
            # never on the first V cell: a repeater at y=4 reads the cell
            # behind it at y=4, and behind the first cell is the ramp at y=3
            # (learned on the 2-bit adder, D-2 iteration 0: b0 -> bit0.t0
            # went dark at the ramp)
            if run >= RUN_RESET and z != v_to and z != v_from:
                _rep(pl, (col, Y_V, z), facing, net)
                reps += 1
                run = 0
            else:
                pl.put((col, Y_V, z), DUST, {"power": "0"}, net)
                run += 1
            z += step
        edge_repeaters[(net, gname)] = reps
        landing_run[(net, gname)] = 0 if mode != "direct" else run + 2   # ramp + row cell
        pl.segments.append({"net": net, "sink": gname, "column": col, "mode": mode,
                            "direct": mode == "direct", "from_row_z": zd, "to_row_z": zs})

    # (3) gate input rows: a direct pin's row IS its net (the landing joins
    # it); diode pins feed an OR-dust that is the gate's own conductor.
    for gname in order:
        if gname not in gates:
            continue
        z, xb, kind = pl.rows[gname], pl.gate_x[gname], gate_kind(gates[gname])
        if kind in ("or_merge", "dust_max"):
            for p in pl.pins[gname]:
                edge_repeaters[(p["net"], gname)] += len(
                    [x for x in reps_at.get(gname, []) if x > p["col"]])
            continue
        if kind == "cmp_inv":
            edge_repeaters[(pl.pins[gname][0]["net"], gname)] += 1     # the side pin's repeater
            continue
        x_last = xb - 2 if kind == "cmp_sub" else xb - 1
        direct = [p for p in pl.pins[gname] if p["mode"] == "direct"]
        diodes = [p for p in pl.pins[gname] if p["mode"] == "diode"]
        for p in direct:
            net, col = p["net"], p["col"]
            h_track(net, col, x_last, z, {col}, run0=landing_run[(net, gname)])
            edge_repeaters[(net, gname)] += len([x for x in reps_at.get(net, []) if x > col])
            if kind == "cmp_sub":
                edge_repeaters[(net, gname)] += 1          # the strength-15 pin repeater
        if diodes:
            label = f"or:{gname}"
            cols = {p["col"] for p in diodes}
            h_track(label, min(cols), x_last, z, cols)
            for p in diodes:
                edge_repeaters[(p["net"], gname)] += len(
                    [x for x in reps_at.get(label, []) if x > p["col"]])
    for seg in pl.segments:
        seg["repeaters_on_path"] = edge_repeaters[(seg["net"], seg["sink"])]
    pl.edge_repeaters = edge_repeaters

    # --- connection props and rest state
    for pos, (block, props) in pl.blocks.items():
        if block == DUST:
            props.update(placement_state(pl.blocks, pos))
    m = Machine(pl.blocks)
    m.run_to_rest()
    for pos, (block, props) in m.blocks.items():
        pl.blocks[pos] = (block, dict(props))
    return pl


def rail_track(pl, net, x0, x1, z):
    """The rail_net wire idiom on one horizontal track (DESIGN 8.1): a
    repeater at x0 (input from the west) powers rail x0+1; rails run east
    to x1-1; an observer at x1 faces west onto the last rail and pulses
    from its east face. Placeable and auditable (I1, I4: rails are not
    dust); the machine has no rail / observer rule, so a placement that
    contains one is refused by prediction, never predicted wrong. Refuses
    a run longer than one source powers (PoweredRailBlock.java:113-132,
    distance < 8 -> 9 rails)."""
    rails = x1 - x0 - 1
    if rails < 1 or rails > IDIOMS["rail_net"]["max_rails"]:
        raise PlaceError(f"rail_net {net}: {rails} rails on one source (1..{IDIOMS['rail_net']['max_rails']})")
    _rep(pl, (x0, Y_ROW, z), "west", net)
    for x in range(x0 + 1, x1):
        pl.put((x, Y_ROW, z), POWERED_RAIL, {"powered": "false", "shape": "east_west", "waterlogged": "false"}, net)
        _support(pl, (x, Y_ROW, z))
    pl.put((x1, Y_ROW, z), OBSERVER, {"facing": "west", "powered": "false"}, net)
    _support(pl, (x1, Y_ROW, z))
    return rails


def place_auto(netlist):
    """Both fabrics; the one with the fewer repeaters that audits clean
    (DESIGN 8.4: the cost model chooses the density). Returns (pl, fabric)."""
    best = None
    for fabric in FABRICS:
        try:
            pl = place(netlist, fabric)
        except PlaceError:
            continue
        if audit(pl):
            continue
        reps = sum(1 for b, _p in pl.blocks.values() if b == REPEATER)
        if best is None or reps < best[0]:
            best = (reps, pl, fabric)
    if best is None:
        raise PlaceError("no fabric places this netlist cleanly")
    return best[1], best[2]


# --------------------------------------------------------------------- audit

def _dust_links(blocks, pos):
    """Dust cells this dust cell is connected to (both directions of the
    source rule, so the graph is undirected)."""
    out = []
    for d in HORIZONTAL:
        c = connection(blocks, pos, d)
        n = add(pos, d)
        if c == "up":
            out.append(add(n, "up"))
        elif c == "side":
            if blocks.get(n, (None,))[0] == DUST:
                out.append(n)
            elif n not in blocks and blocks.get(add(n, "down"), (None,))[0] == DUST:
                out.append(add(n, "down"))      # down-slope: the neighbour cell is air
    return [p for p in out if blocks.get(p, (None,))[0] == DUST]


def _carrier_net(blocks, net_of, pos):
    """The net a dust / repeater cell carries, None for air / stone, '?' for
    an unlabelled conductor or any other emitter."""
    entry = blocks.get(pos)
    if entry is None or entry[0] == SMOOTH_STONE:
        return None
    if entry[0] in (DUST, REPEATER):
        return net_of.get(pos, "?")
    return "?"


def audit(pl):
    """I1..I4, I7 (DESIGN section 4 / 8.4). Returns the list of problems (empty = OK)."""
    problems = []
    blocks = pl.blocks
    # I1 support
    for pos, (block, props) in blocks.items():
        if block in (DUST, REPEATER, COMPARATOR, LEVER, POWERED_RAIL):
            below = blocks.get((pos[0], pos[1] - 1, pos[2]))
            if below is None or below[0] not in (SMOOTH_STONE, LAMP):
                problems.append(f"I1 {block} at {pos} has no solid support")
    # I2/I3 one net per dust component (nets are labels; or:<g> joins its landing)
    seen = set()
    for pos, (block, _p) in blocks.items():
        if block != DUST or pos in seen:
            continue
        comp, queue = set(), [pos]
        while queue:
            p = queue.pop()
            if p in comp:
                continue
            comp.add(p)
            queue.extend(_dust_links(blocks, p))
        seen |= comp
        nets = {pl.net_of.get(p, "?") for p in comp}
        if len(nets) != 1:
            problems.append(f"I2/I3 dust component at {sorted(comp)[0]} carries nets {sorted(nets)}")
    # I2 torch faces: no dust of a foreign net beside a torch except its output
    for pos, (block, props) in blocks.items():
        if block == WALL_TORCH:
            for d in FACES:
                if d == OPPOSITE[props["facing"]]:
                    continue
                n = add(pos, d)
                if blocks.get(n, (None,))[0] == DUST and d != props["facing"]:
                    problems.append(f"I2 torch at {pos} powers dust at {n} on face {d}")
    # I4 dust run <= 15 cells from a source
    sources = {}
    for pos, (block, props) in blocks.items():
        if block in (WALL_TORCH, REPEATER, COMPARATOR):
            d = props["facing"]
            front = add(pos, d) if block == WALL_TORCH else add(pos, OPPOSITE[d])
            if blocks.get(front, (None,))[0] == DUST:
                sources.setdefault(pl.net_of.get(front), []).append(front)
    for port in pl.ports["in"]:
        sources.setdefault(pl.net_of.get(port), []).append(port)
    for net, starts in sources.items():
        # each source ALONE must reach every cell of its conductor: a wired-OR
        # line is powered by whichever source is high, not by their union
        for start in starts:
            dist = {start: 0}
            queue = [start]
            for p in queue:
                for q in _dust_links(blocks, p):
                    if q not in dist:
                        dist[q] = dist[p] + 1
                        queue.append(q)
            far = max(dist.values())
            if far + 1 > DUST_MAX_RUN:
                problems.append(f"I4 net {net} runs {far + 1} dust cells from {start} (> {DUST_MAX_RUN})")
    # I4 for rails: one source powers at most max_rails rails in a line
    for pos, (block, props) in blocks.items():
        if block == POWERED_RAIL and blocks.get(add(pos, "west"), (None,))[0] != POWERED_RAIL:
            n, p = 0, pos
            while blocks.get(p, (None,))[0] == POWERED_RAIL:
                n += 1
                p = add(p, "east")
            if n > IDIOMS["rail_net"]["max_rails"]:
                problems.append(f"I4 rail line at {pos} has {n} rails on one source (> {IDIOMS['rail_net']['max_rails']})")
    # I7 pin purity: a comparator's back and sides, and B's north / south
    # faces, carry only the pin's net (a foreign dust beside a comparator IS
    # read as a side input, AbstractRedstoneGateBlock.java:141-147)
    for pos, gname in pl.cells.items():
        block, props = blocks[pos]
        pins = pl.pins.get(gname, [])
        pin_nets = {p["net"] for p in pins} | {f"or:{gname}"}
        if block == COMPARATOR:
            f = props["facing"]
            if len(pins) == 1:
                # cmp_inv: the back must be the redstone block, nothing else
                if blocks.get(add(pos, f), (None,))[0] != REDSTONE_BLOCK:
                    problems.append(f"I7 comparator {gname} at {pos} back is not a redstone block")
            else:
                back = _carrier_net(blocks, pl.net_of, add(pos, f))
                if back != pins[0]["net"]:
                    problems.append(f"I7 comparator {gname} at {pos} back carries {back!r}, wants {pins[0]['net']!r}")
            for d in HORIZONTAL:
                if d in (f, OPPOSITE[f]):
                    continue
                side = _carrier_net(blocks, pl.net_of, add(pos, d))
                if side not in (None, pins[-1]["net"]):
                    problems.append(f"I7 comparator {gname} at {pos} side {d} carries {side!r}")
        else:
            for d in ("north", "south", "west"):
                carrier = _carrier_net(blocks, pl.net_of, add(pos, d))
                if carrier is not None and carrier not in pin_nets:
                    problems.append(f"I7 B of {gname} at {pos} face {d} carries {carrier!r}")
    return problems


# ------------------------------------------------------------------ emission

def program(pl, name, description):
    blocks = [[x, y, z, library.block_string(b, p)]
              for (x, y, z), (b, p) in sorted(pl.blocks.items())]
    return {"layout": "blocks", "name": name, "description": description,
            "blocks": blocks,
            "ports": [{"name": "in", "role": "in", "width": len(pl.ports["in"]),
                       "offsets": [list(p) for p in pl.ports["in"]],
                       "note": "one dust cell per declared input, in spec order; drive with a lever beside it"},
                      {"name": "out", "role": "out", "width": len(pl.ports["out"]),
                       "offsets": [list(p) for p in pl.ports["out"]],
                       "note": "one redstone_lamp per declared output, in spec order; observe lit"}]}


def ports_doc(pl, name, inputs, outputs):
    """Both port vocabularies at once: wavegen.cellports.v0 (in/out cells,
    what dynharness reads) and the absorb-record families CD-3's project
    row resolves against (drive/tap roles)."""
    return {"kind": "wavegen.cellports.v0", "part": name,
            "family_id": "llmgen.fabric.v0",
            "families": {"in": [{"index": i, "cell": list(c)} for i, c in enumerate(pl.ports["in"])],
                         "out": [{"index": i, "cell": list(c)} for i, c in enumerate(pl.ports["out"])]},
            "note": "cells are [x,y,z] in the program's own frame"}


def absorb_record(pl, name, inputs, outputs):
    fam = []
    for i, (iname, cell) in enumerate(zip(inputs, pl.ports["in"])):
        fam.append({"name": iname, "role": "drive", "members": [{"index": 0, "cell": list(cell)}]})
    for i, (oname, cell) in enumerate(zip(outputs, pl.ports["out"])):
        fam.append({"name": oname, "role": "tap", "members": [{"index": 0, "cell": list(cell)}]})
    return {"part": name, "world_id": "llmgen", "kind": "interface",
            "frame": {"note": "artifact frame, y=2 row plane"}, "families": fam}


def sta_description(name, netlist, arc_table):
    """One instance of the artifact with its arcs inline (sta.py normalise shape)."""
    arcs = [{"from": f"in[{i}]", "to": f"out[{j}]",
             "delay_gt": {"lo": a["lo"], "hi": a["hi"]}, "stages": a["stages"]}
            for i, iname in enumerate(netlist["inputs"])
            for j, oname in enumerate(netlist["outputs"])
            for key, a in arc_table.items() if key == (iname, oname)]
    nets = [{"name": iname, "driver": None, "sinks": [f"u.in[{i}]"]}
            for i, iname in enumerate(netlist["inputs"])]
    nets += [{"name": oname, "driver": f"u.out[{j}]", "sinks": []}
             for j, oname in enumerate(netlist["outputs"])]
    return {"cells": {name: {"arcs": arcs}},
            "instances": [{"id": "u", "cell": name}], "nets": nets,
            "primary_inputs": list(netlist["inputs"]),
            "primary_outputs": list(netlist["outputs"])}


def dumps(doc):
    return json.dumps(doc, indent=1, sort_keys=True) + "\n"
