"""treeroute.timing: forward reach, the reference instant, computed lags (R8), both cuts per lead in
steps or days (R11) and freeze epochs (R9). SCIENCE: owner-approved signatures, agent bodies.

Module-wide convention (D19, approved): content and periods are CLOSED intervals of whole days
(first_day, last_day) as Day ordinals, and 'at or before' is inclusive. Every lag follows CONTENT time
only; release and snapshot dates are never read here (Q2).

Pure functions: no file, no global state, no draw. A rule that cannot give a value raises
TimingRefusal (a RefusedError) naming the rule, the column and the fix.
"""

from .aggregate import aggregate_content_interval, aggregate_reach, aggregate_window, periods_inside
from .calendar import (REFERENCE_FIRST_YEAR, REFERENCE_YEARS, CadenceGrid, describe_reference_period,
                       reference_periods, target_grid)
from .content import (content_interval, forward_reach_days, max_forward_reach_days, reference_day,
                      target_content, target_reach_offset_steps)
from .cuts import (cuts_for_leads, event_fit_cut_day, event_guard_cut_day, fit_cut_step,
                   guard_cut_step, label_usable, latest_label_step, year_last_step)
from .freeze import freeze_epoch
from .lags import compute_lag, lag_trace
from .shapes import AggregateReach, CutPair, Lag, LagTrace, Reach, TimingRefusal

__all__ = [
    # approved signatures
    "content_interval", "forward_reach_days", "reference_day", "compute_lag", "fit_cut_step",
    "guard_cut_step", "latest_label_step", "event_fit_cut_day", "event_guard_cut_day",
    "label_usable", "cuts_for_leads", "freeze_epoch",
    # helpers that carry an approved decision (D21, D12, D28) or derived.json's inputs (R8)
    "max_forward_reach_days", "target_content", "target_reach_offset_steps", "year_last_step",
    "lag_trace",
    # the content of a time aggregate (plan 1.5 aggregate_time: window computed from the span)
    "periods_inside", "aggregate_content_interval", "aggregate_reach", "aggregate_window",
    # shapes and calendar
    "Lag", "CutPair", "LagTrace", "AggregateReach", "Reach", "TimingRefusal", "CadenceGrid",
    "reference_periods", "target_grid", "describe_reference_period", "REFERENCE_FIRST_YEAR",
    "REFERENCE_YEARS",
]
