"""The fixed family of calibration maps (SPEC_HUMAN.txt 1.6; PROT H6; Q19 a, Q13, HQ6 a).

z = link-space prediction; z0 = the row's link-space normal; xbar = the index's own mean per unit x season key over
the same fit rows (a unit-key cell with < 3 covered rows takes the pooled key mean; an unseen key the pooled mean).
  F0 native    pred = x                                    (no fit, no link)
  F1 lin_link  link(y) = a + b link(x)        OLS          (x put inside the link's domain first: >= 0, <= UB)
  F2 iso_raw   link(y) = iso(x)
  F3 lin_anom  link(y) - z0 = a + b (x - xbar)  OLS
  F4 iso_anom  link(y) - z0 = iso(x - xbar)
  F5 unit_mos  link(y) - z0 = a_u + b_u (x - xbar) per unit, a_u and b_u shrunk toward the pooled F3 (a, b):
               slope_u* = (n_u b_u + K b_pool) / (n_u + K), the same for the intercept, K = SHRINK_K; a unit with
               < 3 covered fit rows (or unseen at prediction) takes the pooled map (counted)
  F6 pct_ratio pred = normal x iso_g(x) per group of the ratio y / normal on a per-unit percentile stat (identity link
               only; a group with < MIN_FIT_ROWS rows takes the pooled ratio map). Built generic, enabled only by a
               registry that lists it.
Isotonic maps: direction = the sign of Spearman(x, y) on the fit rows (recorded; undefined -> increasing), sklearn
IsotonicRegression(increasing=..., out_of_bounds="clip"), squared error, knots kept as JSON and applied with np.interp
(the same piecewise-linear clip-extrapolated function). No weights. A map needs >= MIN_FIT_ROWS covered labelled rows
in >= MIN_FIT_GROUPS groups, else NotCalibratable. The L1 isotonic map (weighted-median pool-adjacent-violators) is
for the printed L1 line only (Q13); it never decides.
"""
# Provenance: SPEC_HUMAN.txt 1.6, A4 (SHRINK_K), 6 (map family contract: fit(x, y, z0, link, c, ub, units, keys) ->
# MapModel; MapModel.predict(...) -> link-space z; MapModel.to_json()); engine layer/links.py:84 link_forward, :118
# link_inverse (through rivals.models.link_forward / link_inverse, the common package's wrappers).

import math
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from rivals_human import config as C


class NotCalibratable(Exception):
    """Too few covered labelled fit rows or groups (Q2.HQ9): the rival has no row at this lead (disclosed)."""


def _links():
    from rivals_human.common import load
    _, H = load()
    return H.M


def link_forward(v: np.ndarray, link: str, c: Optional[float], ub: Optional[float]) -> np.ndarray:
    return np.asarray(_links().link_forward(np.asarray(v, dtype=np.float64), link, c, ub), dtype=np.float64)


def link_inverse(z: np.ndarray, link: str, c: Optional[float], ub: Optional[float]) -> np.ndarray:
    return np.asarray(_links().link_inverse(np.asarray(z, dtype=np.float64), link, c, ub), dtype=np.float64)


def into_domain(x: np.ndarray, link: str, ub: Optional[float]) -> np.ndarray:
    """F1 reads link(x): x is put inside the link's domain (log_c and arcsine: >= 0; arcsine: <= UB)."""
    x = np.asarray(x, dtype=np.float64)
    if link in ("log_c", "arcsine"):
        x = np.maximum(x, 0.0)
    if link == "arcsine":
        x = np.minimum(x, float(ub))
    return x


def check_calibratable(y: np.ndarray, groups: Sequence[Any], what: str = "") -> None:
    n = int(np.asarray(y).size)
    g = len(set(str(v) for v in groups))
    if n < C.MIN_FIT_ROWS or g < C.MIN_FIT_GROUPS:
        raise NotCalibratable("%s%d covered labelled fit rows in %d groups (needs >= %d rows in >= %d groups)"
                              % (what + ": " if what else "", n, g, C.MIN_FIT_ROWS, C.MIN_FIT_GROUPS))


# ===================================================================================================== pieces
def spearman_sign(x: np.ndarray, y: np.ndarray) -> Tuple[bool, Optional[float]]:
    from scipy.stats import spearmanr
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    if x.size < 2 or np.all(x == x[0]) or np.all(y == y[0]):
        return True, None
    rho = float(spearmanr(x, y).correlation)
    if not math.isfinite(rho):
        return True, None
    return (rho >= 0.0), rho


