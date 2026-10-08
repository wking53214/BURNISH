# Craft: making code a work of art

The criteria in [CRITERIA.md](CRITERIA.md) and the language guides keep code
correct and consistent. These practices are what lift it past that. They are
ranked by how much they change a reader's experience per unit of effort.

**Provenance, said plainly.** This list comes from established software craft
(Ousterhout's deep modules, Beck's simple design, property-based and mutation
testing, "make illegal states unrepresentable") and was ranked by judgment. No
single document states it, and it was not researched on the web. The ranking is an
opinion; the practices are not new.

**Who can judge.** Only one of these is partly mechanical. Most need a person
who knows the intent. That is why the criteria table marks them `human` or
`proposed`, and why Streamline does not pretend to enforce them.

## Top tier: changes how the code reads

| ID | Practice | What it means |
|----|----------|---------------|
| `CR1` | Make illegal states impossible | Design types so wrong usage cannot be written. The biggest jump from "careful" to "correct by design". The Rust `NonZeroU64` and the C++ `make()` in the exemplars are small cases of it. |
| `CR2` | Deep, simple interfaces | A small surface that hides a lot. The reader learns three things and gets thirty done. |
| `CR3` | Names are the first documentation | A precise name removes the need for a comment. This is principle `PA`. |

## Strong tier: makes the code trustworthy

| ID | Practice | What it means |
|----|----------|---------------|
| `CR4` | Explain why, not what | Comments carry intent, constraints and rejected alternatives. The code already says what. Principles `PB` and `PC`. |
| `CR5` | Tests that state rules | Property tests ("for any input, this holds") and mutation tests over example tests. ghost_tools and SWIZZLE exist for this. |
| `CR6` | One way to do each thing | Remove duplicates and near-duplicates. Each concept lives in one place. |
| `CR7` | Fail loudly, early, specifically | Validate at the boundary. Never return a quiet empty result. `PY-SWALLOW` catches one form of the opposite. |

## Polish tier: makes the code a pleasure to maintain

| ID | Practice | What it means |
|----|----------|---------------|
| `CR8` | One level of abstraction per function | A function reads like an outline; details are pushed down a level. |
| `CR9` | Consistent shape | The same problem is solved the same way everywhere, so a reader predicts the next line. |
| `CR10` | Delete code | Dead code, stale flags and unused options are noise. The most beautiful change is often a removal. |
| `CR11` | Decision notes beside the code | A short "why we chose this" file next to what it explains. [DESIGN.md](DESIGN.md) is Streamline's. |

## The risk

Beauty can destroy working behavior. The usual failure is a cleanup that
quietly changes what the code does. That is why Streamline proposes and Elegant
decides: a person grants the change, and the target's own test suite must be
green before it and still green after it (rule `R7`).

## What is mechanical today

`CR3` through the Python naming check, and the neighbouring Python checks.
`CR7` only in the narrow form `PY-SWALLOW`. `CR8` and `CR10` can be found by
ghost_tools (long functions, dead code) and are not duplicated here. Everything
else is a person's call.
