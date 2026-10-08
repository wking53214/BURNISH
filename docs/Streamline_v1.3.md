# Streamline v1.3

Moved here from the Reporting repository, where it was drafted as Elegant.md v1.3. Author: William N. King.

## What changed

1. **Split of responsibilities.**
   - Elegant is now only the governor of change. It owns the human grant, the green-suite gate (Rule 7), the audit file (Rule 9), the SWIZZLE proof gate, and the tag-team loop.
   - The craft, meaning what "better" looks like, moved to this repository, Streamline.
   - Streamline depends on Elegant. Elegant never depends on Streamline, and a test enforces that.

2. **Where the criteria live now.**
   - The principles (naming as truth, narrative documentation, architectural properties as comments) and rewriting rules R1 to R11 are in Streamline's criteria table, with their full text restored from the earlier versions.
   - R5, R7 and R9 are owned by Elegant. The rest are Streamline's.
   - Streamline adds per-language guides for Python, Rust and C++23, and 11 craft practices.
   - Each criterion is marked as enforced, written down only, or not implemented. Today only the Python rules and the README rules are enforced.

3. **README writing.**
   - Only Streamline writes READMEs. It also holds the README standard (minimum, strong, over the top) and a blunt critic.
   - ghost_tools, SWIZZLE, Elegant and TOUCHSTONE no longer write them. ghost_tools still detects README lies. SWIZZLE now treats any README edit by Ghost as a violation.

4. **Honest status.**
   - The Streamline-as-craft loop has not been run on a real repository, so it is not proven.
   - Rust and C++23 are written down but not checked by Streamline.
   - The four sibling READMEs fail Streamline's minimum.

5. **Version note.** Elegant.md v1.2 had cut the criteria text to headings. This version points to Streamline for the full text.
