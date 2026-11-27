"""Verdict: a requirement claim against the reading of the tree.

The rules, for a package P:

  * "every command needs P" (or the program stops without it): a route that loads P when the program starts supports it.
    No such route, a complete reading and no deferred route contradict it: the program starts without importing P.
  * "every command runs without P" (also "every command but one part"): a route that loads P at start contradicts it. No
    such route, a complete reading and no deferred route support it.
  * "only one part needs P": a route that loads P at start contradicts it (every command needs it). No such route, a
    complete reading, no deferred route and at least one guarded route support it.
  * anything else, a "part" scope, or an incomplete reading: EVIDENCE_INSUFFICIENT or NOT_CHECKED, never a contradiction.

A contradiction here rests on reading the code, not on running it, so its basis is "inferred", and its provenance lists
what a reading of files cannot see.

WHAT IT DOES NOT OWN
    Reading the README or the tree. It compares what `identify` and `evidence` found.
"""

from __future__ import annotations

from ..provenance import Basis, Provenance, Source
from .evidence import Reading
from .identify import RequirementClaim
from .verdict import State, Verdict

__all__ = ["judge_requirement", "METHOD"]

METHOD = ("Read pyproject.toml for the runtime and optional dependencies and the entry points, then followed the imports of "
          "the project's own modules from each entry point as Python would when the program starts, sorting every route "
          "to the package into: loaded at start, behind a guard that expects the import to fail, or inside a function "
          "with no guard.")
_NOT_INSPECTED = ("modules loaded by a plugin system, a subprocess or a path built at run time",
                  "whether the function that holds a deferred import runs on every use",
                  "test files, docs and exemplars: they are not part of the program")


def judge_requirement(claim: RequirementClaim, reading: Reading) -> Verdict:
    """The verdict for one requirement claim."""
    routes = reading.routes.get(claim.package, [])
    load = [r for r in routes if r.kind == "load"]
    deferred = [r for r in routes if r.kind == "deferred"]
    guarded = [r for r in routes if r.kind == "guarded"]
    evidence: list[Source] = [entry for _, entry in reading.entries]
    declared = reading.declared(claim.package)
    if declared is not None:
        evidence.append(declared)
    evidence += [r.at for r in load + guarded + deferred][:6]
    evidence += reading.dynamic[:3]
    evidence += [Source(path, 0, "could not be parsed") for path in reading.unread[:3]]

    basis: Basis = "inferred" if evidence else "none"

    def done(state: State, reason: str) -> Verdict:
        return Verdict(state, Provenance(
            claim=f'"{claim.words}" (read as: {claim.normal})', claim_at=Source("README", claim.line),
            evidence=tuple(evidence), method=METHOD, basis=basis, not_inspected=_NOT_INSPECTED, reason=reason))

    if claim.scope == "part":
        return done(State.NOT_CHECKED, f"The claim is about one part ({claim.part or 'unnamed'}) and says nothing about the "
                    "rest; parts are not mapped to the code, so it was not checked.")
    if not reading.readable or not reading.entries:
        return done(State.EVIDENCE_INSUFFICIENT, "There is no readable pyproject.toml or no entry point to start from, so "
                    "nothing shows what the program loads.")
    gaps = _gaps(reading, deferred)
    if load:
        where = load[0].at.render()
        if claim.needs and claim.scope == "every":
            return done(State.EVIDENCE_SUPPORTS, f"The program imports {claim.package} when it starts ({where}).")
        return done(State.EVIDENCE_CONTRADICTS, f"The program imports {claim.package} when it starts ({where}), so every "
                    f"command needs it; the README says {'only one part does' if claim.needs else 'it runs without it'}.")
    if gaps:
        return done(State.EVIDENCE_INSUFFICIENT, f"Nothing imports {claim.package} when the program starts, but {gaps}, "
                    "so the reading does not settle the claim.")
    if claim.needs and claim.scope == "every":
        how = (f"; it is reached only behind a guard that expects it to be missing ({guarded[0].at.render()})" if guarded
               else "; nothing on any route from an entry point imports it")
        return done(State.EVIDENCE_CONTRADICTS, f"The program starts without importing {claim.package}{how}. The README "
                    "says every command needs it.")
    if claim.needs:   # only one part needs it
        if not guarded:
            return done(State.EVIDENCE_INSUFFICIENT, f"Nothing on any route from an entry point imports {claim.package}, "
                        "so nothing shows the part named needs it.")
        return done(State.EVIDENCE_SUPPORTS, f"The program starts without importing {claim.package}, and reaches it only "
                    f"behind a guard ({guarded[0].at.render()}).")
    return done(State.EVIDENCE_SUPPORTS, f"The program starts without importing {claim.package}"
                + (f"; it is reached only behind a guard ({guarded[0].at.render()})." if guarded else "."))


def _gaps(reading: Reading, deferred: list) -> str:
    """What keeps the reading from settling a claim: a deferred route, an import by name, a file that did not parse."""
    gaps = []
    if deferred:
        gaps.append(f"an unguarded import inside a function reaches it ({deferred[0].at.render()})")
    if reading.dynamic:
        gaps.append(f"a module on a route imports by name ({reading.dynamic[0].render()})")
    if reading.unread:
        gaps.append(f"{reading.unread[0]} could not be parsed")
    return " and ".join(gaps)
