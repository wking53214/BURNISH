# The planted-defect collection

Item 34 of the [remediation plan](REMEDIATION_PLAN_v2.md). A fixed yardstick for the claims critic: small repositories with
defects planted on purpose, and an answer key that says where each defect is. Item 13 (better claim reading) is measured
against it.

## What is in it

Each file in `tests/planted/` is one small repository written out as text: a README, a `pyproject.toml` and a package. The
test unpacks it into a scratch folder, so the planted defects never trip Burnish's own checks on this repository. There are
three groups:

- **catch:** plain defects the critic should catch: a wrong test count, a wrong pin, a "no dependencies" claim the code
  contradicts, an unbacked absolute such as "production ready", a `pyproject.toml` that cannot be parsed.
- **trap:** honest sentences that look like defects: denials, goals, history, quotations, another thing's count, true
  claims. A trap plants no defect, so anything the critic flags in one is a false alarm.
- **hard:** defects and traps where claim reading is hard: tables, headings, blockquotes, and negative or wishful words in
  sentences that still make a claim.

Burnish counts no tests, so each key also gives the suite result a run measured, and the critic judges test counts against
that, as it would against Warden's result.

## How it is scored

A flag is a row of the critic's report that is not supported, identified by its file, line and kind. For each repository:

- a **catch** is a defect in the key that the critic flags with the right kind,
- a **miss** is a defect in the key that the critic does not flag,
- a **false alarm** is a flag the key does not list as a defect.

A line flagged twice counts once.

## The ratchet

The key records today's result as well as the truth: a defect not caught yet is marked `missed`, and a flag on a line with
no defect is listed as `false-alarm`. `tests/test_planted.py` fails when the result differs from the key in either
direction:

- **worse** (a catch lost, a new false alarm): a regression to fix,
- **better** (a miss now caught, a false alarm gone): write it into the key and update the table below in the same change,
  so the improvement is on the record.

## Today's result

The test checks that this table matches the key.

| Group | Repositories | Catches | Misses | False alarms |
|---|---|---|---|---|
| catch | 10 | 12 | 0 | 0 |
| trap | 10 | 0 | 0 | 2 |
| hard | 10 | 5 | 10 | 1 |
| total | 30 | 17 | 10 | 3 |

What the critic misses today, all in the hard group:

- a wrong test count in a table cell,
- a claim after "not just ... but" or "not small:", read as a denial,
- a count after a negative lead-in ("No one disputes it:", "Without exception,"), read as a denial,
- a count after "If you clone it,", read as a wish,
- a count after "As of today," or "now has" following "was", read as history,
- "depends on nothing outside the standard library" and "Dependencies: none", phrasings the reader does not know.

Its false alarms today:

- "production ready" inside quotation marks, as a phrase or as someone else's words (two),
- "The parser module has 3 tests", a count of one module, judged against the whole suite.

## What this does not show

- How the critic does on real repositories. The collection is small and written by the same project; outside validation
  is items 32, 33 and 35 of the plan.
- Anything about `burnish check` or `burnish readme-critic`. Only the claims critic is scored.
