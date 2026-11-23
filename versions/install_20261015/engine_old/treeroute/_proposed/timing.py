"""PROPOSED signatures: treeroute/timing/ (plan 4.2). SCIENCE: owner signatures, agent bodies.

Forward reach, the reference instant, computed lags (R8), both cuts per lead in steps or days (R11)
and freeze epochs (R9). Every lag follows CONTENT time only: release and snapshot dates are
recorded and printed but never used here (Q2).

Calendar convention proposed for every function in this module:
    content and periods are CLOSED intervals of whole days (first_day, last_day), as Day ordinals;
    'at or before' is inclusive (a content last_day equal to the reference day is allowed).
It governs the R8 lags, the R9 freeze epochs and the R11 cuts and label rule.

Module-wide.  Rule: R8, R9, R11.  Needed: Tue 29 Sep (derive v1).
OWNER DECISION: approve whole-day closed intervals as the time resolution of every timing rule,
    with 'at or before' inclusive (the alternative is a finer resolution or an exclusive bound;
    either changes which content counts as known at a reference instant).
"""
# Provenance for the module: pm25_forecast.py:22-27, 190-197; pm25_architecture.py:139-160.
# NOT time_aware.py:36-43, 145-191 (its calibration rule is not ported, plan 4.2 NOT PORTED).
from __future__ import annotations

from typing import Mapping, Optional, Sequence, Tuple

from .common import (Cadence, ColumnFacts, CutPair, Day, LeadPlan, Lag, ReferenceKind, Step,
                     TargetFacts, Windows)


# Provenance: plan 1.3 (window fact, align unknown + max_length signed 'assumed').
def content_interval(column: ColumnFacts, period: Tuple[Day, Day]) -> Tuple[Day, Day]:
    """First and last day of content that a value stored for one period actually describes.

    Rule: R8 (input).  Needed: Tue 29 Sep (derive v1).

    Contract (plan 1.3, 2.1 R8):
        The stamp fact places the value's time inside its stored period (period_start,
        period_centre, period_end or event_date). The window fact (length, unit, align) spans
        content around that instant: backward ends at the stamp, centred straddles it, forward
        starts at it. The result is content time only.
    Inputs:
        column: the column's facts (stamp, window, cadence).
        period: first and last day of the stored row's own period.
    Returns:
        (first_day, last_day) of the content.
    Refuses:
        - align=UNKNOWN without max_length (plan 1.3: with no bound the column is refused at lag 0).
        - align=UNKNOWN with max_length whose fact_status is not ASSUMED (the bound must be signed).
        - a window with no length on a time-varying column.
    OWNER DECISION: for align=UNKNOWN with a signed max_length w, take the worst case, a FORWARD
        window of length w starting at the stamp (plan says only "R8 then lags by the bound").
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 1.4 (keep_unreviewed needs no forward reach), plan 5 G-LAG.
def forward_reach_days(column: ColumnFacts, period: Tuple[Day, Day]) -> int:
    """How many days a column's content reaches past the end of its own stored period.

    Rule: R8, G-LAG, A5.  Needed: Tue 29 Sep (derive v1).

    Contract (plan 1.4, 5):
        forward reach = content last_day minus period last_day, from content_interval. Positive
        means the value describes time after its own period (a centred index does). keep_unreviewed
        is allowed only with no forward reach; G-LAG refuses forward reach at lag 0.
    Inputs:
        column: the column's facts.
        period: first and last day of the stored row's period.
    Returns:
        days of forward reach (0 or negative means none).
    Refuses:
        - whatever content_interval refuses.
    OWNER DECISION: forward reach is measured on every period the column has in the data and the
        MAXIMUM is reported (centred windows and uneven month lengths vary by period).
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.1 R8.
def reference_day(target: TargetFacts, row_period: Tuple[Day, Day], kind: ReferenceKind,
                  issue_period: Optional[Tuple[Day, Day]] = None) -> Day:
    """The instant a feature row must not look past: end of the target's own window (nowcast) or end
    of the issue step (lead L).

    Rule: R8.  Needed: Tue 29 Sep (derive v1).

    Contract (plan 2.1 R8):
        NOWCAST: the END of the target's own window for that row (the composite window when it
        reaches past its step). ISSUE_STEP: the END of the issue step at lead L. Events: the end of
        the event's own window (nowcast), or the issue date (lead).
    Inputs:
        target: target facts (window, stamp, cadence).
        row_period: first and last day of the target row's period.
        kind: NOWCAST or ISSUE_STEP.
        issue_period: first and last day of the issue step (required for ISSUE_STEP).
    Returns:
        the reference day.
    Refuses:
        - an unknown target window (R17 refuses it too).
        - kind=ISSUE_STEP without issue_period.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.1 R8; ruled cases Q2 (centred indices lagged), Q3 a (annual columns at year -1
# on monthly targets), Q38 b (co_measured burn column at lag 1); 9.1 item 3 (annual target reading).
def compute_lag(column: ColumnFacts, target: TargetFacts, target_cadence: Cadence,
                reference: ReferenceKind) -> Lag:
    """The one fixed lag of a column: the smallest whole number of the column's steps that puts its
    newest content at or before the reference instant.

    Rule: R8.  Needed: Tue 29 Sep (derive v1).

    Contract (plan 2.1 R8, 1.3, 5 G-LAG):
        Worked out from the column's stamp, window (or signed assumed maximum) and cadence, by
        CONTENT time only; release and snapshot dates are never used (Q2). The lag is at least 1
        step if the column is co_measured_with_target or listed in the target's computed_from. An
        unknown window with no bound is refused. There is no separate annual clause: on a
        sub-annual target an annual column comes out at year -1 by this rule. On an annual target a
        same-year annual value stays at lag 0 unless its facts reach past the target year. Static
        columns have no lag. Nothing types a lag; this function is the only source of one.
    Inputs:
        column: the column's facts.
        target: target facts (its own window and stamp set the nowcast reference).
        target_cadence: the target's cadence (R1), used to walk every target period.
        reference: NOWCAST or ISSUE_STEP.
    Returns:
        Lag (steps in the column's own cadence, the floor reason when the 1-step floor bit).
    Refuses:
        - align UNKNOWN with no signed bound ("refused at lag 0").
        - a column with CadenceKind.EPOCH (handled by G-EPOCH and freeze, not by a lag).
    OWNER DECISION: lags are counted in the COLUMN's own steps (an annual column on a monthly
        target is 1 year back, which is how "year -1" reads), not in target steps.
    OWNER DECISION: when the needed lag differs across the target's positions in the year (a
        quarterly column on a monthly target), take the LARGEST, so the lag stays one fixed number.
    OWNER DECISION: "one fixed lag per column" versus two references: propose the lag is the
        larger of the NOWCAST and ISSUE_STEP results, so the same number is safe at every lead.
    OWNER DECISION: 9.1 item 3 -- default (a) keeps same-year annual values at lag 0 on an annual
        target; alternative (b) lags every year-stamped annual product one year.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: pm25_forecast.py:190-192 (cut_of: min(T_DEC_train_end, T_DEC_train_end + 1 - L)).
