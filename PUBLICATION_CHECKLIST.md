# Publication checklist

Run before the repository is made public. Every command below is run from the repository
root. `--exclude-dir=.git` and `--binary-files=without-match` are used throughout, so PNG
byte coincidences do not count as hits.

Last run: 2026-09-08, against the tree committed as the initial commit.

## 1. Scans

The patterns are written with a one-character bracket (`pas[i]s`, `\xab`) so that this
file does not itself contain the literal strings it forbids. The regexes still match them.

| what | pattern | hits | required |
|---|---|---|---|
| quotation marks around a person's words | `\xab` / `\xbb` (guillemets) | **0** | 0 |
| verbatim-quotation marker | `逐[語]` | **0** | 0 |
| second-model reviewer's name | `A[s]tra` (case-insensitive) | **0** | 0 |
| private development repository name | `mc-ai[a]gent` | **0** | 0 |
| operator's account name | `pas[i]s` | **0** | 0 |
| e-mail addresses | `[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}` | **0** | 0 |
| absolute Windows paths | `[a-z]:[\\/]users` | **0** | 0 |
| session identifiers | RFC-4122 UUID | **0** | 0 |
| API keys | `api[_-]?key` | **0** | 0 |
| private key material | `BEGIN [A-Z ]*PRIVATE` | **0** | 0 |
| secrets | `\bsecret\b` | **0** | 0 |
| Discord material | `dis[c]ord` | **0** | 0 |
| X / Twitter material | `x\.com`, `twit[t]er` | **0** | 0 |
| operator's save path | `saves/[c]pu` | **0** | 0 |
| withheld reference-circuit directory | `notes/[b]ench` | **0** | 0 |

The counts above are for the export excluding this file's own English labels: the words
"Discord" and "Twitter" appear here three times as the *names* of the categories being
excluded, and nowhere else in the repository.

Three further patterns return hits that are **not** findings and were reviewed line by
line:

- `\btoken\b` — 14 hits, all LLM token counts in cost tables. No credentials.
- `password` — 9 hits, all the *name* of an RCON command-line flag (`--password`) or of a
  file the reader must create themselves (`rcon-password.txt`). No values.

Reproduce:

```
for p in $'\xc2\xab|\xc2\xbb' '逐[語]' 'A[s]tra' 'mc-ai[a]gent' 'pas[i]s' \
         '[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}' '[a-z]:[\\/]users' \
         '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}' \
         'api[_-]?key' 'BEGIN [A-Z ]*PRIVATE' '\bsecret\b' \
         'dis[c]ord' 'x\.com|twit[t]er' 'saves/[c]pu' 'notes/[b]ench'; do
  printf '%-60s %s\n' "$p" \
    "$(grep -rniE "$p" . --binary-files=without-match --exclude-dir=.git | wc -l)"
done
```

## 2. What was deliberately excluded

- The operator's Minecraft world and every save file. Nothing under `saves/` was read or
  copied for this export.
- The pre-existing reference circuit used to calibrate the Bench, and its records. It is
  referenced as a fact (the Bench was calibrated on it; no design seat was shown it) but no
  content from it is here. This is why three unit tests skip.
- The Java mod that exposes the in-game placement commands. Not needed to reproduce
  anything in this repository.
- Operations material: the private repository's state files, logs, session records, and
  handover documents beyond the one placement handover that carries the interference rules.
- Every quoted utterance of the operator, the second-model reviewer, or anyone else.
  Decisions that were originally recorded as quotations are stated as facts instead
  ("the operator ruled that …").
- All Discord, X, and screenshot material.

## 3. What was rewritten rather than removed

- Absolute host paths → `<host-path>`; the host user name → `<user>`; session identifiers →
  `<session-id>`; the private repository name → `<dev-repo>` or a descriptive phrase.
  This applies inside `artifacts/world/*.json` too: those files' **run metadata** is
  redacted, while every measured block state, level and comparison in them is untouched.
- File references were remapped from the development repository's `notes/…` layout to this
  repository's layout. Provenance citations in `tools/llmgen/` docstrings still name
  `notes/…` paths; those are pointers into the private repository and do not resolve here.
  They were kept because they record where a rule came from.
- `sys.path` lines in every copied tool now resolve relative to the file, so the export runs
  from its own root with no configuration.

## 4. Verification re-run before publishing

```
python tools/checks/alu_check2.py       artifacts/layouts/alu_stage_v7.json    # PASS 32/32
python tools/checks/bench_sweep.py      artifacts/layouts/layout_place1.json   # ALL PASS
python tools/checks/alu_check_slices.py artifacts/layouts/v7_as_slice.json 1   # n=1 PASS 20/32
cd tools/llmgen && python -m unittest test_capcell test_strength               # OK (skipped=3)
```

All four produced the expected result on the commit this checklist describes. The printed
lines are pasted verbatim in `README.md` section 5.

## 5. Hygiene

- Line endings: LF everywhere (0 files contain CRLF).
- No `__pycache__`, no `.pyc`, no build output committed.
- 103 files, 2.3 MB total.
- No git remote is configured. Publishing is the operator's act.
