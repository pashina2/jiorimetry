#!/usr/bin/env python3
"""tools/workbench/llmgen/test_capcell.py -- falsifiers for capcell.py: the
capture -> machine mapping, the Bench's observer / target / pinned / container
rules, tiling and the identity vocabulary. Hermetic except one test that
reads the committed B-?? capture when it is present."""

import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import capcell as CC                                       # noqa: E402
import machine as M                                        # noqa: E402
from library import DUST, LEVER, OBSERVER, COMPARATOR, REPEATER, SMOOTH_STONE   # noqa: E402

CAPTURE = ROOT / "notes" / "bench" / "artifacts" / "B-final" / "capture.r1.json"
SOLIDITY = ROOT / "data" / "workbench" / "physics" / "solidity.json"


def dust(power="0"):
    return "minecraft:redstone_wire[east=none,north=none,power=%s,south=none,west=none]" % power


def lever(on=False, face="floor"):
    return "minecraft:lever[face=%s,facing=north,powered=%s]" % (face, "true" if on else "false")


class ParseTests(unittest.TestCase):
    def test_roundtrip(self):
        s = "minecraft:comparator[facing=west,mode=subtract,powered=false]"
        name, props = CC.parse_block(s)
        self.assertEqual(name, "minecraft:comparator")
        self.assertEqual(CC.spell(name, props), s)
        self.assertEqual(CC.parse_block("minecraft:gray_wool"), ("minecraft:gray_wool", {}))

    def test_unterminated_state_is_refused(self):
        with self.assertRaises(CC.CapCellError):
            CC.parse_block("minecraft:lever[face=floor")

    def test_cells_of_wants_the_row_list(self):
        with self.assertRaises(CC.CapCellError):
            CC.cells_of({"scan": {"non_air": 3}})
        self.assertEqual(CC.cells_of({"scan": {"non_air": [[1, 2, 3, "minecraft:gray_wool"]]}}),
                         {(1, 2, 3): "minecraft:gray_wool"})


class MapTests(unittest.TestCase):
    def test_every_kind_goes_where_the_table_says(self):
        cells = {(0, 0, 0): "minecraft:gray_wool", (1, 0, 0): "minecraft:stone_brick_wall[up=true]",
                 (2, 0, 0): "minecraft:target[power=0]", (3, 0, 0): "minecraft:barrel[facing=up,open=false]",
                 (4, 0, 0): dust(), (5, 0, 0): "minecraft:observer[facing=west,powered=false]"}
        blocks, targets, report = CC.machine_blocks(cells)
        self.assertEqual(blocks[(0, 0, 0)], (SMOOTH_STONE, {}))
        self.assertNotIn((1, 0, 0), blocks)
        self.assertEqual(blocks[(2, 0, 0)], (SMOOTH_STONE, {}))
        self.assertEqual(targets, {(2, 0, 0)})
        self.assertEqual(blocks[(3, 0, 0)][0], "minecraft:barrel")
        self.assertEqual(blocks[(5, 0, 0)][0], OBSERVER)
        self.assertEqual(report["dropped"], {"minecraft:stone_brick_wall": 1})
        self.assertEqual(report["target"], 1)

    def test_unknown_kind_is_refused_not_dropped(self):
        with self.assertRaises(CC.CapCellError):
            CC.machine_blocks({(0, 0, 0): "minecraft:piston[extended=false,facing=up]"})

    def test_solidity_column_agrees_with_gap7(self):
        if not SOLIDITY.exists():
            self.skipTest("GAP-7 table absent")
        table = json.loads(SOLIDITY.read_bytes().decode("utf-8"))["blocks"]
        for block, (_kind, solid, _why) in CC.MAP.items():
            row = table.get(block)
            self.assertIsNotNone(row, block)
            self.assertEqual(bool(row["solid"]), bool(solid), block)

    def test_barrel_entities_reproduce_the_measured_levels(self):
        cells = {(0, 0, 0): "minecraft:barrel[facing=up,open=false]",
                 (1, 0, 0): "minecraft:barrel[facing=up,open=false]",
                 (2, 0, 0): "minecraft:barrel[facing=up,open=false]", (3, 0, 0): "minecraft:gray_wool"}
        be = CC.barrel_entities(cells, {(0, 0, 0): 4, "1,0,0": 26, (2, 0, 0): 2})
        levels = [M.comparator_output("minecraft:barrel", {}, be[p]) for p in [(0, 0, 0), (1, 0, 0), (2, 0, 0)]]
        self.assertEqual(levels, [3, 14, 2])
        with self.assertRaises(CC.CapCellError):
            CC.barrel_entities(cells, {(3, 0, 0): 1})


