"""Round 14 reconciler: implementer A vs implementer B vs the official outputs of compare_shap.py (brief items 1-8),
and A vs B for treeroute's B1 sensitivity (brief item 9, which has no official output).

    py -3.9 -I -B D:\\treeroute\\analysis\\shap_v1\\verify_v1\\reconcile\\reconcile.py

Read-only on every file outside V\\reconcile. Reads: V\\A\\results.json, V\\B\\results.json, V\\A\\draws\\*.npz,
V\\B\\draws\\*.npz; the official outputs SHAP\\out\\<p>\\lead_0\\compare\\{per_lead.json, bootstrap_draws.npy,
importance.parquet, families.parquet, pairs.parquet, bootstrap_stats.parquet, AW4_main_row.json, AW3_table.md,
AW4_table.md, pairs.parquet.done.json} (each open is logged with its local time in work\\opened_official.jsonl);
row files (columns row, group of each problem's first model, as compare_shap.py reads them; defo's treeroute and
treeroute_B1 for the identity check); the B1 pieces' meta.json, rows.parquet.done.json (and FAILED.json if present);
the main treeroute meta.json (duplicates_merged); SHAP\\SAMPLE_REGISTER.txt; SHAP\\logs\\tr_shap_<p>_lead0.log (numbers
only; no log line is copied). Writes: V\\reconcile\\mismatches.json (every mismatching key, grouped by cause, with
each group's diagnosis) and V\\reconcile\\work\\{summary.json, no_number_keys.json.gz, opened_official.jsonl,
opened_other.jsonl}.
The mapping of official files and columns to the results.json keys is documented in V\\reconcile\\mapping.md.
"""
import collections
import datetime
import gzip
import hashlib
import json
import math
import os
import re
import sys
import time

sys.path.insert(0, r"D:\treeroute\analysis\shap_v1\verify_v1\reconcile")
import rlib as R  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

WHO = "reconcile.py"
OTHER_LOG = R.WORK + r"\opened_other.jsonl"
FAM = {"own history": "own_history", "global indices": "global_indices", "local drivers": "local_drivers",
       "context and calendar": "context_and_calendar", "seasonal normal": "seasonal_normal"}
STAT = {"spearman": "spearman_J", "spearman_top20_union": "spearman_top20_union", "kendall_tau_b": "kendall_tau_b",
        "jaccard_top5": "jaccard_top5", "jaccard_top10": "jaccard_top10", "jaccard_top20": "jaccard_top20",
        "rbo_p0.9": "rbo_p090", "rbo_p0.95": "rbo_p095", "tvd": "tv_shares", "tvd_family": "tv_family_shares",
        "sign_agreement_top10": "sign_agreement"}
BS_STAT = {"spearman": "spearman_J", "spearman_top20_union": "spearman_top20_union", "rbo_p0.9": "rbo_p090",
           "tvd": "tv_shares"}
IV = R.IV_PARTS
B1_START = "2026-11-15 23:06"


def log_other(path):
    os.makedirs(R.WORK, exist_ok=True)
    with open(OTHER_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps({"time": R.now_local(), "file": R.short(path), "by": WHO}) + "\n")


def read_register():
    reg = {}
    rp = os.path.join(R.SHAP, "SAMPLE_REGISTER.txt")
    log_other(rp)
    with open(rp, "r", encoding="utf-8") as f:
        for ln in f:
            mp = re.search(r"problem=(\S+)", ln)
            ms = re.search(r"\bsample=([0-9a-f]{64})", ln)
            ml = re.search(r"leads=(\S+)", ln)
            if mp and ms and ml and "0" in ml.group(1).split(","):
                reg[mp.group(1)] = ms.group(1)
    return reg


REGISTER = read_register()


def nn(v):
    if v is None:
        return None
    if isinstance(v, np.bool_):
        return bool(v)
    if isinstance(v, np.integer):
        return int(v)
    if isinstance(v, np.floating):
        v = float(v)
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    return v


def LF(v):
    return ("leaf", nn(v))


# ------------------------------------------------------------------------------------------------------------
# The official outputs, flattened to the results.json keys.
#   O  : numbers and lists the official files hold (NaN -> null; "no interval in the file" -> ci keys absent;
#        a key that compare_shap.py writes nowhere by its own rule -> null, see mapping.md)
#   Od : keys the official files do not hold, derived by the reconciler from official numbers with compare_shap.py's
#        own rule (a second check only; a key that is only in Od counts as missing in the official outputs)

def ranked_names(df):
    """compare_shap's ST.ranked over J: mean |phi| descending, ties by the alphabetical player order."""
    return [r.player for r in sorted(df.itertuples(), key=lambda r: (-r.mean_abs, r.player))]


