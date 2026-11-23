"""Skeptic (numbers lens): are the files every source read the files the runs wrote?
- SHA-256 of every rows.parquet vs its rows.parquet.done.json `sha256` and meta.json `rows_sha256`;
- SHA-256 of sample.parquet vs SAMPLE_REGISTER.txt and every piece's sample_sha256;
- background_keys.parquet SHA-256 vs meta.json / done.json `background_keys_sha256`;
- Kendall's W cross-check with scipy's tie-corrected Friedman statistic (W = Q / (m (n - 1))).
"""
import os, sys, json, hashlib, re
import numpy as np
from scipy.stats import friedmanchisquare
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s_lib as L

OUT = r"D:\treeroute\analysis\shap_v1\verify_v1\skeptic\numbers\work"


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


reg = open(os.path.join(L.SHAP, "SAMPLE_REGISTER.txt"), encoding="utf-8").read()
res = {}
for p in ["coral", "defo", "fire", "pm25", "ndvi"]:
    r = {}
    s_hash = sha(os.path.join(L.SHAP, "sample", p, "sample.parquet"))
    r["sample_sha256_in_register"] = s_hash in reg
    lines = [ln for ln in reg.splitlines() if ("problem=%s " % p) in ln or ln.strip().endswith("problem=%s" % p) or ("problem=%s|" % p) in ln or ("problem=%s\t" % p) in ln]
    r["register_lines_for_problem"] = len(lines)
    r["register_line_has_this_hash"] = any(s_hash in ln for ln in lines)
    r["per_lead_sample_sha256_equal"] = L.per_lead(p).get("sample_sha256") == s_hash
    mods = list(L.per_lead(p)["models"])
    if os.path.exists(os.path.join(L.piece(p, "treeroute_B1"), "rows.parquet")):
        mods.append("treeroute_B1")
    pieces = {}
    for m in mods:
        dj = json.load(open(os.path.join(L.piece(p, m), "rows.parquet.done.json"), encoding="utf-8"))
        mt = L.meta(p, m)
        h = sha(os.path.join(L.piece(p, m), "rows.parquet"))
        hb = sha(os.path.join(L.piece(p, m), "background_keys.parquet"))
        pieces[m] = dict(rows_eq_done=h == dj.get("sha256"), rows_eq_meta=h == mt.get("rows_sha256"),
                         sample_eq=(mt.get("sample_sha256") == s_hash) and (dj.get("sample_sha256") == s_hash),
                         bg_eq_meta=hb == mt.get("background_keys_sha256"), bg_eq_done=hb == dj.get("background_keys_sha256"))
    r["pieces"] = pieces
    # W cross-check (variable level, main set)
    pl = L.per_lead(p)
    if len(pl["main_set"]) >= 2:
        d, _ = L.load_draws(p)
        data, g0 = {}, None
        for m in pl["models"]:
            _, g, _, ph = L.load(p, m, "variable")
            g0 = g if g0 is None else g0
            data[m] = ph
        R = L.Regions(g0, d)
        J, _ = L.active_set(data, R)
        Is = [L.imp(data[m], J, R)["I"] for m in pl["main_set"]]
        W = L.kendall_w(Is)
        Q = friedmanchisquare(*[np.array([I[j] for I in Is]) for j in range(len(J))]).statistic
        r["W_mine"] = W
        r["W_from_scipy_friedman"] = float(Q / (len(Is) * (len(J) - 1)))
    res[p] = r
    print(p, json.dumps(r))
with open(os.path.join(OUT, "s05_hashes.json"), "w", encoding="utf-8") as f:
    json.dump(res, f, indent=1)
