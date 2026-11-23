"""The validators of plan Section 5: SCIENCE bodies for the owner-approved signatures of
treeroute/_proposed/validators.py (owner ruling A: every proposed default of D1-D101 accepted;
D93 follows D54 a; D95 refuse above 0.1% out of range, else flag with the count; D79 / D92 a stride sample
of 1,000 rows with a relative tolerance of 1e-9; D51 a statistical bound). Where an owner ruling and a
docstring differ, the ruling wins (each such place says so).

Every validator returns a GuardResult (the shape of layer/decide.py, field-identical to the approved
shared shape): a rule id, PASS / FLAG / BLOCK, the columns, the reason, the fix and a Part number. FLAG is
report only; BLOCK refuses. Declarations are ENFORCED, not detected: a wrong window or lineage fact that is
internally consistent passes, so the planted-fault table labels those guards 'rule enforcement'.

Reuse, not copies. The inline checks that already exist are CALLED, never re-written: io.apply.apply_verdicts
(closed world, G-KEYS), timing.compute_lag (R8), timing.max_forward_reach_days (A5), split.loro_split_sets /
loro_split_differences (G-SPLIT), io.sentinel._hits (the fill-value comparison of the read-time mask),
io.joins.coarse_periods (the coarse period of a target step), pipeline.data.LINEAGE_LEAK_REASONS (the
feature-lineage stand-in's leak reasons), check.recompute.recompute_declared_operation (G-DERIVED).

Engine inputs are read by attribute (the merged facts of check/facts.py, the package schema models, the
derive shapes), because engine code may not import the proposed types (G-IMPORT).

The streamed validators (G-SENTINEL deep, G-RANGE, G-CADENCE) are written as two halves: a COUNT over one
frame and a DECIDE over summed counts. The approved signature is exactly decide(count(frame)); the deep pass
sums the counts of every file and decides once, so a share is a share of the whole column, never of a file.
"""
# Provenance for the module: plan 5 (the guard table), 1.3-1.5, 2.1 R8, 2.4 R30, 6.1 (check, check --deep);
# desertflow_framework/validators.py:32-37, 90-166, 189-242; pm25_ban.py:168-184 (the proposed module's
# provenance); owner rulings A (D44, D51, D54 a, D79, D92-D97), D (leave one region out), J-L.

import ast
import math
import re
import warnings
from types import SimpleNamespace
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

import numpy as np
import pandas as pd

from treeroute import engine_constants as K
from treeroute import split as _split
from treeroute import timing
from treeroute.errors import RefusedError
from treeroute.layer.decide import GuardResult, GuardStatus
from treeroute.timing.content import NOWCAST

PASS, FLAG, BLOCK = GuardStatus.PASS, GuardStatus.FLAG, GuardStatus.BLOCK

KEY_ROLES = ("key_unit", "key_group", "key_time")
TARGET_ROLES = ("target", "target_twin")
ENTERING_VERDICTS = ("keep", "keep_unreviewed", "watch", "freeze")
LEAVING_VERDICTS = ("ban", "conditional")
REVIEWED_VERDICTS = ("keep", "freeze", "ban", "conditional", "watch")
UNLAGGED_KINDS = ("static", "epoch", "irregular")
# Origin: owner ruling N2 (OWNER_RULINGS_2026-10-06.md section N, the static-map dating rule): "physical maps
# (terrain, soil, rivers, coast) are timeless; maps of human-built things carry a content date and are checked against
# every cut". The schema has no field for 'physical', so a store catalog writes it as this content_epoch spelling.
TIMELESS_EPOCH = "timeless"
# Operations a target-derived dataset column may carry (plan 1.5: event counts, years since the last event,
# neighbour aggregates are allowed target-derived transforms; a lag, trailing or cumulative of y is not).
ALLOWED_TARGET_OPERATIONS = ("years_since", "years since", "event_count", "event count", "count of", "neighbour",
                             "neighbor")
FIT_CALLS = ("fit", "fit_transform", "fit_predict", "partial_fit")
FIT_ATTRIBUTES = ("feature_importances_",)
_SHOW = 8
# The packages' placeholder for an unsigned exceptions.yaml entry (their exceptions.yaml headers: "Every 'owner'
# field reads 'UNSIGNED -- basis: ...': the entry is NOT signed ... The owner signs by replacing 'UNSIGNED'").
# The schema only requires a non-empty owner, so the guards read these marks: an owner field whose FIRST WORD is
# one of them discloses, never signs. READING for the owner (weakness stated plainly): this is a list of known
# placeholder words, not a positive rule; any other placeholder text in the owner field still counts as a
# signature. A positive rule (for example a separate signed-date field, or the owner's name as dataset.yaml gives
# it once it is filled in) needs a schema change.
UNSIGNED_MARKS = ("UNSIGNED", "TBD", "TODO", "PENDING", "AWAITING", "PLACEHOLDER", "NONE", "N/A", "?")
UNSIGNED_MARK = UNSIGNED_MARKS[0]
# The entry shape the guards read as addressed to a column (printed in every fix that accepts an entry).
EXCEPTION_SHAPE = ("an exceptions.yaml entry addresses a column when its 'column' field is the column, or its "
                   "'check' field is the rule id exactly (e.g. 'G-LINEAGE') or starts with the rule id and names the "
                   "column (e.g. 'G-LINEAGE co-product (frac)'); it is signed when its owner field names the signer "
                   "(a first word UNSIGNED, TBD, TODO, PENDING, AWAITING, PLACEHOLDER, NONE, N/A or ? discloses only)")

# Part numbers of the lessons each guard encodes (plan 5, 'Lesson it encodes').
PART_CADENCE = 549        # the fake-monthly column
PART_DERIVED = 526        # history copied from the target row at a lead
PART_JOIN = 326           # the assembler that reverted 49 columns while printing OK
PART_SPLIT = 426          # 25-vs-44 groups


# ---------------------------------------------------------------------------------------------------
# Small helpers
def _v(x: Any) -> Any:
    return getattr(x, "value", x)


def _fmt(names: Iterable[Any], show: int = _SHOW) -> str:
    names = list(names)
    return "%s%s" % (", ".join(str(n) for n in names[:show]), " ... (%d in all)" % len(names)
                     if len(names) > show else "")


def result(rule: str, status: GuardStatus, columns: Iterable[str], reason: str, fix: str = "",
           part: Optional[int] = None, details: Optional[Mapping[str, Any]] = None) -> GuardResult:
    return GuardResult(rule_id=rule, status=status, columns=tuple(sorted(set(str(c) for c in columns))),
                       reason=reason, fix=fix, part=part, details=dict(details or {}))


def refusal_result(exc: RefusedError, label_rule: Optional[str] = None, prefix: str = "") -> GuardResult:
    """A refusal raised by an engine function, as a BLOCK result: its rule, its message and its fix, once each."""
    rule = getattr(exc, "rule", None) or label_rule or "G-CLOSED"
    text = str(exc)
    head = "[%s] " % rule
    if text.startswith(head):
        text = text[len(head):]
    fix = getattr(exc, "fix", None) or ""
    if fix and text.endswith(" Fix: %s" % fix):
        text = text[:-len(" Fix: %s" % fix)]
    return result(label_rule or rule, BLOCK, (), prefix + text + ("" if rule == (label_rule or rule)
                                                                  else " (rule %s)" % rule), fix=fix)


def worst(statuses: Iterable[GuardStatus]) -> GuardStatus:
    order = {PASS: 0, FLAG: 1, BLOCK: 2}
    out = PASS
    for s in statuses:
        if order[s] > order[out]:
            out = s
    return out


def verdict_of(verdicts: Mapping[str, Any], column: str) -> Optional[str]:
    v = verdicts.get(column)
    return None if v is None else _v(getattr(v, "verdict", None))


def timing_facts_signed(facts: Any) -> bool:
    """A column's timing facts (stamp, window, cadence, content epoch) are verified, or 'assumed' and signed
    (reviewed_by set: plan 1.3's spelling of a signed fact; the schema has no 'signed' status)."""
    status = _v(getattr(facts, "fact_status", None))
    return status == "verified" or (status == "assumed" and bool(getattr(facts, "reviewed_by", None)))


def _cadence_kind(facts: Any) -> Optional[str]:
    return _v(getattr(getattr(facts, "cadence", None), "kind", None))


def _entering(column: str, verdicts: Mapping[str, Any]) -> bool:
    return verdict_of(verdicts, column) in ENTERING_VERDICTS


_FIRST_WORD = re.compile(r"[A-Za-z/?]+")


def exception_signed(entry: Any) -> bool:
    """An exceptions.yaml entry is signed when its owner field names a person: non-empty and its first word is
    not a placeholder (UNSIGNED_MARKS: the packages' 'UNSIGNED -- basis: ...', 'The owner signs by replacing
    UNSIGNED', and the other common placeholder words)."""
    owner = str(getattr(entry, "owner", None) or "").strip()
    if not owner:
        return False
    word = _FIRST_WORD.match(owner)
    return not (word is not None and word.group(0).upper() in UNSIGNED_MARKS)


def _names_column(text: str, column: str) -> bool:
    """The text names the column as a whole name (not as part of a longer column name)."""
    return re.search(r"(?<![\w:])%s(?![\w:])" % re.escape(column), text) is not None


def _addressed(e: Any, column: str, check: Optional[str], kinds: Tuple[str, ...]) -> bool:
    """EXCEPTION_SHAPE: the entry's 'column' field is the column (with no 'check', or a 'check' that starts with
    the rule id); or its 'check' field is the rule id exactly (every column), or starts with the rule id and names
    the column (the packages write the check as free text naming the columns)."""
    if kinds and _v(getattr(e, "kind", None)) not in kinds:
        return False
    ecol = getattr(e, "column", None)
    text = str(getattr(e, "check", None) or "").strip()
    if ecol is not None:
        return ecol == column and (not text or check is None or text.startswith(check))
    if check is None or not text.startswith(check):
        return False
    return text == check or _names_column(text[len(check):], column)


def _exception_for(exceptions: Sequence[Any], column: str, check: Optional[str] = None,
                   kinds: Tuple[str, ...] = ()) -> Optional[Any]:
    """The exceptions.yaml entry addressed to the column (or to the check), signed by an owner (exception_signed)."""
    for e in exceptions or ():
        if _addressed(e, column, check, kinds) and exception_signed(e):
            return e
    return None


def _unsigned_note(exceptions: Sequence[Any], column: str, check: Optional[str] = None,
                   kinds: Tuple[str, ...] = ()) -> str:
    """' (an exceptions.yaml entry names it, but it is not signed: owner ...)' when only an unsigned entry exists."""
    for e in exceptions or ():
        if _addressed(e, column, check, kinds) and not exception_signed(e):
            return " (an exceptions.yaml entry names it, but it is not signed: owner %r)" % str(
                getattr(e, "owner", None) or "")
    return ""