def ols(x: np.ndarray, t: np.ndarray) -> Tuple[float, float]:
    """(a, b) of t = a + b x by least squares; b = 0 when x has no spread."""
    x = np.asarray(x, dtype=np.float64)
    t = np.asarray(t, dtype=np.float64)
    xm, tm = float(x.mean()), float(t.mean())
    dx = x - xm
    v = float(np.dot(dx, dx))
    b = float(np.dot(dx, t - tm)) / v if v > 0 else 0.0
    return tm - b * xm, b


class Iso(object):
    """An isotonic map as knots (np.interp with flat extrapolation = out_of_bounds='clip')."""

    def __init__(self, xk: np.ndarray, yk: np.ndarray, increasing: bool, rho: Optional[float], loss: str = "l2"):
        self.xk = np.asarray(xk, dtype=np.float64)
        self.yk = np.asarray(yk, dtype=np.float64)
        self.increasing, self.rho, self.loss = bool(increasing), rho, loss

    @classmethod
    def fit(cls, x: np.ndarray, t: np.ndarray, increasing: bool, rho: Optional[float]) -> "Iso":
        from sklearn.isotonic import IsotonicRegression
        m = IsotonicRegression(increasing=bool(increasing), out_of_bounds="clip")
        m.fit(np.asarray(x, dtype=np.float64), np.asarray(t, dtype=np.float64))
        return cls(m.X_thresholds_, m.y_thresholds_, increasing, rho)

    @classmethod
    def fit_l1(cls, x: np.ndarray, t: np.ndarray, increasing: bool, rho: Optional[float]) -> "Iso":
        xk, yk = l1_isotonic(x, t, increasing)
        return cls(xk, yk, increasing, rho, loss="l1")

    def __call__(self, x: np.ndarray) -> np.ndarray:
        x = np.asarray(x, dtype=np.float64)
        if self.xk.size == 1:
            return np.full(x.shape, float(self.yk[0]))
        return np.interp(x, self.xk, self.yk)

    def to_json(self) -> Dict[str, Any]:
        return {"x": self.xk.tolist(), "y": self.yk.tolist(), "increasing": self.increasing, "spearman": self.rho,
                "loss": self.loss}


def l1_isotonic(x: np.ndarray, t: np.ndarray, increasing: bool) -> Tuple[np.ndarray, np.ndarray]:
    """L1 (median) isotonic regression by pool-adjacent-violators on blocks of tied x. When x has more than
    L1_MAX_BLOCKS distinct values it is first cut into that many equal-count rank blocks (printed map only)."""
    x = np.asarray(x, dtype=np.float64)
    t = np.asarray(t, dtype=np.float64)
    sign = 1.0 if increasing else -1.0
    order = np.argsort(x, kind="mergesort")
    xs, ts = x[order], t[order] * sign
    ux, start = np.unique(xs, return_index=True)
    bounds = list(start) + [xs.size]
    if ux.size > C.L1_MAX_BLOCKS:
        cut = np.linspace(0, xs.size, C.L1_MAX_BLOCKS + 1).astype(np.int64)
        bounds = sorted(set(int(b) for b in cut))
    blocks: List[List[Any]] = []          # [values (sorted), median, x_lo, x_hi]
    for i in range(len(bounds) - 1):
        a, b = bounds[i], bounds[i + 1]
        if b <= a:
            continue
        vals = np.sort(ts[a:b])
        blocks.append([vals, float(np.median(vals)), float(xs[a]), float(xs[b - 1])])
        while len(blocks) > 1 and blocks[-2][1] > blocks[-1][1]:
            v2 = blocks.pop()
            v1 = blocks.pop()
            vals = np.sort(np.concatenate([v1[0], v2[0]]))
            blocks.append([vals, float(np.median(vals)), v1[2], v2[3]])
    xk, yk = [], []
    for vals, med, lo, hi in blocks:
        xk.append(lo)
        yk.append(med * sign)
        if hi != lo:
            xk.append(hi)
            yk.append(med * sign)
    return np.array(xk), np.array(yk)


