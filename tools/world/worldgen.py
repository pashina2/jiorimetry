#!/usr/bin/env python3
"""M9 E3 armed-world synthesis (ADR-0038 D4/W1'a).

Given a program (or pattern list), synthesizes ONE complete, loadable
Minecraft 1.20.6 world directory per pattern occurrence: the author-designed
amplifier fixture (drive head + template row + column skeleton) placed AT
`powered=true` rest, so that a server chunk-loads it already armed (the
proven update-free arming mechanism, dyn2-rest-verify -- chunk-load
preserves rest, structure placement does not).

Normative sources (nothing invented beyond them; see
notes/m9-e3-worldgen-task-spec.md, the binding contract):
- Fixture composition: notes/import/2026-07-19-amplifier-probe-fixture-v2/
  (extraction-and-acceptance.md + extraction-diff-dump.txt) -- task spec
  section 3 transcribes the operative data literally.
- Template rows: tools/m8-tplgen/tplgen.py, reused READ-ONLY as a module
  (same _load_module pattern tplgen itself uses for the m2-bridge).
- NBT primitives: tools/m2-bridge/litematic_to_nbt.py, reused READ-ONLY via
  tplgen's own already-loaded `bridge` attribute (read_nbt/write_nbt cover
  all tag types incl. TAG_Long_Array).

PROV-7 note: this module must not modify tplgen or the bridge; it only
imports them. Python stdlib only. Exit codes: 0 = success, 2 = usage /
contract error (no partial output on a contract error).
"""

import argparse
import gzip
import hashlib
import importlib.util
import io
import struct
import sys
import zlib
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent.parent


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Reused READ-ONLY (task spec section 1 / PROV-7): the row-template table
# and the pattern/program parsers are the consumer contract; import them
# rather than re-transcribe them. `tplgen` already loads m2-bridge itself
# (as `tplgen.bridge`) -- reuse that same loaded module rather than loading
# a second copy.
tplgen = _load_module("m9_worldgen_m8_tplgen", _HERE / "_deps" / "tplgen.py")
bridge = tplgen.bridge

ContractError = tplgen.ContractError

DEFAULT_DATA_VERSION = tplgen.DEFAULT_DATA_VERSION  # 3839 (1.20.6).
MC_VERSION_NAME = "1.20.6"
# Anvil STORAGE-format version marker (`Data.version`, lowercase -- distinct
# from `DataVersion`). 19133 = Anvil. Empirically REQUIRED: the 1.20.6 server
# refuses a level.dat without it ("Unknown data version: 0", L1 finding
# 2026-07-20, notes/m9-e3-live-acceptance/).
ANVIL_STORAGE_VERSION = 19133

# World-height convention (1.18+ overworld): sections -4..19 inclusive (24
# sections, y -64..319). Only used for the PostProcessing list count and the
# chunk `yPos` field -- the fixture itself only ever touches section 0.
MIN_SECTION_Y = -4
NUM_WORLD_SECTIONS = 24

_TSV_HEADER = "\t".join(["x", "y", "z", "block", "state-props"])


# ---------------------------------------------------------------------------
# Fixture composition (task spec section 3): NORMATIVE DATA, transcribed
# literally. Gold marker = world (0,0,0); v2 normalized frame used 1:1 as
# world coordinates.
# ---------------------------------------------------------------------------

_RAIL = "minecraft:powered_rail"
_GLASS = "minecraft:white_stained_glass"


def _rail(x, y, z, shape, powered):
    return (x, y, z), (_RAIL, {"powered": powered, "shape": shape, "waterlogged": "false"})


def _glass(x, y, z):
    return (x, y, z), (_GLASS, {})


def _block(x, y, z, name, props=None):
    return (x, y, z), (name, dict(props) if props else {})


# (a) Marker (1 block): gold_block at (0,0,0).
GOLD_MARKER = dict([_block(0, 0, 0, "minecraft:gold_block")])

