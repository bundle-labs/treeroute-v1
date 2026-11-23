"""AW5 sample and per-row backgrounds (PROTOCOL.md sections 3 and 5). Reads only; writes sample/<problem>/.

  py -3.9 -I -B make_sample.py --problem coral [--leads 0 183] [--n 1000] [--defo-regions 42] [--tag v1]
        [--out-root DIR (smoke only)]

Writes sample.parquet (the N explained keys), background_lead_<L>.parquet (each explained row's background keys at
lead L: B2 = same unit, same season key, refit rows at or before L's fit cut that are also treeroute router fit
rows: the keys the run's context_missing/<pass>.parquet lists as left-out router fit rows of that lead's test pass
are removed for every model; coral: the saved router pool), and sample_manifest.json; then appends the files' SHA-256
to the register. A problem's sample is registered ONCE per folder: a second run with identical content does nothing,
one with different content is refused (a new sample needs a new --tag, which names a new folder
sample/<problem>__<tag>/; the default tag v1 is sample/<problem>/).
"""
import argparse
import glob
import math
import os
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shapv1_common as C  # noqa: E402

C.pin_threads(1)
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

SENTINEL = 2 ** 31 - 1
COMMON = ("ridge", "rf", "lgbm", "lgbm_tweedie", "hgb_l1")


def parse():
    ap = argparse.ArgumentParser()
    ap.add_argument("--problem", required=True, choices=sorted(C.PROBLEMS))
    ap.add_argument("--leads", type=int, nargs="+", default=None,
                    help="default: every reported lead, so that one sample serves every scope (lead-invariant)")
    ap.add_argument("--n", type=int, default=C.DEFAULT_N)
    ap.add_argument("--defo-regions", type=int, default=0, help="0 = every region (default)")
    ap.add_argument("--tag", default="v1")
    ap.add_argument("--out-root", default=None, help="smoke tests only: a folder under smoke/")
    return ap.parse_args()


def test_preds(run, lead):
    path = os.path.join(run, "test_preds.parquet") if lead == 0 else os.path.join(run, "ladder", "lead_%d" % lead,
                                                                                  "test_preds.parquet")
    return pq.read_table(path, columns=["unit", "group", "time", "year", "y"]).to_pandas()


def rival_models(problem, lead):
    """(name, preds file, prediction column) of every SHAP-able rival with saved predictions at the lead."""
    P = C.PROBLEMS[problem]
    out = []
    picks = C.read_json(os.path.join(P["board"], "picks.json"))["picks"]
    for learner in COMMON:
        if learner in picks:
            f = os.path.join(P["board"], "lead_%d" % lead, "preds_%s.parquet" % learner)
            if os.path.isfile(f):
                out.append((learner, f, "pre__rival_" + learner))
    if P["human"]:
        f = os.path.join(P["human"], "lead_%d" % lead, "preds_bardl_h1.parquet")
        if os.path.isfile(f):
            out.append(("bardl_h1", f, "pre"))
    return out


def frame(problem, leads, log):
    P = C.PROBLEMS[problem]
    keys = None
    models = {}
    for L in leads:
        tp = test_preds(P["run"], L)
        tp = tp[np.isfinite(tp["y"].to_numpy(np.float64))]
        k = tp[["unit", "group", "time", "year"]].copy()
        n0 = len(k)
        for name, f, col in rival_models(problem, L):
            r = pq.read_table(f, columns=["unit", "time", col]).to_pandas()
            r = r[np.isfinite(r[col].to_numpy(np.float64))][["unit", "time"]]
            k = k.merge(r, on=["unit", "time"], how="inner")
            models.setdefault(L, []).append(name)
        log("frame lead %d: %d labelled treeroute test rows, %d after the rivals %s" % (L, n0, len(k), models.get(L)))
        keys = k if keys is None else keys.merge(k[["unit", "time"]], on=["unit", "time"], how="inner")
    keys = keys.sort_values(["group", "unit", "time"]).reset_index(drop=True)
    return keys, models


