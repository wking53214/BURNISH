# `burnish check` sample, 2026-11-26

Twenty findings drawn at random, four per repository, with Python's `random.seed(20261126)` and `random.sample` over each
repository's findings in the order `<repository>.check.txt` lists them. Reviewer: Claude (an AI model), reading the code at
each line. Not yet reviewed by a person.

| # | Repository | Finding | Verdict | Why |
|---|---|---|---|---|
| 1 | typing_extensions | `src/typing_extensions.py:2256: PY-NAME` | wrong | a public name that must match `typing.Concatenate` |
| 2 | typing_extensions | `src/typing_extensions.py:1447: PY-NAME` | wrong | a public name that must match `typing.TypedDict` |
| 3 | typing_extensions | `doc/_extensions/gh_link.py:4: PY-TYPE` | correct | a Sphinx hook with no annotations |
| 4 | typing_extensions | `src/typing_extensions.py:2526: PY-NAME` | wrong | a public name that must match `typing.ReadOnly` |
| 5 | idna | `idna/codec.py:1: PY-DOC` | correct | the module has no docstring |
| 6 | idna | `idna/codec.py:144: PY-DOC` | low value | overrides `codecs` `setstate`, documented by the standard library |
| 7 | idna | `idna/codec.py:193: PY-DOC` | low value | a one-line `pass` subclass of a standard-library codec class |
| 8 | idna | `idna/codec.py:71: PY-DOC` | low value | overrides `codecs` `setstate`, documented by the standard library |
| 9 | urllib3 | `src/urllib3/http2/connection.py:314: PY-SWALLOW` | low value | ignores errors while sending a final frame on close, on purpose |
| 10 | urllib3 | `noxfile.py:192: PY-DOC` | low value | a test session in `noxfile.py` |
| 11 | urllib3 | `src/urllib3/util/ssl_.py:1: PY-DOC` | correct | the module has no docstring |
| 12 | urllib3 | `src/urllib3/response.py:615: PY-DOC` | correct | a public method of the base class with no docstring |
| 13 | charset_normalizer | `noxfile.py:163: PY-DOC` | low value | a test session in `noxfile.py` |
| 14 | charset_normalizer | `src/charset_normalizer/utils.py:89: PY-DOC` | correct | a public helper with no docstring |
| 15 | charset_normalizer | `bin/merge_macos_wheels.py:28: PY-DOC` | low value | the entry point of a release script |
| 16 | charset_normalizer | `src/charset_normalizer/utils.py:1: PY-DOC` | correct | the module has no docstring |
| 17 | requests | `src/requests/utils.py:371: PY-DOC` | wrong | an `@overload` type stub; the real function below it has a docstring |
| 18 | requests | `src/requests/structures.py:127: PY-DOC` | wrong | an `@overload` type stub |
| 19 | requests | `src/requests/models.py:456: PY-DOC` | correct | a public method with no docstring |
| 20 | requests | `src/requests/utils.py:618: PY-DOC` | wrong | an `@overload` type stub; the real function below it has a docstring |
