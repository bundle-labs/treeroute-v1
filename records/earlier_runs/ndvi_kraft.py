"""KRAFT 2019 AS A SECOND LEAK-FREE RIVAL: a GLOBAL LSTM over climate, against our transfer model.

Kraft et al., "Identifying Dynamic Memory Effects on Vegetation State Using Recurrent Neural
Networks", Frontiers in Big Data 2:31, 2019. A global LSTM fitted for NDVI from climate time series
plus static soil and land-cover variables.

WHY A SECOND RIVAL, AND WHY THIS ONE. McPhillips 2026 (ndvi_mcphillips.py) is a LOCAL per-cell
Gaussian process. Beating one model class proves little -- a reviewer says "you only beat local
models". Kraft is the opposite class: ONE GLOBAL DEEP SEQUENCE MODEL, pooled across space, with
recurrent memory over the climate history. Beating a local GP and a global LSTM is a materially
harder thing to dismiss than beating either alone.

THE ONE CHANGE WE MAKE, AND WHY IT IS REQUIRED RATHER THAN CONVENIENT. Kraft's predictors include
LAND COVER. Every optical land-cover product is a banned proxy in this project, because NDVI is an
input to the classifiers that produce them -- using land cover to predict NDVI leaks the target
through the label. We therefore drop it and keep climate + soil + terrain. This HANDICAPS the rival
relative to its published form, and the report must say so; it is the only way to put it on the
same footing as a model forbidden every vegetation proxy.

WHAT IS AND IS NOT LEAKED. No NDVI, no EVI, no LST, no albedo, no GPP, no land cover, at any lag.
The recurrent memory runs over CLIMATE, not over past vegetation -- which is precisely the
distinction that disqualified BARDL (3-month VCI lags) and the 2024 global DNN (NDVI among its
inputs). Trained on DONOR REGIONS ONLY, so no test region is ever seen, exactly as our donor
forests are.

PHASE TWO, THE SAME THREE VERSIONS AS THE McPHILLIPS RIVAL. A sequence model asked for month t
needs the twelve climate months ending at t, none of which is known a year ahead:

    clim    each step replaced by that cell's calibration climatology for that calendar month
    lag12   the whole window shifted back twelve months -- observed, and in hand at issue time
    ORACLE  the true window. Not a forecast; a labelled ceiling, and the gap to the honest arms
            is the cost of not being able to forecast climate.

    py -3.9 -u ndvi_kraft.py --step=train      # build donor sequences and fit the LSTM
    py -3.9 -u ndvi_kraft.py --step=predict    # 44 held-out regions, three phase-2 variants
    py -3.9 -u ndvi_kraft.py --step=score      # both rivals against ours, information-matched
"""
import os
import sys
import gc
import time
import glob
import warnings

warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

ARG = {a.split("=")[0]: a.split("=")[1] for a in sys.argv[1:] if "=" in a}
STEP = ARG.get("--step", "train")
PANEL = ARG.get("--panel", r"D:\monthly_panel")
OURS = ARG.get("--ours", r"D:\run89full\conformal_fc12")
NOWC = ARG.get("--nowcast", r"D:\run89full\conformal")
MCP = ARG.get("--mcp", r"D:\run89full\mcphillips")
OUT = ARG.get("--out", r"D:\run89full\kraft")
SPLIT = r"D:\run89full\ndvi_split.txt"

SEQ = int(ARG.get("--seq", 12))                  # months of climate history per sample
DONCELLS = int(ARG.get("--doncells", 60))        # cells sampled per donor region
MAXSEQ = int(ARG.get("--maxseq", 1_500_000))     # hard cap on training sequences
EPOCHS = int(ARG.get("--epochs", 8))
BATCH = int(ARG.get("--batch", 4096))
HID = int(ARG.get("--hid", 64))
MINFREE = float(ARG.get("--minfree", 2.5))
SEED = int(ARG.get("--seed", 0))

DYN = ["V01_mean_temp_C", "V02_total_precip_mm", "V05_mean_vpd_kPa",
       "V30_soil_moisture_pct", "solar_radiation_Wm2", "V09_mean_wind_ms"]
STAT = ["soil_organic_carbon_gkg", "soil_ph", "sand_pct", "clay_pct",
        "awc_cm3cm3", "V25_elevation_m"]
