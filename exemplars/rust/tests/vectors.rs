//! The Rust exemplar against the shared vectors in `exemplars/vectors.txt`.

use defect_ids::{Allocator, DefectId, ParseError, Priority};
use std::fs;

fn rows(kind: &str) -> Vec<Vec<String>> {
    let path = concat!(env!("CARGO_MANIFEST_DIR"), "/../vectors.txt");
    let text = fs::read_to_string(path).expect("the shared vectors file is readable");
    text.lines()
        .filter(|line| !line.starts_with('#'))
        .map(|line| {
            line.split_whitespace()
                .map(str::to_owned)
                .collect::<Vec<_>>()
        })
        .filter(|words| words.first().is_some_and(|w| w == kind))
        .map(|words| {
            words[1..]
                .iter()
                .map(|w| {
                    if w == "<empty>" {
                        String::new()
                    } else {
                        w.clone()
                    }
                })
                .collect()
        })
        .collect()
}

fn ids(field: &str) -> Vec<String> {
    if field == "-" {
        Vec::new()
    } else {
        field.split(',').map(str::to_owned).collect()
    }
}

fn priority(letter: &str) -> Priority {
    match letter {
        "C" => Priority::Critical,
        "H" => Priority::High,
        "M" => Priority::Medium,
        "L" => Priority::Low,
        other => panic!("the vectors use an unknown priority {other:?}"),
    }
}

#[test]
fn parse_matches_the_vectors() {
    let table = rows("parse");
    assert!(!table.is_empty(), "no parse vectors were read");
    for row in table {
        let result = row[0].parse::<DefectId>();
        match row[1].as_str() {
            "ok" => assert_eq!(result.expect(&row[0]).to_string(), row[2], "{row:?}"),
            _ => assert_eq!(result.expect_err(&row[0]).kind(), row[2], "{row:?}"),
        }
    }
}

#[test]
fn alloc_matches_the_vectors() {
    let table = rows("alloc");
    assert!(!table.is_empty(), "no alloc vectors were read");
    for row in table {
        let built = Allocator::from_ids(ids(&row[0]));
        match row[2].as_str() {
            "ok" => {
                let id = built
                    .expect("existing IDs are valid")
                    .allocate(priority(&row[1]));
                assert_eq!(id.to_string(), row[3], "{row:?}");
            }
            _ => assert_eq!(
                built.expect_err("existing IDs are invalid").kind(),
                row[3],
                "{row:?}"
            ),
        }
    }
}

#[test]
fn sequences_match_the_vectors() {
    let table = rows("seq");
    assert!(!table.is_empty(), "no seq vectors were read");
    for row in table {
        let mut allocator = Allocator::from_ids(ids(&row[0])).expect("existing IDs are valid");
        let got: Vec<String> = row[1]
            .split(',')
            .map(|p| allocator.allocate(priority(p)).to_string())
            .collect();
        assert_eq!(got.join(","), row[3], "{row:?}");
    }
}

#[test]
fn ids_order_by_priority_then_number() {
    let id = |text: &str| text.parse::<DefectId>().expect("valid");
    assert!(id("C9") < id("H1") && id("H1") < id("M1") && id("M1") < id("L1"));
    assert!(id("H2") < id("H10"));
}

#[test]
fn an_error_can_be_shown_to_a_person() {
    let message = ParseError::BadPriority.to_string();
    assert!(message.contains("C, H, M, L"));
}
