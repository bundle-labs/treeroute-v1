"""R9: the epoch a 'freeze' column is held at."""

from typing import Sequence

from .shapes import TimingRefusal, as_int


# Provenance: plan 2.1 R9; plan 1.4 (freeze: the epoch is computed); defo_ban.py:14-15, 76
# ("usable only as ONE pre-window epoch").
def freeze_epoch(content_epochs: Sequence[int], cut_day: int) -> int:
    """The epoch a 'freeze' column is held at: its last content epoch at or before the cut.

    Rule: R9. Among the column's content epochs (content time, never release dates), the latest one
    at or before the cut (inclusive, D19). D27: the caller passes each cut in use (a lead's fit cut,
    and its inner guard's own cut), so no value observed after a cut enters the fit at that cut.

    Refuses: no epoch at or before the cut (the column cannot be frozen; it must be banned).
    """
    cut = as_int(cut_day, "cut_day")
    epochs = [as_int(e, "content epoch") for e in content_epochs]
    eligible = [e for e in epochs if e <= cut]
    if not eligible:
        raise TimingRefusal("R9", "no content epoch at or before the cut day %d (%d epochs, the "
                            "earliest %s)" % (cut, len(epochs), min(epochs) if epochs else "none"),
                            fix="the column cannot be frozen at this cut: ban it (plan 1.4)")
    return max(eligible)