def official(p, summary):
    d = R.compare_dir(p)
    per = R.read_official_json(os.path.join(d, "per_lead.json"), WHO)
    D, sha = R.read_official_npy(os.path.join(d, "bootstrap_draws.npy"), WHO)
    imp = R.read_official_parquet(os.path.join(d, "importance.parquet"), WHO)
    fam = R.read_official_parquet(os.path.join(d, "families.parquet"), WHO)
    pr = R.read_official_parquet(os.path.join(d, "pairs.parquet"), WHO)
    bs = R.read_official_parquet(os.path.join(d, "bootstrap_stats.parquet"), WHO)
    mr = R.read_official_json(os.path.join(d, "AW4_main_row.json"), WHO)
    aw3 = R.read_official_text(os.path.join(d, "AW3_table.md"), WHO)
    aw4 = R.read_official_text(os.path.join(d, "AW4_table.md"), WHO)
    done = R.read_official_json(os.path.join(d, "pairs.parquet.done.json"), WHO)
    O, Od = {}, {}
    base = "problems/%s/" % p
    chk = []                                                     # internal consistency of the official files
    pp = os.path.join(d, "pairs.parquet")
    R.log_official_open(pp, WHO + " (bytes, for its SHA-256)")
    with open(pp, "rb") as fh:
        rawp = fh.read()
    chk.append(("pairs.parquet SHA-256 and size == pairs.parquet.done.json",
                hashlib.sha256(rawp).hexdigest() == done.get("sha256") and len(rawp) == done.get("bytes")))
    chk.append(("per_lead salt == shap_v1|AW4|<p>|0", per.get("salt") == "shap_v1|AW4|%s|0" % p))
    chk.append(("per_lead sample_sha256 == the registered sample", per.get("sample_sha256") == REGISTER.get(p)))
    # the family map against per_lead.json's own global columns (variable maps from the pieces' meta.json)
    members = {}
    for m in per["models"]:
        mp_ = os.path.join(R.SHAP, "out", p, "lead_0", m, "meta.json")
        log_other(mp_)
        with open(mp_, "r", encoding="utf-8") as fh:
            vm = json.load(fh).get("variable_map") or {}
        for pl_, v_ in vm.items():
            members.setdefault(v_, set()).add(pl_)
    gcols = set(per["global_columns"])
    bad_g = []
    for v_, fam_ in per["families"].items():
        xs = sorted(x for x in members.get(v_, ()) if x.startswith("x__"))
        if not xs or v_.startswith("hist_") or v_ in ("normal", "calendar") or v_.startswith("ctx:"):
            continue
        all_g = all(x in gcols for x in xs)
        if (fam_ == "global indices") != all_g:
            bad_g.append(v_)
    chk.append(("family map: a variable is a global index iff all its x__ columns are in global_columns (%d off)"
                % len(bad_g), not bad_g))

    def put(dct, key, entry):
        dct[base + key] = entry

    def iv(dct, key, value, lo=None, hi=None, nf=None, has_ci=True):
        put(dct, key + "/value", LF(value))
        if has_ci:
            put(dct, key + "/ci_low", LF(lo))
            put(dct, key + "/ci_high", LF(hi))
            put(dct, key + "/n_finite", LF(None if nf is None else int(nf)))

    models, main_set = per["models"], per["main_set"]
    put(O, "lead", LF(per["lead"]))
    put(O, "models", ("list", list(models)))
    put(O, "main_set", ("list", list(main_set)))
    put(O, "declined_by_guard", ("list", list(per["declined_by_guard"])))
    for m, s in per["links"].items():
        put(O, "links/" + m, LF(s))
    put(O, "rows", LF(per["rows"]))
    put(O, "draws/shape", ("list", [int(x) for x in D.shape]))
    put(O, "draws/dtype", LF(str(D.dtype)))
    put(O, "draws/sha256_per_lead", LF(per["draws_sha256"]))
    put(O, "draws/sha256_computed", LF(sha))
    put(O, "draws/sha256_match", LF(sha == per["draws_sha256"]))
    # the region order compare_shap.py uses (lines 146-148): sorted(set(group)) of its first model's rows
    f0 = os.path.join(R.SHAP, "out", p, "lead_0", models[0], "rows.parquet")
    log_other(f0)
    g0 = pq.read_table(f0, columns=["row", "group"]).to_pandas().sort_values("row")
    ureg = sorted(set(g0["group"].astype(str)))
    put(Od, "draws/regions_in_draw_order", ("list", ureg))
    chk.append(("per_lead.regions == number of regions", per["regions"] == len(ureg)))
    chk.append(("per_lead.draws == draw matrix rows", per["draws"] == D.shape[0]))
    chk.append(("draw matrix columns == number of regions", D.shape[1] == len(ureg)))
    chk.append(("draw values in 0..G-1", int(D.min()) >= 0 and int(D.max()) < len(ureg)))

    Jsets, rank, share_of, I_of, S_of, det_of = {}, {}, {}, {}, {}, {}
    for L in ("feature", "variable"):
        lv = per[L]
        sub = imp[imp.level == L]
        allp = sorted(sub.player.unique())
        J = sorted(sub[sub.active].player.unique())
        Jsets[L] = J
        put(O, "levels/%s/active_set/J" % L, ("set", J))
        iv(O, "levels/%s/active_set/n_J" % L, lv["active"], has_ci=False)
        put(O, "levels/%s/active_set/n_J/ci_low" % L, ("leaf", None))     # J is fixed: compare_shap.py l.177-183
        put(O, "levels/%s/active_set/n_J/ci_high" % L, ("leaf", None))
        put(O, "levels/%s/active_set/n_J/n_finite" % L, ("leaf", None))
        put(O, "levels/%s/active_set/structural_zeros" % L, ("set", sorted(lv["structural_zero"])))
        chk.append(("%s: per_lead active == |J| of importance.parquet" % L, lv["active"] == len(J)))
        chk.append(("%s: per_lead structural_zero == inactive players" % L,
                    sorted(lv["structural_zero"]) == sorted(set(allp) - set(J))))
        chk.append(("%s: per_lead players == players of importance.parquet" % L, lv["players"] == len(allp)))
        for m in models:
            sm = sub[sub.model == m]
            chk.append(("%s %s: one row per player" % (L, m), len(sm) == len(allp) and sm.player.is_unique))
            act = sm[sm.active]
            tot = float(act.mean_abs.sum())
            chk.append(("%s %s: share == mean_abs / sum over J" % (L, m),
                        bool(np.allclose(act.share.to_numpy(), act.mean_abs.to_numpy() / tot, rtol=1e-12, atol=0))))
            for r in sm.itertuples():
                pre = "levels/%s/models/%s/players/%s/" % (L, m, r.player)
                put(O, pre + "I/value", LF(r.mean_abs))
                put(O, pre + "share/value", LF(r.share))
                put(O, pre + "signed_mean/value", LF(r.signed_mean))
                put(O, pre + "sign_determined", LF(bool(r.sign_determined)))
            put(O, "levels/%s/models/%s/n_nonzero/value" % (L, m), LF(lv["nonzero_players"][m]))
            top = act.sort_values(["share", "player"], ascending=[False, True]).head(10)   # compare_shap.py l.437
            put(O, "levels/%s/models/%s/top10/names" % (L, m), ("list", list(top.player)))
            put(O, "levels/%s/models/%s/top10/shares" % (L, m), ("nums", [float(x) for x in top.share]))
            rk = ranked_names(act)
            rank[(L, m)] = rk
            put(Od, "levels/%s/models/%s/ranking" % (L, m), ("list", rk))
            share_of[(L, m)] = dict(zip(act.player, act.share.astype(float)))
            I_of[(L, m)] = dict(zip(sm.player, sm.mean_abs.astype(float)))
            S_of[(L, m)] = dict(zip(sm.player, sm.signed_mean.astype(float)))
            det_of[(L, m)] = dict(zip(sm.player, sm.sign_determined.astype(bool)))
        # per problem (item 5)
        kw = lv["kendall_w_main_set"]
        iv(O, "levels/%s/per_problem/kendall_w" % L, kw["value"], kw["ci"][0], kw["ci"][1], kw["finite_replicates"])
        mp = lv["mean_pairwise_spearman_main_set"]
        iv(O, "levels/%s/per_problem/mean_pairwise_spearman" % L, mp["value"], mp["ci"][0], mp["ci"][1],
           mp["finite_replicates"])
        defined_w = len(main_set) > 1
        put(Od, "levels/%s/per_problem/kendall_w_m" % L, LF(len(main_set) if defined_w else None))
        put(Od, "levels/%s/per_problem/kendall_w_n" % L, LF(len(J) if defined_w else None))
        for m, v in lv["stability_under_region_resampling"].items():
            put(O, "levels/%s/per_problem/stability/%s/value" % (L, m), LF(v))
        # pairs (item 4)
        sp = pr[pr.level == L]
        for (a, b), g in sp.groupby(["model_a", "model_b"], sort=False):
            key = "levels/%s/pairs/%s|%s/" % (L, a, b)
            put(O, key + "models", ("list", [a, b]))
            lab = g.pair_label.iloc[0]
            put(O, key + "link_class", LF("same-link" if lab.startswith("same-link") else "cross-link"))
            if lab.startswith("cross-link"):
                m_ = re.search(r"\((not comparable in scale or rank)\)", lab)
                put(O, key + "cross_link_label", LF(m_.group(1) if m_ else None))
            dec = re.search(r"declined by its guard: (.*)$", lab)
            put(O, key + "declined", ("set", sorted(x.strip() for x in dec.group(1).split(",")) if dec else []))
            put(Od, key + "both_in_main_set", LF(a in main_set and b in main_set))
            have = set()
            for r in g.itertuples():
                s = STAT[r.statistic]
                have.add(s)
                iv(O, key + s, r.value, r.ci_low, r.ci_high, r.finite_replicates)
                if s == "sign_agreement":
                    put(O, key + "sign_n_determined/value", LF(int(r.signs_compared)))
                    nsg = int(r.signs_compared)
                    sgv = nn(r.value)
                    put(Od, key + "sign_n_agree/value",
                        LF(int(round(sgv * nsg)) if (nsg > 0 and sgv is not None) else 0))
            if "jaccard_top20" not in have:       # compare_shap.py l.186: top-20 only when |J| >= 200
                iv(O, key + "jaccard_top20", None, None, None, None)
            if "tv_family_shares" not in have:    # compare_shap.py l.281-295: the family TVD at the variable level only
                iv(O, key + "tv_family_shares", None, None, None, None)
            # derived sets of the pair, by compare_shap's rules (top-k by ST.ranked over J)
            ta, tb = rank[(L, a)], rank[(L, b)]
            u20 = sorted(set(ta[:20]) | set(tb[:20]))
            u10 = sorted(set(ta[:10]) | set(tb[:10]))
            put(Od, key + "top20_union", ("set", u20))
            put(Od, key + "sign_union_top10", ("set", u10))
            both = sorted(j for j in u10 if det_of[(L, a)][j] and det_of[(L, b)][j] and S_of[(L, a)][j] != 0
                          and S_of[(L, b)][j] != 0)
            put(Od, key + "sign_determined_both", ("set", both))
            chk.append(("%s %s|%s: signs_compared == |determined in both| (derived)" % (L, a, b),
                        int(g[g.statistic == "sign_agreement_top10"].signs_compared.iloc[0]) == len(both)))
    # families (item 3)
    for v, f in per["families"].items():
        put(O, "levels/variable/families/variable_family/" + v, LF(FAM[f]))
    put(Od, "levels/variable/families/global_indices",
        ("set", sorted(v for v, f in per["families"].items() if f == "global indices")))
    for r in fam.itertuples():
        put(O, "levels/variable/models/%s/family_shares/%s/value" % (r.model, FAM[r.family]), LF(r.share))
        put(O, "levels/variable/models/%s/family_mean_abs/%s" % (r.model, FAM[r.family]), LF(r.mean_abs))
    for m in models:
        fm = fam[fam.model == m]
        chk.append(("families %s: shares sum to 1" % m, abs(float(fm.share.sum()) - 1.0) < 1e-12))
    # main row (item 7)
    mk = "main_row/"
    put(O, mk + "level", LF(mr["level"]))
    put(O, mk + "main_set", ("list", list(mr["models_in_main_set"])))
    tr = "treeroute"
    rivals = [m for m in main_set if m != tr]                     # compare_shap.py l.348
    put(Od, mk + "rivals", ("set", sorted(rivals)))
    kw = mr["kendall_w"]
    iv(O, mk + "kendall_w", kw["value"], kw["ci"][0], kw["ci"][1], kw["ci"][2])
    chk.append(("main row W == per_lead variable W", nn(kw["value"]) == nn(per["variable"]["kendall_w_main_set"]["value"])))
    chk.append(("main row main set == per_lead main_set", mr["models_in_main_set"] == main_set))
    chk.append(("main row declined == per_lead declined_by_guard", mr["declined_models"] == per["declined_by_guard"]))
    Jv = Jsets["variable"]
    key_sp = "treeroute_vs_same_link_rivals_median_spearman_top20_union"
    if key_sp in mr:
        x = mr[key_sp]
        iv(O, mk + "spearman_top20_union_median", x["value"], x["ci"][0], x["ci"][1], x["ci"][2])
        put(O, mk + "spearman_top20_union_min/value", LF(x["range"][0]))
        put(O, mk + "spearman_top20_union_max/value", LF(x["range"][1]))
        pv = pr[(pr.level == "variable") & (pr.statistic == "spearman_top20_union")]
        for rv in rivals:
            a, b = sorted([tr, rv])
            v = pv[(pv.model_a == a) & (pv.model_b == b)].value.iloc[0]
            put(O, mk + "spearman_top20_union_per_rival/" + rv, LF(v))
        x = mr["rbo_vs_consensus_p0.9"]
        iv(O, mk + "rbo_p090_vs_consensus", x["value"], x["ci"][0], x["ci"][1], x["ci"][2])
        cons = {v: float(np.mean([share_of[("variable", rv)][v] for rv in rivals])) for v in Jv}
        for v, s in cons.items():
            put(Od, mk + "consensus_shares/" + v, LF(s))
        tnames = list(mr["treeroute_top3"])
        put(O, mk + "treeroute_top3/names", ("list", tnames))
        put(O, mk + "treeroute_top3/shares", ("nums", [share_of[("variable", tr)][v] for v in tnames]))
        cnames = list(mr["consensus_top3"])
        put(O, mk + "consensus_top3/names", ("list", cnames))
        put(Od, mk + "consensus_top3/shares", ("nums", [cons[v] for v in cnames]))
        crank = [v for v, _ in sorted(cons.items(), key=lambda kv: (-kv[1], kv[0]))]
        chk.append(("consensus top 3 == derived consensus ranking", crank[:3] == cnames))
        chk.append(("treeroute top 3 == derived ranking", rank[("variable", tr)][:3] == tnames))
        x = mr["own_history_share_treeroute"]
        iv(O, mk + "own_history_share_treeroute", x["value"], x["ci"][0], x["ci"][1], x["ci"][2])
        x = mr["own_history_share_median_rival"]
        iv(O, mk + "own_history_share_median_rival", x["value"], x["ci"][0], x["ci"][1], x["ci"][2])
        for rv in rivals:
            sh = fam[(fam.model == rv) & (fam.family == "own history")].share.iloc[0]
            put(O, mk + "own_history_share_per_rival/" + rv, LF(sh))
    else:
        # no same-link guard-passing rival (fire): compare_shap.py l.361 writes none of the rival keys; they are
        # undefined (brief item 7), so they are null here
        for k in ("spearman_top20_union_median", "spearman_top20_union_min", "spearman_top20_union_max",
                  "rbo_p090_vs_consensus", "own_history_share_median_rival"):
            iv(O, mk + k, None, None, None, None)
        for k in ("spearman_top20_union_per_rival", "consensus_shares", "consensus_top3",
                  "own_history_share_per_rival", "median_rival_name"):
            put(O, mk + k, ("leaf", None))
        # treeroute's top 3 and own-history share are NOT written by compare_shap.py for this problem; the
        # full-sample values exist in importance.parquet and families.parquet (derived, Od), the interval nowhere
        rk = rank[("variable", tr)][:3]
        put(Od, mk + "treeroute_top3/names", ("list", rk))
        put(Od, mk + "treeroute_top3/shares", ("nums", [share_of[("variable", tr)][v] for v in rk]))
        sh = fam[(fam.model == tr) & (fam.family == "own history")].share.iloc[0]
        put(Od, mk + "own_history_share_treeroute/value", LF(sh))
    # nonzero forecasts of arcsine-link models (item 8)
    nz = per["nonzero_forecast_rows"]
    put(O, "nonzero_forecast/models_covered", ("set", sorted(nz.keys())))
    allv = sorted(imp[imp.level == "variable"].player.unique())
    for m, v in nz.items():
        k = "nonzero_forecast/models/%s/" % m
        put(O, k + "rows_used", LF(v["rows"]))
        put(O, k + "top10/names", ("list", [x[0] for x in v["top10"]]))
        put(O, k + "top10/shares", ("nums", [float(x[1]) for x in v["top10"]]))
        put(Od, k + "level", LF("variable"))
        put(Od, k + "J", ("set", allv))         # compare_shap.py l.312-315: shares over every variable-level player
    raw = {"per": per, "imp": imp, "fam": fam, "pr": pr, "bs": bs, "mr": mr, "aw3": aw3, "aw4": aw4, "done": done,
           "Jsets": Jsets, "rank": rank, "share_of": share_of, "I_of": I_of}
    summary.setdefault("official_internal_checks", {})[p] = [[c, bool(ok)] for c, ok in chk]
    return O, Od, raw