def select_grid(F, n, problem, n_regions, excluded):
    salt = "shap_v1|AW5|%s" % problem
    F = F[~F.set_index(["unit", "time"]).index.isin(excluded)]
    years = sorted(F["year"].unique().tolist())
    groups = sorted(F["group"].unique().tolist())
    if n_regions and n_regions < len(groups):
        groups = sorted(C.hash_order(salt + "|region", groups)[:n_regions])
    G, Y = len(groups), len(years)
    n_loc = int(math.ceil(n / float(G * Y)))
    rows = []
    for g in groups:
        Fg = F[F["group"] == g]
        full = Fg.groupby("unit")["year"].nunique()
        units = sorted(full.index[full == Y].tolist())
        for u in C.hash_order(salt + "|unit", units)[:n_loc]:
            Fu = Fg[Fg["unit"] == u]
            for yv in years:
                cand = Fu[Fu["year"] == yv]
                keyset = ["%s|%d" % (u, t) for t in cand["time"].tolist()]
                pick = C.hash_order(salt + "|row", keyset)[0]
                rows.append(cand[cand["time"] == int(pick.rsplit("|", 1)[1])].iloc[0])
    S = pd.DataFrame(rows).reset_index(drop=True)
    if len(S) > n:
        order = C.hash_order(salt + "|trim", ["%s|%d" % (u, t) for u, t in zip(S["unit"], S["time"])])
        drop = set(order[n:])
        S = S[[("%s|%d" % (u, t)) not in drop for u, t in zip(S["unit"], S["time"])]]
    return S.sort_values(["group", "unit", "time"]).reset_index(drop=True), {"regions": G, "years": Y,
                                                                              "units_per_region": n_loc}


def select_table(F, n, problem, excluded):
    salt = "shap_v1|AW5|%s" % problem
    F = F[~F.set_index(["unit", "time"]).index.isin(excluded)]
    groups = sorted(F["group"].unique().tolist())
    queues = {}
    for g in groups:
        Fg = F[F["group"] == g]
        per_year = {yv: C.hash_order(salt + "|row", Fg[Fg["year"] == yv]["unit"].tolist())
                    for yv in sorted(Fg["year"].unique().tolist())}
        q = []
        while any(per_year.values()):
            for yv in sorted(per_year):
                if per_year[yv]:
                    q.append(per_year[yv].pop(0))
        queues[g] = q
    quota = {g: 0 for g in groups}
    left = n
    while left > 0:
        active = [g for g in groups if quota[g] < len(queues[g])]
        if not active:
            break
        q = left // len(active)
        if q == 0:
            for g in C.hash_order(salt + "|region", active)[:left]:
                quota[g] += 1
            break
        for g in active:
            take = min(q, len(queues[g]) - quota[g])
            quota[g] += take
            left -= take
    chosen = set(u for g in groups for u in queues[g][:quota[g]])
    S = F[F["unit"].isin(chosen)]
    return S.sort_values(["group", "unit", "time"]).reset_index(drop=True), {"regions": len(groups),
                                                                              "quota": quota}


def export_dir(problem, lead):
    return os.path.join(C.PROBLEMS[problem]["export"], "lead_%d" % lead)


def context_missing_keys(problem, lead):
    """(unit, time) of the router fit rows the run's test pass at this lead left out for missing context (ruling S,
    G1): context_missing/test_pass.parquet at lead 0, lead_<L>_test_pass.parquet at a forecast lead; rows with
    cut_kind 'fit'. An empty set when the run has no such file."""
    P = C.PROBLEMS[problem]
    f = os.path.join(P["run"], "context_missing", "test_pass.parquet" if lead == 0 else
                     "lead_%d_test_pass.parquet" % lead)
    if not os.path.isfile(f):
        return set(), None
    t = pq.read_table(f, columns=["unit", "time", "cut_kind", "lead"]).to_pandas()
    t = t[(t["cut_kind"].astype(str) == "fit") & (t["lead"].astype(int) == int(lead))]
    return set(zip(t["unit"].astype(str), t["time"].astype(np.int64))), os.path.basename(f)


