#!/usr/bin/env python3
"""Measure a real redstone artifact on a throwaway byte-copy of a save, under
`tick freeze`, from a JSON spec (TR-1, `notes/2026-09-06-tr1-worldprobe-order.md`).

WHAT THIS IS. `notes/2026-09-06-bf1-live/probe_bfinal.py` measured one artifact
by hand: it hard-codes that artifact's bounding box, its sixteen input levers,
its eight output trapdoors and its one top lever. Everything in it that is NOT
about that artifact -- copy the region files, launch a template server, freeze
the tick, assert the capture back, drive a lever so the circuit actually sees
it, step one gt at a time and read a list of points -- is the same for every
artifact. This file is that part, with the artifact moved out into a spec.

The copy is of `region/` AND `entities/` (the latter only where it exists):
1.17 moved entities out of the chunk NBT into their own per-region file, so a
`region/`-only copy hands the probe a world whose minecarts, item frames and
item entities are silently gone -- hole 2 of
`notes/2026-09-06-state-holes-frame.md`. See `provision`.

WHAT IT DOES NOT DO. It writes no verdict. `settle_gt`, `final_value` and the
per-gt series are readings; whether a reading is right is the agent's sentence,
written in a bench note. The one concession is `expect`: if the spec states an
expectation, it is evaluated and recorded as true/false beside the reading,
never as a word like "pass".

Units are gt (game ticks) throughout. `tick step 1` advances exactly 1 gt, and
completion is confirmed with `time query gametime`, which `ServerWorld.tickTime()`
advances only on a tick that actually ran (1.20.6-yarn ServerWorld:302,321) --
so a reading taken after a step is a reading of a world that finished the step,
not of one still running it.

Subcommands:
    run      --spec <json> --run-dir <dir>    provision, measure, write results
    selftest --spec <json> --run-dir <dir>    four-arm flip test of the drive
    validate --spec <json>                    parse and check the spec, no world

`reports/raw/**` is NEVER written here: this is not one of ADR-0130's approved
writers. Output goes to the spec's `out_dir` as bench artifacts, carrying
`{"writer": "worldprobe", "report_kind": "bench_trace"}`.

Python stdlib only, plus `tools/world/rcon.py`.
"""

import argparse
import gzip
import hashlib
import json
import re
import shutil
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import rcon  # noqa: E402

WRITER = "worldprobe"
REPORT_KIND = "bench_trace"

#: `execute if <cond>` prints this when the condition holds.
PASS = "Test passed"

#: What a template server directory must lend a run dir.
TEMPLATE_ITEMS = ("fabric-server-launch.jar", "server.jar", "mods", "eula.txt",
                  "server.properties", "rcon-password.txt")

FACES = ("floor", "wall", "ceiling")
FACINGS = ("north", "south", "east", "west")

#: What a read point can be. `state` is an `execute if block` match -> one bit of
#: the per-gt series. `nbt` is `data get block` -> a verbatim string, sampled at
#: the two ends of a regime and never folded into the series (BF-3: a hopper's
#: `Items` is a state variable that no block state carries).
READ_KINDS = ("state", "nbt")

#: The gamerules a frozen measurement wants quiet, unless the spec says otherwise.
DEFAULT_GAMERULES = ("randomTickSpeed 0", "doFireTick false", "doWeatherCycle false",
                     "doMobSpawning false", "commandBlockOutput false")


class SpecError(ValueError):
    """A spec key is missing, unknown, or the wrong shape. Raised eagerly."""


class ProbeError(RuntimeError):
    """The world, the server, or a limit stopped the measurement."""


# --- spec ------------------------------------------------------------------

def _check_keys(obj, where, required, optional=()):
    """Fail loud on a missing OR an unknown key, at every nesting level.

    Unknown keys are rejected and not ignored: a spec is the only thing
    standing between a agent and a wrong measurement, and a silently dropped
    `settle_gt` would produce a number that still looks like a reading."""
    if not isinstance(obj, dict):
        raise SpecError("%s: expected an object, got %s"
                        % (where, type(obj).__name__))
    allowed = set(required) | set(optional)
    unknown = sorted(set(obj) - allowed)
    if unknown:
        raise SpecError("%s: unknown key(s) %s; allowed are %s"
                        % (where, ", ".join(unknown), ", ".join(sorted(allowed))))
    missing = sorted(k for k in required if k not in obj)
    if missing:
        raise SpecError("%s: missing key(s) %s" % (where, ", ".join(missing)))


def _int(value, where, low=None):
    if not isinstance(value, int) or isinstance(value, bool):
        raise SpecError("%s: expected an integer, got %r" % (where, value))
    if low is not None and value < low:
        raise SpecError("%s: expected >= %d, got %d" % (where, low, value))
    return value


def _pos(value, where):
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise SpecError("%s: expected [x, y, z], got %r" % (where, value))
    for i, v in enumerate(value):
        _int(v, "%s[%d]" % (where, i))
    return tuple(value)


def _validate_drives(drives):
    if not isinstance(drives, dict):
        raise SpecError("spec.drives: expected an object of name -> drive")
    for name, drive in drives.items():
        where = "spec.drives.%s" % name
        kind = drive.get("kind") if isinstance(drive, dict) else None
        if kind == "lever_bits":
            _check_keys(drive, where, ("kind", "positions", "face", "facing"), ("block",))
            if not isinstance(drive["positions"], list) or not drive["positions"]:
                raise SpecError("%s.positions: expected a non-empty list" % where)
            for i, p in enumerate(drive["positions"]):
                _pos(p, "%s.positions[%d]" % (where, i))
        elif kind == "lever":
            _check_keys(drive, where, ("kind", "pos", "face", "facing"), ("block",))
            _pos(drive["pos"], "%s.pos" % where)
        else:
            raise SpecError("%s.kind: expected lever_bits or lever, got %r"
                            % (where, kind))
        if drive["face"] not in FACES:
            raise SpecError("%s.face: expected one of %s, got %r"
                            % (where, "/".join(FACES), drive["face"]))
        if drive["facing"] not in FACINGS:
            raise SpecError("%s.facing: expected one of %s, got %r"
                            % (where, "/".join(FACINGS), drive["facing"]))
    return drives


def _validate_reads(reads):
    if not isinstance(reads, list):
        raise SpecError("spec.reads: expected a list of read points")
    seen_bits, names = {}, set()
    for i, read in enumerate(reads):
        where = "spec.reads[%d]" % i
        kind = read.get("kind", "state") if isinstance(read, dict) else None
        if kind == "nbt":
            # A container's contents are not a block state, so an `nbt` read has
            # no `match` to compare and no `bit` to spell: it is a verbatim
            # string, recorded beside the series and never inside it.
            _check_keys(read, where, ("name", "pos", "kind"), ("path",))
            if "path" in read and not (isinstance(read["path"], str) and read["path"]):
                raise SpecError("%s.path: expected a non-empty NBT path string, "
                                "got %r" % (where, read["path"]))
        elif kind == "state":
            _check_keys(read, where, ("name", "pos", "match"), ("bit", "kind"))
        else:
            raise SpecError("%s.kind: expected one of %s, got %r"
                            % (where, "/".join(READ_KINDS), kind))
        _pos(read["pos"], "%s.pos" % where)
        if read["name"] in names:
            raise SpecError("%s.name: %r is used twice" % (where, read["name"]))
        names.add(read["name"])
        if "bit" in read:
            bit = _int(read["bit"], "%s.bit" % where, 0)
            if bit in seen_bits:
                raise SpecError("%s.bit: bit %d is already read by %r"
                                % (where, bit, seen_bits[bit]))
            seen_bits[bit] = read["name"]
    return reads


