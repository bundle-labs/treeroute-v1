# Skeptic (version 3 check, item 2a): J, the active set of each level, recomputed from every model's rows.parquet.
# PROTOCOL 8 (L494, L496): J = the players to which some model gives more than 1e-12 of its total mean |phi|, with
# I_m(j) the REGION-WEIGHTED mean |phi_ij| (each region weighs 1). Version 3's S3.19 caption states the weighting.
# Per problem and level: J from the region-weighted means and J from plain means over the 1,000 rows, against
# importance.parquet's `active` and per_lead.json's counts and structural-zero list; whether every player outside J is
# exactly 0 in every model; the margin to the 1e-12 threshold; and the stored mean_abs against the region-weighted mean
# at both levels. Read-only; prints only.
import json, sys
import numpy as np
import pandas as pd
sys.stdout.reconfigure(encoding="utf-8")
SHAP = r"D:\treeroute\analysis\shap_v1"
THR = 1e-12
bad = 0
for p in ["pm25", "ndvi", "fire", "defo", "coral"]:
    C = SHAP + r"\out\%s\lead_0\compare" % p
    PL = json.load(open(C + r"\per_lead.json", encoding="utf-8"))
    IM = pd.read_parquet(C + r"\importance.parquet")
    R = {m: pd.read_parquet(SHAP + r"\out\%s\lead_0\%s\rows.parquet" % (p, m)) for m in PL["models"]}
    for L, pre in [("variable", "phiv__"), ("feature", "phi__")]:
        q = IM[IM.level == L]
        players = sorted(set(q.player))
        J_im = set(q[q.active].player)
        act_per_model = {m: set(q[(q.model == m) & q.active].player) for m in PL["models"]}
        same_active = all(v == J_im for v in act_per_model.values())
        sz = list(PL[L]["structural_zero"])
        Jw, Jp, max_out, dev_w, dev_p = set(), set(), 0.0, 0.0, 0.0
        smax_w = {}
        notin = []
        for m, df in R.items():
            cols = [c for c in df.columns if c.startswith(pre)]
            names = [c[len(pre):] for c in cols]
            notin += [n for n in names if n not in players]
            A = df[cols].abs()
            A.columns = names
            Iw = A.groupby(df["group"].values).mean().mean()
            Ip = A.mean()
            sw, sp = Iw / Iw.sum(), Ip / Ip.sum()
            Jw |= set(sw.index[sw.values > THR])
            Jp |= set(sp.index[sp.values > THR])
            for n, v in sw.items():
                smax_w[n] = max(smax_w.get(n, 0.0), float(v))
            qm = q[q.model == m].set_index("player").mean_abs
            common = [n for n in names if n in qm.index]
            dev_w = max(dev_w, float(np.max(np.abs(Iw[common].values - qm[common].values))))
            dev_p = max(dev_p, float(np.max(np.abs(Ip[common].values - qm[common].values))))
        outside = [n for n in players if n not in J_im]
        for m, df in R.items():
            cols = [pre + n for n in outside if pre + n in df.columns]
            if cols:
                max_out = max(max_out, float(df[cols].abs().values.max()))
        inJ_min = min(smax_w.get(n, 0.0) for n in J_im)
        ok = (Jw == J_im and len(J_im) == PL[L]["active"] and len(players) == PL[L]["players"]
              and set(sz) == set(players) - J_im and len(sz) == len(set(sz)) and same_active and not notin)
        bad += not ok
        print("%-5s %-8s players %d (PL %s) | J: importance.active %d (PL active %s; same in every model %s) | "
              "J region-weighted == active: %s (|Jw| %d) | J plain mean == active: %s (|Jp| %d) | "
              "structural zeros == players - J: %s (%d) | largest |phi| outside J, any model, any row: %r | "
              "smallest top share in J (region-weighted) %.3e | stored mean_abs vs region-weighted: dev %.1e, vs plain: dev %.1e%s"
              % (p, L, len(players), PL[L]["players"], len(J_im), PL[L]["active"], same_active, Jw == J_im, len(Jw),
                 Jp == J_im, len(Jp), set(sz) == set(players) - J_im, len(sz), max_out, inJ_min, dev_w, dev_p,
                 (" | players not in importance.parquet: %s" % sorted(set(notin))[:5]) if notin else ""))
        if Jw != J_im:
            print("    in Jw not in J:", sorted(Jw - J_im)[:10], "| in J not in Jw:", sorted(J_im - Jw)[:10])
        if Jp != J_im:
            print("    in Jp not in J:", sorted(Jp - J_im)[:10], "| in J not in Jp:", sorted(J_im - Jp)[:10])
print("problem-levels failing:", bad)