def backgrounds(problem, lead, S, log):
    """B2 keys of every explained row (PROTOCOL.md 5): (row, unit, time) of each background row; the second value
    counts the keys removed because the treeroute router did not fit on them (missing context)."""
    P = C.PROBLEMS[problem]
    em = C.read_json(os.path.join(export_dir(problem, lead), "export_manifest.json"))
    season = em["season"]
    out = []
    if season["kind"] == "event_month":                                  # coral: the visit's saved router pool
        f = os.path.join(P["run"], "pools_test_pass.parquet") if lead == 0 else os.path.join(
            P["run"], "ladder", "lead_%d" % lead, "pools_test_pass.parquet")
        pools = pq.read_table(f).to_pandas().set_index("row_id")
        import json
        for i, u in enumerate(S["unit"].tolist()):
            ids = json.loads(pools.loc[u, "pool_row_ids"]) if isinstance(pools.loc[u, "pool_row_ids"], str) \
                else list(pools.loc[u, "pool_row_ids"])
            for b in ids:
                out.append((i, b, -1))
        B = pd.DataFrame(out, columns=["row", "unit", "time"])
        tr = [pq.read_table(fp, columns=["unit", "time", "r_refit"]).to_pandas()
              for _, fp in sorted(C.export_files(problem, lead, "train").items())]
        tr = pd.concat(tr, ignore_index=True)
        tr = tr[tr["r_refit"].astype(bool)].drop_duplicates("unit")
        B = B.drop(columns="time").merge(tr[["unit", "time"]], on="unit", how="left")
        miss = int(B["time"].isna().sum())
        if miss:
            raise SystemExit("REFUSED: %d pool rows are not refit rows of the lead-%d export" % (miss, lead))
        B["time"] = B["time"].astype(np.int64)
        return B.sort_values(["row", "unit"]).reset_index(drop=True), 0, set()
    spy = int(season["steps_per_year"])
    trf = C.export_files(problem, lead, "train")
    miss, _ = context_missing_keys(problem, lead)
    removed = 0
    for g in sorted(S["group"].unique().tolist()):
        tr = pq.read_table(trf[g], columns=["unit", "time", "r_refit"]).to_pandas()
        tr = tr[tr["r_refit"].astype(bool)]
        Sg = S[S["group"] == g]
        for i, u, t in zip(Sg.index.tolist(), Sg["unit"].tolist(), Sg["time"].tolist()):
            tu = tr[tr["unit"] == u]["time"].to_numpy(np.int64)
            if season["kind"] == "month_of_year":
                tu = tu[(tu % spy) == (int(t) % spy)]
            for b in sorted(tu.tolist()):
                if (str(u), int(b)) in miss:
                    removed += 1
                    continue
                out.append((i, u, b))
    B = pd.DataFrame(out, columns=["row", "unit", "time"])
    empty = sorted(set(range(len(S))) - set(B["row"].tolist()))
    no_bg = set((S.loc[r, "unit"], int(S.loc[r, "time"])) for r in empty)
    if empty:
        log("lead %d: %d explained rows have no background row (excluded and reselected)" % (lead, len(empty)))
    return B, removed, no_bg


def sentinel_rows(problem, lead, S, B, log):
    """Explained rows whose own or background features hold |x| >= 2^31 - 1 (PROTOCOL.md 3, exclusions)."""
    bad = set()
    tef, trf = C.export_files(problem, lead, "test"), C.export_files(problem, lead, "train")
    for g in sorted(S["group"].unique().tolist()):
        Sg = S[S["group"] == g]
        tf = tef[g]
        cols = [c for c in pq.read_schema(tf).names if c.startswith(("x__", "c__", "nfit__"))]
        te = pq.read_table(tf, columns=["unit", "time"] + cols).to_pandas()
        te = te.merge(Sg[["unit", "time"]], on=["unit", "time"], how="inner")
        hit = np.abs(np.nan_to_num(te[cols].to_numpy(np.float64))) >= SENTINEL
        for u, t in zip(te["unit"][hit.any(1)], te["time"][hit.any(1)]):
            bad.add((u, int(t)))
    bunits = sorted(set(B["unit"].astype(str)))
    groups = sorted(trf) if C.PROBLEMS[problem]["kind"] == "neighbour" else sorted(set(S["group"].astype(str)))
    for g in groups:                       # gridded: a background row is the explained unit's own row (its group)
        tf = trf[g]
        cols = [c for c in pq.read_schema(tf).names if c.startswith(("x__", "c__", "nfit__"))]
        tr = pq.read_table(tf, columns=["unit", "time"] + cols, filters=[("unit", "in", bunits)]).to_pandas()
        tr = tr.merge(B[["unit", "time"]].drop_duplicates(), on=["unit", "time"], how="inner")
        hit = np.abs(np.nan_to_num(tr[cols].to_numpy(np.float64))) >= SENTINEL
        if hit.any():
            badbg = set(zip(tr["unit"][hit.any(1)], tr["time"][hit.any(1)].astype(int)))
            rows = B[[(u, int(t)) in badbg for u, t in zip(B["unit"], B["time"])]]["row"].unique()
            for r in rows:
                bad.add((S.loc[r, "unit"], int(S.loc[r, "time"])))
    return bad


def sample_root(problem, tag, out_root):
    if out_root:
        return out_root
    return C.sample_dir(problem) if tag == "v1" else C.sample_dir(problem) + "__" + tag