def _validate_input_map(values, drives, where):
    if not isinstance(values, dict):
        raise SpecError("%s: expected an object of drive name -> value" % where)
    for drive_name in values:
        if drive_name not in drives:
            raise SpecError("%s: %r is not a declared drive (declared: %s)"
                            % (where, drive_name, ", ".join(sorted(drives)) or "none"))
    return values


def _validate_regime(regime, i, drives):
    where = "spec.regimes[%d]" % i
    _check_keys(regime, where, ("name", "inputs", "max_gt", "settle_gt"),
                ("trigger", "pre_inputs", "expect"))
    _int(regime["max_gt"], "%s.max_gt" % where, 0)
    _int(regime["settle_gt"], "%s.settle_gt" % where, 0)
    if regime["settle_gt"] > regime["max_gt"]:
        raise SpecError("%s: settle_gt %d exceeds max_gt %d -- no window could "
                        "ever be called settled"
                        % (where, regime["settle_gt"], regime["max_gt"]))
    _validate_input_map(regime["inputs"], drives, "%s.inputs" % where)
    if regime.get("pre_inputs") is not None:
        _validate_input_map(regime["pre_inputs"], drives, "%s.pre_inputs" % where)
    trigger = regime.get("trigger")
    if trigger is not None:
        tw = "%s.trigger" % where
        _check_keys(trigger, tw, ("pos", "hold_gt"), ("delay_gt",))
        pos = _pos(trigger["pos"], "%s.pos" % tw)
        hold = trigger["hold_gt"]
        if hold != "inf" and not (isinstance(hold, int) and not isinstance(hold, bool)
                                  and hold > 0):
            raise SpecError("%s.hold_gt: expected a positive integer or the "
                            "string inf, got %r" % (tw, hold))
        _int(trigger.get("delay_gt", 0), "%s.delay_gt" % tw, 0)
        if lever_by_pos(drives, pos) is None:
            raise SpecError("%s.pos: no declared lever drive sits at %r; the "
                            "attachment update needs its face and facing"
                            % (tw, list(pos)))
    if "expect" in regime:
        _check_keys(regime["expect"], "%s.expect" % where, (),
                    ("final_value", "settle_gt_at_most", "final_reads"))
    return regime


def validate_spec(spec):
    """Return the spec, or raise `SpecError` naming the offending key path."""
    _check_keys(spec, "spec", ("name", "world", "out_dir"),
                ("server", "identity", "drives", "reads", "regimes",
                 "selftest", "limits"))
    if not isinstance(spec["name"], str) or not spec["name"]:
        raise SpecError("spec.name: expected a non-empty string")
    if not isinstance(spec["out_dir"], str) or not spec["out_dir"]:
        raise SpecError("spec.out_dir: expected a non-empty string")

    world = spec["world"]
    _check_keys(world, "spec.world", ("template", "bbox"),
                ("source_save", "world_dir", "world_files"))
    if ("source_save" in world) == ("world_dir" in world):
        raise SpecError("spec.world: give exactly one of source_save (copy the "
                        "region files out of a save) or world_dir (reuse a "
                        "world directory that was already copied)")
    bbox = world["bbox"]
    _check_keys(bbox, "spec.world.bbox", ("min", "max"))
    lo = _pos(bbox["min"], "spec.world.bbox.min")
    hi = _pos(bbox["max"], "spec.world.bbox.max")
    if any(a > b for a, b in zip(lo, hi)):
        raise SpecError("spec.world.bbox: min %r is not <= max %r" % (list(lo), list(hi)))
    if "world_files" in world and not (
            isinstance(world["world_files"], list)
            and all(isinstance(f, str) for f in world["world_files"])):
        raise SpecError("spec.world.world_files: expected a list of relative paths")

    server = spec.get("server", {})
    _check_keys(server, "spec.server", (),
                ("host", "rcon_port", "java_xmx", "launch_timeout_s",
                 "rcon_timeout_s", "gamerules"))
    port = server.get("rcon_port", 25585)
    _int(port, "spec.server.rcon_port", 1)
    if port > 65535:
        raise SpecError("spec.server.rcon_port: expected a TCP port, got %r" % (port,))

    if "identity" in spec:
        _check_keys(spec["identity"], "spec.identity", ("capture",),
                    ("reference_region",))

    drives = _validate_drives(spec.get("drives", {}))
    _validate_reads(spec.get("reads", []))
    regimes = spec.get("regimes", [])
    if not isinstance(regimes, list):
        raise SpecError("spec.regimes: expected a list")
    for i, regime in enumerate(regimes):
        _validate_regime(regime, i, drives)

    if "selftest" in spec:
        _check_keys(spec["selftest"], "spec.selftest",
                    ("drive_inputs", "restore_inputs"), ("rest_inputs", "span_gt"))
        for key in ("drive_inputs", "restore_inputs", "rest_inputs"):
            if spec["selftest"].get(key) is not None:
                _validate_input_map(spec["selftest"][key], drives,
                                    "spec.selftest.%s" % key)
        if "span_gt" in spec["selftest"]:
            _int(spec["selftest"]["span_gt"], "spec.selftest.span_gt", 1)

    limits = spec.get("limits", {})
    _check_keys(limits, "spec.limits", (), ("max_rcon",))
    if "max_rcon" in limits:
        _int(limits["max_rcon"], "spec.limits.max_rcon", 1)
    return spec


def load_spec(path):
    text = Path(path).read_text(encoding="utf-8")
    try:
        spec = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SpecError("%s: not valid JSON (%s)" % (path, exc)) from exc
    return validate_spec(spec)


# --- geometry --------------------------------------------------------------

def region_coords(pos):
    """Region file coordinates of a block position: x >> 9, z >> 9.

    A region is 32x32 chunks and a chunk is 16 blocks, so a region spans 512
    blocks on each horizontal axis. The shift is the source of truth and it
    agrees with floor division here because Python floors negatives too."""
    return (pos[0] >> 9, pos[2] >> 9)


#: `forceload add` refuses more than this many chunks in one command
#: (net/minecraft/server/command/ForceLoadCommand: "Cannot force load more
#: than %s chunks at a time"). A generated artifact is wide -- SYN-1's 8 bit
#: adder is 48x6 = 288 chunks -- so the box is asked for in strips.
FORCELOAD_MAX_CHUNKS = 256