def fit_cut_step(lead_steps: int, train_end_step: Step) -> Step:
    """Grid fit cut for lead L: the donor train end moved back by L-1 steps, never later than it.

    Rule: R11.  Needed: Tue 29 Sep (derive v1).

    Contract (plan 2.1 R11):
        cut(L) = train_end_step - (L - 1), but never later than train_end_step, so the nowcast
        (lead 0) and lead 1 share the train end. Every fitted object at that lead uses only labels
        at or before this step.
    Inputs:
        lead_steps: the lead in steps (0 for the nowcast).
        train_end_step: the last step of the donor train end year (R6).
    Returns:
        the fit cut as an integer step.
    Refuses:
        - lead_steps < 0.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: pm25_forecast.py:195-197 (inner_cut_of: the same rule from the inner-fit end).
def guard_cut_step(lead_steps: int, inner_fit_end_step: Step) -> Step:
    """Grid cut of the inner guard at lead L: the same rule as fit_cut_step, from the inner-fit end.

    Rule: R11.  Needed: Tue 29 Sep (derive v1).

    Contract (plan 2.1 R11):
        guard_cut(L) = inner_fit_end_step - (L - 1), never later than inner_fit_end_step. Every
        inner score row must be issued at or after this cut (G-FITCUT).
    Inputs:
        lead_steps: the lead in steps (0 for the nowcast).
        inner_fit_end_step: the last step of the inner-fit window (R7).
    Returns:
        the guard cut as an integer step.
    Refuses:
        - lead_steps < 0.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.1 R11 ("Labels reach the issue step at leads of 1 or more, and t-1 at lead 0").