# ===================================================================================================
# Quick checks
# Provenance: plan 5 G-CLOSED; plan 1.4, 9.2 A5; default-in feature lists (pm25_architecture.py:219-221);
# a silent skip (defo_ban.py:149-173). D-decision: keep_unreviewed needs no evidence Part (accepted default).
def check_g_closed(data_columns: Tuple[str, ...], columns: Mapping[str, Any], verdicts: Mapping[str, Any],
                   forward_reach: Mapping[str, int], lineage_flagged: Set[str]) -> GuardResult:
    """G-CLOSED: every non-key column has facts and a verdict (closed world).

    Rule: G-CLOSED, A5. data_columns are the non-key columns observed in the data (store footers and the
    feature script's outputs); columns their facts (a package catalog row at least; an ENTERING column also
    needs physical facts, has_store_facts); verdicts ban.yaml. BLOCK on: a column without facts or verdict;
    a verdict or fact for a column the data do not hold; a verdict without a reason; a ban without its
    BanReason label; a reviewed verdict without an evidence Part; keep_unreviewed with unsigned timing
    facts, forward reach > 0 or a lineage flag; and whatever io.apply.apply_verdicts refuses (a key role
    with a verdict, the target or a twin not banned, an unknown verdict or role). The keep_unreviewed list
    is in details (listed in every report).
    """
    from treeroute.io.apply import apply_verdicts
    from treeroute.package.schema import BAN_REASONS

    data = tuple(data_columns)
    seen = set(data)
    problems: List[str] = []
    bad: Set[str] = set()
    no_facts = [c for c in data if c not in columns]
    no_verdict = [c for c in data if c not in verdicts]
    stray_facts = sorted(c for c in columns if c not in seen)
    stray_verdicts = sorted(c for c in verdicts if c not in seen)
    def _verdict_mix(names):
        mix: Dict[str, int] = {}
        for c in names:
            key = verdict_of(verdicts, c) or "no verdict"
            mix[key] = mix.get(key, 0) + 1
        return ", ".join("%s x %d" % kv for kv in sorted(mix.items()))

    absent_text = "catalog rows for columns no declared store or feature output holds (verdicts: %s)" %         _verdict_mix(stray_facts) if stray_facts else ""
    for label, names in (("columns in the data without facts (no catalog row)", no_facts),
                         ("columns in the data without a verdict", no_verdict),
                         (absent_text, stray_facts),
                         ("verdicts for columns the data do not hold", [c for c in stray_verdicts
                                                                        if c not in columns])):
        if names:
            problems.append("%d %s: %s" % (len(names), label, _fmt(names)))
            bad.update(names)
    no_physical = [c for c in data if c in columns and _entering(c, verdicts)
                   and not getattr(columns[c], "has_store_facts", True)]
    if no_physical:
        problems.append("%d entering columns have no physical facts in any store catalog or feature output: %s"
                        % (len(no_physical), _fmt(no_physical)))
        bad.update(no_physical)
    no_reason, no_label, no_evidence = [], [], []
    for c, v in verdicts.items():
        verdict = _v(getattr(v, "verdict", None))
        reason = getattr(v, "reason", None)
        if not reason:
            no_reason.append(c)
        if verdict == "ban" and reason not in BAN_REASONS:
            no_label.append(c)
        if verdict in REVIEWED_VERDICTS and not getattr(v, "evidence", None):
            no_evidence.append(c)
    for label, names in (("verdicts without a reason", no_reason),
                         ("bans without one BanReason label", no_label),
                         ("reviewed verdicts without an evidence Part", no_evidence)):
        if names:
            problems.append("%d %s: %s" % (len(names), label, _fmt(sorted(names))))
            bad.update(names)
    unreviewed = sorted(c for c in data if verdict_of(verdicts, c) == "keep_unreviewed")
    unreviewed_bad = []
    for c in unreviewed:
        f = columns.get(c)
        why = []
        if f is not None and not timing_facts_signed(f):
            why.append("timing facts not signed (fact_status %s)" % _v(getattr(f, "fact_status", None)))
        if int(forward_reach.get(c, 0) or 0) > 0:
            why.append("forward reach %d days" % int(forward_reach[c]))
        if c in lineage_flagged:
            why.append("a lineage flag")
        if why:
            unreviewed_bad.append("%s (%s)" % (c, "; ".join(why)))
            bad.add(c)
    if unreviewed_bad:
        problems.append("%d keep_unreviewed columns are not allowed unreviewed: %s"
                        % (len(unreviewed_bad), _fmt(unreviewed_bad)))
    if not problems:
        roles = {c: _v(getattr(columns[c], "role", None)) for c in data}
        try:
            apply_verdicts(data, verdicts, roles)
        except RefusedError as exc:
            problems.append("io.apply_verdicts refused: %s" % exc)
    details = {"keep_unreviewed": unreviewed, "data_columns": len(data), "verdicts": len(verdicts)}
    if problems:
        return result("G-CLOSED", BLOCK, bad, "closed world: " + "; ".join(problems),
                      fix="give every column in the data a catalog row (role and facts) and exactly one "
                          "verdict with a reason (and a Part for a reviewed verdict); remove rows and "
                          "verdicts of columns the data do not hold (plan 1.3, 1.4)", details=details)
    return result("G-CLOSED", PASS, (), "every one of the %d non-key columns has facts and one verdict; "
                  "keep_unreviewed (listed in every report): %s" % (len(data), _fmt(unreviewed) or "none"),
                  details=details)


# Provenance: plan 5 G-LAG; centred indices (Q2); window-centre dating (fire_ban.py:33-37); product-year
# dating (defo_ban.py:28-29); F10.
def check_g_lag(columns: Mapping[str, Any], target: Any, target_cadence: Any,
                lags: Any) -> GuardResult:
    """G-LAG: every lag is COMPUTED from facts (R8); nothing types a lag; an unknown window is refused.

    Rule: G-LAG, R8. columns are the facts of the ENTERING columns; lags the R8 entry (a Derived, or its
    {column: Lag} value). Each time-varying entering column must hold a lag equal to timing.compute_lag on
    its facts (both references, D24). BLOCK on: a missing lag, a lag that differs from its recomputation,
    a column R8 refuses (an unknown window without a signed bound is refused at lag 0, an epoch column
    without its freeze, a column whose step does not hold the target's step). Details: every lag, by size.
    """
    lag_map = getattr(lags, "value", lags) or {}
    missing, differ, refused = [], [], []
    computed: Dict[str, int] = {}
    for name in sorted(columns):
        f = columns[name]
        if _cadence_kind(f) in UNLAGGED_KINDS:
            continue
        try:
            lag = timing.compute_lag(f, target, target_cadence, NOWCAST)
        except RefusedError as exc:
            refused.append((name, str(exc)))
            continue
        computed[name] = int(lag.steps)
        given = lag_map.get(name)
        if given is None:
            missing.append(name)
        elif int(getattr(given, "steps", -1)) != int(lag.steps):
            differ.append("%s (given %s, computed %d)" % (name, getattr(given, "steps", None), lag.steps))
    by_size: Dict[int, int] = {}
    for s in computed.values():
        by_size[s] = by_size.get(s, 0) + 1
    details = {"lags": computed, "lags_by_steps": {str(k): n for k, n in sorted(by_size.items())},
               "refused": {n: m for n, m in refused}}
    problems, cols = [], set()
    if refused:
        problems.append("%d entering columns are refused by R8: %s" % (
            len(refused), _fmt(["%s: %s" % (n, m) for n, m in refused], 4)))
        cols.update(n for n, _ in refused)
    if missing:
        problems.append("%d entering columns have no lag: %s" % (len(missing), _fmt(missing)))
        cols.update(missing)
    if differ:
        problems.append("%d lags differ from their recomputation: %s" % (len(differ), _fmt(differ)))
        cols.update(d.split(" ")[0] for d in differ)
    if problems:
        return result("G-LAG", BLOCK, cols, "; ".join(problems),
                      fix="sign a cautious bound for an unknown window (window max_length, owner-signed) or "
                          "ban the column; never type a lag (R8 computes it from the facts)", details=details)
    return result("G-LAG", PASS, (), "%d entering time-varying columns have R8's computed lag (by steps: %s)"
                  % (len(computed), ", ".join("%s: %d" % kv for kv in sorted(details["lags_by_steps"].items()))),
                  details=details)