def forceload_tiles(lo, hi, max_chunks=FORCELOAD_MAX_CHUNKS):
    """The box as (x0, z0, x1, z1) strips, each of at most `max_chunks` chunks.

    The strips are cut on CHUNK boundaries and clamped back to the box, so
    their union is exactly the box's chunk set and no chunk is asked for
    twice. A box whose z extent alone exceeds the limit cannot be tiled this
    way and is refused rather than truncated.
    """
    cz = (hi[2] >> 4) - (lo[2] >> 4) + 1
    if cz > max_chunks:
        raise ProbeError("bbox spans %d chunks on z, more than the %d a single "
                         "forceload command accepts; this tiler cuts on x only"
                         % (cz, max_chunks))
    per = max_chunks // cz
    cx0, cx1 = lo[0] >> 4, hi[0] >> 4
    tiles = []
    cx = cx0
    while cx <= cx1:
        end = min(cx + per - 1, cx1)
        tiles.append((max(lo[0], cx << 4), lo[2],
                      min(hi[0], (end << 4) + 15), hi[2]))
        cx = end + 1
    return tiles


def region_files_for_bbox(lo, hi, kind="region"):
    """Every <kind>/r.<rx>.<rz>.mca the box touches, in a stable order.

    A box that straddles a region boundary needs BOTH files; copying only the
    one holding the min corner silently truncates the artifact.

    `kind` is the save subdirectory: "region" for blocks, "entities" for the
    SEPARATE per-region entity storage 1.17 split out (see `provision`). The
    numbering is identical, which is the whole reason one function answers for
    both."""
    rx0, rz0 = region_coords(lo)
    rx1, rz1 = region_coords(hi)
    return ["%s/r.%d.%d.mca" % (kind, rx, rz)
            for rx in range(min(rx0, rx1), max(rx0, rx1) + 1)
            for rz in range(min(rz0, rz1), max(rz0, rz1) + 1)]


_OPPOSITE = {"north": "south", "south": "north", "east": "west", "west": "east",
             "up": "down", "down": "up"}
_STEP = {"north": (0, 0, -1), "south": (0, 0, 1),
         "east": (1, 0, 0), "west": (-1, 0, 0),
         "up": (0, 1, 0), "down": (0, -1, 0)}


def lever_direction(face, facing):
    """`WallMountedBlock.getDirection` (1.20.6-yarn WallMountedBlock.java:60-70).

    floor -> UP, ceiling -> DOWN, wall -> FACING. The facing property is
    carried on all three faces but only the wall face reads it, so 8 of the 12
    (face, facing) states share their answer with three siblings."""
    if face == "floor":
        return "up"
    if face == "ceiling":
        return "down"
    if face == "wall":
        if facing not in FACINGS:
            raise SpecError("lever facing %r is not one of %s"
                            % (facing, "/".join(FACINGS)))
        return facing
    raise SpecError("lever face %r is not one of %s" % (face, "/".join(FACES)))


def lever_attachment(pos, face, facing):
    """The block a lever is mounted ON: pos.offset(getDirection().getOpposite())."""
    dx, dy, dz = _STEP[_OPPOSITE[lever_direction(face, facing)]]
    return (pos[0] + dx, pos[1] + dy, pos[2] + dz)


def neighbours(pos):
    """The six orthogonal neighbours, in a fixed order."""
    return [(pos[0] + dx, pos[1] + dy, pos[2] + dz)
            for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 1, 0),
                               (0, -1, 0), (0, 0, 1), (0, 0, -1))]


def lever_by_pos(drives, pos):
    """(name, drive, bit index or None) for the declared lever at `pos`."""
    pos = tuple(pos)
    for name in sorted(drives):
        drive = drives[name]
        if drive["kind"] == "lever" and tuple(drive["pos"]) == pos:
            return (name, drive, None)
        if drive["kind"] == "lever_bits":
            for i, p in enumerate(drive["positions"]):
                if tuple(p) == pos:
                    return (name, drive, i)
    return None


# --- NBT (just enough to read one int) --------------------------------------

_FIXED = {1: 1, 2: 2, 3: 4, 4: 8, 5: 4, 6: 8}


def _i32(raw, i):
    return int.from_bytes(raw[i:i + 4], "big", signed=True)


def _skip_payload(raw, i, tid):
    if tid in _FIXED:
        return i + _FIXED[tid]
    if tid == 7:                                        # byte array
        return i + 4 + _i32(raw, i)
    if tid == 8:                                        # string
        return i + 2 + int.from_bytes(raw[i:i + 2], "big")
    if tid == 9:                                        # list
        sub, n, i = raw[i], _i32(raw, i + 1), i + 5
        for _ in range(max(n, 0)):
            i = _skip_payload(raw, i, sub)
        return i
    if tid == 10:                                       # compound
        return _skip_compound(raw, i)
    if tid == 11:                                       # int array
        return i + 4 + 4 * _i32(raw, i)
    if tid == 12:                                       # long array
        return i + 4 + 8 * _i32(raw, i)
    raise ProbeError("unknown NBT tag id %d" % tid)


def _entries(raw, i):
    """Yield (name, tag id, payload index, next index) for one compound."""
    while True:
        tid = raw[i]
        if tid == 0:
            return
        n = int.from_bytes(raw[i + 1:i + 3], "big")
        name = raw[i + 3:i + 3 + n].decode("utf-8", "replace")
        payload = i + 3 + n
        nxt = _skip_payload(raw, payload, tid)
        yield name, tid, payload, nxt
        i = nxt


def _skip_compound(raw, i):
    for _name, _tid, _payload, nxt in _entries(raw, i):
        i = nxt
    return i + 1


def nbt_int(raw, path):
    """The TAG_Int at `path` under the root compound, or None.

    A path walk and not a byte scan: a real level.dat carries TWO DataVersion
    ints (the world's and the player's), so a scan would have to guess which
    one it had found."""
    if not raw or raw[0] != 10:
        raise ProbeError("not an NBT compound (first tag id %r)"
                         % (raw[0] if raw else None))
    i = 3 + int.from_bytes(raw[1:3], "big")             # root name, then entries
    for step_name in path[:-1]:
        found = None
        for name, tid, payload, _nxt in _entries(raw, i):
            if name == step_name and tid == 10:
                found = payload
                break
        if found is None:
            return None
        i = found
    for name, tid, payload, _nxt in _entries(raw, i):
        if name == path[-1] and tid == 3:
            return _i32(raw, payload)
    return None


def data_version(level_dat):
    """Data.DataVersion of a level.dat, gzipped or not."""
    blob = Path(level_dat).read_bytes()
    raw = gzip.decompress(blob) if blob[:2] == b"\x1f\x8b" else blob
    value = nbt_int(raw, ["Data", "DataVersion"])
    if value is None:
        raise ProbeError("%s: no Data.DataVersion" % level_dat)
    return value


