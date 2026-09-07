#!/usr/bin/env python3
"""M2 authoring bridge: Litematica `.litematic` -> vanilla structure `.nbt`.

Converts a Rommatic-era authoring artifact (Litematica format, DataVersion
3839 / 1.20.6) into a vanilla structure template that the pinned 1.21.11
verification runtime DFU-upgrades on load (ADR-0015 Track B; feasibility
proven by M1 Probe 1 in `notes/m1-underdefined-probes.md`).

This is a PURE FILE TRANSFORM: it reads one existing `.litematic`, decodes it,
and writes one `.nbt`. It fabricates nothing, edits no authoring artifact, and
launches nothing. The output is a generated artifact (ADR-0007): never
hand-edited, never canonical, not committed to git.

Input contract (fail loudly outside it, per ADR-0015):
- Litematica `Version` 6 (the encoding verified exactly during M0 Tier 3
  against the real artifacts `demo8_1`/`smoke1`: bits/entry =
  `max(2, ceil(log2(paletteSize)))`, tightly bit-packed little-endian across
  the unsigned 64-bit `BlockStates` longs with entries spanning long
  boundaries, `YZX` index order, `BlockStatePalette[0] = minecraft:air`).
- Exactly one region; empty `TileEntities`/`Entities`/`PendingBlockTicks`/
  `PendingFluidTicks`.

Self-check: the decoded non-air block count must equal the artifact's own
`Metadata.TotalBlocks`; a mismatch means a decode bug, and the tool refuses to
write output.

Output: gzipped vanilla structure template NBT — `size`, `palette`
(`Name`/`Properties` carried over verbatim), `blocks` (`pos`/`state`, air
included, anchored at 0,0,0), empty `entities`, and the SOURCE `DataVersion`
(the runtime's DataFixer performs the upgrade on load, the exact path M1
Probe 1 validated). The 1.21.11 datapack/generated registry path is SINGULAR
(`data/<ns>/structure/`), per the same probe.

Python stdlib only. Exit codes: 0 = converted (or --info printed),
1 = self-check mismatch (nothing written), 2 = usage/contract/parse errors.
"""

import argparse
import gzip
import io
import math
import struct
import sys
from pathlib import Path

__version__ = "0.1.0"

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

SUPPORTED_LITEMATIC_VERSION = 6

# NBT tag ids
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


class ContractError(Exception):
    """Input violates the v0 converter contract (ADR-0015 Track B)."""


# ---------------------------------------------------------------------------
# Minimal NBT model: every value is (tag_id, payload).
# Compound payload: dict name -> (tag_id, payload). List payload:
# (element_tag_id, [payload, ...]).
# ---------------------------------------------------------------------------


def _read_exact(buf, n):
    data = buf.read(n)
    if len(data) != n:
        raise ContractError("unexpected end of NBT data")
    return data


def _read_string(buf):
    (length,) = struct.unpack(">H", _read_exact(buf, 2))
    return _read_exact(buf, length).decode("utf-8")