# ------------------------------------------------------------------------------------------------------------
# Comparison

def status_pair(x, y):
    """x, y: entries or None (absent)."""
    if x is None and y is None:
        return "absent_both"
    if x is None or y is None:
        present = x if y is None else y
        if R.is_null(present):
            return "null_vs_absent"
        return "missing_in_first" if x is None else "missing_in_second"
    return "match" if R.entry_eq("", x, y) else "diff"


def status_key(key, x, y):
    if x is None or y is None:
        return status_pair(x, y)
    return "match" if R.entry_eq(key, x, y) else "diff"


def compare_all(A, B, O, Od):
    keys = sorted(set(A) | set(B) | set(O) | set(Od))
    rows = []
    for k in keys:
        is_b1 = k.startswith("b1/")
        if is_b1 and (k in O or k in Od):
            raise SystemExit("an official key under b1/: " + k)
        ea, eb = A.get(k), B.get(k)
        eo = None if is_b1 else O.get(k)
        eod = None if is_b1 else Od.get(k)
        st = {"AB": status_key(k, ea, eb)}
        if not is_b1:
            st["AO"] = status_key(k, ea, eo)
            st["BO"] = status_key(k, eb, eo)
            if eo is None and eod is not None:
                st["AOd"] = status_key(k, ea, eod)
                st["BOd"] = status_key(k, eb, eod)
        rows.append((k, ea, eb, eo, eod, st))
    return rows


def verdict(st, is_b1):
    """match: every source that has the key agrees and none holds a number the others lack."""
    bad = {"diff", "missing_in_first", "missing_in_second"}
    used = ["AB"] if is_b1 else ["AB", "AO", "BO"]
    if any(st[u] in bad for u in used):
        return "mismatch"
    if any(st[u] == "null_vs_absent" for u in used):
        return "match_no_number"
    return "match"


# ------------------------------------------------------------------------------------------------------------
# Causes (every mismatching key is put in exactly one group; each group's diagnosis is in GROUPS below and is
# written into mismatches.json)

def classify(k, ea, eb, eo, eod, st):
    is_b1 = k.startswith("b1/")
    if is_b1:
        if "/feature/pair_main_b1/tv_family_shares" in k:
            return "C15_feature_family_tvd_B1"
        return "B1_unclassified"
    if re.search(r"/pairs/[^/]+/sign_n_agree/(ci_low|ci_high|n_finite)$", k) and eo is None and eod is None:
        return "C08_no_interval_count"
    if k.endswith("/families/test_set_columns"):
        return "test_set_columns_text"
    if "/levels/feature/pairs/" in k and "/tv_family_shares" in k:
        return "C15_feature_family_tvd"
    if re.search(r"/family_shares/(own_history|context_and_calendar)", k) and (R.is_null(ea) or ea is None):
        return "C15_empty_family"
    if "/main_row/own_history_share" in k and k.startswith("problems/coral/"):
        return "C15_empty_family"
    if "/family_mean_abs/" in k:
        return "O_only_family_mean_abs"
    m_ = re.match(r"problems/([^/]+)/levels/([^/]+)/models/([^/]+)/players/([^/]+)/", k)
    if m_:
        p, L, m, j = m_.groups()
        if eo is not None and ea is None and eb is None:
            return "O_only_structural_zero_rows"
        if k.endswith(("/ci_low", "/ci_high", "/n_finite")) and eo is None:
            return "no_interval_importance"
    if re.search(r"/family_shares/[^/]+/(ci_low|ci_high|n_finite)$", k) and eo is None:
        return "no_interval_family_share"
    if re.search(r"/models/[^/]+/n_nonzero/(ci_low|ci_high|n_finite)$", k) and "/nonzero_forecast/" not in k \
            and eo is None:
        return "C08_no_interval_count"
    if re.search(r"/pairs/[^/]+/sign_n_determined/(ci_low|ci_high|n_finite)$", k) and eo is None:
        return "C08_no_interval_count"
    if re.search(r"/pairs/[^/]+/sign_agreement/(ci_low|ci_high|n_finite)$", k):
        return "sign_agreement_no_interval"
    if re.search(r"/main_row/spearman_top20_union_(min|max)/(ci_low|ci_high|n_finite)$", k):
        return "C22_range_no_interval"
    if "/main_row/median_rival_name" in k:
        return "C23_median_rival_name"
    if k.startswith("problems/fire/main_row/") and ("treeroute_top3" in k or "own_history_share_treeroute" in k):
        return "fire_main_row_missing"
    if "/nonzero_forecast/" in k and eo is None:
        return "C25_item8_scope"
    if "/nonzero_forecast/models/" in k and k.endswith("/J"):
        return "C25_item8_scope"
    if "/per_problem/kendall_w" in k or "/per_problem/mean_pairwise_spearman" in k or "/main_row/kendall_w" in k:
        if k.endswith("/n_finite") and R.is_null(ea) and R.is_null(eb) and eo is not None and eo[1] == 0:
            return "undefined_nan_zero_replicates"
    if eo is None and eod is not None:
        return "derived_only"
    return "unclassified"