# --- provisioning ----------------------------------------------------------

def assert_not_a_save(run_dir, source):
    """The run dir may never be, contain, or sit inside the source save.

    Order item 4: a save path in a spec is a COPY SOURCE and nothing else.
    Everything this file writes to a world goes through a server whose working
    directory is the run dir, so this single check covers every setblock, fill
    and forceload a spec can ask for."""
    run = Path(run_dir).resolve()
    if any(part == "saves" for part in run.parts):
        raise ProbeError("run dir %s is under a saves directory; a probe never "
                         "writes into a save" % run)
    if source is None:
        return
    src = Path(source).resolve()
    if run == src or src in run.parents or run in src.parents:
        raise ProbeError("run dir %s overlaps the read-only source %s" % (run, src))


def provision(spec, run_dir):
    """Build a throwaway server directory. Reads the source, never writes it."""
    world = spec["world"]
    run_dir = Path(run_dir)
    template = Path(world["template"])
    source = world.get("source_save") or world.get("world_dir")
    assert_not_a_save(run_dir, source)
    run_dir.mkdir(parents=True, exist_ok=False)

    for name in TEMPLATE_ITEMS:
        src = template / name
        if not src.exists():
            raise ProbeError("template %s has no %s" % (template, name))
        (shutil.copytree if src.is_dir() else shutil.copy2)(src, run_dir / name)

    info = {"run_dir": str(run_dir), "template": str(template),
            "mode": "world_dir" if world.get("world_dir") else "source_save",
            "source": str(source), "copied": [], "absent": []}

    if world.get("world_dir"):
        # The world was copied out of the save by an earlier run; take it whole
        # and drop the lock the previous server left behind.
        shutil.copytree(Path(world["world_dir"]), run_dir / "world")
        lock = run_dir / "world" / "session.lock"
        if lock.exists():
            lock.unlink()
        info["copied"].append({"rel": ".", "kind": "whole world directory"})
    else:
        shutil.copytree(template / "world", run_dir / "world")
        lo = tuple(world["bbox"]["min"])
        hi = tuple(world["bbox"]["max"])
        explicit = world.get("world_files")
        if explicit:
            rels, optional = list(explicit), []
        else:
            rels = ["level.dat"] + region_files_for_bbox(lo, hi)
            # HOLE 2 of `notes/2026-09-06-state-holes-frame.md`: since 1.17 an
            # entity does not live in the chunk NBT, it lives in a SEPARATE
            # `entities/r.<rx>.<rz>.mca` with the same numbering. A copy that
            # takes `region/` alone therefore hands the probe a world with no
            # minecart, no item frame and no item entity that was already in
            # the box -- silently, because the server happily generates an
            # empty entity storage for chunks it finds none for. So the same
            # region numbers are copied out of `entities/` too.
            #
            # OPTIONAL, not required, and that asymmetry is deliberate: a
            # missing `region/` file means the box is not in the save and the
            # probe would measure the template's void, while a missing (or
            # 0-byte, which is what the observed save has) `entities/` file means the
            # box holds no entities -- a fact, not a fault. Absent ones are
            # named in `info["absent"]` so a record can say which.
            optional = region_files_for_bbox(lo, hi, kind="entities")
        save = Path(world["source_save"])

        def _copy(rel):
            src, dst = save / rel, run_dir / "world" / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            info["copied"].append({
                "rel": rel, "bytes": src.stat().st_size,
                "src_mtime": src.stat().st_mtime,
                "sha256": hashlib.sha256(dst.read_bytes()).hexdigest()})

        for rel in rels:
            if not (save / rel).exists():
                raise ProbeError("source save %s has no %s" % (save, rel))
            _copy(rel)
        for rel in optional:
            if not (save / rel).exists():
                info["absent"].append(rel)
                continue
            _copy(rel)

    template_level = template / "world" / "level.dat"
    info["data_version"] = {
        "world": data_version(run_dir / "world" / "level.dat"),
        "template": data_version(template_level) if template_level.exists() else None}
    dv = info["data_version"]
    if dv["template"] is not None and dv["world"] != dv["template"]:
        raise ProbeError("DataVersion mismatch: the copied world is %d and the "
                         "template server's own world is %d -- the template is "
                         "the wrong Minecraft version for this save"
                         % (dv["world"], dv["template"]))
    (run_dir / "provision.json").write_bytes(
        json.dumps(info, indent=1).encode("utf-8"))
    return info


def launch(run_dir, log_path, xmx="3G", timeout=300):
    run_dir = Path(run_dir)
    handle = open(log_path, "w", encoding="utf-8", errors="replace", newline="\n")
    proc = subprocess.Popen(["java", "-Xmx" + xmx, "-jar",
                             "fabric-server-launch.jar", "nogui"],
                            cwd=str(run_dir), stdout=handle, stderr=subprocess.STDOUT)
    start = time.time()
    while True:
        handle.flush()
        text = Path(log_path).read_text(encoding="utf-8", errors="replace")
        if "Done (" in text:
            return proc, handle
        if proc.poll() is not None:
            raise ProbeError("server exited before Done ( -- see %s" % log_path)
        if time.time() - start > timeout:
            raise ProbeError("server did not report Done ( within %ds" % timeout)
        time.sleep(1.0)


def port_is_free(host, port, timeout=1.0):
    """True when nothing is listening -- another agent's server may hold it."""
    sock = socket.socket()
    sock.settimeout(timeout)
    try:
        sock.connect((host, port))
    except OSError:
        return True
    else:
        return False
    finally:
        sock.close()


def set_rcon_port(run_dir, port):
    """Rewrite the RUN DIR copy of server.properties.

    The template is never edited: it is shared with every other agent's run, and
    a second agent measuring at the same time must be able to take its own
    port without this one moving under it."""
    path = Path(run_dir) / "server.properties"
    out, seen = [], False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("rcon.port="):
            out.append("rcon.port=%d" % port)
            seen = True
        else:
            out.append(line)
    if not seen:
        out.append("rcon.port=%d" % port)
    path.write_bytes(("\n".join(out) + "\n").encode("utf-8"))
    return port


# --- rcon session ----------------------------------------------------------

class Session:
    """One RCON connection that counts and logs every roundtrip."""

    def __init__(self, host, port, password, log_path, timeout=60, limit=None):
        self._rid = 1
        self._log = open(log_path, "w", encoding="utf-8", newline="\n")
        self._sock = socket.create_connection((host, port), timeout=timeout)
        rcon.send_packet(self._sock, self._rid, rcon.TYPE_LOGIN, password)
        rid, _t, _p = rcon.recv_packet(self._sock)
        if rid == -1:
            raise ProbeError("RCON authentication failed on %s:%d" % (host, port))
        self.n = 0
        self.limit = limit
        self.phase = "connect"
        self.by_phase = {}

    def send(self, cmd):
        if self.limit is not None and self.n >= self.limit:
            raise ProbeError("rcon roundtrip limit %d reached "
                             "(spec.limits.max_rcon); the measurement is "
                             "incomplete and no result is claimed" % self.limit)
        self._rid += 1
        self.n += 1
        self.by_phase[self.phase] = self.by_phase.get(self.phase, 0) + 1
        rcon.send_packet(self._sock, self._rid, rcon.TYPE_COMMAND, cmd)
        _rid, _t, payload = rcon.recv_packet(self._sock)
        self._log.write("> " + cmd + "\n< " + str(payload).replace("\n", "\\n") + "\n")
        if self.n % 200 == 0:
            self._log.flush()
        return payload

    def close(self):
        self._log.flush()
        self._log.close()
        try:
            self._sock.close()
        except OSError:
            pass


