#!/usr/bin/env python3
"""tools/llmgen/map.py -- technology mapping: truth table -> netlist
over the idiom table, under a cost profile; NOR-NOR is the fallback.

DESIGN section 8. A leaf function (<= 4 inputs) is a SIGNATURE: an integer
with one bit per truth-table row (row index = the input bitstring read as a
number, spec key order). Every idiom row of `library.IDIOMS` with a `fn` is
a function on signatures, so covering is a search over signatures: start
from the inputs, apply every idiom to every pair of known signatures, keep
the cheapest cover per signature (a label-setting relaxation), stop when
every output signature is reached. Hash-consing is free -- one signature is
one net -- which is how XOR = or_merge(cmp_sub(a,b), cmp_sub(b,a)) and
AND = cmp_sub(a, XOR) share the XOR without being told to.

An output the search does not reach (the idiom set cannot build it, or the
pop budget ran out) FALLS BACK to `netlist.synthesize`'s NOR-NOR for that
output alone, spliced in with fresh net names. Profile `nor` never enters
the search: a flat spec goes straight to `netlist.synthesize` (byte-
identical to D-1, pinned by test); a hierarchical spec runs synthesize per
leaf and wires the instances.

Cost is a vector (parts by class, rows, cols, arrival lo, arrival hi);
parts / rows / cols add, arrival is max(fanin) + the cell's arc. A profile
scalarises it. The tree cost of a DAG double-counts shared cones -- said
here, not hidden: the search ranks by tree cost, the emitted netlist shares.
"""

import heapq
import itertools

from library import IDIOMS, MATERIAL, REPEATER_GT_PER_DELAY
import netlist as nl


class MapError(ValueError):
    """A spec or profile this module refuses, naming why."""


#: Cost profiles (DESIGN 8.2). `weights` scalarise the vector; `idioms`
#: restricts the rows the search may use (None = every logic row).
PROFILES = {
    "nor": {"note": "D-1 path: netlist.synthesize, no search", "idioms": (), "weights": None},
    "timing": {"note": "arrival hi first, then parts",
               "weights": {"hi": 100.0, "lo": 0.0, "parts": 1.0, "rows": 0.0, "cols": 0.0, "material": 0.0}},
    "material": {"note": "vanilla crafting cost of the parts (library.MATERIAL), then arrival",
                 "weights": {"hi": 0.01, "lo": 0.0, "parts": 0.0, "rows": 0.0, "cols": 0.0, "material": 1.0}},
    "footprint": {"note": "fabric rows and columns, then arrival",
                  "weights": {"hi": 0.01, "lo": 0.0, "parts": 0.0, "rows": 10.0, "cols": 1.0, "material": 0.0}},
    # SYN-2: the comparator-only technology. Its rows carry `profiles`, which
    # keeps them out of every other profile's search (regression: D-1 / D-2 /
    # MB-1 / REF-1 / SYN-1 fixtures byte-identical).
    "strength": {"note": "comparator-only technology: cmp_sub / cmp_inv / dust_max, arrival hi first, then parts",
                 "idioms": ("cmp_sub", "cmp_inv", "dust_max"),
                 "weights": {"hi": 100.0, "lo": 0.0, "parts": 1.0, "rows": 0.0, "cols": 0.0, "material": 0.0}},
}

#: The rows every unrestricted profile searches: a logic function and no
#: `profiles` restriction.
LOGIC_IDIOMS = tuple(name for name, row in IDIOMS.items()
                     if row.get("fn") is not None and not row.get("profiles"))


def profile_idioms(profile, idioms=None):
    """The rows a profile searches: the caller's list, else the profile's own
    `idioms`, else every unrestricted logic row."""
    if idioms is not None:
        return idioms
    own = PROFILES[profile].get("idioms")
    return tuple(own) if own else None
POP_BUDGET = 6000


def signature(table, inputs, out_index):
    """The output column of a truth table as a signature."""
    sig = 0
    for key, value in table.items():
        if value[out_index] == "1":
            sig |= 1 << int(key, 2)
    return sig


def input_signature(n, j):
    """Signature of input j (0 = most significant, spec key order) over 2^n rows."""
    sig = 0
    for row in range(1 << n):
        if (row >> (n - 1 - j)) & 1:
            sig |= 1 << row
    return sig


def zero_vector():
    return {"parts": {}, "rows": 0, "cols": 0, "lo": 0, "hi": 0}


