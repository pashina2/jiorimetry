#!/usr/bin/env python3
"""Check the evidence citations of docs/facts.md and docs/failures.md (and their mirrors).

Every data row of the tables in those files carries one evidence cell of the form

    `<path>` - `<literal>` [- `<literal>` ...]

where <path> is a file in this repository and each <literal> is a string that must occur
verbatim in that file. This script verifies both, prints one line per row, and exits 0
only when nothing is MISSING.

    python tools/check_tables.py            # from the repository root

Rows whose evidence cell has no literal are checked for the path only. Cells that carry no
backticked path at all are reported as MISSING, so a row cannot exist without a file.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TABLES = [
    "docs/facts.md",
    "docs/facts.ja.md",
    "docs/failures.md",
    "docs/failures.ja.md",
]
CODE = re.compile(r"`([^`]+)`")
PATHLIKE = re.compile(r"^[A-Za-z0-9_.\-/]+\.(md|json|txt|py|png)$")

_cache = {}


def read(path):
    if path not in _cache:
        _cache[path] = (ROOT / path).read_bytes().decode("utf-8", "replace")
    return _cache[path]


def rows(text):
    """Yield (row_number, cells) for every data row of every markdown table."""
    n = 0
    header = None
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            header = None
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if header is None:
            header = [c.lower() for c in cells]
            continue
        if all(set(c) <= set("-: ") for c in cells):
            continue
        n += 1
        yield n, header, cells


def evidence_cell(header, cells):
    for i, h in enumerate(header):
        if "evidence" in h and i < len(cells):
            return cells[i]
    return None


def check_file(rel):
    path = ROOT / rel
    if not path.exists():
        print("MISSING %s: file not found" % rel)
        return 0, 1
    ok = miss = 0
    for n, header, cells in rows(read(rel)):
        cell = evidence_cell(header, cells)
        if cell is None:
            continue
        tokens = CODE.findall(cell)
        paths = [t for t in tokens if PATHLIKE.match(t)]
        if not paths:
            print("MISSING %s row %d: no evidence file cited" % (rel, n))
            miss += 1
            continue
        target = paths[0]
        literals = [t for t in tokens[tokens.index(target) + 1:] if not PATHLIKE.match(t)]
        if not (ROOT / target).exists():
            print("MISSING %s row %d: %s does not exist" % (rel, n, target))
            miss += 1
            continue
        body = read(target)
        bad = [t for t in literals if t not in body]
        if bad:
            print("MISSING %s row %d: %s does not contain %s" % (rel, n, target, bad))
            miss += 1
            continue
        print("OK      %s row %d: %s%s" % (
            rel, n, target,
            "" if not literals else " (%d literal%s)" % (len(literals), "" if len(literals) == 1 else "s")))
        ok += 1
    return ok, miss


def main():
    ok = miss = 0
    for rel in TABLES:
        a, b = check_file(rel)
        ok += a
        miss += b
    print("%d OK, %d MISSING" % (ok, miss))
    return 0 if miss == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