# --- primitives ------------------------------------------------------------

def gametime(s):
    m = re.search(r"(-?\d+)", s.send("time query gametime"))
    if not m:
        raise ProbeError("cannot parse time query gametime")
    return int(m.group(1))


def step(s, n=1, timeout=30.0):
    """Advance exactly n gt and return only once they have actually run."""
    t0 = gametime(s)
    s.send("tick step %d" % n)
    start = time.time()
    while True:
        t = gametime(s)
        if t >= t0 + n:
            return t
        if time.time() - start > timeout:
            raise ProbeError("tick step %d did not complete (gametime %d -> %d)"
                             % (n, t0, t))
        time.sleep(0.01)


def is_block(s, pos, state):
    return PASS in s.send("execute if block %d %d %d %s"
                          % (pos[0], pos[1], pos[2], state))


def update_attachment(s, pos, face, facing):
    """Deliver the neighbour update setblock omits when it places a lever.

    `LeverBlock.updateNeighbors` (1.20.6-yarn LeverBlock.java:170-172) makes TWO
    calls -- at the lever, and at the block it is attached to:

        world.updateNeighborsAlways(pos, this);
        world.updateNeighborsAlways(pos.offset(getDirection(state).getOpposite()), this);

    Only togglePower() (a real click) and onStateReplaced() reach it, and
    onStateReplaced early-returns when a lever is replaced by a lever
    (LeverBlock.java:143). SetBlockCommand (SetBlockCommand.java:53) issues only
    updateNeighbors(pos), so the block the lever powers is notified but the
    blocks that READ that block never are, and nothing propagates: BF-1 watched
    a whole adder sit still for 200 gt after a setblock flip.

    Scarpet update(p) delivers an update TO p; it does NOT update the
    neighbours of p (BF-1 measured that too -- updating only the attached block
    still moved nothing). So this issues the update at each of the SIX
    neighbours of the attached block, which is what updateNeighborsAlways does.
    Returns the six positions it touched."""
    attached = lever_attachment(pos, face, facing)
    touched = neighbours(attached)
    for p in touched:
        s.send("script run update(%d,%d,%d)" % p)
    return touched


def scarpet_ok(s):
    reply = s.send("script run 2+3")
    return ("5" in reply), reply.strip()


def lever_state(drive, powered):
    block = drive.get("block", "minecraft:lever")
    return "%s[face=%s,facing=%s,powered=%s]" % (
        block, drive["face"], drive["facing"], "true" if powered else "false")


def drive_positions(drive):
    """The lever positions a drive owns, bit 0 first for a bit vector."""
    if drive["kind"] == "lever":
        return [tuple(drive["pos"])]
    return [tuple(p) for p in drive["positions"]]


def wanted_states(drive, value):
    """[(pos, powered)] for one drive at one value."""
    if drive["kind"] == "lever":
        return [(tuple(drive["pos"]), bool(value))]
    return [(tuple(p), bool((int(value) >> i) & 1))
            for i, p in enumerate(drive["positions"])]


def set_drive(s, drive, value, do_update=True):
    """Set one drive to `value` and wake the circuit. Returns changed positions.

    Only levers that must change are written: setblock of an identical state
    fails and does not call updateNeighbors (SetBlockCommand:50-53), so
    rewriting an unchanged lever costs a roundtrip and delivers nothing."""
    changed = []
    for pos, powered in wanted_states(drive, value):
        if is_block(s, pos, lever_state(drive, powered)):
            continue
        s.send("setblock %d %d %d %s" % (pos + (lever_state(drive, powered),)))
        if do_update:
            update_attachment(s, pos, drive["face"], drive["facing"])
        changed.append([list(pos), powered])
    return changed


def apply_inputs(s, drives, values, do_update=True):
    changed = []
    for name in sorted(values):
        changed.extend(set_drive(s, drives[name], values[name], do_update))
    return changed


def state_reads(reads):
    """The read points that spell the per-gt series, in spec order."""
    return [r for r in reads if r.get("kind", "state") == "state"]


def nbt_reads(reads):
    """The read points answered by `data get block`, in spec order."""
    return [r for r in reads if r.get("kind") == "nbt"]


def read_points(s, reads):
    return [1 if is_block(s, tuple(r["pos"]), r["match"]) else 0
            for r in state_reads(reads)]


def read_nbt(s, reads):
    """{name: the server's verbatim reply} for every `nbt` read point.

    The reply is stored as it came back and is not parsed: a `data get` answer
    carries counts, slots, ids and components, and the agent's sentence is
    written against the text the server actually said."""
    out = {}
    for r in nbt_reads(reads):
        cmd = "data get block %d %d %d" % tuple(r["pos"])
        if r.get("path"):
            cmd += " " + r["path"]
        out[r["name"]] = {"command": cmd, "reply": s.send(cmd)}
    return out


def reads_value(reads, sample):
    """The integer the bit-carrying read points spell, or None if none do."""
    bits = [(r["bit"], v) for r, v in zip(state_reads(reads), sample) if "bit" in r]
    if not bits:
        return None
    return sum(v << b for b, v in bits)


def first_stable(series, need):
    """First index g with series[g..g+need] all equal to series[g]."""
    if need == 0:
        return 0 if series else None
    for g in range(len(series)):
        if g + need >= len(series):
            return None
        if all(series[g + k] == series[g] for k in range(1, need + 1)):
            return g
    return None


def last_change_gt(changes):
    """The gt of the last row `compress` emitted -- the last gt the reads moved.

    `compress` always emits a row for gt 0, so a series that never moved reads 0,
    not null; null means there was no series at all. Recorded beside
    `first_stable_gt` and never in place of it: `first_stable_gt` can fire on an
    intermediate plateau (BF-2, `notes/2026-09-06-bf1-record.md` section 7.3,
    `G2a-hold8` returned 12 for a series whose last change was at 26), and this
    number is only unambiguous for a series that ran to its limit -- hence the
    `truncated` reading beside it."""
    return changes[-1][0] if changes else None


def plateau_flag(first_stable, last_change):
    """True when the settle criterion fired before the series stopped moving.

    None when either number is missing: not comparable is not the same as false."""
    if first_stable is None or last_change is None:
        return None
    return first_stable != last_change