# (b) Drive head (12 blocks, z=-1), transcribed from the import dump
# (task spec section 3(b) / extraction-diff-dump.txt "remainder" positions
# 2-14, excluding the sign at (1,3,-1)).
DRIVE_HEAD = dict([
    _block(0, 5, -1, "minecraft:lever",
           {"face": "wall", "facing": "west", "powered": "false"}),
    _block(1, 5, -1, "minecraft:lapis_block"),
    _block(2, 5, -1, "minecraft:piston", {"extended": "false", "facing": "east"}),
    _rail(2, 4, -1, "east_west", "true"),
    _block(2, 3, -1, "minecraft:observer", {"facing": "up", "powered": "false"}),
    # RS-1 intended rest state: (2,2,-1) powered=false. Do NOT "correct" it.
    _rail(2, 2, -1, "east_west", "false"),
    _glass(2, 1, -1),
    _block(3, 4, -1, "minecraft:observer", {"facing": "west", "powered": "false"}),
    _rail(3, 3, -1, "ascending_east", "true"),
    _glass(3, 2, -1),
    _rail(4, 4, -1, "east_west", "true"),
    _glass(4, 3, -1),
])

# Template-row shift (task spec section 3(c)): the import record's verified
# identity -- v2's x5..x10 row layer equals the v1 template's x1..x6 exactly.
ROW_X_SHIFT = 4

# (d) Column skeleton (12 blocks), pattern-INDEPENDENT. RS-1-corrected: ALL
# column rails powered=true (the saved v2 litematic's four powered=false
# states at x in {6,8} are a pre-save test-drive artifact per the author
# ruling, notes/import/2026-07-19-amplifier-probe-fixture-v2/
# extraction-and-acceptance.md RS-1).
COLUMN_X_CELLS = (6, 8, 10)
COLUMN_Z_ROWS = (-1, -2)


def _build_column_skeleton():
    out = {}
    for x in COLUMN_X_CELLS:
        for z in COLUMN_Z_ROWS:
            coord, value = _rail(x, 1, z, "north_south", "true")
            out[coord] = value
            coord, value = _glass(x, 0, z)
            out[coord] = value
    return out


COLUMN_SKELETON = _build_column_skeleton()

# (e) Row-label sign (M12 E2 task spec D2), present in EVERY row's
# composition BY DEFAULT (both generate modes). Blockstate is
# pattern-INDEPENDENT (only the block entity's text differs by pattern);
# position (1,3,-1) is the same fixture-relative frame as DRIVE_HEAD (x=1
# shares a column with the lapis marker at a different y -- no collision).
# Extracted from the v2 litematic's single tile entity (notes/import/
# 2026-07-19-amplifier-probe-fixture-v2/amplifier-template-8patterns-v1_011&
# source.litematic region TileEntities[0], read with the unmodified
# m2-bridge primitives); verified against the live extraction by
# test_worldgen.py's A2/D2 tests (fail-loud if the fixture file is missing).
SIGN_POSITION = (1, 3, -1)

SIGN_BLOCK = dict([
    _block(*SIGN_POSITION, "minecraft:oak_wall_sign",
           {"facing": "west", "waterlogged": "false"}),
])


def build_sign_block_entity(x, y, z, pattern):
    """The row-label sign's block-entity compound (task spec D2): the
    extraction verbatim except absolute x/y/z and
    front_text.messages[0] = '"<pattern>"' (JSON-string form). `keepPacked`
    is NOT added -- the extraction's own tile entity has no such field, and
    the D2 test requires DEEP equality against it; if the M12 E4 live
    acceptance finds it necessary for a clean server load, that is this
    function's amendment point (task spec D2 note)."""
    def _side_text(messages):
        return {
            "color": (bridge.TAG_STRING, "black"),
            "has_glowing_text": (bridge.TAG_BYTE, 0),
            "messages": (bridge.TAG_LIST, (bridge.TAG_STRING, list(messages))),
        }

    return {
        "id": (bridge.TAG_STRING, "minecraft:sign"),
        "x": (bridge.TAG_INT, x),
        "y": (bridge.TAG_INT, y),
        "z": (bridge.TAG_INT, z),
        "is_waxed": (bridge.TAG_BYTE, 0),
        "front_text": (bridge.TAG_COMPOUND,
                        _side_text([f'"{pattern}"', '""', '""', '""'])),
        "back_text": (bridge.TAG_COMPOUND,
                       _side_text(['""', '""', '""', '""'])),
    }


