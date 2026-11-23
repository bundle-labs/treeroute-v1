# common_table.py -- READ-ONLY: one table of the five finished common-rival boards (deciding contrast: the rival's
# guarded answer vs our headline answer). Writes engine/RIVALS_TABLE_COMMON.md and prints a compact version.
import csv, os, glob
B = {"Coral (% bleached)": r"D:\treeroute\rivals\coral\20261020_f3b8e3da", "Fire (burned fraction)": r"D:\treeroute\rivals\fire\20261017_869d1f38",
     "PM2.5 (ug/m3)": r"D:\treeroute\rivals\pm25\20261007_74e67609", "Defo (loss fraction)": r"D:\treeroute\rivals\defo\20261017_d71c61f4",
     "NDVI": r"D:\treeroute\rivals\ndvi\20261016_d1de3158"}
SYM = {"BEATS": "WIN", "LOSES": "loss", "CANNOT TELL": "?", "EQUIVALENT": "=", "IDENTICAL": "same"}
RIV = ["ridge", "rf", "lgbm", "lgbm_tweedie", "hgb_l1"]
NAME = {"ridge": "Ridge", "rf": "Random Forest", "lgbm": "LightGBM", "lgbm_tweedie": "LightGBM-Tweedie", "hgb_l1": "L1-boosting"}
def fmt(v):
    v = float(v)
    return ("%.3f" % v) if v >= 1 else ("%.4f" % v) if v >= 0.01 else ("%.5f" % v)
rows, tally = [], {}
for prob, d in B.items():
    for f in sorted(glob.glob(os.path.join(d, "board_lead_*.csv")), key=lambda p: int(p.rsplit("_", 1)[1].split(".")[0])):
        L = int(f.rsplit("_", 1)[1].split(".")[0])
        rs = [r for r in csv.DictReader(open(f)) if r["contrast"] == "guarded_vs_headline"]
        if not rs: continue
        ours = fmt(rs[0]["ours_mae"]); oc2 = float(rs[0]["ours_corr2"]) if rs[0]["ours_corr2"] not in ("", "nan") else float("nan")
        cell = {}
        best_c2 = max([float(r["rival_corr2"]) for r in rs if r["rival_corr2"] not in ("", "nan")] + [oc2])
        for r in rs:
            v = SYM.get(r["ours_beats_rival"], r["ours_beats_rival"])
            t = " TIMID" if r["timid_win"] in ("True", "yes", "1") else ""
            cell[r["learner"]] = "%s %s%s" % (fmt(r["rival_mae"]), v, t)
            tally[v] = tally.get(v, 0) + 1
        rows.append((prob, L, ours, oc2, oc2 >= best_c2 - 1e-12, cell))
hdr = "| Problem | Lead | Ours (MAE) | " + " | ".join(NAME[x] for x in RIV) + " | Ours best corr2? |"
md = ["# Common rivals: all five problems (deciding contrast: rival's guarded answer vs our headline answer)", "",
      "Cell = rival MAE + verdict for OURS: WIN = we beat it, loss = it beats us, ? = cannot tell, = equivalent, same = identical answers (both fell back to the normal). TIMID = the rival's win comes from cautious near-zero predictions. Lower MAE is better. Built 2026-10-25 from the five boards (Parts 600, 606, 610, 614, 616).", "",
      hdr, "|" + "---|" * (len(RIV) + 4)]
for prob, L, ours, oc2, best, cell in rows:
    md.append("| %s | %s | %s | %s | %s |" % (prob, L, ours, " | ".join(cell.get(x, "-") for x in RIV), "yes" if best else "no"))
md += ["", "Verdict count over all cells: " + ", ".join("%s %d" % (k, v) for k, v in sorted(tally.items()))]
open(r"C:\Users\<user>\Desktop\data set for reserch paper\engine\RIVALS_TABLE_COMMON.md", "w", encoding="utf-8").write("\n".join(md) + "\n")
print("\n".join(md))