def compress(series, reads):
    """[[gt, bitstring, value]], one row per change only."""
    rows, prev = [], None
    for gt, sample in enumerate(series):
        if sample != prev:
            rows.append([gt, "".join(str(v) for v in sample),
                         reads_value(reads, sample)])
            prev = sample
    return rows


# --- measurement -----------------------------------------------------------

def prepare(s, spec):
    lo = tuple(spec["world"]["bbox"]["min"])
    hi = tuple(spec["world"]["bbox"]["max"])
    for x0, z0, x1, z1 in forceload_tiles(lo, hi):
        s.send("forceload add %d %d %d %d" % (x0, z0, x1, z1))
    for rule in spec.get("server", {}).get("gamerules", DEFAULT_GAMERULES):
        s.send("gamerule " + rule)
    time.sleep(2.0)          # let the forceloaded chunks arrive while it still ticks
    s.send("tick freeze")    # BEFORE the first setblock
    return s.send("tick query")


def identity_from_region(spec, out):
    """The same verdict, read out of a save's region files. ZERO rcon.

    OPT-IN, and the default stays the rcon path: this reads a save DIRECTLY
    and answers about the bytes on disk at the last autosave, while the rcon
    path answers about the world the running server holds. Those are not the
    same question, and a caller who wants the second must not get the first
    by accident -- so this runs only when the spec names
    `identity.reference_region`.

    WHY IT EXISTS (SCALE-1, measured 2026-09-06): `identity` asks
    `is_block` once per captured row, and the row counts here are 2,225 for
    the bench board and 43,681 for the operator's CPU. A per-row roundtrip
    over rcon needs a launched server before it can answer at all;
    `regioncap` reads the same rows in 0.095 s at 2,225 rows and 1.82 s at
    43,681 with no server, no Minecraft and no `session.lock` contact.

    The difference classes are `regioncap.classify`'s, which are the same
    three this function's rcon arm reports -- id, property, count -- so the
    verdict word does not change with the route.
    """
    import tempfile
    harness = Path(__file__).resolve().parent
    if str(harness) not in sys.path:
        sys.path.insert(0, str(harness))
    import regioncap

    capture = Path(spec["identity"]["capture"])
    save = spec["identity"]["reference_region"]
    document = json.loads(capture.read_text(encoding="utf-8"))
    rows = regioncap.reference_rows(document)
    box = document["bbox"]
    bbox = list(box["min"]) + list(box["max"])
    with tempfile.TemporaryDirectory() as scratch:
        got = regioncap.capture(save, bbox, scratch)
    result = regioncap.classify(rows, got["scan"]["non_air"])
    id_fail = result["id_difference"]
    prop_fail = result["property_difference"]
    count_fail = result["only_in_reference"] + result["only_in_region"]
    out["identity"] = {
        "capture": str(capture), "rows": len(rows),
        "id_fail": len(id_fail), "prop_fail": len(prop_fail),
        "count_fail": len(count_fail),
        "id_fail_rows": [[r[0][0], r[0][1], r[0][2], r[1]]
                         for r in id_fail[:40]],
        "prop_fail_rows": [[r[0][0], r[0][1], r[0][2], r[1]]
                           for r in prop_fail[:40]],
        # WHICH INSTRUMENT ANSWERED. A verdict that cannot name its own
        # route is a verdict a later reader attributes to the wrong world:
        # the region files are the LAST AUTOSAVE, the server is NOW.
        "source": "regioncap",
        "reference_region": str(save),
        "rcon_roundtrips": 0,
        "freshness": got["provenance"]["freshness"],
        "world_open": got["provenance"]["world_open"],
    }
    print("identity rows=%d id_fail=%d prop_fail=%d count_fail=%d "
          "(regioncap, 0 rcon)"
          % (len(rows), len(id_fail), len(prop_fail), len(count_fail)),
          flush=True)
    return not id_fail


def identity(s, spec, out):
    """Assert every captured row back, splitting id differences from property ones.

    An id difference means the copy is not the capture's world. A property
    difference (power, powered, open, ...) means it IS that world, read at a
    different input state -- the normal case for a world that has already been
    driven. The two are counted apart and neither is a verdict."""
    if spec["identity"].get("reference_region"):
        return identity_from_region(spec, out)
    capture = Path(spec["identity"]["capture"])
    rows = json.loads(capture.read_text(encoding="utf-8"))["scan"]["non_air"]
    id_fail, prop_fail = [], []
    for x, y, z, state in rows:
        if is_block(s, (x, y, z), state):
            continue
        if is_block(s, (x, y, z), state.split("[")[0]):
            prop_fail.append([x, y, z, state])
        else:
            id_fail.append([x, y, z, state])
    out["identity"] = {"capture": str(capture), "rows": len(rows),
                       "id_fail": len(id_fail), "prop_fail": len(prop_fail),
                       "id_fail_rows": id_fail[:40], "prop_fail_rows": prop_fail[:40],
                       "source": "rcon", "rcon_roundtrips": len(rows)}
    print("identity rows=%d id_fail=%d prop_fail=%d"
          % (len(rows), len(id_fail), len(prop_fail)), flush=True)
    return not id_fail


def settle_here(s, spec, limit, need):
    """Step until the read points hold for `need` gt. Returns (gt, series)."""
    reads = spec.get("reads", [])
    series = [read_points(s, reads)]
    for _gt in range(1, limit + 1):
        step(s, 1)
        series.append(read_points(s, reads))
        g = first_stable(series, need)
        if g is not None:
            return g, series
    return first_stable(series, need), series


