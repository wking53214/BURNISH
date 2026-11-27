# BURNISH Remediation Plan v2

**As of:** Nov 27, 2026, BURNISH 0.5.11.
**Replaces:** v1 (a draft of Nov 26, 2026, written at 0.4.0 and never saved), which replaced the outside 45-item "9.0+"
plan that was checked against the code on Nov 25, 2026.

## Key
✅ Done · 🟢 Already met the plan's own test · 🔵 Next · 🟡 Open · ⚪ Deferred or not planned · 🔴 Critical for 9.0

## What changed since the original plan
- **The original plan's facts held up.** 663 passing tests, the failed Clang build, only three tests that go through the
  real Warden, and the CNS analyzer recommending an adapter on a mere mention were all confirmed in the code.
- **The original plan missed one big thing:** BURNISH was released from the circuit on Oct 29, 2026. The finisher (the
  part that proposes edits through Warden) is no longer in active use, so hardening the Warden boundary is worth much
  less. The standalone checkers (`check`, `critic`, `readme-critic`) are what still matter.
- **Several items it called "silent" were not.** They were already documented, already tested, and already reported when
  BURNISH runs.

## Campaign A: Correctness (complete)

| # | Item | Status | Notes |
|---|---|---|---|
| 1 | Imports inside functions counted as optional | ✅ 0.3.29 | Owner's choice: the strict rule. Unlisted packages make the claim "not confirmed" |
| 2 | Test counts written as words | 🟢 | Wordy counts are missed but never misread as a smaller number. Reading more forms is a nice-to-have |
| 3 | One shared file walk | ✅ 0.3.28 | `check` reads the same files as everything else |
| 4 | Broken `pyproject.toml` | ✅ 0.3.28 | Claims against it are "unchecked" and the problem is named |
| 5 | Files with a BOM | 🟢 | Left alone, with a note saying so |
| 6 | Unclosed code fence in a README | 🟢 | Left alone, and tested |
| 7 | Stale facts in a README written from scratch | ✅ 0.4.3 | The compiled README states no version or module count, and is held to the sibling patterns |
| 8 | README.rst and other non-Markdown formats | 🟢 | Documented limitation, and the notes say so at runtime |
| 46 | A pin change with no changelog entry | ✅ 0.4.4 | A release test requires every git pin's ref to be named in the CHANGELOG |
| 47 | Pin or dependency claims with no `pyproject.toml` | ✅ 0.4.4 | Reported as "unchecked"; the critic ends INCOMPLETE |
| 48 | **New:** broken `pyproject.toml` and no claims ended PASS | ✅ 0.4.2 | Found while testing item 10. Owner's choice: INCOMPLETE, not FAIL |

## Campaign B: The evidence engine

