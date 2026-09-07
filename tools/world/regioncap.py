#!/usr/bin/env python3
"""Build a bench capture from a save's Anvil region files, reading only.

REGION-1 (`notes/2026-09-06-region1-capture-from-region-order.md`, OC-A30).

WHAT THIS IS. `aiwb_scan` reads a running world through the serving mod and
returns rows `[x, y, z, "minecraft:<id>[props]"]`. That needs the game up, a
forceload for non-resident columns, and an MCP round trip -- and it returns
the block state and nothing else, so every state variable that lives in a
block entity, in a scheduled-tick queue or in an entity falls outside the
capture (`notes/2026-09-06-state-holes-frame.md`, holes 1-4). This module
decodes the SAME rows straight out of `region/r.<x>.<z>.mca`, and can carry
the block entities, the tick queues and the entities from the same chunks in
the same file.

Hole 5 -- the state that lives in level.dat and not in any chunk: time of day,
weather, and the four gamerules a redstone artifact is a function of -- rides
in `provenance.world_state`, always, because level.dat has to be read for the
DataVersion anyway and the answer is a dozen scalars. Without it a capture
cannot say what world its rows were the rest state OF: a daylight detector
reads the clock, a rain sensor reads the weather, and a copper bulb oxidises
at `randomTickSpeed`. See `world_state`.

WHAT IT IS NOT. It is not a front observation. ADR-0130 D4.1 evidence is
whatever `frontcap.py` saw on the operator's own configuration; nothing here
substitutes for that. The freshness ceiling is the world's last autosave, so
a region capture of a world that is open is a picture of the past, and the
provenance says so. Nothing written here is promotion-grade and nothing here
writes `reports/raw/**`.

THE SAVE IS READ-ONLY, and that is enforced rather than intended:

- every read goes through `copy_for_read`, which refuses any path outside the
  allowlist (`level.dat`, `region/*.mca`, `entities/*.mca`, `*/*.mcc`) and
  copies the file into a caller-supplied scratch directory before parsing;
- `session.lock` is never opened and never stat'ed -- the "is the world open"
  signal is taken from `level.dat`'s mtime instead, which is a file this tool
  already has to read for the DataVersion (see `world_open`);
- the copy is checked for a torn read: sha256 before and after the copy must
  agree, one retry, then it fails rather than guessing.

Subcommands:
    capture  --save <world dir> --bbox x1 y1 z1 x2 y2 z2 --out <json>
             [--with-block-entities] [--with-ticks] [--with-entities]
    selftest --save <world dir> --pin <reference capture json> ...
             identity of the decoded rows against existing front captures

Anvil, for the version this repo targets (DataVersion 3839 = 1.20.6): a region
file is a 4 KiB location table, a 4 KiB timestamp table, then 4 KiB-aligned
chunk payloads; a chunk payload is a 4-byte big-endian length, a compression
byte (1 gzip, 2 zlib, 3 none, +0x80 = the payload lives in a sibling `.mcc`),
then the NBT. A chunk's `sections[]` each carry `block_states {palette, data}`
where `data` is a long array of palette indices at max(4, ceil(log2(n))) bits
per entry that do NOT span longs, indexed `(y*16 + z)*16 + x`, and the section
sits at `Y` (signed, so the world floor at y=-64 is section -4). A palette of
one has no `data` at all.

Python stdlib only, plus the m2-bridge NBT primitives loaded READ-ONLY by the
same `_load_module` pattern m9-worldgen and chunkgen document.
"""

import argparse
import gzip
import hashlib
import importlib.util
import json
import re
import shutil
import struct
import sys
import tempfile
import zlib
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_nbt = _load_module("aiwb_regioncap_nbt",
                    HERE / "_deps" / "litematic_to_nbt.py")

WRITER = "regioncap"
REPORT_KIND = "bench_capture"

#: The JSON encoding of a raw NBT compound this module emits. Lossy in ONE
#: documented direction: TAG_Byte/Short/Int/Long all become JSON numbers, so
#: the width of a scalar does not survive. The three array tags DO survive,
#: because telling a UUID (int array) from a light array (byte array) apart
#: matters and JSON gives them all the same shape otherwise.
NBT_JSON_VERSION = "nbt_json_v1"