class ConnectionTests(unittest.TestCase):
    def test_dust_connects_to_a_target_but_not_to_a_stone(self):
        blocks = {(0, 0, 0): (DUST, {"power": "0"}), (1, 0, 0): (SMOOTH_STONE, {}),
                  (0, -1, 0): (SMOOTH_STONE, {}), (0, 0, -1): (DUST, {"power": "0"}), (0, -1, -1): (SMOOTH_STONE, {})}
        plain = CC.placement_state_t(blocks, set(), (0, 0, 0))
        target = CC.placement_state_t(blocks, {(1, 0, 0)}, (0, 0, 0))
        self.assertEqual(plain["east"], "none")
        self.assertEqual(target["east"], "side")
        self.assertEqual(plain, M.placement_state(blocks, (0, 0, 0)))


def observer_rig(on=False):
    """lever -> dust (watched by an observer whose back powers a dust)."""
    blocks = {
        (0, 0, 0): (LEVER, {"face": "floor", "facing": "north", "powered": "true" if on else "false"}),
        (0, -1, 0): (SMOOTH_STONE, {}),
        (1, 0, 0): (DUST, {"power": "0"}), (1, -1, 0): (SMOOTH_STONE, {}),
        (2, 0, 0): (OBSERVER, {"facing": "west", "powered": "false"}),
        (3, 0, 0): (SMOOTH_STONE, {}),
        (3, 1, 0): (DUST, {"power": "0"}),
    }
    return blocks