def _read_payload(buf, tag_id):
    if tag_id == TAG_BYTE:
        return struct.unpack(">b", _read_exact(buf, 1))[0]
    if tag_id == TAG_SHORT:
        return struct.unpack(">h", _read_exact(buf, 2))[0]
    if tag_id == TAG_INT:
        return struct.unpack(">i", _read_exact(buf, 4))[0]
    if tag_id == TAG_LONG:
        return struct.unpack(">q", _read_exact(buf, 8))[0]
    if tag_id == TAG_FLOAT:
        return struct.unpack(">f", _read_exact(buf, 4))[0]
    if tag_id == TAG_DOUBLE:
        return struct.unpack(">d", _read_exact(buf, 8))[0]
    if tag_id == TAG_BYTE_ARRAY:
        (n,) = struct.unpack(">i", _read_exact(buf, 4))
        return list(struct.unpack(f">{n}b", _read_exact(buf, n)))
    if tag_id == TAG_STRING:
        return _read_string(buf)
    if tag_id == TAG_LIST:
        (etype,) = struct.unpack(">b", _read_exact(buf, 1))
        (n,) = struct.unpack(">i", _read_exact(buf, 4))
        return (etype, [_read_payload(buf, etype) for _ in range(n)])
    if tag_id == TAG_COMPOUND:
        out = {}
        while True:
            (child,) = struct.unpack(">b", _read_exact(buf, 1))
            if child == TAG_END:
                return out
            name = _read_string(buf)
            out[name] = (child, _read_payload(buf, child))
    if tag_id == TAG_INT_ARRAY:
        (n,) = struct.unpack(">i", _read_exact(buf, 4))
        return list(struct.unpack(f">{n}i", _read_exact(buf, 4 * n)))
    if tag_id == TAG_LONG_ARRAY:
        (n,) = struct.unpack(">i", _read_exact(buf, 4))
        return list(struct.unpack(f">{n}q", _read_exact(buf, 8 * n)))
    raise ContractError(f"unsupported NBT tag id {tag_id}")


def read_nbt(data):
    """Parse gzipped-or-plain NBT bytes -> (root_name, root_compound)."""
    if data[:2] == b"\x1f\x8b":
        data = gzip.decompress(data)
    buf = io.BytesIO(data)
    (tag_id,) = struct.unpack(">b", _read_exact(buf, 1))
    if tag_id != TAG_COMPOUND:
        raise ContractError(f"root tag is {tag_id}, expected compound")
    name = _read_string(buf)
    return name, _read_payload(buf, TAG_COMPOUND)


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
    elif tag_id == TAG_BYTE_ARRAY:
        out.write(struct.pack(">i", len(payload)))
        out.write(struct.pack(f">{len(payload)}b", *payload))
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
        raise ContractError(f"unsupported NBT tag id {tag_id}")


def write_nbt(root_compound, root_name="", compress=True):
    """Serialize a compound payload dict -> NBT bytes (gzipped by default)."""
    out = io.BytesIO()
    out.write(struct.pack(">b", TAG_COMPOUND))
    _write_string(out, root_name)
    _write_payload(out, TAG_COMPOUND, root_compound)
    raw = out.getvalue()
    return gzip.compress(raw) if compress else raw


# ---------------------------------------------------------------------------
# Litematic decoding
# ---------------------------------------------------------------------------


def _get(compound, name, tag_id, where):
    if name not in compound:
        raise ContractError(f"{where}: missing '{name}'")
    actual, payload = compound[name]
    if actual != tag_id:
        raise ContractError(
            f"{where}: '{name}' has tag {actual}, expected {tag_id}"
        )
    return payload


def _require_empty_list(region, name, where):
    if name not in region:
        return
    tag_id, payload = region[name]
    if tag_id != TAG_LIST:
        raise ContractError(f"{where}: '{name}' is not a list")
    if payload[1]:
        raise ContractError(
            f"{where}: '{name}' is non-empty ({len(payload[1])} entries) — "
            "outside the v0 converter contract (ADR-0015)"
        )


def bits_per_entry(palette_size):
    """Litematica packing width, verified in M0 Tier 3."""
    return max(2, math.ceil(math.log2(palette_size))) if palette_size > 1 else 2


def unpack_block_states(longs, palette_size, volume):
    """Decode the tightly-packed little-endian BlockStates long array.

    Entries span 64-bit long boundaries (Litematica's LitematicaBitArray),
    unlike the padded per-long packing of post-1.16 chunk sections.
    """
    bits = bits_per_entry(palette_size)
    need_longs = (volume * bits + 63) // 64
    if len(longs) < need_longs:
        raise ContractError(
            f"BlockStates too short: {len(longs)} longs for volume {volume} "
            f"at {bits} bits/entry (need {need_longs})"
        )
    ulongs = [v & 0xFFFFFFFFFFFFFFFF for v in longs]
    mask = (1 << bits) - 1
    out = []
    for i in range(volume):
        start = i * bits
        li = start >> 6
        off = start & 63
        value = ulongs[li] >> off
        if off + bits > 64:
            value |= ulongs[li + 1] << (64 - off)
        index = value & mask
        if index >= palette_size:
            raise ContractError(
                f"decoded palette index {index} out of range "
                f"(palette size {palette_size}) at entry {i}"
            )
        out.append(index)
    return out


