# Design

Why Burnish is shaped the way it is. This is the decision record that the
README links to (README rule `OT-DECISIONS`, craft practice `CR11`).

## The analogy

Burnish is a **style editor beside a safety inspector**.

A style editor knows what good writing looks like, and marks it up. An
inspector decides whether the building may be changed at all, and checks it
afterwards. The editor never signs off on a structural change; the inspector
never has opinions about prose. Burnish is the editor. Warden is the
inspector.

| Vibecode | Plain language | In operational terms |
|----------|----------------|----------------------|
| `Burnish.finish` | Here is the finished work | One Transformation, proposed once after the loop, that Warden applies or puts back |
| `critic` | Is it good enough, and what is still wrong? | Commentary on the facts Warden and Ghost measured, written into the README |
| `readme-critic` | A blunt second reader | Rules from the README sources, sorted by tier, no score |

## Layer map

```text
criteria.py          the rules, as data
   │
   ├── checks.py          Python rules a program can judge
   ├── readme_critic.py   README rules, in three tiers
   └── critic.py          the critic's commentary on measured facts
                              │
narrative.py  reads the tree  │
beautify.py   tidies Python source, behavior-preserving
readme.py     compiles and finalizes the README
finisher.py   the one proposal Warden asks for, once, after the loop
cli.py        read-only commands
```

## Decisions

**D1. Burnish never writes.** Writing a repository is Warden's job, behind
a human grant and a green suite. A test fails if any Burnish module calls a
write or delete. Rejected alternative: letting `readme` write the file. It
would have been convenient and would have put a second, ungated writer in the
corpus.

**D2. Burnish counts and detects nothing.** Ghost Tools reports, Warden runs the suite, and both results reach Burnish as facts. The documentation-honesty oracle and the test-count check were removed because they counted what Ghost counts. Tested.

**D3. No score.** A number hides which rule failed. Every report is a list of
named rules. Rejected alternative: a 0 to 100 "beauty score". It would be
quoted instead of read.

**D4. Say what is checked.** A criterion is `IMPLEMENTED` only if Burnish
enforces it, and `DESIGNED` if it is written down. Rust and C++23 are written
down and exemplified, not checked. `burnish languages` prints the truth.
Rejected alternative: a table that marked every language "supported".

**D5. One shared set of test vectors for the three exemplars.** Three
implementations that read one file cannot quietly drift apart. Rejected
alternative: each language with its own tests, which would pass while
disagreeing.

**D6. The over-the-top tier is labelled a synthesis.** Its sources show what
good READMEs share; none states a standard. See
[README_STANDARD.md](README_STANDARD.md).

**D7. Burnish imports Warden; Warden never imports Burnish.** Warden
can govern a finisher it did not write. Tested in Warden.

**D8. The beautification criteria were restored, not reinvented.** The text of
the principles and rules 1 to 6 had been cut to headings in Elegant.md v1.1. The
full text came back from v1.0 in git history, unchanged except for IDs.

## What is not built

Renames, narrative comments, inline architectural comments, guards, and
function splits are designed (`PA`, `PB`, `PC`, `R1` to `R4`) and have no
rewriter. They need a judgement about intent that the tree does not contain.
The first of them to be built should be the one a person can approve at a
glance.