class BenchTests(unittest.TestCase):
    def test_observer_pulses_two_gt_on_a_change_of_the_faced_block(self):
        b = CC.Bench(observer_rig())
        b.dc_solve()
        b.set_levers({(0, 0, 0): True})
        self.assertIn((2, 0, 0), b.pending)
        b.step(); b.step()
        self.assertEqual(b.blocks[(2, 0, 0)][1]["powered"], "true")
        self.assertEqual(b.blocks[(3, 1, 0)][1]["power"], "15")
        b.step(); b.step()
        self.assertEqual(b.blocks[(2, 0, 0)][1]["powered"], "false")
        self.assertEqual(b.blocks[(3, 1, 0)][1]["power"], "0")

    def test_observer_is_silent_without_a_change(self):
        b = CC.Bench(observer_rig())
        b.dc_solve()
        self.assertEqual(b.run_to_rest(), 0)
        self.assertEqual(b.blocks[(3, 1, 0)][1]["power"], "0")

    def test_prime_books_only_unpowered_unqueued_observers_in_order(self):
        blocks = observer_rig()
        blocks[(2, 0, 2)] = (OBSERVER, {"facing": "west", "powered": "false"})
        blocks[(1, 0, 2)] = (SMOOTH_STONE, {})
        blocks[(2, 0, 4)] = (OBSERVER, {"facing": "west", "powered": "true"})
        blocks[(1, 0, 4)] = (SMOOTH_STONE, {})
        b = CC.Bench(blocks)
        b.dc_solve()
        n = b.prime([(2, 0, 2), (2, 0, 0), (2, 0, 4), (2, 0, 2)])
        self.assertEqual(n, 2)
        self.assertEqual(b.due_order(), [])
        b.gt += 2
        self.assertEqual(b.due_order(), [(2, 0, 2), (2, 0, 0)])

    def test_pinned_dust_keeps_its_power_and_powers_the_wool_under_it(self):
        blocks = {(0, 1, 0): (DUST, {"power": "0"}), (0, 0, 0): (SMOOTH_STONE, {}),
                  (1, 0, 0): (DUST, {"power": "0"}), (1, -1, 0): (SMOOTH_STONE, {})}
        held = CC.Bench(blocks, pinned={(0, 1, 0)})
        held.blocks[(0, 1, 0)][1]["power"] = "9"
        held.dc_solve()
        self.assertEqual(held.blocks[(0, 1, 0)][1]["power"], "9")
        self.assertEqual(held.blocks[(1, 0, 0)][1]["power"], "8")
        free = CC.Bench(blocks)
        free.blocks[(0, 1, 0)][1]["power"] = "9"
        free.dc_solve()
        self.assertEqual(free.blocks[(0, 1, 0)][1]["power"], "0")

    def test_bench_of_pins_the_given_state(self):
        cells = {(0, 1, 0): dust(), (0, 0, 0): "minecraft:gray_wool", (1, 0, 0): dust(), (1, -1, 0): "minecraft:gray_wool"}
        b = CC.bench_of(cells, pinned={(0, 1, 0)}, pinned_state={(0, 1, 0): {"power": 7}})
        b.dc_solve()
        self.assertEqual(b.dust_powers([(0, 1, 0), (1, 0, 0)]), (7, 6))

    def test_a_comparator_reads_a_declared_outside_cell(self):
        blocks = {(0, 0, 0): (COMPARATOR, {"facing": "west", "mode": "compare", "powered": "false"}),
                  (0, -1, 0): (SMOOTH_STONE, {}), (1, 0, 0): (DUST, {"power": "0"}), (1, -1, 0): (SMOOTH_STONE, {})}
        b = CC.Bench(blocks, containers={(-1, 0, 0): 5})
        b.dc_solve()
        self.assertEqual(b.cmp_out[(0, 0, 0)], 5)
        self.assertEqual(b.blocks[(1, 0, 0)][1]["power"], "5")
        silent = CC.Bench(blocks)
        silent.dc_solve()
        self.assertEqual(silent.blocks[(1, 0, 0)][1]["power"], "0")

    def test_machine_module_is_not_patched(self):
        self.assertNotIn(OBSERVER, M.KNOWN)
        self.assertEqual(M.SOLID, {SMOOTH_STONE, M.LAMP, M.REDSTONE_BLOCK})


class TileTests(unittest.TestCase):
    def test_tile_stacks_downward_from_the_top(self):
        band = {(0, 6, 0): "a", (0, 7, 0): "b"}
        t = CC.tile(band, 6, 7, 3, 13)
        self.assertEqual(t, {(0, 12, 0): "a", (0, 13, 0): "b", (0, 10, 0): "a", (0, 11, 0): "b",
                             (0, 8, 0): "a", (0, 9, 0): "b"})

    def test_tile_refuses_an_overlap(self):
        with self.assertRaises(CC.CapCellError):
            CC.tile({(0, 6, 0): "a", (0, 7, 0): "b"}, 6, 6, 2, 13)

    def test_identity_vocabulary(self):
        ref = {(0, 0, 0): "minecraft:gray_wool", (1, 0, 0): dust("3"), (2, 0, 0): "minecraft:target[power=0]",
               (3, 0, 0): "minecraft:lever"}
        obs = {(0, 0, 0): "minecraft:gray_wool", (1, 0, 0): dust("4"), (2, 0, 0): "minecraft:gray_wool",
               (4, 0, 0): "minecraft:lever"}
        idn = CC.identity(ref, obs)
        self.assertEqual((idn["identical"], idn["property_diff"], idn["id_diff"],
                          idn["only_reference"], idn["only_observed"], idn["identity"]),
                         (1, 1, 1, 1, 1, False))
        self.assertTrue(CC.identity(ref, dict(ref))["identity"])

    def test_cell_doc_round_trips_its_cells(self):
        band = {(5, 6, 7): dust(), (5, 7, 7): "minecraft:gray_wool"}
        doc = CC.cell_doc("c", band, 6, 7, {}, [], {"design": "test"})
        self.assertEqual(CC.cells_of_doc(doc), band)
        self.assertEqual(doc["census"], {"gray_wool": 1, "redstone_wire": 1})
        self.assertEqual(doc["source"], {"design": "test"})


