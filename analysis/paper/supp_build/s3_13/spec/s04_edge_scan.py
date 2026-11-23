"""Spec writer's helper (read-only): facts the table spec relies on, and the formatting edge cases in the data.

Usage: py -3.9 -I -B s04_edge_scan.py
Prints findings only (no table): which pair statistics exist per level, their finite counts, undefined values,
signs_compared, the families with no variable, whether sorting importance.parquet by (-mean_abs, player) over the
active players reproduces A's top-10 and the official top-3, and every double that the spec's formats would print
as an exact decimal tie or as a negative number that rounds to zero. Opens SHAP\\out\\<p>\\lead_0\\compare\\ files,
V\\A\\results.json and V\\_lead\\outputs\\bardl_maxima.txt. Writes nothing.
"""
import json
import math
import os
import re
from decimal import Decimal, ROUND_HALF_EVEN, ROUND_HALF_UP

import pandas as pd

SHAP = r"D:\treeroute\analysis\shap_v1"
RES = os.path.join(SHAP, "verify_v1", "A", "results.json")
PROBLEMS = ["pm25", "ndvi", "fire", "defo", "coral"]


def tie_or_negzero(x, places, scale=1.0):
    """Return a short flag when format(scale*x, '.{places}f') sits on an exact decimal tie or is a negative zero."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return None
    y = scale * float(x)
    q = Decimal(1).scaleb(-places)
    d = Decimal(y)
    flags = []
    if d.quantize(q, ROUND_HALF_EVEN) != d.quantize(q, ROUND_HALF_UP):
        flags.append("TIE(%r -> %s)" % (y, format(y, ".%df" % places)))
    s = format(y, ".%df" % places)
    if s.startswith("-") and set(s[1:]) <= set("0."):
        flags.append("NEGZERO(%r -> %s)" % (y, s))
    return ", ".join(flags) if flags else None


def main():
    with open(RES, encoding="utf-8") as f:
        A = json.load(f)
    findings = []
    for p in PROBLEMS:
        cdir = os.path.join(SHAP, "out", p, "lead_0", "compare")
        with open(os.path.join(cdir, "per_lead.json"), encoding="utf-8") as f:
            PL = json.load(f)
        with open(os.path.join(cdir, "AW4_main_row.json"), encoding="utf-8") as f:
            MR = json.load(f)
        pairs = pd.read_parquet(os.path.join(cdir, "pairs.parquet"))
        imp = pd.read_parquet(os.path.join(cdir, "importance.parquet"))
        fam = pd.read_parquet(os.path.join(cdir, "families.parquet"))
        print("=" * 90)
        print(p, "| models", PL["models"], "| main", PL["main_set"], "| declined", PL["declined_by_guard"])
        # statistics per level
        for lev in ("variable", "feature"):
            sub = pairs[pairs.level == lev]
            stats = sorted(sub.statistic.unique().tolist())
            print("  %s: J=%d players=%d stats=%s" % (lev, PL[lev]["active"], PL[lev]["players"], stats))
            nf = sub[sub.finite_replicates != PL["draws"]]
            for _, r in nf.iterrows():
                print("    finite<draws: %s|%s %s value=%r ci=(%r,%r) nf=%d signs=%r" % (
                    r.model_a, r.model_b, r.statistic, r.value, r.ci_low, r.ci_high, r.finite_replicates,
                    r.signs_compared))
            nan = sub[sub.value.isna()]
            for _, r in nan.iterrows():
                print("    value NaN: %s|%s %s nf=%d signs=%r" % (r.model_a, r.model_b, r.statistic,
                                                                  r.finite_replicates, r.signs_compared))
            sc = sub[sub.statistic != "sign_agreement_top10"].signs_compared.dropna()
            if len(sc):
                print("    signs_compared outside sign rows:", len(sc))
            # pair order in the file
            order = []
            for _, r in sub.iterrows():
                k = (r.model_a, r.model_b)
                if k not in order:
                    order.append(k)
            print("    pair order in file:", ["%s|%s" % k for k in order][:4], "...", len(order), "pairs;",
                  "sorted" if order == sorted(order) else "NOT sorted")
            # A vs official sign agreement
            for (a, b) in order:
                key = "%s|%s" % (a, b)
                ra = A["problems"][p]["levels"][lev]["pairs"][key]
                s = sub[(sub.model_a == a) & (sub.model_b == b) & (sub.statistic == "sign_agreement_top10")].iloc[0]
                av, ov = ra["sign_agreement"]["value"], s.value
                same = (av is None and math.isnan(ov)) or (av is not None and not math.isnan(ov) and abs(av - ov) <= 1e-12)
                nd = ra["sign_n_determined"]["value"]
                if not same or nd != s.signs_compared:
                    print("    SIGN MISMATCH", key, av, ov, nd, s.signs_compared)
                for part in ("ci_low", "ci_high"):
                    fl = tie_or_negzero(ra["sign_agreement"][part], 2)
                    if fl:
                        findings.append("%s %s %s sign_agreement %s: %s" % (p, lev, key, part, fl))
            # edge scan of pair values at 2 decimals
            for _, r in sub.iterrows():
                for col in ("value", "ci_low", "ci_high"):
                    fl = tie_or_negzero(getattr(r, col), 2)
                    if fl:
                        findings.append("%s %s %s|%s %s %s: %s" % (p, lev, r.model_a, r.model_b, r.statistic, col, fl))
            # per-level W, mean spearman, stability
            for k in ("kendall_w_main_set", "mean_pairwise_spearman_main_set"):
                o = PL[lev][k]
                for x in [o["value"]] + list(o["ci"]):
                    fl = tie_or_negzero(x, 2)
                    if fl:
                        findings.append("%s %s %s: %s" % (p, lev, k, fl))
            for m, x in PL[lev]["stability_under_region_resampling"].items():
                fl = tie_or_negzero(x, 2)
                if fl:
                    findings.append("%s %s stability %s: %s" % (p, lev, m, fl))
            # top-10 order check against A, and share edge cases in percent
            for m in PL["models"]:
                s = imp[(imp.level == lev) & (imp.model == m) & (imp.active)]
                s = s.assign(neg=-s.mean_abs).sort_values(["neg", "player"], kind="mergesort")
                top = s.head(10)
                mine = top.player.tolist()
                theirs = [t[0] for t in A["problems"][p]["levels"][lev]["models"][m]["top10"]]
                if mine != theirs:
                    print("    TOP10 ORDER DIFFERS", lev, m, mine, theirs)
                ties = s[s.duplicated("mean_abs", keep=False) & (s.mean_abs > 0)]
                if len(ties):
                    print("    tied nonzero mean_abs", lev, m, ties.player.tolist()[:6])
                for _, r in top.iterrows():
                    fl = tie_or_negzero(r.share, 1, 100.0)
                    if fl:
                        findings.append("%s %s top10 %s %s: %s" % (p, lev, m, r.player, fl))
                if lev == "variable" and m == "treeroute" and "treeroute_top3" in MR:
                    if mine[:3] != MR["treeroute_top3"]:
                        print("    TOP3 differs from AW4_main_row", mine[:3], MR["treeroute_top3"])
        # families
        famap = PL["families"]
        counts = {}
        for v, fname in famap.items():
            counts[fname] = counts.get(fname, 0) + 1
        allf = ["own history", "global indices", "local drivers", "context and calendar", "seasonal normal"]
        print("  family variable counts:", {f: counts.get(f, 0) for f in allf})
        print("  families.parquet family order per model:", fam[fam.model == fam.model.iloc[0]].family.tolist())
        for _, r in fam.iterrows():
            fl = tie_or_negzero(r.share, 1, 100.0)
            if fl:
                findings.append("%s family %s %s: %s" % (p, r.model, r.family, fl))
        # nonzero forecast
        for m, o in PL.get("nonzero_forecast_rows", {}).items():
            for name, sh in o["top10"]:
                fl = tie_or_negzero(sh, 1, 100.0)
                if fl:
                    findings.append("%s nonzero %s %s: %s" % (p, m, name, fl))
        # main row
        for k in ("kendall_w", "rbo_vs_consensus_p0.9", "own_history_share_treeroute", "own_history_share_median_rival",
                  "treeroute_vs_same_link_rivals_median_spearman_top20_union"):
            if k in MR:
                o = MR[k]
                xs = [o["value"], o["ci"][0], o["ci"][1]] + list(o.get("range", []))
                for x in xs:
                    fl = tie_or_negzero(x, 2)
                    if fl:
                        findings.append("%s main_row %s: %s" % (p, k, fl))
        print("  AW4 keys:", sorted(MR.keys()))
    # B1
    for p in ("pm25", "ndvi", "fire"):
        B = A["b1"][p]
        for lev in ("variable", "feature"):
            pr = B[lev]["pair_main_b1"]
            for k, o in pr.items():
                if isinstance(o, dict) and "value" in o and "ci_low" in o:
                    for part in ("value", "ci_low", "ci_high"):
                        fl = tie_or_negzero(o[part], 2)
                        if fl:
                            findings.append("b1 %s %s %s %s: %s" % (p, lev, k, part, fl))
                    if o.get("n_finite") not in (None, 2000):
                        print("  b1 finite<2000", p, lev, k, o.get("n_finite"))
            for name, sh in B[lev]["top10"]:
                fl = tie_or_negzero(sh, 1, 100.0)
                if fl:
                    findings.append("b1 %s %s top10 %s: %s" % (p, lev, name, fl))
        for fk, o in B["variable"]["families"].items():
            if fk == "extra":
                continue
            for part in ("value", "ci_low", "ci_high"):
                fl = tie_or_negzero(o[part], 1, 100.0)
                if fl:
                    findings.append("b1 %s family %s %s: %s" % (p, fk, part, fl))
        o = B["variable"]["own_history_share"]
        for part in ("value", "ci_low", "ci_high"):
            fl = tie_or_negzero(o[part], 2)
            if fl:
                findings.append("b1 %s own_history_share %s: %s" % (p, part, fl))
    # fire main row from A
    o = A["problems"]["fire"]["main_row"]["own_history_share_treeroute"]
    for part in ("value", "ci_low", "ci_high"):
        fl = tie_or_negzero(o[part], 2)
        if fl:
            findings.append("fire A main_row own_history %s: %s" % (part, fl))
    # bardl maxima
    with open(os.path.join(SHAP, "verify_v1", "_lead", "outputs", "bardl_maxima.txt"), encoding="utf-8") as f:
        txt = f.read()
    for m in re.finditer(r"^\s+(\S+)\s+spread ([0-9.]+) -> .* at (\S+); values (.+)$", txt, re.M):
        print("  maxima:", m.group(1), m.group(2), m.group(3), m.group(4))
    print("=" * 90)
    print("EDGE CASES (%d):" % len(findings))
    for x in findings:
        print("  " + x)


if __name__ == "__main__":
    main()