# cause, kind, affects_reported_numbers, diagnosis (plain words; written into mismatches.json)
GROUPS = {
    "fire_main_row_missing": (
        "compare_shap.py writes no treeroute top 3 and no treeroute own-history share in fire's main row",
        "compare_bug", True,
        "PROTOCOL.md section 8, main-text row: 'treeroute's top 3 variables; the consensus top 3; the own-history "
        "share of treeroute [CI] and of the median rival [CI]'; the brief, item 7: 'Fire's main set is treeroute "
        "alone: W and the pair statistics are undefined there, and treeroute's top 3 and own-history share still have "
        "values.' compare_shap.py main_text_row() writes treeroute_top3 and own_history_share_treeroute only inside "
        "'if tr and rivals:' (lines 361-386), so fire's AW4_main_row.json and AW4_table.md hold neither. A and B "
        "agree on both numbers. The full-sample top 3 and share are in importance.parquet and families.parquet and "
        "equal A's and B's (derived check); the interval of the share is in no official file. Finding for the owner."),
    "sign_agreement_no_interval": (
        "compare_shap.py does not recompute the sign agreement on the draws: no interval (finite_replicates written "
        "as 0)", "compare_bug", False,
        "PROTOCOL.md section 8 lists the sign agreement among the 'Pairwise statistics, every pair, both levels' and "
        "says 'The importances, every statistic and every number of the main-text row are recomputed per draw. "
        "Percentile 95% intervals, each with its number of finite replicates.'; section 10 asks S3.13 for 'pairs x "
        "statistics with intervals'. compare_shap.py (lines 227-235) evaluates the sign agreement on the full sample "
        "only and writes ci_low = ci_high = NaN and finite_replicates = 0 although no draw was evaluated. A and B "
        "recompute it on every draw (that draw's top-10 union and signed means, the determined set fixed by the "
        "bootstrap interval) and agree on every interval. The full-sample values and the sign counts agree "
        "(A = B = official). No reported value changes; an interval the protocol's words ask for is absent. Finding "
        "for the owner."),
    "no_interval_importance": (
        "importance.parquet holds no interval for I, s and S (full-sample values only)", "open_choice", False,
        "A and B give every player's I, share and signed mean a percentile interval with its finite count, and agree "
        "on all of them. compare_shap.py recomputes the importances on every draw (lines 201-208) but writes only "
        "the full-sample mean_abs, share, signed_mean and sign_determined (lines 245-248). Section 8 says the "
        "importances are 'recomputed per draw' (they are) and that intervals are 'Percentile 95% intervals, each "
        "with its number of finite replicates'; it does not say that each importance is reported with an interval, "
        "and section 10 lists for S3.13 'pairs x statistics with intervals ... each model's top-10 with shares; "
        "family shares'. Not one of the spec's C entries (spec 2.2 item 6: 'The format does not decide which numbers "
        "get an interval'). compare_shap's choice: no interval. No reported number changes."),
    "no_interval_family_share": (
        "families.parquet holds no interval for the family shares", "open_choice", False,
        "As for the importances: families.parquet holds each family's full-sample mean_abs and share (compare_shap.py "
        "lines 264-275); only the own-history share of the main row and the family TVD are bootstrapped. A and B "
        "give every family share an interval and agree. compare_shap's choice: no interval. No reported number "
        "changes."),
    "C08_no_interval_count": (
        "counts carry no interval in the official outputs (n_nonzero, sign_n_determined, sign_n_agree)",
        "open_choice", False,
        "Spec C08 (section 10: 'or whether a count gets an interval'). A and B recompute the counts on every draw and "
        "give intervals (they agree); per_lead.json nonzero_players and pairs.parquet signs_compared are full-sample "
        "counts only. compare_shap's choice: no interval for a count. The values agree; compare_shap counts nonzero "
        "players over J (line 333), A and B over each model's own columns (C09), with equal counts everywhere. For "
        "B1, section 10 says the B1 numbers 'make the main comparison's choice (compare_shap.py)', so B1's counts "
        "should be reported without intervals (their values stand)."),
    "C22_range_no_interval": (
        "the main row's range (min and max over the rivals) has no interval in the official output", "open_choice",
        False,
        "Spec C22 ('what the range reports (its two ends), and whether its ends get intervals'). compare_shap.py "
        "(lines 379-380) reports the full-sample min and max; section 8's row reads 'the median of the "
        "top-20-union Spearman [CI] and the range'. A and B give each end an interval and agree. The values agree."),
    "C23_median_rival_name": (
        "the official main row names no 'median rival'", "open_choice", False,
        "Spec C23. compare_shap.py takes the median of the rivals' own-history shares (numpy median, line 385) and "
        "names no rival; A and B name the rival whose full-sample share is that median when the count of rivals is "
        "odd (defo and pm25: rival_lgbm). The median's value and interval agree (A = B = official)."),
    "C25_item8_scope": (
        "item 8: the official outputs hold only the rows and the top-10 shares (over all variables), full sample",
        "open_choice", False,
        "Spec C25 ('which numbers the variable-level importances are ... over which set of variables the shares are "
        "taken ... whether these numbers get intervals'). compare_shap.py (lines 302-315) reports per arcsine model "
        "the number of rows with pre > 0 and the top 10 [name, share] (per_lead.json nonzero_forecast_rows, the AW3 "
        "table), with shares over every variable-level player of the problem; A and B add I, S, intervals, counts, "
        "the ranking and the regions used, with shares over the level's J. The numbers the official outputs hold "
        "(rows, top-10 names and shares) equal A's and B's; the share denominators differ only by the structural "
        "zeros, which are 0 on those rows."),
    "C15_feature_family_tvd": (
        "feature-level family-share distance: A null, B the variable-level number, compare_shap none (variable "
        "level only)", "open_choice", False,
        "Spec C15 ('whether the feature-level pairs carry a family-share distance, and from which phi'). Families "
        "are sums of variable-level phi (section 8), so A writes no feature-level family TVD; B repeats the "
        "variable-level value (its X03); compare_shap.py computes tvd_family at the variable level only (lines "
        "281-295), which is A's choice. The variable-level family TVD agrees (A = B = official)."),
    "C15_feature_family_tvd_B1": (
        "B1 feature-level family-share distance: A null, B the variable-level number", "open_choice", False,
        "The same open choice for the B1 pair. Section 10: the B1 numbers 'make the main comparison's choice "
        "(compare_shap.py), as the independent re-computation establishes it'; compare_shap has no feature-level "
        "family TVD, so A's B1 choice is the one to report. B's extra value equals its own variable-level B1 family "
        "TVD, which agrees with A's."),
    "C15_empty_family": (
        "a family with no variable (coral own history, defo context and calendar): A null, B and compare_shap 0",
        "open_choice", False,
        "Spec C15 ('a family with no variable in a problem'). compare_shap.py gives an empty family a zero row sum "
        "and share 0 (lines 268-274), and coral's main-row own-history shares 0.00 [0.00, 0.00] with 2,000 finite "
        "replicates; B does the same; A writes null with its why. The reported numbers are compare_shap's (0). No B1 "
        "problem has an empty family."),
    "undefined_nan_zero_replicates": (
        "fire's W and mean pairwise Spearman: official NaN with 0 finite replicates, A and B null", "other", False,
        "The main set of fire is treeroute alone. compare_shap evaluates W and the mean Spearman on every draw and "
        "finds none finite (value NaN, interval NaN, finite_replicates 0); A and B write them as undefined by "
        "definition (null, n_finite null). Same meaning, different notation."),
    "O_only_structural_zero_rows": (
        "importance.parquet also holds rows for the structural zeros (players outside J)", "other", False,
        "A and B report players of J only (spec 2.4: 'players holds one entry per player of J'); compare_shap writes "
        "one row per player and model, J or not. These 898 rows (3,592 numbers) have no counterpart in A or B; "
        "every one is exactly 0 (mean |phi|, share and signed mean) with sign_determined false."),
    "O_only_family_mean_abs": (
        "families.parquet mean_abs has no results.json key", "other", False,
        "Each family's region-weighted mean |row sum| (the numerator of its share). A and B report the family "
        "shares, which agree with the official shares; the unnormalised value has no key in the spec."),
    "derived_only": (
        "lists and counts that no official file holds, derived from official numbers by compare_shap's rules",
        "other", False,
        "Rankings over J, the top-20 and top-10 unions, the determined-in-both sets, both_in_main_set, sign_n_agree, "
        "W's m and n, the main row's rivals, consensus shares and consensus top-3 shares, the region order and the "
        "global-index list are not written by compare_shap.py. Rebuilt from the official files with compare_shap's "
        "own rules (mapping.md), every one equals A's and B's."),
    "test_set_columns_text": (
        "A and B list different columns read from the lead's test set (an I04 record, not a number)", "other", False,
        "A also lists the context columns it read and B the column 'issue'; both read the same records (the rivals' "
        "export, lead_0\\test) and their global-index lists equal each other and per_lead.json's family map."),
}


# ------------------------------------------------------------------------------------------------------------
# Second check: the rounded .md tables

def fmt2(v):
    return "nan" if v is None or (isinstance(v, float) and not math.isfinite(v)) else "%.2f" % v


def fmt_pct(v):
    return "%.1f%%" % (100 * v)


