# Human review of the README side, 2026-11-26

Item 33 of the remediation plan. Reviewer: William N. King, on 2026-11-26, in a review sheet that listed, for each
question, what Burnish 0.5.3 said and what the AI reviewer (Claude) said, with a link to the README lines at the commit
in `SELECTION.md`. "Agree" means the reviewer agrees with the AI reviewer's answer.

The reviewer does not read Python, so this covers the README side only: the claims critic and the brochure rule. The
`check` sample in `CHECK_SAMPLE.md` has not been reviewed by a person.

| # | Repository | Question | Burnish said | AI reviewer said | Human verdict |
|---|---|---|---|---|---|
| 1 | typing_extensions | Does the README state a test count, a pin, a "no dependencies" claim or one of the five absolutes? | none found | none found | Agree |
| 2 | typing_extensions | Does it read like an ad that admits no limits? | no | no | Agree |
| 3 | idna | Does the README state a test count, a pin, a "no dependencies" claim or one of the five absolutes? | none found | none found | Agree |
| 4 | idna | Does it read like an ad that admits no limits? | yes (install line, no "does not") | no: it admits limits (lines 125 and 128) | Agree |
| 5 | urllib3 | Line 30, "100% test coverage.": is it one of the five absolutes, so the critic should have caught it? | missed (read since 0.5.6) | yes; probably true, CI requires 100% | Agree |
| 6 | urllib3 | Apart from line 30, any claim of those kinds? | none found | none found | Agree |
| 7 | urllib3 | Does it read like an ad that admits no limits? | yes ("powerful") | yes | Agree |
| 8 | charset_normalizer | Does the README state a test count, a pin, a "no dependencies" claim or one of the five absolutes? | none found | none found | Agree |
| 9 | charset_normalizer | Does it read like an ad that admits no limits? | no | no: it has a Known limitations section | Agree |
| 10 | requests | Does the README state a test count, a pin, a "no dependencies" claim or one of the five absolutes? | none found | none found | Agree |
| 11 | requests | Does it read like an ad that admits no limits? | yes (install line, no "does not") | yes | Agree |
| 12 | idna | Line 115, Python 3.10 and higher, against `requires-python = ">=3.10"`: do they match? | not read | yes | Agree |
| 13 | requests | Line 38, Python 3.10+, against `requires-python = ">=3.10"`: do they match? | not read | yes | Agree |
| 14 | charset_normalizer | Lines 216 to 218, unsupported and older Pythons, against `requires-python = ">=3.7"`: do they agree? | not read | yes | Agree |

**Result.** The reviewer agreed with all 14 of the AI reviewer's answers. Against the human verdicts, the claims critic in
this run had one miss (row 5) and no wrongly flagged claim; the brochure rule fired three times and was right twice
(rows 7 and 11) and wrong once (row 4).