def run_regime(s, spec, regime, out):
    """One input change, one optional trigger schedule, one per-gt series.

    gt 0 of the series is the frozen tick in which the inputs change."""
    drives = spec.get("drives", {})
    reads = spec.get("reads", [])
    trigger = regime.get("trigger")
    lever = lever_by_pos(drives, tuple(trigger["pos"])) if trigger else None

    pre = {}
    if lever:
        set_drive(s, lever[1], False)
    if regime.get("pre_inputs"):
        apply_inputs(s, drives, regime["pre_inputs"])
        pre_gt, pre_series = settle_here(s, spec, regime["max_gt"], regime["settle_gt"])
        pre_last = last_change_gt(compress(pre_series, reads))
        pre = {"inputs": regime["pre_inputs"], "settle_gt": pre_gt,
               "first_stable_gt": pre_gt, "last_change_gt": pre_last,
               "plateau": plateau_flag(pre_gt, pre_last),
               "truncated": len(pre_series) - 1 < regime["max_gt"],
               "value": reads_value(reads, pre_series[-1]),
               "bits": "".join(str(v) for v in pre_series[-1])}

    nbt_before = read_nbt(s, reads)
    delay = trigger.get("delay_gt", 0) if trigger else 0
    hold = trigger["hold_gt"] if trigger else None
    off_at = None if hold in (None, "inf") else delay + int(hold)

    events = []
    changed = apply_inputs(s, drives, regime["inputs"])
    if trigger and delay == 0 and set_drive(s, lever[1], True):
        events.append(["on", 0])
    series = [read_points(s, reads)]
    for gt in range(1, regime["max_gt"] + 1):
        step(s, 1)
        if trigger and delay and gt == delay and set_drive(s, lever[1], True):
            events.append(["on", gt])
        if off_at is not None and gt == off_at and set_drive(s, lever[1], False):
            events.append(["off", gt])
        series.append(read_points(s, reads))

    g = first_stable(series, regime["settle_gt"])
    final = series[-1]
    changes = compress(series, reads)
    last = last_change_gt(changes)
    rec = {"name": regime["name"], "inputs": regime["inputs"], "pre": pre,
           "trigger": trigger, "trigger_events_gt": events,
           "levers_changed": len(changed), "max_gt": regime["max_gt"],
           "settle_need_gt": regime["settle_gt"],
           "settle_gt": g, "settled": g is not None,
           "first_stable_gt": g, "last_change_gt": last,
           "plateau": plateau_flag(g, last),
           "truncated": len(series) - 1 < regime["max_gt"],
           "final_bits": "".join(str(v) for v in final),
           "final_value": reads_value(reads, final),
           "final_reads": {r["name"]: bool(v)
                           for r, v in zip(state_reads(reads), final)},
           "changes": changes,
           "series": ["".join(str(v) for v in sample) for sample in series]}
    if nbt_reads(reads):
        # Sampled at the two ends only. `data get` is not a per-gt reading: it
        # costs a roundtrip per container per gt and a container's contents are
        # not what the settle criterion is about.
        rec["nbt"] = {"before": nbt_before, "after": read_nbt(s, reads)}
    if "expect" in regime:
        rec["expect"] = evaluate_expect(regime["expect"], rec)
    out.setdefault("regimes", []).append(rec)
    print("%-20s settle_gt=%s last_change_gt=%s final_value=%s events=%s"
          % (regime["name"], g, last, rec["final_value"], events), flush=True)
    return rec


def evaluate_expect(expect, rec):
    """Record true/false beside the reading. No verdict word is produced."""
    result = {}
    if "final_value" in expect:
        result["final_value"] = {"expected": expect["final_value"],
                                 "got": rec["final_value"],
                                 "equal": rec["final_value"] == expect["final_value"]}
    if "settle_gt_at_most" in expect:
        got = rec["settle_gt"]
        result["settle_gt_at_most"] = {
            "expected_at_most": expect["settle_gt_at_most"], "got": got,
            "within": got is not None and got <= expect["settle_gt_at_most"]}
    if "final_reads" in expect:
        result["final_reads"] = {
            k: {"expected": bool(v), "got": rec["final_reads"].get(k),
                "equal": rec["final_reads"].get(k) == bool(v)}
            for k, v in expect["final_reads"].items()}
    return result


# --- tables ----------------------------------------------------------------

MISSING = object()


def md_cell(value):
    """One table cell. Absent, null, and false are three different readings.

    `--` means the row carries no such reading at all (a result written before the
    reading existed); `null` means it was looked for and is not a number (an
    unsettled series has no `first_stable_gt` to compare)."""
    if value is MISSING:
        return "--"
    if value is None:
        return "null"
    if value is True or value is False:
        return "true" if value else "false"
    return str(value)


def tables_md(result):
    """The result as markdown. Readings only; the agent writes the sentence."""
    lines = ["# worldprobe -- %s (%s)" % (result["spec_name"], result["which"]), "",
             "writer `%s`, report_kind `%s`, %s. Units: gt."
             % (WRITER, REPORT_KIND, result["provenance"]["utc"]), "",
             "run dir `%s`" % result["run_dir"], ""]
    ident = result.get("identity")
    if ident:
        lines += ["## identity", "",
                  "| rows | id_fail | prop_fail |", "|---|---|---|",
                  "| %d | %d | %d |" % (ident["rows"], ident["id_fail"],
                                        ident["prop_fail"]), ""]
    if result.get("regimes"):
        # first_stable_gt and last_change_gt are appended, not inserted: the columns
        # a reader already knows keep their places, and both settle readings are on
        # the same row so a plateau cannot hide behind one of them.
        lines += ["## regimes", "",
                  "| regime | trigger | settle_gt | final_value | final_bits "
                  "| first_stable_gt | last_change_gt | plateau | truncated |",
                  "|---|---|---|---|---|---|---|---|---|"]
        for rec in result["regimes"]:
            trig = "none" if not rec["trigger"] else "pos %s hold %s delay %s" % (
                rec["trigger"]["pos"], rec["trigger"]["hold_gt"],
                rec["trigger"].get("delay_gt", 0))
            lines.append("| %s | %s | %s | %s | `%s` | %s | %s | %s | %s |" % (
                rec["name"], trig,
                rec["settle_gt"] if rec["settled"] else "unsettled@%d" % rec["max_gt"],
                rec["final_value"], rec["final_bits"],
                md_cell(rec.get("first_stable_gt", MISSING)),
                md_cell(rec.get("last_change_gt", MISSING)),
                md_cell(rec.get("plateau", MISSING)),
                md_cell(rec.get("truncated", MISSING))))
        lines.append("")
        for rec in result["regimes"]:
            lines += ["### %s -- changes" % rec["name"], "",
                      "| gt | bits | value |", "|---|---|---|"]
            lines += ["| %d | `%s` | %s |" % tuple(row) for row in rec["changes"]]
            lines.append("")
            if rec.get("nbt"):
                lines += ["### %s -- nbt (verbatim `data get block` replies)"
                          % rec["name"], "",
                          "| read | end | reply |", "|---|---|---|"]
                for end in ("before", "after"):
                    for name in sorted(rec["nbt"][end]):
                        lines.append("| %s | %s | `%s` |" % (
                            name, end,
                            rec["nbt"][end][name]["reply"].replace("\n", " ")))
                lines.append("")
    arms = result.get("selftest")
    if arms:
        lines += ["## selftest (drive flip test)", "",
                  "| arm | value | bits |", "|---|---|---|"]
        lines += ["| %s | %s | `%s` |" % (a["arm"], a["value"], a["bits"])
                  for a in arms]
        lines += ["",
                  "separates = %s (the setblock-only arm did not move and the "
                  "updated arm did)" % result.get("selftest_separates"), ""]
    lines += ["## rcon", "", "| roundtrips | limit |", "|---|---|",
              "| %d | %s |" % (result["rcon"]["roundtrips"],
                               result["rcon"].get("limit") or "none"), ""]
    return "\n".join(lines)


