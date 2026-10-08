# README standard

What a README must do, what makes it strong, and what makes it over the top.
`burnish readme-critic` applies every rule below and is blunt about the
result. The rules are code (`burnish/readme_critic.py`); a test fails if
this page and that table disagree.

## Where the rules come from

Read on 2026-10-08:

- [Standard Readme specification](https://github.com/RichardLitt/standard-readme/blob/main/spec.md): required sections, their order, and rules for each.
- [GitHub, About READMEs](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes): what a README covers, where GitHub looks for it, the 500 KiB cut-off, relative links, the generated outline.
- [The Art of README](https://github.com/hackergrrl/art-of-readme/blob/master/README.md): be brief, a one-liner, show usage early, "cognitive funneling", be objective.
- [Make a README](https://www.makeareadme.com/): the usual sections, visuals, project status, "length is less of a concern than missing information".
- [awesome-readme](https://github.com/matiassingers/awesome-readme): what the examples have in common (visual demos, navigation, informative badges, architecture diagrams with invariants and design decisions).

A web search for more "great README" guides returned only blog posts and AI
skill pages, which were not used.

## Three tiers

**Minimum.** What a reader needs to decide, install and use the project. A
failure here means the README does not do its job.

| ID | Rule | The critic says when it fails | Source |
|----|------|-------------------------------|--------|
| `RM-TITLE` | Title | It does not open with a title. | Standard Readme spec |
| `RM-ONELINER` | One-line description | It never says what the project is in one plain sentence. | Standard Readme spec; Art of README |
| `RM-INSTALL` | Install, with a command | A reader cannot get this running. | Standard Readme spec; Make a README |
| `RM-USAGE` | Usage, with a code block | A reader cannot tell how to use it. | Standard Readme spec; Art of README |
| `RM-LICENSE` | License, named | A reader cannot tell whether they may use it. | Standard Readme spec; Make a README |
| `RM-LINKS` | No broken relative links | It points at files that are not there. | Standard Readme spec; GitHub, About READMEs |
| `RM-SIZE` | Under GitHub's size limit | GitHub will cut it off. | GitHub, About READMEs |
| `RM-CONTRIB` | Contributing, with a stance | Nobody can tell if help is wanted. | Standard Readme spec; Make a README |
| `RM-LIMITS` | Says what it will not do | It reads as a brochure: no limits are admitted. | Art of README (be objective) |

**Strong.** What separates a competent README from a forgettable one.

| ID | Rule | The critic says when it fails | Source |
|----|------|-------------------------------|--------|
| `RM-STATUS` | Project status | A reader cannot tell whether this is alive. | Make a README |
| `RM-SUPPORT` | Where to get help | A stuck reader has nowhere to go. | Make a README |
| `RM-TOC` | Navigation for a long README | It is long and offers no way through. | Standard Readme spec; GitHub, About READMEs |
| `RM-FENCES` | Code blocks name their language | Code is shown unhighlighted. | Standard Readme spec |
| `RM-EXAMPLES` | Runnable examples | No example a reader can run. | Art of README |

**Over the top.** What the best READMEs add: a picture of the thing, a way in
within one screen, evidence that the claims are true, and an honest account of
what it will not do.

| ID | Rule | The critic says when it fails | Source |
|----|------|-------------------------------|--------|
| `OT-QUICKLINKS` | A way in within one screen | There is no way to jump to what you came for. | awesome-readme examples |
| `OT-VISUAL` | A picture of the thing | There is nothing to look at. | awesome-readme examples; Make a README |
| `OT-DEMO` | A demo with its output | It never shows the result. | awesome-readme examples; Make a README |
| `OT-BADGES` | Badges that carry information | No badge tells the reader anything. | Make a README; Art of README |
| `OT-ARCH` | Architecture with invariants | A contributor cannot see how it fits together. | awesome-readme examples |
| `OT-EVIDENCE` | Claims come with their evidence | It asks to be believed. | Burnish synthesis of awesome-readme examples |
| `OT-FAQ` | A FAQ | The obvious questions go unanswered. | awesome-readme examples |
| `OT-ALTERNATIVES` | Compared with the alternatives | It does not say why this and not something else. | Make a README; Art of README |
| `OT-ROADMAP` | A roadmap | It does not say where it is going. | Make a README |
| `OT-DECISIONS` | Design decisions linked | The reasoning behind the design is not written down. | awesome-readme examples |

## Where the sources disagree

- **License position.** Standard Readme says the License section is last. The Art
  of README says to put the license high, because readers leave over an
  incompatible one. The rule here is that a License section exists and names a
  license (`RM-LICENSE`); a license badge near the top (`OT-BADGES`) satisfies
  the Art of README without moving the section.
- **Length.** The Art of README says be brief. Make a README says length matters
  less than missing information. The rule here is that a long README needs a way
  through it (`RM-TOC`, `OT-QUICKLINKS`), not that it be short.
- **Description format.** Standard Readme wants a plain line under 120 characters
  that is not a quote block (`RM-ONELINER`).

## Honesty about the over-the-top tier

The minimum and strong tiers are drawn from the sources above. The
over-the-top tier is a **synthesis**: awesome-readme shows what excellent
READMEs share, but no source states it as a standard. Treat it as Burnish's
own bar, set high on purpose.

## What the critic cannot judge

It reads the README and the local files it links to. It does not fetch URLs, so
it cannot tell a dead external link or a stale badge. It cannot tell whether an
image is any good, or whether prose is clear. It matches section titles by
keyword, so an unusual title can hide a real section. It gives no score,
because a number would hide which rule failed.

## The critic's verdicts

| Situation | Verdict |
|-----------|---------|
| Any minimum rule fails | "This README fails the minimum." |
| Minimum met, strong gaps remain | "It meets the minimum and nothing more." |
| Strong met, over-the-top gaps remain | "Solid." with the count |
| Every rule holds | "Over the top." |

`burnish readme-critic PATH --tier minimum|strong|over-the-top` exits 1 when
the README is below the tier asked for.
