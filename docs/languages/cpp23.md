# C++23

Authorities: the [C++ Core Guidelines](https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines)
and [cppreference's C++23 page](https://en.cppreference.com/w/cpp/23).
Read on 2026-10-08. **The Core Guidelines page was truncated at about 100,000 of
109,000 characters, and its resource-management, concurrency and error-handling
rule text was not in what was read.** Those rules are not summarised here.

## Status, said plainly

Burnish **does not check C++ trees**. The criteria are written down and the
exemplar follows them. CI builds the exemplar with `g++ -std=c++23 -Wall
-Wextra -Wpedantic -Wconversion -Wshadow -Werror` and runs it under `ctest`.

## Criteria

| ID | Rule | Guideline | In the exemplar |
|----|------|-----------|-----------------|
| `CX-EXPLICIT` | Say it in code; compilers do not read comments | P.1 | `Priority` and `ParseError` are enum classes, not chars and ints |
| `CX-TYPES` | Strong, explicit interfaces; no swappable adjacent parameters | I.4, I.24 | `DefectId::make(Priority, std::uint64_t)` takes two different types |
| `CX-PRE` | State and check preconditions | I.5, I.6 | `make` rejects a zero number instead of trusting the caller |
| `CX-OWN` | Never transfer ownership through a raw pointer | I.11 | Nothing owns through a pointer; values only |
| `CX-GLOBAL` | Avoid non-const globals | I.2 | None. `Allocator` holds its own state |
| `CX-EXPECTED` | Expected failures are values: `std::expected` | cppreference C++23 | `parse` and `Allocator` return `std::expected<..., ParseError>`; no expected failure throws |
| `CX-NODISCARD` | Mark results a caller must not ignore | Elegant.md v1.0 | Every returning function is `[[nodiscard]]` |
| `CX-SUPPORT` | Know the compiler; some C++23 is version-sensitive | cppreference | See below |

## Which C++23 features the exemplar uses, and which it avoids

Uses: `std::expected`, `std::to_underlying`, `std::unreachable`, defaulted
`operator<=>`. Avoids `<print>` (GCC 14), `import std` and `std::mdspan`
(GCC 15 and 16 per cppreference), because the build should not need a very
recent compiler. The cppreference support tables are a snapshot and the page
says it is incomplete.

## A measured compiler caveat

Verified with **GCC 13.3** on Ubuntu 24.04. **Clang 18.1.3 with libstdc++ 13
does not build it**: the standard library hides `std::expected` unless the
compiler reports a newer concepts level than Clang 18 does. Clang with libc++,
a newer libstdc++, and MSVC were not tried. This is why `CX-SUPPORT` exists.

## The exemplar

[`exemplars/cpp23`](../../exemplars/cpp23) is one header and one test.
The test reads [`exemplars/vectors.txt`](../../exemplars/vectors.txt).
