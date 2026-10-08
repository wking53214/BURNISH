# Design

Why Streamline is shaped the way it is. This is the decision record that the
README links to (README rule `OT-DECISIONS`, craft practice `CR11`).

## The analogy

Streamline is a **style editor beside a safety inspector**.

A style editor knows what good writing looks like, and marks it up. An
inspector decides whether the building may be changed at all, and checks it
afterwards. The editor never signs off on a structural change; the inspector
never has opinions about prose. Streamline is the editor. Elegant is the
inspector.

| Vibecode | Plain language | In operational terms |
|----------|----------------|----------------------|
| `Streamline.review` | Is this good enough yet? | The critic compares claims in documents with the tree |
| `Streamline.propose` | Here is the one change I would make | A proposer returns a Transformation that has not been applied |
| `Streamline.attack` | Did the fix hold up? | An oracle that never imports the critic re-measures the tree |
| `readme-critic` | A blunt second reader | Rules from the README sources, sorted by tier, no score |

## Layer map

```text
criteria.py          the rules, as data
   │
   ├── checks.py          Python rules a program can judge
   ├── readme_critic.py   README rules, in three tiers
   └── critic.py          claims in documents against the tree
                              │
narrative.py  reads the tree  │
oracle.py     freezes, then re-measures (does not import critic)
proposers.py  proposes one change
readme.py     compiles a README draft
craft.py      the four answers Elegant asks for
cli.py        read-only commands
```

## Decisions

**D1. Streamline never writes.** Writing a repository is Elegant's job, behind
a human grant and a green suite. A test fails if any Streamline module calls a
write or delete. Rejected alternative: letting `readme` write the file. It
would have been convenient and would have put a second, ungated writer in the
corpus.

**D2. The reviewer and the oracle never import each other.** A flattering
review must not launder a bad change, and a harsh one must not hide a good one.
Tested.

**D3. No score.** A number hides which rule failed. Every report is a list of
named rules. Rejected alternative: a 0 to 100 "beauty score". It would be
quoted instead of read.

**D4. Say what is checked.** A criterion is `IMPLEMENTED` only if Streamline
enforces it, and `DESIGNED` if it is written down. Rust and C++23 are written
down and exemplified, not checked. `streamline languages` prints the truth.
Rejected alternative: a table that marked every language "supported".

**D5. One shared set of test vectors for the three exemplars.** Three
implementations that read one file cannot quietly drift apart. Rejected
alternative: each language with its own tests, which would pass while
disagreeing.

**D6. The over-the-top tier is labelled a synthesis.** Its sources show what
good READMEs share; none states a standard. See
[README_STANDARD.md](README_STANDARD.md).

**D7. Streamline imports Elegant; Elegant never imports Streamline.** Elegant
can govern a craft it did not write. Tested in Elegant.

**D8. The beautification criteria were restored, not reinvented.** The text of
the principles and rules 1 to 6 had been cut to headings in Elegant.md v1.1. The
full text came back from v1.0 in git history, unchanged except for IDs.

## What is not built

Renames, narrative comments, inline architectural comments, guards, and
function splits are designed (`PA`, `PB`, `PC`, `R1` to `R4`) and have no
proposer. They need a judgement about intent that the tree does not contain.
The first of them to be built should be the one a person can approve at a
glance.
