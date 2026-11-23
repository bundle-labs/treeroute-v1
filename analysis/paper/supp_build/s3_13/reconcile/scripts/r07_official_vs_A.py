# r07: every main-comparison number that tables.md prints from the official comparison files, formatted again
# from implementer A's independent value in V\A\results.json; reports the largest difference of the two doubles
# and every cell whose print would differ (a number near a rounding boundary). Read-only.
import sys, json, math, itertools, collections
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import *  # noqa: E402,F401,F403
import pandas as pd  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
A = load_json(V / "A" / "results.json", strict=True)
SMAP = {"spearman": "spearman_J", "spearman_top20_union": "spearman_top20_union", "kendall_tau_b": "kendall_tau_b",
        "jaccard_top5": "jaccard_top5", "jaccard_top10": "jaccard_top10", "jaccard_top20": "jaccard_top20", "rbo_p0.9": "rbo_p090",
        "rbo_p0.95": "rbo_p095", "tvd": "tv_shares", "tvd_family": "tv_family_shares", "sign_agreement_top10": "sign_agreement"}
n, worst, fragile, missing = 0, 0.0, [], []


def cmpv(where, off, a, f):
    global n, worst
    if off is None and a is None:
        n += 1
        return
    if off is None or a is None:
        missing.append((where, off, a))
        return
    n += 1
    worst = max(worst, abs(off - a))
    if f(off) != f(a):
        fragile.append((where, off, a, f(off), f(a)))


