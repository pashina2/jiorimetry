#!/usr/bin/env python3
"""tools/llmgen/netlist.py -- spec (truth table) -> NOR-basis netlist,
levels, and the arc table in the cell-decl vocabulary.

DESIGN section 3. The NOR is redstone's own basis: a torch on a solid block
whose faces several dusts point into is a NOR of those dusts; a NOR of one
net is a NOT. Synthesis: for every output, take the minterm SOP of f and of
not-f, build the NOR-NOR two-level form of each, hash-cons identical NORs,
and keep the cheaper. The NOR-NOR of not-f's SOP IS f (the final inverter
folds away), which is how the classic half adder falls out unasked: carry =
NOR(not a, not b) is one of sum's own terms.

Nothing here reads the truth table back into the output: the table drives
which NORs exist, and `evaluate()` (a test aid) re-derives the function from
the gates so a test can catch a synthesis that disagrees with its spec.
"""

import itertools
import json

from library import TORCH_GT, REPEATER_GT_PER_DELAY, COMPARATOR_GT, LAMP_OFF_GT

#: Scheduled ticks the cell of each gate kind adds on a path, and the tick
#: stages it counts as (D-2, DESIGN 8.1). `nor` covers the one-input NOT.
KIND_GT = {"nor": TORCH_GT, "not": TORCH_GT, "cmp_sub": COMPARATOR_GT, "or_merge": 0,
           "cmp_inv": COMPARATOR_GT, "dust_max": 0}
KIND_STAGES = {"nor": 1, "not": 1, "cmp_sub": 1, "or_merge": 0, "cmp_inv": 1, "dust_max": 0}


def gate_value(kind, values):
    """Boolean value of one gate from its ordered fanin values."""
    if kind in ("nor", "not"):
        return 0 if any(values) else 1
    if kind == "cmp_sub":
        return 1 if values[0] and not values[1] else 0
    if kind in ("or_merge", "dust_max"):
        return 1 if any(values) else 0
    if kind == "cmp_inv":
        return 0 if values[0] else 1
    raise NetlistError(f"no evaluation rule for gate kind {kind!r}")


class NetlistError(ValueError):
    """A spec this module refuses, naming why."""


def load_spec(doc):
    """Validate the spec shape (DESIGN section 1) and return it."""
    for key in ("name", "inputs", "outputs", "function"):
        if key not in doc:
            raise NetlistError(f"spec needs {key!r}")
    ins, outs, table = doc["inputs"], doc["outputs"], doc["function"]
    if not ins or not outs or len(set(ins)) != len(ins) or len(set(outs)) != len(outs):
        raise NetlistError("inputs and outputs must be non-empty and unique")
    if set(ins) & set(outs):
        raise NetlistError("an input name may not also be an output name")
    keys = {"".join(bits) for bits in itertools.product("01", repeat=len(ins))}
    if set(table) != keys:
        raise NetlistError(f"function must cover every input bitstring ({len(keys)} rows)")
    for k, v in table.items():
        if not isinstance(v, str) or len(v) != len(outs) or set(v) - {"0", "1"}:
            raise NetlistError(f"function[{k!r}] must be {len(outs)} output bits")
    return doc


class Builder:
    """Hash-consed NOR network. Nets are named; gates are `t<n>`."""

    def __init__(self, inputs):
        self.inputs = list(inputs)
        self.gates = []           # [{id, kind: 'nor', fanin: [net], out: net}]
        self._memo = {}           # frozenset(fanin) -> out net
        self.fanout = {name: 0 for name in inputs}

    def nor(self, fanin):
        key = frozenset(fanin)
        if key in self._memo:
            return self._memo[key]
        out = f"t{len(self.gates)}"
        self.gates.append({"id": out, "kind": "nor", "fanin": sorted(key), "out": out})
        self._memo[key] = out
        self.fanout[out] = 0
        for net in key:
            self.fanout[net] += 1
        return out

    def complement(self, net):
        return self.nor([net])

    def cost_of(self, fanin_sets):
        """How many NEW gates a list of NOR fanin sets would create."""
        seen = set(self._memo)
        new = 0
        for fanin in fanin_sets:
            key = frozenset(fanin)
            if key not in seen:
                new += 1
                seen.add(key)
        return new


def _minterms(table, out_index, ninputs, value):
    return [tuple(int(c) for c in k) for k, v in sorted(table.items())
            if v[out_index] == value]


def _term_fanin(minterm, inputs, builder, dry):
    """NOR fanin realising AND of the minterm: a literal x=1 needs NOT x,
    a literal x=0 needs x itself."""
    fanin = []
    for name, bit in zip(inputs, minterm):
        if bit:
            fanin.append(builder.nor([name]) if not dry else ("not", name))
        else:
            fanin.append(name)
    return fanin


def _plan(minterms, inputs, builder, direct):
    """Fanin sets the polarity would create (for costing), and how many
    complement gates it needs."""
    sets, comps = [], set()
    for m in minterms:
        fanin = []
        for name, bit in zip(inputs, m):
            if bit:
                comps.add(name)
                fanin.append(("not", name))
            else:
                fanin.append(name)
        sets.append(fanin)
    # resolve ("not", x) against existing complements for costing
    resolved = []
    for fanin in sets:
        resolved.append([builder._memo.get(frozenset([x[1]]), f"not:{x[1]}")
                         if isinstance(x, tuple) else x for x in fanin])
    comp_sets = [[name] for name in sorted(comps)]
    if len(minterms) == 1:
        # direct: out = term; complement: out = NOT term
        top = [] if direct else [["term0"]]
    else:
        top = [["terms"]] + ([["ornot"]] if direct else [])
    return builder.cost_of(comp_sets + resolved + top)


