"""Making text that came from outside safe to print into a README.

Detector names, finding ids, summaries and reasons come from other programs
(Ghost Tools, Warden, a test run). They are data. Written into a Markdown file
unchanged, a string with a line break and a heading in it becomes a heading, a
fake section, or a closing marker for Burnish's own generated block.

`clean` makes one such string into one harmless line:

  * every control character is dropped and all white space (newlines too) is
    collapsed to single spaces,
  * a leading Markdown marker (a heading, quote, list bullet, numbered item,
    table bar or rule) is escaped with a backslash,
  * backticks, pipes, brackets and angle brackets are escaped, so nothing can
    open code, a table, a link or an HTML comment,
  * em and en dashes are replaced, and
  * the result is cut to `limit` characters (200 by default).
"""

from __future__ import annotations

import re
import unicodedata

__all__ = ["clean", "LIMIT"]

LIMIT = 200

_SPACE = re.compile(r"\s+")
_LEADING = re.compile(r"^(?:(\d+)([.)])|(#|>|-|\*|\+|=|~|_))")
_ESCAPED = {"`": "\\`", "|": "\\|", "<": "&lt;", ">": "&gt;", "[": "\\[", "]": "\\]"}


def clean(value: object, limit: int = LIMIT) -> str:
    """`value` as one safe line of at most `limit` characters."""
    text = value if isinstance(value, str) else str(value)
    text = "".join(" " if ch in "  " or ch.isspace() else ch
                   for ch in text if ch.isspace() or unicodedata.category(ch) not in {"Cc", "Cf", "Cs", "Co", "Cn"})
    text = _SPACE.sub(" ", text).strip().replace("—", "-").replace("–", "-")
    text = text.replace("\\", "\\\\")
    text = "".join(_ESCAPED.get(ch, ch) for ch in text)
    text = _LEADING.sub(lambda m: f"{m.group(1)}\\{m.group(2)}" if m.group(1) else "\\" + m.group(3), text)
    if len(text) > limit:
        text = text[: max(limit - 3, 0)].rstrip("\\ ") + "..."
    return text[:limit]
