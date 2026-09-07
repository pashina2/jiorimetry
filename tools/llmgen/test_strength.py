#!/usr/bin/env python3
"""tools/llmgen/test_strength.py -- falsifiers for the SYN-2
comparator technology: the `strength` profile (cmp_sub / cmp_inv / dust_max,
no torch), its isolation from every other profile, the cmp_inv row shape on
the fabric and in the machine, the idiom attribution (`origin`), and the
declared level rows against B-??'s measured carry table."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import gen                                                 # noqa: E402
import library                                             # noqa: E402
import machine as M                                        # noqa: E402
import map as mapper                                       # noqa: E402
import netlist as nl                                       # noqa: E402
import place                                               # noqa: E402

FULL_ADDER = {
    "kind": "llmgen.spec.v0", "name": "full_adder",
    "inputs": ["a", "b", "cin"], "outputs": ["sum", "cout"],
    "function": {"000": "00", "001": "10", "010": "10", "011": "01",
                 "100": "10", "101": "01", "110": "01", "111": "11"},
}
NOT = {"kind": "llmgen.spec.v0", "name": "inv", "inputs": ["a"], "outputs": ["y"],
       "function": {"0": "1", "1": "0"}}
CELL = HERE / "fixtures" / "b_final_bit_slice.cell.json"
STRENGTH_ROWS = ("cmp_sub", "cmp_inv", "dust_max")


def kinds_of(net):
    out = {}
    for g in net["gates"]:
        out[g["kind"]] = out.get(g["kind"], 0) + 1
    return out


def implements(net, spec):
    for vector, want in spec["function"].items():
        val = nl.evaluate(net, vector)
        got = "".join(str(val[net["outputs"][o]]) for o in net["outputs"])
        if got != want:
            return False
    return True


class ProfileTests(unittest.TestCase):
    def test_strength_profile_builds_the_full_adder_with_comparators_only(self):
        net = mapper.map_spec(FULL_ADDER, "strength", "sparse")
        kinds = kinds_of(net)
        self.assertTrue(set(kinds) <= set(STRENGTH_ROWS), kinds)
        self.assertEqual(net["mapping"]["fallback_outputs"], [])
        self.assertTrue(implements(net, FULL_ADDER))
        # measured 2026-09-06 (record section 5): 15 gates, 9 comparators, 0 torches
        self.assertEqual(len(net["gates"]), 15)
        self.assertEqual(kinds["cmp_sub"] + kinds["cmp_inv"], 9)
        self.assertNotIn("nor", kinds)
        self.assertNotIn("not", kinds)

    def test_parts_first_weights_reach_eight_comparators(self):
        weights = {"hi": 0.01, "lo": 0.0, "parts": 1.0, "rows": 0.0, "cols": 0.0, "material": 0.0}
        mapper.PROFILES["_parts_first_test"] = {"idioms": STRENGTH_ROWS, "weights": weights}
        try:
            net = mapper.map_spec(FULL_ADDER, "_parts_first_test", "sparse")
        finally:
            del mapper.PROFILES["_parts_first_test"]
        kinds = kinds_of(net)
        self.assertTrue(implements(net, FULL_ADDER))
        self.assertEqual(len(net["gates"]), 12)
        self.assertEqual(kinds["cmp_sub"] + kinds["cmp_inv"], 8)

    def test_the_strength_rows_are_invisible_to_the_other_profiles(self):
        self.assertEqual(mapper.LOGIC_IDIOMS, ("not", "nor", "cmp_sub", "or_merge"))
        for name in ("cmp_inv", "dust_max"):
            self.assertEqual(library.IDIOMS[name]["profiles"], ("strength",))
        timing = kinds_of(mapper.map_spec(FULL_ADDER, "timing", "sparse"))
        self.assertEqual(timing, {"cmp_sub": 4, "or_merge": 3, "not": 2, "nor": 3})
        self.assertIsNone(mapper.profile_idioms("timing"))
        self.assertEqual(mapper.profile_idioms("strength"), STRENGTH_ROWS)
        self.assertEqual(mapper.profile_idioms("timing", ["nor"]), ["nor"])

    def test_a_row_with_profiles_never_enters_the_default_search(self):
        library.IDIOMS["_probe"] = dict(library.IDIOMS["not"], profiles=("strength",))
        try:
            logic = tuple(name for name, row in library.IDIOMS.items()
                          if row.get("fn") is not None and not row.get("profiles"))
            self.assertNotIn("_probe", logic)
            loose = tuple(name for name, row in library.IDIOMS.items() if row.get("fn") is not None)
            self.assertIn("_probe", loose)
        finally:
            del library.IDIOMS["_probe"]


class RowShapeTests(unittest.TestCase):
    def test_cmp_inv_is_a_comparator_behind_a_redstone_block_and_the_machine_inverts(self):
        net = mapper.map_spec(NOT, "strength", "sparse")
        self.assertEqual(kinds_of(net), {"cmp_inv": 1})
        pl = place.place(net, "sparse")
        self.assertEqual(place.audit(pl), [])
        blocks = {b for b, _p in pl.blocks.values()}
        self.assertIn(library.REDSTONE_BLOCK, blocks)
        self.assertNotIn(library.WALL_TORCH, blocks)
        cmp_pos = [p for p, (b, _p) in pl.blocks.items() if b == library.COMPARATOR][0]
        self.assertEqual(pl.blocks[(cmp_pos[0] - 1, cmp_pos[1], cmp_pos[2])][0], library.REDSTONE_BLOCK)
        with tempfile.TemporaryDirectory() as tmp:
            spec_path = Path(tmp) / "inv.spec.json"
            spec_path.write_bytes(json.dumps(NOT).encode("utf-8"))
            result = gen.generate(spec_path, tmp, None, 4, "strength", "sparse")
        self.assertEqual(result["kinds"], ["cmp_inv"])
        self.assertEqual(result["parts"]["comparator"], 1)
        self.assertEqual(result["parts"]["redstone_block"], 1)

    def test_audit_refuses_a_cmp_inv_whose_back_is_not_the_redstone_block(self):
        net = mapper.map_spec(NOT, "strength", "sparse")
        pl = place.place(net, "sparse")
        cmp_pos = [p for p, (b, _p) in pl.blocks.items() if b == library.COMPARATOR][0]
        back = (cmp_pos[0] - 1, cmp_pos[1], cmp_pos[2])
        pl.blocks[back] = (library.SMOOTH_STONE, {})
        self.assertTrue(any(p.startswith("I7") for p in place.audit(pl)))

    def test_full_adder_generates_and_the_machine_agrees(self):
        with tempfile.TemporaryDirectory() as tmp:
            spec_path = Path(tmp) / "full_adder.spec.json"
            spec_path.write_bytes(json.dumps(FULL_ADDER).encode("utf-8"))
            result = gen.generate(spec_path, tmp, None, 4, "strength", "sparse")
        self.assertEqual(result["fallback_outputs"], [])
        self.assertEqual(result["parts"]["comparator"], 9)
        self.assertEqual(result["parts"]["redstone_block"], 2)
        self.assertNotIn("redstone_wall_torch", result["parts"])
        self.assertEqual(result["gates"], 15)

    def test_netlist_rules_for_the_new_kinds(self):
        self.assertEqual(nl.gate_value("cmp_inv", [1]), 0)
        self.assertEqual(nl.gate_value("cmp_inv", [0]), 1)
        self.assertEqual(nl.gate_value("dust_max", [1, 1]), 1)
        self.assertEqual(nl.gate_value("dust_max", [0, 0]), 0)
        self.assertEqual(nl.KIND_GT["cmp_inv"], library.COMPARATOR_GT)
        self.assertEqual(nl.KIND_GT["dust_max"], 0)
        self.assertEqual(nl.edge_repeaters_of({"kind": "cmp_inv", "fanin": ["x"]}), 1)


class AttributionTests(unittest.TestCase):
    def test_every_idiom_row_carries_an_origin_in_the_frame_vocabulary(self):
        for name, row in library.IDIOMS.items():
            origin = row.get("origin")
            self.assertTrue(origin, name)
            self.assertTrue(origin == "engine" or any(origin.startswith(v) for v in library.ORIGIN_VOCABULARY[1:]),
                            (name, origin))
        self.assertEqual(library.IDIOMS["cmp_inv"]["origin"], "engine")
        self.assertTrue(library.IDIOMS["rail_net"]["origin"].startswith("community technique: "))
        for name in library.LEVEL_IDIOMS:
            self.assertTrue(library.IDIOMS[name]["calibrated_on"].startswith("operator design: B-??"))

    def test_level_rows_are_declared_not_searched(self):
        for name in library.LEVEL_IDIOMS:
            self.assertIsNone(library.IDIOMS[name]["fn"])
            self.assertNotIn(name, mapper.LOGIC_IDIOMS)
            self.assertNotIn(name, mapper.PROFILES["strength"]["idioms"])


class LevelTests(unittest.TestCase):
    def test_level_functions_are_the_comparator_rules(self):
        E = library.level_eval
        self.assertEqual(E(("cmp_sub_s", 12, 3)), 9)
        self.assertEqual(E(("cmp_sub_s", 3, 12)), 0)
        self.assertEqual(E(("cmp_cmp_s", 12, 3)), 12)
        self.assertEqual(E(("cmp_cmp_s", 3, 12)), 0)
        self.assertEqual(E(("cmp_cmp_s", 7, 7)), 7)
        self.assertEqual(E(("attenuate_s", 15, 14)), 1)
        self.assertEqual(E(("attenuate_s", 3, 5)), 0)
        self.assertEqual(E(("dust_max_s", 4, ("const_s", 2))), 4)
        with self.assertRaises(KeyError):
            E(("nor", 1, 1))

    def test_const_s_matches_the_measured_barrel_levels(self):
        for n, want in ((4, 3), (26, 14), (2, 2)):
            items = [{"count": 1, "max_count": 1}] * n
            self.assertEqual(M.inventory_output(items, 27), want)

    def test_level_rows_reproduce_b_final_kill_and_generate_rows(self):
        if not CELL.exists():
            self.skipTest("cell fixture absent")
        doc = json.loads(CELL.read_bytes().decode("utf-8"))
        alphabet = doc["ports"]["cin"]["alphabet"]
        self.assertEqual(alphabet, [1, 2, 4, 10, 12])
        E = library.level_eval
        rows = {(r["a"], r["b"], r["cin"]): r for r in doc["gate_table"]}
        for cin in alphabet:
            kill = E(("dust_max_s", ("cmp_sub_s", cin, ("const_s", 8)), ("const_s", 2)))
            self.assertEqual(rows[(0, 0, cin)]["cout"], kill, cin)
            self.assertEqual(rows[(1, 1, cin)]["cout"], E(("const_s", 12)), cin)
            # sum on the alphabet: a xor b xor [cin >= 10]
            for a in (0, 1):
                for b in (0, 1):
                    bit = 1 if rows[(a, b, cin)]["sum"] > 0 else 0
                    self.assertEqual(bit, a ^ b ^ (1 if cin >= 10 else 0), (a, b, cin))


if __name__ == "__main__":
    unittest.main()