class CaptureTests(unittest.TestCase):
    def test_b_final_capture_is_reproduced_with_declared_barrels(self):
        if not CAPTURE.exists():
            self.skipTest("capture absent")
        cells = CC.cells_of(json.loads(CAPTURE.read_bytes().decode("utf-8")))
        be = CC.barrel_entities(cells, {**{(2546, y, 199): 4 for y in range(48, 63, 2)},
                                        **{(2544, y, 199): 26 for y in range(47, 62, 2)}, (2541, 62, 201): 2})
        b = CC.bench_of(cells, block_entities=be, containers={(2535, y, 193): 1 for y in range(49, 64, 2)})
        rounds, ok = b.dc_solve()
        self.assertTrue(ok)
        pm = cm = gm = 0
        for p, s in cells.items():
            name, props = CC.parse_block(s)
            if name == DUST:
                got = b.blocks[p][1]
                pm += int(got["power"]) != int(props["power"])
                cm += sum(got[d] != props[d] for d in ("north", "east", "south", "west"))
            elif name in (COMPARATOR, M.REPEATER):
                gm += b.blocks[p][1]["powered"] != props["powered"]
        self.assertEqual((pm, cm, gm), (0, 0, 0))


class GuardTests(unittest.TestCase):
    def test_cp932_guard(self):
        src = (HERE / "capcell.py").read_text(encoding="utf-8")
        self.assertIn('sys.stdout.reconfigure(errors="backslashreplace")', src)


