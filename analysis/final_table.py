# final_table.py -- READ-ONLY: the final rival table in one compact view (common + human deciding rows), from the joined
# RIVALS_TABLE.csv (D:/treeroute/rivals_table/20261025T162302876402Z). Writes engine/RIVALS_TABLE_FINAL.md.
import pandas as pd, numpy as np, sys
SRC = r"D:\treeroute\rivals_table\20261025T162302876402Z\RIVALS_TABLE.csv"
t = pd.read_csv(SRC)
SYM = {"BEATS": "WIN", "LOSES": "loss", "CANNOT TELL": "?", "EQUIVALENT": "=", "IDENTICAL": "same"}
HUM = {"crw_dhw": "NOAA heat-stress rule", "crw_outlook": "NOAA 4-month outlook", "vt0007_shipped": "VT0007 shipped",
       "vt0007_cal": "VT0007 calibrated", "vt0007_frozen2019": "VT0007 frozen-2019", "merra2_lag1": "MERRA-2 (lag 1)",
       "bardl_h1": "rain-lag regression (H1)", "kraft_lstm": "Kraft LSTM"}
COM = ["ridge", "rf", "lgbm", "lgbm_tweedie", "hgb_l1"]
PROB = [("coral", "Coral"), ("fire", "Fire"), ("pm25", "PM2.5"), ("defo", "Defo"), ("ndvi", "NDVI")]
def v(r):
    s = str(r["verdict"]); base = next((SYM[k] for k in SYM if s.startswith(k)), s)
    if "TIMID" in str(r.get("timid_win", "")) or str(r.get("timid_win")) in ("True", "yes"): base += " (timid)"
    if s.startswith("BEATS (NOAA's nowcast rule fed old heat)"): base = "WIN (vs rule fed old heat)"
    return base
def mae(x):
    x = float(x); return ("%.3f" % x) if x >= 1 else ("%.4f" % x) if x >= 0.01 else ("%.5f" % x)
lines = ["| Problem | Lead | Ours (MAE) | Common rivals (Ridge / RF / LightGBM / Tweedie / L1) | Human rivals (deciding rows) |", "|---|---|---|---|---|"]
for p, P in PROB:
    for L in sorted(t[t.problem == p].lead.unique()):
        blk = t[(t.problem == p) & (t.lead == L)]
        ours = blk[blk.rival_type == "ours"]
        o = mae(ours.iloc[0]["ours_mae_all_rows"] if "ours_mae_all_rows" in ours and pd.notna(ours.iloc[0]["ours_mae_all_rows"]) else ours.iloc[0]["rival_mae"]) if len(ours) else "-"
        com = blk[(blk.rival_type == "common") & (blk.contrast == "guarded_vs_headline")]
        def cv(r):
            x = com[com.rival == r].iloc[0]; s_ = v(x)
            return s_ + "*" if str(x.guard_passed) != "True" and not s_.startswith("same") else s_
        cs = " / ".join(cv(r) if (com.rival == r).any() else "-" for r in COM)
        hum = blk[(blk.rival_type == "human") & (blk.decides == True)]
        hs = "; ".join("%s %s vs ours %s: %s%s" % (HUM.get(r.rival, r.rival), mae(r.rival_mae), mae(r.ours_mae_same_rows), v(r),
                       "" if str(r.guard_passed) == "True" else " [rival's guard failed: its answer = the normal]") for _, r in hum.iterrows())
        if not hs:
            note = blk[(blk.rival_type == "human")]["flags"].dropna()
            hs = ("pending (Part B)" if note.astype(str).str.contains("pending").any() else
                  "no published forecast at this lead" if len(blk[blk.rival_type == "human"]) else "-")
        lines.append("| %s | %s | %s | %s | %s |" % (P, L, o, cs, hs))
hd = t[(t.rival_type == "human") & (t.decides == True)]
cnt_h = pd.Series([v(r).split(" ")[0] for _, r in hd.iterrows()]).value_counts().to_dict()
cc = t[(t.rival_type == "common") & (t.contrast == "guarded_vs_headline")]
cnt_c = pd.Series([v(r).split(" ")[0] for _, r in cc.iterrows()]).value_counts().to_dict()
md = ["# Final rival table (common + human), 2026-10-25 (notes corrected 2026-10-26)", "",
      "Source: %s (join of the five common boards, Parts 600/606/610/614/616, and the human boards, Parts 617/618; fire human rivals = Part B, pending)." % SRC,
      "Deciding contrast everywhere: the rival's guarded answer vs our headline answer. WIN = ours beats the rival; loss = the rival beats ours; ? = cannot tell; = equivalent; same = identical answers (both fell back to the normal). Lower MAE is better. Human rows listed are the deciding ones (tier P or L); advantaged (A), extension (X) and placebo rows are in the full table. Human cells compare on the rival's deciding rows ('ours' there is our MAE on those rows; coral: NOAA covers all 2,312 test rows and the deciding contrast uses 2,290 rows in 32 of 37 ecoregions with >= 10 rows). When a rival's guard failed, its deciding answer is the normal, so that WIN is ours beating the normal; the raw rival is in the full table. * on a common verdict = that rival's guard failed, so its deciding answer is the normal (a WIN* is ours beating the normal).", "",
      ] + lines + ["", "Common verdicts: " + ", ".join("%s %d" % kv for kv in sorted(cnt_c.items())),
                   "Human deciding verdicts: " + ", ".join("%s %d" % kv for kv in sorted(cnt_h.items())),
                   "Joint claim (pre-registered): defo lead 0 and lead 1 - ours beats VT0007 (every form): YES."]
open(r"C:\Users\<user>\Desktop\data set for reserch paper\engine\RIVALS_TABLE_FINAL.md", "w", encoding="utf-8").write("\n".join(md) + "\n")
sys.stdout.reconfigure(encoding="utf-8"); print("\n".join(md))
