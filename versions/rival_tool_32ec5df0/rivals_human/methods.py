"""The M-runner interface: published methods with their own fit (SPEC_HUMAN.txt 6; PROT H7; PLAN 3.6).

A runner is a module (the registry's `runner`, under adapters/) with
    fit(ctx, rival, lead, fit_set) -> params            (JSON-able; labels only through ctx.fit_labels(fit_set),
                                                         answered only inside this fit and only for this fit_set)
    predict(ctx, rival, lead, params, score_set) -> DataFrame(unit, group, time, issue, lead, pre, info_end,
                                                             target_obs_end)
The tool calls them in tune and refit; runners never pick (one configuration, published settings). Every output is
checked here: one row per key of the score set, pre finite or NaN (+-inf refuses), the T1 / T2 rule of the lead's
tier on every predicted row (a shifted-label runner refuses, PLAN R8), and params that survive a JSON round trip.
"""
# Provenance: SPEC_HUMAN.txt 6 (M runner contract), 1.5 (timing), 1.9 (M kind: F0, identity comparator);
# PROT H7 (fit up to each cut; read labels up to the T2 step, never refit on them).

import importlib
import json
import sys
from typing import Any, Dict, Mapping, Tuple

import numpy as np
import pandas as pd

from rivals_human import config as C
from rivals_human import index as IX
from rivals_human.common import refuse


def load_runner(rival: Mapping[str, Any]):
    spec = str(rival["runner"])
    if str(C.BUILD_ROOT) not in sys.path:
        sys.path.insert(0, str(C.BUILD_ROOT))
    m = importlib.import_module(spec)
    for fn in ("fit", "predict"):
        if not callable(getattr(m, fn, None)):
            refuse("runner %s has no %s(...) (spec 6: fit(ctx, rival, lead, fit_set), predict(ctx, rival, lead, "
                   "params, score_set))" % (spec, fn))
    return m


def run_fit(runner: Any, ctx: IX.AdapterCtx, rival: Mapping[str, Any], lead: int, fit_set: str) -> Dict[str, Any]:
    if fit_set not in C.FIT_SETS:
        refuse("internal: a runner is fitted on a fit set %s, not %r" % (C.FIT_SETS, fit_set))
    if isinstance(ctx, IX.AdapterCtx):
        with ctx._fitting(fit_set):                  # fit_labels answers this fit set only, during this fit only
            params = runner.fit(ctx, dict(rival), int(lead), fit_set)
    else:                                            # a test's stand-in context (no slim behind it)
        params = runner.fit(ctx, dict(rival), int(lead), fit_set)
    try:
        text = json.dumps(params, sort_keys=True, allow_nan=True)
    except (TypeError, ValueError) as exc:
        refuse("runner %s returned params that are not JSON-able (%s)" % (rival["runner"], exc))
    return json.loads(text)


def run_predict(runner: Any, ctx: IX.AdapterCtx, rival: Mapping[str, Any], lead: int, params: Any, score_set: str,
                expected_keys: pd.DataFrame, tier: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """The runner's predictions in the order of expected_keys, checked."""
    out = runner.predict(ctx, dict(rival), int(lead), params, score_set)
    what = "runner %s lead %d set %s" % (rival["id"], int(lead), score_set)
    if not isinstance(out, pd.DataFrame):
        refuse("%s returned %s, not a DataFrame" % (what, type(out).__name__))
    miss = [c for c in C.RUNNER_COLUMNS if c not in out.columns]
    if miss:
        refuse("%s: the output lacks %s (spec 6: keys, pre, info_end, target_obs_end)" % (what, miss))
    if out.duplicated(subset=list(C.JOIN_KEYS)).any():
        refuse("%s names a key twice" % what)
    ek = expected_keys[list(C.KEYS)].reset_index(drop=True).copy()
    ek["_pos"] = np.arange(len(ek))
    o = out[list(C.RUNNER_COLUMNS)].copy()
    for k in ("unit", "group"):
        ek[k] = ek[k].astype(str)
        o[k] = o[k].astype(str)
    j = ek.merge(o, on=list(C.JOIN_KEYS), how="outer", indicator=True, suffixes=("", "_out"))
    if (j["_merge"] != "both").any():
        refuse("%s: %d keys of the set have no prediction, %d predictions name no key of the set"
               % (what, int((j["_merge"] == "left_only").sum()), int((j["_merge"] == "right_only").sum())))
    j = j.sort_values("_pos").reset_index(drop=True)
    pre = j["pre"].to_numpy(np.float64)
    if np.isinf(pre).any():
        refuse("%s: %d infinite predictions" % (what, int(np.isinf(pre).sum())))
    if j[C.COL_INFO_END].isna().any():
        refuse("%s: info_end is missing on %d rows" % (what, int(j[C.COL_INFO_END].isna().sum())))
    timing = IX.Timing(ctx.run, rival, lead)
    rec = IX.check_tier_timing(tier, timing, j[list(C.KEYS)], j[C.COL_INFO_END].to_numpy(np.int64),
                               j[C.COL_TARGET_OBS_END].to_numpy(np.float64), np.isfinite(pre), what)
    rec.update(rows=int(len(j)), predicted=int(np.isfinite(pre).sum()))
    frame = j[list(C.KEYS)].copy()
    frame["pre"] = pre
    frame[C.COL_INFO_END] = j[C.COL_INFO_END].to_numpy(np.int64)
    frame[C.COL_TARGET_OBS_END] = j[C.COL_TARGET_OBS_END].to_numpy(np.float64)
    return frame, rec