def build_fixture_block_entities(pattern):
    """One row's block-entity map (task spec D2), fixture-relative frame,
    UNSHIFTED -- multi-row composition shifts this the same way it shifts
    the row's placements (task spec D1)."""
    x, y, z = SIGN_POSITION
    return {SIGN_POSITION: build_sign_block_entity(x, y, z, pattern)}


def _merge_placements(*maps):
    """Union placement (or block-entity) maps; a coordinate collision is a
    contract error (fail loud, not overwrite -- task spec section 3)."""
    out = {}
    for m in maps:
        for coord, value in m.items():
            if coord in out:
                raise ContractError(
                    f"coordinate collision at {coord}: "
                    f"{out[coord]} vs {value}")
            out[coord] = value
    return out


def _build_fixed_part_no_gold():
    """(b)+(d)+(e): the pattern-independent part of the fixture, EXCLUDING
    the gold marker (task spec D1 multi-row: gold appears once per world,
    not once per row)."""
    return _merge_placements(DRIVE_HEAD, COLUMN_SKELETON, SIGN_BLOCK)


def build_fixed_part():
    """(a)+(b)+(d)+(e): the pattern-independent part of the fixture,
    including the gold marker (single-row / per-pattern-world use)."""
    return _merge_placements(GOLD_MARKER, _build_fixed_part_no_gold())


def _build_row_placements_no_gold(pattern):
    """One row's full composition (drive head + template row + column
    skeleton + sign), EXCLUDING the gold marker -- task spec D1's
    "single-row composition" building block for multi-row assembly."""
    row = tplgen.build_row_placements(pattern, 0)
    shifted_row = {(x + ROW_X_SHIFT, y, z): value for (x, y, z), value in row.items()}
    return _merge_placements(_build_fixed_part_no_gold(), shifted_row)


def build_fixture_placements(pattern):
    """Full composed block map for one pattern (task spec section 3):
    gold marker UNION the fixed part UNION the template row shifted +4 in
    x (39 blocks: (a)+(b)+(d)+(e)+13-block row)."""
    return _merge_placements(GOLD_MARKER, _build_row_placements_no_gold(pattern))


def _shift_z_map(value_map, dz):
    """Shift every coordinate key's z by dz (task spec D1 multi-row row
    stride); values (blockstate tuples or block-entity compounds) are
    unchanged by THIS helper -- block entities carry their own x/y/z and
    are shifted separately by _shift_block_entities."""
    return {(x, y, z + dz): value for (x, y, z), value in value_map.items()}


def _shift_block_entities(block_entities, dz):
    """Shift a block-entity map's coordinate keys AND each compound's own
    embedded x/y/z fields by dz (task spec D1)."""
    out = {}
    for (x, y, z), entry in block_entities.items():
        shifted_entry = dict(entry)
        shifted_entry["z"] = (bridge.TAG_INT, entry["z"][1] + dz)
        out[(x, y, z + dz)] = shifted_entry
    return out


def build_multi_row_placements(patterns):
    """Task spec D1: row r = the single-row composition (drive head +
    template row + column skeleton + sign) of patterns[r], z-shifted by
    -2r; ONE gold marker at world (0,0,0) (rows share the world anchor).
    Coordinate collisions across rows are a contract error -- the merge
    check IS the guard (they must not occur at the 2-block stride, not
    assumed safe)."""
    if not patterns:
        raise ContractError("no patterns given")
    parts = [GOLD_MARKER]
    for row_index, pattern in enumerate(patterns):
        row = _build_row_placements_no_gold(pattern)
        parts.append(_shift_z_map(row, -2 * row_index))
    return _merge_placements(*parts)


def build_multi_row_block_entities(patterns):
    """Task spec D1: the row-label sign's block entity for every row, same
    z-shift as its row's placements."""
    parts = []
    for row_index, pattern in enumerate(patterns):
        row_entities = build_fixture_block_entities(pattern)
        parts.append(_shift_block_entities(row_entities, -2 * row_index))
    return _merge_placements(*parts)


# ---------------------------------------------------------------------------
# Manifest TSV (task spec section 4): EXACTLY tplgen's placements-TSV
# format -- reused directly, not reimplemented.
# ---------------------------------------------------------------------------


def render_blocks_tsv(placements):
    return tplgen.render_placements_tsv(placements)