#: What `aiwb_scan` drops from its rows, and therefore what this drops too.
AIR = ("minecraft:air", "minecraft:cave_air", "minecraft:void_air")

#: The row spelling, restated where a reader of the output will look for it.
ROW_SPELLING = ("minecraft:<id>[<prop>=<value>,...] with property names in "
                "ascending name order and no spaces; a state with no "
                "properties is bare. Identical to an aiwb_scan row.")

_SECTOR = 4096
_HEADER_SECTORS = 2
_MASK64 = (1 << 64) - 1

#: Paths inside the operator's save this tool may copy. Anything else raises:
#: the boundary is a code fence, not a habit.
_ALLOWED = re.compile(r"^(level\.dat"
                      r"|(region|entities|poi)/r\.-?\d+\.-?\d+\.mca"
                      r"|(region|entities|poi)/c\.-?\d+\.-?\d+\.mcc)$")

#: How recently `level.dat` must have been written for `world_open` to be
#: true. Vanilla autosaves every 6000 gt (5 minutes) and writes level.dat on
#: the way out, so a level.dat older than this window means nobody is holding
#: the world. Deliberately NOT read from `session.lock`, which this tool is
#: forbidden to open.
DEFAULT_OPEN_WINDOW_S = 900


class CaptureError(RuntimeError):
    """A region could not be read as the format this module documents."""


# --- reading the save, once, into scratch -----------------------------------

def region_coords(pos):
    """Region file coordinates of a block position: x >> 9, z >> 9."""
    return (pos[0] >> 9, pos[2] >> 9)


def chunk_coords(pos):
    """Chunk coordinates of a block position: x >> 4, z >> 4."""
    return (pos[0] >> 4, pos[2] >> 4)


def chunks_for_bbox(lo, hi):
    """Every chunk column the box touches, in a stable order."""
    cx0, cz0 = chunk_coords(lo)
    cx1, cz1 = chunk_coords(hi)
    return [(cx, cz)
            for cx in range(min(cx0, cx1), max(cx0, cx1) + 1)
            for cz in range(min(cz0, cz1), max(cz0, cz1) + 1)]


def region_files_for_bbox(lo, hi, kind="region"):
    """Every <kind>/r.<rx>.<rz>.mca the box touches, in a stable order.

    A box that straddles a region boundary needs BOTH files; copying only the
    one holding the min corner silently truncates the artifact."""
    rx0, rz0 = region_coords(lo)
    rx1, rz1 = region_coords(hi)
    return ["%s/r.%d.%d.mca" % (kind, rx, rz)
            for rx in range(min(rx0, rx1), max(rx0, rx1) + 1)
            for rz in range(min(rz0, rz1), max(rz0, rz1) + 1)]


def _sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _iso(stamp):
    return datetime.fromtimestamp(stamp, timezone.utc).isoformat(
        timespec="seconds").replace("+00:00", "Z")


def copy_for_read(save, rel, scratch):
    """Copy one allowlisted file out of the save and prove it was not torn.

    Returns (path to the copy, provenance record) or (None, record) when the
    file does not exist -- an absent `entities/r.x.z.mca` is a world with no
    entities there, not an error.

    The sha256 is taken BEFORE and AFTER the copy. A running server rewriting
    the region mid-copy changes it, so the two disagree and the copy is taken
    again exactly once; a second disagreement raises rather than parsing half
    of one save and half of another."""
    if not _ALLOWED.match(str(Path(rel).as_posix())):
        raise CaptureError(
            "refusing to read %r from the save: outside the allowlist "
            "(level.dat, region/entities/poi *.mca and *.mcc only)" % (rel,))
    src = Path(save) / rel
    record = {"path": str(src), "sha256": None, "mtime": None, "bytes": None}
    if not src.exists():
        record["absent"] = True
        return None, record
    dst = Path(scratch) / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    last = None
    for _attempt in (1, 2):
        before = _sha256_file(src)
        shutil.copy2(src, dst)
        after = _sha256_file(src)
        if before == after:
            record["sha256"] = before
            record["mtime"] = _iso(src.stat().st_mtime)
            record["bytes"] = src.stat().st_size
            return dst, record
        last = (before, after)
    raise CaptureError(
        "%s changed while being copied twice (%s -> %s): the world is being "
        "written; retry once the save has settled" % (rel, last[0][:12],
                                                      last[1][:12]))


