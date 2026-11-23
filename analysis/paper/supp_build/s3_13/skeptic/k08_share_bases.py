# Skeptic (version 2 check of C1): the two share bases, recomputed from the row-level SHAP values. Read-only; prints only.
#  - top-k (player) shares: importance.parquet share = I(j) / sum over J, I = region-weighted mean |phi| (PROTOCOL 8)
#  - family shares: families.parquet share = region-weighted mean |sum of the family's variable phi| / sum over the five
#    families (the basis the version-2 captions state), against the version-1 basis (sum of the variables' shares)
#  - panel g (fire, coral): shares on the rows with pre > 0
#  - B1 (pm25, ndvi, fire): A's family shares, own-history share, top 3 and top 10 against the B1 rows
import json, sys
import numpy as np
import pandas as pd
sys.stdout.reconfigure(encoding="utf-8")
SHAP = r"D:\treeroute\analysis\shap_v1"
A = json.load(open(SHAP + r"\verify_v1\A\results.json", encoding="utf-8"))
FAMS = ["own history", "global indices", "local drivers", "context and calendar", "seasonal normal"]


def imp(df, cols, weighted=True):
    """mean |phi| per column; region-weighted (each region weighs 1) or plain; a column the model lacks is 0"""
    a = df.reindex(columns=cols, fill_value=0.0).abs()
    if not weighted:
        return a.mean()
    a = a.assign(_g=df["group"].values)
    return a.groupby("_g").mean().mean()


def fam_attr(df, fam, vars_):
    out = {}
    for f in FAMS:
        vs = [v for v in vars_ if fam.get(v) == f]
        out[f] = df.reindex(columns=["phiv__" + v for v in vs], fill_value=0.0).sum(axis=1) if vs else pd.Series(0.0, index=df.index)
    return pd.DataFrame(out).assign(group=df["group"].values)


worst = {"imp_w": 0.0, "imp_plain": 0.0, "share": 0.0, "fam_new": 0.0, "fam_old": 0.0, "g": 0.0}
for p in ["pm25", "ndvi", "fire", "defo", "coral"]:
    C = SHAP + r"\out\%s\lead_0\compare" % p
    PL = json.load(open(C + r"\per_lead.json", encoding="utf-8"))
    IM = pd.read_parquet(C + r"\importance.parquet")
    FA = pd.read_parquet(C + r"\families.parquet")
    fam = PL["families"]
    for m in PL["models"]:
        R = pd.read_parquet(SHAP + r"\out\%s\lead_0\%s\rows.parquet" % (p, m))
        q = IM[(IM.level == "variable") & (IM.model == m)].set_index("player")
        vars_ = list(q.index)
        cols = ["phiv__" + v for v in vars_]
        Iw = imp(R, cols, True).values
        Ip = imp(R, cols, False).values
        d_w = float(np.max(np.abs(Iw - q.mean_abs.values)))
        d_p = float(np.max(np.abs(Ip - q.mean_abs.values)))
        act = q.active.values
        sh = Iw / Iw[act].sum()
        d_s = float(np.max(np.abs(sh[act] - q.share.values[act])))
        F = fam_attr(R, fam, vars_)
        Fw = F.drop(columns="group").abs().assign(_g=F["group"].values).groupby("_g").mean().mean()
        new = Fw / Fw.sum()
        old = q[q.active].assign(f=lambda d: d.index.map(fam)).groupby("f").share.sum()
        fa = FA[FA.model == m].set_index("family").share
        d_new = max(abs(float(new[f]) - float(fa[f])) for f in FAMS)
        d_old = max(abs(float(old.get(f, 0.0)) - float(fa[f])) for f in FAMS)
        for k, v in [("imp_w", d_w), ("imp_plain", d_p), ("share", d_s), ("fam_new", d_new)]:
            worst[k] = max(worst[k], v)
        print("%-5s %-19s I: region-weighted dev %.1e, plain-mean dev %.1e | share=I/sumJ dev %.1e | family share: v2 basis dev %.1e, v1 basis (sum of variable shares) dev %.3f | own history %.4f vs %.4f"
              % (p, m, d_w, d_p, d_s, d_new, d_old, float(fa["own history"]), float(old.get("own history", 0.0))))
    for m, o in PL.get("nonzero_forecast_rows", {}).items():
        R = pd.read_parquet(SHAP + r"\out\%s\lead_0\%s\rows.parquet" % (p, m))
        Z = R[R.pre > 0]
        vars_ = list(IM[(IM.level == "variable") & (IM.model == m)].player)
        Iz = imp(Z, ["phiv__" + v for v in vars_], True)
        Iz.index = vars_
        shz = Iz / Iz.sum()
        act = set(PL["variable"]["active"]) if isinstance(PL["variable"]["active"], list) else None
        dev = max(abs(float(shz[n]) - s) for n, s in o["top10"])
        top_ok = [n for n, _ in o["top10"]] == list(shz.sort_values(ascending=False).index[:10])
        Ip = imp(Z, ["phiv__" + v for v in vars_], False)
        Ip.index = vars_
        devp = max(abs(float(Ip[n] / Ip.sum()) - s) for n, s in o["top10"])
        worst["g"] = max(worst["g"], dev)
        print("   panel g %-5s %-15s rows pre>0: %d (stored %d) | top10 share dev, region-weighted over every variable %.1e (plain mean %.1e) | same top-10 order: %s"
              % (p, m, len(Z), o["rows"], dev, devp, top_ok))