def latest_label_step(target_step: Step, lead_steps: int) -> Step:
    """The newest label a row predicting step t may read at lead L (history, persistence).

    Rule: R11, R17.  Needed: Tue 29 Sep (derive v1).

    Contract (plan 2.1 R11, R17):
        Lead L >= 1: the issue step t - L. Lead 0 (nowcast): t - 1. The history block and the
        persistence baselines end here (before any start offset R17 adds).
    Inputs:
        target_step: the step being predicted.
        lead_steps: the lead in steps.
    Returns:
        the newest readable label step.
    Refuses:
        - lead_steps < 0.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.1 R11 (events); plan 3.3 flag 13 (event leads in days). M8 under the fast track.
def event_fit_cut_day(lead_days: int, test_first_day: Day, train_end_last_day: Day) -> Day:
    """Event fit cut for a lead in days: the first day of the test window minus L days.

    Rule: R11 (events).  Needed: M8 (event rules; fast track).

    Contract (plan 2.1 R11):
        Lead L days >= 1: test_first_day - L. Lead 0 (nowcast): the last day of the donor train
        end year. Every fitted object then uses only labels dated at or before the cut whose own
        window has ended by then.
    Inputs:
        lead_days: the lead in days (0 for the nowcast).
        test_first_day: the first day of the test window.
        train_end_last_day: the last day of the donor train end year.
    Returns:
        the fit cut as a Day.
    Refuses:
        - lead_days < 0.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.1 R11 (events: "the inner guard's cut follows the same rule from the first day
# of the inner score window"). M8 under the fast track.
def event_guard_cut_day(lead_days: int, inner_score_first_day: Day,
                        inner_fit_end_last_day: Day) -> Day:
    """Event cut of the inner guard: the same rule from the first day of the inner score window.

    Rule: R11 (events).  Needed: M8 (event rules; fast track).

    Contract (plan 2.1 R11):
        Lead L days >= 1: inner_score_first_day - L.
    Inputs:
        lead_days: the lead in days.
        inner_score_first_day: the first day of the inner score window.
        inner_fit_end_last_day: the last day of the inner-fit window.
    Returns:
        the guard cut as a Day.
    Refuses:
        - lead_days < 0.
    OWNER DECISION: at lead 0 the plan does not state the event guard cut; propose the last day of
        the inner-fit end year, by analogy with the fit cut's lead-0 clause.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.1 R11 ("labels dated at or before the cut whose own window has ended by then").
def label_usable(label_day: Day, label_window_last_day: Day, cut_day: Day) -> bool:
    """True if a label may enter a fitted object at this cut.

    Rule: R11, G-FITCUT.  Needed: Tue 29 Sep (derive v1).

    Contract (plan 2.1 R11):
        A label is usable only if it is dated at or before the cut AND its own window has ended by
        the cut (inclusive).
    Inputs:
        label_day: the label's date (for grids: the last day of its step).
        label_window_last_day: the last day of the label's own window (composite window).
        cut_day: the cut as a day (for grids: the last day of the cut step).
    Returns:
        True if usable.
    Refuses:
        - nothing; pure predicate.
    OWNER DECISION: the plan writes the window-ended clause under Events; propose it applies to
        grid cuts too, which drops the cut step's own label when the target window reaches past its
        step (overlapping composites).
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.1 R11 ("Both: FitContext applies the cuts to every fitted object").
def cuts_for_leads(windows: Windows, leads: LeadPlan, target_cadence: Cadence) -> Mapping[int, CutPair]:
    """Both cuts (fit and inner guard) for lead 0 and every derived lead.

    Rule: R11.  Needed: Tue 29 Sep (derive v1).

    Contract (plan 2.1 R11):
        For grids: fit_cut_step and guard_cut_step per lead, in steps. For events: the day rules.
        Lead 0 is always present (the contract). The result is written to derived.json and
        FitContext reads it; no other module computes a cut.
    Inputs:
        windows: R3-R7 windows.
        leads: R10 lead plan.
        target_cadence: R1 cadence (steps vs days).
    Returns:
        {lead: CutPair}, lead 0 included.
    Refuses:
        - a lead plan whose unit does not match the cadence (steps for grids, days for events).
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.1 R9; plan 1.4 (freeze: the epoch is computed); defo_ban.py:14-15, 76
# ("usable only as ONE pre-window epoch").
def freeze_epoch(content_epochs: Sequence[Day], cut_day: Day) -> Day:
    """The epoch a 'freeze' column is held at: its last content epoch at or before the fit cut.

    Rule: R9.  Needed: Tue 29 Sep (derive v1).

    Contract (plan 2.1 R9):
        Among the column's content epochs (content time, never release dates), pick the latest one
        at or before the cut of that lead.
    Inputs:
        content_epochs: every content epoch the column has.
        cut_day: the cut as a day (last day of the cut step for grids).
    Returns:
        the chosen epoch.
    Refuses:
        - no epoch at or before the cut (the column cannot be frozen; it must be banned).
    OWNER DECISION: the plan names only "the fit cut of that lead"; propose the inner guard and the
        inner decision surface use the epoch at or before THEIR OWN cut (so no value observed after
        the guard cut enters the guard's fit). derive_r09 keys its epochs by (column, lead, cut
        kind), so derived.json holds both.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")