# --- Anvil ------------------------------------------------------------------

def _tag(compound, name):
    """The payload of `name` in a parsed compound, or None."""
    tagged = compound.get(name) if isinstance(compound, dict) else None
    if tagged is None:
        return None
    return tagged[1] if isinstance(tagged, tuple) else tagged


def chunk_payload(data, cx, cz, mcc_reader=None):
    """The decompressed NBT bytes of one chunk, or None if the slot is empty.

    `mcc_reader(cx, cz) -> bytes` supplies the payload for the oversized
    chunks Anvil stores outside the region file (compression byte | 0x80)."""
    if len(data) < _HEADER_SECTORS * _SECTOR:
        if not data:
            return None                     # a 0-byte region file: no chunks
        raise CaptureError("region data shorter than its 2-sector header")
    index = (cx & 31) + (cz & 31) * 32
    (loc,) = struct.unpack(">I", data[index * 4:index * 4 + 4])
    if loc == 0:
        return None
    start = (loc >> 8) * _SECTOR
    end = start + (loc & 0xFF) * _SECTOR
    if end > len(data):
        raise CaptureError(
            "chunk (%d,%d) location table points past the end of the file"
            % (cx, cz))
    payload = data[start:end]
    (length,) = struct.unpack(">I", payload[0:4])
    scheme = payload[4]
    external = bool(scheme & 0x80)
    scheme &= 0x7F
    if external:
        if mcc_reader is None:
            raise CaptureError(
                "chunk (%d,%d) is stored externally (c.%d.%d.mcc) and no "
                "reader for it was supplied" % (cx, cz, cx, cz))
        raw = mcc_reader(cx, cz)
    else:
        raw = payload[5:4 + length]
    if scheme == 1:
        raw = gzip.decompress(raw)
    elif scheme == 2:
        raw = zlib.decompress(raw)
    elif scheme != 3:
        raise CaptureError("unsupported chunk compression %d" % scheme)
    return raw


def bits_for_palette(size):
    """Bits per entry of a chunk-section paletted container.

    max(4, ceil(log2(n))) -- the floor of 4 is the format's, not a rounding
    convenience, and a palette of one carries no data array at all."""
    return max(4, (size - 1).bit_length()) if size > 1 else 4


def unpack_indices(longs, bits, count):
    """Palette indices out of a post-1.16 long array.

    Entries do NOT span 64-bit boundaries here (unlike Litematica's packing in
    `tools/m2-bridge`), so each long holds floor(64/bits) entries and the top
    64 % bits bits are padding."""
    if bits <= 0 or bits > 64:
        raise CaptureError("nonsensical bits per entry: %r" % (bits,))
    per_long = 64 // bits
    needed = (count + per_long - 1) // per_long
    if len(longs) < needed:
        raise CaptureError(
            "block_states data too short: %d longs for %d entries at %d "
            "bits (need %d)" % (len(longs), count, bits, needed))
    mask = (1 << bits) - 1
    out = []
    for word in longs[:needed]:
        unsigned = word & _MASK64
        for slot in range(per_long):
            if len(out) == count:
                break
            out.append((unsigned >> (slot * bits)) & mask)
    return out


def block_state_string(entry):
    """A palette entry as the string an `aiwb_scan` row carries.

    The property order is `sorted()` on the property NAME and not the order
    the properties appear in the file. Both happen to agree today -- vanilla's
    `NbtHelper.fromBlockState` walks `BlockState#getEntries`, whose
    `StateManager` map is sorted by name -- but the row spelling is this
    module's contract with the front's rows, so it is imposed here rather
    than inherited from whatever wrote the file."""
    name = _tag(entry, "Name")
    if name is None:
        raise CaptureError("palette entry with no Name: %r" % (entry,))
    props = _tag(entry, "Properties")
    if not props:
        return name
    body = ",".join("%s=%s" % (key, _tag(props, key)) for key in sorted(props))
    return "%s[%s]" % (name, body)