CELL = re.compile(r"^(nan|-?\d+\.\d+) \[(nan|-?\d+\.\d+), (nan|-?\d+\.\d+)\]$")
SIGN = re.compile(r"^(nan|-?\d+\.\d+) \((\d+) signs\)$")


def get_leaf(F, key):
    e = F.get(key)
    if e is None:
        return "ABSENT"
    return e[1]


def second_checks(p, raw, A, B, O):
    """Every rounded number of AW3_table.md and AW4_table.md against the official unrounded value and A's and B's."""
    res = []          # (where, table text, official unrounded formatted, A formatted, B formatted, ok)
    base = "problems/%s/" % p

    def cmp(where, cell, keyv, fmt=fmt2, also=None):
        out = [where, cell]
        for F in (O, A, B):
            v = get_leaf(F, keyv) if keyv else None
            if v == "ABSENT":
                out.append("ABSENT")
            else:
                out.append(fmt(v) if (v is not None or fmt is fmt2) else "null")
        ok_o = out[2] == cell
        ok_a = out[3] == cell or out[3] in ("ABSENT",)
        ok_b = out[4] == cell or out[4] in ("ABSENT",)
        res.append(out + [ok_o, out[3] == cell, out[4] == cell])

    level = None
    stats = None
    lines = raw["aw3"].splitlines()
    in_fam = False
    fam_models = None
    in_nz = False
    for ln in lines:
        mlev = re.match(r"^## (variable|feature) level", ln)
        if mlev:
            level, in_fam, in_nz = mlev.group(1), False, False
            continue
        if ln.startswith("## Families"):
            level, in_fam, in_nz = None, True, False
            continue
        if ln.startswith("## Nonzero forecasts"):
            level, in_fam, in_nz = None, False, True
            continue
        if level and ln.startswith("| Pair | label |"):
            stats = [c.strip() for c in ln.strip("|").split("|")][2:]
            continue
        if level and ln.startswith("| ") and " vs " in ln:
            cells = [c.strip() for c in ln.strip().strip("|").split(" | ")]
            a, b = cells[0].split(" vs ")
            for s, cell in zip(stats, cells[2:]):
                key = base + "levels/%s/pairs/%s|%s/%s" % (level, a, b, STAT[s])
                if s == "sign_agreement_top10":
                    mm = SIGN.match(cell)
                    cmp("AW3 %s %s|%s %s" % (level, a, b, s), mm.group(1), key + "/value")
                    cmp("AW3 %s %s|%s signs" % (level, a, b), mm.group(2),
                        base + "levels/%s/pairs/%s|%s/sign_n_determined/value" % (level, a, b),
                        fmt=lambda v: "%d" % int(round(v)) if v is not None else "null")
                elif cell == "":
                    continue
                else:
                    mm = CELL.match(cell)
                    for part, txt in zip(("value", "ci_low", "ci_high"), mm.groups()):
                        cmp("AW3 %s %s|%s %s %s" % (level, a, b, s, part), txt, key + "/" + part)
            continue
        mw = re.match(r"^Kendall's W \(main set\) = (\S+) \[(\S+), (\S+)\]; mean pairwise Spearman \(main set\) = "
                      r"(\S+) \[(\S+), (\S+)\]\.$", ln)
        if level and mw:
            g = mw.groups()
            for i, part in enumerate(("value", "ci_low", "ci_high")):
                cmp("AW3 %s W %s" % (level, part), g[i], base + "levels/%s/per_problem/kendall_w/%s" % (level, part))
                cmp("AW3 %s mean rho %s" % (level, part), g[3 + i],
                    base + "levels/%s/per_problem/mean_pairwise_spearman/%s" % (level, part))
            continue
        if level and ln.startswith("Stability under region resampling"):
            body = ln.split("): ", 1)[1]
            for item in body.split(", "):
                m, v = item.rsplit(" ", 1)
                cmp("AW3 %s stability %s" % (level, m), v, base + "levels/%s/per_problem/stability/%s/value" % (level, m))
            continue
        mt = re.match(r"^- (\S+) top-10 \((\d+) nonzero\): (.*)$", ln)
        if level and mt:
            m, nzc, body = mt.groups()
            cmp("AW3 %s %s nonzero" % (level, m), nzc, base + "levels/%s/models/%s/n_nonzero/value" % (level, m),
                fmt=lambda v: "%d" % int(round(v)) if v is not None else "null")
            items = [it.rsplit(" ", 1) for it in body.split("; ")]
            names = [x[0] for x in items]
            for F, tag in ((O, "O"), (A, "A"), (B, "B")):
                e = F.get(base + "levels/%s/models/%s/top10/names" % (level, m))
                res.append(["AW3 %s %s top-10 names (%s)" % (level, m, tag), "; ".join(names),
                            "; ".join(e[1]) if e else "ABSENT", "", "", e is not None and e[1] == names,
                            True, True])
            for i, (nm, pc) in enumerate(items):
                vals = []
                for F in (O, A, B):
                    e = F.get(base + "levels/%s/models/%s/top10/shares" % (level, m))
                    vals.append(fmt_pct(e[1][i]) if e and i < len(e[1]) else "ABSENT")
                res.append(["AW3 %s %s top-10 #%d %s" % (level, m, i + 1, nm), pc] + vals +
                           [vals[0] == pc, vals[1] == pc, vals[2] == pc])
            continue
        if in_fam and ln.startswith("| Family |"):
            fam_models = [c.strip() for c in ln.strip().strip("|").split("|")][1:]
            continue
        if in_fam and ln.startswith("| ") and not ln.startswith("|---"):
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            f = FAM[cells[0]]
            for m, cell in zip(fam_models, cells[1:]):
                if cell == "":
                    continue
                key = base + "levels/variable/models/%s/family_shares/%s/value" % (m, f)
                vals = []
                for F in (O, A, B):
                    v = get_leaf(F, key)
                    vals.append("ABSENT" if v == "ABSENT" else ("null" if v is None else fmt_pct(v)))
                res.append(["AW3 family %s %s" % (m, f), cell] + vals + [vals[0] == cell, vals[1] == cell,
                                                                         vals[2] == cell])
            continue
        mz = re.match(r"^- (\S+), (\d+) rows: (.*)$", ln)
        if in_nz and mz:
            m, nrows, body = mz.groups()
            cmp("AW3 nonzero %s rows" % m, nrows, base + "nonzero_forecast/models/%s/rows_used" % m,
                fmt=lambda v: "%d" % int(v) if v is not None else "null")
            items = [it.rsplit(" ", 1) for it in body.split("; ")]
            for i, (nm, pc) in enumerate(items):
                vals = []
                for F in (O, A, B):
                    en = F.get(base + "nonzero_forecast/models/%s/top10/names" % m)
                    es = F.get(base + "nonzero_forecast/models/%s/top10/shares" % m)
                    vals.append(("%s %s" % (en[1][i], fmt_pct(es[1][i]))) if en and es and i < len(en[1]) else "ABSENT")
                want = "%s %s" % (nm, pc)
                res.append(["AW3 nonzero %s #%d" % (m, i + 1), want] + vals + [vals[0] == want, vals[1] == want,
                                                                                vals[2] == want])
            continue
    # AW4_table.md: the one data row
    row = [ln for ln in raw["aw4"].splitlines() if ln.startswith("| %s " % p)]
    if len(row) == 1:
        cells = [c.strip() for c in row[0].strip().strip("|").split(" | ")]
        mw = CELL.match(cells[2])
        for part, txt in zip(("value", "ci_low", "ci_high"), mw.groups()):
            cmp("AW4 W %s" % part, txt, base + "main_row/kendall_w/" + part)
        msp = re.match(r"^(\S+) \[(\S+), (\S+)\] \((\S+) to (\S+)\)$", cells[3])
        if msp:
            g = msp.groups()
            for part, txt in zip(("value", "ci_low", "ci_high"), g[:3]):
                cmp("AW4 median rho %s" % part, txt, base + "main_row/spearman_top20_union_median/" + part)
            cmp("AW4 range min", g[3], base + "main_row/spearman_top20_union_min/value")
            cmp("AW4 range max", g[4], base + "main_row/spearman_top20_union_max/value")
            mr_ = CELL.match(cells[4])
            for part, txt in zip(("value", "ci_low", "ci_high"), mr_.groups()):
                cmp("AW4 RBO %s" % part, txt, base + "main_row/rbo_p090_vs_consensus/" + part)
            for col, key in ((5, "treeroute_top3"), (6, "consensus_top3")):
                names = [x.strip() for x in cells[col].split(",")]
                for F, tag in ((O, "O"), (A, "A"), (B, "B")):
                    e = F.get(base + "main_row/%s/names" % key)
                    res.append(["AW4 %s names (%s)" % (key, tag), ", ".join(names), ", ".join(e[1]) if e else "ABSENT",
                                "", "", e is not None and e[1] == names, True, True])
            mo = re.match(r"^(\S+) \[(\S+), (\S+)\] / (\S+) \[(\S+), (\S+)\]$", cells[7])
            g = mo.groups()
            for i, part in enumerate(("value", "ci_low", "ci_high")):
                cmp("AW4 own history treeroute %s" % part, g[i], base + "main_row/own_history_share_treeroute/" + part)
                cmp("AW4 own history median rival %s" % part, g[3 + i],
                    base + "main_row/own_history_share_median_rival/" + part)
        else:
            # no same-link rival (fire): the four cells after the note are empty in the official table, while
            # section 8 asks for treeroute's top 3 and own-history share there; A's and B's values are listed
            empty_tail = re.search(r"\|\s*\|\s*\|\s*\|\s*\|\s*$", row[0]) is not None
            res.append(["AW4 row (no rival): last four cells empty", "yes" if empty_tail else "no", "", "", "",
                        True, True, True])
            for key in ("treeroute_top3", ):
                for F, tag in ((A, "A"), (B, "B")):
                    e = F.get(base + "main_row/%s/names" % key)
                    res.append(["AW4 row (no rival): %s of %s (not in the table)" % (key, tag), "",
                                ", ".join(e[1]) if e else "ABSENT", "", "", True, True, True])
    else:
        res.append(["AW4 data row", "found %d rows" % len(row), "", "", "", False, False, False])
    return res