NDVI = "V11_mean_ndvi"
KEEP = ["cell_id", "year", "month", "lat", NDVI] + DYN + STAT


def log(m):
    print("[%s] %s" % (time.strftime("%H:%M:%S"), m), flush=True)


def guard(where):
    try:
        import psutil
        free = psutil.virtual_memory().available / 2 ** 30
    except Exception:
        return
    if free < MINFREE:
        raise MemoryError("ABORT at %.1f GB free (limit %.1f) during %s -- refusing to page onto "
                          "the HDD. Lower --doncells or --maxseq and re-run." % (free, MINFREE, where))


def regions():
    txt = open(SPLIT).read().split()
    d = txt[txt.index("donors") + 1:txt.index("tests")]
    t = txt[txt.index("tests") + 1:]
    return d, t


def load_cells(region, cells, y0, y1):
    frames = []
    for yr in range(y0, y1 + 1):
        f = os.path.join(PANEL, "%s_monthly_%d.parquet" % (region, yr))
        if not os.path.exists(f):
            continue
        try:
            # PUSH THE CELL FILTER INTO THE READ. Reading the whole file and then subsetting
            # materialises every cell in the region first -- 321,540 rows x 17 columns for a big
            # region, twenty-two times over -- and that, not the sequence buffers, is what tripped
            # the memory guard twice. A predicate lets pyarrow skip row groups entirely.
            if cells is not None:
                d = pd.read_parquet(f, columns=KEEP,
                                    filters=[("cell_id", "in", list(cells))])
            else:
                d = pd.read_parquet(f, columns=KEEP)
        except Exception:
            try:
                d = pd.read_parquet(f, columns=KEEP)
                if cells is not None:
                    d = d[d.cell_id.isin(cells)]
            except Exception:
                continue
        if len(d):
            frames.append(d)
        del d
    if not frames:
        return None
    X = pd.concat(frames, ignore_index=True)
    del frames
    gc.collect()
    return X.sort_values(["cell_id", "year", "month"]).reset_index(drop=True)


def windows(A, seq):
    """(n, f) -> (n-seq+1, seq, f) sliding windows, no copy until asked."""
    from numpy.lib.stride_tricks import sliding_window_view
    return np.ascontiguousarray(sliding_window_view(A, seq, axis=0).transpose(0, 2, 1))


def cell_sequences(d, seq, want_clim_from=None):
    """Build (samples, seq, |DYN|) plus statics, target and the month index, for ONE cell.

    Returns None if the cell has fewer than seq+1 contiguous months. Contiguity is checked on the
    month index, not on row position, so a gap in the panel cannot silently produce a window that
    spans it.
    """
    t = d.year.values * 12 + d.month.values
    if len(t) < seq + 1 or not np.all(np.diff(t) == 1):
        # keep the longest contiguous run
        brk = np.flatnonzero(np.diff(t) != 1)
        segs, s0 = [], 0
        for b in list(brk) + [len(t) - 1]:
            segs.append((s0, b + 1))
            s0 = b + 1
        s0, s1 = max(segs, key=lambda ab: ab[1] - ab[0])
        d = d.iloc[s0:s1]
        t = t[s0:s1]
        if len(t) < seq + 1:
            return None
    A = d[DYN].values.astype(np.float32)
    W = windows(A, seq)                                  # (n-seq+1, seq, f)
    y = d[NDVI].values.astype(np.float32)[seq - 1:]
    S = np.repeat(d[STAT].values.astype(np.float32)[seq - 1:][:, None, :], 1, axis=1)[:, 0, :]
    mo = d.month.values[seq - 1:]
    yr = d.year.values[seq - 1:]
    ok = np.isfinite(W).all(axis=(1, 2)) & np.isfinite(y) & np.isfinite(S).all(axis=1)
    return W[ok], S[ok], y[ok], yr[ok], mo[ok]