def load_litematic(data):
    """Decode `.litematic` bytes into a summary dict.

    Returns: {data_version, version, sub_version, region_name,
    size (ax, ay, az), palette (list of (tag, payload) compounds),
    indices (flat YZX list), total_blocks_meta, counts (per palette index)}.
    """
    _name, root = read_nbt(data)

    version = _get(root, "Version", TAG_INT, "root")
    if version != SUPPORTED_LITEMATIC_VERSION:
        raise ContractError(
            f"litematic Version {version} unsupported "
            f"(contract: {SUPPORTED_LITEMATIC_VERSION})"
        )
    sub_version = None
    if "SubVersion" in root:
        sub_version = root["SubVersion"][1]
    data_version = _get(root, "MinecraftDataVersion", TAG_INT, "root")

    regions = _get(root, "Regions", TAG_COMPOUND, "root")
    if len(regions) != 1:
        raise ContractError(
            f"{len(regions)} regions found — the v0 contract is exactly one "
            "(ADR-0015)"
        )
    region_name, (region_tag, region) = next(iter(regions.items()))
    if region_tag != TAG_COMPOUND:
        raise ContractError(f"region '{region_name}' is not a compound")

    where = f"region '{region_name}'"
    size = _get(region, "Size", TAG_COMPOUND, where)
    sx = _get(size, "x", TAG_INT, where + ".Size")
    sy = _get(size, "y", TAG_INT, where + ".Size")
    sz = _get(size, "z", TAG_INT, where + ".Size")
    ax, ay, az = abs(sx), abs(sy), abs(sz)
    volume = ax * ay * az
    if volume == 0:
        raise ContractError(f"{where}: zero-volume region")

    palette_tag = _get(region, "BlockStatePalette", TAG_LIST, where)
    etype, palette = palette_tag
    if etype != TAG_COMPOUND or not palette:
        raise ContractError(f"{where}: BlockStatePalette empty or not compounds")

    for field in ("TileEntities", "Entities", "PendingBlockTicks",
                  "PendingFluidTicks"):
        _require_empty_list(region, field, where)

    longs = _get(region, "BlockStates", TAG_LONG_ARRAY, where)
    indices = unpack_block_states(longs, len(palette), volume)

    counts = [0] * len(palette)
    for index in indices:
        counts[index] += 1

    total_blocks_meta = None
    if "Metadata" in root and root["Metadata"][0] == TAG_COMPOUND:
        meta = root["Metadata"][1]
        if "TotalBlocks" in meta:
            total_blocks_meta = meta["TotalBlocks"][1]

    return {
        "data_version": data_version,
        "version": version,
        "sub_version": sub_version,
        "region_name": region_name,
        "size": (ax, ay, az),
        "palette": palette,
        "indices": indices,
        "total_blocks_meta": total_blocks_meta,
        "counts": counts,
    }


# ---------------------------------------------------------------------------
# Structure template emission
# ---------------------------------------------------------------------------


