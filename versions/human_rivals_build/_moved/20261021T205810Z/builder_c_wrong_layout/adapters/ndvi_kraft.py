"""Kraft et al. 2019 global LSTM (OPTIONAL NDVI rival, opt-in; ruling Q10: CPU only, lead 0 only).

SPEC_HUMAN.txt section 5 (Kraft). Kind M, tier P at lead 0, F0 (no extra map). Architecture as the old
ndvi_kraft.py (root folder; read-only reference, NEVER imported): an LSTM over a window of `seq` months of the
`drivers`, its last hidden state joined to the `statics`, a 64-unit ReLU head, one output = the NDVI level.
L1 loss, Adam, `epochs` passes, batch shuffling from numpy default_rng(seed); land cover dropped (banned proxy).

Fit: one global model on the fit set's rows of ALL units in it (the bank units; tune -> guard rows, refit ->
test rows), labels only through ctx.fit_labels. Inputs only from the Kraft store (ndvi_kraft_prep.py), opened
through ctx.open_product (sha checked). The window of a row ends at e = issue - S, S = the largest R8 `steps` of
the rival's `t1_kind_columns` (the drivers; 0 on the ndvi run: the nowcast sees month-t climate). A row without a
complete window or statics is not covered (counted). No NDVI is read: target_obs_end = NaN.
Determinism: torch.manual_seed(seed) (the one fixed seed, PROT H18), deterministic algorithms, CPU, `threads`
threads. No seed is varied.

Opt-in: the registry entry is `optional: true`; nothing here is imported unless the tool calls this runner.
"""
import base64
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

ADAPTER_FORMAT = "human-adapter-ndvi-kraft/1"
PARAMS_FORMAT = "human-kraft-params/1"
KEYS = ("unit", "group", "time", "issue", "lead")
DEFAULTS = {"seq": 12, "hidden": 64, "head": 64, "epochs": 8, "batch": 4096, "lr": 2e-3, "seed": 0, "threads": 8,
            "norm_eps": 1e-6}
FIT_SETS = ("tune", "refit", "guardfit")


class KraftRefusal(RuntimeError):
    """A Kraft rule refused (fail loud)."""


def _refuse(message: str, fix: Optional[str] = None):
    raise KraftRefusal(message + ("" if not fix else "  FIX: " + fix))


def options(rival: Mapping[str, Any]) -> Dict[str, Any]:
    opt = dict(DEFAULTS)
    opt.update(dict(rival.get("options") or {}))
    for k in ("store_product", "drivers", "statics"):
        if k not in opt:
            _refuse("rival %s: registry options lack %r" % (rival.get("id"), k))
    for k in ("seq", "hidden", "head", "epochs", "batch", "seed", "threads"):
        opt[k] = int(opt[k])
    opt["lr"] = float(opt["lr"])
    opt["norm_eps"] = float(opt["norm_eps"])
    if opt["seq"] < 1 or opt["epochs"] < 1 or opt["batch"] < 1:
        _refuse("rival %s: seq, epochs and batch must be >= 1" % rival.get("id"))
    return opt


def window_shift(run: Any, rival: Mapping[str, Any]) -> int:
    """S = max R8 `steps` over the rival's t1_kind_columns (the T1 boundary of SPEC_HUMAN 1.5)."""
    names = list(rival.get("t1_kind_columns") or [])
    r8 = run.derived["R8"]["value"]
    if not names:
        return int(max(int(v["steps"]) for v in r8.values()))
    missing = [n for n in names if n not in r8]
    if missing:
        _refuse("t1_kind_columns %s are not R8 entries of the run" % missing)
    return int(max(int(r8[n]["steps"]) for n in names))