| # | Item | Status | Notes |
|---|---|---|---|
| 9 | Recognize more kinds of claims (OS, security, performance, coverage...) | 🟡 | Large. Build it on top of 13 |
| 10 | Every finding says what evidence it used | ✅ 0.4.1 | Six lines under every finding in the printed report (owner's choice: printed, no JSON mode) |
| 11 | Keep "finding a claim" separate from "judging it" | 🟡 | Not assessed during item 10. Some of the separation exists (claims are read in one module, judged in another) |
| 12 | PASS / FAIL / INCOMPLETE | ✅ 0.4.0 | INCOMPLETE has its own exit code, 4 |
| 13 | Better claim reading (negations, tables, headings, quotes) | ✅ 0.5.3 | Every planted defect caught, no false alarms (was 10 misses, 3 false alarms). Owner's choice: the two new "no dependencies" phrasings were part of 13, not 9 |
| 14 | Optional link checking over the network | ⚪ | Off by default. Useful but not urgent |
| 15 | Label README rules as mechanical, structural or human judgment | ⚪ | Mostly a documentation change |
| 49 | **New:** the brochure rule made the critic FAIL outside repos | ✅ 0.5.5 | Found by the outside run (item 32). Owner's choice: a style note, not part of the outcome; a FAIL now means a claim is contradicted or a rule of the tree is broken |
| 50 | **New:** wrong findings from the outside run (`@overload` stubs, names a decorator fixes, "100% test coverage") | ✅ 0.5.6 | Owner's choice: fixed before items 16 to 18. Four PY-NAME findings remain, listed under Known defects |

## Campaign C: CNS analysis and the Warden boundary

| # | Item | Status | Notes |
|---|---|---|---|
| 16 | Decide adapter recommendations from real evidence, not mentions | ✅ 0.5.8 | Imports and pyproject.toml decide; mentions and folder names do not. Owner's choice: internal convergence is never recommended automatically |
| 17 | Each recommendation lists the evidence it requires | ✅ 0.5.8 | Evidence, method, what was not read, and what would change it |
| 18 | Test the CNS analyzer against known example repos | ✅ 0.5.8 | Eleven examples, each in four folder names; spot-checked on CNS, Warden, swizzle and Burnish |
| 19 | Prove BURNISH never writes files | ✅ 0.5.9 | Narrowed to the read-only commands (`finish` is out of scope). Owner's choice: the tree must be unchanged and no write is allowed anywhere on the machine during a run. Proven on Linux in 0.5.9; runs on Windows and macOS too since 0.5.10 |
| 20 | Integrity checks on proposed edits | ✅ 0.5.11 | Owner's choice, Nov 27, 2026: Campaign 3 of the 9.5 mission in full. Edits to existing files are whole-text replaces Warden refuses when the file changed; every edit has a hash record and a stale check |
| 21 | More finisher stress tests | ✅ 0.5.11 | `finish` proven to write nothing (preview and library calls, both scopes, real process); 23 planted write mechanisms blocked; one boundary before every proposal |
| 22 | Full Warden end-to-end tests | 🟡 | Two more tag-team tests (a concurrent change puts the whole finish back). A run through the whole circuit with Burnish seated is still not tested |

## Campaign D: Other languages (decided)

| # | Item | Status | Notes |
|---|---|---|---|
| 23 | Real Rust checker | ⚪ Not planned | Owner's choice, Nov 26, 2026: BURNISH is a Python checker with written standards for Rust and C++23 (0.5.1) |
| 24 | Real C++23 checker | ⚪ Not planned | Same decision |
| 25 | One finding format shared across languages | ⚪ | Only needed if 23 or 24 happens |
| 26 | Shared test examples across languages | ⚪ | Only needed if 23 or 24 happens |

## Campaign E: Portability

| # | Item | Status | Notes |
|---|---|---|---|
| 27 | Windows CI | ✅ 0.5.10 | Owner's choice: everything but `finish` runs on Windows. Warden uses `fcntl`, which Windows lacks, so the tests that need it are left out by name in `tests/conftest.py`, and a guard holds the list to what needs Warden |
| 28 | macOS CI | ✅ 0.5.10 | Everything runs. One test assumed a case-sensitive file system and was corrected |
| 29 | Second C++ compiler (Clang) | ⚪ | Tied to Campaign D, which is not planned |
| 30 | Exact CMake version | ⚪ | Tied to Campaign D, which is not planned |
| 31 | Run without Warden installed | ✅ 0.5.0 | Every command but `finish` runs without Warden. Owner's choice: Warden is now the `finisher` extra, so a plain install brings only CNS |

## Campaign F: Proof from outside the ecosystem

| # | Item | Status | Notes |
|---|---|---|---|
| 32 | Blind runs on 5 unrelated public repos | ✅ 0.5.4 | Five popular libraries, picked by a rule written first (owner's choice); see `docs/VALIDATION.md` |
| 33 | Count false alarms and misses against a human reviewer | ✅ 0.5.7 | The owner reviewed the README side and agreed with all 14 AI verdicts; the `check` sample is still AI-reviewed only |
| 34 | Deliberately broken repos with planted defects | ✅ 0.5.2 | 30 planted repos (33 since 0.5.3) in `tests/planted/`, scored against an answer key with a ratchet (owner's choice); see `docs/PLANTED.md` |
| 35 | Publish the results in `docs/VALIDATION.md` | ✅ 0.5.4 | Evidence only, with every output and commit on file |
| 36 | Two independent reviewers | 🟡 | Comes after 32 to 35 |

## Campaign G: Release maturity

Items 37 to 45 (stable release, compatibility policy, API tests, vulnerability scanning, dependency inventory, signed
releases, support policy, extension guide, contribution process): ⚪ all later. None of these can make up for a claims
engine that misses defects. Which of them already exist in some form has not been checked.

## Recommended order
1. ✅ Item 10: findings carry their evidence (0.4.1)
2. ✅ Items 46 and 47, plus 48 (0.4.2, 0.4.4); item 7 (0.4.3)
3. ✅ Item 31: run without Warden (0.5.0)
4. ✅ Campaign D: reposition as a Python checker (0.5.1)
5. ✅ Item 34: the planted-defect collection (0.5.2)
6. ✅ Item 13: better claim reading, measured against the collection (0.5.3)
7. ✅ Items 32 and 35, and a first review for 33: outside validation (0.5.4). 33's README side reviewed by the owner (0.5.7)
8. ✅ Items 16 to 18: evidence-based CNS recommendations (0.5.8)
9. ✅ Item 19: the read-only commands write nothing (0.5.9)
10. ✅ Items 27 and 28: Windows and macOS CI (0.5.10)
11. ✅ Items 20 and 21, and part of 22: finisher write safety (0.5.11)
12. **Items 9, 11 and the rest**

## What this plan does not claim
- **No new scores.** Nothing here has been re-audited end to end, so the original plan's target scores are not earned.
- **One fact still comes from the original plan only:** the "three Warden tests" count was not independently re-checked.
  Item 31's import path was checked (Nov 26, 2026): only `burnish/finisher.py` imports Warden.