for p in PROBS:
    pl = load_json(comp(p) / "per_lead.json")
    df = pd.read_parquet(comp(p) / "pairs.parquet")
    imp = pd.read_parquet(comp(p) / "importance.parquet")
    fam = pd.read_parquet(comp(p) / "families.parquet")
    AP = A["problems"][p]
    for r in df.itertuples():
        if r.statistic == "tvd_family" and r.level == "feature":
            continue
        key = r.model_a + "|" + r.model_b
        ao = AP["levels"][r.level]["pairs"][key][SMAP[r.statistic]]
        w = "%s %s %s %s" % (p, r.level, key, r.statistic)
        if r.statistic == "sign_agreement_top10":
            cmpv(w + " value", nan2none(r.value), ao["value"], NUM2)
            continue
        cmpv(w + " value", nan2none(r.value), ao["value"], NUM2)
        cmpv(w + " ci_low", nan2none(r.ci_low), ao["ci_low"], NUM2)
        cmpv(w + " ci_high", nan2none(r.ci_high), ao["ci_high"], NUM2)
        if r.finite_replicates != ao["n_finite"]:
            missing.append((w + " n_finite", r.finite_replicates, ao["n_finite"]))
    for L in ("variable", "feature"):
        pp = AP["levels"][L]["per_problem"]
        for k_pl, k_a in (("kendall_w_main_set", "kendall_w"), ("mean_pairwise_spearman_main_set", "mean_pairwise_spearman")):
            o = pl[L][k_pl]
            if pp[k_a] is None:
                cmpv("%s %s %s value" % (p, L, k_pl), nan2none(o["value"]), None, NUM2)
                continue
            cmpv("%s %s %s value" % (p, L, k_pl), nan2none(o["value"]), pp[k_a]["value"], NUM2)
            if p != "fire":
                cmpv("%s %s %s ci_low" % (p, L, k_pl), o["ci"][0], pp[k_a]["ci_low"], NUM2)
                cmpv("%s %s %s ci_high" % (p, L, k_pl), o["ci"][1], pp[k_a]["ci_high"], NUM2)
        for m, v in pl[L]["stability_under_region_resampling"].items():
            cmpv("%s %s stability %s" % (p, L, m), v, pp["stability"][m]["value"], NUM2)
        for m in pl["models"]:
            am = AP["levels"][L]["models"][m]
            sub = imp[(imp.level == L) & (imp.model == m) & (imp.active)]
            rk = sorted(((-x.mean_abs, x.player, x.share) for x in sub.itertuples()), key=lambda t: (t[0], t[1]))[:10]
            at = am["top10"]
            if [x[1] for x in rk] != [x[0] for x in at]:
                missing.append(("%s %s %s top-10 order" % (p, L, m), [x[1] for x in rk], [x[0] for x in at]))
            for (_, name, sh), (aname, ash) in zip(rk, at):
                cmpv("%s %s %s share %s" % (p, L, m, name), sh, ash, PCT1)
            if am["n_nonzero"]["value"] != pl[L]["nonzero_players"][m]:
                missing.append(("%s %s %s nonzero" % (p, L, m), pl[L]["nonzero_players"][m], am["n_nonzero"]["value"]))
    for m in pl["models"]:
        fs = AP["levels"]["variable"]["models"][m]["family_shares"]
        for f in FAMS:
            off = fam[(fam.model == m) & (fam.family == f)].iloc[0]["share"].item()
            ao = fs[f.replace(" ", "_")]
            av = ao["value"] if isinstance(ao, dict) else ao
            cmpv("%s family %s %s" % (p, m, f), off, av, PCT1)
    nz = pl["nonzero_forecast_rows"]
    for m, o in nz.items():
        an = AP["nonzero_forecast"]["models"][m]
        at = an["top10"] if isinstance(an, dict) and "top10" in an else None
        if at is None:
            missing.append(("%s nonzero_forecast %s structure" % (p, m), list(an.keys()) if isinstance(an, dict) else an))
            continue
        for (nm, sh), (anm, ash) in zip(o["top10"], at):
            if nm != anm:
                missing.append(("%s nzf %s name" % (p, m), nm, anm))
            cmpv("%s nzf %s %s" % (p, m, nm), sh, ash, PCT1)
        ar = an.get("rows_used")
        if ar != o["rows"]:
            missing.append(("%s nzf %s rows" % (p, m), o["rows"], ar))
    if p == "fire":
        continue
    aw = load_json(comp(p) / "AW4_main_row.json")
    mr = AP["main_row"]
    cmpv(p + " main W", aw["kendall_w"]["value"], mr["kendall_w"]["value"], NUM2)
    cmpv(p + " main W lo", aw["kendall_w"]["ci"][0], mr["kendall_w"]["ci_low"], NUM2)
    cmpv(p + " main W hi", aw["kendall_w"]["ci"][1], mr["kendall_w"]["ci_high"], NUM2)
    md = aw["treeroute_vs_same_link_rivals_median_spearman_top20_union"]
    cmpv(p + " median", md["value"], mr["spearman_top20_union_median"]["value"], NUM2)
    cmpv(p + " median lo", md["ci"][0], mr["spearman_top20_union_median"]["ci_low"], NUM2)
    cmpv(p + " median hi", md["ci"][1], mr["spearman_top20_union_median"]["ci_high"], NUM2)
    cmpv(p + " range min", md["range"][0], mr["spearman_top20_union_min"]["value"], NUM2)
    cmpv(p + " range max", md["range"][1], mr["spearman_top20_union_max"]["value"], NUM2)
    rb = aw["rbo_vs_consensus_p0.9"]
    cmpv(p + " rbo", rb["value"], mr["rbo_p090_vs_consensus"]["value"], NUM2)
    cmpv(p + " rbo lo", rb["ci"][0], mr["rbo_p090_vs_consensus"]["ci_low"], NUM2)
    cmpv(p + " rbo hi", rb["ci"][1], mr["rbo_p090_vs_consensus"]["ci_high"], NUM2)
    for k in ("own_history_share_treeroute", "own_history_share_median_rival"):
        if mr[k] is None:
            print(p, k, "is null in A; AW4 holds", aw[k], "; A's reason:", mr.get(k + "_why"))
            missing.append((p + " " + k, aw[k], None))
            continue
        cmpv(p + " " + k, aw[k]["value"], mr[k]["value"], NUM2)
        cmpv(p + " " + k + " lo", aw[k]["ci"][0], mr[k]["ci_low"], NUM2)
        cmpv(p + " " + k + " hi", aw[k]["ci"][1], mr[k]["ci_high"], NUM2)
    if aw["treeroute_top3"] != [x[0] for x in mr["treeroute_top3"]] or aw["consensus_top3"] != [x[0] for x in mr["consensus_top3"]]:
        missing.append((p + " top3 names", aw["treeroute_top3"], aw["consensus_top3"], mr["treeroute_top3"], mr["consensus_top3"]))
    for r_, v in mr["spearman_top20_union_per_rival"].items():
        v = v["value"] if isinstance(v, dict) else v
        a, b = sorted([r_, "treeroute"])
        off = df[(df.level == "variable") & (df.model_a == a) & (df.model_b == b) & (df.statistic == "spearman_top20_union")].iloc[0]["value"].item()
        cmpv(p + " per-rival spearman " + r_, off, v, NUM2)
    for r_, v in (mr["own_history_share_per_rival"] or {}).items():
        v = v["value"] if isinstance(v, dict) else v
        if v is None:
            missing.append((p + " per-rival own history null in A " + r_, None))
            continue
        off = fam[(fam.model == r_) & (fam.family == "own history")].iloc[0]["share"].item()
        cmpv(p + " per-rival own history " + r_, off, v, NUM2)
    if mr["median_rival_name"] is not None:
        print(p, "A's median rival:", mr["median_rival_name"])
print("official numbers re-formatted from A's values:", n, "largest |official - A|:", worst)
print("cells whose print would differ:", len(fragile))
for f in fragile:
    print("  ", f)
print("structure or count differences:", len(missing))
for m in missing[:30]:
    print("  ", m)