# ---------------------------------------------------------------------------
# Region/chunk packing (task spec section 4, Anvil format).
# ---------------------------------------------------------------------------


def _chunk_of(x, z):
    return x >> 4, z >> 4


def _region_of(cx, cz):
    return cx >> 5, cz >> 5


def _group_by_chunk(placements):
    chunks = {}
    for (x, y, z), value in placements.items():
        cx, cz = _chunk_of(x, z)
        chunks.setdefault((cx, cz), {})[(x, y, z)] = value
    return chunks


def _pack_indices(indices, bits):
    """Post-1.16 paletted-container packing: entries do NOT span longs."""
    values_per_long = 64 // bits
    mask = (1 << bits) - 1
    unsigned_longs = []
    for i in range(0, len(indices), values_per_long):
        group = indices[i:i + values_per_long]
        val = 0
        for j, v in enumerate(group):
            val |= (v & mask) << (j * bits)
        unsigned_longs.append(val)
    return [v - (1 << 64) if v >= (1 << 63) else v for v in unsigned_longs]


def _bits_for_palette(size):
    return max(4, (size - 1).bit_length()) if size > 1 else 4


def _build_section_nbt(section_y, local_blocks):
    """local_blocks: {(lx,ly,lz) in 0..15: (block, props)} -> section compound."""
    palette = []
    palette_index = {}

    def get_index(block, props):
        key = (block, tuple(sorted(props.items())))
        if key not in palette_index:
            palette_index[key] = len(palette)
            palette.append((block, props))
        return palette_index[key]

    air_index = get_index("minecraft:air", {})
    grid = [air_index] * 4096
    for (lx, ly, lz), (block, props) in local_blocks.items():
        if not (0 <= lx < 16 and 0 <= ly < 16 and 0 <= lz < 16):
            raise ContractError(
                f"local coordinate out of section bounds: {(lx, ly, lz)}")
        grid[(ly * 16 + lz) * 16 + lx] = get_index(block, props)

    palette_entries = []
    for block, props in palette:
        entry = {"Name": (bridge.TAG_STRING, block)}
        if props:
            entry["Properties"] = (
                bridge.TAG_COMPOUND,
                {k: (bridge.TAG_STRING, v) for k, v in props.items()},
            )
        palette_entries.append(entry)

    block_states = {
        "palette": (bridge.TAG_LIST, (bridge.TAG_COMPOUND, palette_entries)),
    }
    if len(palette) > 1:
        bits = _bits_for_palette(len(palette))
        block_states["data"] = (bridge.TAG_LONG_ARRAY, _pack_indices(grid, bits))

    biomes = {
        "palette": (bridge.TAG_LIST, (bridge.TAG_STRING, ["minecraft:the_void"])),
    }

    return {
        "Y": (bridge.TAG_BYTE, section_y),
        "block_states": (bridge.TAG_COMPOUND, block_states),
        "biomes": (bridge.TAG_COMPOUND, biomes),
    }


def build_chunk_nbt(cx, cz, chunk_blocks, chunk_entities, data_version):
    """chunk_entities: {(x,y,z): block-entity compound} for THIS chunk only
    (task spec: each chunk's block_entities list carries its signs'
    compounds; chunks without signs keep empty block_entities)."""
    sections_by_y = {}
    for (x, y, z), value in chunk_blocks.items():
        sy = y >> 4
        local = (x - cx * 16, y - sy * 16, z - cz * 16)
        sections_by_y.setdefault(sy, {})[local] = value

    sections = [_build_section_nbt(sy, sections_by_y[sy]) for sy in sorted(sections_by_y)]
    empty_list = (bridge.TAG_LIST, (bridge.TAG_END, []))

    if chunk_entities:
        # Deterministic order (task spec D5): sorted by absolute position.
        block_entities_list = (
            bridge.TAG_LIST,
            (bridge.TAG_COMPOUND,
             [chunk_entities[coord] for coord in sorted(chunk_entities)]),
        )
    else:
        block_entities_list = empty_list

    return {
        "DataVersion": (bridge.TAG_INT, data_version),
        "xPos": (bridge.TAG_INT, cx),
        "zPos": (bridge.TAG_INT, cz),
        "yPos": (bridge.TAG_INT, MIN_SECTION_Y),
        "Status": (bridge.TAG_STRING, "minecraft:full"),
        "LastUpdate": (bridge.TAG_LONG, 0),
        "InhabitedTime": (bridge.TAG_LONG, 0),
        "sections": (bridge.TAG_LIST, (bridge.TAG_COMPOUND, sections)),
        "block_entities": block_entities_list,
        "block_ticks": empty_list,
        "fluid_ticks": empty_list,
        "PostProcessing": (
            bridge.TAG_LIST,
            (bridge.TAG_LIST, [(bridge.TAG_END, []) for _ in range(NUM_WORLD_SECTIONS)]),
        ),
        "structures": (bridge.TAG_COMPOUND, {}),
    }


