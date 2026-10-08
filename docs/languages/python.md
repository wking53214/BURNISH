# Python

Authority: [PEP 8, Style Guide for Python Code](https://peps.python.org/pep-0008/).
Read in full on 2026-10-08. Burnish checks eight of these items itself
(`burnish check`). Everything else PEP 8 asks for is left to a formatter,
and this page says which.

## What Burnish checks

| ID | Rule | Why it matters |
|----|------|----------------|
| `PY-EXC` | No bare `except:` | It catches `KeyboardInterrupt` and `SystemExit` and hides bugs. Name what you handle. |
| `PY-SWALLOW` | No handler whose body is only `pass` | A failure that vanishes looks exactly like success. This is the same defect Elegant.md calls "swallowed exceptions", rated HIGH at adoption. |
| `PY-STAR` | No `from x import *` | A reader cannot tell where a name came from. |
| `PY-DOC` | Docstrings on the public surface | PEP 8 asks for them on every public module, class, function and method. Properties and one-line bodies are exempt. |
| `PY-NAME` | `lowercase_with_underscores` functions, `CapWords` classes | Names are the first documentation (criterion `CR3`). |
| `PY-CMP` | `is None`, never `== None`; no `== True` | Equality is not identity. |
| `PY-RET` | No bare `return` in a function that returns a value elsewhere | PEP 8: write `return None` where None is meant. |
| `PY-TYPE` | Annotated public signatures | PEP 484, recommended by PEP 8. |

Test files are held to the checks about behavior (`PY-EXC`, `PY-SWALLOW`,
`PY-STAR`, `PY-CMP`, `PY-RET`) and not asked for docstrings or annotations.
A file that does not parse is reported as `PY-PARSE`, never skipped.

## What PEP 8 asks for that Burnish does not check

These are mechanical, and a formatter does them better than Burnish would.
Use one (ruff or black) and let it fail the build.

- Four-space indentation, spaces not tabs, line length 79 (72 in docstrings and comments).
- Import order: standard library, third party, local, with a blank line between groups; absolute imports.
- Blank lines around definitions, spaces around operators, no trailing whitespace.
- `startswith` instead of slicing, `def` instead of assigning a lambda, `with` for cleanup, `raise X from Y`.

## The exemplar

[`exemplars/python/defect_ids.py`](../../exemplars/python/defect_ids.py) is a
small program written to these rules. `burnish check exemplars` passes on it,
and its tests read the same vectors as the Rust and C++ versions.

## Limits

PEP 8 describes style, not design. A file can pass every check above and still
be badly designed. The craft practices in [CRAFT.md](../CRAFT.md) are where
design lives, and most of them need a person.
