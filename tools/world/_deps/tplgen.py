#!/usr/bin/env python3
"""M8 E2 amplifier-template generator v0 (ADR-0036).

Given a list of 3-bit patterns ("b2 b1 b0" strings), emit the author-ruled
amplifier-template row for each pattern: a placements TSV and a vanilla
structure-template `.nbt`. v0 target: the 8-pattern fixture reproduction
(patterns 000..111 in fixture order).

Normative source (authority order; nothing invented beyond it):
- notes/m8-e2-tplgen-task-spec.md sections 2-4 (layout conventions, the
  section-3 template-table DATA, the CLI contract).
- tools/m2-bridge/litematic_to_nbt.py, reused READ-ONLY (never modified):
  `write_nbt` serializes the structure NBT; the local build_structure_nbt
  below mirrors the shape of the bridge's own build_structure_nbt (size /
  entities / blocks / palette / DataVersion), the same pattern
  tools/m5-romgen/romgen.py uses for its own placements (that module also
  cannot reuse the bridge's build_structure_nbt directly, since that
  function decodes a *.litematic-shaped* `lit` dict, not an arbitrary
  placement map).
- The `--program` bitstream lexical rules mirror (not import)
  tools/m5-romgen/romgen.py's romcheck.parse_program_text tolerances:
  `#`/`//` line comments, `_`/whitespace ignored, only `0`/`1` meaningful.

Python stdlib only. Exit codes: 0 = success; 2 = usage / contract error (no
partial output on a contract error).
"""

import argparse
import hashlib
import importlib.util
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent.parent

DEFAULT_DATA_VERSION = 3839  # smoke1 / fixture Minecraft 1.20.6, per task spec.
ROW_STRIDE = 2  # D=2 toward -Z (task spec section 2).

_TSV_HEADER = ["x", "y", "z", "block", "state-props"]


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Reused READ-ONLY (task spec section 4 / PROV-7): the NBT serializer is the
# consumer contract; import it rather than fork it.
bridge = _load_module(
    "m8_tplgen_m2_bridge", Path(__file__).resolve().parent / "litematic_to_nbt.py")


class ContractError(Exception):
    """Input violates the v0 tplgen contract (exit 2, no output written)."""


# ---------------------------------------------------------------------------
# Block-state helpers (task spec section 3 macros: pr[...], glass, obs).
# ---------------------------------------------------------------------------

_RAIL = "minecraft:powered_rail"
_GLASS = "minecraft:white_stained_glass"
_OBSERVER = "minecraft:observer"


def _rail(x, y, shape):
    return (x, y, _RAIL, {"powered": "true", "shape": shape, "waterlogged": "false"})


def _glass(x, y):
    return (x, y, _GLASS, {})


def _obs(x, y):
    return (x, y, _OBSERVER, {"facing": "east", "powered": "false"})


# ---------------------------------------------------------------------------
# Template table (task spec section 3): NORMATIVE DATA, transcribed
# literally per pattern (13 blocks each = the 2-block common prefix + the
# 11 pattern-specific blocks listed in the spec). Positions are hardcoded
# per pattern, not derived from the bit values.
# ---------------------------------------------------------------------------

_COMMON_PREFIX = [_glass(1, 3), _rail(1, 4, "east_west")]