# ---------------------------------------------------------------------------------------------------
# The store and the windows
class Store(object):
    """Dense per-unit arrays: drivers [U, T, D] and statics [U, T, K] over the steps step0..step1."""

    def __init__(self, frame: pd.DataFrame, drivers: Sequence[str], statics: Sequence[str]):
        need = ["unit", "step"] + list(drivers) + list(statics)
        missing = [c for c in need if c not in frame.columns]
        if missing:
            _refuse("Kraft store lacks the columns %s" % missing)
        if frame.duplicated(subset=["unit", "step"]).any():
            _refuse("Kraft store names a (unit, step) twice")
        self.units = pd.Index(sorted(frame["unit"].astype(str).unique()))
        self.step0 = int(frame["step"].min())
        self.step1 = int(frame["step"].max())
        T = self.step1 - self.step0 + 1
        ui = self.units.get_indexer(frame["unit"].astype(str))
        ti = frame["step"].to_numpy(np.int64) - self.step0
        self.dyn = np.full((len(self.units), T, len(drivers)), np.nan, dtype=np.float32)
        self.sta = np.full((len(self.units), T, len(statics)), np.nan, dtype=np.float32)
        self.dyn[ui, ti] = frame[list(drivers)].to_numpy(np.float32)
        self.sta[ui, ti] = frame[list(statics)].to_numpy(np.float32)

    def windows(self, units: Sequence[str], end_step: np.ndarray, seq: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """(W n x seq x D, S n x K, ok n): the window of months end-seq+1..end and the statics at end. ok = the
        unit is in the store, every window month and static is present and finite."""
        n = len(units)
        ui = self.units.get_indexer(pd.Index([str(u) for u in units]))
        e = np.asarray(end_step, dtype=np.int64) - self.step0
        ok = (ui >= 0) & (e - (seq - 1) >= 0) & (e < self.dyn.shape[1])
        W = np.zeros((n, seq, self.dyn.shape[2]), dtype=np.float32)
        S = np.zeros((n, self.sta.shape[2]), dtype=np.float32)
        r = np.flatnonzero(ok)
        if r.size:
            idx = e[r][:, None] - np.arange(seq - 1, -1, -1)[None, :]
            W[r] = self.dyn[ui[r][:, None], idx]
            S[r] = self.sta[ui[r], e[r]]
        ok &= np.isfinite(W).all(axis=(1, 2)) & np.isfinite(S).all(axis=1)
        return W, S, ok


def load_store(ctx: Any, opt: Mapping[str, Any]) -> Store:
    pid = opt["store_product"]
    man = ctx.product_manifest(pid)
    if man is None:
        _refuse("the Kraft store %s is not on disk: run the Kraft prep (SPEC_HUMAN 8 O15) and its manifest first" % pid)
    names = sorted(n for n in (man.get("files") or {}) if n.endswith(".parquet"))
    if not names:
        _refuse("the Kraft store %s lists no parquet file" % pid)
    cols = ["unit", "step"] + list(opt["drivers"]) + list(opt["statics"])
    parts = [pd.read_parquet(str(ctx.open_product(pid, n)), columns=cols) for n in names]
    return Store(pd.concat(parts, ignore_index=True), opt["drivers"], opt["statics"])


# ---------------------------------------------------------------------------------------------------
# The network (as ndvi_kraft.py:251-260)
def _net(opt: Mapping[str, Any]):
    import torch.nn as nn
    import torch

    class Net(nn.Module):
        def __init__(self):
            super().__init__()
            self.lstm = nn.LSTM(len(opt["drivers"]), opt["hidden"], batch_first=True)
            self.head = nn.Sequential(nn.Linear(opt["hidden"] + len(opt["statics"]), opt["head"]), nn.ReLU(),
                                      nn.Linear(opt["head"], 1))

        def forward(self, w, s):
            h, _ = self.lstm(w)
            return self.head(torch.cat([h[:, -1, :], s], 1)).squeeze(1)

    return Net()


def _torch_setup(opt: Mapping[str, Any]):
    import torch

    torch.set_num_threads(int(opt["threads"]))
    torch.use_deterministic_algorithms(True)
    torch.manual_seed(int(opt["seed"]))
    return torch


def _encode(a: np.ndarray) -> Dict[str, Any]:
    a = np.ascontiguousarray(a, dtype=np.float32)
    return {"shape": list(a.shape), "f32_b64": base64.b64encode(a.tobytes()).decode("ascii")}


def _decode(d: Mapping[str, Any]) -> np.ndarray:
    return np.frombuffer(base64.b64decode(d["f32_b64"]), dtype=np.float32).reshape(d["shape"]).copy()


def _scored_units(ctx: Any) -> set:
    u = ctx.units
    if "is_scored" not in u.columns:
        _refuse("units.parquet has no is_scored column")
    return set(u.loc[u["is_scored"].astype(bool), "unit"].astype(str))


def _keys(ctx: Any, lead: int, set_name: str) -> pd.DataFrame:
    got = ctx.read_inputs(int(lead), set_name)
    keys = got[0] if isinstance(got, tuple) else got
    return keys[list(KEYS)].reset_index(drop=True)


# ---------------------------------------------------------------------------------------------------
# The M runner
def fit(ctx: Any, rival: Mapping[str, Any], lead: int, fit_set: str, store: Optional[Store] = None) -> Dict[str, Any]:
    if fit_set not in FIT_SETS:
        _refuse("Kraft fits on a fit set (%s), not %r" % ("/".join(FIT_SETS), fit_set))
    opt = options(rival)
    torch = _torch_setup(opt)
    S_shift = window_shift(ctx.run, rival)
    store = store if store is not None else load_store(ctx, opt)
    keys = _keys(ctx, lead, fit_set)
    y = np.asarray(ctx.fit_labels(int(lead), fit_set), dtype=np.float32)
    if y.shape != (len(keys),):
        _refuse("fit labels of %s hold %s values for %d rows" % (fit_set, y.shape, len(keys)))
    end = keys["issue"].to_numpy(np.int64) - S_shift
    W, S, ok = store.windows(keys["unit"].astype(str).tolist(), end, opt["seq"])
    ok &= np.isfinite(y)
    W, S, y = W[ok], S[ok], y[ok]
    if len(y) == 0:
        _refuse("Kraft %s: no fit row has a complete window" % fit_set)
    D = W.shape[2]
    wm = W.reshape(-1, D).mean(0)
    ws = W.reshape(-1, D).std(0) + opt["norm_eps"]
    sm = S.mean(0)
    ss = S.std(0) + opt["norm_eps"]
    W = (W - wm) / ws
    S = (S - sm) / ss
    net = _net(opt)
    optim = torch.optim.Adam(net.parameters(), lr=opt["lr"])
    lossf = torch.nn.L1Loss()
    rs = np.random.default_rng(int(opt["seed"]))
    idx = np.arange(len(y))
    losses = []
    for ep in range(opt["epochs"]):
        rs.shuffle(idx)
        tl, nb = 0.0, 0
        for a in range(0, len(y), opt["batch"]):
            b = idx[a:a + opt["batch"]]
            optim.zero_grad()
            l = lossf(net(torch.from_numpy(W[b]), torch.from_numpy(S[b])), torch.from_numpy(y[b]))
            l.backward()
            optim.step()
            tl += float(l)
            nb += 1
        losses.append(tl / max(nb, 1))
        ctx.log("Kraft %s lead %d epoch %d/%d train MAE %.6f" % (rival.get("id"), int(lead), ep + 1, opt["epochs"],
                                                                losses[-1]))
    state = {k: _encode(v.detach().cpu().numpy()) for k, v in net.state_dict().items()}
    return {"format": PARAMS_FORMAT, "adapter": ADAPTER_FORMAT, "rival": rival.get("id"), "lead": int(lead),
            "fit_set": fit_set, "window_shift": S_shift,
            "options": {k: opt[k] for k in sorted(opt) if k in DEFAULTS or k in ("drivers", "statics")},
            "norm": {"wm": _encode(wm), "ws": _encode(ws), "sm": _encode(sm), "ss": _encode(ss)},
            "state": state, "epoch_train_mae": losses,
            "counts": {"rows_fit_set": int(len(keys)), "rows_with_window": int(ok.sum())}}


def predict(ctx: Any, rival: Mapping[str, Any], lead: int, params: Mapping[str, Any], score_set: str,
            store: Optional[Store] = None) -> pd.DataFrame:
    opt = options(rival)
    if params.get("format") != PARAMS_FORMAT or int(params.get("lead", -1)) != int(lead):
        _refuse("Kraft params are not %s params of lead %d" % (PARAMS_FORMAT, int(lead)))
    torch = _torch_setup(opt)
    S_shift = window_shift(ctx.run, rival)
    if S_shift != int(params["window_shift"]):
        _refuse("Kraft params were fitted with window shift %s, the run gives %d" % (params["window_shift"], S_shift))
    store = store if store is not None else load_store(ctx, opt)
    keys = _keys(ctx, lead, score_set)
    scored = _scored_units(ctx)
    keys = keys[keys["unit"].astype(str).isin(scored).to_numpy()].reset_index(drop=True)
    end = keys["issue"].to_numpy(np.int64) - S_shift
    W, S, ok = store.windows(keys["unit"].astype(str).tolist(), end, opt["seq"])
    nm = {k: _decode(v) for k, v in params["norm"].items()}
    net = _net(opt)
    import torch as _t
    net.load_state_dict({k: _t.from_numpy(_decode(v)) for k, v in params["state"].items()})
    net.eval()
    pre = np.full(len(keys), np.nan)
    r = np.flatnonzero(ok)
    with torch.no_grad():
        for a in range(0, r.size, opt["batch"]):
            b = r[a:a + opt["batch"]]
            w = torch.from_numpy(((W[b] - nm["wm"]) / nm["ws"]).astype(np.float32))
            s = torch.from_numpy(((S[b] - nm["sm"]) / nm["ss"]).astype(np.float32))
            pre[b] = net(w, s).numpy().astype(np.float64)
    out = keys.loc[ok].reset_index(drop=True)
    out["pre"] = pre[ok]
    out["info_end"] = end[ok].astype(np.int64)
    out["target_obs_end"] = np.nan
    ctx.log("Kraft %s lead %d predict on %s: %d scored-unit rows, %d without a complete window (not covered)"
            % (rival.get("id"), int(lead), score_set, len(keys), int((~ok).sum())))
    return out


__all__ = ["ADAPTER_FORMAT", "PARAMS_FORMAT", "KraftRefusal", "options", "window_shift", "Store", "load_store",
           "fit", "predict"]