class XBar(object):
    """The index's own mean per unit x season key over the fit rows (spec 1.6)."""

    def __init__(self, cells: Dict[str, float], keys: Dict[str, float], pooled: float):
        self.cells, self.keys, self.pooled = cells, keys, float(pooled)

    @classmethod
    def fit(cls, x: np.ndarray, units: Sequence[Any], season: Sequence[Any]) -> "XBar":
        f = pd.DataFrame({"u": np.asarray(units).astype(str), "k": np.asarray(season).astype(np.int64),
                          "x": np.asarray(x, dtype=np.float64)})
        g = f.groupby(["u", "k"], sort=True)["x"].agg(["mean", "size"])
        cells = {"%s|%d" % (u, k): float(m) for (u, k), m, n in zip(g.index, g["mean"], g["size"])
                 if int(n) >= C.MIN_UNIT_ROWS}
        kk = f.groupby("k", sort=True)["x"].mean()
        return cls(cells, {str(int(k)): float(v) for k, v in kk.items()}, float(f["x"].mean()))

    def __call__(self, units: Sequence[Any], season: Sequence[Any]) -> np.ndarray:
        u = np.asarray(units).astype(str)
        k = np.asarray(season).astype(np.int64)
        out = np.empty(u.size, dtype=np.float64)
        for i in range(u.size):
            key = "%s|%d" % (u[i], k[i])
            v = self.cells.get(key)
            if v is None:
                v = self.keys.get(str(int(k[i])), self.pooled)
            out[i] = v
        return out

    def counts(self, units: Sequence[Any], season: Sequence[Any]) -> Dict[str, int]:
        u = np.asarray(units).astype(str)
        k = np.asarray(season).astype(np.int64)
        cell = sum(1 for i in range(u.size) if "%s|%d" % (u[i], k[i]) in self.cells)
        key = sum(1 for i in range(u.size) if "%s|%d" % (u[i], k[i]) not in self.cells
                  and str(int(k[i])) in self.keys)
        return {"unit_key_mean": cell, "pooled_key_mean": key, "pooled_mean": int(u.size - cell - key)}

    def to_json(self) -> Dict[str, Any]:
        return {"cells": self.cells, "keys": self.keys, "pooled": self.pooled, "min_rows": C.MIN_UNIT_ROWS}


# ===================================================================================================== the models
class MapModel(object):
    """A fitted map. predict(...) returns link-space z (the tool back-transforms with link_inverse, no smearing)."""

    family = ""

    def __init__(self, link: Optional[str], c: Optional[float], ub: Optional[float]):
        self.link, self.c, self.ub = link, c, ub
        self.info: Dict[str, Any] = {}

    def predict(self, x: np.ndarray, z0: np.ndarray, units: Sequence[Any], keys: pd.DataFrame) -> np.ndarray:
        raise NotImplementedError

    def to_json(self) -> Dict[str, Any]:
        return {"family": self.family, "link": self.link, "c": self.c, "ub": self.ub, "info": self.info}


class F0Native(MapModel):
    family = "F0"

    @classmethod
    def fit(cls, x, y, z0, link, c, ub, units, keys):
        m = cls(None, c, ub)
        m.info = {"rule": "pred = x as shipped (no fit)"}
        return m

    def predict(self, x, z0, units, keys):
        return np.asarray(x, dtype=np.float64)


class F1LinLink(MapModel):
    family = "F1"

    @classmethod
    def fit(cls, x, y, z0, link, c, ub, units, keys):
        check_calibratable(y, keys["group"])
        m = cls(link, c, ub)
        lx = link_forward(into_domain(x, link, ub), link, c, ub)
        m.a, m.b = ols(lx, link_forward(y, link, c, ub))
        m.info = {"a": m.a, "b": m.b, "rows": int(np.asarray(y).size)}
        return m

    def predict(self, x, z0, units, keys):
        return self.a + self.b * link_forward(into_domain(x, self.link, self.ub), self.link, self.c, self.ub)


class F2IsoRaw(MapModel):
    family = "F2"
    loss = "l2"

    @classmethod
    def fit(cls, x, y, z0, link, c, ub, units, keys, loss="l2"):
        check_calibratable(y, keys["group"])
        m = cls(link, c, ub)
        inc, rho = spearman_sign(x, y)
        t = link_forward(y, link, c, ub)
        m.iso = Iso.fit(x, t, inc, rho) if loss == "l2" else Iso.fit_l1(x, t, inc, rho)
        m.info = {"iso": m.iso.to_json(), "rows": int(np.asarray(y).size)}
        return m

    def predict(self, x, z0, units, keys):
        return self.iso(x)