TEMPLATE_BLOCKS = {
    "000": _COMMON_PREFIX + [
        _glass(2, 3), _rail(2, 4, "east_west"),
        _glass(3, 2), _rail(3, 3, "ascending_west"), _obs(3, 4),
        _glass(4, 3), _rail(4, 4, "east_west"),
        _glass(5, 3), _rail(5, 4, "east_west"),
        _glass(6, 3), _rail(6, 4, "east_west"),
    ],
    "001": _COMMON_PREFIX + [
        _glass(2, 2), _rail(2, 3, "ascending_west"), _obs(2, 4),
        _glass(3, 3), _rail(3, 4, "east_west"),
        _glass(4, 3), _rail(4, 4, "east_west"),
        _glass(5, 3), _rail(5, 4, "east_west"),
        _glass(6, 3), _rail(6, 4, "east_west"),
    ],
    "010": _COMMON_PREFIX + [
        _glass(2, 3), _rail(2, 4, "east_west"),
        _glass(3, 3), _rail(3, 4, "east_west"),
        _glass(4, 2), _rail(4, 3, "ascending_west"), _obs(4, 4),
        _glass(5, 3), _rail(5, 4, "east_west"),
        _glass(6, 3), _rail(6, 4, "east_west"),
    ],
    "011": _COMMON_PREFIX + [
        _glass(2, 2), _rail(2, 3, "ascending_west"), _obs(2, 4),
        _glass(3, 3), _rail(3, 4, "east_west"),
        _glass(4, 2), _rail(4, 3, "ascending_west"),
        _glass(5, 3), _rail(5, 4, "east_west"),
        _glass(6, 3), _rail(6, 4, "east_west"),
    ],
    "100": _COMMON_PREFIX + [
        _glass(2, 3), _rail(2, 4, "east_west"),
        _glass(3, 2), _rail(3, 3, "ascending_west"), _obs(3, 4),
        _glass(4, 3), _rail(4, 4, "east_west"),
        _glass(5, 3), _rail(5, 4, "east_west"),
        _glass(6, 2), _rail(6, 3, "ascending_west"),
    ],
    "101": _COMMON_PREFIX + [
        _glass(2, 2), _rail(2, 3, "ascending_west"), _obs(2, 4),
        _glass(3, 3), _rail(3, 4, "east_west"),
        _glass(4, 3), _rail(4, 4, "east_west"),
        _glass(5, 3), _rail(5, 4, "east_west"),
        _glass(6, 2), _rail(6, 3, "ascending_west"),
    ],
    "110": _COMMON_PREFIX + [
        _glass(2, 3), _rail(2, 4, "east_west"),
        _glass(3, 3), _rail(3, 4, "east_west"),
        _glass(4, 2), _rail(4, 3, "ascending_west"), _obs(4, 4),
        _glass(5, 3), _rail(5, 4, "east_west"),
        _glass(6, 2), _rail(6, 3, "ascending_west"),
    ],
    "111": _COMMON_PREFIX + [
        _glass(2, 2), _rail(2, 3, "ascending_west"), _obs(2, 4),
        _glass(3, 3), _rail(3, 4, "east_west"),
        _glass(4, 2), _rail(4, 3, "ascending_west"),
        _glass(5, 2), _rail(5, 3, "east_west"),
        _glass(6, 2), _rail(6, 3, "ascending_east"),
    ],
}

for _pattern, _blocks in TEMPLATE_BLOCKS.items():
    if len(_blocks) != 13:
        raise AssertionError(
            f"TEMPLATE_BLOCKS[{_pattern!r}] has {len(_blocks)} blocks, "
            "expected 13 (transcription bug)")


def state_str(block, props):
    if not props:
        return block
    return block + "[" + ",".join(f"{k}={v}" for k, v in sorted(props.items())) + "]"


def _fmt_props(props):
    if not props:
        return ""
    return "[" + ",".join(f"{k}={v}" for k, v in sorted(props.items())) + "]"


# ---------------------------------------------------------------------------
# Pattern parsing (task spec section 4).
# ---------------------------------------------------------------------------


def validate_pattern(pattern):
    if len(pattern) != 3 or any(ch not in "01" for ch in pattern):
        raise ContractError(
            f"invalid pattern {pattern!r}: must match [01]{{3}}")


def parse_patterns_arg(raw):
    """Comma-separated 3-char binary strings -> validated list."""
    parts = raw.split(",")
    if not parts or any(p == "" for p in parts):
        raise ContractError("--patterns: empty pattern in list")
    for p in parts:
        validate_pattern(p)
    return parts