def combine(children, idiom, fabric):
    """Cost vector of one idiom instance over its children's vectors."""
    row = IDIOMS[idiom]
    k = len(children)
    parts = {}
    for c in children:
        for name, n in c["parts"].items():
            parts[name] = parts.get(name, 0) + n
    for name, n in row["parts"](k, fabric).items():
        parts[name] = parts.get(name, 0) + n
    # pin repeaters (strength conditions) and diodes are 2 gt each on the
    # edge; the placer's inline repeaters are not known here
    pin_gt = REPEATER_GT_PER_DELAY * nl.edge_repeaters_of({"kind": idiom, "fanin": ["x"] * k})
    if idiom == "nor" and fabric == "dense" and k <= 2:
        pin_gt = 0
    arc = row["arc_gt"] + pin_gt
    return {"parts": parts,
            "rows": sum(c["rows"] for c in children) + row["rows"],
            "cols": sum(c["cols"] for c in children) + row["cols"](k),
            "lo": (min(c["lo"] for c in children) if children else 0) + arc,
            "hi": (max(c["hi"] for c in children) if children else 0) + arc}


def scalar(vec, weights):
    material = sum(MATERIAL.get(name, 1.0) * n for name, n in vec["parts"].items())
    total = sum(vec["parts"].values())
    return (weights["hi"] * vec["hi"] + weights["lo"] * vec["lo"] + weights["parts"] * total
            + weights["rows"] * vec["rows"] + weights["cols"] * vec["cols"]
            + weights["material"] * material)


def cover(inputs, targets, profile, fabric="sparse", idioms=None, pop_budget=POP_BUDGET):
    """Search the signature space. Returns {sig: (vector, expr)} for every
    settled signature, where expr = ("in", name) | (idiom, [child sigs]).
    `targets` stops the search early once every one is settled."""
    n = len(inputs)
    mask = (1 << (1 << n)) - 1
    weights = PROFILES[profile]["weights"]
    if weights is None:
        raise MapError(f"profile {profile!r} does not search")
    rows = [name for name in (idioms if idioms is not None else LOGIC_IDIOMS)
            if IDIOMS[name].get("fn") is not None]
    best = {}            # sig -> (cost, vector, expr)
    settled = {}         # sig -> (vector, expr)
    heap = []
    counter = itertools.count()

    def offer(sig, vec, expr):
        cost = scalar(vec, weights)
        if sig in settled:
            return
        if sig not in best or cost < best[sig][0]:
            best[sig] = (cost, vec, expr)
            heapq.heappush(heap, (cost, next(counter), sig))

    for j, name in enumerate(inputs):
        offer(input_signature(n, j), zero_vector(), ("in", name))
    pops = 0
    while heap and pops < pop_budget:
        cost, _c, sig = heapq.heappop(heap)
        if sig in settled or best[sig][0] != cost:
            continue
        settled[sig] = (best[sig][1], best[sig][2])
        pops += 1
        if all(t in settled for t in targets):
            break
        vec = settled[sig][0]
        for name in rows:
            row = IDIOMS[name]
            if row["arity"] == 1:
                out = row["fn"](mask, sig)
                if out not in (0, mask):
                    offer(out, combine([vec], name, fabric), (name, [sig]))
                continue
            for other, (ovec, _e) in list(settled.items()):
                if other == sig:
                    continue
                for x, y in ((sig, other), (other, sig)):
                    pre = row.get("precondition")
                    if pre is not None and not pre(x, y):
                        continue
                    out = row["fn"](mask, x, y)
                    if out in (0, mask):
                        continue
                    offer(out, combine([settled[x][0], settled[y][0]], name, fabric), (name, [x, y]))
    return settled


class Emitter:
    """Turns settled expressions into netlist gates, one gate per signature."""

    def __init__(self, prefix=""):
        self.gates = []
        self.names = {}         # sig -> net
        self.prefix = prefix

    def net(self, settled, sig):
        if sig in self.names:
            return self.names[sig]
        vec, expr = settled[sig]
        if expr[0] == "in":
            self.names[sig] = expr[1]
            return expr[1]
        kind, children = expr
        fanin = [self.net(settled, c) for c in children]
        out = f"{self.prefix}m{len(self.gates)}"
        self.gates.append({"id": out, "kind": kind, "fanin": fanin, "out": out})
        self.names[sig] = out
        return out