def synthesize(spec):
    """spec -> netlist dict (DESIGN section 3)."""
    spec = load_spec(spec)
    inputs, outputs, table = spec["inputs"], spec["outputs"], spec["function"]
    b = Builder(inputs)
    out_nets = {}
    for j, oname in enumerate(outputs):
        on = _minterms(table, j, len(inputs), "1")
        off = _minterms(table, j, len(inputs), "0")
        if not on or not off:
            raise NetlistError(f"output {oname!r} is constant; v1 refuses constants")
        cost_direct = _plan(on, inputs, b, True)
        cost_comp = _plan(off, inputs, b, False)
        if cost_comp <= cost_direct:
            terms = [b.nor(_term_fanin(m, inputs, b, False)) for m in off]
            net = b.nor(terms)            # NOR-NOR of not-f's SOP == f
        else:
            terms = [b.nor(_term_fanin(m, inputs, b, False)) for m in on]
            net = terms[0] if len(terms) == 1 else b.complement(b.nor(terms))
        out_nets[oname] = net
    for net in out_nets.values():
        b.fanout[net] += 1
    return {"kind": "llmgen.netlist.v0", "name": spec["name"],
            "inputs": list(inputs), "outputs": dict(out_nets),
            "gates": b.gates, "fanout": b.fanout}


def levels(netlist):
    """Longest-path level per net: inputs 0, a gate = 1 + max(fanin)."""
    lv = {name: 0 for name in netlist["inputs"]}
    pending = list(netlist["gates"])
    while pending:
        rest = []
        for g in pending:
            if all(n in lv for n in g["fanin"]):
                lv[g["out"]] = 1 + max(lv[n] for n in g["fanin"])
            else:
                rest.append(g)
        if len(rest) == len(pending):
            raise NetlistError("netlist has a cycle or an undriven net")
        pending = rest
    return lv


def evaluate(netlist, vector):
    """Boolean value of every net for one input vector (test aid)."""
    val = dict(zip(netlist["inputs"], (int(v) for v in vector)))
    gates = {g["out"]: g for g in netlist["gates"]}
    def value(net):
        if net in val:
            return val[net]
        g = gates[net]
        val[net] = gate_value(g.get("kind", "nor"), [value(n) for n in g["fanin"]])
        return val[net]
    for net in list(gates):
        value(net)
    return val


def edge_repeaters_of(gate):
    """Repeaters on one fanin edge when nothing else is known: the diode a
    multi-input NOR puts on every input (DESIGN section 3 / 4: distinct nets
    never merge on dust). The placer refines this with the inline repeaters
    its dust-run rule inserted (`place.Placement.edge_repeaters`). A
    comparator's pins carry a strength-15 repeater each (DESIGN 8.0) and a
    merge's inputs are diodes."""
    kind = gate.get("kind", "nor")
    if kind in ("cmp_sub", "or_merge", "cmp_inv", "dust_max"):
        return 1
    return 1 if len(gate["fanin"]) > 1 else 0


def arcs(netlist, lamp_outputs=True, edge_repeaters=None):
    """{(input, output): {lo, hi, stages}} -- the cell-decl arc vocabulary.
    lo = shortest path (gt), hi = longest path plus the lamp's fall delay
    when the output is observed on a lamp; stages = scheduled ticks on the
    longest path. Delay per edge (net -> gate) = torch + 2 gt per repeater
    on that edge, repeaters taken from `edge_repeaters[(net, gate)]` when
    given and from the diode rule otherwise. An input with no path to an
    output has no arc (STA's 'dead end'); that absence is returned, not
    invented."""
    gates = {g["out"]: g for g in netlist["gates"]}
    lv = levels(netlist)
    out = {}
    for name in netlist["inputs"]:
        # all paths from input to every net: keep (min, max) delay and stage count
        best = {name: (0, 0, 0)}   # net -> (lo, hi, stages_on_hi_path)
        for net in sorted(gates, key=lambda n: lv[n]):
            g = gates[net]
            reach = []
            for n in g["fanin"]:
                if n not in best:
                    continue
                reps = (edge_repeaters or {}).get((n, net), edge_repeaters_of(g))
                kind = g.get("kind", "nor")
                d = KIND_GT[kind] + REPEATER_GT_PER_DELAY * reps
                reach.append((best[n][0] + d, best[n][1] + d, best[n][2] + KIND_STAGES[kind] + reps))
            if not reach:
                continue
            best[net] = (min(r[0] for r in reach), max(r[1] for r in reach),
                         max(r[2] for r in reach))
        for oname, onet in netlist["outputs"].items():
            if onet in best and onet != name:
                lo, hi, st = best[onet]
                out[(name, oname)] = {"lo": lo, "hi": hi + (LAMP_OFF_GT if lamp_outputs else 0),
                                      "stages": st + (1 if lamp_outputs else 0)}
    return out


def to_json(netlist):
    return json.dumps(netlist, indent=1, sort_keys=True) + "\n"
