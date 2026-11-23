"""The DRAFT stamp of a package (boilerplate).

A development package may take verdicts that are not the owner's review (for example the shipped
verdicts, before the owner's ban lists exist). Such a package stamps its ban.yaml: every verdict whose
reason or evidence starts with DRAFT_MARKER is a draft verdict, and one draft verdict makes the whole
package a draft (fail safe). dataset.yaml's description or version may carry the marker too.

The engine never names a package: it reads the marker. A run of a draft package is stamped DRAFT in its
run record, its manifest config and its verdict, and the headline-table builder refuses it, so nothing a
draft package produces can enter a headline table.
"""

from dataclasses import dataclass
from typing import Any, Tuple

DRAFT_MARKER = "DRAFT --"
DRAFT_RULE = "G-DRAFT"


@dataclass(frozen=True)
class DraftStatus:
    """Whether a package is a draft, and why."""
    is_draft: bool
    stamped_verdicts: int
    stamp: str
    where: Tuple[str, ...]

    def record(self) -> dict:
        return {"is_draft": self.is_draft, "stamped_verdicts": self.stamped_verdicts,
                "stamp": self.stamp, "where": list(self.where)}


def _stamp_of(text: Any) -> str:
    if isinstance(text, str) and text.lstrip().startswith(DRAFT_MARKER):
        return text.lstrip().split("|", 1)[0].strip()
    return ""


def draft_status(package: Any) -> DraftStatus:
    """Read the DRAFT stamp of a loaded package (treeroute.package.load.LoadedPackage)."""
    where = []
    stamp = ""
    n = 0
    for column, v in sorted(package.ban.verdicts.items()):
        s = _stamp_of(getattr(v, "evidence", None)) or _stamp_of(getattr(v, "reason", None))
        if s:
            n += 1
            stamp = stamp or s
    if n:
        where.append("ban.yaml (%d verdicts)" % n)
    for field in ("description", "version"):
        text = getattr(package.dataset, field, "")
        if isinstance(text, str) and DRAFT_MARKER in text:
            where.append("dataset.yaml %s" % field)
            if not stamp:
                start = text.index(DRAFT_MARKER)
                stamp = text[start:].split(".", 1)[0].strip()
    return DraftStatus(is_draft=bool(where), stamped_verdicts=n, stamp=stamp, where=tuple(where))


__all__ = ["DRAFT_MARKER", "DRAFT_RULE", "DraftStatus", "draft_status"]