# ------------------------------------------------------------------------------------------------------------
# Per-draw values: bootstrap_stats.parquet against A's and B's npz; and A's npz against B's npz

def close_arrays(x, y):
    x = np.asarray(x, np.float64)
    y = np.asarray(y, np.float64)
    if x.shape != y.shape:
        return False, float("inf"), -1
    fx, fy = np.isfinite(x), np.isfinite(y)
    same_nan = (~fx & ~fy)
    d = np.where(fx & fy, np.abs(x - y), np.where(same_nan, 0.0, np.inf))
    tolok = (d <= R.TOL) | (d <= R.TOL * np.maximum(np.abs(np.where(fx, x, 0)), np.abs(np.where(fy, y, 0))))
    nbad = int((~tolok).sum())
    dm = float(np.max(np.where(np.isfinite(d), d, 0.0))) if d.size else 0.0
    if np.isinf(d).any():
        dm = float("inf")
    return nbad == 0, dm, nbad


def per_draw_checks(p, raw, summary):
    out = {"bootstrap_stats_vs_A": {}, "bootstrap_stats_vs_B": {}, "A_vs_B_npz": {}}
    za = np.load(os.path.join(R.V, "A", "draws", p + ".npz"), allow_pickle=False)
    zb = np.load(os.path.join(R.V, "B", "draws", p + ".npz"), allow_pickle=False)
    bs = raw["bs"]
    for (L, pair), g in bs.groupby(["level", "pair"], sort=False):
        g = g.sort_values("draw")
        assert g["draw"].tolist() == list(range(2000))
        for col, sk in BS_STAT.items():
            key = "levels/%s/pairs/%s/%s" % (L, pair, sk)
            for X, z in (("A", za), ("B", zb)):
                if key not in z.files:
                    out["bootstrap_stats_vs_" + X][key] = {"ok": False, "why": "absent in npz"}
                    continue
                ok, dm, nbad = close_arrays(g[col].to_numpy(), z[key])
                out["bootstrap_stats_vs_" + X][key] = {"ok": ok, "max_abs_diff": dm, "draws_off": nbad}
    out["A_vs_B_npz"] = npz_ab(za, zb)
    return out


def npz_ab(za, zb):
    res = {"keys_A": len(za.files), "keys_B": len(zb.files), "only_A": [], "only_B": [], "bad": {}, "n_ok": 0}
    fa, fb = set(za.files), set(zb.files)
    res["only_A"] = sorted(fa - fb)
    res["only_B"] = sorted(fb - fa)
    for k in sorted(fa & fb):
        if k.endswith("/names"):
            continue
        xa, xb = za[k], zb[k]
        if xa.ndim == 2:
            base = k.rsplit("/", 1)[0]
            na, nb = list(za[base + "/names"]), list(zb[base + "/names"])
            if set(na) != set(nb):
                res["bad"][k] = {"why": "different player sets"}
                continue
            ib = {n: i for i, n in enumerate(nb)}
            xb = xb[:, [ib[n] for n in na]]
        ok, dm, nbad = close_arrays(xa, xb)
        if ok:
            res["n_ok"] += 1
        else:
            res["bad"][k] = {"max_abs_diff": dm, "entries_off": nbad}
    return res


# ------------------------------------------------------------------------------------------------------------
# B1 checks (item 9; no official output)

def read_json_logged(path):
    log_other(path)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def b1_checks(RA, RB, summary):
    out = {}
    reg = {}
    rp = os.path.join(R.SHAP, "SAMPLE_REGISTER.txt")
    log_other(rp)
    with open(rp, "r", encoding="utf-8") as f:
        for ln in f:
            mp = re.search(r"problem=(\S+)", ln)
            ms = re.search(r"\bsample=([0-9a-f]{64})", ln)
            ml = re.search(r"leads=(\S+)", ln)
            if mp and ms and ml and "0" in ml.group(1).split(","):
                reg[mp.group(1)] = ms.group(1)
    for p in R.PROBLEMS:
        o = {}
        fold = os.path.join(R.SHAP, "out", p, "lead_0", "treeroute_B1")
        o["folder_exists"] = os.path.isdir(fold)
        o["has_done_json"] = os.path.isfile(os.path.join(fold, "rows.parquet.done.json"))
        o["has_failed_json"] = os.path.isfile(os.path.join(fold, "FAILED.json"))
        o["registered_sample_sha256"] = reg.get(p)
        stA, stB = RA["b1"][p]["status"], RB["b1"][p]["status"]
        o["A_status"] = {k: stA.get(k) for k in ("folder_exists", "has_done_json", "has_failed_json", "finished",
                                                  "numbers", "per_lead_models_lists_treeroute_B1",
                                                  "sample_sha256_is_registered", "background_is_B1")}
        o["B_status"] = {k: stB.get(k) for k in o["A_status"]}
        o["A_registered"] = stA.get("sample_sha256_registered")
        o["B_registered"] = stB.get("sample_sha256_registered")
        if o["folder_exists"] and o["has_done_json"]:
            meta = read_json_logged(os.path.join(fold, "meta.json"))
            dj = read_json_logged(os.path.join(fold, "rows.parquet.done.json"))
            mmain = read_json_logged(os.path.join(R.SHAP, "out", p, "lead_0", "treeroute", "meta.json"))
            fields = ("pass", "checks_passed", "rows", "background", "pairs", "trees_used", "sample_sha256",
                      "duplicates_merged")
            o["meta"] = {k: meta.get(k) for k in fields}
            o["meta_players_nonzero"] = meta.get("players_nonzero")
            o["meta_variables_nonzero"] = meta.get("variables_nonzero")
            o["meta_tree_shap_seconds"] = meta.get("tree_shap_seconds")
            o["done_seconds"] = dj.get("seconds")
            o["main_duplicates_merged"] = sorted((mmain.get("duplicates_merged") or {}).keys())
            o["b1_duplicates_merged"] = sorted((meta.get("duplicates_merged") or {}).keys())
            o["A_meta_equal"] = stA.get("meta") == o["meta"]
            o["B_meta_equal"] = stB.get("meta") == o["meta"]
            o["sample_is_registered"] = meta.get("sample_sha256") == reg.get(p)
            # nonzero counts of A and B against meta.json
            if p != "defo":
                cnt = {}
                for X, RX in (("A", RA), ("B", RB)):
                    fe = RX["b1"][p]["feature"]["importance"]
                    va = RX["b1"][p]["variable"]["importance"]
                    cnt[X] = {"feature_n_nonzero_before_merge": fe["n_nonzero_before_merge"]["value"],
                              "feature_n_nonzero": fe["n_nonzero"]["value"],
                              "variable_n_nonzero": va["n_nonzero"]["value"]}
                o["nonzero_counts"] = cnt
                o["nonzero_vs_meta"] = {
                    X: {"before_merge_eq_players_nonzero": cnt[X]["feature_n_nonzero_before_merge"] == meta.get("players_nonzero"),
                        "after_merge_eq_players_nonzero": cnt[X]["feature_n_nonzero"] == meta.get("players_nonzero"),
                        "variable_eq_variables_nonzero": cnt[X]["variable_n_nonzero"] == meta.get("variables_nonzero")}
                    for X in ("A", "B")}
            # run facts of A and B against the records
            for X, RX in (("A", RA), ("B", RB)):
                run = RX["b1"][p]["identity"] if p == "defo" else RX["b1"][p]["run"]
                o[X + "_run"] = {k: run.get(k) for k in ("log_setup_line_number", "log_done_line_number", "pairs_log",
                                                         "pairs_meta", "total_seconds_log", "total_seconds_done_json",
                                                         "tree_shap_seconds_log", "tree_shap_seconds_meta")}
            # the log, numbers only
            lp = os.path.join(R.SHAP, "logs", "tr_shap_%s_lead0.log" % p)
            log_other(lp)
            with open(lp, "r", encoding="utf-8", errors="replace") as f:
                lines = f.read().splitlines()
            setup = done_ = None
            for i, ln in enumerate(lines, 1):
                mt = re.match(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}):\d{2} ", ln)
                if not mt or mt.group(1) < B1_START:
                    continue
                if setup is None and "background pairs" in ln:
                    setup = (i, int(re.search(r"(\d+) background pairs", ln).group(1)))
                md = re.search(r"done in ([\d.]+) s \(tree SHAP ([\d.]+) s\)", ln)
                if setup is not None and done_ is None and md:
                    done_ = (i, float(md.group(1)), float(md.group(2)))
                mn = re.search(r"treeroute: \d+ rows, \d+ players \((\d+) nonzero\), \d+ variables \((\d+) nonzero\)",
                               ln)
                if setup is not None and mn:
                    o["log_nonzero"] = [int(mn.group(1)), int(mn.group(2))]
            o["log"] = {"setup_line": setup[0] if setup else None, "pairs": setup[1] if setup else None,
                        "done_line": done_[0] if done_ else None, "total_seconds": done_[1] if done_ else None,
                        "tree_shap_seconds": done_[2] if done_ else None}
        if p == "defo" and o.get("has_done_json"):
            o["identity_reconciler"] = defo_identity()
            for X, RX in (("A", RA), ("B", RB)):
                idt = RX["b1"]["defo"]["identity"]
                o[X + "_identity"] = {k: idt.get(k) for k in (
                    "max_abs_diff_phi", "max_abs_diff_phiv", "same_rows", "same_players", "same_variables",
                    "n_rows_main", "n_rows_b1", "n_players_main", "n_players_b1", "n_variables_main",
                    "n_variables_b1", "as_expected")}
        out[p] = o
    return out