def _date_day(text: Any) -> Optional[int]:
    """A fact date ('YYYY', 'YYYY-MM' or 'YYYY-MM-DD') as the ordinal of its LAST day, or None."""
    if text is None:
        return None
    import datetime as _dt

    s = str(text).strip()
    parts = s.split("-")
    try:
        y = int(parts[0])
        if len(parts) == 1:
            return _dt.date(y, K.MONTHS_PER_YEAR, 31).toordinal()
        m = int(parts[1])
        if len(parts) == 2:
            nxt = _dt.date(y + (m // K.MONTHS_PER_YEAR), (m % K.MONTHS_PER_YEAR) + 1, 1)
            return nxt.toordinal() - 1
        return _dt.date(y, m, int(parts[2][:2])).toordinal()
    except (ValueError, IndexError):
        return None


# Provenance: plan 5 G-EPOCH; plan 1.3 ("Release and snapshot dates are recorded and printed but never used by R8
# or G-EPOCH: lags follow content time only"); post-window snapshots, projections, extrapolations
# (defo_ban.py:80-111); Q43 a (base periods allowed and disclosed). D-decision (accepted default): "observed after
# the cut" = "observed_through (or a snapshot's content epoch) later than the cut, checked against EVERY cut the
# column is used at (each lead's fit cut and guard cut)".
def _cut_list(cuts: Mapping[int, Any]) -> List[Tuple[str, int]]:
    """[(label, day ordinal)] of every cut given: a lead's fit and guard cut as their LAST days (the records of
    derive.rules.cut_days, fit_cut_day / guard_cut_day), or a bare day ordinal. A step-unit cut is refused: a
    step is not a day (derive.rules.cut_days turns R11's steps into days)."""
    out: List[Tuple[str, int]] = []
    for lead in sorted(cuts or {}):
        c = cuts[lead]
        if isinstance(c, (int, np.integer)) and not isinstance(c, bool):
            out.append(("lead %s" % lead, int(c)))
            continue
        fields = [(f, w) for f, w in (("fit_cut_day", "fit"), ("guard_cut_day", "guard")) if hasattr(c, f)]
        if not fields:
            raise RefusedError("G-EPOCH", "the cut of lead %r is neither a day ordinal nor a record with "
                               "fit_cut_day / guard_cut_day" % (lead,),
                               fix="pass derive.rules.cut_days(R11 cuts, target cadence)")
        for field, word in fields:
            out.append(("lead %s %s cut" % (lead, word), int(getattr(c, field))))
    return out


def _day_text(day: int) -> str:
    import datetime as _dt

    return _dt.date.fromordinal(int(day)).isoformat()


def check_g_epoch(columns: Mapping[str, Any], verdicts: Mapping[str, Any], cuts: Mapping[int, Any],
                  target: Any, train_end: Optional[int], exceptions: Sequence[Any]) -> GuardResult:
    """G-EPOCH: a column whose content is observed after the cut is refused unless 'freeze'; a target
    calibrated past the donor train end is refused unless recalibrated or disclosed.

    Rule: G-EPOCH, R9. cuts: R11's cuts per lead as days ({lead: a record with fit_cut_day / guard_cut_day, as
    derive.rules.cut_days builds them from timing.cuts_for_leads, or a day ordinal}); EVERY cut given is checked
    and a refusal names the cuts the epoch lies after. The observation epoch of an ENTERING column, whatever its
    cadence kind (static included: a post-window snapshot is the guard's own lesson), is its content_epoch; and,
    for a static or epoch-cadence column, its observed_through (a column observed once: that is its one
    observation epoch). Either one after a cut refuses the column unless its verdict is 'freeze' (R9 then picks
    the epoch at or before each cut). An epoch-cadence entering column without 'freeze' is refused whatever the
    cut (derive's stand-in rule, kept). A fact date that cannot be read is refused.
    Never used (plan 1.3): release_date and snapshot_date. A baseline period ending after a cut is listed as a
    disclosure (Q43 a), never refused.
    Owner ruling N S23 (the owner rulings file, section N): the observed_through of a REGULAR or composite column is
    where its record ends, not a content date (engineered lag columns of a parent whose record ends later, held
    columns that copy a last observed year forward). It is listed in details['observed_through_record_end'], never
    compared with a cut, never flagged and never refused; an unreadable one is still refused.
    A target whose calibration_through (a year) is after train_end is refused unless a signed exceptions.yaml
    entry (EXCEPTION_SHAPE; check G-EPOCH or the target column) discloses it.
    Static-map dating rule (owner ruling N2): an ENTERING static column must be either physical (content_epoch
    TIMELESS_EPOCH: never compared with a cut) or dated (a content_epoch, or its observed_through, compared with every
    cut). A static column that is neither is refused by name, whatever the cut; TIMELESS_EPOCH on a non-static
    column is refused (only a static map can be timeless).
    """
    cut_list = _cut_list(cuts)
    earliest = min((d for _, d in cut_list), default=None)
    refused, disclosed, unchecked, unreadable, record_ends = [], [], [], [], []
    undated, misplaced_timeless = [], []
    for name in sorted(columns):
        f = columns[name]
        if not _entering(name, verdicts):
            continue
        verdict = verdict_of(verdicts, name)
        kind = _cadence_kind(f)
        if kind == "epoch" and verdict != "freeze":
            refused.append("%s (epoch cadence, verdict %s)" % (name, verdict))
            continue
        once = kind in ("static", "epoch")
        epoch_text = getattr(f, "content_epoch", None)
        timeless = epoch_text is not None and str(epoch_text).strip() == TIMELESS_EPOCH
        record_end = getattr(f, "observed_through", None)
        if timeless and kind != "static":
            misplaced_timeless.append("%s (content_epoch %r, %s cadence)" % (name, epoch_text, kind))
            continue
        if kind == "static" and not timeless and not epoch_text and not record_end:
            undated.append(name)
            continue
        compared = [("content_epoch", None if timeless else epoch_text)]
        if once:
            compared.append(("observed_through", record_end))
        for field, text in compared:
            if not text:
                continue
            day = _date_day(text)
            if day is None:
                unreadable.append("%s (%s %r)" % (name, field, text))
                continue
            if not cut_list:
                unchecked.append("%s (%s %s)" % (name, field, text))
                continue
            after = [label for label, cut in cut_list if day > cut]
            if after and verdict != "freeze":
                refused.append("%s (%s %s, after %d of the %d cuts, e.g. %s)"
                               % (name, field, text, len(after), len(cut_list), _fmt(after, 2)))
        if record_end and not once:
            # owner ruling N S23 (OWNER_RULINGS_2026-10-06.md N): a regular or composite column's observed_through
            # is its record end, not a content date: listed in the details, never compared with a cut, never flagged
            if _date_day(record_end) is None:
                unreadable.append("%s (observed_through %r)" % (name, record_end))
            else:
                record_ends.append("%s (observed_through %s, %s cadence)" % (name, record_end, kind))
        base = getattr(f, "baseline_period", None)
        if base and earliest is not None:
            end = _date_day(base[1])
            if end is not None and end > earliest:
                disclosed.append("%s (baseline period %s-%s)" % (name, base[0], base[1]))
    cal = getattr(target, "calibration_through", None)
    target_problem = None
    if cal is not None and train_end is not None and int(cal) > int(train_end):
        if _exception_for(exceptions, getattr(target, "name", ""), "G-EPOCH") is None:
            target_problem = ("the target is calibrated through %s, after the donor train end %s, and no "
                              "signed exceptions.yaml entry discloses it%s"
                              % (cal, train_end, _unsigned_note(exceptions, getattr(target, "name", ""), "G-EPOCH")))
    details = {"cuts": [{"cut": label, "day": _day_text(day)} for label, day in cut_list],
               "earliest_cut_day": earliest, "baseline_disclosures": disclosed, "not_compared": unchecked,
               "observed_through_record_end": record_ends,
               "static_undated": undated,
               "never_used": "release_date, snapshot_date (plan 1.3)"}
    cut_text = ("%d cuts (R11: every lead's fit and guard cut), the earliest %s" % (len(cut_list), _day_text(earliest))
                if cut_list else "no cut known to this check")
    problems = []
    if undated:
        problems.append("%d entering static columns are neither physical (content_epoch %r) nor dated (a content_epoch "
                        "or observed_through), ruling N2: %s" % (len(undated), TIMELESS_EPOCH, _fmt(undated)))
    if misplaced_timeless:
        problems.append("%d entering columns are marked %r but are not static (only a static physical map is "
                        "timeless, ruling N2): %s" % (len(misplaced_timeless), TIMELESS_EPOCH, _fmt(misplaced_timeless)))
    if refused:
        problems.append("%d entering columns are observed after a cut without a 'freeze' verdict: %s"
                        % (len(refused), _fmt(refused)))
    if unreadable:
        problems.append("%d entering columns carry a fact date that cannot be read ('YYYY', 'YYYY-MM' or "
                        "'YYYY-MM-DD'): %s" % (len(unreadable), _fmt(unreadable)))
    if target_problem:
        problems.append(target_problem)
    if problems:
        return result("G-EPOCH", BLOCK, list(undated) + [r.split(" ")[0] for r in misplaced_timeless + refused
                                                         + unreadable]
                      + ([getattr(target, "name", "")] if target_problem else []), "; ".join(problems) + "; " + cut_text,
                      fix="mark a physical static map content_epoch '%s' and give a map of human-built things its "
                          "content date in the store catalog (ruling N2); "
                          "give a column observed after the cut a 'freeze' verdict (R9) or ban it; write fact dates as "
                          "YYYY, YYYY-MM or YYYY-MM-DD; recalibrate the target at the train end or disclose it in a "
                          "signed exceptions.yaml entry (%s)" % (TIMELESS_EPOCH, EXCEPTION_SHAPE), details=details)
    if unchecked:
        return result("G-EPOCH", FLAG, [u.split(" ")[0] for u in unchecked],
                      "%d entering columns carry an observation epoch that was not compared with a cut (no cut "
                      "known to this check): %s" % (len(unchecked), _fmt(unchecked)),
                      fix="run check --deep (it derives the windows and R11's cuts) or plan (derived.json R11)",
                      details=details)
    text = "no entering column is observed after a cut (content_epoch on every kind, observed_through of a static " \
           "or epoch column; %s)" % cut_text
    if record_ends:
        text += ("; %d regular or composite columns declare observed_through: their record end, never compared with "
                 "a cut (owner ruling N S23)" % len(record_ends))
    if disclosed:
        text += "; baseline periods past the cut (disclosed, Q43 a): %s" % _fmt(disclosed)
    return result("G-EPOCH", PASS, (), text, details=details)


def _target_names(columns: Mapping[str, Any], target: Any) -> Set[str]:
    out = {getattr(target, "name", None)}
    out.update(c for c, f in columns.items() if _v(getattr(f, "role", None)) in TARGET_ROLES)
    return {c for c in out if c}


def _target_family(target: Any) -> Optional[str]:
    return getattr(target, "product_family", None)


def _co_product_reason(f: Any, target: Any, targets: Set[str]) -> Optional[str]:
    fam = _target_family(target)
    pf = getattr(f, "product_family", None)
    lineage = set(getattr(f, "lineage_assimilates", ()) or ()) | set(getattr(f, "lineage_trained_on", ()) or ())
    if fam and pf == fam:
        return "same product family %r as the target" % fam
    if fam and fam in lineage:
        return "its lineage assimilates or was trained on the target's product family %r" % fam
    hit = sorted(lineage & targets)
    if hit:
        return "its lineage names the target %s" % hit
    return None


# Provenance: plan 5 G-LINEAGE; plan 1.4 (sum groups share one verdict; target and twins forced to ban); a sum
# group rebuilt from its members (defo_ban.py:28-34); a product constrained by the target source; classifiers
# trained on the target (Q35); F16; the feature-lineage stand-in (pipeline/data.py check_feature_lineage).
def check_g_lineage(columns: Mapping[str, Any], target: Any, verdicts: Mapping[str, Any],
                    exceptions: Sequence[Any]) -> GuardResult:
    """G-LINEAGE (quick): provenance facts checked against the target.

    Rule: G-LINEAGE. BLOCK on (the approved contract, exactly): the target or a twin not banned; an ENTERING
    co-product (same product family as the target, or a lineage that assimilates or was trained on it) without a
    signed exceptions.yaml entry (EXCEPTION_SHAPE); a sum group with mixed verdicts. FLAG (lineage flag, G-CLOSED
    reads it): an entering column derived from a column banned or held out for any reason, or a disclosed one.
    READING for the owner (listed in details['leak_parent'], never refused): an entering column derived from a
    column banned for a leak reason (pipeline.data.LINEAGE_LEAK_REASONS, the list the feature runner's stand-in
    refuses) without a signed entry. A column derived from the target itself is G-HIST's (plan 1.5 allows
    event counts, years since and neighbour aggregates). DIFFERENCE recorded for the owner: the feature runner's
    stand-in (pipeline/data.py check_feature_lineage) refuses every feature-script output derived from the target
    and every leak-banned source, with no exception path, and it sees only feature-script outputs, never
    precomputed store columns. Flagged columns are in details['flagged'].
    """
    from treeroute.pipeline.data import LINEAGE_LEAK_REASONS

    targets = _target_names(columns, target)
    blocks: List[str] = []
    cols: Set[str] = set()
    flagged: Dict[str, str] = {}
    leak_parent: Dict[str, str] = {}
    for t in sorted(targets):
        if t in verdicts and verdict_of(verdicts, t) != "ban":
            blocks.append("%s is the target or a twin with verdict %s (forced to ban)" % (t, verdict_of(verdicts, t)))
            cols.add(t)
    for name in sorted(columns):
        if name in targets:
            continue
        f = columns[name]
        entering = _entering(name, verdicts)
        why = _co_product_reason(f, target, targets)
        if why and entering:
            if _exception_for(exceptions, name, "G-LINEAGE") is None:
                blocks.append("%s is a co-product (%s) without a signed exceptions.yaml entry%s"
                              % (name, why, _unsigned_note(exceptions, name, "G-LINEAGE")))
                cols.add(name)
            else:
                flagged[name] = "co-product disclosed: %s" % why
        sources = list(getattr(f, "derived_from", ()) or ()) + list(getattr(f, "computed_from", ()) or ())
        if not entering:
            continue
        for src in sources:
            if src in targets:
                continue                  # a target-derived column: G-HIST decides (plan 1.5 allowed transforms)
            sv = verdicts.get(src)
            if sv is None:
                continue
            sverdict, sreason = _v(getattr(sv, "verdict", None)), getattr(sv, "reason", None)
            if sverdict == "ban" and sreason in LINEAGE_LEAK_REASONS:
                # READING for the owner (a FLAG, not the approved contract, which refuses only the target or a
                # twin not banned, an unsigned co-product and a mixed sum group): the feature runner's stand-in
                # refuses such a feature-script output; whether a STORE column derived from a leak-banned parent
                # refuses is the owner's choice (an engine change), so it is listed, never refused here.
                if _exception_for(exceptions, name, "G-LINEAGE") is None:
                    leak_parent[name] = ("derived from %s, banned as %r (a leak reason); no signed exceptions.yaml "
                                         "entry discloses why it does not carry what the ban keeps out (for example "
                                         "a lag that ends before the predicted period)%s"
                                         % (src, sreason, _unsigned_note(exceptions, name, "G-LINEAGE")))
                    flagged[name] = leak_parent[name]
                else:
                    flagged[name] = "derived from %s, banned as %r, disclosed in a signed exceptions.yaml entry" % (
                        src, sreason)
            elif sverdict in LEAVING_VERDICTS and name not in leak_parent:
                flagged[name] = ("derived from %s, which is %s (%r): allowed only because %r is not a leak reason "
                                 "(a leak reason such as post_window_snapshot or coproduct would refuse it)"
                                 % (src, sverdict, sreason, sreason))
    groups: Dict[str, List[str]] = {}
    for name, f in columns.items():
        g = getattr(f, "sum_group", None)
        if g:
            groups.setdefault(g, []).append(name)
    mixed = []
    for g, members in sorted(groups.items()):
        vs = {verdict_of(verdicts, m) for m in members}
        if len(vs) > 1:
            mixed.append("%s: %s" % (g, ", ".join("%s=%s" % (m, verdict_of(verdicts, m)) for m in sorted(members))))
            cols.update(members)
    if mixed:
        blocks.append("%d sum groups hold mixed verdicts (one group, one verdict): %s" % (len(mixed), _fmt(mixed, 3)))
    details = {"flagged": flagged, "leak_parent": leak_parent,
               "sum_groups": {g: sorted(m) for g, m in sorted(groups.items())}}
    leak_text = ""
    if leak_parent:
        leak_text = ("; READING for the owner (flagged, not refused: the approved contract does not refuse it): %d "
                     "entering columns derive from a parent banned for a leak reason with no signed exceptions.yaml "
                     "entry: %s" % (len(leak_parent), _fmt(["%s (%s)" % kv for kv in sorted(leak_parent.items())], 3)))
    if blocks:
        return result("G-LINEAGE", BLOCK, cols, "; ".join(blocks) + leak_text,
                      fix="ban the target and its twins; ban a co-product or disclose it with a signed "
                          "exceptions.yaml entry (%s); give every sum-group member the same verdict" % EXCEPTION_SHAPE,
                      details=details)
    if flagged:
        others = {c: t for c, t in flagged.items() if c not in leak_parent}
        text = "%d entering columns carry a lineage flag" % len(flagged)
        if others:
            text += ": %s" % _fmt(["%s (%s)" % kv for kv in sorted(others.items())], 4)
        return result("G-LINEAGE", FLAG, flagged, text + leak_text,
                      fix="confirm the reason word on each source; for a column derived from a leak-banned parent, the "
                          "owner rules whether it refuses, or signs an exceptions.yaml entry (%s)" % EXCEPTION_SHAPE,
                      details=details)
    return result("G-LINEAGE", PASS, (), "no lineage reaches the target; %d sum groups hold one verdict each"
                  % len(groups), details=details)


_CADENCE_DAYS = {"day": 1.0, "month": K.DAYS_PER_YEAR / K.MONTHS_PER_YEAR, "year": K.DAYS_PER_YEAR}


def _step_days(cadence: Any) -> Optional[float]:
    kind = _v(getattr(cadence, "kind", None))
    if kind == "regular":
        return float(getattr(cadence, "length", 1) or 1) * _CADENCE_DAYS.get(_v(getattr(cadence, "unit", None)), math.nan)
    if kind == "composite_of_year":
        return float(getattr(cadence, "length", None) or getattr(cadence, "composite_days", 1) or 1)
    return None


# Provenance: plan 1.3 co_measured_with_target ("No default: the checker lists every column that shares product
# family or sensor lineage with the target in the same period"). D-decision (accepted default): same
# product_family, or the target's family in lineage_assimilates / lineage_trained_on, at a cadence no coarser
# than the target's.
def list_co_measured_candidates(columns: Mapping[str, Any], target: Any) -> Tuple[str, ...]:
    """Every column that must carry an explicit co_measured_with_target answer (sorted)."""
    fam = _target_family(target)
    if not fam:
        return ()
    t_days = _step_days(getattr(target, "cadence", None))
    out = []
    for name, f in columns.items():
        if _v(getattr(f, "role", None)) in TARGET_ROLES + KEY_ROLES:
            continue
        lineage = set(getattr(f, "lineage_assimilates", ()) or ()) | set(getattr(f, "lineage_trained_on", ()) or ())
        if getattr(f, "product_family", None) != fam and fam not in lineage:
            continue
        c_days = _step_days(getattr(f, "cadence", None))
        slack = 1.0 + float(K.CADENCE_COMPARE_REL_TOLERANCE)
        if c_days is None or (t_days is not None and c_days > t_days * slack):
            continue
        out.append(name)
    return tuple(sorted(out))


def _operation_head(f: Any) -> str:
    op = getattr(f, "operation", None)
    return str(op).strip().split(" ")[0] if op else ""


# Provenance: plan 5 G-HIST (quick: by declaration); y(t) at lead 0 (pm25_forecast.py:99); F22.
def check_g_hist_declared(columns: Mapping[str, Any], target: Any) -> GuardResult:
    """G-HIST (quick): refuse dataset columns DECLARED as a lag, trailing or cumulative sum or mean of the
    unit's own target.

    Rule: G-HIST, R17. BLOCK on any dataset column with reads_target true (or derived_from naming the
    target or a twin) whose operation is not an allowed target-derived transform (event counts, years
    since the last event, neighbour aggregates: plan 1.5). DIFFERENCE recorded for the owner: the feature
    runner (pipeline/data.py feature_outputs) refuses EVERY reads_target output, the allowed transforms
    included; this guard follows plan 1.5.
    """
    targets = _target_names(columns, target)
    bad = []
    for name in sorted(columns):
        if name in targets:
            continue
        f = columns[name]
        reads = bool(getattr(f, "reads_target", False)) or bool(set(getattr(f, "derived_from", ()) or ()) & targets)
        op_text = str(getattr(f, "operation", None) or "").lower()
        if reads and not any(word in op_text for word in ALLOWED_TARGET_OPERATIONS):
            bad.append("%s (operation %r)" % (name, getattr(f, "operation", None)))
    if bad:
        return result("G-HIST", BLOCK, [b.split(" ")[0] for b in bad],
                      "%d dataset columns are declared as a look-back of the unit's own target: %s"
                      % (len(bad), _fmt(bad)),
                      fix="drop them: the engine builds the own-history block (R17); only event counts, years "
                          "since the last event and neighbour aggregates may read the target (plan 1.5)",
                      part=PART_DERIVED)
    return result("G-HIST", PASS, (), "no dataset column is declared as a look-back of the own target")


# Provenance: plan 5 G-KEYS (memorised calendar posing as skill); plan 1.3 roles.
def check_g_keys(columns: Mapping[str, Any], column_sets: Any) -> GuardResult:
    """G-KEYS: keys are never tree features; a key-derived column may only be router context.

    Rule: G-KEYS. column_sets is io.apply.apply_verdicts' outcome. BLOCK on a key-role column among the
    tree features or the router context, a column derived from a key-role column among the tree features,
    and a router_context-role column among the tree features.
    """
    keys = {c for c, f in columns.items() if _v(getattr(f, "role", None)) in KEY_ROLES}
    trees = tuple(getattr(column_sets, "tree_features", ()) or ())
    context = tuple(getattr(column_sets, "router_context", ()) or ())
    bad = []
    for c in trees + context:
        if c in keys:
            bad.append("%s (a key)" % c)
    for c in trees:
        f = columns.get(c)
        src = set(getattr(f, "derived_from", ()) or ()) & keys if f is not None else set()
        if src:
            bad.append("%s (derived from the key %s, a tree feature)" % (c, sorted(src)))
        if f is not None and _v(getattr(f, "role", None)) == "router_context":
            bad.append("%s (router context among the tree features)" % c)
    if bad:
        return result("G-KEYS", BLOCK, [b.split(" ")[0] for b in bad], "%d key or key-derived columns reach the "
                      "trees: %s" % (len(bad), _fmt(bad)),
                      fix="give a key-derived column the role router_context (read by the router only)")
    return result("G-KEYS", PASS, (), "no key or key-derived column is a tree feature (%d tree features, %d router "
                  "context columns)" % (len(trees), len(context)))


# Provenance: plan 5 G-SPLIT; NDVI 25-vs-44 (Part 426); pm25_split.check() never called (pm25_split.py:192-197).
# Owner ruling D (leave one region out) replaces the donor/test sets of the docstring: split.yaml holds only
# exclusions and seen_during_design, checked with split.loro_split_differences.
def check_g_split(split: Any, data_groups: Tuple[str, ...]) -> GuardResult:
    """G-SPLIT (quick): split lists are sets, sorted by the engine; the data's groups equal the split's.

    Rule: G-SPLIT. split is the loaded split.yaml (or split.LoroSplitSets). BLOCK on duplicates, a listed
    group the data do not hold, or a seen_during_design group that is excluded. Counts are printed, never
    used as the check.
    """
    try:
        sets = split if hasattr(split, "excluded") and isinstance(getattr(split, "excluded"), tuple) \
            else _split.loro_split_sets(split)
        diff = _split.loro_split_differences(sets, tuple(data_groups))
        groups = _split.groups_under_loro(sets, tuple(data_groups)) if not (
            diff.listed_not_in_data or diff.reported_and_excluded or diff.duplicates) else ()
    except RefusedError as exc:
        return result("G-SPLIT", BLOCK, (), "split.yaml refused: %s" % exc, part=PART_SPLIT,
                      fix="split.yaml holds only exclusions and seen_during_design, as sets")
    problems = []
    if diff.duplicates:
        problems.append("listed twice: %s" % _fmt(diff.duplicates))
    if diff.listed_not_in_data:
        problems.append("listed but not in the data: %s" % _fmt(diff.listed_not_in_data))
    if diff.reported_and_excluded:
        problems.append("seen_during_design and excluded: %s" % _fmt(diff.reported_and_excluded))
    details = {"data_groups": len(data_groups), "excluded": len(sets.excluded),
               "seen_during_design": len(sets.seen_during_design), "groups": len(groups)}
    if problems:
        return result("G-SPLIT", BLOCK, (), "split.yaml differs from the data: " + "; ".join(problems),
                      fix="list only groups the data hold; a seen_during_design group is never excluded",
                      part=PART_SPLIT, details=details)
    return result("G-SPLIT", PASS, (), "%d groups in the data, %d excluded, %d after exclusions (every one trained "
                  "and tested); seen_during_design: %d" % (len(data_groups), len(sets.excluded), len(groups),
                                                         len(sets.seen_during_design)), details=details)


# Provenance: plan 5 G-SUPPORT (NEW); 9.1 item 2f; D44 (thresholds signed); Q19. Under leave one region out
# (owner ruling D) the signed "3 test or 2 donor groups" reads "fewer than 3 groups refused, fewer than 14
# flagged" (plan 5); the 5-donor-group flag went with C8's folds.
SUPPORT_DONOR_NOT_JUDGED = "donor labels not judged here (check --deep reads them)"


def check_g_support(donor: Any, census_complete: Optional[bool], is_events: bool,
                    n_zero_observations: Optional[int], n_test_groups: int, n_donor_groups: int,
                    any_all_zero_unit: Optional[bool]) -> GuardResult:
    """G-SUPPORT: enough support to learn and to judge.

    Rule: G-SUPPORT, C15. donor: donor labels at the nowcast fit cut (an object with y), or None in the
    quick check (not judged there). census_complete: the grid census had no hole (None = not judged).
    BLOCK on: fewer than S5.support_min_distinct_values distinct donor values; an incomplete census (a
    presence-only table: "grid it to unit x step with zeros"); an event table with no zero observation;
    fewer than C15.min_groups groups. FLAG (report only): fewer than C15.flag_groups_below groups; no
    all-zero unit in the unit set.
    """
    blocks, flags, notes = [], [], []
    groups = int(n_test_groups)
    if groups < K.MIN_GROUPS:
        blocks.append("only %d groups (at least %d are needed: every group is tested and each router sees the "
                      "other groups' trees)" % (groups, K.MIN_GROUPS))
    elif groups < K.FLAG_GROUPS_BELOW:
        flags.append("%d groups: below %d the 1.96 jackknife interval is more than 10%% narrower than t(n-1)"
                     % (groups, K.FLAG_GROUPS_BELOW))
    if donor is not None:
        y = np.asarray(getattr(donor, "y", donor), dtype=np.float64)
        y = y[np.isfinite(y)]
        distinct = int(np.unique(y[:]).size) if y.size else 0
        if distinct < K.SUPPORT_MIN_DISTINCT_VALUES:
            blocks.append("the donor labels hold %d distinct values (at least %d)" % (distinct,
                                                                                    K.SUPPORT_MIN_DISTINCT_VALUES))
        notes.append("donor rows: %d valid labels, distinct values: %s" % (int(getattr(donor, "n_rows", y.size)),
                                                                           distinct if distinct < 3 else ">= 3"))
    else:
        notes.append(SUPPORT_DONOR_NOT_JUDGED)
    if census_complete is False:
        blocks.append("the target is not a complete unit x step census (a presence-only or holed table)")
    elif census_complete is None:
        notes.append("census not judged here (check --deep reads it)")
    if is_events and n_zero_observations is not None and int(n_zero_observations) == 0:
        blocks.append("the event table holds no zero observation (presence-only)")
    if any_all_zero_unit is False:
        flags.append("no unit's labels are all zero (the unit set is declared in AUDIT_CHECKLIST)")
    details = {"groups": groups, "notes": notes}
    if blocks:
        return result("G-SUPPORT", BLOCK, (), "; ".join(blocks + flags),
                      fix="grid it to unit x step with zeros; add groups or a target with more than one value",
                      details=details)
    if flags:
        return result("G-SUPPORT", FLAG, (), "; ".join(flags) + " (report only)", details=details)
    return result("G-SUPPORT", PASS, (), "%d groups; %s" % (groups, "; ".join(notes)), details=details)


def _data_selected_problem(name: str, f: Any, earliest_fit_cut_day: Optional[int], test_groups: Sequence[str],
                           exceptions: Sequence[Any]) -> Optional[str]:
    ds = getattr(f, "data_selected", None)
    if ds is None:
        return None
    if _exception_for(exceptions, name, None, kinds=("test_exposure",)) is not None:
        return None
    read_test = sorted(set(getattr(ds, "groups", ()) or ()) & set(test_groups))
    late = None
    day = _date_day(getattr(ds, "latest_date", None))
    if earliest_fit_cut_day is not None and day is not None and day > int(earliest_fit_cut_day):
        late = getattr(ds, "latest_date", None)
    if read_test or late:
        return "%s: a data-selected list that read %s%s, not disclosed as test-exposed by a signed entry%s" % (
            name, ("test groups %s" % _fmt(read_test, 3)) if read_test else "",
            (" rows up to %s, after the earliest fit cut" % late) if late else "",
            _unsigned_note(exceptions, name, None, kinds=("test_exposure",)))
    return None


# Provenance: plan 5 G-FACTS (NEW; headline + pre-registration); plan 1.3 data_selected; F15; the top-5 context
# list (cross_region_run89.py:887); R8's 'unanswered' flags ("G-FACTS blocks it at the headline").
def check_g_facts(columns: Mapping[str, Any], verdicts: Mapping[str, Any], target: Any,
                  co_measured_candidates: Tuple[str, ...], earliest_fit_cut_day: Optional[int],
                  test_groups: Tuple[str, ...], exceptions: Sequence[Any], headline: bool) -> GuardResult:
    """G-FACTS: unsigned timing facts cannot enter the headline.

    Rule: G-FACTS. Checked on every KEPT (entering) column: its timing facts are verified or signed
    'assumed' (timing_facts_signed); a time-varying column answers co_measured_with_target (R8 computed
    an unanswered one as 'no' and flagged it); every listed co-measured candidate answers it with a Part
    (co_measured_evidence). The target's legal range cites a documented source. A data-selected list is
    refused if it read test groups (under leave one region out every group is tested) or rows after the
    earliest fit cut, unless an exceptions.yaml test_exposure entry discloses it. headline True (the
    freeze gate, the pre-registration) BLOCKs; False only FLAGs. Roles appear only in package catalogs:
    the schema refuses a role in a store catalog, so that part always passes here.
    """
    status = BLOCK if headline else FLAG
    unsigned, unanswered, no_part, selected = [], [], [], []
    for name in sorted(columns):
        f = columns[name]
        if not _entering(name, verdicts):
            continue
        if not timing_facts_signed(f):
            unsigned.append("%s (%s%s)" % (name, _v(getattr(f, "fact_status", None)),
                                           ", no reviewer" if _v(getattr(f, "fact_status", None)) == "assumed" else ""))
        if _cadence_kind(f) not in UNLAGGED_KINDS and getattr(f, "co_measured_with_target", None) is None:
            unanswered.append(name)
        problem = _data_selected_problem(name, f, earliest_fit_cut_day, test_groups, exceptions)
        if problem:
            selected.append(problem)
    for name in co_measured_candidates:
        f = columns.get(name)
        if f is None:
            continue
        if getattr(f, "co_measured_with_target", None) is None or not getattr(f, "co_measured_evidence", None):
            no_part.append(name)
    uncited = not getattr(target, "legal_range_source", None)
    problems, cols = [], set()
    if unsigned:
        no_reviewer = [u for u in unsigned if "no reviewer" in u]
        others = [u for u in unsigned if "no reviewer" not in u]
        if others:
            problems.append("%d kept columns have unverified timing facts: %s" % (len(others), _fmt(others, 6)))
        if no_reviewer:
            problems.append("%d kept columns have 'assumed' timing facts with no reviewer (not signed): %s"
                            % (len(no_reviewer), _fmt([u.split(" ")[0] for u in no_reviewer], 10)))
        cols.update(u.split(" ")[0] for u in unsigned)
    if unanswered:
        problems.append("%d kept time-varying columns leave co_measured_with_target unanswered (R8 computed them "
                        "as 'no'): %s" % (len(unanswered), _fmt(unanswered, 6)))
        cols.update(unanswered)
    if no_part:
        problems.append("%d co-measured candidates lack an explicit answer with a Part: %s"
                        % (len(no_part), _fmt(no_part)))
        cols.update(no_part)
    if uncited:
        problems.append("the target's legal range cites no documented source (legal_range_source)")
        cols.add(getattr(target, "name", ""))
    if selected:
        problems.append("; ".join(selected))
        cols.update(s.split(":")[0] for s in selected)
    details = {"unsigned": [u.split(" ")[0] for u in unsigned], "co_measured_unanswered": unanswered,
               "co_measured_candidates": list(co_measured_candidates), "headline": bool(headline)}
    if problems:
        return result("G-FACTS", status, cols, "; ".join(problems),
                      fix="sign each kept column's timing facts (fact_status verified, or assumed with reviewed_by "
                          "and date), answer co_measured_with_target with a Part, cite the target's legal range, "
                          "disclose a data-selected list as test-exposed in a signed test_exposure entry (%s)"
                          % EXCEPTION_SHAPE, details=details)
    return result("G-FACTS", PASS, (), "every kept column's timing facts are verified or signed; co-measured "
                  "answers and the target's legal-range source are present", details=details)


# Provenance: plan 5 G-MISSING; plan 2.4 R30, 1.4 (a flagged column needs keep with evidence or ban;
# keep_unreviewed is not enough); SPEI/AMO vanishing in the last year.
def check_g_missing(flags: Any, verdicts: Mapping[str, Any]) -> GuardResult:
    """G-MISSING (quick): every column R30 flags carries keep-with-evidence or ban.

    Rule: G-MISSING, R30. flags: the R30 entry (a Derived, or {column: reasons}); None = not available to
    this check (FLAG, never a pass). BLOCK on a flagged column whose verdict is keep_unreviewed, or an
    entering verdict without an evidence Part. ban and conditional (both out of every run) pass.
    """
    if flags is None:
        return result("G-MISSING", FLAG, (), "R30's missing-value flags are not available to the quick check "
                      "(they come from the data); not evaluated", fix="run check --deep (or plan: derived.json R30)")
    value = getattr(flags, "value", flags) or {}
    bad, ok = [], []
    for c, reasons in sorted(value.items()):
        v = verdicts.get(c)
        verdict = _v(getattr(v, "verdict", None)) if v is not None else None
        reasons_text = ",".join(reasons) if not isinstance(reasons, str) else reasons
        if verdict in LEAVING_VERDICTS:
            ok.append(c)
        elif verdict == "keep_unreviewed" or verdict is None or not getattr(v, "evidence", None):
            bad.append("%s (%s; verdict %s)" % (c, reasons_text, verdict))
        else:
            ok.append(c)
    details = {"flagged": {c: list(r) if not isinstance(r, str) else [r] for c, r in sorted(value.items())},
               "ruled": ok}
    if bad:
        return result("G-MISSING", BLOCK, [b.split(" ")[0] for b in bad],
                      "%d R30-flagged columns lack a keep-with-evidence or ban verdict: %s" % (len(bad), _fmt(bad)),
                      fix="rule each flagged column in the Q34 review: keep with an evidence Part, or ban",
                      details=details)
    if value:
        return result("G-MISSING", FLAG, value, "%d R30-flagged columns, each ruled (report only): %s"
                      % (len(value), _fmt(sorted(value))), details=details)
    return result("G-MISSING", PASS, (), "R30 flags no column", details=details)


# ===================================================================================================
# Deep checks
# Provenance: plan 5 G-MISSING (deep: missingness per year; absent groups only by store fact); plan 2.4 R30;
# plan 3.2 and 3.3 flag 7 (all-NaN columns inside files that exist are FLAGGED, never blocked); plan 6.1.
def check_g_missing_deep(missing_share_by_group_year: Mapping[Tuple[str, str, int], float],
                         absent_groups: Mapping[str, Mapping[str, str]]) -> GuardResult:
    """G-MISSING (deep): missing shares per column x group x year, with store-declared absences separated.
    REPORT ONLY (FLAG or PASS, never BLOCK). The file-level stop is io.checks.check_missing_files.
    """
    all_missing: Dict[str, List[str]] = {}
    declared: Dict[str, List[str]] = {}
    by_column: Dict[str, List[float]] = {}
    for (column, group, year), share in missing_share_by_group_year.items():
        by_column.setdefault(column, []).append(float(share))
        if float(share) >= 1.0:
            target = declared if group in (absent_groups.get(column) or {}) else all_missing
            target.setdefault(column, []).append("%s/%s" % (group, year))
    summary = {c: {"cells": len(v), "mean_missing_share": round(float(np.mean(v)), 6),
                   "max_missing_share": round(float(np.max(v)), 6)} for c, v in sorted(by_column.items())}
    details = {"all_missing_group_years": {c: sorted(v) for c, v in sorted(all_missing.items())},
               "declared_absent_group_years": {c: len(v) for c, v in sorted(declared.items())},
               "summary": summary}
    if all_missing:
        text = "; ".join("%s all missing in %d group-years (e.g. %s)" % (c, len(v), _fmt(sorted(v), 3))
                         for c, v in sorted(all_missing.items())[:_SHOW])
        more = " ... (%d columns in all)" % len(all_missing) if len(all_missing) > _SHOW else ""
        return result("G-MISSING", FLAG, all_missing, "columns all missing in a group-year (inside files that exist, "
                      "or in a year inside the store's record that has no file, which G-MISSING (files) refuses) "
                      "(report only; R30 and the Q34 review rule them): " + text + more, details=details)
    return result("G-MISSING", PASS, (), "no column is all missing in a group-year outside its store's declared "
                  "absences (%d columns measured)" % len(by_column), details=details)


# ---- G-CADENCE: count and decide -------------------------------------------------------------------
YEAR_CADENCE = SimpleNamespace(kind="regular", length=1, unit="year")
MONTH_CADENCE = SimpleNamespace(kind="regular", length=1, unit="month")


def _next_coarser(cadence: Any) -> Optional[Any]:
    """D91 (accepted default): month -> year, N-day composite -> month, year -> none."""
    kind = _v(getattr(cadence, "kind", None))
    if kind == "regular" and _v(getattr(cadence, "unit", None)) == "month" and int(getattr(cadence, "length", 1)) == 1:
        return YEAR_CADENCE
    if kind == "composite_of_year":
        return MONTH_CADENCE
    return None


def _same_cadence(a: Any, b: Any) -> bool:
    from treeroute.io.steps import cadence_identity, cadence_view

    try:
        return cadence_identity(cadence_view(a)) == cadence_identity(cadence_view(b))
    except RefusedError:
        return False


def _group_index(codes: np.ndarray, periods: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """(row order, group starts) of the unit x period groups: rows sorted by one int64 key (no groupby)."""
    codes = np.asarray(codes, dtype=np.int64)
    periods = np.asarray(periods, dtype=np.int64)
    if codes.size == 0:
        return np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.int64)
    span = int(periods.max()) - int(periods.min()) + 1
    key = codes * span + (periods - int(periods.min()))
    order = np.argsort(key, kind="stable")
    ks = key[order]
    starts = np.flatnonzero(np.r_[True, ks[1:] != ks[:-1]])
    return order, starts


def _varying_counts(values: np.ndarray, codes: np.ndarray, periods: np.ndarray,
                    index: Optional[Tuple[np.ndarray, np.ndarray]] = None) -> Tuple[int, int]:
    """(unit x periods holding at least two non-missing values, those holding more than one distinct value):
    distinct > 1 exactly when the period's largest finite value exceeds its smallest."""
    order, starts = index if index is not None else _group_index(codes, periods)
    if starts.size == 0:
        return 0, 0
    v = np.asarray(values, dtype=np.float64)[order]
    fin = np.isfinite(v)
    cnt = np.add.reduceat(fin.astype(np.int64), starts)
    lo = np.minimum.reduceat(np.where(fin, v, np.inf), starts)
    hi = np.maximum.reduceat(np.where(fin, v, -np.inf), starts)
    judged = cnt >= 2
    return int(judged.sum()), int((judged & (hi > lo)).sum())


def cadence_counts(frame: pd.DataFrame, unit_codes: np.ndarray, steps: np.ndarray, columns: Mapping[str, Any],
                   target_cadence: Any, cache: Optional[Dict[Any, Any]] = None) -> Dict[str, Dict[str, Any]]:
    """The COUNT half of check_g_cadence over one frame (rows at the target's step). Per column: what is
    judged ('fine': a column at the target's step, fake-fine if constant within every unit x next-coarser
    period; 'coarse': a coarser column stored on target-step rows, contradicted if it varies inside its own
    period; 'static': varies inside a unit), and (judged, varying) unit x period counts. cache (keyword,
    one frame's keys): the unit x period groupings, shared by the frame's columns."""
    from treeroute.io.joins import coarse_periods
    from treeroute.io.steps import cadence_identity, cadence_view

    codes = np.asarray(unit_codes, dtype=np.int64)
    st = np.asarray(steps, dtype=np.int64)
    cache = {} if cache is None else cache

    def index_for(kind: str, cad: Any) -> Tuple[np.ndarray, np.ndarray]:
        key = (kind, cadence_identity(cadence_view(cad)) if cad is not None else None)
        if key not in cache:
            periods = np.zeros(len(codes), dtype=np.int64) if cad is None else coarse_periods(st, target_cadence, cad)
            cache[key] = _group_index(codes, periods)
        return cache[key]

    out: Dict[str, Dict[str, Any]] = {}
    for c in frame.columns:
        f = columns.get(c)
        if f is None:
            continue
        cad = getattr(f, "cadence", None)
        kind = _v(getattr(cad, "kind", None))
        if kind in ("epoch", "irregular") or cad is None:
            continue
        values = np.asarray(pd.to_numeric(frame[c], errors="coerce"), dtype=np.float64)
        if kind == "static":
            judged, varying = _varying_counts(values, codes, None, index_for("static", None))
            out[c] = {"judged_as": "static", "judged": judged, "varying": varying}
        elif _same_cadence(cad, target_cadence):
            coarser = _next_coarser(cad)
            if coarser is None:
                continue
            judged, varying = _varying_counts(values, codes, None, index_for("fine", coarser))
            out[c] = {"judged_as": "fine", "judged": judged, "varying": varying}
        else:
            try:
                idx = index_for("coarse", cad)
            except RefusedError:
                continue                         # a finer column cannot sit on target-step rows
            judged, varying = _varying_counts(values, codes, None, idx)
            out[c] = {"judged_as": "coarse", "judged": judged, "varying": varying}
    return out


def add_counts(total: Dict[str, Dict[str, Any]], part: Mapping[str, Mapping[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Sum per-column integer counts of one frame into a running total (other fields are kept)."""
    for c, counts in part.items():
        slot = total.setdefault(c, {})
        for k, v in counts.items():
            if isinstance(v, (int, np.integer)) and not isinstance(v, bool):
                slot[k] = int(slot.get(k, 0)) + int(v)
            elif isinstance(v, dict):
                sub = slot.setdefault(k, {})
                for kk, vv in v.items():
                    sub[kk] = int(sub.get(kk, 0)) + int(vv)
            else:
                slot.setdefault(k, v)
    return total


# Provenance: the conflict-count lesson (pm25_ban.py:139-140: monthly counts, zero in quiet regions, only LOOK
# constant); the constancy tolerance (pm25_architecture.py:139-160).
def decide_cadence(counts: Mapping[str, Mapping[str, Any]], entering: Optional[Set[str]] = None) -> GuardResult:
    """The DECIDE half of check_g_cadence over summed counts. Fake-fine is the plan's words exactly: constant
    within EVERY unit x next-coarser period judged (no period varies), so a sparse monthly count that is zero in
    quiet periods but varies where events happen is not fake-fine (the conflict-count lesson). A coarser or
    static column is contradicted when it varies in more than S5.cadence_constancy_tolerance of its periods (the
    0.1% that io.joins.join_coarser_column asserts). entering (keyword): when given, a
    finding on a column that does not enter any run (ban, conditional) is FLAGGED (its fact is still wrong and
    is listed for correction), and only an entering column is refused. READING for the owner to confirm: the
    approved G-CADENCE contract BLOCKs a contradicted or fake-fine cadence on ANY column; this downgrade of the
    columns no run reads is the check's reading, not the contract's."""
    tol = float(K.CADENCE_CONSTANCY_TOLERANCE)
    fake, contradicted, unjudged = [], [], []
    for c, n in sorted(counts.items()):
        judged, varying = int(n.get("judged", 0)), int(n.get("varying", 0))
        if judged == 0:
            unjudged.append(c)
            continue
        share = varying / float(judged)
        if n.get("judged_as") == "fine" and varying == 0:
            fake.append("%s (varies in %d of %d unit x coarser periods)" % (c, varying, judged))
        elif n.get("judged_as") in ("coarse", "static") and share > tol:
            contradicted.append("%s (declared %s, varies in %d of %d unit x periods, share %.4f)"
                                % (c, "static" if n.get("judged_as") == "static" else "coarser", varying, judged, share))
    details = {"counts": {c: dict(v) for c, v in sorted(counts.items())}, "not_judged": unjudged,
               "tolerance": tol}
    problems = []
    if fake:
        problems.append("%d columns are fake-fine (constant within every unit x next-coarser period): %s"
                        % (len(fake), _fmt(fake, 4)))
    if contradicted:
        problems.append("%d declared cadences are contradicted by the data: %s" % (len(contradicted),
                                                                                  _fmt(contradicted, 4)))
    cols = [x.split(" ")[0] for x in fake + contradicted]
    if problems:
        status = BLOCK
        if entering is not None and not (set(cols) & set(entering)):
            status = FLAG
            problems.append("none of these columns enters a run (report only until a verdict lets one in; a "
                            "reading for the owner to confirm: the approved contract refuses on any column)")
        elif entering is not None:
            out = sorted(set(cols) - set(entering))
            if out:
                problems.append("not entering (listed only): %s" % _fmt(out))
            cols = [c for c in cols if c in entering]
        details["entering_refused"] = [c for c in cols if entering is None or c in entering]
        return result("G-CADENCE", status, cols, "; ".join(problems),
                      fix="correct the column's cadence fact (declare the coarser step it really has), or rebuild "
                          "the column at the declared step", part=PART_CADENCE, details=details)
    if len(counts) == len(unjudged):
        return result("G-CADENCE", PASS, (), "no column could be judged (%d columns: none holds two values inside one "
                      "unit x next-coarser period; an annual column on an annual step cannot be fake-fine)"
                      % len(counts), details=details)
    return result("G-CADENCE", PASS, (), "%d columns judged, each matches its declared cadence on every unit (%d not "
                  "judged: fewer than two values per period)" % (len(counts) - len(unjudged), len(unjudged)),
                  details=details)


# Provenance: plan 5 G-CADENCE (deep, ALL units); fake-monthly column (Part 549); a misread count column
# (pm25_ban.py:139-140); the constancy assert pm25_architecture.py:139-160.
def check_g_cadence(frame: pd.DataFrame, unit_codes: np.ndarray, steps: np.ndarray, columns: Mapping[str, Any],
                    target_cadence: Any) -> GuardResult:
    """G-CADENCE: declared versus observed step on every unit; fake-fine columns refused.

    Rule: G-CADENCE. decide_cadence(cadence_counts(frame, ...)). BLOCK on a column at the target's step that
    is constant within every unit x next-coarser period (fake-fine, D91: month -> year, composite -> month,
    year -> none) and on a coarser or static column that varies inside its declared period.
    """
    return decide_cadence(cadence_counts(frame, unit_codes, steps, columns, target_cadence))


def _as_dtype(values: np.ndarray, dtype_text: Any) -> np.ndarray:
    """Values rounded through the column's declared dtype (a float32 output is compared as float32)."""
    try:
        dt = np.dtype(str(dtype_text)) if dtype_text else np.dtype(np.float64)
    except TypeError:
        dt = np.dtype(np.float64)
    if dt.kind != "f":
        return np.asarray(values, dtype=np.float64)
    with np.errstate(over="ignore", invalid="ignore"):
        return np.asarray(values, dtype=dt).astype(np.float64)


def _dtype_eps(dtype_text: Any) -> float:
    """The machine epsilon of a declared float dtype (0 for anything else)."""
    try:
        dt = np.dtype(str(dtype_text)) if dtype_text else np.dtype(np.float64)
    except TypeError:
        return 0.0
    return float(np.finfo(dt).eps) if dt.kind == "f" else 0.0


def values_match(a: np.ndarray, b: np.ndarray, rel_tol: float) -> np.ndarray:
    """True where two arrays agree: both NaN, or |a - b| <= rel_tol * max(|a|, |b|) (exact for zeros)."""
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    both_nan = np.isnan(a) & np.isnan(b)
    with np.errstate(invalid="ignore"):
        close = np.abs(a - b) <= rel_tol * np.maximum(np.abs(a), np.abs(b))
    return both_nan | close


# Provenance: plan 5 G-DERIVED (deep); plan 1.5; lags rebuilt at leads (Q33); history copied from the target row
# at a lead (Part 526). D92 (1,000 stride rows, rel tol 1e-9); D93 follows D54 a (the sample spans every row).
def check_g_derived(columns: Mapping[str, Any], script_values: pd.DataFrame, sample_rows: np.ndarray, grid: Any,
                    labels: Any, sources: pd.DataFrame, adjacency: Optional[pd.DataFrame],
                    target_cadence: Any = None) -> GuardResult:
    """G-DERIVED (recompute): every engineered column recomputed on a stride sample from its declaration.

    Rule: G-DERIVED, plan 1.5, G-LOCK. columns: the facts of the feature script's declared outputs;
    script_values / sources: one row per grid position (unit row x step, the keys-only DenseGrid order);
    sample_rows: grid positions. Each output is recomputed with check.recompute.recompute_declared_operation
    and rounded through its declared dtype; it must match the script within V1.check_sample_rel_tolerance
    (NaN matches NaN). BLOCK on any mismatch, an output the script did not return, and an operation the
    recompute does not know (an undeclared or unrecomputable engineered column). target_cadence (keyword
    addition) is the grid's step, which the calendar operations need.
    """
    from .recompute import RecomputeRefusal, recompute_declared_operation

    tol = float(K.CHECK_SAMPLE_REL_TOLERANCE)
    rows = np.asarray(sample_rows, dtype=np.int64)
    mismatch, unknown, absent = [], [], []
    matched: Dict[str, int] = {}
    for name in sorted(columns):
        f = columns[name]
        if name not in script_values.columns:
            absent.append(name)
            continue
        try:
            ref = recompute_declared_operation(f, sources, grid, labels, rows, adjacency,
                                               target_cadence=target_cadence)
        except RecomputeRefusal as exc:
            unknown.append("%s (%s)" % (name, exc))
            continue
        ref = _as_dtype(ref, getattr(f, "dtype", None))
        got = np.asarray(script_values[name].to_numpy(dtype=np.float64)[rows], dtype=np.float64)
        ok = values_match(got, ref, tol)
        if not ok.all():
            bad = np.flatnonzero(~ok)
            mismatch.append("%s (%d of %d sample rows differ, e.g. position %d: script %r, declaration %r)"
                            % (name, bad.size, rows.size, int(rows[bad[0]]), float(got[bad[0]]), float(ref[bad[0]])))
        else:
            matched[name] = int(rows.size)
    details = {"sample_rows": int(rows.size), "matched": matched, "tolerance": tol}
    problems = []
    if mismatch:
        problems.append("%d engineered columns differ from their declaration: %s" % (len(mismatch), _fmt(mismatch, 3)))
    if unknown:
        problems.append("%d engineered columns cannot be recomputed from their declaration: %s"
                        % (len(unknown), _fmt(unknown, 3)))
    if absent:
        problems.append("%d declared outputs were not returned by the script: %s" % (len(absent), _fmt(absent)))
    cols = [x.split(" ")[0] for x in mismatch + unknown] + absent
    if problems:
        return result("G-DERIVED", BLOCK, cols, "; ".join(problems),
                      fix="make the feature script compute exactly what each output declares (operation, sources, "
                          "trailing only), or correct the declaration", part=PART_DERIVED, details=details)
    return result("G-DERIVED", PASS, (), "%d engineered columns match their declaration on %d stride-sampled rows"
                  % (len(matched), rows.size), details=details)


# Provenance: plan 5 G-DERIVED ("no model fitted on the target inside a feature script": a static scan for .fit
# and feature_importances_); plan 1.5 Forbidden list.
def scan_feature_script(source_text: str) -> GuardResult:
    """G-DERIVED (static): refuse a feature script that fits a model (a .fit / .fit_transform / .fit_predict /
    .partial_fit call, or feature_importances_). A script that does not parse is refused too."""
    try:
        tree = ast.parse(source_text)
    except SyntaxError as exc:
        return result("G-DERIVED", BLOCK, (), "features/build.py does not parse: %s" % exc,
                      fix="fix the script's syntax")
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in FIT_CALLS:
            hits.append("line %d: .%s(...)" % (node.lineno, node.func.attr))
        elif isinstance(node, ast.Attribute) and node.attr in FIT_ATTRIBUTES:
            hits.append("line %d: .%s" % (node.lineno, node.attr))
        elif isinstance(node, ast.Name) and node.id in FIT_ATTRIBUTES:
            hits.append("line %d: %s" % (node.lineno, node.id))
    if hits:
        return result("G-DERIVED", BLOCK, (), "the feature script fits a model: %s" % _fmt(sorted(set(hits))),
                      fix="no model is fitted inside a feature script (plan 1.5); the engine's banks are the "
                          "only fitted objects")
    return result("G-DERIVED", PASS, (), "the feature script fits no model (static scan)")


def _trailing_steps(target_cadence: Any) -> Tuple[int, ...]:
    """R17's trailing windows (S2.history_trailing_years) in target steps, for a 1-month or 1-year step."""
    kind = _v(getattr(target_cadence, "kind", None))
    unit = _v(getattr(target_cadence, "unit", None))
    length = int(getattr(target_cadence, "length", 1) or 1)
    if kind != "regular" or length != 1:
        return ()
    per_year = K.MONTHS_PER_YEAR if unit == "month" else (1 if unit == "year" else 0)
    return tuple(int(y) * per_year for y in K.HISTORY_TRAILING_YEARS if per_year)


# Provenance: plan 5 G-HIST (runtime: "by a sample match"). Accepted default: lags 0-3 and the R17 trailing
# windows, the D79 tolerance, stride rows at or before the donor train end.
def check_g_hist_sample(columns: Mapping[str, Any], values: pd.DataFrame, grid: Any, labels: Any,
                        sample_rows: np.ndarray, target_cadence: Any = None) -> GuardResult:
    """G-HIST (runtime): refuse any dataset column that MATCHES a lag or trailing mean of the unit's own
    target on a sample, whatever its declaration says.

    Rule: G-HIST, G-LOCK. values: the dataset columns, one row per grid position; sample_rows: grid
    positions (the caller takes them at or before the donor train end). The look-backs (V4.hist_sample_lags
    and, when target_cadence is given, R17's trailing windows) are read only through labels.asof_rows. A
    column matches a look-back when every sample row where the column is finite has the look-back finite
    and equal within V1.check_sample_rel_tolerance, over at least S5.support_min_distinct_values distinct
    values. BLOCK on a match. target_cadence is a keyword addition (the trailing windows need the step).
    """
    tol = float(K.CHECK_SAMPLE_REL_TOLERANCE)
    rows = np.asarray(sample_rows, dtype=np.int64)
    n = int(grid.n_steps)
    first = int(grid.first_step)
    unit_rows = rows // n
    steps = first + (rows - unit_rows * n)
    looks: Dict[str, np.ndarray] = {}
    for k in K.HIST_SAMPLE_LAGS:
        looks["lag %d" % k] = labels.asof_rows(unit_rows, steps, int(k), purpose="G-HIST sample match")
    for w in (_trailing_steps(target_cadence) if target_cadence is not None else ()):
        stack = np.vstack([labels.asof_rows(unit_rows, steps, j, purpose="G-HIST sample match") for j in range(w)])
        with np.errstate(invalid="ignore"), warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)       # a row with no finite look-back gives NaN
            looks["trailing mean %d" % w] = np.nanmean(np.where(np.isfinite(stack), stack, np.nan), axis=0) \
                if np.isfinite(stack).any() else np.full(rows.size, np.nan)
    hits = []
    for name in sorted(columns):
        if name not in values.columns:
            continue
        v = np.asarray(pd.to_numeric(values[name], errors="coerce"), dtype=np.float64)[rows]
        have = np.isfinite(v)
        if np.unique(v[have]).size < K.SUPPORT_MIN_DISTINCT_VALUES:
            continue
        dtype = getattr(columns[name], "dtype", None)
        for label, y in looks.items():
            yy = _as_dtype(y[have], dtype)           # a copy stored in the column's dtype is still a copy
            if np.isfinite(yy).all() and values_match(v[have], yy, tol).all():
                hits.append("%s (equals the own target's %s on %d sample rows)" % (name, label, int(have.sum())))
                break
    details = {"sample_rows": int(rows.size), "look_backs": sorted(looks)}
    if hits:
        return result("G-HIST", BLOCK, [h.split(" ")[0] for h in hits],
                      "%d dataset columns copy the unit's own target: %s" % (len(hits), _fmt(hits, 4)),
                      fix="drop the column: the engine builds the own-history block (R17) through the label vault",
                      part=PART_DERIVED, details=details)
    return result("G-HIST", PASS, (), "no dataset column matches a look-back of the own target on %d sample rows"
                  % rows.size, details=details)


# Provenance: plan 5 G-CALENDAR (runtime); forecast_arms.py:127-171; row-shift lags across gaps
# (fire_architecture.py:273, 294-304); F1.
def check_g_calendar(read_unit: np.ndarray, read_time: np.ndarray, row_unit: np.ndarray, row_time: np.ndarray,
                     expected_back: Optional[int], is_events: bool) -> GuardResult:
    """G-CALENDAR: every look-back read is in the same unit and exactly where it should be.

    Rule: G-CALENDAR. Grids: each read exactly expected_back steps before its row, in the row's unit.
    Events: each read in the row's unit and dated strictly before the row's issue date. BLOCK otherwise.
    Integer time only.
    """
    ru, rt = np.asarray(read_unit), np.asarray(read_time)
    wu, wt = np.asarray(row_unit), np.asarray(row_time)
    if not (ru.shape == rt.shape == wu.shape == wt.shape):
        return result("G-CALENDAR", BLOCK, (), "the read and row arrays differ in length",
                      fix="pass one read per served row")
    if rt.dtype.kind not in "iu" or wt.dtype.kind not in "iu":
        return result("G-CALENDAR", BLOCK, (), "times must be integer steps or days (got %s, %s)" % (rt.dtype, wt.dtype),
                      fix="use the integer step index (io.steps.step_index)")
    other_unit = ru != wu
    if is_events:
        wrong = rt >= wt
        what = "dated at or after the issue date"
    else:
        if expected_back is None:
            return result("G-CALENDAR", BLOCK, (), "a grid read needs its expected look-back",
                          fix="pass L for grid reads")
        wrong = (wt - rt) != int(expected_back)
        what = "not exactly %d steps back" % int(expected_back)
    n_unit, n_wrong = int(other_unit.sum()), int((wrong & ~other_unit).sum())
    details = {"reads": int(ru.size), "other_unit": n_unit, "wrong_time": n_wrong}
    if n_unit or n_wrong:
        bad = np.flatnonzero(other_unit | wrong)[:3]
        return result("G-CALENDAR", BLOCK, (), "%d reads leave their unit and %d are %s (e.g. rows %s)"
                      % (n_unit, n_wrong, what, bad.tolist()),
                      fix="read look-backs only through the dense-grid predecessor lookup "
                          "(io.steps.predecessor_index), never by a row shift", details=details)
    return result("G-CALENDAR", PASS, (), "%d look-back reads are in their own unit and exactly where they belong"
                  % ru.size, details=details)


# ---- G-SENTINEL deep: count and decide ------------------------------------------------------------
def sentinel_counts(frame: pd.DataFrame, columns: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    """The COUNT half of check_g_sentinel_deep over RAW (unmasked) values. Per column: each known fill code
    (V3.known_fill_codes) present but not declared, and the near-sentinel count (abs >= 2^30, below the
    1e30 mask, not a declared fill) unless the column opts out. Key-role and non-numeric columns are
    skipped. The equality test is io.sentinel's (float64 and the column's own float type)."""
    from treeroute.io.sentinel import _hits

    out: Dict[str, Dict[str, Any]] = {}
    for c in frame.columns:
        f = columns.get(c)
        if f is None or _v(getattr(f, "role", None)) in KEY_ROLES:
            continue
        s = frame[c]
        if pd.api.types.is_bool_dtype(s) or not pd.api.types.is_numeric_dtype(s):
            continue
        raw = s.to_numpy()
        values = raw.astype(np.float64) if raw.dtype.kind in "iu" else np.asarray(raw)
        declared = tuple(float(x) for x in (getattr(f, "fill_values", ()) or ()))
        v64 = values.astype(np.float64)
        with np.errstate(invalid="ignore"):
            big = np.abs(v64) >= K.SENTINEL_MASK_ABS
        declared_hit = _hits(values, declared) & ~big if declared else np.zeros(len(values), dtype=bool)
        codes: Dict[str, int] = {}
        undeclared = [code for code in K.KNOWN_FILL_CODES if code not in declared]
        candidate = np.isin(v64, np.asarray(undeclared, dtype=np.float64))
        if values.dtype.kind == "f" and values.dtype != np.float64:
            with np.errstate(over="ignore"):
                cast = np.asarray(undeclared, dtype=values.dtype)
            candidate |= np.isin(values, cast[np.isfinite(cast)])
        if candidate.any():                       # per-code counts only on the few candidate values
            sub = values[candidate]
            sub64 = sub.astype(np.float64)
            with np.errstate(invalid="ignore"):
                sub_big = np.abs(sub64) >= K.SENTINEL_MASK_ABS
            for code in undeclared:
                hit = _hits(sub, (code,))
                if abs(code) < K.SENTINEL_MASK_ABS:
                    hit &= ~sub_big                   # _hits also marks every abs >= 1e30 value
                else:
                    hit &= np.isclose(sub64, code, rtol=float(K.LARGE_FILL_CODE_REL_TOLERANCE), atol=0.0)
                n = int(hit.sum())
                if n:
                    codes["%r" % code] = n
        near = 0
        if not bool(getattr(f, "near_sentinel_optout", False)):
            with np.errstate(invalid="ignore"):
                near = int((np.isfinite(v64) & ~big & ~declared_hit & (np.abs(v64) >= K.SENTINEL_FLAG_ABS)).sum())
        out[c] = {"undeclared_codes": codes, "near_sentinel": near, "rows": int(len(values))}
    return out


def decide_sentinel(counts: Mapping[str, Mapping[str, Any]]) -> GuardResult:
    flagged = []
    for c, n in sorted(counts.items()):
        codes = n.get("undeclared_codes") or {}
        if codes or int(n.get("near_sentinel", 0)):
            parts = ["code %s x %d" % kv for kv in sorted(codes.items())]
            if int(n.get("near_sentinel", 0)):
                parts.append("abs >= 2^30 x %d" % int(n["near_sentinel"]))
            flagged.append("%s (%s)" % (c, ", ".join(parts)))
    details = {"counts": {c: dict(v) for c, v in sorted(counts.items()) if v.get("undeclared_codes") or v.get("near_sentinel")}}
    if flagged:
        return result("G-SENTINEL", FLAG, [x.split(" ")[0] for x in flagged],
                      "%d columns hold known fill codes they do not declare, or near-sentinel magnitudes (report "
                      "only; the read-time mask removes declared codes and abs >= 1e30 only): %s"
                      % (len(flagged), _fmt(flagged, 5)),
                      fix="declare the provider's fill codes in the store catalog (fill_values), or opt the column "
                          "out of the near-sentinel flag when such magnitudes are real", details=details)
    return result("G-SENTINEL", PASS, (), "no undeclared fill code and no near-sentinel magnitude in %d columns"
                  % len(counts), details=details)


# Provenance: plan 5 G-SENTINEL (deep: flags known codes present but undeclared); the -2^31 poison in 47/133
# regions; a derived near-sentinel missed by panel_sentinel.py:15-20; a provider float fill. D94 (accepted).
def check_g_sentinel_deep(frame: pd.DataFrame, columns: Mapping[str, Any]) -> GuardResult:
    """G-SENTINEL (deep): known fill codes present but undeclared; near-sentinel magnitudes. FLAG only."""
    return decide_sentinel(sentinel_counts(frame, columns))


# ---- G-RANGE: count and decide ---------------------------------------------------------------------
def range_counts(frame: pd.DataFrame, columns: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    """The COUNT half of check_g_range over MASKED values: per column with a legal range, the non-missing
    values and those outside the range."""
    out: Dict[str, Dict[str, Any]] = {}
    for c in frame.columns:
        f = columns.get(c)
        lr = getattr(f, "legal_range", None) if f is not None else None
        if lr is None or _v(getattr(f, "role", None)) in KEY_ROLES:
            continue
        s = frame[c]
        if pd.api.types.is_bool_dtype(s) or not pd.api.types.is_numeric_dtype(s):
            continue
        v = s.to_numpy(dtype=np.float64)
        ok = np.isfinite(v)
        lo, hi = float(lr[0]), float(lr[1])
        out[c] = {"nonmissing": int(ok.sum()), "below": int((ok & (v < lo)).sum()), "above": int((ok & (v > hi)).sum())}
    return out


def _units_problems(columns: Mapping[str, Any]) -> List[str]:
    """One unit per physical quantity, as far as the facts identify a quantity without a units library: the
    members of a sum group share one unit string; a value-preserving engineered column (a copy, a lag, a
    hold, a trailing mean) carries its single parent's unit string."""
    problems = []
    groups: Dict[str, Set[str]] = {}
    for name, f in columns.items():
        g = getattr(f, "sum_group", None)
        if g and getattr(f, "units", None):
            groups.setdefault(g, set()).add(str(f.units))
    for g, units in sorted(groups.items()):
        if len(units) > 1:
            problems.append("sum group %s mixes units %s" % (g, sorted(units)))
    preserving = ("", "lag", "hold_last_observed", "trailing_mean")
    for name, f in sorted(columns.items()):
        src = list(getattr(f, "derived_from", ()) or ())
        if len(src) != 1 or _operation_head(f) not in preserving or src[0] not in columns:
            continue
        parent = columns[src[0]]
        pu, cu = getattr(parent, "units", None), getattr(f, "units", None)
        if pu and cu and str(pu) != str(cu) and getattr(parent, "has_store_facts", True):
            problems.append("%s is a %s of %s but declares units %r, not %r"
                            % (name, _operation_head(f) or "copy", src[0], cu, pu))
    return problems


# What the approved G-RANGE contract names that this check does not build (printed in every G-RANGE line).
RANGE_NOT_BUILT = ("not built: (1) D96's 'one unit per physical quantity by UDUNITS dimension equality': no units "
                   "library is installed and the G-NONAMES scan forbids unit spellings in engine code, so one unit per "
                   "quantity is checked only where the facts identify the quantity (one unit string per sum group; a "
                   "copy, lag, hold or trailing mean carries its single parent's unit string); (2) the output-side "
                   "pre-clip rate and calibration ratio per arm: both exist only after a run (R28, R34; "
                   "layer/decide.py prints each arm's pre-clip counts), and check runs before any plan")
RANGE_NOT_BUILT_SHORT = ("not built here: D96's UDUNITS dimension test (unit strings of sum groups and single-parent "
                         "copies only) and the per-arm pre-clip rate and calibration ratio (run outputs)")


def decide_range(counts: Mapping[str, Mapping[str, Any]], columns: Mapping[str, Any],
                 target_counts: Optional[Mapping[str, Any]] = None) -> GuardResult:
    """The DECIDE half of check_g_range: D95 (refuse above V2.range_refuse_share, else flag with the count),
    the target's donor rows judged the same way (the share outside and at the bounds printed), and the
    one-unit-per-quantity facts."""
    share_max = float(K.RANGE_REFUSE_SHARE)
    refuse, flag = [], []
    for c, n in sorted(counts.items()):
        out = int(n.get("below", 0)) + int(n.get("above", 0))
        nn = int(n.get("nonmissing", 0))
        if not out:
            continue
        text = "%s (%d of %d outside: %d below, %d above)" % (c, out, nn, n.get("below", 0), n.get("above", 0))
        (refuse if nn and out / float(nn) > share_max else flag).append(text)
    target_text = None
    if target_counts:
        nn = int(target_counts.get("nonmissing", 0))
        out = int(target_counts.get("below", 0)) + int(target_counts.get("above", 0))
        at = int(target_counts.get("at_bounds", 0))
        target_text = "target %s donor rows: %d of %d outside the cited range, %d at the bounds" % (
            target_counts.get("name", ""), out, nn, at)
        if out:
            (refuse if nn and out / float(nn) > share_max else flag).append(target_text)
    units = _units_problems(columns)
    details = {"counts": {c: dict(v) for c, v in sorted(counts.items())}, "refuse_share": share_max,
               "target": dict(target_counts or {}), "units": units,
               "not_built": RANGE_NOT_BUILT}
    cols = [x.split(" ")[0] for x in refuse + flag]
    if refuse or units:
        parts = []
        if refuse:
            parts.append("%d columns are out of their legal range above %.1f%% of their values: %s"
                         % (len(refuse), 100 * share_max, _fmt(refuse, 4)))
        if units:
            parts.append("units: %s" % _fmt(units, 4))
        if flag:
            parts.append("flagged under the share: %s" % _fmt(flag, 4))
        return result("G-RANGE", BLOCK, cols, "; ".join(parts) + "; " + RANGE_NOT_BUILT_SHORT,
                      fix="correct the column's units or legal-range facts (or its data); one unit string per "
                          "physical quantity", details=details)
    if flag:
        return result("G-RANGE", FLAG, cols, "%d columns hold values outside their legal range at or under %.1f%% "
                      "(report only): %s; %s" % (len(flag), 100 * share_max, _fmt(flag, 5), RANGE_NOT_BUILT_SHORT),
                      details=details)
    text = "every value of %d ranged columns lies inside its legal range" % len(counts)
    if target_text:
        text += "; " + target_text
    return result("G-RANGE", PASS, (), text + "; " + RANGE_NOT_BUILT_SHORT, details=details)


# Provenance: plan 5 G-RANGE (deep); Kelvin columns; a density column at 368,684; negative predictions of a
# non-negative target. D95 (refuse above 0.1%, else flag with the count); D96 see decide_range.
def check_g_range(frame: pd.DataFrame, columns: Mapping[str, Any], target: Any, donor: Any) -> GuardResult:
    """G-RANGE: units and legal ranges on inputs and outputs; one unit per physical quantity.

    Rule: G-RANGE. decide_range(range_counts(frame, columns), columns, the target's donor counts). donor
    holds the target's donor labels (an object with y) or None.
    """
    tc = None
    if donor is not None:
        tc = target_range_counts(np.asarray(getattr(donor, "y", donor), dtype=np.float64),
                                 getattr(target, "legal_range", None), getattr(target, "name", ""))
    return decide_range(range_counts(frame, columns), columns, tc)


def target_range_counts(y: np.ndarray, legal_range: Any, name: str) -> Dict[str, Any]:
    y = np.asarray(y, dtype=np.float64)
    ok = np.isfinite(y)
    if legal_range is None:
        return {"name": name, "nonmissing": int(ok.sum()), "below": 0, "above": 0, "at_bounds": 0}
    lo, hi = float(legal_range[0]), float(legal_range[1])
    return {"name": name, "nonmissing": int(ok.sum()), "below": int((ok & (y < lo)).sum()),
            "above": int((ok & (y > hi)).sum()), "at_bounds": int((ok & ((y == lo) | (y == hi))).sum())}


# Provenance: plan 5 G-JOIN (deep + runtime); the assembler reverting 49 columns while printing OK (Part 326).
def check_g_join(reports: Tuple[Any, ...], column_set_ok: Mapping[str, bool],
                 refusals: Optional[Mapping[str, str]] = None,
                 report_only: Optional[Mapping[str, str]] = None,
                 rows_without_file: Optional[Mapping[str, int]] = None) -> GuardResult:
    """G-JOIN (deep): every join was 1:1 with an unchanged row count; every table's column set equals its
    catalog.

    Rule: G-JOIN. reports: every io.joins.JoinReport of the deep pass; column_set_ok: {table: its column set
    equals its catalog (io.checks.check_column_set)}; refusals (keyword addition): {join or table: the
    refusal text} for a join or column-set check that refused (a duplicated key, a NaN key, a column-set
    difference), which leaves no JoinReport. BLOCK on any changed row count, refusal or column-set
    difference. report_only (keyword addition): {join or table: the problem} of a store a run reads no column
    from (the pipeline reader takes each needed column from the FIRST driver store that holds it; check/deep.py
    read_plan): the run never joins it, so its problems are FLAGGED, with the fix to remove the store from
    dataset.yaml or to declare it fully. rows_without_file (keyword addition): {store: target rows of the years
    (inside the store's record) or groups for which the store holds NO file}: those rows enter no join, so no
    JoinReport counts them; they are added to the unmatched count (NaN, then R30; G-MISSING (files) refuses the
    missing files).
    """
    changed = ["%s (%d -> %d rows)" % (r.what, r.left_rows, r.out_rows) for r in reports if r.out_rows != r.left_rows]
    bad_sets = sorted(t for t, ok in column_set_ok.items() if not ok)
    refused = sorted((refusals or {}).items())
    unmatched = sum(int(r.unmatched_left) for r in reports)
    no_file = {k: int(v) for k, v in sorted((rows_without_file or {}).items()) if int(v)}
    details = {"joins": len(reports), "tables": len(column_set_ok), "unmatched_left_rows": unmatched,
               "rows_without_file": no_file, "refusals": dict(refused)}
    no_file_text = (" and %d more lie in years or groups a store holds no file for (%s)"
                    % (sum(no_file.values()), _fmt(["%s: %d" % kv for kv in no_file.items()], 3))) if no_file else ""
    problems = []
    if changed:
        problems.append("%d joins changed the row count: %s" % (len(changed), _fmt(changed, 4)))
    if refused:
        problems.append("%d joins or column sets refused: %s" % (len(refused), _fmt(["%s: %s" % kv for kv in refused], 2)))
    if bad_sets:
        problems.append("%d tables' column sets differ from their catalogs: %s" % (len(bad_sets), _fmt(bad_sets)))
    noted = sorted((report_only or {}).items())
    details["report_only"] = dict(noted)
    if problems:
        if noted:
            problems.append("report only (stores a run reads no column from): %s"
                            % _fmt(["%s: %s" % kv for kv in noted], 2))
        return result("G-JOIN", BLOCK, (), "; ".join(problems),
                      fix="one row per key on each side (no duplicated unit x step); declare every stored column "
                          "in its store catalog and remove declared columns the files lack", part=PART_JOIN,
                      details=details)
    if noted:
        return result("G-JOIN", FLAG, (), "%d joins were 1:1 (%d target rows had no driver row inside a store file%s); "
                      "stores a run reads no column from (the reader takes each column from the first store that "
                      "holds it) cannot be joined or differ from their catalogs (report only): %s"
                      % (len(reports), unmatched, no_file_text, _fmt(["%s: %s" % kv for kv in noted], 3)),
                      fix="remove an unused store from dataset.yaml, or give it the unit key and declare every column",
                      part=PART_JOIN, details=details)
    return result("G-JOIN", PASS, (), "%d joins were 1:1 with unchanged row counts (%d target rows had no driver row "
                  "inside a store file%s: NaN, then R30); %d tables match their catalogs"
                  % (len(reports), unmatched, no_file_text, len(column_set_ok)), details=details)


# Provenance: plan 5 G-LINEAGE ("deep flags reconstructions"); a sum-group member rebuilt from the others
# (defo_ban.py:28-34). D97 (accepted default): declared sum groups only, a banned member recoverable as the
# group total minus the kept members.
def flag_lineage_reconstructions(frame: pd.DataFrame, columns: Mapping[str, Any],
                                 verdicts: Mapping[str, Any]) -> GuardResult:
    """G-LINEAGE (deep): flag kept columns that reconstruct a banned one. FLAG only.

    A declared sum group whose members' row sum is constant on the sample (within V1.check_sample_rel_tolerance
    of its mean, over every row where all members are finite) lets a banned member be rebuilt as the total
    minus the others; when every other member enters, the group is flagged.
    """
    tol = float(K.CHECK_SAMPLE_REL_TOLERANCE)
    groups: Dict[str, List[str]] = {}
    for name, f in columns.items():
        g = getattr(f, "sum_group", None)
        if g:
            groups.setdefault(g, []).append(name)
    flagged = []
    for g, members in sorted(groups.items()):
        members = sorted(members)
        banned = [m for m in members if verdict_of(verdicts, m) in LEAVING_VERDICTS]
        kept = [m for m in members if m not in banned]
        if not banned or not kept or len(banned) != 1 or any(not _entering(m, verdicts) for m in kept):
            continue
        if not all(m in frame.columns for m in members):
            continue
        block = np.vstack([np.asarray(pd.to_numeric(frame[m], errors="coerce"), dtype=np.float64) for m in members])
        ok = np.isfinite(block).all(axis=0)
        if ok.sum() < K.SUPPORT_MIN_DISTINCT_VALUES:
            continue
        total = block[:, ok].sum(axis=0)
        centre = float(np.mean(total))
        # the tolerance: V1's, or the rounding of the members' declared dtypes when they are stored coarser
        eps = sum(_dtype_eps(getattr(columns[m], "dtype", None)) for m in members)
        if np.all(np.abs(total - centre) <= max(tol, eps) * max(abs(centre), 1.0)):
            flagged.append("%s: %s (banned) = %.6g minus %s (kept)" % (g, banned[0], centre, ", ".join(kept)))
    if flagged:
        return result("G-LINEAGE", FLAG, [f.split(":")[1].split(" ")[1] for f in flagged],
                      "%d sum groups let a banned member be rebuilt from kept members: %s" % (len(flagged), _fmt(flagged, 3)),
                      fix="give the whole sum group one verdict (plan 1.4)",
                      details={"reconstructions": flagged})
    return result("G-LINEAGE", PASS, (), "no banned sum-group member can be rebuilt from kept members on the sample",
                  details={"sum_groups": len(groups)})


__all__ = ["GuardResult", "GuardStatus", "PASS", "FLAG", "BLOCK", "result", "worst", "timing_facts_signed",
           "check_g_closed", "check_g_lag", "check_g_epoch", "check_g_lineage", "list_co_measured_candidates",
           "check_g_hist_declared", "check_g_keys", "check_g_split", "check_g_support", "check_g_facts",
           "check_g_missing", "check_g_missing_deep", "check_g_cadence", "cadence_counts", "decide_cadence",
           "check_g_derived", "scan_feature_script", "check_g_hist_sample", "check_g_calendar",
           "check_g_sentinel_deep", "sentinel_counts", "decide_sentinel", "check_g_range", "range_counts",
           "decide_range", "target_range_counts", "check_g_join", "flag_lineage_reconstructions", "add_counts",
           "values_match"]
