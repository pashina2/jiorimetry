#!/usr/bin/env python3
"""FEED-1: the derivations `feed.py` makes instead of a seat, pinned.

Three joints, each the place where this tool could be wrong while every
printed number still looked healthy:

  (1) the REQUIREMENT -- expected values that quietly came from the Bench
      instead of from the function table would make the whole run circular;
  (2) the FEEDER -- a feeder that disturbs the layout it feeds, or a
      convention flipped (data lever ON = 0, control lever ON = 15), turns
      every row into an answer about a different circuit;
  (3) the REFUSAL -- a pin that cannot be fed must stop the job WITH ITS
      REASON and build no world; a refusal that silently becomes a world is
      the failure this tool exists to prevent.

Each pin is followed by the control that says it is not vacuous: a seeded
defect it must catch, and a harmless change it must ignore.

No server is launched here; every test is Bench-level or geometric. The live
runs are in `docs/world/record.md`.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for _p in (str(HERE), str(ROOT / "tools" / "llmgen"),
           str(ROOT / "tools" / "m9-worldgen")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import feed                                                # noqa: E402
import worldprobe                                          # noqa: E402

STONE = feed.STONE
DUST = feed.DUST


def wire_line(z0, z1, x=0, y=1):
    """A supported dust run along z, as a layout `blocks` list."""
    rows = []
    for z in range(z0, z1 + 1):
        rows.append([x, y, z, DUST])
        rows.append([x, y - 1, z, STONE])
    return rows


def toy_layout():
    """The smallest thing with a pin and a read: a short supported dust run.
    The read IS the pin cell, so the requirement `expect: a` says exactly what
    the feeder convention promises and nothing else."""
    return {"blocks": wire_line(0, 2), "barrels": {}}


def toy_job(tmp, blocks=None, levels=(0, 3), expect="a"):
    lay = toy_layout()
    if blocks:
        lay["blocks"] = lay["blocks"] + blocks
    path = Path(tmp) / "toy.json"
    path.write_bytes((json.dumps(lay) + "\n").encode("utf-8"))
    return {"name": "toy", "layout": str(path),
            "require": {"kind": "expect",
                        "pins": {"a": {"cell": [0, 1, 0],
                                       "levels": list(levels)}},
                        "outputs": [{"name": "O", "cell": [0, 1, 0],
                                     "expect": expect}]}}


class Requirement(unittest.TestCase):
    """(1) The expected values are the function table, not a measurement."""

    def test_alu_rows_are_the_relation(self):
        rows = {r["name"]: r for r in feed.rows_alu(2)}
        # ADD 2 + 3 + 1 = 6 = 2 (mod 4) carry 1
        r = rows["ADD_A2B3k1"]
        self.assertEqual(r["expect"]["r0"], 0)
        self.assertEqual(r["expect"]["r1"], 3)
        self.assertEqual(r["expect"]["f"], 3)
        # SUB 1 - 2 - 0 = -1 -> R = 3, F = 1 (borrow), and A - B - k == R - 4F
        r = rows["SUB_A1B2k0"]
        self.assertEqual((r["expect"]["r0"], r["expect"]["r1"]), (3, 3))
        self.assertEqual(r["expect"]["f"], 3)
        # AND / OR carry nothing out
        self.assertEqual(rows["AND_A3B2k1"]["expect"]["f"], 0)
        self.assertEqual(rows["OR_A1B2k0"]["expect"]["r0"], 3)
        self.assertEqual(rows["OR_A1B2k0"]["expect"]["r1"], 3)

    def test_every_alu_row_satisfies_its_own_relation(self):
        """The control on the table: the levels it hands out must satisfy the
        relation the checkers state, for every row of n = 1, 2 and 3."""
        for n in (1, 2, 3):
            rows = feed.rows_alu(n)
            self.assertEqual(len(rows), 4 * (2 ** n) * (2 ** n) * 2)
            for row in rows:
                mode, A, B, k = (row["key"]["mode"], row["key"]["A"],
                                 row["key"]["B"], row["key"]["k"])
                R = sum((row["expect"]["r%d" % i] // 3) << i for i in range(n))
                F = row["expect"]["f"] // 3
                if mode == "ADD":
                    self.assertEqual(A + B + k, R + (2 ** n) * F, row["name"])
                elif mode == "SUB":
                    self.assertEqual(A - B - k, R - (2 ** n) * F, row["name"])
                elif mode == "AND":
                    self.assertEqual((R, F), (A & B, 0), row["name"])
                else:
                    self.assertEqual((R, F), (A | B, 0), row["name"])

    def test_carry_is_the_carry_chain(self):
        self.assertEqual(feed.expected_carry("ADD", 1, 1, 0, 1), 1)
        self.assertEqual(feed.expected_carry("ADD", 1, 0, 0, 1), 0)
        self.assertEqual(feed.expected_carry("SUB", 0, 1, 0, 1), 1)
        self.assertEqual(feed.expected_carry("AND", 3, 3, 1, 1), 0)

    def test_placer0_rows_are_the_expect_expression(self):
        prob = {"fixed": [[0, 1, 0, DUST]], "pins": {
            "a": {"cell": [0, 1, 0], "levels": [0, 3]},
            "b": {"cell": [1, 1, 0], "levels": [0, 3]}},
            "outputs": [{"name": "O", "cell": [0, 1, 0],
                         "expect": "max(a,b)"}]}
        rows = feed.rows_expect(prob["pins"], prob["outputs"])
        self.assertEqual(len(rows), 4)
        self.assertEqual(sorted(r["expect"]["O"] for r in rows), [0, 3, 3, 3])


class Feeder(unittest.TestCase):
    """(2) The feeder delivers the level the convention promises, and the
    layout cannot tell it is there."""

    def search(self, entry, tmp):
        art = feed.load_artifact(entry, Path(tmp))
        feed.add_readout(art)
        s = feed.Searcher(art)
        return art, s.run()

    def test_data_feeder_is_found_and_reads_0_and_3(self):
        with tempfile.TemporaryDirectory() as tmp:
            art, fail = self.search(toy_job(tmp), tmp)
            self.assertEqual(fail, {})
            cand = art.feeders["a"][0]
            states = dict(cand.cells)
            self.assertEqual(sum(1 for s in states.values()
                                 if s.startswith("minecraft:comparator")), 1)
            self.assertIn(feed.BARREL, states.values())
            self.assertIn(feed.LEVER, states.values())
            blocks, barrels = feed.apply_feeders(art)
            self.assertEqual(set(barrels.values()), {feed.L3})
            rows = feed.verify(art, blocks, barrels)
            self.assertEqual([r["ok"] for r in rows], [True, True])
            # the inverted convention, in the readings themselves
            on = {r["levers_on"][cand.lever_name]: r["got"]["O"] for r in rows}
            self.assertEqual(on[True], 0)
            self.assertEqual(on[False], 3)

    def test_control_feeder_reads_0_and_15(self):
        with tempfile.TemporaryDirectory() as tmp:
            entry = toy_job(tmp, levels=(0, 15), expect="a")
            art, fail = self.search(entry, tmp)
            self.assertEqual(fail, {})
            cand = art.feeders["a"][0]
            self.assertEqual(cand.kind, "ctrl")
            self.assertEqual(len(cand.cells), 2)
            blocks, barrels = feed.apply_feeders(art)
            rows = feed.verify(art, blocks, barrels)
            self.assertEqual([r["ok"] for r in rows], [True, True])
            on = {r["levers_on"][cand.lever_name]: r["got"]["O"] for r in rows}
            self.assertEqual((on[True], on[False]), (15, 0))

    def test_seeded_defect_a_feeder_that_disturbs_is_rejected(self):
        """The control: a candidate whose side wire would drive a layout gate's
        side must be refused, and the reason must be the electrical one, not a
        collision."""
        with tempfile.TemporaryDirectory() as tmp:
            art = feed.load_artifact(toy_job(tmp), Path(tmp))
            s = feed.Searcher(art)
            s.run()
            cand = art.feeders["a"][0]
            # move the whole feeder one cell along z: the gate now feeds the
            # wire run's SECOND cell and the pin cell is left unfed
            moved = feed.Candidate(
                cand.kind, [((p[0], p[1], p[2] + 1), st) for p, st in cand.cells],
                (cand.lever[0], cand.lever[1], cand.lever[2] + 1), "a",
                (0, 1, 0), "moved")
            s2 = feed.Searcher(art)
            bad = s2.electrical_reject(moved, "a")
            self.assertIsNotNone(bad)
            self.assertEqual(bad[0], "electrical")

    def test_harmless_change_is_ignored(self):
        """The other half of the control: a solid block parked far away is not
        a reason to reject anything."""
        with tempfile.TemporaryDirectory() as tmp:
            entry = toy_job(tmp, blocks=[[9, 9, 9, STONE]])
            art, fail = self.search(entry, tmp)
            self.assertEqual(fail, {})

    def test_substitution_only_of_an_inert_floor_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            art = feed.load_artifact(
                toy_job(tmp, blocks=[[3, 0, 9, STONE], [5, 0, 9, STONE],
                                     [5, 1, 9, DUST]]), Path(tmp))
            self.assertTrue(feed.substitutable(art, (3, 0, 9)))
            # supports a dust -> not inert
            self.assertFalse(feed.substitutable(art, (5, 0, 9)))
            # a floor cell of the layout's own wire run touches dust
            self.assertFalse(feed.substitutable(art, (0, 0, 2)))
            # and a dust cell is not a floor block at all
            self.assertFalse(feed.substitutable(art, (0, 1, 2)))


class Refusal(unittest.TestCase):
    """(3) A pin that cannot be fed stops the job, with a reason."""

    def walled(self, tmp):
        """The toy pin walled in: every horizontal neighbour of the pin cell
        and of its support taken by a layout block."""
        wall = []
        for dx, dz in ((-1, 0), (1, 0), (0, -1)):
            wall.append([dx, 1, dz, STONE])
            wall.append([dx, 0, dz, STONE])
            wall.append([dx, 2, dz, STONE])
        wall.append([0, 2, 0, STONE])
        wall.append([0, -1, 0, STONE])
        return toy_job(tmp, blocks=wall)

    def test_walled_pin_is_refused_with_a_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            art = feed.load_artifact(self.walled(tmp), Path(tmp))
            feed.add_readout(art)
            fail = feed.Searcher(art).run()
            self.assertIn("a", fail)
            self.assertTrue(fail["a"]["tried"] > 0)
            self.assertTrue(set(fail["a"]["reasons"])
                            & {"collision", "side_or_back", "support"},
                            fail["a"]["reasons"])
            self.assertTrue(fail["a"]["examples"])
            self.assertTrue(all("detail" in e for e in fail["a"]["examples"]))

    def test_main_refuses_and_builds_no_world(self):
        with tempfile.TemporaryDirectory() as tmp:
            job = {"name": "walled", "artifacts": [self.walled(tmp)]}
            jp = Path(tmp) / "job.json"
            jp.write_bytes((json.dumps(job) + "\n").encode("utf-8"))
            out = Path(tmp) / "run"
            rc = feed.main([str(jp), "--out", str(out),
                            "--out-dir", str(Path(tmp) / "rep")])
            self.assertEqual(rc, 2)
            self.assertFalse((out / "world_build").exists())
            report = json.loads((Path(tmp) / "rep" / "walled.feed.json")
                                .read_text(encoding="utf-8"))
            self.assertEqual(report["refused"]["artifact"], "toy")
            self.assertIn("a", report["refused"]["pins"])

    def test_a_bistable_row_is_refused_and_named(self):
        """A pin cell the circuit can hold up by itself: cold and hot DC
        disagree, so the feeder is refused as `bistable` -- WORLD-4's p4
        latch, caught before a world exists.

        The loop: the pin drives repeater R1, R1 drives a wire, the wire drives
        repeater R2, and R2's front is the solid block beside the pin, which it
        strongly powers.  All zero is a solution; all lit is another."""
        latch = [[0, 1, 0, DUST], [0, 0, 0, STONE],
                 [0, 1, 1, "minecraft:repeater[facing=north,delay=1]"],
                 [0, 0, 1, STONE],
                 [0, 1, 2, DUST], [0, 0, 2, STONE],
                 [1, 1, 2, DUST], [1, 0, 2, STONE],
                 [1, 1, 1, "minecraft:repeater[facing=south,delay=1]"],
                 [1, 0, 1, STONE],
                 [1, 1, 0, STONE]]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "latch.json"
            body = json.dumps({"blocks": latch, "barrels": {}})
            path.write_bytes((body + chr(10)).encode("utf-8"))
            entry = {"name": "latch", "layout": str(path),
                     "require": {"kind": "expect",
                                 "pins": {"a": {"cell": [0, 1, 0],
                                                "levels": [0, 15]}},
                                 "outputs": [{"name": "O", "cell": [0, 1, 0],
                                              "expect": "a"}]}}
            art = feed.load_artifact(entry, Path(tmp))
            fail = feed.Searcher(art).run()
            self.assertIn("a", fail, "the latch must not be fed silently")
            self.assertIn("bistable", fail["a"]["reasons"])


class Spec(unittest.TestCase):
    """The spec the tool writes is one `worldprobe` accepts, and it splits."""

    def build(self, tmp):
        job = {"name": "toy", "artifacts": [toy_job(tmp)]}
        jp = Path(tmp) / "job.json"
        jp.write_bytes((json.dumps(job) + "\n").encode("utf-8"))
        out, rep = Path(tmp) / "run", Path(tmp) / "rep"
        rc = feed.main([str(jp), "--out", str(out), "--out-dir", str(rep)])
        return rc, out, rep

    def test_spec_validates_and_carries_the_wake_and_warm_regimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc, out, rep = self.build(tmp)
            self.assertEqual(rc, 0)
            self.assertTrue((out / "world_build" / "world" / "level.dat").exists())
            spec = worldprobe.load_spec(str(rep / "toy.spec.json"))
            names = [r["name"] for r in spec["regimes"]]
            self.assertEqual(names[:2], ["wake_on", "wake_off"])
            self.assertEqual(len([n for n in names if n.startswith("warm_")]), 2)
            self.assertEqual(len([n for n in names if n.startswith("v_")]), 2)
            for reg in spec["regimes"]:
                self.assertEqual("expect" in reg, reg["name"].startswith("v_"))
            # both candidate levels are read at the output cell
            reads = {r["name"] for r in spec["reads"]}
            self.assertEqual({"O_0", "O_3"} & reads, {"O_0", "O_3"})
            self.assertTrue(any(r.get("kind") == "nbt" for r in spec["reads"]))

    def test_rows_split_when_the_rcon_estimate_passes_the_ceiling(self):
        with tempfile.TemporaryDirectory() as tmp:
            job = {"name": "toy", "artifacts": [toy_job(tmp)]}
            jp = Path(tmp) / "job.json"
            jp.write_bytes((json.dumps(job) + "\n").encode("utf-8"))
            out, rep = Path(tmp) / "run", Path(tmp) / "rep"
            rc = feed.main([str(jp), "--out", str(out), "--out-dir", str(rep),
                            "--max-rcon", "1200"])
            self.assertEqual(rc, 0)
            specs = sorted(p.name for p in rep.glob("*.spec.json"))
            self.assertEqual(specs, ["toy_1.spec.json", "toy_2.spec.json"])
            rows = []
            for name in specs:
                spec = worldprobe.load_spec(str(rep / name))
                self.assertEqual([r["name"] for r in spec["regimes"]][:2],
                                 ["wake_on", "wake_off"])
                rows += [r["name"] for r in spec["regimes"]
                         if r["name"].startswith("v_")]
            self.assertEqual(len(rows), 2)         # every row driven once
            self.assertEqual(len(set(rows)), 2)


if __name__ == "__main__":                                 # pragma: no cover
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    unittest.main()