class F3LinAnom(MapModel):
    family = "F3"

    @classmethod
    def fit(cls, x, y, z0, link, c, ub, units, keys):
        check_calibratable(y, keys["group"])
        m = cls(link, c, ub)
        m.xbar = XBar.fit(x, units, keys[C.SEASON_KEY])
        xa = np.asarray(x, dtype=np.float64) - m.xbar(units, keys[C.SEASON_KEY])
        m.a, m.b = ols(xa, link_forward(y, link, c, ub) - np.asarray(z0, dtype=np.float64))
        m.info = {"a": m.a, "b": m.b, "rows": int(np.asarray(y).size),
                  "xbar_rows": m.xbar.counts(units, keys[C.SEASON_KEY])}
        return m

    def predict(self, x, z0, units, keys):
        xa = np.asarray(x, dtype=np.float64) - self.xbar(units, keys[C.SEASON_KEY])
        return np.asarray(z0, dtype=np.float64) + self.a + self.b * xa

    def to_json(self):
        d = super().to_json()
        d["xbar"] = self.xbar.to_json()
        return d


class F4IsoAnom(MapModel):
    family = "F4"

    @classmethod
    def fit(cls, x, y, z0, link, c, ub, units, keys, loss="l2"):
        check_calibratable(y, keys["group"])
        m = cls(link, c, ub)
        m.xbar = XBar.fit(x, units, keys[C.SEASON_KEY])
        xa = np.asarray(x, dtype=np.float64) - m.xbar(units, keys[C.SEASON_KEY])
        inc, rho = spearman_sign(x, y)
        t = link_forward(y, link, c, ub) - np.asarray(z0, dtype=np.float64)
        m.iso = Iso.fit(xa, t, inc, rho) if loss == "l2" else Iso.fit_l1(xa, t, inc, rho)
        m.info = {"iso": m.iso.to_json(), "rows": int(np.asarray(y).size),
                  "xbar_rows": m.xbar.counts(units, keys[C.SEASON_KEY])}
        return m

    def predict(self, x, z0, units, keys):
        xa = np.asarray(x, dtype=np.float64) - self.xbar(units, keys[C.SEASON_KEY])
        return np.asarray(z0, dtype=np.float64) + self.iso(xa)

    def to_json(self):
        d = super().to_json()
        d["xbar"] = self.xbar.to_json()
        return d


class F5UnitMos(MapModel):
    family = "F5"

    @classmethod
    def fit(cls, x, y, z0, link, c, ub, units, keys):
        check_calibratable(y, keys["group"])
        m = cls(link, c, ub)
        season = keys[C.SEASON_KEY]
        m.xbar = XBar.fit(x, units, season)
        xa = np.asarray(x, dtype=np.float64) - m.xbar(units, season)
        t = link_forward(y, link, c, ub) - np.asarray(z0, dtype=np.float64)
        m.a_pool, m.b_pool = ols(xa, t)
        u = np.asarray(units).astype(str)
        f = pd.DataFrame({"u": u, "xa": xa, "t": t})
        m.per_unit: Dict[str, Tuple[float, float, int]] = {}
        pooled_units, flat_units = 0, 0
        K = float(C.SHRINK_K)
        for unit, g in f.groupby("u", sort=True):
            n = int(len(g))
            if n < C.MIN_UNIT_ROWS:
                pooled_units += 1
                continue
            xv, tv = g["xa"].to_numpy(), g["t"].to_numpy()
            if float(np.dot(xv - xv.mean(), xv - xv.mean())) > 0:
                a_u, b_u = ols(xv, tv)
            else:
                flat_units += 1
                b_u = m.b_pool
                a_u = float(np.mean(tv - m.b_pool * xv))
            a_s = (n * a_u + K * m.a_pool) / (n + K)
            b_s = (n * b_u + K * m.b_pool) / (n + K)
            m.per_unit[str(unit)] = (float(a_s), float(b_s), n)
        m.info = {"a_pool": m.a_pool, "b_pool": m.b_pool, "shrink_k": C.SHRINK_K, "rows": int(t.size),
                  "units_fitted": len(m.per_unit), "units_pooled_fewer_than_min_rows": pooled_units,
                  "units_without_x_spread_pooled_slope": flat_units,
                  "xbar_rows": m.xbar.counts(units, season)}
        return m

    def coefficients(self, units: Sequence[Any]) -> Tuple[np.ndarray, np.ndarray, int]:
        u = np.asarray(units).astype(str)
        a = np.full(u.size, self.a_pool)
        b = np.full(u.size, self.b_pool)
        unseen = 0
        for i, unit in enumerate(u.tolist()):
            rec = self.per_unit.get(unit)
            if rec is None:
                unseen += 1
                continue
            a[i], b[i] = rec[0], rec[1]
        return a, b, unseen

    def predict(self, x, z0, units, keys):
        xa = np.asarray(x, dtype=np.float64) - self.xbar(units, keys[C.SEASON_KEY])
        a, b, unseen = self.coefficients(units)
        self.info["predict_rows_on_pooled_map"] = int(unseen)
        return np.asarray(z0, dtype=np.float64) + a + b * xa

    def to_json(self):
        d = super().to_json()
        d["xbar"] = self.xbar.to_json()
        d["per_unit"] = {u: {"a": v[0], "b": v[1], "n": v[2]} for u, v in sorted(self.per_unit.items())}
        return d


