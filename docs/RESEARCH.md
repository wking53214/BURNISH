# Research log

What was read to write Streamline's guides, when, and what was not read. A
guide is only as good as its reading, so the gaps are listed with the sources.

All reading was done on 2026-10-08 with WebFetch and WebSearch.

| Topic | Source | What was read | Not read or not trusted |
|-------|--------|---------------|-------------------------|
| Python | [PEP 8](https://peps.python.org/pep-0008/) | Naming, imports, whitespace, comments and docstrings, programming recommendations | Nothing known to be missed. PEP 257 (docstrings) and PEP 484 (typing) were not opened; they are cited only as PEP 8 cites them |
| Python tooling | Web search for 2026 practice (ruff, mypy, pyproject layout) | Link lists only, mostly AI skill pages | **Not used.** Tooling advice here is limited to "use a formatter" |
| Rust | [Rust API Guidelines checklist](https://rust-lang.github.io/api-guidelines/checklist.html) | The checklist summary, all eleven categories | The individual item pages. Clippy's lint list |
| C++ | [C++ Core Guidelines](https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines) | The first 100,000 of 109,052 characters, as a summary: philosophy, interfaces | The final 9,052 characters. **The text of the resource-management (R), expressions (ES), concurrency (CP) and error-handling (E) rules** was not in the summary |
| C++23 | [cppreference, C++23](https://en.cppreference.com/w/cpp/23) | The first 100,000 of 114,434 characters: feature list and compiler-support tables | The final 14,434 characters. The page says it is incomplete, and its support tables are a snapshot |
| README | [Standard Readme](https://github.com/RichardLitt/standard-readme/blob/main/spec.md), [GitHub About READMEs](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes), [Art of README](https://github.com/hackergrrl/art-of-readme/blob/master/README.md), [Make a README](https://www.makeareadme.com/), [awesome-readme](https://github.com/matiassingers/awesome-readme) | Each in full, as a summary | The example READMEs awesome-readme links to were not opened one by one |
| README | Web search for "great README" guides | Link lists: blog posts and AI skill pages | **Not used** |
| Craft | Established practice, no web source | n/a | See [CRAFT.md](CRAFT.md): ranked by judgment |

## Measured, not read

- The exemplars were built and run: GCC 13.3, Clang 18.1.3, Rust (cargo, clippy, rustfmt), Python 3.13.
- Clang 18.1.3 with libstdc++ 13 could not build the C++ exemplar because `std::expected` is not exposed. See [languages/cpp23.md](languages/cpp23.md).

## What a future pass should do

1. Read the Core Guidelines' R, ES, CP and E sections in full and add the criteria they support.
2. Read Rust's individual checklist items and Clippy's lint groups.
3. Open a sample of the awesome-readme examples and check the over-the-top tier against them.
4. Try the C++ exemplar on Clang with libc++, a newer libstdc++, and MSVC.
