#!/usr/bin/env python3
"""the development repository M15 Workbench v1 -- W9 litematic export writer (E5b Part B).

The EXACT INVERSE of `tools/m2-bridge/litematic_to_nbt.py`'s reader: it takes a
set of placed blocks (name + block-state properties) and emits a Litematica
`.litematic` **Version 6** file that that reader (the round-trip checker, kept
UNMODIFIED -- PROV-7) decodes block-for-block. The packing contract is inverted
from `unpack_block_states`: `bits = max(2, ceil(log2(paletteSize)))` (>=2),
tight little-endian bit-packing across unsigned 64-bit `BlockStates` longs with
entries spanning long boundaries, **YZX** index order (`i = (y*az + z)*ax + x`),
`BlockStatePalette[0] = minecraft:air`.

No tile entities in v1 (E4 already refuses TE payloads): passing a non-empty
`block_entities` is refused with a clear error, mirroring the reader's contract
(empty `TileEntities`/`Entities`/`PendingBlockTicks`/`PendingFluidTicks`).

Region offset (`Position`) is the artifact frame at origin (0,0,0); the block
grid itself is normalized to a local frame anchored at the block bounding-box
min corner (exactly what a Litematica selection save records, and what the
m2-bridge reader decodes back -- it ignores `Position` and anchors at 0,0,0).
Metadata carries `Name`, `Author` ("the development repository workbench"), created/modified
timestamps, the enclosing size, and the block/volume counts; `TotalBlocks`
equals the reader's own non-air self-check count.

Python stdlib only.
"""

import gzip
import io
import math
import struct
import time

__version__ = "0.1.0"

# The Litematica encoding version the m2-bridge reader ACCEPTS (its round-trip
# is our only correctness oracle).
LITEMATIC_VERSION = 6
LITEMATIC_SUBVERSION = 1

# MC 1.20.6 (the surveyed environment, ADR-0059 context). The reader carries
# this through verbatim; the value only needs to be a plausible DataVersion.
DEFAULT_DATA_VERSION = 3839

AIR_BLOCK = "minecraft:air"
DEFAULT_AUTHOR = "the development repository workbench"
DEFAULT_REGION_NAME = "artifact"

MASK64 = 0xFFFFFFFFFFFFFFFF

# NBT tag ids (identical to the reader's -- this is the shared wire format).
TAG_END = 0
TAG_BYTE = 1
TAG_SHORT = 2
TAG_INT = 3
TAG_LONG = 4
TAG_FLOAT = 5
TAG_DOUBLE = 6
TAG_BYTE_ARRAY = 7
TAG_STRING = 8
TAG_LIST = 9
TAG_COMPOUND = 10
TAG_INT_ARRAY = 11
TAG_LONG_ARRAY = 12


class WriterError(Exception):
    """The blocks/args violate the v1 litematic-writer contract."""


# ---------------------------------------------------------------------------
# Minimal NBT serialization (same (tag_id, payload) model as the reader, but
# self-contained: the writer never imports the m2-bridge module at runtime).
# ---------------------------------------------------------------------------


def _write_string(out, s):
    raw = s.encode("utf-8")
    out.write(struct.pack(">H", len(raw)))
    out.write(raw)


def _write_payload(out, tag_id, payload):
    if tag_id == TAG_BYTE:
        out.write(struct.pack(">b", payload))
    elif tag_id == TAG_SHORT:
        out.write(struct.pack(">h", payload))
    elif tag_id == TAG_INT:
        out.write(struct.pack(">i", payload))
    elif tag_id == TAG_LONG:
        out.write(struct.pack(">q", payload))
    elif tag_id == TAG_FLOAT:
        out.write(struct.pack(">f", payload))
    elif tag_id == TAG_DOUBLE:
        out.write(struct.pack(">d", payload))
    elif tag_id == TAG_STRING:
        _write_string(out, payload)
    elif tag_id == TAG_LIST:
        etype, items = payload
        out.write(struct.pack(">b", etype))
        out.write(struct.pack(">i", len(items)))
        for item in items:
            _write_payload(out, etype, item)
    elif tag_id == TAG_COMPOUND:
        for name, (child, child_payload) in payload.items():
            out.write(struct.pack(">b", child))
            _write_string(out, name)
            _write_payload(out, child, child_payload)
        out.write(struct.pack(">b", TAG_END))
    elif tag_id == TAG_INT_ARRAY:
        out.write(struct.pack(">i", len(payload)))
        out.write(struct.pack(f">{len(payload)}i", *payload))
    elif tag_id == TAG_LONG_ARRAY:
        out.write(struct.pack(">i", len(payload)))
        out.write(struct.pack(f">{len(payload)}q", *payload))
    else:
        raise WriterError(f"unsupported NBT tag id {tag_id}")


