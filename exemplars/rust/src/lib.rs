//! Durable defect IDs: Elegant.md Rule 9, as a small crate that follows the
//! [Rust API Guidelines](https://rust-lang.github.io/api-guidelines/checklist.html).
//!
//! A defect ID is one letter for its priority (`C` critical, `H` high, `M`
//! medium, `L` low) and a number: `H12`. An ID never changes meaning once
//! published, so the [`Allocator`] only moves forward. Gaps are not reused: if
//! `H3` was deleted, the next high-priority ID is still one past the highest
//! ever seen.
//!
//! This is the Rust member of a trio. `exemplars/python` and `exemplars/cpp23`
//! do the same job and read the same `exemplars/vectors.txt`.
//!
//! # Example
//!
//! ```
//! use defect_ids::{Allocator, Priority};
//!
//! # fn main() -> Result<(), defect_ids::ParseError> {
//! let mut allocator = Allocator::from_ids(["C1", "H2", "H7"])?;
//! assert_eq!(allocator.allocate(Priority::High).to_string(), "H8");
//! assert_eq!(allocator.allocate(Priority::Medium).to_string(), "M1");
//! # Ok(())
//! # }
//! ```
//!
//! # What it cannot do
//!
//! Persist anything. Callers hand it the IDs that already exist.

use std::collections::HashMap;
use std::error::Error;
use std::fmt;
use std::num::NonZeroU64;
use std::str::FromStr;

/// How urgent a defect is. Declaration order is sort order: critical first.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum Priority {
    /// Breaks containment or a safety invariant immediately.
    Critical,
    /// Enables bypass, an audit that lies, or a race on the critical path.
    High,
    /// Orchestration gaps, policy defects, gradual escape.
    Medium,
    /// Noise, environment-sensitive thresholds, cosmetic mismatch.
    Low,
}

impl Priority {
    /// The letter used in an ID.
    #[must_use]
    pub fn letter(self) -> char {
        match self {
            Self::Critical => 'C',
            Self::High => 'H',
            Self::Medium => 'M',
            Self::Low => 'L',
        }
    }

    fn from_letter(letter: char) -> Option<Self> {
        match letter {
            'C' => Some(Self::Critical),
            'H' => Some(Self::High),
            'M' => Some(Self::Medium),
            'L' => Some(Self::Low),
            _ => None,
        }
    }
}

/// Why a string is not a defect ID.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ParseError {
    /// The string was empty.
    Empty,
    /// The first character was not one of `C`, `H`, `M`, `L`.
    BadPriority,
    /// What follows the letter is not a positive whole number that fits in 64 bits.
    BadNumber,
    /// The number began with a zero, so two spellings would name one defect.
    LeadingZero,
}

impl ParseError {
    /// A short stable name for the error, shared with the other exemplars.
    #[must_use]
    pub fn kind(self) -> &'static str {
        match self {
            Self::Empty => "empty",
            Self::BadPriority => "bad_priority",
            Self::BadNumber => "bad_number",
            Self::LeadingZero => "leading_zero",
        }
    }
}

impl fmt::Display for ParseError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let why = match self {
            Self::Empty => "it is empty",
            Self::BadPriority => "its first character is not one of C, H, M, L",
            Self::BadNumber => "its number is missing, zero, negative or too large",
            Self::LeadingZero => "its number starts with a zero",
        };
        write!(f, "not a defect ID: {why}")
    }
}

impl Error for ParseError {}

/// A priority and a number of at least one. Fields are private so the type can change later.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct DefectId {
    priority: Priority,
    number: NonZeroU64,
}

impl DefectId {
    /// Build an ID from parts that are already known to be valid.
    #[must_use]
    pub fn new(priority: Priority, number: NonZeroU64) -> Self {
        Self { priority, number }
    }

    /// The priority this ID was filed under.
    #[must_use]
    pub fn priority(self) -> Priority {
        self.priority
    }

    /// The number, which is never zero.
    #[must_use]
    pub fn number(self) -> NonZeroU64 {
        self.number
    }
}

impl fmt::Display for DefectId {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}{}", self.priority.letter(), self.number)
    }
}

impl FromStr for DefectId {
    type Err = ParseError;

    /// Read an ID such as `H12`.
    ///
    /// # Errors
    ///
    /// Returns a [`ParseError`] naming exactly what is wrong.
    ///
    /// # Example
    ///
    /// ```
    /// use defect_ids::{DefectId, ParseError};
    ///
    /// # fn main() -> Result<(), ParseError> {
    /// let id: DefectId = "H12".parse()?;
    /// assert_eq!(id.to_string(), "H12");
    /// assert_eq!("H01".parse::<DefectId>(), Err(ParseError::LeadingZero));
    /// # Ok(())
    /// # }
    /// ```
    fn from_str(text: &str) -> Result<Self, Self::Err> {
        let mut characters = text.chars();
        let first = characters.next().ok_or(ParseError::Empty)?;
        let priority = Priority::from_letter(first).ok_or(ParseError::BadPriority)?;
        let digits = characters.as_str();
        if digits.is_empty() || !digits.bytes().all(|b| b.is_ascii_digit()) {
            return Err(ParseError::BadNumber);
        }
        let number: NonZeroU64 = digits.parse().map_err(|_| ParseError::BadNumber)?;
        if digits.starts_with('0') {
            return Err(ParseError::LeadingZero);
        }
        Ok(Self { priority, number })
    }
}

/// Hands out the next unused number for a priority, and never goes backward.
#[derive(Debug, Clone, Default)]
pub struct Allocator {
    highest: HashMap<Priority, u64>,
}

impl Allocator {
    /// An allocator that has seen no IDs.
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    /// An allocator that has seen these IDs.
    ///
    /// # Errors
    ///
    /// Returns the first [`ParseError`] met. An ID that cannot be read is
    /// refused rather than skipped, because skipping it could hand out a
    /// number that is already taken.
    pub fn from_ids<I, S>(existing: I) -> Result<Self, ParseError>
    where
        I: IntoIterator<Item = S>,
        S: AsRef<str>,
    {
        let mut allocator = Self::new();
        for text in existing {
            let known: DefectId = text.as_ref().parse()?;
            let slot = allocator.highest.entry(known.priority()).or_insert(0);
            *slot = (*slot).max(known.number().get());
        }
        Ok(allocator)
    }

    /// The next ID for `priority`. It is recorded, so it is never handed out twice.
    ///
    /// # Panics
    ///
    /// Panics only if 2^64 - 1 IDs of one priority already exist.
    pub fn allocate(&mut self, priority: Priority) -> DefectId {
        let slot = self.highest.entry(priority).or_insert(0);
        *slot = slot.checked_add(1).expect("defect numbers are exhausted");
        let number = NonZeroU64::new(*slot).expect("a number after adding one is not zero");
        DefectId::new(priority, number)
    }
}
