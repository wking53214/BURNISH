# Validation

Evidence only. Items 32, 33 and 35 of the [remediation plan](REMEDIATION_PLAN_v2.md): Burnish run blind on public
repositories it was not built for, its output checked by a reviewer, and the results written here.

## 2026-11-26: five popular Python libraries

**What was run.** Burnish 0.5.3 on five repositories chosen by a rule written before any run: walk the PyPI top-downloads
list in order and take the first five whose GitHub repository has `README.md` and `pyproject.toml` at the root, at most
one per owner. The rule, every package looked at, and every output are in
[`docs/validation/2026-11-26/`](validation/2026-11-26/SELECTION.md).

| Repository | Commit | `critic` | `check` findings | `readme-critic` (minimum) |
|---|---|---|---|---|
| python/typing_extensions | `7cfb2ae` | PASS | 47 | fails 5 |
| kjd/idna | `d357725` | FAIL | 20 | fails 4 |
| urllib3/urllib3 | `3db5970` | FAIL | 276 | fails 4 |
| jawah/charset_normalizer | `0b45fe2` | PASS | 83 | fails 3 |
| psf/requests | `3c7baaa` | FAIL | 48 | fails 4 |

**Who reviewed it.** Claude (an AI model), on 2026-11-26, reading each README in full and the code behind a sample of the
`check` findings. **No person has reviewed these results yet.** Item 33 asks for a human reviewer, so it stays open; the
review below is a first pass for a person to confirm or overturn.

### The claims critic

The reviewer read every sentence of the five READMEs and listed each claim of a kind the critic says it checks (a test
count or "all tests pass", a pin, a "no dependencies" claim, and the five absolutes: fully verified, production ready,
battle tested, 100% coverage, no known bugs).

| Repository | Claims of a checked kind | Caught | Missed | Wrongly flagged | Brochure rule | Reviewer on the brochure rule |
|---|---|---|---|---|---|---|
| typing_extensions | 0 | 0 | 0 | 0 | not fired | agrees |
| idna | 0 | 0 | 0 | 0 | fired | disagrees: the README admits limits (old Pythons may reject new Unicode, emoji are not supported) |
| urllib3 | 1 | 0 | 1 | 0 | fired | agrees: promotional wording and no limits admitted |
| charset_normalizer | 0 | 0 | 0 | 0 | not fired | agrees: it has a Known limitations section |
| requests | 0 | 0 | 0 | 0 | fired | agrees: promotional wording and no limits admitted |

- **The one miss:** urllib3's README line 30, "100% test coverage." The critic matches "100% coverage" only with nothing
  between the words. Its CI enforces the figure (`.github/workflows/ci.yml` line 215, `--fail-under=100`), so the claim is
  probably true; the critic would have reported it as backed by nothing it reads, not as false. It is now planted as
  `tests/planted/hard-12-coverage-with-a-word-inside.txt`, recorded as a miss.
- **Every FAIL came from the brochure rule, not from a false claim.** The rule fails a README with a brochure word or a
  pip install line and no "does not" anywhere. It is Burnish's own house standard, so a FAIL on an outside repository
  means "does not admit its limits in Burnish's words", which a reader of the outcome would not guess.
- **The kinds of claim the critic checks are rare in these READMEs.** One in five. The checkable claim that did appear was
  Python version support (idna line 115, requests line 38, charset_normalizer lines 216 to 218), which the critic does not
  read; the reviewer checked all three against `requires-python` and all three agree. That is evidence for where item 9
  (more kinds of claims) should start.

**Follow-up (0.5.5).** On the owner's choice the brochure rule no longer decides the outcome: it is a style note, and
the README critic's RM-LIMITS judges the same thing. The critic was run again on the same five, at the same commits: all
five end PASS. The outputs are beside the first ones, as `<repository>.critic-0.5.5.txt`. urllib3's PASS still rests on
the missed "100% test coverage" above.

**Follow-up (0.5.6).** The three wrong patterns this run found were fixed: `@overload` stubs no longer need a
docstring, a CapWords function that a class-named decorator turns into an object keeps its name, and "100% test coverage"
is read. Run again on the same five at the same commits (`<repository>.check-0.5.6.txt`, `<repository>.critic-0.5.6.txt`):
474 `check` findings became 441 (typing_extensions 47 to 34, urllib3 276 to 268, requests 48 to 36, the other two
unchanged), and urllib3 now ends INCOMPLETE, because its "100% test coverage" is read and nothing the critic reads backs
it. The other four end PASS. Four PY-NAME findings in typing_extensions remain (`NamedTuple`, `IntVar`, `deprecated`,
`sentinel`).

### `burnish check`

474 findings in all. The reviewer drew a seeded random sample of 20, four per repository, and read the code at each one
(each finding and its verdict: [`CHECK_SAMPLE.md`](validation/2026-11-26/CHECK_SAMPLE.md)):

| Verdict | Count | Examples |
|---|---|---|
| Correct: the rule applies and is worth fixing | 7 | module with no docstring (idna `codec.py`, urllib3 `util/ssl_.py`), public method with no docstring (requests `models.py` `copy`) |
| Correct but low value: the rule applies, a maintainer would reasonably leave it | 7 | overrides of a documented standard-library method (idna `setstate`), test and build sessions in `noxfile.py`, best-effort cleanup that ignores errors on close |
| Wrong in context | 6 | `@overload` type stubs reported as public functions with no docstring (requests, three), public names that must match the `typing` module (`TypedDict`, `Concatenate`, `ReadOnly`) reported as not lower case |

The two wrong patterns were then counted across all 474: **20** PY-DOC findings are on `@overload` stubs (12 of the 23
public-function findings in requests, 8 in urllib3), and all **17** PY-NAME findings in typing_extensions are names that
mirror the standard `typing` module. The stubs are a defect in the check (a stub carries no docstring by convention); the
names are a rule meeting a library whose public names are fixed by another standard.

### `burnish readme-critic`

All five fail the minimum tier. These are judgments against Burnish's README standard, not claims of fact, so they were
not scored. Two misreadings stood out: urllib3 and charset_normalizer open with an HTML `<h1>` title, which the rule does
not see, so both fail "opens with a title" and "one plain sentence under the title"; and charset_normalizer's usage
examples sit in sub-sections, so it fails "usage has a code block".

## What this does not show

- Anything about repositories with test counts, pins or "no dependencies" claims in their README: none of these five had
  them, so the parts of the critic built for those were not exercised.
- Whether a person agrees with the review. Until one does, every verdict above is one AI reviewer's reading.
- How Burnish does on applications, data projects or anything that is not a widely used library. The rule picks the most
  downloaded packages, which are small, mature libraries.