def write_nbt(root_compound, root_name="", compress=True):
    """Serialize a compound payload dict -> NBT bytes (gzipped by default)."""
    out = io.BytesIO()
    out.write(struct.pack(">b", TAG_COMPOUND))
    _write_string(out, root_name)
    _write_payload(out, TAG_COMPOUND, root_compound)
    raw = out.getvalue()
    return gzip.compress(raw) if compress else raw


# ---------------------------------------------------------------------------
# Packing (the inverse of `unpack_block_states`).
# ---------------------------------------------------------------------------


def bits_per_entry(palette_size):
    """Litematica packing width -- identical formula to the reader's."""
    return max(2, math.ceil(math.log2(palette_size))) if palette_size > 1 else 2


def _to_signed_long(value):
    """Unsigned 64-bit -> signed (the LONG_ARRAY on-disk representation)."""
    value &= MASK64
    return value - (1 << 64) if value >= (1 << 63) else value


def pack_block_states(indices, palette_size):
    """Tightly pack a flat (YZX-ordered) palette-index list into the signed
    long array the m2-bridge reader's `unpack_block_states` decodes. Entries
    span 64-bit boundaries (LitematicaBitArray), little-endian within each
    long -- the exact inverse of the reader's read path."""
    bits = bits_per_entry(palette_size)
    volume = len(indices)
    need_longs = (volume * bits + 63) // 64
    ulongs = [0] * need_longs
    mask = (1 << bits) - 1
    for i, raw_index in enumerate(indices):
        index = raw_index & mask
        start = i * bits
        li = start >> 6
        off = start & 63
        ulongs[li] |= (index << off) & MASK64
        if off + bits > 64:
            ulongs[li + 1] |= index >> (64 - off)
    return [_to_signed_long(v) for v in ulongs]


# ---------------------------------------------------------------------------
# Block-input normalization.
# ---------------------------------------------------------------------------


def parse_block_string(block_string):
    """Split a scarpet/rom16gen block string into (name, props_dict).

    `minecraft:powered_rail[powered=true,shape=east_west]` ->
    ("minecraft:powered_rail", {"powered": "true", "shape": "east_west"});
    a bare `minecraft:stone` -> ("minecraft:stone", {}). Property values are
    kept as strings (the reader carries `Properties` values as NBT strings)."""
    if "[" not in block_string:
        return block_string, {}
    name, rest = block_string.split("[", 1)
    rest = rest.rstrip("]")
    props = {}
    for pair in rest.split(","):
        if not pair:
            continue
        key, _, value = pair.partition("=")
        props[key] = value
    return name, props


def blocks_from_payload(payload):
    """Convert a rom16gen placement payload (`[[x, y, z, block_string], ...]`)
    into the writer's `(x, y, z, name, props)` block list. The single adapter
    the culvert export path uses, so the writer's inversion contract has one
    entry point."""
    blocks = []
    for row in payload:
        x, y, z, block_string = row[0], row[1], row[2], row[3]
        name, props = parse_block_string(block_string)
        blocks.append((int(x), int(y), int(z), name, props))
    return blocks


def _size_compound(x, y, z):
    return (TAG_COMPOUND, {"x": (TAG_INT, x), "y": (TAG_INT, y),
                           "z": (TAG_INT, z)})


def _palette_entry(name, props):
    entry = {"Name": (TAG_STRING, name)}
    if props:
        entry["Properties"] = (TAG_COMPOUND,
                               {k: (TAG_STRING, str(v))
                                for k, v in props.items()})
    return entry


def _empty_list():
    return (TAG_LIST, (TAG_END, []))


# ---------------------------------------------------------------------------
# Writer entry point.
# ---------------------------------------------------------------------------


