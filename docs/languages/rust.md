# Rust

Authority: [Rust API Guidelines checklist](https://rust-lang.github.io/api-guidelines/checklist.html).
Read on 2026-10-08 as a summary of the checklist, not item by item.

## Status, said plainly

Streamline **does not check Rust trees**. These criteria are written down and
the exemplar follows them. CI enforces the exemplar with Rust's own tools:
`cargo fmt --check`, `cargo clippy --all-targets -- -D warnings` with the
pedantic group on, and `cargo test` (which runs the doc examples).

## Criteria

| ID | Rule | In the exemplar |
|----|------|-----------------|
| `RS-NAME` | Conversions are named by cost: `as_` is a cheap view, `to_` is an expensive copy, `into_` consumes | `Priority::letter`, `DefectId::number` read, never convert silently |
| `RS-TYPES` | Use newtypes and enums, not bare `bool` or `Option`, to say what an argument means | `Priority` is an enum; the number is `NonZeroU64`, so zero cannot exist |
| `RS-DOC` | Every public item has a runnable example and says when it errors or panics; examples use `?` | The crate and `FromStr` examples return `Result`; `# Errors` and `# Panics` sections are present |
| `RS-DEBUG` | Every public type implements `Debug`, and its output is never empty | All public types derive it |
| `RS-PRIVATE` | Struct fields are private so the type can change later | `DefectId` and `Allocator` keep their fields private; reads go through methods |
| `RS-VALIDATE` | Validate arguments at the boundary with a typed error | `FromStr` returns `ParseError`; `Allocator::from_ids` refuses an unreadable ID instead of skipping it |

## Other items from the checklist worth knowing

Not in the table because the exemplar is too small to need them: eagerly
implement common traits (`Clone`, `Eq`, `Hash`, `Default`, `From`, `AsRef`),
make types `Send` and `Sync` where possible, builders for complex values, seal
traits that outsiders should not implement, and give macros input that looks
like their output.

## The exemplar

[`exemplars/rust`](../../exemplars/rust) is a crate with no dependencies,
`unsafe_code` forbidden and `missing_docs` on. Its tests read
[`exemplars/vectors.txt`](../../exemplars/vectors.txt).

## Limits

The checklist was read as a summary. The Rust API Guidelines have more items
than the six above; this page lists the ones that apply to the exemplar and
the ones most worth a human's attention.