def section_states(section):
    """(section Y, 4096 state strings in (y*16+z)*16+x order), or None.

    None means the section carries no blocks to read: a proto-chunk section
    saved below full status has no `block_states` at all, and iterating one
    as if it did is how a naive decoder dies on a real save
    (`lanerun.py:3848-3877` walks sections one by one for this reason)."""
    section_y = _tag(section, "Y")
    states = _tag(section, "block_states")
    if states is None:
        return None
    palette = _tag(states, "palette")
    if palette is None:
        return None
    _etype, entries = palette
    if not entries:
        return None
    names = [block_state_string(entry) for entry in entries]
    data = _tag(states, "data")
    if data is None:
        if len(names) != 1:
            raise CaptureError(
                "section Y=%r has a palette of %d and no data array"
                % (section_y, len(names)))
        return section_y, [names[0]] * 4096
    indices = unpack_indices(data, bits_for_palette(len(names)), 4096)
    limit = len(names)
    for index in indices:
        if index >= limit:
            raise CaptureError(
                "section Y=%r: palette index %d out of range (palette %d)"
                % (section_y, index, limit))
    return section_y, [names[index] for index in indices]


# --- NBT -> JSON ------------------------------------------------------------

_ARRAY_KEY = {_nbt.TAG_BYTE_ARRAY: "__bytes",
              _nbt.TAG_INT_ARRAY: "__ints",
              _nbt.TAG_LONG_ARRAY: "__longs"}


def nbt_json(payload, tag_id=None):
    """A parsed NBT payload as plain JSON (`nbt_json_v1`, see the constant)."""
    if tag_id is None:
        tag_id = _nbt.TAG_COMPOUND
    if tag_id == _nbt.TAG_COMPOUND:
        return {name: nbt_json(child_payload, child_tag)
                for name, (child_tag, child_payload) in payload.items()}
    if tag_id == _nbt.TAG_LIST:
        etype, items = payload
        return [nbt_json(item, etype) for item in items]
    if tag_id in _ARRAY_KEY:
        return {_ARRAY_KEY[tag_id]: list(payload)}
    return payload


# --- the capture ------------------------------------------------------------

def in_bbox(pos, lo, hi):
    return all(lo[i] <= pos[i] <= hi[i] for i in range(3))


def _norm_bbox(bbox):
    x1, y1, z1, x2, y2, z2 = bbox
    lo = [min(x1, x2), min(y1, y2), min(z1, z2)]
    hi = [max(x1, x2), max(y1, y2), max(z1, z2)]
    return lo, hi


class _Regions:
    """Lazily copied region bytes, one copy per file per capture."""

    def __init__(self, save, scratch, kind):
        self.save = Path(save)
        self.scratch = Path(scratch)
        self.kind = kind
        self.records = []
        self._bytes = {}

    def data(self, rx, rz):
        key = (rx, rz)
        if key not in self._bytes:
            rel = "%s/r.%d.%d.mca" % (self.kind, rx, rz)
            copy, record = copy_for_read(self.save, rel, self.scratch)
            self.records.append(record)
            self._bytes[key] = copy.read_bytes() if copy is not None else b""
        return self._bytes[key]

    def mcc_reader(self):
        def read(cx, cz):
            rel = "%s/c.%d.%d.mcc" % (self.kind, cx, cz)
            copy, record = copy_for_read(self.save, rel, self.scratch)
            self.records.append(record)
            if copy is None:
                raise CaptureError("external chunk file %s is missing" % rel)
            return copy.read_bytes()
        return read

    def chunk(self, cx, cz):
        data = self.data(cx >> 5, cz >> 5)
        raw = chunk_payload(data, cx, cz, self.mcc_reader())
        if raw is None:
            return None
        _name, root = _nbt.read_nbt(raw)
        return root


