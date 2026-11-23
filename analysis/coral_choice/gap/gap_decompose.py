"""Analysis 3 (post-hoc, read-only): where the coral test MAE gap GLS vs unweighted sits, and whether the
decision surface (2013-2015) could have shown it. Reads the frozen run + the coral store; writes only here."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RUN = Path(r"D:/treeroute/runs/coral/headline/20261020_f3b8e3da")
STORE = Path(r"D:/treeroute/coral_build/coral_store/20261020_014201/lead_0.parquet")
OUT = Path(r"D:/treeroute/analysis/coral_choice/gap")

G_T, U_T = "arm__arcsine_corrector_gls", "arm__arcsine_corrector_unweighted"
G_S, U_S = "arcsine_corrector_gls@level=100.0,ratio=1.0", "arcsine_corrector_unweighted@level=100.0,ratio=1.0"
OFF = "arcsine_trees_off_unweighted"

store = pd.read_parquet(STORE, columns=["row_id", "programme", "target_date", "pct_bleached", "mark", "group"])
store["year"] = pd.to_datetime(store["target_date"]).dt.year
y_of = dict(zip(store.row_id, store.pct_bleached))
yr_of = dict(zip(store.row_id, store.year))
prog_of = dict(zip(store.row_id, store.programme))


def band(y):
    return np.select([y == 0, y < 10, y < 50], ["a:0", "b:(0,10)", "c:[10,50)"], "d:>=50")


def frame(df, g, u, label):
    out = pd.DataFrame({"row_id": df["unit"].values, "group": df["group"].values, "y": df["y"].values,
                        "gls": df[g].values, "unw": df[u].values})
    out["year"] = out.row_id.map(yr_of)
    out["programme"] = out.row_id.map(prog_of)
    assert out.year.notna().all() and out.programme.notna().all(), label
    assert np.allclose(out.y.values, out.row_id.map(y_of).values), label
    out["band"] = band(out.y.values)
    out["ae_g"] = (out.gls - out.y).abs()
    out["ae_u"] = (out.unw - out.y).abs()
    out["d"] = out.ae_g - out.ae_u          # >0 = GLS worse on this row
    out["pdiff"] = out.unw - out.gls        # >0 = unweighted predicts higher
    out["set"] = label
    return out


inner = pd.read_parquet(RUN / "inner_preds.parquet", columns=["unit", "group", "time", "y", G_S, U_S, OFF])
test = pd.read_parquet(RUN / "test_preds.parquet")
S = frame(inner, G_S, U_S, "surface")
T = frame(test, G_T, U_T, "test")
assert (T.programme.values == test.programme.values).all()


# pool composition: donor rows each row's router could draw on
def pool_stats(path, rows):
    p = pd.read_parquet(path)
    p = p.set_index("row_id").loc[rows]
    res = []
    for ids in p.pool_row_ids:
        ids = json.loads(ids)
        ys = np.array([y_of[i] for i in ids])
        yrs = np.array([yr_of[i] for i in ids])
        res.append((len(ids), ys.mean(), (ys >= 50).mean(), (ys == 0).mean(), yrs.max(), (yrs >= 2013).mean()))
    return pd.DataFrame(res, columns=["pool_n", "pool_ymean", "pool_sev_share", "pool_zero_share", "pool_maxyear",
                                      "pool_share_2013plus"], index=p.index)


for F, f in ((S, "pools_decision_surface.parquet"), (T, "pools_test_pass.parquet")):
    ps = pool_stats(RUN / f, F.row_id.values)
    for c in ps.columns:
        F[c] = ps[c].values
    F["pool_sev_q"] = pd.cut(F.pool_sev_share, [-1e-9, 0.02, 0.05, 0.10, 1.0],
                             labels=["<=2%", "(2,5]%", "(5,10]%", ">10%"])



def md(df, fmt=".3f"):
    df = df.reset_index() if not isinstance(df.index, pd.RangeIndex) else df
    cols = [str(c) for c in df.columns]
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in df.itertuples(index=False):
        out.append("| " + " | ".join(format(v, fmt) if isinstance(v, (float, np.floating)) else str(v) for v in r) + " |")
    return chr(10).join(out)

lines = []
P = lines.append


def table(F, key, title):
    n_all = len(F)
    tot = F.d.sum()
    g = F.groupby(key, observed=True).agg(n=("d", "size"), y_mean=("y", "mean"), mae_gls=("ae_g", "mean"),
                                          mae_unw=("ae_u", "mean"), pred_gls=("gls", "mean"),
                                          pred_unw=("unw", "mean"), d_sum=("d", "sum"))
    g["gap_contrib"] = g.d_sum / n_all
    g["share_of_gap"] = g.d_sum / tot
    g = g.drop(columns="d_sum")
    P(f"\n### {title}  (rows {n_all}; MAE gls {F.ae_g.mean():.4f}, unw {F.ae_u.mean():.4f}, "
      f"gap gls-unw {F.d.mean():+.4f})\n")
    P(g.pipe(md))
    return g


res = {}
for F in (T, S):
    nm = F.set.iloc[0]
    res[nm] = {}
    for key in ("year", "programme", "band", "pool_sev_q"):
        res[nm][key] = table(F, key, f"{nm}: by {key}")
    gg = table(F, "group", f"{nm}: by group (ecoregion)")
    res[nm]["group"] = gg

# focus shares
tot = T.d.sum()
m16, mMc, mSev = T.year == 2016, T.programme == "McClanahan", T.band == "d:>=50"
focus = {
    "test_gap": T.d.mean(), "surface_gap": S.d.mean(),
    "test_mae": (T.ae_g.mean(), T.ae_u.mean()), "surface_mae": (S.ae_g.mean(), S.ae_u.mean()),
    "share_2016": T.d[m16].sum() / tot, "share_McC": T.d[mMc].sum() / tot, "share_severe": T.d[mSev].sum() / tot,
    "share_McC_2016_severe": T.d[m16 & mMc & mSev].sum() / tot,
    "share_severe_not_McC": T.d[mSev & ~mMc].sum() / tot,
    "share_bleached_any": T.d[T.y > 0].sum() / tot, "share_zero": T.d[T.y == 0].sum() / tot,
    "n_severe_test": int(mSev.sum()), "n_severe_McC": int((mSev & mMc).sum()),
    "n_severe_surface": int((S.band == "d:>=50").sum()),
    "gap_without_McC": T.d[~mMc].mean(), "gap_without_severe": T.d[~mSev].mean(),
    "gap_without_2016": T.d[~m16].mean(),
}

# shift-share: gap = sum_b s_b g_b
def bandstats(F):
    s = F.band.value_counts(normalize=True).sort_index()
    gb = F.groupby("band").d.mean()
    return s, gb


sT, gT = bandstats(T)
sS, gS = bandstats(S)
comp = float(((sT - sS) * gS).sum())
within = float((sT * (gT - gS)).sum())
focus.update({"shiftshare_composition": comp, "shiftshare_within_band": within,
              "test_gap_if_surface_behaviour": float((sT * gS).sum())})

# severe surface rows: how did the arms do?
Ssev = S[S.band == "d:>=50"]
Tsev = T[T.band == "d:>=50"]
P("\n### Severe rows (y>=50) side by side\n")
sev = pd.DataFrame({
    "surface": [len(Ssev), Ssev.y.mean(), Ssev.gls.mean(), Ssev.unw.mean(), Ssev.ae_g.mean(), Ssev.ae_u.mean(),
                Ssev.pdiff.mean(), (Ssev.pdiff > 5).mean(), Ssev.pool_sev_share.mean()],
    "test": [len(Tsev), Tsev.y.mean(), Tsev.gls.mean(), Tsev.unw.mean(), Tsev.ae_g.mean(), Tsev.ae_u.mean(),
             Tsev.pdiff.mean(), (Tsev.pdiff > 5).mean(), Tsev.pool_sev_share.mean()]},
    index=["rows", "y mean", "pred gls", "pred unw", "MAE gls", "MAE unw", "unw-gls pred", "share unw>gls+5",
           "pool severe share"])
P(sev.pipe(md))
P("\nsurface severe rows by programme/year/group:\n")
P(Ssev.groupby(["year", "programme", "group"]).agg(n=("y", "size"), y=("y", "mean"), gls=("gls", "mean"),
                                                   unw=("unw", "mean"), mae_g=("ae_g", "mean"),
                                                   mae_u=("ae_u", "mean")).pipe(md, ".2f"))

# prediction divergence everywhere
P("\n### How far apart the two arms predict (|unw-gls|, mean) by band\n")
div = pd.DataFrame({"surface": S.groupby("band").pdiff.apply(lambda x: x.abs().mean()),
                    "test": T.groupby("band").pdiff.apply(lambda x: x.abs().mean()),
                    "surface signed": S.groupby("band").pdiff.mean(),
                    "test signed": T.groupby("band").pdiff.mean()})
P(div.pipe(md))
focus["mean_abs_pdiff"] = (S.pdiff.abs().mean(), T.pdiff.abs().mean())

# composition of the two sets
P("\n### Composition: surface vs test\n")
for key in ("programme", "year", "band"):
    c = pd.DataFrame({"surface_n": S[key].value_counts(), "test_n": T[key].value_counts()}).fillna(0)
    c["surface_share"] = c.surface_n / len(S)
    c["test_share"] = c.test_n / len(T)
    P(c.sort_index().pipe(md))
    P("")
P("pool composition (mean over rows):\n")
P(pd.DataFrame({k: F[["pool_n", "pool_ymean", "pool_sev_share", "pool_zero_share", "pool_maxyear",
                      "pool_share_2013plus"]].mean() for k, F in (("surface", S), ("test", T))}).pipe(md))
# McClanahan programme on test: is its group present in surface?
mcg = sorted(T[mMc].group.unique())
P("\nMcClanahan test groups: " + ", ".join(mcg))
P("those groups on the surface: " + json.dumps(S[S.group.isin(mcg)].groupby("group").size().to_dict()))
P("McClanahan rows on surface: %d" % int((S.programme == "McClanahan").sum()))

# test gap by pool severe-share quartile restricted to severe rows
P("\n### Test severe rows: gap by pool severe-share\n")
P(Tsev.groupby("pool_sev_q", observed=True).agg(n=("d", "size"), y=("y", "mean"), gls=("gls", "mean"),
                                                unw=("unw", "mean"), d=("d", "mean")).pipe(md))

S.to_parquet(OUT / "surface_rows.parquet")
T.to_parquet(OUT / "test_rows.parquet")
(OUT / "tables.md").write_text("\n".join(lines), encoding="utf-8")
json.dump({k: (list(v) if isinstance(v, tuple) else v) for k, v in focus.items()},
          open(OUT / "focus.json", "w"), indent=1, default=float)
print(json.dumps({k: (list(v) if isinstance(v, tuple) else v) for k, v in focus.items()}, indent=1, default=float))