def main():
    a = parse()
    P = C.PROBLEMS[a.problem]
    if not re.match(r"^[A-Za-z0-9_.-]+$", a.tag):
        raise SystemExit("REFUSED: --tag must be letters, digits, '_', '.' or '-'")
    root = sample_root(a.problem, a.tag, a.out_root)
    C.makedirs(root)
    reg = C.SAMPLE_REGISTER if a.out_root is None else os.path.join(root, "SAMPLE_REGISTER.txt")
    log = C.Log("make_sample_%s" % a.problem)
    leads = sorted(set(a.leads if a.leads else P["leads"]))
    for L in leads:
        if L not in P["leads"]:
            raise SystemExit("lead %d is not a reported lead of %s" % (L, a.problem))
    held = os.path.join(root, "sample.parquet")
    held_reg = C.registered(a.problem, held, reg)
    log("problem %s, leads %s, N %d, defo regions %s, tag %s; folder %s%s" % (
        a.problem, leads, a.n, a.defo_regions or "all", a.tag, root,
        " (holds a registered sample)" if held_reg else ""))
    F, models = frame(a.problem, leads, log)
    excluded, no_bg_all = set(), set()
    for attempt in range(10):
        if P["kind"] == "neighbour":
            S, info = select_table(F, a.n, a.problem, excluded)
        else:
            S, info = select_grid(F, a.n, a.problem, a.defo_regions, excluded)
        Bs, removed, bad = {}, {}, set()
        for L in leads:
            Bs[L], removed[L], nob = backgrounds(a.problem, L, S, log)
            bad |= nob
            no_bg_all |= nob
        for L in leads:
            bad |= sentinel_rows(a.problem, L, S, Bs[L], log)
        log("selection %d: %d rows, %d with a sentinel value or no background row (excluded and reselected)"
            % (attempt, len(S), len(bad)))
        if not bad:
            break
        excluded |= bad
    else:
        raise SystemExit("REFUSED: exclusions did not settle in 10 rounds")
    S.insert(0, "row", np.arange(len(S), dtype=np.int64))
    # write to temporary names first: a registered sample is never overwritten (only compared)
    tmp = {"sample.parquet": C.write_parquet(os.path.join(root, "sample.parquet.new"), S)}
    for L in leads:
        tmp["background_lead_%d.parquet" % L] = C.write_parquet(
            os.path.join(root, "background_lead_%d.parquet.new" % L), Bs[L])
    sha = {k: C.sha256_file(v) for k, v in tmp.items()}
    if held_reg:
        same = all(os.path.isfile(os.path.join(root, k)) and C.sha256_file(os.path.join(root, k)) == v
                   for k, v in sha.items())
        for v in tmp.values():
            os.remove(v)
        if same:
            log("the folder already holds this registered sample (identical files): nothing written, nothing "
                "registered again")
            return
        raise SystemExit("REFUSED: %s already holds a registered sample with other content (S-SAMPLE: a problem's "
                         "sample is registered once per folder; a new sample needs a new --tag)" % root)
    for k, v in tmp.items():
        os.replace(v, C.assert_writable(os.path.join(root, k)))
    man = {"problem": a.problem, "leads": leads, "n": int(len(S)), "n_asked": a.n, "tag": a.tag,
           "defo_regions": int(a.defo_regions or 0),
           "frame_rows": int(len(F)), "models_in_frame": {str(k): v for k, v in models.items()},
           "selection": info, "excluded_sentinel_or_no_background": sorted("%s|%d" % k for k in excluded),
           "excluded_no_background": sorted("%s|%d" % k for k in no_bg_all),
           "background_keys_removed_missing_context": {str(L): int(removed[L]) for L in leads},
           "regions_in_sample": int(S["group"].nunique()), "units_in_sample": int(S["unit"].nunique()),
           "rows_per_year": {str(k): int(v) for k, v in S["year"].value_counts().sort_index().items()},
           "background_rows": {str(L): {"min": int(Bs[L].groupby("row").size().min()),
                                        "median": float(Bs[L].groupby("row").size().median()),
                                        "max": int(Bs[L].groupby("row").size().max())} for L in leads},
           "sha256": sha, "rule": "PROTOCOL.md section 3 (v3)"}
    C.write_json(os.path.join(root, "sample_manifest.json"), man)
    line = "%s problem=%s tag=%s leads=%s n=%d defo_regions=%d sample=%s %s\n" % (
        C.datetime.datetime.now().isoformat(timespec="seconds"), a.problem, a.tag, ",".join(map(str, leads)), len(S),
        int(a.defo_regions or 0), sha["sample.parquet"],
        " ".join("%s=%s" % (k, v) for k, v in sorted(sha.items()) if k != "sample.parquet"))
    C.assert_writable(reg)
    with open(reg, "a", encoding="utf-8") as fh:
        fh.write(line)
    log("sample written: %d rows in %d regions, %d units; background keys removed for missing router context %s; "
        "register line appended to %s" % (len(S), S["group"].nunique(), S["unit"].nunique(),
                                          {str(L): removed[L] for L in leads}, reg))


if __name__ == "__main__":
    main()