def decode_rows(regions, lo, hi):
    """The non-air rows of the box, sorted by (x, y, z), and the columns that
    held no chunk at all."""
    rows = []
    missing = []
    air = set(AIR)
    y_lo, y_hi = lo[1], hi[1]
    for cx, cz in chunks_for_bbox(lo, hi):
        chunk = regions.chunk(cx, cz)
        if chunk is None:
            missing.append([cx, cz])
            continue
        sections = _tag(chunk, "sections")
        if sections is None:
            missing.append([cx, cz])
            continue
        _etype, entries = sections
        for section in entries:
            section_y = _tag(section, "Y")
            if section_y is None:
                continue
            base_y = section_y * 16
            if base_y > y_hi or base_y + 15 < y_lo:
                continue
            decoded = section_states(section)
            if decoded is None:
                continue
            _y, states = decoded
            for local_y in range(max(0, y_lo - base_y),
                                 min(15, y_hi - base_y) + 1):
                world_y = base_y + local_y
                for local_z in range(16):
                    world_z = cz * 16 + local_z
                    if not lo[2] <= world_z <= hi[2]:
                        continue
                    row_base = (local_y * 16 + local_z) * 16
                    for local_x in range(16):
                        world_x = cx * 16 + local_x
                        if not lo[0] <= world_x <= hi[0]:
                            continue
                        state = states[row_base + local_x]
                        if state.split("[", 1)[0] in air:
                            continue
                        rows.append([world_x, world_y, world_z, state])
    rows.sort(key=lambda row: (row[0], row[1], row[2]))
    return rows, missing


def _positioned(chunk, key, lo, hi, extra=None):
    """Rows of a chunk-root list whose x/y/z fall inside the box."""
    tagged = _tag(chunk, key)
    if not tagged:
        return []
    _etype, items = tagged
    out = []
    for item in items:
        pos = [_tag(item, axis) for axis in ("x", "y", "z")]
        if any(value is None for value in pos):
            continue
        if not in_bbox(pos, lo, hi):
            continue
        row = {"pos": pos, "nbt": nbt_json(item)}
        for name, source in (extra or {}).items():
            row[name] = _tag(item, source)
        out.append(row)
    return out


def _by_pos(rows):
    rows.sort(key=lambda row: (row["pos"][0], row["pos"][1], row["pos"][2]))
    return rows


def decode_block_entities(regions, lo, hi):
    """Hole 1 of the frame: container Items, comparator OutputSignal, hopper
    TransferCooldown -- everything a block state string cannot carry."""
    out = []
    for cx, cz in chunks_for_bbox(lo, hi):
        chunk = regions.chunk(cx, cz)
        if chunk is None:
            continue
        out.extend(_positioned(chunk, "block_entities", lo, hi, {"id": "id"}))
    return _by_pos(out)


def decode_ticks(regions, lo, hi, key):
    """`block_ticks` / `fluid_ticks`: the in-flight queue, hole 3 of the frame.

    The compact spelling is vanilla's: `i` the block or fluid id, `t` the
    remaining delay, `p` the tick priority."""
    out = []
    for cx, cz in chunks_for_bbox(lo, hi):
        chunk = regions.chunk(cx, cz)
        if chunk is None:
            continue
        out.extend(_positioned(chunk, key, lo, hi,
                               {"id": "i", "delay": "t", "priority": "p"}))
    return _by_pos(out)