class F6PctRatio(MapModel):
    family = "F6"

    @classmethod
    def fit(cls, x, y, z0, link, c, ub, units, keys):
        if link != "identity":
            raise NotCalibratable("F6 is defined on the identity link only (normal x ratio, target units)")
        check_calibratable(y, keys["group"])
        m = cls(link, c, ub)
        normal = np.asarray(z0, dtype=np.float64)
        ok = normal > 0
        inc, rho = spearman_sign(x, y)
        x, y, groups = np.asarray(x, dtype=np.float64), np.asarray(y, dtype=np.float64), keys["group"].astype(str).to_numpy()
        r = np.zeros_like(y)
        r[ok] = y[ok] / normal[ok]
        m.pooled = Iso.fit(x[ok], r[ok], inc, rho)
        m.groups: Dict[str, Iso] = {}
        for g in sorted(set(groups[ok].tolist())):
            sel = ok & (groups == g)
            if int(sel.sum()) >= C.MIN_FIT_ROWS:
                m.groups[g] = Iso.fit(x[sel], r[sel], inc, rho)
        m.info = {"rows_with_positive_normal": int(ok.sum()), "groups_own_map": len(m.groups),
                  "pooled": m.pooled.to_json()}
        return m

    def predict(self, x, z0, units, keys):
        x = np.asarray(x, dtype=np.float64)
        groups = keys["group"].astype(str).to_numpy()
        ratio = self.pooled(x)
        for g, iso in self.groups.items():
            sel = groups == g
            if sel.any():
                ratio[sel] = iso(x[sel])
        return np.asarray(z0, dtype=np.float64) * ratio

    def to_json(self):
        d = super().to_json()
        d["groups"] = {g: iso.to_json() for g, iso in sorted(self.groups.items())}
        return d


FAMILIES = {"F0": F0Native, "F1": F1LinLink, "F2": F2IsoRaw, "F3": F3LinAnom, "F4": F4IsoAnom, "F5": F5UnitMos,
            "F6": F6PctRatio}


def fit(family: str, x, y, z0, link, c, ub, units, keys) -> MapModel:
    if family not in FAMILIES:
        raise KeyError("unknown family %r" % family)
    return FAMILIES[family].fit(x, y, z0, link, c, ub, units, keys)


def fit_l1(family: str, x, y, z0, link, c, ub, units, keys) -> MapModel:
    """The printed L1 map of a pick (Q13): the L1 isotonic version of the raw form (F0 / F1 / F2 picks) or of the
    anomaly form (F3 / F4 / F5 picks), same stat and link (identity for an F0 pick)."""
    lk = link or "identity"
    if family in ("F0", "F1", "F2"):
        m = F2IsoRaw.fit(x, y, z0, lk, c, ub, units, keys, loss="l1")
        m.info["l1_of"] = family
        return m
    m = F4IsoAnom.fit(x, y, z0, lk, c, ub, units, keys, loss="l1")
    m.info["l1_of"] = family
    return m


def candidate_id(stat: str, family: str, link: Optional[str]) -> str:
    return "%s__%s__%s" % (stat[len(C.X_PREFIX):] if stat.startswith(C.X_PREFIX) else stat, family,
                           link or "native")


def candidates(rival: Mapping[str, Any], links: Sequence[str]) -> List[Dict[str, Any]]:
    """Every candidate of an index rival in the fixed order (stat order, family F0..F6, R22 link order)."""
    out = []
    rl = rival.get("links")
    use_links = [l for l in links if (not rl or rl == "all" or l in rl)]
    for si, stat in enumerate(rival["stats"]):
        for f in rival.get("families") or []:
            fi = C.FAMILY_ORDER.index(f)
            for li, link in enumerate([None] if f == "F0" else use_links):
                out.append({"id": candidate_id(stat, f, link), "stat": stat, "family": f, "link": link,
                            "order": [si, fi, li]})
    return out