_SECTOR_SIZE = 4096
_HEADER_SECTORS = 2  # location table + timestamp table, 1 sector each.


def build_region_bytes(region_chunks, data_version):
    """region_chunks: {(cx,cz): ({(x,y,z):(block,props)}, {(x,y,z):entity})}
    all in ONE region.

    Returns the .mca bytes (4KiB-sector Anvil format, big-endian location
    table, per-chunk timestamp 0, zlib payload compression type 2).
    """
    locations = [0] * 1024
    timestamps = [0] * 1024
    payload_sectors = []
    next_sector = _HEADER_SECTORS

    for (cx, cz), (chunk_blocks, chunk_entities) in sorted(region_chunks.items()):
        chunk_nbt = build_chunk_nbt(cx, cz, chunk_blocks, chunk_entities, data_version)
        raw = bridge.write_nbt(chunk_nbt, root_name="", compress=False)
        compressed = zlib.compress(raw)
        payload = struct.pack(">B", 2) + compressed  # compression type 2 = zlib
        framed = struct.pack(">I", len(payload)) + payload
        pad = (-len(framed)) % _SECTOR_SIZE
        framed += b"\x00" * pad
        sector_count = len(framed) // _SECTOR_SIZE
        if sector_count > 255:
            raise ContractError(
                f"chunk ({cx},{cz}) needs {sector_count} sectors, exceeds "
                "the Anvil 1-byte sector-count limit (255)")

        rx, rz = cx & 31, cz & 31
        idx = rz * 32 + rx
        locations[idx] = (next_sector << 8) | sector_count
        timestamps[idx] = 0
        payload_sectors.append(framed)
        next_sector += sector_count

    loc_bytes = b"".join(struct.pack(">I", v) for v in locations)
    ts_bytes = b"".join(struct.pack(">I", v) for v in timestamps)
    return loc_bytes + ts_bytes + b"".join(payload_sectors)


def build_region_files(placements, block_entities, data_version):
    """placements + block_entities -> {(rx,rz): region_bytes} for every
    region containing a fixture chunk (task spec section 4: only regions
    that contain blocks; a chunk with entities but no other blocks would
    also be included, though the fixture never produces one)."""
    chunks = _group_by_chunk(placements)
    entity_chunks = _group_by_chunk(block_entities)
    by_region = {}
    for (cx, cz) in set(chunks) | set(entity_chunks):
        chunk_blocks = chunks.get((cx, cz), {})
        chunk_entities = entity_chunks.get((cx, cz), {})
        rx, rz = _region_of(cx, cz)
        by_region.setdefault((rx, rz), {})[(cx, cz)] = (chunk_blocks, chunk_entities)
    return {region: build_region_bytes(chunk_map, data_version)
            for region, chunk_map in by_region.items()}


# ---------------------------------------------------------------------------
# Region/chunk reading (the implementation's OWN reader, task spec A4).
# ---------------------------------------------------------------------------


