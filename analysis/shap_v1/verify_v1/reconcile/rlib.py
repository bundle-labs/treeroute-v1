"""Round 14 reconciler: shared helpers (paths, the official-file open log, flattening, tolerant comparison).

Read-only on every file outside V\\reconcile; writes only into V\\reconcile.
"""
import datetime
import hashlib
import json
import math
import os

SHAP = r"D:\treeroute\analysis\shap_v1"
V = SHAP + r"\verify_v1"
RC = V + r"\reconcile"
WORK = RC + r"\work"
PROBLEMS = ("coral", "defo", "fire", "pm25", "ndvi")
TOL = 1e-9
OPEN_LOG = WORK + r"\opened_official.jsonl"


def now_local():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def short(path):
    p = os.path.normpath(path)
    for long_, s in ((V, "V"), (SHAP, "SHAP")):
        if p.lower().startswith(long_.lower()):
            return s + p[len(long_):]
    return p


def compare_dir(p):
    return os.path.join(SHAP, "out", p, "lead_0", "compare")


def log_official_open(path, who):
    """Append (local time, short path, script) to the open log BEFORE the file is opened."""
    assert os.path.normpath(OPEN_LOG).lower().startswith(os.path.normpath(RC).lower())
    os.makedirs(WORK, exist_ok=True)
    with open(OPEN_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps({"time": now_local(), "file": short(path), "by": who}) + "\n")


def read_official_json(path, who):
    log_official_open(path, who)
    with open(path, "r", encoding="utf-8") as f:
        txt = f.read()
    return json.loads(txt)


def read_official_text(path, who):
    log_official_open(path, who)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def read_official_parquet(path, who):
    import pyarrow.parquet as pq
    log_official_open(path, who)
    return pq.read_table(path).to_pandas()


def read_official_npy(path, who):
    import numpy as np
    log_official_open(path, who)
    with open(path, "rb") as f:
        raw = f.read()
    sha = hashlib.sha256(raw).hexdigest()
    arr = np.load(path, allow_pickle=False)
    return arr, sha


def write_json(path, obj):
    assert os.path.normpath(path).lower().startswith(os.path.normpath(RC).lower()), path
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, allow_nan=False, ensure_ascii=False)


def write_text(path, txt):
    assert os.path.normpath(path).lower().startswith(os.path.normpath(RC).lower()), path
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(txt)


# ---------------------------------------------------------------------------------------------------------------
# Flattening of results.json (A and B) to keys "problems/<p>/..." and "b1/<p>/..."

SKIP_TOP = {"choices", "software", "written_at", "implementer", "notes", "schema_version"}
# descriptive text, not numbers (listed in mapping.md as not matched)
SKIP_KEYS = {"extra", "path", "region_source", "sha256_covers", "npz", "test_set_records", "log_file",
             "models_covered_why", "numbers_why"}
TOPK = {"top10", "top3", "treeroute_top3", "consensus_top3"}
SETS = {"J", "structural_zeros", "top20_union", "sign_union_top10", "sign_determined_both", "global_indices",
        "test_set_columns", "rivals", "models_covered", "declined", "context_columns_summed",
        "rows_only_in_main", "rows_only_in_b1", "players_only_in_main", "players_only_in_b1",
        "variables_only_in_main", "variables_only_in_b1", "duplicates_merged_main", "duplicates_merged_b1"}
INTERVAL_KEYS = {"I", "share", "signed_mean", "spearman_J", "spearman_top20_union", "kendall_tau_b", "jaccard_top5",
                 "jaccard_top10", "jaccard_top20", "rbo_p090", "rbo_p095", "tv_shares", "tv_family_shares",
                 "sign_agreement", "sign_n_determined", "sign_n_agree", "n_J", "n_nonzero",
                 "n_nonzero_before_merge", "kendall_w", "mean_pairwise_spearman", "spearman_top20_union_median",
                 "spearman_top20_union_min", "spearman_top20_union_max", "rbo_p090_vs_consensus",
                 "own_history_share_treeroute", "own_history_share_median_rival", "own_history_share"}
FAMILY_KEYS = ("own_history", "global_indices", "local_drivers", "context_and_calendar", "seasonal_normal")
IV_PARTS = ("value", "ci_low", "ci_high", "n_finite")


def is_interval_slot(path):
    k = path[-1]
    par = path[-2] if len(path) > 1 else ""
    if k in INTERVAL_KEYS and not (k == "global_indices"):
        return True
    if par in ("stability", "family_shares"):
        return True
    if par == "families" and path[0] == "b1":
        return True
    return False