def defo_identity():
    pm = os.path.join(R.SHAP, "out", "defo", "lead_0", "treeroute", "rows.parquet")
    pb = os.path.join(R.SHAP, "out", "defo", "lead_0", "treeroute_B1", "rows.parquet")
    log_other(pm)
    log_other(pb)
    M = pq.read_table(pm).to_pandas().set_index("row").sort_index()
    Bt = pq.read_table(pb).to_pandas().set_index("row").sort_index()
    res = {"n_rows_main": len(M), "n_rows_b1": len(Bt), "same_rows": sorted(M.index) == sorted(Bt.index)}
    for pref, tag in (("phi__", "phi"), ("phiv__", "phiv")):
        cm = sorted(c for c in M.columns if c.startswith(pref))
        cb = sorted(c for c in Bt.columns if c.startswith(pref))
        res["n_%s_main" % tag] = len(cm)
        res["n_%s_b1" % tag] = len(cb)
        res["same_%s" % tag] = cm == cb
        common = [c for c in cm if c in set(cb)]
        rows = M.index.intersection(Bt.index)
        dmat = np.abs(M.loc[rows, common].to_numpy(np.float64) - Bt.loc[rows, common].to_numpy(np.float64))
        res["max_abs_diff_%s" % tag] = float(dmat.max()) if dmat.size else None
        res["n_values_compared_%s" % tag] = int(dmat.size)
    return res


# ------------------------------------------------------------------------------------------------------------

def main():
    t0 = time.time()
    summary = {"run_started": R.now_local()}
    RA, A = R.load_results("A")
    RB, B = R.load_results("B")
    O, Od, RAW = {}, {}, {}
    for p in R.PROBLEMS:
        o, od, raw = official(p, summary)
        O.update(o)
        Od.update(od)
        RAW[p] = raw
    rows = compare_all(A, B, O, Od)
    # key counts per source and verdicts
    counts = {"A": len(A), "B": len(B), "official": len(O), "official_derived": len(Od)}
    nums = {"A": sum(R.count_numbers(e) for e in A.values()), "B": sum(R.count_numbers(e) for e in B.values()),
            "official": sum(R.count_numbers(e) for e in O.values())}
    groups = collections.OrderedDict()
    verdicts = collections.Counter()
    no_number_keys = []
    per_key = []
    for k, ea, eb, eo, eod, st in rows:
        is_b1 = k.startswith("b1/")
        v = verdict(st, is_b1)
        verdicts[("b1" if is_b1 else "items1_8", v)] += 1
        if v == "match_no_number":
            no_number_keys.append(k)
        if v != "mismatch":
            continue
        c = classify(k, ea, eb, eo, eod, st)
        groups.setdefault(c, []).append(k)
        per_key.append({"key": k, "group": c, "status": st, "A": R.show(ea), "B": R.show(eb),
                        "official": R.show(eo), "official_derived": R.show(eod),
                        "abs_diff_AB": R.entry_diff(ea, eb), "abs_diff_AO": R.entry_diff(ea, eo),
                        "abs_diff_BO": R.entry_diff(eb, eo)})
    # derived second check: for keys missing in O but present in Od, do A and B agree with the derivation?
    derived = collections.Counter()
    for k, ea, eb, eo, eod, st in rows:
        if "AOd" in st:
            derived[("A", st["AOd"])] += 1
            derived[("B", st["BOd"])] += 1
    summary["key_counts"] = counts
    summary["number_counts"] = nums
    summary["verdicts"] = {"%s %s" % kv: n for kv, n in verdicts.items()}
    summary["derived_second_check"] = {"%s %s" % kv: n for kv, n in derived.items()}
    summary["derived_disagreements"] = [
        {"key": k, "A": R.show(ea), "B": R.show(eb), "derived": R.show(eod), "st": st}
        for k, ea, eb, eo, eod, st in rows if "AOd" in st and (st["AOd"] != "match" or st["BOd"] != "match")][:200]
    summary["groups"] = {g: len(v) for g, v in groups.items()}
    summary["group_patterns"] = {g: collections.Counter(R.pattern(k) for k in v).most_common(40)
                                 for g, v in groups.items()}
    summary["no_number_keys_count"] = len(no_number_keys)
    summary["no_number_key_patterns"] = collections.Counter(R.pattern(k) for k in no_number_keys).most_common(40)
    # second checks
    sc = {}
    for p in R.PROBLEMS:
        sc[p] = second_checks(p, RAW[p], A, B, O)
    summary["second_checks"] = {p: {"n": len(v), "official_table_eq_unrounded": sum(1 for r in v if r[5]),
                                    "A_eq": sum(1 for r in v if r[6]), "B_eq": sum(1 for r in v if r[7]),
                                    "not_ok": [r for r in v if not (r[5] and r[6] and r[7])][:80]}
                                for p, v in sc.items()}
    # per-draw
    pdc = {}
    for p in R.PROBLEMS:
        pdc[p] = per_draw_checks(p, RAW[p], summary)
    for p in ("fire", "pm25", "ndvi"):
        za = np.load(os.path.join(R.V, "A", "draws", "b1_%s.npz" % p), allow_pickle=False)
        zb = np.load(os.path.join(R.V, "B", "draws", "b1_%s.npz" % p), allow_pickle=False)
        pdc["b1_" + p] = {"A_vs_B_npz": npz_ab(za, zb)}
    summary["per_draw"] = {
        p: {kind: ({"n": len(v), "n_ok": sum(1 for x in v.values() if x.get("ok")),
                    "max_abs_diff": max([x.get("max_abs_diff", 0) for x in v.values()] or [0]),
                    "bad": {k: x for k, x in v.items() if not x.get("ok")}}
                   if kind.startswith("bootstrap") else v)
            for kind, v in d.items()} for p, d in pdc.items()}
    # B1
    summary["b1"] = b1_checks(RA, RB, summary)
    # independence of items 1-8 from B1, from the official files
    ind = {}
    for p in R.PROBLEMS:
        per = RAW[p]["per"]
        ind[p] = {"per_lead_models_lists_treeroute_B1": "treeroute_B1" in per["models"],
                  "pairs_done_finished": RAW[p]["done"].get("finished"),
                  "compare_file_mtimes": {f: datetime.datetime.fromtimestamp(
                      os.stat(os.path.join(R.compare_dir(p), f)).st_mtime).astimezone().isoformat(timespec="seconds")
                      for f in ("per_lead.json", "importance.parquet", "families.parquet", "pairs.parquet",
                                "bootstrap_stats.parquet", "bootstrap_draws.npy", "AW3_table.md", "AW4_table.md",
                                "AW4_main_row.json")}}
        if p != "coral":
            # official treeroute importances against A's main and A's B1 values (same players)
            for L in ("feature", "variable"):
                I_o = RAW[p]["I_of"][(L, "treeroute")]
                b1p = RA["b1"][p][L]["importance"]["players"] if p != "defo" else {}
                mainp = RA["problems"][p]["levels"][L]["models"]["treeroute"]["players"]
                dm = max([abs(I_o[j] - mainp[j]["I"]["value"]) for j in mainp if j in I_o] or [0])
                db = max([abs(I_o[j] - b1p[j]["I"]["value"]) for j in b1p if j in I_o] or [0]) if b1p else None
                ind[p]["max_abs_official_minus_A_main_I_" + L] = dm
                ind[p]["max_abs_official_minus_A_B1_I_" + L] = db
    summary["independence"] = ind
    # extra facts (summary.json)
    summary["by_item"] = {}
    for k, ea, eb, eo, eod, st in rows:
        it = item_of(k)
        v = verdict(st, k.startswith("b1/"))
        summary["by_item"].setdefault(it, collections.Counter())[v] += 1
    summary["by_item"] = {it: dict(c) for it, c in summary["by_item"].items()}
    summary["matched_patterns"] = collections.Counter(
        R.pattern(k) for k, ea, eb, eo, eod, st in rows if verdict(st, k.startswith("b1/")) == "match").most_common()
    sz = {"rows": 0, "max_mean_abs": 0.0, "max_abs_share": 0.0, "max_abs_signed_mean": 0.0, "sign_determined_true": 0,
          "nonzero_mean_abs_rows": 0, "max_mean_abs_over_model_total": 0.0}
    for p in R.PROBLEMS:
        imp = RAW[p]["imp"]
        for (L, m), g in imp.groupby(["level", "model"]):
            tot = float(g.mean_abs.sum())
            z = g[~g.active]
            sz["rows"] += len(z)
            if len(z):
                sz["max_mean_abs"] = max(sz["max_mean_abs"], float(z.mean_abs.max()))
                sz["max_abs_share"] = max(sz["max_abs_share"], float(z.share.abs().max()))
                sz["max_abs_signed_mean"] = max(sz["max_abs_signed_mean"], float(z.signed_mean.abs().max()))
                sz["sign_determined_true"] += int(z.sign_determined.sum())
                sz["nonzero_mean_abs_rows"] += int((z.mean_abs > 0).sum())
                if tot > 0:
                    sz["max_mean_abs_over_model_total"] = max(sz["max_mean_abs_over_model_total"],
                                                              float(z.mean_abs.max()) / tot)
    summary["structural_zero_rows_official"] = sz
    # how close the matched numbers are: largest |difference| per comparison, over keys present in both sources
    close = {}
    for tag, i, j in (("A_vs_B_items1_8", 1, 2), ("A_vs_official", 1, 3), ("B_vs_official", 2, 3),
                      ("A_vs_B_b1", 1, 2)):
        best = {"n_numbers": 0, "max_abs_diff": 0.0, "key": None, "max_rel_diff": 0.0, "key_rel": None,
                "n_exactly_equal": 0}
        for r_ in rows:
            k = r_[0]
            if (tag == "A_vs_B_b1") != k.startswith("b1/"):
                continue
            x, y = r_[i], r_[j]
            if x is None or y is None or x[0] != y[0] or not R.entry_eq(k, x, y):
                continue                       # matched keys only (the mismatching ones are in mismatches.json)
            pairs_ = []
            if x[0] == "leaf" and R._isnum(x[1]) and R._isnum(y[1]):
                pairs_ = [(x[1], y[1])]
            elif x[0] == "nums" and len(x[1]) == len(y[1]):
                pairs_ = [(a, b) for a, b in zip(x[1], y[1]) if R._isnum(a) and R._isnum(b)]
            for a, b in pairs_:
                best["n_numbers"] += 1
                d = abs(float(a) - float(b))
                if d == 0:
                    best["n_exactly_equal"] += 1
                if d > best["max_abs_diff"]:
                    best["max_abs_diff"], best["key"] = d, k
                rel = d / max(abs(float(a)), abs(float(b))) if d > 0 else 0.0
                if rel > best["max_rel_diff"]:
                    best["max_rel_diff"], best["key_rel"] = rel, k
        close[tag] = best
    summary["closeness"] = close
    b1tvd = {}
    for p in ("fire", "pm25", "ndvi"):
        fb = RB["b1"][p]["feature"]["pair_main_b1"]["tv_family_shares"]
        vb = RB["b1"][p]["variable"]["pair_main_b1"]["tv_family_shares"]
        va = RA["b1"][p]["variable"]["pair_main_b1"]["tv_family_shares"]
        b1tvd[p] = {"B_feature": fb, "B_variable": vb, "A_variable": va,
                    "B_feature_equals_B_variable": all(R.num_eq(fb[x], vb[x], exact=(x == "n_finite")) for x in IV),
                    "A_variable_equals_B_variable": all(R.num_eq(va[x], vb[x], exact=(x == "n_finite")) for x in IV)}
    summary["b1_feature_family_tvd"] = b1tvd
    zero_det = []
    for k, ea, eb, eo, eod, st in rows:
        if k.endswith("/sign_agreement/n_finite") and not k.startswith("b1/") and eo is not None and \
                ea is not None and ea[1] == 0:
            zero_det.append(k.rsplit("/", 2)[0])
    summary["pairs_with_no_sign_determined_in_both"] = zero_det
    summary["seconds"] = round(time.time() - t0, 1)
    summary["run_finished"] = R.now_local()
    # outputs
    R.write_json(os.path.join(R.WORK, "summary.json"), summary)
    write_mismatches(per_key, groups, no_number_keys, counts, nums)
    print(json.dumps({k: summary[k] for k in ("key_counts", "number_counts", "verdicts", "groups",
                                               "derived_second_check", "seconds")}, indent=1))