def read_region_bytes(data):
    """.mca bytes -> {(cx_local_bits omitted): ...}. Returns a dict keyed by
    the LOCAL chunk index (rx=idx%32, rz=idx//32) -> parsed chunk dict, for
    every non-empty location-table slot. Caller supplies the region's own
    (rx,rz) to recover absolute chunk coordinates."""
    if len(data) < _HEADER_SECTORS * _SECTOR_SIZE:
        raise ContractError("region file shorter than the 2-sector header")
    locations = struct.unpack(">1024I", data[0:4096])
    out = {}
    for idx, loc in enumerate(locations):
        if loc == 0:
            continue
        sector_offset = loc >> 8
        sector_count = loc & 0xFF
        start = sector_offset * _SECTOR_SIZE
        end = start + sector_count * _SECTOR_SIZE
        chunk_bytes = data[start:end]
        (length,) = struct.unpack(">I", chunk_bytes[0:4])
        compression = chunk_bytes[4]
        if compression != 2:
            raise ContractError(f"unsupported chunk compression type {compression}")
        compressed = chunk_bytes[5:4 + length]
        raw = zlib.decompress(compressed)
        _name, chunk_nbt = bridge.read_nbt(raw)
        out[idx] = chunk_nbt
    return out


def _decode_section_blocks(section, cx, cz):
    sy = section["Y"][1]
    block_states = section["block_states"][1]
    palette_entries = block_states["palette"][1][1]
    palette = []
    for entry in palette_entries:
        name = entry["Name"][1]
        props = {}
        if "Properties" in entry:
            props = {k: v[1] for k, v in entry["Properties"][1].items()}
        palette.append((name, props))

    if len(palette) <= 1:
        indices = [0] * 4096
    else:
        bits = _bits_for_palette(len(palette))
        longs = block_states["data"][1]
        values_per_long = 64 // bits
        mask = (1 << bits) - 1
        indices = []
        for v in longs:
            uv = v & 0xFFFFFFFFFFFFFFFF
            for j in range(values_per_long):
                if len(indices) >= 4096:
                    break
                indices.append((uv >> (j * bits)) & mask)

    blocks = {}
    i = 0
    for ly in range(16):
        for lz in range(16):
            for lx in range(16):
                name, props = palette[indices[i]]
                i += 1
                if name != "minecraft:air":
                    x = cx * 16 + lx
                    y = sy * 16 + ly
                    z = cz * 16 + lz
                    blocks[(x, y, z)] = (name, props)
    return blocks


def _decode_chunk_block_entities(chunk_nbt):
    """A chunk's block_entities list -> {(x,y,z): compound} (task spec D4:
    the reader extended to return block entities); empty for a chunk with
    no signs (empty list -> empty dict)."""
    entries = chunk_nbt["block_entities"][1][1]
    out = {}
    for entry in entries:
        pos = (entry["x"][1], entry["y"][1], entry["z"][1])
        out[pos] = entry
    return out


def decode_region_blocks(data, rx, rz):
    """Full round-trip: region bytes -> {(x,y,z): (block,props)} plus a
    per-chunk metadata dict plus {(x,y,z): block-entity compound} (task spec
    D4), for the implementation's own A4/D4 reader."""
    chunks = read_region_bytes(data)
    blocks = {}
    chunk_meta = {}
    block_entities = {}
    for idx, chunk_nbt in chunks.items():
        local_rx, local_rz = idx % 32, idx // 32
        cx, cz = rx * 32 + local_rx, rz * 32 + local_rz
        chunk_meta[(cx, cz)] = chunk_nbt
        for section in chunk_nbt["sections"][1][1]:
            blocks.update(_decode_section_blocks(section, cx, cz))
        block_entities.update(_decode_chunk_block_entities(chunk_nbt))
    return blocks, chunk_meta, block_entities


# ---------------------------------------------------------------------------
# level.dat (task spec section 4).
# ---------------------------------------------------------------------------

GAME_RULES = {
    "spawnChunkRadius": "0",
    "doDaylightCycle": "false",
    "doWeatherCycle": "false",
    "doMobSpawning": "false",
    "doFireTick": "false",
    "randomTickSpeed": "0",
}