def write_outputs(spec, result, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = "%s.%s" % (spec["name"], result["which"])
    js, md = out_dir / (stem + ".result.json"), out_dir / (stem + ".tables.md")
    js.write_bytes(json.dumps(result, indent=1).encode("utf-8"))
    md.write_bytes((tables_md(result) + "\n").encode("utf-8"))
    return [str(js), str(md)]


# --- drivers ---------------------------------------------------------------

def new_result(spec, spec_path, run_dir, which):
    raw = Path(spec_path).read_bytes() if spec_path else b""
    return {
        "provenance": {"writer": WRITER, "report_kind": REPORT_KIND,
                       "spec_path": str(spec_path) if spec_path else None,
                       "spec_sha256": hashlib.sha256(raw).hexdigest() if raw else None,
                       "utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")},
        "which": which, "spec_name": spec["name"], "run_dir": str(run_dir),
        "completed": False}


def connect(spec, run_dir, log_name, result):
    server = spec.get("server", {})
    host = server.get("host", "127.0.0.1")
    port = server.get("rcon_port", 25585)
    if not port_is_free(host, port):
        raise ProbeError("%s:%d is already listening -- another agent holds this "
                         "port. Set spec.server.rcon_port to a free one; the "
                         "template server.properties is not edited." % (host, port))
    set_rcon_port(run_dir, port)
    result["server"] = {"host": host, "rcon_port": port}
    proc, handle = launch(run_dir, Path(run_dir) / ("%s.server.log" % log_name),
                          server.get("java_xmx", "3G"),
                          server.get("launch_timeout_s", 300))
    time.sleep(1.0)
    s = Session(host, port,
                (Path(run_dir) / "rcon-password.txt").read_text(encoding="utf-8").strip(),
                Path(run_dir) / ("%s.rcon.log" % log_name),
                server.get("rcon_timeout_s", 60),
                spec.get("limits", {}).get("max_rcon"))
    return s, proc, handle


def measure_run(s, spec, result):
    s.phase = "prepare"
    result["tick_query"] = prepare(s, spec)
    ok, reply = scarpet_ok(s)
    result["scarpet"] = {"ok": ok, "reply": reply}
    if not ok:
        raise ProbeError("carpet script run is unavailable (%r); the drive needs "
                         "it to deliver the attachment update" % reply)
    if "identity" in spec:
        s.phase = "identity"
        if not identity(s, spec, result):
            result["stopped"] = "identity: block ids differ from the capture"
            return False
    for regime in spec.get("regimes", []):
        s.phase = "regime:" + regime["name"]
        run_regime(s, spec, regime, result)
    return True


def measure_selftest(s, spec, result):
    """Four arms that differ ONLY by the attachment update.

    rest -> setblock with no update (negative control) -> the same lever states
    with the update added -> back to the rest inputs. If the negative arm moves,
    setblock alone drives this circuit and the update is not what is being
    measured; if the positive arm does not move, the drive is broken. Neither
    outcome is written as a verdict: the two values are recorded and
    `selftest_separates` states whether they differ."""
    cfg = spec["selftest"]
    drives, reads = spec["drives"], spec["reads"]
    s.phase = "prepare"
    prepare(s, spec)
    ok, reply = scarpet_ok(s)
    result["scarpet"] = {"ok": ok, "reply": reply}
    if not ok:
        raise ProbeError("carpet script run is unavailable (%r)" % reply)
    span = cfg.get("span_gt", 200)
    arms = []

    def arm(label):
        sample = read_points(s, reads)
        arms.append({"arm": label, "bits": "".join(str(v) for v in sample),
                     "value": reads_value(reads, sample)})
        print("selftest %-34s value=%s" % (label, arms[-1]["value"]), flush=True)

    s.phase = "selftest:rest"
    if cfg.get("rest_inputs"):
        apply_inputs(s, drives, cfg["rest_inputs"])
        step(s, span)
    arm("rest")

    s.phase = "selftest:no_update"
    setblocked = apply_inputs(s, drives, cfg["drive_inputs"], do_update=False)
    step(s, span)
    arm("setblock only (negative control)")

    s.phase = "selftest:update"
    for name in sorted(cfg["drive_inputs"]):
        drive = drives[name]
        for pos in drive_positions(drive):
            update_attachment(s, pos, drive["face"], drive["facing"])
    step(s, span)
    arm("same states + attachment update")

    s.phase = "selftest:restore"
    apply_inputs(s, drives, cfg["restore_inputs"])
    step(s, span)
    arm("restored")

    result["selftest"] = arms
    result["selftest_span_gt"] = span
    result["selftest_levers_setblocked"] = len(setblocked)
    result["selftest_separates"] = (arms[1]["value"] == arms[0]["value"]
                                    and arms[2]["value"] != arms[1]["value"])
    print("selftest separates=%s" % result["selftest_separates"], flush=True)
    return True


def execute(spec, spec_path, run_dir, which):
    run_dir = Path(run_dir)
    result = new_result(spec, spec_path, run_dir, which)
    result["world"] = provision(spec, run_dir)
    s = proc = handle = None
    try:
        s, proc, handle = connect(spec, run_dir, which, result)
        result["completed"] = (measure_run(s, spec, result) if which == "run"
                               else measure_selftest(s, spec, result))
    finally:
        result["rcon"] = {"roundtrips": s.n if s else 0,
                          "limit": spec.get("limits", {}).get("max_rcon"),
                          "by_phase": s.by_phase if s else {}}
        result["outputs"] = write_outputs(spec, result, spec["out_dir"])
        if s is not None:
            for cmd in ("tick unfreeze", "stop"):
                try:
                    s.send(cmd)
                except Exception as exc:                       # noqa: BLE001
                    print("shutdown %r failed: %r" % (cmd, exc), file=sys.stderr)
            s.close()
        if proc is not None:
            for _ in range(120):
                if proc.poll() is not None:
                    break
                time.sleep(0.5)
            if proc.poll() is None:
                proc.kill()
        if handle is not None:
            handle.close()
    for path in result["outputs"]:
        print("wrote", path, flush=True)
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(prog="worldprobe.py",
                                 description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("run", "selftest"):
        p = sub.add_parser(name)
        p.add_argument("--spec", required=True)
        p.add_argument("--run-dir", required=True)
    p = sub.add_parser("validate")
    p.add_argument("--spec", required=True)
    args = ap.parse_args(argv)

    spec = load_spec(args.spec)
    if args.cmd == "validate":
        print("spec OK: %s (%d drive(s), %d read point(s), %d regime(s))"
              % (spec["name"], len(spec.get("drives", {})),
                 len(spec.get("reads", [])), len(spec.get("regimes", []))))
        return 0
    if args.cmd == "selftest" and "selftest" not in spec:
        raise SpecError("spec.selftest: required by the selftest subcommand "
                        "(keys: drive_inputs, restore_inputs, and optionally "
                        "rest_inputs and span_gt)")
    result = execute(spec, args.spec, args.run_dir, args.cmd)
    return 0 if result.get("completed") else 1


if __name__ == "__main__":                                     # pragma: no cover
    # `tools/test_console_encoding.py` rule. This CLI prints spec names, server
    # replies and capture rows -- all data read from files, the case where
    # checking this source for unencodable characters would still miss it.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    raise SystemExit(main())