def decode_entities(entities, lo, hi):
    """`entities/r.x.z.mca` -- a SEPARATE file since 1.17, which is why a
    region-only byte copy of a save carries no entities (frame, hole 2)."""
    out = []
    for cx, cz in chunks_for_bbox(lo, hi):
        chunk = entities.chunk(cx, cz)
        if chunk is None:
            continue
        tagged = _tag(chunk, "Entities")
        if not tagged:
            continue
        _etype, items = tagged
        for item in items:
            pos = _tag(item, "Pos")
            values = pos[1] if isinstance(pos, tuple) else pos
            if not values or len(values) != 3:
                continue
            block_pos = [int(value // 1) for value in values]
            if not in_bbox(block_pos, lo, hi):
                continue
            out.append({"id": _tag(item, "id"), "pos": list(values),
                        "block_pos": block_pos, "nbt": nbt_json(item)})
    out.sort(key=lambda row: (row["block_pos"][0], row["block_pos"][1],
                              row["block_pos"][2], row["id"] or ""))
    return out


#: The gamerules a redstone artifact's behaviour actually turns on, out of the
#: ~40 a level.dat carries. `maxChainedNeighborUpdates` caps an update cascade,
#: which a big circuit can hit; `randomTickSpeed` drives crops, the cauldron
#: filling in rain and copper oxidation (so a copper bulb's state is a function
#: of it); the two cycles decide whether a daylight detector or a rain sensor
#: ever sees the world change at all. Hole 5 of the state-holes frame.
WORLD_GAME_RULES = ("maxChainedNeighborUpdates", "randomTickSpeed",
                    "doDaylightCycle", "doWeatherCycle")


def level_data(level_dat_bytes):
    """The `Data` compound of a copied level.dat, gzipped or not."""
    raw = level_dat_bytes
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    _name, root = _nbt.read_nbt(raw)
    data = _tag(root, "Data")
    if data is None:
        raise CaptureError("level.dat has no Data compound")
    return data


def data_version(level_dat_bytes):
    """The world's DataVersion, from a copied level.dat."""
    return _tag(level_data(level_dat_bytes), "DataVersion")


def _flag(compound, name):
    """A TAG_Byte flag as a bool, or None when the save does not carry it.

    Absent is NOT false: a level.dat that never wrote a weather state (a
    synthetic one, or a dimension folder) would otherwise be reported as a
    world it is known to be clear in, which is a claim nobody measured."""
    value = _tag(compound, name)
    return None if value is None else bool(value)


def world_state(level_dat_bytes):
    """Hole 5 of `notes/2026-09-06-state-holes-frame.md`: the state that lives
    in level.dat rather than in any chunk, and which no scan row can carry.

    A daylight detector reads `DayTime`, a rain sensor reads `raining`, an
    oxidising copper bulb is a function of `randomTickSpeed`, and a circuit
    large enough to chain updates is a function of
    `maxChainedNeighborUpdates` -- so a capture that does not record these
    cannot say what world its rows were the rest state OF.

    Two shapes are the file's and are kept rather than normalised: every
    gamerule is stored as a STRING (so `randomTickSpeed` comes back "3", not
    3), and a rule the save does not carry comes back None rather than
    vanilla's default, because this reports what was read and not what the
    game would have used."""
    data = level_data(level_dat_bytes)
    rules = _tag(data, "GameRules")
    return {
        "data_version": _tag(data, "DataVersion"),
        "day_time": _tag(data, "DayTime"),
        "time": _tag(data, "Time"),
        "raining": _flag(data, "raining"),
        "thundering": _flag(data, "thundering"),
        "game_rules": {key: (_tag(rules, key) if rules else None)
                       for key in WORLD_GAME_RULES},
        "basis": ("level.dat Data, read-only; gamerule values are the file's "
                  "strings and an absent key is None, never a default"),
    }


def capture(save, bbox, scratch, with_block_entities=False, with_ticks=False,
            with_entities=False, open_window_s=DEFAULT_OPEN_WINDOW_S,
            now=None):
    """The whole capture, as the dict `--out` serialises."""
    lo, hi = _norm_bbox(bbox)
    save = Path(save)
    at = now or datetime.now(timezone.utc)
    regions = _Regions(save, scratch, "region")
    rows, missing = decode_rows(regions, lo, hi)

    level_copy, level_record = copy_for_read(save, "level.dat", scratch)
    version = None
    world_open = None
    state = None
    if level_copy is not None:
        # One parse of the copy answers both: the DataVersion this capture
        # already reported, and hole 5's world-level state (always on -- it is
        # a dozen scalars out of a file that had to be read anyway).
        state = world_state(level_copy.read_bytes())
        version = state["data_version"]
        age = at.timestamp() - (save / "level.dat").stat().st_mtime
        world_open = age < open_window_s

    provenance = {
        "writer": WRITER,
        "report_kind": REPORT_KIND,
        "promotion_grade": False,
        "source_save": str(save),
        "region_files": regions.records,
        "level_dat": level_record,
        "data_version": version,
        "world_state": state,
        "world_open": world_open,
        "world_open_basis": ("level.dat mtime within %d s of the capture; "
                             "session.lock is deliberately never opened or "
                             "stat'ed by this tool" % open_window_s),
        "freshness": ("last autosave; not a front observation (ADR-0130 D4.1 "
                      "evidence stays the front's)"),
        "row_spelling": ROW_SPELLING,
        "air_ids": list(AIR),
        "nbt_json": NBT_JSON_VERSION,
        "options": {"with_block_entities": bool(with_block_entities),
                    "with_ticks": bool(with_ticks),
                    "with_entities": bool(with_entities)},
    }
    out = {
        "world": save.name,
        "bbox": {"min": lo, "max": hi},
        "command": "capture",
        "at": at.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "provenance": provenance,
        "scan": {"status": "ok", "error": False,
                 "loaded": not missing,
                 "non_air": rows,
                 "non_air_count": len(rows),
                 "bbox": {"min": lo, "max": hi}},
    }
    if missing:
        out["scan"]["missing_columns"] = missing
    if with_block_entities:
        out["block_entities"] = decode_block_entities(regions, lo, hi)
    if with_ticks:
        out["block_ticks"] = decode_ticks(regions, lo, hi, "block_ticks")
        out["fluid_ticks"] = decode_ticks(regions, lo, hi, "fluid_ticks")
    if with_entities:
        entities = _Regions(save, scratch, "entities")
        out["entities"] = decode_entities(entities, lo, hi)
        provenance["entity_files"] = entities.records
    return out


# --- identity against a front capture ---------------------------------------

def reference_rows(document):
    """The `[x, y, z, state]` rows of a front capture, single or tiled.

    B-03 and B-04 are `tiles`: several `scan` results that partition the
    declared box. Folding them here is what makes the identity comparable to
    a single region read of the same box."""
    if "scan" in document:
        return [list(row) for row in document["scan"].get("non_air", [])]
    rows = []
    for tile in document.get("tiles", []):
        rows.extend(list(row) for row in tile.get("scan", {}).get(
            "non_air", []))
    return rows


def classify(reference, observed):
    """Difference between two row lists, split the way the order asks.

    property: same position, same block id, different properties -- a live
    circuit legitimately does this.
    id: same position, different block -- the world was edited.
    count: a position present on one side only."""
    ref = {(row[0], row[1], row[2]): row[3] for row in reference}
    obs = {(row[0], row[1], row[2]): row[3] for row in observed}
    same, prop, ident, only_ref, only_obs = [], [], [], [], []
    for pos in sorted(set(ref) | set(obs)):
        a, b = ref.get(pos), obs.get(pos)
        if a is None:
            only_obs.append([list(pos), b])
        elif b is None:
            only_ref.append([list(pos), a])
        elif a == b:
            same.append(pos)
        elif a.split("[", 1)[0] == b.split("[", 1)[0]:
            prop.append([list(pos), a, b])
        else:
            ident.append([list(pos), a, b])
    return {"reference_rows": len(reference), "observed_rows": len(observed),
            "identical": len(same),
            "property_difference": prop, "id_difference": ident,
            "only_in_reference": only_ref, "only_in_region": only_obs,
            "identity": (len(same) == len(reference) == len(observed))}


def selftest(save, pins, scratch, **kwargs):
    """Each pin is a path to a front capture; its own bbox drives the read."""
    results = []
    for pin in pins:
        document = json.loads(Path(pin).read_text(encoding="utf-8"))
        box = document["bbox"]
        bbox = list(box["min"]) + list(box["max"])
        got = capture(save, bbox, scratch, **kwargs)
        result = classify(reference_rows(document), got["scan"]["non_air"])
        result["pin"] = str(pin)
        result["bbox"] = {"min": bbox[:3], "max": bbox[3:]}
        result["region_files"] = got["provenance"]["region_files"]
        results.append(result)
    return {"writer": WRITER, "command": "selftest",
            "at": datetime.now(timezone.utc).isoformat(
                timespec="seconds").replace("+00:00", "Z"),
            "source_save": str(save), "pins": results,
            "identity": all(item["identity"] for item in results)}


# --- CLI --------------------------------------------------------------------

def _refuse_raw(path):
    """`reports/raw/**` has approved writers and this is not one of them."""
    resolved = Path(path).resolve()
    raw = (ROOT / "reports" / "raw").resolve()
    if raw == resolved or raw in resolved.parents:
        raise SystemExit(
            "regioncap: refusing to write %s -- reports/raw/** is written "
            "only by approved processes (ADR-0130) and regioncap is not one; "
            "write bench artifacts instead" % (resolved,))


def _write_json(path, document):
    _refuse_raw(path)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(document, indent=2, sort_keys=False,
                      ensure_ascii=False) + "\n"
    path.write_bytes(body.encode("utf-8"))
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="regioncap",
        description="Bench captures decoded from a save's region files, "
                    "read-only. Not a front observation.")
    sub = parser.add_subparsers(dest="command", required=True)

    cap = sub.add_parser("capture", help="decode one bbox into a capture json")
    cap.add_argument("--save", required=True, help="the world directory")
    cap.add_argument("--bbox", required=True, nargs=6, type=int,
                     metavar=("X1", "Y1", "Z1", "X2", "Y2", "Z2"))
    cap.add_argument("--out", required=True)
    cap.add_argument("--with-block-entities", action="store_true")
    cap.add_argument("--with-ticks", action="store_true")
    cap.add_argument("--with-entities", action="store_true")
    cap.add_argument("--open-window", type=int, default=DEFAULT_OPEN_WINDOW_S)

    test = sub.add_parser("selftest",
                          help="identity against existing front captures")
    test.add_argument("--save", required=True)
    test.add_argument("--pin", required=True, action="append",
                      help="a front capture json; repeatable")
    test.add_argument("--out", help="where to write the comparison json")

    args = parser.parse_args(argv)
    with tempfile.TemporaryDirectory(prefix="regioncap-") as scratch:
        if args.command == "capture":
            document = capture(
                args.save, args.bbox, scratch,
                with_block_entities=args.with_block_entities,
                with_ticks=args.with_ticks, with_entities=args.with_entities,
                open_window_s=args.open_window)
            written = _write_json(args.out, document)
            print("regioncap capture %s rows=%d bbox=%s..%s -> %s"
                  % (document["world"], document["scan"]["non_air_count"],
                     document["bbox"]["min"], document["bbox"]["max"],
                     written))
            for key in ("block_entities", "block_ticks", "fluid_ticks",
                        "entities"):
                if key in document:
                    print("  %s: %d" % (key, len(document[key])))
            if document["scan"].get("missing_columns"):
                print("  missing columns: %s"
                      % (document["scan"]["missing_columns"],))
            return 0

        report = selftest(args.save, args.pin, scratch)
        for item in report["pins"]:
            print("pin %s: reference=%d region=%d identical=%d "
                  "property_diff=%d id_diff=%d only_reference=%d "
                  "only_region=%d identity=%s"
                  % (item["pin"], item["reference_rows"],
                     item["observed_rows"], item["identical"],
                     len(item["property_difference"]),
                     len(item["id_difference"]),
                     len(item["only_in_reference"]),
                     len(item["only_in_region"]), item["identity"]))
        if args.out:
            print("-> %s" % _write_json(args.out, report))
        return 0 if report["identity"] else 1


if __name__ == "__main__":                                     # pragma: no cover
    # `tools/test_console_encoding.py` rule. This CLI prints block state
    # strings and save paths read out of files -- data, the case where
    # checking this source for unencodable characters would still miss it.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    raise SystemExit(main())