def build_level_dat(level_name, data_version):
    version_compound = {
        "Id": (bridge.TAG_INT, data_version),
        "Name": (bridge.TAG_STRING, MC_VERSION_NAME),
        "Series": (bridge.TAG_STRING, "main"),
        "Snapshot": (bridge.TAG_BYTE, 0),
    }
    flat_settings = {
        "layers": (bridge.TAG_LIST, (bridge.TAG_END, [])),
        "biome": (bridge.TAG_STRING, "minecraft:the_void"),
        "features": (bridge.TAG_BYTE, 0),
        "lakes": (bridge.TAG_BYTE, 0),
    }
    generator = {
        "type": (bridge.TAG_STRING, "minecraft:flat"),
        "settings": (bridge.TAG_COMPOUND, flat_settings),
    }
    overworld_dim = {
        "type": (bridge.TAG_STRING, "minecraft:overworld"),
        "generator": (bridge.TAG_COMPOUND, generator),
    }
    worldgen_settings = {
        "seed": (bridge.TAG_LONG, 0),
        "generate_features": (bridge.TAG_BYTE, 0),
        "dimensions": (
            bridge.TAG_COMPOUND,
            {"minecraft:overworld": (bridge.TAG_COMPOUND, overworld_dim)},
        ),
    }
    game_rules = {k: (bridge.TAG_STRING, v) for k, v in GAME_RULES.items()}
    data = {
        "DataVersion": (bridge.TAG_INT, data_version),
        "version": (bridge.TAG_INT, ANVIL_STORAGE_VERSION),
        "Version": (bridge.TAG_COMPOUND, version_compound),
        "LevelName": (bridge.TAG_STRING, level_name),
        "GameType": (bridge.TAG_INT, 1),
        "allowCommands": (bridge.TAG_BYTE, 1),
        "Difficulty": (bridge.TAG_BYTE, 0),
        "initialized": (bridge.TAG_BYTE, 1),
        "SpawnX": (bridge.TAG_INT, 0),
        "SpawnY": (bridge.TAG_INT, 1),
        "SpawnZ": (bridge.TAG_INT, 0),
        "WorldGenSettings": (bridge.TAG_COMPOUND, worldgen_settings),
        "GameRules": (bridge.TAG_COMPOUND, game_rules),
    }
    root = {"Data": (bridge.TAG_COMPOUND, data)}
    # Deterministic gzip: bridge.write_nbt(compress=True) uses gzip.compress,
    # whose header embeds the wall-clock second -- that broke A6 byte-identity
    # whenever two generations straddled a second boundary (the LOG E62 gate
    # flake, root-caused 2026-07-20). Compress here with mtime=0 instead; the
    # bridge itself stays unmodified (PROV-7).
    raw = bridge.write_nbt(root, root_name="", compress=False)
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as handle:
        handle.write(raw)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# World assembly (task spec sections 4-5).
# ---------------------------------------------------------------------------


class World:
    __slots__ = ("name", "placements", "level_dat", "regions", "tsv")

    def __init__(self, name, placements, level_dat, regions, tsv):
        self.name = name
        self.placements = placements
        self.level_dat = level_dat
        self.regions = regions  # {(rx,rz): bytes}
        self.tsv = tsv


def build_world(name, pattern, row_index, data_version):
    """Unchanged signature/return shape (worldgen.World with the frozen
    5-slot constructor) -- `placements`/`tsv` now include the row's sign
    (task spec D2), and the sign's block entity is embedded in `regions`
    via build_region_files (D2/D4); nothing about the World class itself
    changed, since tools/m9-dynharness/dynharness.py constructs
    `worldgen.World(...)` positionally for the online-place world_source
    and must not need editing (PROV-7 boundary)."""
    world_name = f"{name}_r{row_index}_{pattern}"
    placements = build_fixture_placements(pattern)
    block_entities = build_fixture_block_entities(pattern)
    level_dat = build_level_dat(world_name, data_version)
    regions = build_region_files(placements, block_entities, data_version)
    tsv = render_blocks_tsv(placements).encode("utf-8")
    return World(world_name, placements, level_dat, regions, tsv)


def build_worlds(patterns, data_version=DEFAULT_DATA_VERSION, name="world"):
    if not patterns:
        raise ContractError("no patterns given")
    worlds = []
    seen_names = set()
    for row_index, pattern in enumerate(patterns):
        world = build_world(name, pattern, row_index, data_version)
        if world.name in seen_names:
            raise ContractError(f"duplicate world name {world.name!r}")
        seen_names.add(world.name)
        worlds.append(world)
    return worlds