def map_leaf(spec, profile, fabric="sparse", idioms=None, prefix="", pop_budget=POP_BUDGET):
    """One leaf truth table -> {gates, outputs, fallback: [output names]}."""
    spec = nl.load_spec(spec)
    inputs, outputs, table = spec["inputs"], spec["outputs"], spec["function"]
    if profile == "nor":
        net = nl.synthesize(spec)
        gates = [dict(g, id=prefix + g["id"], out=prefix + g["out"],
                      fanin=[prefix + n if n not in inputs else n for n in g["fanin"]])
                 for g in net["gates"]]
        outs = {o: (prefix + n if n not in inputs else n) for o, n in net["outputs"].items()}
        return {"gates": gates, "outputs": outs, "fallback": [], "profile": profile}
    targets = {signature(table, inputs, j): o for j, o in enumerate(outputs)}
    settled = cover(inputs, set(targets), profile, fabric, profile_idioms(profile, idioms), pop_budget)
    em = Emitter(prefix)
    outs, fallback = {}, []
    for sig, oname in targets.items():
        if sig in settled:
            outs[oname] = em.net(settled, sig)
        else:
            fallback.append(oname)
    if fallback:
        # NOR-NOR for the unreached outputs only, spliced with fresh names
        sub = dict(spec, outputs=fallback,
                   function={k: "".join(v[outputs.index(o)] for o in fallback) for k, v in table.items()})
        net = nl.synthesize(sub)
        fp = f"{prefix}f"
        for g in net["gates"]:
            em.gates.append({"id": fp + g["id"], "kind": "nor", "out": fp + g["out"],
                             "fanin": [fp + n if n not in inputs else n for n in g["fanin"]]})
        for o, n in net["outputs"].items():
            outs[o] = fp + n if n not in inputs else n
    return {"gates": em.gates, "outputs": outs, "fallback": fallback, "profile": profile}


def _finish(spec, gates, outputs, profile, fabric, fallback):
    for o, n in outputs.items():
        if n in spec["inputs"]:
            raise MapError(f"output {o!r} is the bare input {n!r}; v1 refuses pass-through")
    outputs = {o: outputs[o] for o in spec["outputs"]}      # spec order: evaluate joins by it
    fanout = {name: 0 for name in spec["inputs"]}
    for g in gates:
        fanout.setdefault(g["out"], 0)
    for g in gates:
        for n in g["fanin"]:
            fanout[n] = fanout.get(n, 0) + 1
    for n in outputs.values():
        fanout[n] += 1
    return {"kind": "llmgen.netlist.v0", "name": spec["name"],
            "inputs": list(spec["inputs"]), "outputs": dict(outputs),
            "gates": gates, "fanout": fanout,
            "mapping": {"profile": profile, "fabric": fabric, "fallback_outputs": fallback,
                        "kinds": sorted({g["kind"] for g in gates})}}


def map_spec(spec, profile="nor", fabric="sparse", idioms=None, pop_budget=POP_BUDGET):
    """spec -> netlist. Flat spec under `nor` is exactly netlist.synthesize
    (plus the `mapping` note). A hierarchical spec (`cells` + `instances`,
    DESIGN 8.3) is mapped per leaf and wired by the instance maps; its flat
    `function` is the contract gen.py checks the result against."""
    if profile not in PROFILES:
        raise MapError(f"unknown profile {profile!r} (have {sorted(PROFILES)})")
    spec = nl.load_spec(spec)
    if "instances" not in spec:
        if profile == "nor":
            net = nl.synthesize(spec)
            net["mapping"] = {"profile": profile, "fabric": fabric, "fallback_outputs": [],
                              "kinds": sorted({g["kind"] for g in net["gates"]})}
            return net
        leaf = map_leaf(spec, profile, fabric, idioms, "", pop_budget)
        return _finish(spec, leaf["gates"], leaf["outputs"], profile, fabric, leaf["fallback"])
    cells = spec.get("cells") or {}
    gates, outputs, fallback = [], {}, []
    driven = set(spec["inputs"])
    for inst in spec["instances"]:
        for key in ("id", "cell", "map"):
            if key not in inst:
                raise MapError(f"instance needs {key!r}")
        if inst["cell"] not in cells:
            raise MapError(f"instance {inst['id']!r} names unknown cell {inst['cell']!r}")
        leaf_spec = dict(cells[inst["cell"]], name=inst["cell"])
        leaf_spec = nl.load_spec(leaf_spec)
        m = inst["map"]
        missing = [p for p in leaf_spec["inputs"] + leaf_spec["outputs"] if p not in m]
        if missing:
            raise MapError(f"instance {inst['id']!r} leaves ports unmapped: {missing}")
        for p in leaf_spec["inputs"]:
            if m[p] not in driven:
                raise MapError(f"instance {inst['id']!r} input {p!r} <- {m[p]!r} is not driven yet "
                               "(order instances so every input is driven before use)")
        leaf = map_leaf(leaf_spec, profile, fabric, idioms, f"{inst['id']}.", pop_budget)
        rename = {p: m[p] for p in leaf_spec["inputs"]}
        # leaf output nets take the instance map's name so the carry chain
        # is one net; a leaf output that is a bare leaf input is refused
        for p in leaf_spec["outputs"]:
            n = leaf["outputs"][p]
            if n in leaf_spec["inputs"]:
                raise MapError(f"instance {inst['id']!r} output {p!r} is its bare input")
            rename[n] = m[p]
            driven.add(m[p])
        for g in leaf["gates"]:
            gates.append({"id": rename.get(g["id"], g["id"]), "kind": g["kind"],
                          "fanin": [rename.get(n, n) for n in g["fanin"]],
                          "out": rename.get(g["out"], g["out"])})
        fallback += [f"{inst['id']}.{o}" for o in leaf["fallback"]]
    for o in spec["outputs"]:
        if o not in driven:
            raise MapError(f"output {o!r} is driven by no instance")
        outputs[o] = o
    # an output net is named by the spec's output name: the gate that
    # drives it already carries that name through the instance map
    return _finish(spec, gates, outputs, profile, fabric, fallback)


