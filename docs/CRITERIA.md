# Criteria

The rules for making code beautiful without changing what it does. This is the
full text that `Elegant.md` v1.0 carried for the principles and rules 1 to 6. The
v1.1 edit cut them to one-line headings; they are restored here. Rules 7 to 11
are as they stand in Elegant.md v1.2.
`burnish/criteria.py` holds the same rules as data, and a test fails if the
two disagree.

Rules 5, 7 and 9 describe the discipline of change itself. They are enforced by
[Warden](https://github.com/wking53214/Warden), not by Burnish.

**How to read the IDs.** `PA` to `PC` are principles, `R1` to `R11` are rules.
Python, Rust and C++23 items are in [docs/languages/](languages/), the craft
practices are in [CRAFT.md](CRAFT.md), and the README rules are in
[README_STANDARD.md](README_STANDARD.md).

**Author of the original rules:** William N. King. Origin: the ≡TACK Kernel
artistic rewrite and validation phase, 2026-10-01.

---

## Part 1. Principles

Beautification is the documentation and restructuring of code to make its intent, architecture, and defects visible. It is not rewriting; it is translation to transparency.

### PA. Naming as truth

**Rule: Names must match the contract they represent.**

When code's name contradicts its implementation, beautification corrects the name, the documentation, or the implementation-whichever is the truth.

**Example: SlidingWindowRing Defect**

```cpp
// BEFORE (Hidden defect)
class SlidingWindowRing {
private:
    uint64_t counter_ = 0;  // Name says "sliding window"; is actually single counter
public:
    void Consume(uint32_t tokens) { counter_ += tokens; }
};
```

```cpp
// AFTER (Defect visible)
/**
 * SLIDING WINDOW RING: Token Bucket with Explicit Defect
 * 
 * ARCHITECTURAL DEFECT: Single Counter (Not Sliding Window)
 * This class implements a single counter that increments with token consumption.
 * True sliding-window behavior would track time windows and reset periodically.
 * Current implementation: reactive debt tracking, not proactive rate limiting.
 */
class SlidingWindowRing {
private:
    uint64_t counter_ = 0;  // Single counter masquerading as sliding window
public:
    [[nodiscard]] uint64_t Consume(uint32_t tokens) noexcept {
        counter_ += tokens;
        return counter_;
    }
};
```

**The defect becomes visible. The name either changes, or documentation makes the mismatch explicit.**

### PB. Narrative documentation

**Rule: Code must tell a story about what it does, why it exists, and what it cannot do.**

Documentation goes before the code, not after. It establishes the contract (what the reader should expect), then the implementation either fulfills it or documents why it doesn't.

**Example: Layer Structure Documentation**

```cpp
/**
 * ≡TACK KERNEL LAYER 1: Hardware-Locked Timing
 *
 * PURPOSE: Measure the execution point of untrusted code at hardware precision.
 *
 * CORRECTNESS RULE: Every transaction measures actual CPU clock ticks from
 * RDTSCP (x86) or CNTPCT_EL0 (ARM64), not virtual time or wall clock.
 * This enables deadline enforcement independent of OS scheduler.
 *
 * ───────────────────────────────────────────────────────────────────────────
 * ARCHITECTURAL DEFECT: Silent Fallback to Zero on Unknown Architectures
 *
 * On unknown architectures (not x86_64 or aarch64), ReadTicks() returns 0.
 * This breaks containment: a sandbox reports zero execution time, bypassing
 * deadline enforcement. The correct behavior is to fail at compile time or
 * throw at runtime, not silently disable the layer.
 *
 * Impact: CRITICAL. Layer 1 is the foundation; a silent zero enables escape.
 * ───────────────────────────────────────────────────────────────────────────
 */

namespace stack::governor {

class HardwareClock {
public:
    /**
     * READ TICKS: Sample hardware clock counter.
     *
     * Returns the current cycle count from the CPU clock register.
     * On known architectures, this is precise and reliable.
     * On unknown architectures, returns 0 (DEFECT).
     *
     * Contract: Caller assumes result > 0 on successful measurement.
     * Defect: No validation that architecture is known.
     */
    [[nodiscard]] static uint64_t ReadTicks() noexcept {
#if defined(__x86_64__)
        unsigned int aux;
        return __rdtscp(&aux);
#elif defined(__aarch64__)
        uint64_t ticks;
        asm volatile("mrs %0, cntpct_el0" : "=r"(ticks));
        return ticks;
#else
        return 0;  // DEFECT: Silent fallback instead of compile error
#endif
    }
};

} // namespace stack::governor
```

### PC. Architectural properties as comments

**Rule: Every non-obvious property must be documented inline.**

Properties like atomicity, fallback behavior, lifecycle expectations, and threading rules belong in the code, not in a separate document.

```cpp
/**
 * LIFECYCLE GUARD: Atomic Counter Prevents Mid-Transaction State Mutation
 *
 * Purpose: Prevent SetActiveCapabilities() from being called while a
 * transaction is executing, which would create a race between the transaction
 * checking capabilities and the host changing them mid-flight.
 *
 * Mechanism: transactions_in_flight_ is incremented before payload execution
 * and decremented in a RAII destructor. SetActiveCapabilities() checks this
 * counter and returns false if any transaction is in flight.
 *
 * Memory ordering: memory_order_acquire on load (SetActiveCapabilities check),
 * memory_order_release on increment/decrement (transaction guard). This ensures
 * visibility without unnecessary barriers.
 *
 * Trade-off: SetActiveCapabilities becomes blocking on busy systems.
 * A production implementation might defer capability changes to the next
 * transaction boundary instead of failing.
 */
std::atomic<uint32_t> transactions_in_flight_{0};

[[nodiscard]] bool SetActiveCapabilities(const CapabilityMask256& mask) noexcept {
    if (transactions_in_flight_.load(std::memory_order_acquire) > 0) {
        return false;  // Atomic guard prevents mid-flight capability changes
    }
    active_host_capabilities_ = mask;
    return true;
}
```

---

## Part 2. Rewriting rules

Rewriting preserves behavior while restructuring for clarity. The rules ensure transformation is surgical, not wholesale.

### R1. Rename Without Changing Behavior

Change the name to match the implementation. If the implementation is wrong, fix it in a separate rewrite pass, and document the fix.

**Example:**

```cpp
// Step 1: Rename (rewriting pass 1)
// OLD: class SlidingWindowRing { ... }
// NEW: class TokenBucketCounter { ... }  // More accurate name

// Step 2: Fix Implementation (rewriting pass 2, separate commit)
// OLD: uint64_t counter_ = 0;  // Increments forever
// NEW: Implement actual sliding window with time windows
```

### R2. Preserve Existing Call Sites

When restructuring, ensure all existing callers continue to work without modification. If this is impossible, it's not a beautification; it's a redesign.

**Example: SetActiveCapabilities Signature Change**

```cpp
// BEFORE: void SetActiveCapabilities(...)
// AFTER: [[nodiscard]] bool SetActiveCapabilities(...)

// All call sites must be updated to CHECK the return value
// This is a signature change, so it's documented in a separate pass
// and merged after all call sites are verified.
```

### R3. Add Guards Without Changing Logic

Add lifecycle guards (atomic counters, RAII destructors) around existing logic. The guard wraps the logic; it doesn't replace it.

```cpp
// BEFORE
auto result = g_host->ExecuteGovernedTransaction(...);
return result.has_value() ? 0 : -3;

// AFTER (with lifecycle guard)
transactions_in_flight_.fetch_add(1, std::memory_order_release);
struct TransactionGuard {
    std::atomic<uint32_t>& counter;
    ~TransactionGuard() noexcept {
        counter.fetch_sub(1, std::memory_order_release);
    }
} lifecycle_guard{transactions_in_flight_};

// ... existing logic unchanged ...

auto result = g_host->ExecuteGovernedTransaction(...);
return result.has_value() ? 0 : -3;
```

### R4. Fix Namespace References Systematically

Rename all tack_ files to stack_ and update all namespace declarations in one pass. Use grep, sed, and verify with compilation.

```bash
# Step 1: Rename files
git mv cpp/include/tack_kernel.hpp cpp/include/stack_kernel.hpp
git mv cpp/include/tack_kinetic_governor.hpp cpp/include/stack_kinetic_governor.hpp

# Step 2: Update includes and namespaces
sed -i 's/#include "tack_/#include "stack_/g' **/*.cpp **/*.hpp
sed -i 's/using namespace tack;/using namespace stack;/g' **/*.cpp

# Step 3: Verify with compilation
cmake . && cmake --build .

# Step 4: One commit per step (tack_kernel.hpp rename, tack_kinetic_governor.hpp rename, ..., using namespace changes)
```

### R5. Document Defects Without Fixing Them (First Pass)

On the first rewriting pass, document defects in comments and structural tests. Don't fix them yet. This makes the defects visible and falsifiable.

**Example: Layer 5 (Audit) Silent Defect**

```cpp
/**
 * ARCHITECTURAL DEFECT: Audit Ring Push Never Called
 *
 * The audit ring is initialized and available, but Layer 4 (orchestration)
 * never calls Push() to record governance events. The audit trail is silent.
 *
 * Why: Layer 4 orchestrates six gates but doesn't have a call path to audit.
 * The audit ring exists (Layer 5) but is disconnected from the execution flow.
 *
 * Impact: MEDIUM. No visibility into governance decisions at runtime.
 * Silent defect: code compiles, tests pass, but governance is not recorded.
 *
 * Fix: (deferred to defect-fixing phase)
 * Layer 4 must call g_audit_ring.Push() after each transaction completes.
 */
class SeccompAuditRing {
public:
    void Push(AuditEventType event_type, uint64_t context_id, uint32_t tokens) noexcept {
        // This method exists and is correct.
        // But Layer 4 never calls it. (DEFECT)
        // ...
    }
};
```

### R6. Validate Architectural Boundaries

When rewriting, verify that each layer's contract is enforced:

- **Layer 1**: Always returns > 0 or throws (never silent zero)
- **Layer 2**: Signal handler sets flag; preemption is checked before payload returns
- **Layer 3**: Token consumption is atomic relative to deadline checks
- **Layer 4**: All six gates execute in order before payload runs
- **Layer 5**: Every transaction that passes Layer 4 is recorded
- **Layer 6**: Arena allocations are guarded; Reset() fails if allocations in flight

```cpp
// Validation test: Verify layer boundaries are enforced
TEST_CASE("Layer Integration: Six-Layer End-to-End Flow") {
    uint64_t baseline = HardwareClock::ReadTicks();
    REQUIRE(baseline > 0);  // Layer 1: never silent zero

    REQUIRE(HardenedPosixPreemptionGuard::RegisterSignalHandler().has_value());
    // Layer 2: signal handler registered

    KineticGovernor<> gov;
    // Layer 3: rate limiter available

    GovernedMinotaurHost<> host;
    REQUIRE(host.SetActiveCapabilities(...));  // Layer 4: capabilities set
    
    SeccompAuditRing<> audit;
    // Layer 5: audit ring available

    StaticArenaBuffer<> arena;
    // Layer 6: arena available

    // All six layers coordinated in one transaction
    auto result = host.ExecuteGovernedTransaction(...);
    REQUIRE(result.has_value());
}
```

---


### R7. Behavior-Preservation Gate (Hard)

**No beautification or fix commit merges without a green automated suite.**

| Gate | Requirement |
|------|-------------|
| Unit / integration suite | Pass count ≥ baseline; zero new failures |
| Invariant tests | Authority / safety invariants still pass |
| Multi-seed / property checks (if present) | Documented targets still met |
| Before/after | Record test counts in the commit message |

If the suite cannot protect invariants, **add tests before** changing behavior.

### R8. Scope Control (Critical Path Default)

Default beautification scope is the **critical path**, not the entire repository.

1. Identify the invariant-bearing spine (e.g. authority → proposal → apply → detection).
2. Beautify and audit that spine first.
3. Expand outward only after a durable `WARDEN_AUDIT.md` exists for the spine.

### R9. Durable Defect IDs

Every defect gets a stable ID in a single source of truth (e.g. `WARDEN_AUDIT.md`):

- Format: `C1`, `H1`, `M1`, `L1` (Critical / High / Medium / Low).
- IDs **never reuse** meanings once published.
- Every fix commit **must cite** the ID(s): `Fix H2: introduce OPERATOR_APPROVED`.
- Audit status: Open → Fixed (commit SHA).

### R10. Re-Anchor Mutation Sites, Never Weaken Them

When a split or rename moves code that a mutation suite targets by exact text:

1. Re-point each moved site to its new text with the **same** mutation. Never delete a mutant to make a move pass.
2. A moved line must still match **exactly once**. If its new indentation makes it a substring of another site, make it unique (an inline comment is enough) rather than loosening the anchor.
3. Run every mutant suite that touches the changed file, not only the obvious one. Every mutant must still be killed.
4. Split along seams the code already has: a collection loop, one builder per kind of output, a verification step. Keep check order identical.

### R11. Documentation Moves With Behavior

A commit that changes what a repository does changes what its README says, **in the same pull request**.

1. Before merge, run the repository's own self-check on itself (`warden critic .`, `ghost-buster .`, `verify_manifest.py`) and record the result.
2. State counts in a form the self-check verifies ("24 tests exist"), not in prose it cannot read ("15 passed").
3. A live run that proves something gets a row in the repository's registry or audit file; the README points to it rather than asserting it.

---

## Part 3. Defect priority

| Priority | Meaning |
|----------|---------|
| **CRITICAL** | Breaks containment or a safety invariant immediately |
| **HIGH** | Enables bypass, an audit that lies, or a race on the critical path |
| **MEDIUM** | Orchestration gaps, policy defects, gradual escape |
| **LOW** | Noise, environment-sensitive thresholds, cosmetic mismatch |

## Part 4. The commit template for a fix

```text
Fix <ID>: <one-line summary>

WARDEN:
  Defect: <ID> (<priority>)
  Layer/spine: <component>
  Red team: <attack> -> <result>

TESTS:
  Run: <n>  Pass: <n>  Fail: 0
```

## Part 5. Where the original lives

The version history of the rules is in the Reporting repository's
`Elegant.md` (v1.0 on 2026-10-01, v1.1 on 2026-10-02, v1.2 on 2026-10-07).
Because the rules now live with the code that applies them, this file is the
working copy and `Elegant.md` points here.
