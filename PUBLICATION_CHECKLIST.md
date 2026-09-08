# Publication checklist

Run before the repository is made public. Every command below is run from the repository
root. `--exclude-dir=.git` and `--binary-files=without-match` are used throughout, so PNG
byte coincidences do not count as hits.

Last run: 2026-09-08, re-run after the terminology change described in section 6.
240 tracked files. Commit hashes are not cited here: every hash in this repository changed
once, when the commit author was corrected before publication.

## 1. Scans

The patterns are written with a one-character bracket (`pas[i]s`, `\xab`) so that this
file does not itself contain the literal strings it forbids. The regexes still match them.

| what | pattern | hits | required |
|---|---|---|---|
| quotation marks around a person's words | `\xab` / `\xbb` (guillemets) | **0** | 0 |
| verbatim-quotation marker | `逐[語]` | **0** | 0 |
| private development repository name | `mc-ai[a]gent` | **0** | 0 |
| operator's account name | `pas[i]s` | **0** | 0 |
| e-mail addresses | `[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}` | **0** | 0 |
| absolute Windows paths | `[a-z]:[\\/]users` | **0** | 0 |
| session identifiers, full form | RFC-4122 UUID | **0** | 0 |
| API keys | `api[_-]?key` | **0** | 0 |
| private key material | `BEGIN [A-Z ]*PRIVATE` | **0** | 0 |
| secrets | `\bsecret\b` | **0** | 0 |
| Discord material | `dis[c]ord` | **0** | 0 |
| X / Twitter material | `x\.com`, `twit[t]er` | **2** | 2 — the operator's own public handle, linked once in each README's Credits (deliberate; section 6) |
| operator's save path | `saves/[c]pu` | **0** | 0 |
| withheld reference-circuit directory | `notes/[b]ench` | **0** | 0 |
| decompiled game source (imports) | `import\s+net\.mine[c]raft` | **0** | 0 |
| decompiled game source (class bodies) | `public\s+class\s+\w*Blo[c]k` | **0** | 0 |

The counts above are for the export excluding this file's own English labels: the words
"Discord" and "Twitter" appear here three times as the *names* of the categories being
excluded, and nowhere else in the repository.

These are pattern scans. They bound what a regular expression can find; they do not prove
the absence of a quoted utterance or a game-code fragment that happens to avoid every
pattern. The four documents a reader meets first — both READMEs, this checklist and
`docs/report-alu-stage.md` — were additionally read in full with that question by the author
and by a second reviewer (Astra, section 7). Every other file was scanned only.

Three further patterns return hits that are **not** findings and were reviewed line by
line:

- `\btoken\b` — 14 hits, all LLM token counts in cost tables. No credentials.
- `password` — 9 hits, all the *name* of an RCON command-line flag (`--password`) or of a
  file the reader must create themselves (`rcon-password.txt`). No values.

A pattern table only finds what its patterns describe. Section 6 lists the internal
references these patterns cannot match, which are present and are kept on purpose.

Reproduce:

```
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
  referenced as a fact (the Bench was calibrated on it; no design agent was shown it) but no
  content from it is here. This is why three unit tests skip.
- The Java mod that exposes the in-game placement commands. Not needed to reproduce
  anything in this repository.
- Operations material: the private repository's state files, logs, session records, and
  handover documents beyond the one placement handover that carries the interference rules.
- Every quoted utterance of the operator, Astra, or anyone else (names are credited; utterances are not quoted).
  Decisions that were originally recorded as quotations are stated as facts instead
  ("the operator ruled that …").
- All Discord, X, and screenshot material.

## 3. What was rewritten rather than removed

- Absolute host paths → `<host-path>`; the host user name → `<user>`; session identifiers →
  `<session-id>`; the private repository name → `<dev-repo>` or a descriptive phrase.
  This applies inside `artifacts/world/*.json` too: those files' **run metadata** is
  redacted, while every measured block state, level and comparison in them is untouched.
  The same redaction was applied to `artifacts/world/world4*.json` on 2026-09-08 (host paths
  and the session id in the run metadata; escaped backslashes normalised to `/` in those
  strings; the files still parse as JSON).
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
python tools/checks/alu_check_slices.py artifacts/layouts/alu_slice_v9.json 3  # n=3 PASS 512/512
python tools/checks/alu_check_contract.py artifacts/layouts/alu_slice_v9.json  # CONTRACT PASS: 0 FAIL, 3 notes
cd tools/llmgen && python -m unittest test_capcell test_strength               # OK (skipped=3)
```

All six produced the expected result on the commit this checklist describes. The printed
lines are pasted verbatim in `README.md` section 5.

## 5. Hygiene

- Line endings: LF everywhere (0 of the 112 text files contain CRLF; the 7 PNGs are binary).
- No `__pycache__`, no `.pyc`, no build output committed.
- 240 files, 22,750,584 bytes (22.8 MB) tracked.
- Verified from a clean `git clone` of this repository, not from the working tree:
  all six commands in section 4 produce the results quoted above.
- Not yet published as of this checklist: the repository is local and has no remote. The
  operator's stated plan is a **private** GitHub repository first, so that the rendering can
  be checked before anyone else reads it. Making it public is a separate act by the operator.


## 6. Internal references deliberately kept

A second scan on 2026-09-08 looked for internal references that the pattern table in
section 1 cannot match. They are present and are kept. None is a credential, a personal
detail, or a real address.

| what | example | where | why it stays |
|---|---|---|---|
| development session short ids | `0c3d10be`, `f9d66fa1`, `3ef098ad` | 11 files, in document titles | they say which run wrote which document — the thing section 4 of the README makes claims about |
| internal role names | `DIRECTOR 7`, `DIRECTOR 8`, `CONDUCTOR 6` | document titles | same |
| the placement command of an unpublished mod | `/aiwb place <program> <x> <y> <z>` | 9 files | `tools/llmgen/cell_to_program.py` exists to emit those lines; deleting them would delete the tool's output format. The mod itself is not distributed |
| the operator's public X handle | `@pashina_2` | both READMEs, Credits | the operator's chosen public identity for this work (the same name the license carries). It makes the GitHub account ↔ X account correspondence explicit; removing the two links is one edit if the operator prefers not to |
| coordinates in the operator's single-player save | `6005 133 -4113`, `6001 131 -4114` | 5 files | they are the placement origin the records were taken at, in a world no one else can reach |
| paths in the private development repository | `tools/workbench/…`, `data/workbench/…`, `notes/…` | documents and tool docstrings | they record where a rule came from. They do not resolve here — section 3 already says this of `notes/…` |
| internal decision ids | `ADR-…`, `OC-…`, `PROV-…`, `GAP-7`, `M9`, `M12`, `M15` | mostly tool docstrings | same |

The section 1 row "session identifiers, full form" covers the RFC-4122 form only. The
8-hex short ids above are session identifiers too and were never removed. That row is not
a claim that every session identifier is gone; before this section existed it could be
read as one.

Two things were changed rather than kept:

- The report pair `docs/report-alu-stage.md` / `.ja.md` addressed the operator in the
  second person ("your world", "Your acts"). It now names the operator in the third
  person, because the reader of a public document is not the person being addressed.
- One term was normalised across every file: one model instance working from a written
  order is called an **agent**.

## Amendment (2026-09-08, operator ruling)

Other-company model agents are credited by name and role. Astra (second-model reviewer, GPT-6, OpenAI) is named in the credits and wherever its review shaped the work. The earlier scan that required 0 hits of the name is withdrawn.

## 7. Second reviewer's reading (2026-09-08)

Astra (second model, reviewer) read the four key documents with the single question of
whether anything unfit for publication remained. Findings and what was done:

| finding | disposition |
|---|---|
| section 5 said the repository was already on private GitHub; it was local with no remote | corrected (section 5) |
| section 1 reported 0 X URLs while both Credits link `@pashina_2` | row corrected to 2, kept deliberately (section 6) |
| `v7` was called an "ALU slice" in both READMEs' result tables and headings and in the report, while README section 3 says it is not a slice (20/32 under the slice checker) | `v7` is now "ALU stage" everywhere; the slice `v8` has its own row in the result table |
| `untouched` for `artifacts/world/*.json` contradicted section 3 (run metadata redacted) | wording now says: measured values unchanged, run metadata redacted |
| the scan table reads as a guarantee stronger than pattern scans can give | stated explicitly (section 1); full readings cover the four key documents only |
| the Credits line for Astra | no objection |

Fourth round (same day, FEED-1): the world stage became a tool (`tools/world/feed.py`); its outputs for the runs cited in the README are in `artifacts/world/feed1/` with the same run-metadata redaction as `world4*.json`; the reviewer's pitch-14 slice is included as `artifacts/layouts/reviewer_slice_p14_relocated.json` with credit; the p4 "latch" was traced to a 56-gt decay and is reported in README section 6.

Third round (same day, WORLD-4): the second reviewer asked for the placer's five solutions to be replayed in a world; one latched (`p4_throughline`, T = 0) where the Bench and the judge had passed it. Disposition: `tools/llmgen/capcell.py` now treats pins as floors and solves from two seeds (`dc_solve_both`), the checkers use it, PLACER-0 and WORLD-4 are added to the export (`tools/placer0/`, `artifacts/placer0/`, `docs/world/world4-*`), and the failure is reported in README section 6.

Second reading, of the slice checker (same day): the function-table checker does not measure the contract, and `v8` violates clause 2 (through-line exit not restored to 15). Disposition: `tools/checks/alu_check_contract.py` added, `v9` replaces `v8` in the results, the contract amendment is recorded in `docs/placement/slice-contract.md`, and the README no longer says `v8` meets the contract.