class FloorAndLatchTests(unittest.TestCase):
    """floors: a pin is a source the circuit may raise; dc_solve_both: the
    two-seed probe that finds the WORLD-4 p4 latch (2026-09-08)."""

    def floor_rig(self, on):
        return {
            (0, 0, 0): (DUST, {"power": "0"}), (0, -1, 0): (SMOOTH_STONE, {}),
            (1, 0, 0): (DUST, {"power": "0"}), (1, -1, 0): (SMOOTH_STONE, {}),
            (2, 0, 0): (LEVER, {"face": "floor", "facing": "north", "powered": "true" if on else "false"}),
            (2, -1, 0): (SMOOTH_STONE, {}),
        }

    def test_floored_dust_reads_the_max_of_its_floor_and_its_neighbours(self):
        off = CC.Bench(self.floor_rig(False), floors={(0, 0, 0): 3})
        off.dc_solve()
        self.assertEqual(off.dust_powers([(0, 0, 0), (1, 0, 0)]), (3, 2))
        on = CC.Bench(self.floor_rig(True), floors={(0, 0, 0): 3})
        on.dc_solve()
        self.assertEqual(on.dust_powers([(0, 0, 0), (1, 0, 0)]), (14, 15))

    def latch_rig(self):
        """WORLD-4 sol_p4: pin dust (0,1,1) -> repeater (0,1,2) facing north -> relay (0,1,3)
        -> dust (1,1,3) -> repeater (1,1,2) facing south -> relay (1,1,1), which touches the pin."""
        return {
            (0, 1, 1): (DUST, {"power": "0"}), (0, 0, 1): (SMOOTH_STONE, {}),
            (0, 1, 2): (REPEATER, {"facing": "north", "delay": "1", "locked": "false", "powered": "false"}),
            (0, 0, 2): (SMOOTH_STONE, {}),
            (0, 1, 3): (SMOOTH_STONE, {}),
            (1, 1, 3): (DUST, {"power": "0"}), (1, 0, 3): (SMOOTH_STONE, {}),
            (1, 1, 2): (REPEATER, {"facing": "south", "delay": "1", "locked": "false", "powered": "false"}),
            (1, 0, 2): (SMOOTH_STONE, {}),
            (1, 1, 1): (SMOOTH_STONE, {}),
        }

    def decay_rig(self):
        """The re-solved p4 shape: the same loop but with a wire hop (0,1,3)->(1,1,3) and
        subtract comparators, so the loop loses one level per round and decays."""
        return {
            (0, 1, 1): (DUST, {"power": "0"}), (0, 0, 1): (SMOOTH_STONE, {}),
            (0, 1, 2): (COMPARATOR, {"facing": "north", "mode": "subtract", "powered": "false"}),
            (0, 0, 2): (SMOOTH_STONE, {}),
            (0, 1, 3): (DUST, {"power": "0"}), (0, 0, 3): (SMOOTH_STONE, {}),
            (1, 1, 3): (DUST, {"power": "0"}), (1, 0, 3): (SMOOTH_STONE, {}),
            (1, 1, 2): (COMPARATOR, {"facing": "south", "mode": "subtract", "powered": "false"}),
            (1, 0, 2): (SMOOTH_STONE, {}),
            (1, 1, 1): (SMOOTH_STONE, {}),
        }

    def test_time_clause_sees_a_slow_decay_and_a_true_latch(self):
        # decaying loop: DC says 0 after T goes 15 -> 0, and the ticked circuit gets there, but slowly
        b = CC.Bench(self.decay_rig(), floors={(0, 1, 1): 15})
        b.dc_solve()
        self.assertEqual(b.dust_powers([(0, 1, 1), (1, 1, 3)]), (15, 14))
        gt, rested, last = b.settle_after({(0, 1, 1): 0}, [(0, 1, 1), (1, 1, 3)], limit=40)
        self.assertFalse(rested)                      # not within 40 gt
        self.assertGreater(b.dust_powers([(0, 1, 1)])[0], 0)
        b2 = CC.Bench(self.decay_rig(), floors={(0, 1, 1): 15})
        b2.dc_solve()
        gt, rested, last = b2.settle_after({(0, 1, 1): 0}, [(0, 1, 1), (1, 1, 3)], limit=120)
        self.assertTrue(rested)
        self.assertEqual(b2.dust_powers([(0, 1, 1), (1, 1, 3)]), (0, 0))
        self.assertGreater(gt, 40)
        # true latch: rests at once, but not at the DC solution
        c = CC.Bench(self.latch_rig(), floors={(0, 1, 1): 15})
        c.dc_solve()
        gt, rested, last = c.settle_after({(0, 1, 1): 0}, [(0, 1, 1)], limit=40)
        self.assertTrue(rested)
        self.assertEqual(c.dust_powers([(0, 1, 1)]), (15,))

    def test_a_held_pin_hides_the_latch_and_a_floored_pin_shows_it(self):
        held = CC.Bench(self.latch_rig(), pinned={(0, 1, 1)})
        _, conv, conv_hot, diff = held.dc_solve_both()
        self.assertTrue(conv and conv_hot)
        self.assertEqual(diff, {})
        floored = CC.Bench(self.latch_rig(), floors={(0, 1, 1): 0})
        rounds, conv, conv_hot, diff = floored.dc_solve_both()
        self.assertTrue(conv and conv_hot)
        self.assertIn((0, 1, 1), diff)
        self.assertEqual(diff[(0, 1, 1)], (("power", "0"), ("power", "15")))
        # left in the cold solution
        self.assertEqual(floored.dust_powers([(0, 1, 1)]), (0,))
        lit = CC.Bench(self.latch_rig(), floors={(0, 1, 1): 15})
        _, conv, conv_hot, diff = lit.dc_solve_both()
        self.assertEqual(diff, {})
        self.assertEqual(lit.dust_powers([(0, 1, 1), (1, 1, 3)]), (15, 15))


if __name__ == "__main__":
    unittest.main()