def flatten(o, path, out):
    if isinstance(o, dict):
        if set(IV_PARTS) <= set(o.keys()):
            for part in IV_PARTS:
                out["/".join(path + (part,))] = ("leaf", o[part])
            return
        for k, v in o.items():
            if k in SKIP_KEYS or k.endswith("_why"):
                continue
            flatten(v, path + (k,), out)
    elif isinstance(o, list):
        k = path[-1]
        if k in TOPK:
            # a top-k list [[name, share], ...] is matched as two keys: its names (exact, in rank order) and its
            # shares (within the tolerance, position by position)
            out["/".join(path + ("names",))] = ("list", [x[0] for x in o])
            out["/".join(path + ("shares",))] = ("nums", [x[1] for x in o])
        elif k in SETS:
            out["/".join(path)] = ("set", sorted(o))
        else:
            out["/".join(path)] = ("list", list(o))
    else:
        if o is None and is_interval_slot(path):
            for part in IV_PARTS:
                out["/".join(path + (part,))] = ("leaf", None)
            return
        out["/".join(path)] = ("leaf", o)


def load_results(X):
    p = os.path.join(V, X, "results.json")
    with open(p, encoding="utf-8") as f:
        R = json.load(f)
    out = {}
    for k, v in R.items():
        if k in SKIP_TOP:
            continue
        flatten(v, (k,), out)
    return R, out


def _isnum(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def num_eq(a, b, exact=False):
    if a is None or b is None:
        return a is None and b is None
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b
    if _isnum(a) and _isnum(b):
        if isinstance(a, float) and math.isnan(a):
            return isinstance(b, float) and math.isnan(b)
        if exact:
            return a == b
        d = abs(a - b)
        return d <= TOL or d <= TOL * max(abs(a), abs(b))
    return a == b


def entry_eq(key, x, y):
    """x, y: flattened entries ('leaf', v) / ('set', list) / ('list', list) / ('topk', names, shares)."""
    if x[0] != y[0]:
        return False
    if x[0] == "leaf":
        return num_eq(x[1], y[1], exact=key.endswith("/n_finite"))
    if x[0] in ("set", "list"):
        return x[1] == y[1]
    if x[0] == "nums":
        return len(x[1]) == len(y[1]) and all(num_eq(a, b) for a, b in zip(x[1], y[1]))
    return False


def entry_diff(x, y):
    """A short numeric description of the difference (for the mismatch list)."""
    if x is None or y is None:
        return None
    if x[0] == "leaf" and y[0] == "leaf" and _isnum(x[1]) and _isnum(y[1]):
        return abs(float(x[1]) - float(y[1]))
    if x[0] == "nums" and y[0] == "nums" and len(x[1]) == len(y[1]):
        d = [abs(a - b) for a, b in zip(x[1], y[1]) if _isnum(a) and _isnum(b)]
        return max(d or [0.0])
    return None


def is_null(entry):
    return entry is not None and entry[0] == "leaf" and entry[1] is None


def count_numbers(entry):
    if entry is None:
        return 0
    if entry[0] == "leaf":
        return int(_isnum(entry[1]))
    if entry[0] == "nums":
        return sum(1 for x in entry[1] if _isnum(x))
    return 0


def show(entry, n=200):
    if entry is None:
        return None
    if entry[0] == "leaf":
        v = entry[1]
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return repr(v)
        return v
    if entry[0] in ("set", "list", "nums"):
        s = entry[1]
        return s if len(json.dumps(s)) <= n else (s[:8] + ["... (%d items)" % len(s)])
    return str(entry)


def pattern(key):
    """Collapse names (models, players, pairs, rivals, ...) into placeholders for grouping."""
    parts = key.split("/")
    out = []
    holders = {"players", "pairs", "models", "stability", "variable_family", "family_shares", "consensus_shares",
               "main_shares", "spearman_top20_union_per_rival", "own_history_share_per_rival", "links", "families",
               "checks_passed", "duplicates_merged", "problems", "b1"}
    for i, p in enumerate(parts):
        if i > 0 and parts[i - 1] in holders and not (parts[i - 1] == "families" and p in (
                "variable_family", "global_indices", "test_set_columns")):
            out.append("<%s>" % parts[i - 1])
        elif i > 0 and parts[i - 1] in ("top10", "top3", "treeroute_top3", "consensus_top3"):
            out.append("<i>")
        else:
            out.append(p)
    return "/".join(out)
