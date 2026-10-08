/**
 * DURABLE DEFECT IDS: Elegant.md Rule 9, as a small header that follows the
 * C++ Core Guidelines.
 *
 * A defect ID is one letter for its priority (C critical, H high, M medium,
 * L low) and a number: "H12". An ID never changes meaning once published, so
 * the allocator only moves forward. Gaps are not reused: if H3 was deleted,
 * the next high-priority ID is still one past the highest ever seen.
 *
 * WHAT THIS IS
 *   The C++23 member of a trio. exemplars/python and exemplars/rust do the same
 *   job and read the same exemplars/vectors.txt.
 *
 * WHAT IT CANNOT DO
 *   Persist anything. Callers hand it the IDs that already exist.
 *
 * COMPILER NOTE
 *   Needs <expected> (GCC 12, Clang 16, MSVC 19.33) and std::to_underlying.
 *   It does not use <print> or `import std`: those arrived later and are the
 *   most version-sensitive C++23 features.
 */
#ifndef STREAMLINE_DEFECT_IDS_HPP
#define STREAMLINE_DEFECT_IDS_HPP

#include <algorithm>
#include <array>
#include <charconv>
#include <cstdint>
#include <expected>
#include <optional>
#include <span>
#include <string>
#include <string_view>
#include <system_error>
#include <utility>

namespace defect_ids {

/// How urgent a defect is. Declaration order is sort order: critical first. A type, not a char (I.4).
enum class Priority : std::uint8_t { critical, high, medium, low };

inline constexpr std::size_t kPriorityCount = 4;

/// Why a string is not a defect ID. A value, not an exception: bad input is expected, so it is returned (std::expected).
enum class ParseError : std::uint8_t { empty, bad_priority, bad_number, leading_zero };

/// A short stable name for an error, shared with the other exemplars.
[[nodiscard]] constexpr std::string_view kind(ParseError error) noexcept {
    switch (error) {
        case ParseError::empty: return "empty";
        case ParseError::bad_priority: return "bad_priority";
        case ParseError::bad_number: return "bad_number";
        case ParseError::leading_zero: return "leading_zero";
    }
    std::unreachable();  // every enumerator is handled above
}

/// The letter used in an ID.
[[nodiscard]] constexpr char letter(Priority priority) noexcept {
    return "CHML"[std::to_underlying(priority)];
}

[[nodiscard]] constexpr std::optional<Priority> priority_from_letter(char c) noexcept {
    switch (c) {
        case 'C': return Priority::critical;
        case 'H': return Priority::high;
        case 'M': return Priority::medium;
        case 'L': return Priority::low;
        default: return std::nullopt;
    }
}

/// A priority and a number of at least one. Construct it only through make() or parse().
class DefectId {
public:
    /// Precondition: number >= 1. Returns bad_number otherwise rather than trusting the caller (I.5, I.6).
    [[nodiscard]] static constexpr std::expected<DefectId, ParseError> make(Priority priority,
                                                                            std::uint64_t number) noexcept {
        if (number == 0) {
            return std::unexpected(ParseError::bad_number);
        }
        return DefectId{priority, number};
    }

    [[nodiscard]] constexpr Priority priority() const noexcept { return priority_; }
    [[nodiscard]] constexpr std::uint64_t number() const noexcept { return number_; }

    /// Critical before high before medium before low, then by number.
    [[nodiscard]] friend constexpr auto operator<=>(const DefectId&, const DefectId&) noexcept = default;

    [[nodiscard]] std::string to_string() const {
        return std::string(1, letter(priority_)) + std::to_string(number_);
    }

private:
    constexpr DefectId(Priority priority, std::uint64_t number) noexcept : priority_{priority}, number_{number} {}

    Priority priority_;
    std::uint64_t number_;
};

/// Read an ID such as "H12"; the error says exactly what is wrong.
[[nodiscard]] inline std::expected<DefectId, ParseError> parse(std::string_view text) noexcept {
    if (text.empty()) {
        return std::unexpected(ParseError::empty);
    }
    const auto priority = priority_from_letter(text.front());
    if (!priority) {
        return std::unexpected(ParseError::bad_priority);
    }
    const std::string_view digits = text.substr(1);
    std::uint64_t number = 0;
    const auto [end, status] = std::from_chars(digits.data(), digits.data() + digits.size(), number);
    const bool consumed_all = end == digits.data() + digits.size();
    if (digits.empty() || status != std::errc{} || !consumed_all || digits.front() == '-' || digits.front() == '+') {
        return std::unexpected(ParseError::bad_number);
    }
    if (number == 0) {
        return std::unexpected(ParseError::bad_number);
    }
    if (digits.front() == '0') {
        return std::unexpected(ParseError::leading_zero);
    }
    return DefectId::make(*priority, number);
}

/// Hands out the next unused number for a priority, and never goes backward.
class Allocator {
public:
    Allocator() = default;

    /// An allocator that has seen these IDs. An ID that cannot be read is refused,
    /// not skipped, because skipping it could hand out a number that is already taken.
    [[nodiscard]] static std::expected<Allocator, ParseError> from_ids(std::span<const std::string> existing) {
        Allocator allocator;
        for (const std::string& text : existing) {
            const auto known = parse(text);
            if (!known) {
                return std::unexpected(known.error());
            }
            auto& slot = allocator.highest_[std::to_underlying(known->priority())];
            slot = std::max(slot, known->number());
        }
        return allocator;
    }

    /// The next ID for `priority`. It is recorded, so it is never handed out twice.
    /// Returns bad_number only if every 64-bit number of that priority is already taken.
    [[nodiscard]] std::expected<DefectId, ParseError> allocate(Priority priority) noexcept {
        auto& slot = highest_[std::to_underlying(priority)];
        if (slot == UINT64_MAX) {
            return std::unexpected(ParseError::bad_number);
        }
        ++slot;
        return DefectId::make(priority, slot);
    }

private:
    std::array<std::uint64_t, kPriorityCount> highest_{};
};

}  // namespace defect_ids

#endif  // STREAMLINE_DEFECT_IDS_HPP