def item_of(k):
    if k.startswith("b1/"):
        return "9"
    for pat, it in (("/active_set/", "1"), ("/families/", "3"), ("/family_shares/", "3"), ("/family_mean_abs/", "3"),
                    ("/models/", "2"), ("/pairs/", "4"), ("/per_problem/", "5"), ("/draws/", "6"),
                    ("/main_row/", "7"), ("/nonzero_forecast/", "8")):
        if pat in k:
            if pat == "/models/" and "/nonzero_forecast/" in k:
                return "8"
            return it
    return "copied structural keys"


def secondary(group, st):
    out = []
    if group == "C15_empty_family" and st.get("BO") == "missing_in_second":
        out.append("no_interval_family_share")
    return out


def write_mismatches(per_key, groups, no_number_keys, counts, nums):
    order = ["fire_main_row_missing", "sign_agreement_no_interval", "C15_empty_family", "C15_feature_family_tvd",
             "C15_feature_family_tvd_B1", "C08_no_interval_count", "C22_range_no_interval", "C23_median_rival_name",
             "C25_item8_scope", "no_interval_importance", "no_interval_family_share",
             "undefined_nan_zero_replicates", "O_only_structural_zero_rows", "O_only_family_mean_abs",
             "derived_only", "test_set_columns_text"]
    unknown = [g for g in groups if g not in GROUPS]
    if unknown:
        raise SystemExit("unclassified mismatch groups: %s" % unknown)
    order = [g for g in order if g in groups] + [g for g in groups if g not in order]
    head = {
        "written_at": R.now_local(),
        "what": "Every key on which A, B and the official outputs (items 1-8) or A and B (item 9, B1) do not agree, "
                "including every number that one source holds and another lacks. Keys are results.json paths joined "
                "by '/'; a top-k list is two keys, '<path>/names' and '<path>/shares'; an interval object is four "
                "keys, '<path>/value', '/ci_low', '/ci_high', '/n_finite'.",
        "tolerance": "values and interval bounds: 1e-9 absolute or relative; n_finite exact; lists, sets and top-k "
                     "names exact; top-k shares within 1e-9 position by position",
        "sources": {"A": "V\\A\\results.json", "B": "V\\B\\results.json",
                    "official": "SHAP\\out\\<p>\\lead_0\\compare\\ (mapping: V\\reconcile\\mapping.md)",
                    "official_derived": "keys no official file holds, rebuilt from official numbers with "
                                        "compare_shap.py's rules (a second check only)"},
        "status_codes": {"match": "equal within the tolerance", "diff": "both present, not equal",
                         "missing_in_first": "the first source of the pair lacks the key",
                         "missing_in_second": "the second source of the pair lacks the key",
                         "null_vs_absent": "one source has null, the other lacks the key (no number either side)",
                         "pairs": "AB = A vs B, AO = A vs official, BO = B vs official, AOd/BOd = against the "
                                  "official-derived value"},
        "key_counts": counts, "number_counts": nums,
        "n_mismatch_keys": len(per_key),
        "groups": [{"group": g, "cause": GROUPS[g][0], "kind": GROUPS[g][1], "affects_reported_numbers": GROUPS[g][2],
                    "n_keys": len(groups[g]), "diagnosis": GROUPS[g][3], "example_keys": groups[g][:6]}
                   for g in order],
        "columns": ["key", "group", "secondary_groups", "status", "A", "B", "official", "official_derived"],
    }
    path = os.path.join(R.RC, "mismatches.json")
    assert os.path.normpath(path).lower().startswith(os.path.normpath(R.RC).lower())
    byg = {g: [] for g in order}
    for x in per_key:
        byg[x["group"]].append(x)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        txt = json.dumps(head, indent=1, ensure_ascii=False, allow_nan=False)
        f.write(txt[:-2] + ",\n \"keys\": [\n")
        first = True
        for g in order:
            for x in byg[g]:
                st = " ".join("%s=%s" % kv for kv in sorted(x["status"].items()))
                rec = [x["key"], g, secondary(g, x["status"]), st, x["A"], x["B"], x["official"],
                       x["official_derived"]]
                f.write(("" if first else ",\n") + "  " + json.dumps(rec, ensure_ascii=False, allow_nan=False))
                first = False
        f.write("\n ],\n \"keys_without_a_number_anywhere\": {\n  \"what\": \"null in A and B, absent in the "
                "official files: no source holds a number, so these are not counted as mismatches\",\n  \"keys\": ")
        f.write(json.dumps(no_number_keys, ensure_ascii=False))
        f.write("\n }\n}\n")


if __name__ == "__main__":
    main()
