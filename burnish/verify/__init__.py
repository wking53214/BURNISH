"""Claims verification, in stages kept apart so each can be read, tested and replaced alone.

The stages, in order:

  1. extraction (`sentences`): the README becomes pieces of prose, each with the line it came from and whether it is a
     heading, a table cell or a blockquote. Code, HTML comments and Burnish's own block are gone before this.
  2. identification (`identify`): a piece that states a claim of a known shape becomes a claim object. A piece that is
     history, a wish, a quotation or a denial of the shape is not a claim.
  3. normalization (`identify`): the claim's subject, scope and polarity are written in one form ("every command runs
     without warden"), whatever words the README used.
  4. comparison (`evidence`): the tree is read for what could back or contradict the claim, and what could not be read
     is recorded with it.
  5. verdict (`verdict`, `judge`): one of six states, with the trail of states that led to it.
  6. presentation: the critic prints the verdict with its provenance. Nothing in this package prints.

The six states are `burnish.verify.verdict.State`. Absence of evidence is never falsity: a verdict of
EVIDENCE_CONTRADICTS needs evidence that was read, and the `Verdict` type refuses one without it.

WHAT IT DOES NOT OWN
    Running anything. The evidence is what the tree declares and what its files say when parsed, never what a run did.
"""