def build_multi_row_world(name, patterns, data_version):
    """Task spec D1: ONE world named `<name>_rows<N>` (N = row count)
    holding every row's composition, z-shifted by -2r, with ONE gold marker
    shared at world (0,0,0). Same World shape as build_world (frozen
    5-slot constructor, PROV-7 boundary above)."""
    if not patterns:
        raise ContractError("no patterns given")
    world_name = f"{name}_rows{len(patterns)}"
    placements = build_multi_row_placements(patterns)
    block_entities = build_multi_row_block_entities(patterns)
    level_dat = build_level_dat(world_name, data_version)
    regions = build_region_files(placements, block_entities, data_version)
    tsv = render_blocks_tsv(placements).encode("utf-8")
    return World(world_name, placements, level_dat, regions, tsv)


def _region_filename(rx, rz):
    return f"r.{rx}.{rz}.mca"


def check_no_overwrite(out_dir, worlds):
    """Refuse to overwrite an existing world dir or manifest (task spec
    section 5) -- checked BEFORE any write (no partial output on error)."""
    out_dir = Path(out_dir)
    for world in worlds:
        world_dir = out_dir / world.name
        tsv_path = out_dir / f"{world.name}_blocks.tsv"
        if world_dir.exists():
            raise ContractError(f"refusing to overwrite existing world dir: {world_dir}")
        if tsv_path.exists():
            raise ContractError(f"refusing to overwrite existing manifest: {tsv_path}")


def write_worlds(out_dir, worlds):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for world in worlds:
        world_dir = out_dir / world.name
        region_dir = world_dir / "region"
        region_dir.mkdir(parents=True, exist_ok=False)
        (world_dir / "level.dat").write_bytes(world.level_dat)
        for (rx, rz), region_bytes in world.regions.items():
            (region_dir / _region_filename(rx, rz)).write_bytes(region_bytes)
        (out_dir / f"{world.name}_blocks.tsv").write_bytes(world.tsv)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="worldgen.py",
        description=(
            "M9 E3 armed-world synthesis: emit one loadable Minecraft "
            "1.20.6 world per pattern, with the author-designed amplifier "
            "fixture placed AT powered=true rest (ADR-0038)."))
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate", help="generate one world per pattern")
    gen.add_argument(
        "--patterns", default=None,
        help="comma-separated 3-char binary pattern strings (b2b1b0)")
    gen.add_argument(
        "--program", default=None,
        help="program bitstream text file (0/1 chars, grouped by 3)")
    gen.add_argument("--name", required=True, help="world-name base")
    gen.add_argument("--out-dir", required=True, help="output directory")
    gen.add_argument("--data-version", type=int, default=DEFAULT_DATA_VERSION,
                      help=f"NBT DataVersion (default {DEFAULT_DATA_VERSION})")
    gen.add_argument(
        "--multi-row", action="store_true",
        help=("emit ONE world '<name>_rows<N>' holding all rows z-shifted "
              "by -2 per row, instead of one world per pattern (task spec "
              "D1)"))
    args = parser.parse_args(argv)

    has_patterns = args.patterns is not None
    has_program = args.program is not None
    if has_patterns == has_program:
        print("error: exactly one of --patterns or --program is required",
              file=sys.stderr)
        return 2

    try:
        if has_patterns:
            patterns = tplgen.parse_patterns_arg(args.patterns)
        else:
            patterns = tplgen.parse_program_file(args.program)
        if args.multi_row:
            worlds = [build_multi_row_world(args.name, patterns, args.data_version)]
        else:
            worlds = build_worlds(patterns, args.data_version, args.name)
        out_dir = Path(args.out_dir)
        check_no_overwrite(out_dir, worlds)
    except ContractError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    write_worlds(out_dir, worlds)

    for world in worlds:
        world_dir = out_dir / world.name
        tsv_path = out_dir / f"{world.name}_blocks.tsv"
        print(f"world: {world_dir}")
        print(f"  blocks-tsv: {tsv_path}")
        print(f"    sha256: {_sha256_bytes(world.tsv)}")
        for (rx, rz) in sorted(world.regions):
            region_path = world_dir / "region" / _region_filename(rx, rz)
            print(f"  region: {region_path}")
            print(f"    sha256: {_sha256_bytes(world.regions[(rx, rz)])}")
        print(f"  block-count: {len(world.placements)}")

    return 0


if __name__ == "__main__":
    # cp932: stdout is strict by default and one unencodable
    # character costs the whole run. Why `errors=` and not
    # `encoding=`: tools/test_console_encoding.py.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    sys.exit(main())