def parse_program_text(text):
    """Program bitstream text -> list of '0'/'1' chars.

    Mirrors (does not import) romgen's program-parser lexical tolerance:
    `#` and `//` start a line comment; `_` and whitespace are ignored
    separators; any other character is a fail-loud contract error.
    """
    bits = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for marker in ("#", "//"):
            idx = line.find(marker)
            if idx != -1:
                line = line[:idx]
        for col, ch in enumerate(line, start=1):
            if ch in "01":
                bits.append(ch)
            elif ch == "_" or ch.isspace():
                continue
            else:
                raise ContractError(
                    f"program: invalid character {ch!r} at line {lineno} "
                    f"col {col}")
    if not bits:
        raise ContractError("program: no bits found")
    return bits


def bits_to_patterns(bits):
    """Consecutive 3-char groups in file order -> pattern labels (task 4)."""
    if len(bits) % 3 != 0:
        raise ContractError(
            f"program: bit count {len(bits)} is not a multiple of 3")
    return ["".join(bits[i:i + 3]) for i in range(0, len(bits), 3)]


def parse_program_file(path):
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise ContractError(f"cannot read program file: {exc}") from exc
    return bits_to_patterns(parse_program_text(text))


# ---------------------------------------------------------------------------
# Row / placement assembly (task spec section 2).
# ---------------------------------------------------------------------------


def build_row_placements(pattern, row_index):
    """One row's placements at z = -(1 + ROW_STRIDE*row_index)."""
    if pattern not in TEMPLATE_BLOCKS:
        raise ContractError(
            f"row {row_index}: pattern {pattern!r} not in template table "
            f"(known: {sorted(TEMPLATE_BLOCKS)})")
    z = -(1 + ROW_STRIDE * row_index)
    return {(x, y, z): (block, props)
            for x, y, block, props in TEMPLATE_BLOCKS[pattern]}


def build_placements(patterns):
    if not patterns:
        raise ContractError("no patterns given")
    placements = {}
    for row_index, pattern in enumerate(patterns):
        row = build_row_placements(pattern, row_index)
        for coord, value in row.items():
            if coord in placements:
                raise ContractError(f"row {row_index}: coordinate collision "
                                     f"at {coord} (unexpected row overlap)")
            placements[coord] = value
    return placements


# ---------------------------------------------------------------------------
# Output serialization.
# ---------------------------------------------------------------------------


def render_placements_tsv(placements):
    """x/y/z/block/state-props TSV, ordered z descending, x asc, y asc.

    `block` is the bare block id (e.g. minecraft:powered_rail);
    `state-props` is the bracketed sorted key=value property string (e.g.
    [powered=true,shape=east_west,waterlogged=false]), or empty for a
    block with no properties (e.g. white_stained_glass).
    """
    lines = ["\t".join(_TSV_HEADER)]
    for coord in sorted(placements, key=lambda c: (-c[2], c[0], c[1])):
        block, props = placements[coord]
        lines.append(
            f"{coord[0]}\t{coord[1]}\t{coord[2]}\t{block}\t{_fmt_props(props)}")
    return "\n".join(lines) + "\n"


