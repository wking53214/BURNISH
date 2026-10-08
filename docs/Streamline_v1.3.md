# Burnish v1.3

Moved here from the Reporting repository, where it was drafted as Elegant.md v1.3. Author: William N. King.

## What changed

1. **Split of responsibilities.**
   - Warden is now only the governor of change. It owns the human grant, the green-suite gate (Rule 7), the audit file (Rule 9), the SWIZZLE proof gate, and the tag-team loop.
   - The craft, meaning what "better" looks like, moved to this repository, Burnish.
   - Burnish depends on Warden. Warden never depends on Burnish, and a test enforces that.

2. **Where the criteria live now.**
   - The principles (naming as truth, narrative documentation, architectural properties as comments) and rewriting rules R1 to R11 are in Burnish's criteria table, with their full text restored from the earlier versions.
   - R5, R7 and R9 are owned by Warden. The rest are Burnish's.
   - Burnish adds per-language guides for Python, Rust and C++23, and 11 craft practices.
   - Each criterion is marked as enforced, written down only, or not implemented. Today only the Python rules and the README rules are enforced.

3. **README writing.**
   - Only Burnish writes READMEs. It also holds the README standard (minimum, strong, over the top) and a blunt critic.
   - ghost_tools, SWIZZLE, Warden and ASSAY no longer write them. ghost_tools still detects README lies. SWIZZLE now treats any README edit by Ghost as a violation.

4. **Honest status.**
   - The Burnish-as-craft loop has not been run on a real repository, so it is not proven.
   - Rust and C++23 are written down but not checked by Burnish.
   - The four sibling READMEs fail Burnish's minimum.

5. **Version note.** Elegant.md v1.2 had cut the criteria text to headings. This version points to Burnish for the full text.
