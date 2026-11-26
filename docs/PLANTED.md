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

A line flagged twice counts once. The critic reports one complaint once: the same wrong number said on two lines, or the
same missing dependency behind two sentences, is one row on one of those lines. So each planted repository states each
complaint once, and every planted line is scored on its own.

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
| trap | 12 | 0 | 0 | 0 |
| hard | 12 | 15 | 1 | 0 |
| total | 34 | 27 | 1 | 0 |

## History

- **0.5.2:** 30 repositories; 17 catches, 10 misses and 3 false alarms, all the misses in the hard group. It missed a count
  in a table cell; claims after "not just ... but", "not small:", "No one disputes it:", "Without exception,", "If you clone
  it,", "As of today," and "was rewritten; it now has"; and "depends on nothing" and "Dependencies: none". It flagged
  "production ready" inside quotation marks (twice) and a count that belongs to one module.
- **0.5.3 (item 13):** all ten caught and all three false alarms gone. Three hard repositories held two sentences that make
  the same complaint, which the critic reports once; one was split in two and two had a number changed, so each line is
  scored alone. Two traps were added to check that the new reading does not go too far: real denials, wishes and history
  next to the phrases it now reads as claims, history after a colon, an old quoted motto, and one package's count.
- **0.5.4:** one hard repository added from the first outside run (`docs/VALIDATION.md`): "100% test coverage", an
  absolute with a word inside it, which the critic misses. Recorded as a miss.

A score here does not mean the critic reads every README right. Every sentence in the collection was written by this
project, and the two newest traps were written after the reader was changed.

## What this does not show

- How the critic does on real repositories. The collection is small and written by the same project; outside validation
  is items 32, 33 and 35 of the plan.
- Anything about `burnish check` or `burnish readme-critic`. Only the claims critic is scored.