def build_structure_nbt(lit):
    """Build the vanilla structure template compound from a decoded litematic.

    Blocks are anchored at (0,0,0); air entries are included (a
    structure-block-saved template includes them); palette order and
    Name/Properties payloads are carried over verbatim; DataVersion is the
    SOURCE version (DFU upgrades on load).
    """
    ax, ay, az = lit["size"]
    blocks = []
    i = 0
    for y in range(ay):
        for z in range(az):
            for x in range(ax):
                state = lit["indices"][i]
                i += 1
                blocks.append(
                    {
                        "pos": (TAG_LIST, (TAG_INT, [x, y, z])),
                        "state": (TAG_INT, state),
                    }
                )
    palette = []
    for tag_id, entry in [(TAG_COMPOUND, p) for p in lit["palette"]]:
        carried = {}
        if "Name" not in entry:
            raise ContractError("palette entry without Name")
        carried["Name"] = entry["Name"]
        if "Properties" in entry:
            carried["Properties"] = entry["Properties"]
        palette.append(carried)
    return {
        "size": (TAG_LIST, (TAG_INT, [ax, ay, az])),
        "entities": (TAG_LIST, (TAG_END, [])),
        "blocks": (TAG_LIST, (TAG_COMPOUND, blocks)),
        "palette": (TAG_LIST, (TAG_COMPOUND, palette)),
        "DataVersion": (TAG_INT, lit["data_version"]),
    }


def palette_name(entry):
    return entry["Name"][1] if "Name" in entry else "<unnamed>"


def render_summary(lit, source, dest):
    ax, ay, az = lit["size"]
    non_air = sum(
        c
        for entry, c in zip(lit["palette"], lit["counts"])
        if palette_name(entry) != "minecraft:air"
    )
    lines = [
        f"source: {source}",
        f"litematic_version: {lit['version']} (SubVersion {lit['sub_version']})",
        f"data_version: {lit['data_version']}",
        f"region: {lit['region_name']}",
        f"size: {ax}x{ay}x{az} (volume {ax * ay * az})",
        f"bits_per_entry: {bits_per_entry(len(lit['palette']))}",
        "palette_counts:",
    ]
    for entry, count in zip(lit["palette"], lit["counts"]):
        lines.append(f"  - {palette_name(entry)}: {count}")
    meta = lit["total_blocks_meta"]
    lines.append(
        f"non_air_decoded: {non_air} / metadata TotalBlocks: "
        f"{meta if meta is not None else '<absent>'}"
    )
    if dest:
        lines.append(f"output: {dest}")
    return "\n".join(lines)


def convert(source_path, dest_path):
    """Read, decode, self-check, and (if dest_path) write. Returns (lit, ok)."""
    lit = load_litematic(Path(source_path).read_bytes())
    non_air = sum(
        c
        for entry, c in zip(lit["palette"], lit["counts"])
        if palette_name(entry) != "minecraft:air"
    )
    ok = lit["total_blocks_meta"] is None or non_air == lit["total_blocks_meta"]
    if ok and dest_path:
        Path(dest_path).parent.mkdir(parents=True, exist_ok=True)
        Path(dest_path).write_bytes(write_nbt(build_structure_nbt(lit)))
    return lit, ok


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="litematic_to_nbt.py",
        description=(
            "Convert a Litematica .litematic (v6, single region) into a "
            "vanilla structure template .nbt. Pure file transform; the "
            "output is a generated artifact and must not be committed."
        ),
    )
    parser.add_argument("source", help=".litematic input path")
    parser.add_argument(
        "dest",
        nargs="?",
        help=".nbt output path (omit with --info to only inspect)",
    )
    parser.add_argument(
        "--info",
        action="store_true",
        help="decode and print the summary without writing output",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    args = parser.parse_args(argv)

    if not args.info and not args.dest:
        parser.error("dest is required unless --info is given")

    try:
        lit, ok = convert(args.source, None if args.info else args.dest)
    except OSError as exc:
        print(f"error: cannot read/write: {exc}", file=sys.stderr)
        return 2
    except ContractError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(render_summary(lit, args.source, None if args.info else args.dest))
    if not ok:
        print(
            "error: decoded non-air count does not match metadata "
            "TotalBlocks — decode bug suspected, nothing written",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    # cp932: stdout is strict by default and one unencodable
    # character costs the whole run. Why `errors=` and not
    # `encoding=`: tools/test_console_encoding.py.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    sys.exit(main())