def build_litematic_nbt(blocks, name=DEFAULT_REGION_NAME, author=DEFAULT_AUTHOR,
                        block_entities=None, data_version=DEFAULT_DATA_VERSION,
                        region_name=None, time_created_ms=None,
                        time_modified_ms=None):
    """Build the Version-6 `.litematic` root compound (the (tag, payload) NBT
    model) for `blocks` -- a list of `(x, y, z, name, props_dict)`.

    Refuses a non-empty `block_entities` (no SNBT carry path in v1, the same
    boundary E4 enforces). The block grid is normalized to a local frame at
    its bounding-box min corner; the region `Position` records the artifact
    frame origin (0,0,0)."""
    if block_entities:
        raise WriterError(
            f"litematic export cannot carry {len(block_entities)} tile "
            "entity/entities (no SNBT path in v1) -- refusing rather than "
            "silently dropping them (use a signless v3/v4 artifact)")

    placed = [(int(x), int(y), int(z), nm, pr)
              for (x, y, z, nm, pr) in blocks if nm != AIR_BLOCK]
    if not placed:
        raise WriterError("no non-air blocks to export -- nothing to write")

    xs = [b[0] for b in placed]
    ys = [b[1] for b in placed]
    zs = [b[2] for b in placed]
    min_x, min_y, min_z = min(xs), min(ys), min(zs)
    ax = max(xs) - min_x + 1
    ay = max(ys) - min_y + 1
    az = max(zs) - min_z + 1
    volume = ax * ay * az

    # Deterministic YZX walk order for both palette assignment and indexing.
    ordered = sorted(placed, key=lambda b: (b[1], b[2], b[0]))

    palette_entries = [_palette_entry(AIR_BLOCK, {})]
    palette_index = {(AIR_BLOCK, ()): 0}
    indices = [0] * volume
    for (x, y, z, nm, pr) in ordered:
        key = (nm, tuple(sorted(pr.items())))
        idx = palette_index.get(key)
        if idx is None:
            idx = len(palette_entries)
            palette_index[key] = idx
            palette_entries.append(_palette_entry(nm, pr))
        lx, ly, lz = x - min_x, y - min_y, z - min_z
        flat = (ly * az + lz) * ax + lx
        indices[flat] = idx

    longs = pack_block_states(indices, len(palette_entries))

    now_ms = int(time.time() * 1000)
    t_created = now_ms if time_created_ms is None else int(time_created_ms)
    t_modified = t_created if time_modified_ms is None else int(time_modified_ms)
    reg_name = region_name or name or DEFAULT_REGION_NAME

    region = {
        "Position": _size_compound(0, 0, 0),
        "Size": _size_compound(ax, ay, az),
        "BlockStatePalette": (TAG_LIST, (TAG_COMPOUND, palette_entries)),
        "BlockStates": (TAG_LONG_ARRAY, longs),
        "TileEntities": _empty_list(),
        "Entities": _empty_list(),
        "PendingBlockTicks": _empty_list(),
        "PendingFluidTicks": _empty_list(),
    }

    metadata = {
        "Name": (TAG_STRING, name),
        "Author": (TAG_STRING, author),
        "Description": (TAG_STRING, "the development repository workbench W9 export"),
        "TimeCreated": (TAG_LONG, t_created),
        "TimeModified": (TAG_LONG, t_modified),
        "EnclosingSize": _size_compound(ax, ay, az),
        "RegionCount": (TAG_INT, 1),
        "TotalBlocks": (TAG_INT, len(placed)),
        "TotalVolume": (TAG_INT, volume),
    }

    return {
        "Version": (TAG_INT, LITEMATIC_VERSION),
        "SubVersion": (TAG_INT, LITEMATIC_SUBVERSION),
        "MinecraftDataVersion": (TAG_INT, data_version),
        "Metadata": (TAG_COMPOUND, metadata),
        "Regions": (TAG_COMPOUND, {reg_name: (TAG_COMPOUND, region)}),
    }


def write_litematic(blocks, name=DEFAULT_REGION_NAME, author=DEFAULT_AUTHOR,
                    block_entities=None, data_version=DEFAULT_DATA_VERSION,
                    region_name=None, time_created_ms=None,
                    time_modified_ms=None):
    """`blocks` -> gzipped Version-6 `.litematic` bytes. See
    `build_litematic_nbt` for the block-input contract and refusals."""
    root = build_litematic_nbt(
        blocks, name=name, author=author, block_entities=block_entities,
        data_version=data_version, region_name=region_name,
        time_created_ms=time_created_ms, time_modified_ms=time_modified_ms)
    return write_nbt(root, root_name="")