def netlist_cost(netlist, fabric="sparse"):
    """Cost vector of a whole netlist (tree cost per output, parts summed
    once per gate), for reports and the fabric choice."""
    parts = {}
    for g in netlist["gates"]:
        k = len(g["fanin"])
        kind = g["kind"] if g["kind"] != "nor" or k > 1 else "not"
        for name, n in IDIOMS[kind]["parts"](k, fabric).items():
            parts[name] = parts.get(name, 0) + n
    arc = nl.arcs(netlist)
    return {"parts": parts, "gates": len(netlist["gates"]),
            "hi": max((a["hi"] for a in arc.values()), default=0),
            "lo": min((a["lo"] for a in arc.values()), default=0),
            "material": sum(MATERIAL.get(name, 1.0) * n for name, n in parts.items())}


def wire_choice(dust_cells, profile="timing", edge_consumer=False):
    """Which wire idiom carries a net over `dust_cells` cells of straight
    track (DESIGN 8.1 rail_net), from the sources, not from the premise:

      dust     free for 15 cells (RedstoneWireBlock :251-275), then a
               repeater (2 gt) -- the placer resets every RUN_RESET cells
      rail     0 gt along at most 9 rails per redstone source
               (PoweredRailBlock.isPoweredByOtherRails :113-132 stops at
               distance 8), and the ONLY reader of a rail's POWERED is an
               observer: 2 gt, and a PULSE (ObserverBlock :55-63). A level
               consumer needs the piston T-flip-flop after it (2 gt lower
               bound) -- so a rail chain costs 2 gt per 11 cells against the
               dust's 2 gt per RUN_RESET cells, and never beats dust on a
               straight level run. It wins only when the consumer is EDGE-
               triggered (the instant-circuit wave family, ADR-0036) and the
               run fits one source: that is the row's real domain, and the
               D-2 order's '0 gt for a long net' premise fails re-derivation
               (recorded, decide-and-disclose).

    Returns {"idiom", "gt", ..., "alternatives"}."""
    from place import RUN_RESET
    row = IDIOMS["rail_net"]
    if dust_cells <= 15 and not edge_consumer:
        return {"idiom": "dust", "gt": 0, "repeaters": 0, "note": "fits one dust run", "alternatives": {}}
    repeaters = max(0, (dust_cells - 1) // RUN_RESET)
    inline = {"idiom": "inline_repeaters", "gt": REPEATER_GT_PER_DELAY * repeaters,
              "repeaters": repeaters, "note": "one repeater per RUN_RESET cells",
              "material": MATERIAL["repeater"] * repeaters}
    segments = max(1, -(-dust_cells // (row["max_rails"] + 2)))
    rails = min(dust_cells - 2, row["max_rails"]) if segments == 1 else row["max_rails"] * segments
    rail = {"idiom": "rail_net", "gt": row["arc_gt"] * segments
            + (0 if edge_consumer else IDIOMS["piston_tff"]["arc_gt"]),
            "rails": rails, "segments": segments,
            "note": ("repeater + rails + observer per segment; exit is a 2 gt pulse"
                     + ("" if edge_consumer else "; level consumer adds the piston T-flip-flop")),
            "material": segments * (MATERIAL["repeater"] + MATERIAL["observer"]) + MATERIAL["powered_rail"] * rails}
    if not edge_consumer:
        rail["material"] += MATERIAL["sticky_piston"] + MATERIAL["redstone_block"]
    weights = PROFILES[profile]["weights"] or PROFILES["material"]["weights"]
    cost = lambda c: weights["hi"] * c["gt"] + weights["material"] * c["material"]
    # an edge consumer cannot use a level wire's repeater chain as such; a
    # tie goes to the rail row there, and to the dust chain everywhere else
    pick = rail if (cost(rail) < cost(inline) or (edge_consumer and cost(rail) == cost(inline))) else inline
    return dict(pick, alternatives={"inline_repeaters": inline["gt"], "rail_net": rail["gt"]})