# ---------------------------------------------------------------------------------------------
def step_train():
    import torch
    import torch.nn as nn

    don, _ = regions()
    rs = np.random.default_rng(SEED)   # batch shuffling only
    chosen = []
    Ws, Ss, ys = [], [], []
    tot = 0
    log("=" * 104)
    log("KRAFT RIVAL | building donor sequences | %d donor regions | %d cells each | seq %d"
        % (len(don), DONCELLS, SEQ))
    log("  dynamic: %s" % ", ".join(DYN))
    log("  static : %s   (LAND COVER DROPPED -- banned proxy)" % ", ".join(STAT))
    t0 = time.time()
    for i, r in enumerate(don, 1):
        f0 = os.path.join(PANEL, "%s_monthly_2010.parquet" % r)
        if not os.path.exists(f0):
            continue
        try:
            ids = pd.read_parquet(f0, columns=["cell_id"]).cell_id.unique()
        except Exception:
            continue
        # DETERMINISTIC TRAINING SET. Which donor cells train the model is a DATA CHOICE, not an
        # implementation detail, so it must not be drawn at random: two runs of this configuration
        # have to be the same experiment. Sorted order, first DONCELLS, and the chosen ids are
        # written to disk so any later run joins onto the identical training cells.
        # EVENLY SPACED, NOT FIRST-N. Both are deterministic, but cell_id sorts by position, so
        # first-N collapses onto a single longitude: on great_plains it spans 0.69 deg of latitude
        # and 0.00 deg of longitude out of a 9.04 x 6.00 deg region -- a vertical sliver. A stride
        # over the sorted ids is equally reproducible and covers 8.59 x 5.79 deg. Training a GLOBAL
        # model on slivers cost the rival 16% of its annual score, which is a handicap invented by
        # the sampling rule rather than by the method.
        _sid = sorted(ids)
        pick = set(_sid[::max(1, len(_sid) // DONCELLS)][:DONCELLS])
        chosen.extend((r, c) for c in sorted(pick))
        X = load_cells(r, pick, 2002, 2023)
        if X is None:
            continue
        for _, d in X.groupby("cell_id", sort=False):
            out = cell_sequences(d, SEQ)
            if out is None or not len(out[0]):
                continue
            Ws.append(out[0]); Ss.append(out[1]); ys.append(out[2])
            tot += len(out[0])
        del X
        gc.collect()
        # CONSOLIDATE. Thousands of small per-cell arrays cost far more in Python object overhead
        # than the 288 bytes per sequence they actually hold -- 450k sequences is 130 MB of data
        # and was costing ~3 GB of process. Collapsing to one array every few regions keeps the
        # footprint proportional to the data.
        if len(Ws) > 2000:
            Ws = [np.concatenate(Ws)]
            Ss = [np.concatenate(Ss)]
            ys = [np.concatenate(ys)]
            gc.collect()
        guard("donor %s" % r)
        if i % 15 == 0:
            log("  %d/%d donor regions | %s sequences | %.1f min"
                % (i, len(don), format(tot, ","), (time.time() - t0) / 60))
        if tot >= MAXSEQ:
            log("  reached the %s-sequence cap at donor region %d -- stopping collection"
                % (format(MAXSEQ, ","), i))
            break
    pd.DataFrame(chosen, columns=["region", "cell_id"]).to_csv(
        os.path.join(OUT, "train_cells.csv"), index=False)
    log("  training cells recorded -> %s (%s cells, fixed)"
        % (os.path.join(OUT, "train_cells.csv"), format(len(chosen), ",")))
    W = np.concatenate(Ws); S = np.concatenate(Ss); y = np.concatenate(ys)
    del Ws, Ss, ys
    gc.collect()
    log("  training set: %s sequences x %d months x %d vars + %d statics"
        % (format(len(W), ","), SEQ, len(DYN), len(STAT)))

    wm, ws = W.reshape(-1, len(DYN)).mean(0), W.reshape(-1, len(DYN)).std(0) + 1e-6
    sm, ss = S.mean(0), S.std(0) + 1e-6
    np.savez(os.path.join(OUT, "norm.npz"), wm=wm, ws=ws, sm=sm, ss=ss)
    W = (W - wm) / ws
    S = (S - sm) / ss

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    torch.manual_seed(SEED)

    class Net(nn.Module):
        def __init__(self):
            super().__init__()
            self.lstm = nn.LSTM(len(DYN), HID, batch_first=True)
            self.head = nn.Sequential(nn.Linear(HID + len(STAT), 64), nn.ReLU(), nn.Linear(64, 1))

        def forward(self, w, s):
            h, _ = self.lstm(w)
            return self.head(torch.cat([h[:, -1, :], s], 1)).squeeze(1)

    net = Net().to(dev)
    opt = torch.optim.Adam(net.parameters(), lr=2e-3)
    lossf = nn.L1Loss()
    n = len(W)
    idx = np.arange(n)
    log("  training on %s | %d epochs | batch %d | hidden %d" % (dev, EPOCHS, BATCH, HID))
    for ep in range(EPOCHS):
        rs.shuffle(idx)
        tl, nb = 0.0, 0
        for a in range(0, n, BATCH):
            b = idx[a:a + BATCH]
            w = torch.from_numpy(W[b]).to(dev)
            s = torch.from_numpy(S[b]).to(dev)
            t = torch.from_numpy(y[b]).to(dev)
            opt.zero_grad()
            l = lossf(net(w, s), t)
            l.backward()
            opt.step()
            tl += float(l); nb += 1
        log("    epoch %d/%d  train MAE %.5f" % (ep + 1, EPOCHS, tl / max(nb, 1)))
    torch.save(net.state_dict(), os.path.join(OUT, "kraft_lstm.pt"))
    log("TRAIN DONE | %.1f min | model -> %s" % ((time.time() - t0) / 60,
                                                 os.path.join(OUT, "kraft_lstm.pt")))



# ---------------------------------------------------------------------------------------------
# PREDICT -- 44 held-out regions, three phase-2 versions of the climate window
# ---------------------------------------------------------------------------------------------
def step_predict():
    import torch
    import torch.nn as nn

    z = np.load(os.path.join(OUT, "norm.npz"))
    wm, ws, sm, ss = z["wm"], z["ws"], z["sm"], z["ss"]
    dev = "cuda" if torch.cuda.is_available() else "cpu"

    class Net(nn.Module):
        def __init__(self):
            super().__init__()
            self.lstm = nn.LSTM(len(DYN), HID, batch_first=True)
            self.head = nn.Sequential(nn.Linear(HID + len(STAT), 64), nn.ReLU(), nn.Linear(64, 1))

        def forward(self, w, s):
            h, _ = self.lstm(w)
            return self.head(torch.cat([h[:, -1, :], s], 1)).squeeze(1)

    net = Net().to(dev)
    net.load_state_dict(torch.load(os.path.join(OUT, "kraft_lstm.pt"), map_location=dev))
    net.eval()

    _, tst = regions()
    regs = sorted(os.path.basename(f)[:-8] for f in glob.glob(os.path.join(OURS, "*.parquet")))
    log("=" * 104)
    log("KRAFT PREDICT | %d held-out regions | seq %d | device %s" % (len(regs), SEQ, dev))
    t0 = time.time()
    done = 0
    for n_r, r in enumerate(regs, 1):
        dst = os.path.join(OUT, "%s.parquet" % r)
        if os.path.exists(dst):
            continue
        O = pd.read_parquet(os.path.join(OURS, "%s.parquet" % r),
                            columns=["cell_id", "year", "month"])
        cells = set(pd.unique(O.cell_id))
        guard("predict %s" % r)
        X = load_cells(r, cells, 2002, int(O.year.max()))
        if X is None:
            continue
        # per-cell calibration climatology of every dynamic driver
        cal = X[X.year <= 2019]
        cm = cal.groupby(["cell_id", "month"])[DYN].mean().reset_index()
        cm = cm.rename(columns={c: c + "__c" for c in DYN})
        X = X.merge(cm, on=["cell_id", "month"], how="left")

        rows = []
        for cid, d in X.groupby("cell_id", sort=False):
            t = d.year.values * 12 + d.month.values
            if len(t) < SEQ + 13 or not np.all(np.diff(t) == 1):
                brk = np.flatnonzero(np.diff(t) != 1)
                segs, s0 = [], 0
                for b in list(brk) + [len(t) - 1]:
                    segs.append((s0, b + 1)); s0 = b + 1
                s0, s1 = max(segs, key=lambda ab: ab[1] - ab[0])
                d = d.iloc[s0:s1]
                if len(d) < SEQ + 13:
                    continue
            A = d[DYN].values.astype(np.float32)
            C = d[[c + "__c" for c in DYN]].values.astype(np.float32)
            S1 = d[STAT].values.astype(np.float32)
            yr = d.year.values
            mo = d.month.values
            WA = windows(A, SEQ)                     # WA[j] ends at row j+SEQ-1
            WC = windows(C, SEQ)
            tgt = np.flatnonzero((yr >= int(O.year.min())) & (yr <= int(O.year.max())))
            tgt = tgt[tgt >= SEQ - 1 + 12]           # need a lag-12 window as well
            if not len(tgt):
                continue
            io_ = tgt - (SEQ - 1)
            il_ = tgt - 12 - (SEQ - 1)
            r_ = pd.DataFrame({"cell_id": cid, "year": yr[tgt], "month": mo[tgt]})
            st = (S1[tgt] - sm) / ss
            for tag, Wsel in (("oracle", WA[io_]), ("lag12", WA[il_]), ("clim", WC[io_])):
                w = (Wsel - wm) / ws
                ok = np.isfinite(w).all(axis=(1, 2)) & np.isfinite(st).all(axis=1)
                p = np.full(len(w), np.nan, np.float32)
                if ok.any():
                    with torch.no_grad():
                        wt = torch.from_numpy(np.ascontiguousarray(w[ok], np.float32)).to(dev)
                        stt = torch.from_numpy(np.ascontiguousarray(st[ok], np.float32)).to(dev)
                        out = []
                        for a in range(0, len(wt), 8192):
                            out.append(net(wt[a:a + 8192], stt[a:a + 8192]).cpu().numpy())
                        p[ok] = np.concatenate(out)
                r_["kraft_" + tag] = np.clip(p, -1.0, 1.0)
            rows.append(r_)
        del X
        gc.collect()
        if not rows:
            continue
        R = pd.concat(rows, ignore_index=True)
        R.to_parquet(dst, index=False)
        done += 1
        el = (time.time() - t0) / 60
        log("  %-34s %7s rows | %d/%d | %.1f min | ~%.0f min left"
            % (r, format(len(R), ","), n_r, len(regs), el, el / max(done, 1) * (len(regs) - n_r)))
        del R, rows
        gc.collect()
    log("PREDICT DONE | %d regions | %.1f min" % (done, (time.time() - t0) / 60))


# ---------------------------------------------------------------------------------------------
# SCORE -- both rivals against ours, information-matched
# ---------------------------------------------------------------------------------------------
def step_score():
    mae = lambda y, p: (lambda m: float(np.mean(np.abs(y[m] - p[m]))))(np.isfinite(y) & np.isfinite(p))
    M, A = [], []
    for f in sorted(glob.glob(os.path.join(OUT, "*.parquet"))):
        reg = os.path.basename(f)[:-8]
        if reg in ("norm",):
            continue
        k = pd.read_parquet(f)
        try:
            o = pd.read_parquet(os.path.join(OURS, "%s.parquet" % reg),
                                columns=["cell_id", "year", "month", "y_true", "clim", "evt"])
            nc = pd.read_parquet(os.path.join(NOWC, "%s.parquet" % reg),
                                 columns=["cell_id", "year", "month", "evt"]).rename(
                                 columns={"evt": "ours_now"})
            mc = pd.read_parquet(os.path.join(MCP, "%s.parquet" % reg),
                                 columns=["cell_id", "year", "month",
                                          "mcp_clim", "mcp_lag12", "mcp_oracle"])
        except Exception:
            continue
        d = k.merge(o, on=["cell_id", "year", "month"]).merge(
            nc, on=["cell_id", "year", "month"]).merge(mc, on=["cell_id", "year", "month"])
        if not len(d):
            continue
        y = d.y_true.values
        arms = [a for a in ["ours_now", "evt", "clim", "mcp_oracle", "mcp_lag12", "mcp_clim",
                "kraft_oracle", "kraft_lag12", "kraft_clim", "kraft_oracle_cal",
                "kraft_lag12_cal", "kraft_clim_cal"] if a in d.columns]
        M.append(dict(region=reg, n=len(d), **{a: mae(y, d[a].values) for a in arms}))
        g = d.groupby(["cell_id", "year"]).agg(months=("y_true", "size"),
            **{a: (a, "mean") for a in ["y_true"] + arms}).reset_index()
        g = g[g.months >= 10]
        if len(g):
            A.append(dict(region=reg, n=len(g),
                          **{a: mae(g.y_true.values, g[a].values) for a in arms}))
        del d, k, g
        gc.collect()

    TIER1 = [("ours_now", "OURS nowcast"), ("mcp_oracle", "McPhillips ORACLE"),
             ("kraft_oracle", "Kraft LSTM ORACLE (raw)"),
             ("kraft_oracle_cal", "Kraft LSTM ORACLE (calibrated)")]
    TIER2 = [("evt", "OURS forecast @12mo"), ("mcp_lag12", "McPhillips lag-12"),
             ("mcp_clim", "McPhillips driver-clim"),
             ("kraft_lag12_cal", "Kraft LSTM lag-12 (cal)"),
             ("kraft_clim_cal", "Kraft LSTM driver-clim (cal)")]
    for tag, rows in (("MONTHLY", M), ("ANNUAL MEAN", A)):
        if not rows:
            continue
        R = pd.DataFrame(rows)
        b = R["clim"]
        log("=" * 104)
        log("%s | %d regions | %s rows | THREE ARCHITECTURES, INFORMATION-MATCHED"
            % (tag, len(R), format(int(R.n.sum()), ",")))
        for title, tier in (("sees the target month's climate -- NOT a forecast", TIER1),
                            ("genuine 12-month forecasts", TIER2)):
            log("  --- %s ---" % title)
            tier = [(a, nm) for a, nm in tier if a in R.columns]
            for a, nm in sorted(tier, key=lambda x: R[x[0]].mean()):
                log("    %-26s %9.5f  %+6.1f%% vs clim   beats clim %2d/%d"
                    % (nm, R[a].mean(), 100 * (1 - R[a].mean() / b.mean()),
                       int((R[a] < b).sum()), len(R)))
        log("    %-26s %9.5f" % ("cell climatology", b.mean()))
        rivcols = [c for c in ("mcp_lag12", "mcp_clim", "kraft_lag12_cal", "kraft_clim_cal",
                               "kraft_lag12", "kraft_clim") if c in R.columns]
        best_riv = R[rivcols].min(axis=1)
        log("")
        log("  OURS forecast beats the BEST of both rivals' honest arms in %d of %d regions"
            % (int((R["evt"] < best_riv).sum()), len(R)))
        R.to_csv(os.path.join(OUT, "scores_3way_%s.csv" % tag.split()[0].lower()), index=False)
        log("  written to %s" % os.path.join(OUT, "scores_3way_%s.csv" % tag.split()[0].lower()))


# ---------------------------------------------------------------------------------------------
# CALIBRATE -- give the global LSTM the same local calibration every other baseline received
# ---------------------------------------------------------------------------------------------
CAL_Y0 = int(ARG.get("--caly0", 2017))
CAL_Y1 = int(ARG.get("--caly1", 2019))


def step_calib():
    """Fit a per-cell correction on <=2019 and apply it to the held-out predictions.

    WHY THIS IS OWED. Every other external baseline in this project was handed a local calibration:
    CRW and CEMS got an isotonic link fitted on donors, and McPhillips is per-cell by construction.
    The Kraft LSTM is a single GLOBAL model with six static features to tell a Saharan cell from a
    Bornean one -- and the input that would have carried the NDVI LEVEL, land cover, was dropped as
    a banned proxy. Scoring it uncalibrated against two locally-calibrated models measures the
    calibration, not the architecture. Diagnosed before this step: correlation with truth 0.587
    (0.94 in some regions), SD ratio 0.94, mean |bias| 0.0201 -- it tracks and has the right
    amplitude, it is simply not anchored per cell.

    The correction is a per-cell LINEAR map fitted on CALIBRATION YEARS ONLY (default 2017-2019),
    y ~ a + b * pred, with a fallback to a pure bias shift where a cell has too few months or a
    degenerate spread. Calibration uses ORACLE drivers because at calibration time the climate IS
    observed; the phase-2 variants still differ in the test window, which is where the forecast
    question lives.
    """
    import torch
    import torch.nn as nn

    z = np.load(os.path.join(OUT, "norm.npz"))
    wm, ws, sm, ss = z["wm"], z["ws"], z["sm"], z["ss"]
    dev = "cuda" if torch.cuda.is_available() else "cpu"

    class Net(nn.Module):
        def __init__(self):
            super().__init__()
            self.lstm = nn.LSTM(len(DYN), HID, batch_first=True)
            self.head = nn.Sequential(nn.Linear(HID + len(STAT), 64), nn.ReLU(), nn.Linear(64, 1))

        def forward(self, w, s):
            h, _ = self.lstm(w)
            return self.head(torch.cat([h[:, -1, :], s], 1)).squeeze(1)

    net = Net().to(dev)
    net.load_state_dict(torch.load(os.path.join(OUT, "kraft_lstm.pt"), map_location=dev))
    net.eval()

    regs = sorted(os.path.basename(f)[:-8] for f in glob.glob(os.path.join(OURS, "*.parquet")))
    log("=" * 104)
    log("KRAFT CALIBRATION | per-cell linear fit on %d-%d | %d regions | device %s"
        % (CAL_Y0, CAL_Y1, len(regs), dev))
    t0 = time.time()
    done = 0
    for n_r, r in enumerate(regs, 1):
        dst = os.path.join(OUT, "%s.parquet" % r)
        if not os.path.exists(dst):
            continue
        K = pd.read_parquet(dst)
        if "kraft_oracle_cal" in K.columns:
            continue
        guard("calib %s" % r)
        cells = set(pd.unique(K.cell_id))
        X = load_cells(r, cells, 2002, CAL_Y1)
        if X is None:
            continue
        rows = []
        for cid, d in X.groupby("cell_id", sort=False):
            t = d.year.values * 12 + d.month.values
            if len(t) < SEQ + 1 or not np.all(np.diff(t) == 1):
                brk = np.flatnonzero(np.diff(t) != 1)
                segs, s0 = [], 0
                for b in list(brk) + [len(t) - 1]:
                    segs.append((s0, b + 1)); s0 = b + 1
                s0, s1 = max(segs, key=lambda ab: ab[1] - ab[0])
                d = d.iloc[s0:s1]
                if len(d) < SEQ + 1:
                    continue
            A = d[DYN].values.astype(np.float32)
            S1 = d[STAT].values.astype(np.float32)
            yv = d[NDVI].values.astype(np.float32)
            yr = d.year.values
            WA = windows(A, SEQ)
            tgt = np.flatnonzero((yr >= CAL_Y0) & (yr <= CAL_Y1))
            tgt = tgt[tgt >= SEQ - 1]
            if not len(tgt):
                continue
            w = (WA[tgt - (SEQ - 1)] - wm) / ws
            st = (S1[tgt] - sm) / ss
            ok = np.isfinite(w).all(axis=(1, 2)) & np.isfinite(st).all(axis=1) & np.isfinite(yv[tgt])
            if ok.sum() < 12:
                continue
            with torch.no_grad():
                wt = torch.from_numpy(np.ascontiguousarray(w[ok], np.float32)).to(dev)
                stt = torch.from_numpy(np.ascontiguousarray(st[ok], np.float32)).to(dev)
                p = net(wt, stt).cpu().numpy()
            yy = yv[tgt][ok]
            # linear where the predictor actually varies, otherwise a pure bias shift
            if p.std() > 1e-4:
                b1, b0 = np.polyfit(p, yy, 1)
                if not np.isfinite(b1) or not np.isfinite(b0) or abs(b1) > 10:
                    b1, b0 = 1.0, float(yy.mean() - p.mean())
            else:
                b1, b0 = 1.0, float(yy.mean() - p.mean())
            rows.append((cid, b0, b1, int(ok.sum())))
        del X
        gc.collect()
        if not rows:
            continue
        C = pd.DataFrame(rows, columns=["cell_id", "b0", "b1", "n_cal"])
        K = K.merge(C, on="cell_id", how="left")
        for tag in ("oracle", "lag12", "clim"):
            src = "kraft_" + tag
            if src in K.columns:
                K[src + "_cal"] = np.clip(K.b0 + K.b1 * K[src], -1.0, 1.0).astype(np.float32)
        K.drop(columns=["b0", "b1"], inplace=True)
        K.to_parquet(dst, index=False)
        done += 1
        el = (time.time() - t0) / 60
        log("  %-34s %6d cells calibrated | %d/%d | %.1f min | ~%.0f min left"
            % (r, len(C), n_r, len(regs), el, el / max(done, 1) * (len(regs) - n_r)))
        del K, C, rows
        gc.collect()
    log("CALIB DONE | %d regions | %.1f min" % (done, (time.time() - t0) / 60))

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    if STEP == "train":
        step_train()
    elif STEP == "predict":
        step_predict()
    elif STEP == "calib":
        step_calib()
    elif STEP == "score":
        step_score()
    else:
        log("unknown --step=%s  (train | predict | score)" % STEP)