print("worst:", {k: "%.1e" % v for k, v in worst.items()})

# Table 9 own-history shares are family shares
for p in ["pm25", "ndvi", "defo", "coral"]:
    C = SHAP + r"\out\%s\lead_0\compare" % p
    AW = json.load(open(C + r"\AW4_main_row.json", encoding="utf-8"))
    FA = pd.read_parquet(C + r"\families.parquet")
    t = float(FA[(FA.model == "treeroute") & (FA.family == "own history")].share.iloc[0])
    print("Table 9", p, "AW4 own_history_share_treeroute", AW["own_history_share_treeroute"]["value"], "families.parquet", t,
          "equal:", abs(AW["own_history_share_treeroute"]["value"] - t) < 1e-12)
FA = pd.read_parquet(SHAP + r"\out\fire\lead_0\compare\families.parquet")
t = float(FA[(FA.model == "treeroute") & (FA.family == "own history")].share.iloc[0])
print("Table 9 fire A own_history_share_treeroute", A["problems"]["fire"]["main_row"]["own_history_share_treeroute"]["value"], "families.parquet", t)

# B1
KEY = {"own history": "own_history", "global indices": "global_indices", "local drivers": "local_drivers",
       "context and calendar": "context_and_calendar", "seasonal normal": "seasonal_normal"}
for p in ["pm25", "ndvi", "fire"]:
    PL = json.load(open(SHAP + r"\out\%s\lead_0\compare\per_lead.json" % p, encoding="utf-8"))
    fam = PL["families"]
    B = A["b1"][p]
    M = pd.read_parquet(SHAP + r"\out\%s\lead_0\treeroute\rows.parquet" % p)
    R1 = pd.read_parquet(SHAP + r"\out\%s\lead_0\treeroute_B1\rows.parquet" % p)
    for L, pre in [("variable", "phiv__"), ("feature", "phi__")]:
        cm = [c for c in M.columns if c.startswith(pre)]
        c1 = [c for c in R1.columns if c.startswith(pre)]
        allc = sorted(set(cm) | set(c1))
        Im = imp(M.reindex(columns=allc + ["group"], fill_value=0.0), allc, True)
        I1 = imp(R1.reindex(columns=allc + ["group"], fill_value=0.0), allc, True)
        J = [c for c in allc if Im[c] / Im.sum() > 1e-12 or I1[c] / I1.sum() > 1e-12]
        s1 = I1[J] / I1[J].sum()
        s1.index = [c[len(pre):] for c in J]
        top = B[L]["top10"]
        dev = max(abs(float(s1[n]) - s) for n, s in top)
        order = [n for n, _ in top] == list(s1.sort_values(ascending=False).index[:10])
        msg = "B1 %-5s %-8s pair J %d (A n_J %s) | top10 share = I_B1/sum over pair's J: dev %.1e, same order %s" % (
            p, L, len(J), B[L]["pair_main_b1"]["n_J"]["value"], dev, order)
        if L == "variable":
            t3 = B["variable"]["top3"]
            dev3 = max(abs(float(s1[n]) - s) for n, s in t3)
            vars_ = [c[len(pre):] for c in c1]
            F = fam_attr(R1, fam, vars_)
            Fw = F.drop(columns="group").abs().assign(_g=F["group"].values).groupby("_g").mean().mean()
            new = Fw / Fw.sum()
            dfam = max(abs(float(new[f]) - B["variable"]["families"][KEY[f]]["value"]) for f in FAMS)
            sumvar = {f: float(sum(s1[v] for v in s1.index if fam.get(v) == f)) for f in FAMS}
            oh = B["variable"]["own_history_share"]["value"]
            msg += " | top3 dev %.1e | A family shares vs v2 basis dev %.1e | own-history share %.4f = family %.4f; sum of its variables' shares %.4f | seasonal normal family %.4f vs `normal` share %.4f" % (
                dev3, dfam, oh, B["variable"]["families"]["own_history"]["value"], sumvar["own history"],
                B["variable"]["families"]["seasonal_normal"]["value"], float(s1.get("normal", float("nan"))))
        print(msg)