def build_structure_nbt(placements, data_version):
    """Vanilla structure NBT: local coords = world - min corner.

    Mirrors the shape of tools/m2-bridge/litematic_to_nbt.py's own
    build_structure_nbt (size/entities/blocks/palette/DataVersion), using
    the bridge's write_nbt + TAG_* constants -- the same reuse pattern
    tools/m5-romgen/romgen.py applies for its own placement map (the
    bridge's build_structure_nbt itself decodes a *.litematic-shaped* `lit`
    dict, not an arbitrary placement map, so it cannot be called directly).
    """
    coords = sorted(placements)
    min_x = min(c[0] for c in coords)
    min_y = min(c[1] for c in coords)
    min_z = min(c[2] for c in coords)
    palette = []
    palette_index = {}
    blocks = []
    max_l = [0, 0, 0]
    for coord in coords:
        block, props = placements[coord]
        key = (block, tuple(sorted(props.items())))
        if key not in palette_index:
            palette_index[key] = len(palette)
            entry = {"Name": (bridge.TAG_STRING, block)}
            if props:
                entry["Properties"] = (
                    bridge.TAG_COMPOUND,
                    {k: (bridge.TAG_STRING, v) for k, v in props.items()},
                )
            palette.append(entry)
        lx, ly, lz = coord[0] - min_x, coord[1] - min_y, coord[2] - min_z
        max_l = [max(max_l[0], lx), max(max_l[1], ly), max(max_l[2], lz)]
        blocks.append({
            "pos": (bridge.TAG_LIST, (bridge.TAG_INT, [lx, ly, lz])),
            "state": (bridge.TAG_INT, palette_index[key]),
        })
    root = {
        "size": (bridge.TAG_LIST,
                 (bridge.TAG_INT, [max_l[0] + 1, max_l[1] + 1, max_l[2] + 1])),
        "entities": (bridge.TAG_LIST, (bridge.TAG_END, [])),
        "blocks": (bridge.TAG_LIST, (bridge.TAG_COMPOUND, blocks)),
        "palette": (bridge.TAG_LIST, (bridge.TAG_COMPOUND, palette)),
        "DataVersion": (bridge.TAG_INT, data_version),
    }
    return bridge.write_nbt(root)


def generate(patterns, data_version=DEFAULT_DATA_VERSION):
    """Pure in-memory generation. Returns (tsv_text, nbt_bytes)."""
    for pattern in patterns:
        validate_pattern(pattern)
    placements = build_placements(patterns)
    tsv = render_placements_tsv(placements)
    nbt = build_structure_nbt(placements, data_version)
    return tsv, nbt


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="tplgen.py",
        description=(
            "M8 E2 amplifier-template generator: emit placements.tsv and "
            ".nbt for a list of 3-bit patterns (ADR-0036)."))
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser(
        "generate",
        help="generate <name>_placements.tsv and <name>.nbt")
    gen.add_argument(
        "--patterns", default=None,
        help="comma-separated 3-char binary pattern strings (b2b1b0)")
    gen.add_argument(
        "--program", default=None,
        help="program bitstream text file (0/1 chars, grouped by 3)")
    gen.add_argument("--name", required=True, help="artifact base name")
    gen.add_argument("--out-dir", required=True, help="output directory")
    gen.add_argument("--data-version", type=int, default=DEFAULT_DATA_VERSION,
                      help=f"structure NBT DataVersion (default "
                           f"{DEFAULT_DATA_VERSION})")
    args = parser.parse_args(argv)

    has_patterns = args.patterns is not None
    has_program = args.program is not None
    if has_patterns == has_program:
        print("error: exactly one of --patterns or --program is required",
              file=sys.stderr)
        return 2

    try:
        if has_patterns:
            patterns = parse_patterns_arg(args.patterns)
        else:
            patterns = parse_program_file(args.program)
        tsv, nbt = generate(patterns, args.data_version)
    except ContractError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    tsv_path = out_dir / f"{args.name}_placements.tsv"
    nbt_path = out_dir / f"{args.name}.nbt"
    tsv_path.write_text(tsv, encoding="utf-8", newline="")
    nbt_path.write_bytes(nbt)

    print(f"name: {args.name}")
    print(f"patterns: {','.join(patterns)}")
    print(f"out-dir: {out_dir}")
    for label, path in (("placements", tsv_path), ("artifact", nbt_path)):
        print(f"{label}: {path}")
        print(f"  sha256: {_sha256(path)}")

    return 0


if __name__ == "__main__":
    # cp932: stdout is strict by default and one unencodable
    # character costs the whole run. Why `errors=` and not
    # `encoding=`: tools/test_console_encoding.py.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    sys.exit(main())
