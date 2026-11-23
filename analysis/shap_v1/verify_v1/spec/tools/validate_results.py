# Round 14: format validator for V\<X>\results.json (and, optionally, V\<X>\draws\*.npz).
# FORMAT ONLY: it checks keys, types, nulls with their _why, list order, pair keys and the per-draw files'
# finite counts. It computes no statistic and judges no value.
# jsonschema is not installed, so this file carries a small draft-07 validator (the keywords the schema uses).
#
# Usage:
#   py -3.9 -I -B validate_results.py --results V\A\results.json [--draws V\A\draws] [--shap D:\treeroute\analysis\shap_v1]
#   py -3.9 -I -B validate_results.py --selftest
# --shap compares problems.<p>.models/main_set/declined_by_guard/links/rows and draws.sha256_per_lead with
# per_lead.json's structural keys only (nothing else of per_lead.json is read or printed).
import argparse
import io
import itertools
import json
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMA_PATH = os.path.join(os.path.dirname(HERE), "results_schema.json")
P5 = ["coral", "defo", "fire", "pm25", "ndvi"]
IV_KEYS = ("value", "ci_low", "ci_high", "n_finite")
PER_PLAYER = ("I", "share", "signed_mean")
STRUCT_KEYS = ("models", "main_set", "declined_by_guard", "links", "rows")


# ---------------------------------------------------------------- strict JSON
def _reject_constant(name):
    raise ValueError("non-JSON number token %r (NaN/Infinity are not allowed; use null + _why)" % name)


def load_strict(path):
    with open(path, "rb") as f:
        raw = f.read()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError("file starts with a UTF-8 BOM")
    return json.loads(raw.decode("utf-8"), parse_constant=_reject_constant)


# ---------------------------------------------------------------- draft-07 subset
class TypeErr(str):
    pass


def _is_num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _type_ok(x, t):
    if t == "object":
        return isinstance(x, dict)
    if t == "array":
        return isinstance(x, list)
    if t == "string":
        return isinstance(x, str)
    if t == "boolean":
        return isinstance(x, bool)
    if t == "null":
        return x is None
    if t == "number":
        return _is_num(x)
    if t == "integer":
        return (isinstance(x, int) and not isinstance(x, bool)) or (isinstance(x, float) and x.is_integer())
    raise ValueError("unknown type " + t)


def _tname(x):
    return {dict: "object", list: "array", str: "string", bool: "boolean", type(None): "null"}.get(type(x), "number")


def _jeq(a, b):
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_jeq(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_jeq(x, y) for x, y in zip(a, b))
    return type(a) is type(b) and a == b if not (_is_num(a) and _is_num(b)) else a == b


class Validator(object):
    def __init__(self, schema):
        self.root = schema

    def _resolve(self, ref):
        if not ref.startswith("#/"):
            raise ValueError("only local refs: " + ref)
        node = self.root
        for part in ref[2:].split("/"):
            node = node[part.replace("~1", "/").replace("~0", "~")]
        return node

    def check(self, x, s, path="$"):
        if s is True or s == {} or (isinstance(s, dict) and set(s) <= {"description"}):
            return []
        if s is False:
            return [path + ": not allowed here"]
        if "$ref" in s:
            return self.check(x, self._resolve(s["$ref"]), path)
        errs = []
        if "type" in s:
            ts = s["type"] if isinstance(s["type"], list) else [s["type"]]
            if not any(_type_ok(x, t) for t in ts):
                return [TypeErr("%s: is %s, expected %s" % (path, _tname(x), "/".join(ts)))]
        if "const" in s and not _jeq(x, s["const"]):
            errs.append("%s: must be %r" % (path, s["const"]))
        if "enum" in s and not any(_jeq(x, e) for e in s["enum"]):
            errs.append("%s: %r not in %r" % (path, x, s["enum"]))
        if isinstance(x, dict):
            for r in s.get("required", []):
                if r not in x:
                    errs.append("%s: missing key %r" % (path, r))
            if "minProperties" in s and len(x) < s["minProperties"]:
                errs.append("%s: fewer than %d keys" % (path, s["minProperties"]))
            if "propertyNames" in s:
                for k in x:
                    errs += self.check(k, s["propertyNames"], "%s.<key %r>" % (path, k))
            props, pats, addl = s.get("properties", {}), s.get("patternProperties", {}), s.get("additionalProperties", True)
            for k, v in x.items():
                sub = "%s.%s" % (path, k)
                hit = False
                if k in props:
                    hit = True
                    errs += self.check(v, props[k], sub)
                for pat, ps in pats.items():
                    if re.search(pat, k):
                        hit = True
                        errs += self.check(v, ps, sub)
                if not hit:
                    if addl is False:
                        errs.append("%s: unexpected key %r" % (path, k))
                    elif isinstance(addl, dict):
                        errs += self.check(v, addl, sub)
        if isinstance(x, list):
            items = s.get("items")
            if isinstance(items, list):
                for i, (v, si) in enumerate(zip(x, items)):
                    errs += self.check(v, si, "%s[%d]" % (path, i))
                if len(x) > len(items) and s.get("additionalItems", True) is False:
                    errs.append("%s: more than %d items" % (path, len(items)))
            elif isinstance(items, dict):
                for i, v in enumerate(x):
                    errs += self.check(v, items, "%s[%d]" % (path, i))
            if "minItems" in s and len(x) < s["minItems"]:
                errs.append("%s: fewer than %d items" % (path, s["minItems"]))
            if "maxItems" in s and len(x) > s["maxItems"]:
                errs.append("%s: more than %d items" % (path, s["maxItems"]))
        if isinstance(x, str):
            if "minLength" in s and len(x) < s["minLength"]:
                errs.append("%s: empty string" % path)
            if "pattern" in s and not re.search(s["pattern"], x):
                errs.append("%s: %r does not match %s" % (path, x, s["pattern"]))
        if _is_num(x):
            if "minimum" in s and x < s["minimum"]:
                errs.append("%s: below %r" % (path, s["minimum"]))
            if "maximum" in s and x > s["maximum"]:
                errs.append("%s: above %r" % (path, s["maximum"]))
        for sub in s.get("allOf", []):
            errs += self.check(x, sub, path)
        if "anyOf" in s and all(self.check(x, sub, path) for sub in s["anyOf"]):
            errs.append("%s: matches none of anyOf" % path)
        if "oneOf" in s:
            res = [self.check(x, sub, path) for sub in s["oneOf"]]
            n_ok = sum(1 for r in res if not r)
            if n_ok == 0:
                real = [r for r in res if not (len(r) == 1 and isinstance(r[0], TypeErr) and r[0].startswith(path + ":"))]
                errs += (min(real, key=len) if real else [path + ": matches no branch (%s)" % "; ".join(r[0] for r in res)])
            elif n_ok > 1:
                errs.append("%s: matches %d branches of oneOf" % (path, n_ok))
        if "not" in s and not self.check(x, s["not"], path):
            errs.append("%s: must not match the 'not' schema (a key present that must be absent?)" % path)
        if "if" in s:
            if not self.check(x, s["if"], path):
                if "then" in s:
                    errs += self.check(x, s["then"], path)
            elif "else" in s:
                errs += self.check(x, s["else"], path)
        return errs


# ---------------------------------------------------------------- semantic checks
def _is_iv(d):
    return isinstance(d, dict) and all(k in d for k in IV_KEYS) and all(
        k in IV_KEYS or k.endswith("_why") for k in d)


def _sorted_ok(lst):
    return isinstance(lst, list) and all(lst[i] <= lst[i + 1] for i in range(len(lst) - 1))


# Subtrees that are free diagnostics ("extra") or verbatim copies of meta.json objects are not checked.
SKIP_SUBTREES = {"extra", "checks_passed", "duplicates_merged"}


def _walk(node, path, fn):
    fn(node, path)
    if isinstance(node, dict):
        for k, v in node.items():
            if k in SKIP_SUBTREES:
                continue
            _walk(v, path + [k], fn)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            _walk(v, path + ["[%d]" % i], fn)


SORTED_KEYS = {"J", "structural_zeros", "top20_union", "sign_union_top10", "sign_determined_both", "global_indices",
               "test_set_columns", "rivals", "models_covered", "declined", "rows_only_in_main", "rows_only_in_b1",
               "players_only_in_main", "players_only_in_b1", "variables_only_in_main", "variables_only_in_b1",
               "duplicates_merged_main", "duplicates_merged_b1", "context_columns_summed"}


def semantic(res, errs, warns):
    def visit(node, path):
        if _is_iv(node):
            lo, hi = node["ci_low"], node["ci_high"]
            if lo is not None and hi is not None and lo > hi:
                errs.append("%s: ci_low > ci_high" % "/".join(path))
            if (lo is None) != (hi is None):
                warns.append("%s: only one interval end is null" % "/".join(path))
        if isinstance(node, dict):
            for k, v in node.items():
                if k in SORTED_KEYS and isinstance(v, list) and not _sorted_ok(v):
                    errs.append("%s: list %r is not sorted ascending" % ("/".join(path), k))
                if v is None and not k.endswith("_why") and (k + "_why") not in node:
                    errs.append("%s: %r is null without %r" % ("/".join(path), k, k + "_why"))
    _walk(res, [], visit)

    for p in P5:
        pr = res["problems"][p]
        models = pr["models"]
        want_pairs = set("|".join(sorted(c)) for c in itertools.combinations(models, 2))
        for L in ("feature", "variable"):
            lv = pr["levels"][L]
            base = "problems/%s/levels/%s" % (p, L)
            if set(lv["models"]) != set(models):
                errs.append("%s/models: keys %s differ from per-problem models %s" % (base, sorted(lv["models"]), models))
            if set(lv["pairs"]) != want_pairs:
                errs.append("%s/pairs: missing %s, unexpected %s" % (
                    base, sorted(want_pairs - set(lv["pairs"])), sorted(set(lv["pairs"]) - want_pairs)))
            for k, pair in lv["pairs"].items():
                a, b = k.split("|")
                if a > b:
                    errs.append("%s/pairs/%s: names not in alphabetical order" % (base, k))
                if pair.get("models") != [a, b]:
                    errs.append("%s/pairs/%s: models %r differ from the key" % (base, k, pair.get("models")))
                dec = sorted(m for m in (a, b) if m in pr["declined_by_guard"])
                if pair.get("declined") != dec:
                    errs.append("%s/pairs/%s: declined %r, per-problem declined_by_guard gives %r" % (base, k, pair.get("declined"), dec))
                both = a in pr["main_set"] and b in pr["main_set"]
                if pair.get("both_in_main_set") != both:
                    errs.append("%s/pairs/%s: both_in_main_set disagrees with main_set" % (base, k))
                same = pr["links"].get(a) == pr["links"].get(b)
                if (pair.get("link_class") == "same-link") != same:
                    warns.append("%s/pairs/%s: link_class %r while the two links strings are %s" % (
                        base, k, pair.get("link_class"), "equal" if same else "different"))
            J = set(lv["active_set"]["J"])
            for m, ml in lv["models"].items():
                if set(ml["ranking"]) != J:
                    warns.append("%s/models/%s: ranking is not a permutation of J (%d vs %d names)" % (base, m, len(ml["ranking"]), len(J)))
                if ml.get("top10") is not None:
                    names = [t[0] for t in ml["top10"]]
                    if names != ml["ranking"][:len(names)]:
                        warns.append("%s/models/%s: top10 names differ from the ranking's first names" % (base, m))
            st = lv["per_problem"]["stability"]
            if set(k for k in st if not k.endswith("_why")) != set(models):
                errs.append("%s/per_problem/stability: keys differ from models" % base)
            for m, v in st.items():
                if v is None and (m + "_why") not in st:
                    errs.append("%s/per_problem/stability/%s: null without _why" % (base, m))
        mr = pr["main_row"]
        if mr["main_set"] != pr["main_set"]:
            errs.append("problems/%s/main_row/main_set differs from main_set" % p)
        nz = pr["nonzero_forecast"]
        if set(nz["models"]) != set(nz["models_covered"]):
            errs.append("problems/%s/nonzero_forecast: models keys differ from models_covered" % p)
        if not set(nz["models_covered"]) <= set(models):
            errs.append("problems/%s/nonzero_forecast: models_covered not in models" % p)
        if "treeroute_B1" in models:
            warns.append("problems/%s/models lists treeroute_B1" % p)
    for p in P5:
        b = res["b1"][p]
        if b["status"]["numbers"] == "full":
            for L in ("feature", "variable"):
                pj = set(b[L]["pair_main_b1"]["J"])
                if set(b[L]["importance"]["ranking"]) != pj:
                    warns.append("b1/%s/%s: importance ranking is not a permutation of the pair's J" % (p, L))
                if set(b[L]["pair_main_b1"]["main_ranking"]) != pj:
                    warns.append("b1/%s/%s: main_ranking is not a permutation of the pair's J" % (p, L))


def check_per_lead(res, shap, errs):
    for p in P5:
        pl_path = os.path.join(shap, "out", p, "lead_0", "compare", "per_lead.json")
        with open(pl_path, "r", encoding="utf-8") as f:
            pl = json.load(f)
        pr = res["problems"][p]
        for k in STRUCT_KEYS:
            if k in pl and pr.get(k) != pl[k]:
                errs.append("problems/%s/%s differs from per_lead.json key %s" % (p, k, k))
        if "draws_sha256" in pl and pr["draws"]["sha256_per_lead"] != pl["draws_sha256"]:
            errs.append("problems/%s/draws/sha256_per_lead differs from per_lead.json key draws_sha256" % p)
        del pl


# ---------------------------------------------------------------- per-draw files
def _collect(node, path, scalars, playermaps):
    if isinstance(node, dict):
        for k, v in node.items():
            if k in SKIP_SUBTREES:
                continue
            if k == "players" and isinstance(v, dict) and v and all(
                    isinstance(e, dict) and "I" in e for kk, e in v.items() if not kk.endswith("_why")):
                playermaps.append((path + ["players"], v))
            elif _is_iv(v):
                if v["n_finite"] is not None:
                    scalars.append((path + [k], v))
            else:
                _collect(v, path + [k], scalars, playermaps)


def check_npz_obj(z, label, subtree, errs, n_draws=2000):
    scalars, pmaps = [], []
    _collect(subtree, [], scalars, pmaps)
    files = set(z.files)
    for path, iv in scalars:
        key = "/".join(path)
        if key not in files:
            errs.append("%s: no entry %r for an interval with n_finite=%r" % (label, key, iv["n_finite"]))
            continue
        a = z[key]
        if a.shape != (n_draws,):
            errs.append("%s:%s: shape %r, expected (%d,)" % (label, key, a.shape, n_draws))
            continue
        nf = int(np.isfinite(a).sum())
        if nf != iv["n_finite"]:
            errs.append("%s:%s: %d finite values, results.json says %d" % (label, key, nf, iv["n_finite"]))
    for path, pm in pmaps:
        key = "/".join(path)
        need = [key + "/names"] + [key + "/" + s for s in PER_PLAYER]
        wants = any(pm[j][s]["n_finite"] is not None for j in pm if not j.endswith("_why") for s in PER_PLAYER)
        if not wants:
            continue
        miss = [n for n in need if n not in files]
        if miss:
            errs.append("%s: missing entries %r" % (label, miss))
            continue
        names = [str(x) for x in z[key + "/names"]]
        col = {n: i for i, n in enumerate(names)}
        for s in PER_PLAYER:
            a = z[key + "/" + s]
            if a.shape != (n_draws, len(names)):
                errs.append("%s:%s/%s: shape %r, expected (%d, %d)" % (label, key, s, a.shape, n_draws, len(names)))
                continue
            fin = np.isfinite(a).sum(axis=0)
            for j, e in pm.items():
                if j.endswith("_why") or e[s]["n_finite"] is None:
                    continue
                if j not in col:
                    errs.append("%s:%s/names lacks %r" % (label, key, j))
                    continue
                if int(fin[col[j]]) != e[s]["n_finite"]:
                    errs.append("%s:%s/%s[%r]: %d finite, results.json says %d" % (
                        label, key, s, j, int(fin[col[j]]), e[s]["n_finite"]))


def check_npz_dir(res, draws_dir, errs):
    for p in P5:
        f = os.path.join(draws_dir, p + ".npz")
        if not os.path.exists(f):
            errs.append("missing per-draw file %s" % f)
        else:
            with np.load(f, allow_pickle=False) as z:
                check_npz_obj(z, p + ".npz", res["problems"][p], errs)
        if res["b1"][p]["status"]["numbers"] == "full":
            f = os.path.join(draws_dir, "b1_" + p + ".npz")
            if not os.path.exists(f):
                errs.append("missing per-draw file %s" % f)
            else:
                with np.load(f, allow_pickle=False) as z:
                    check_npz_obj(z, "b1_" + p + ".npz", res["b1"][p], errs)


def run_all(res, schema, draws_dir=None, shap=None, npz_objs=None):
    errs, warns = [], []
    errs += [str(e) for e in Validator(schema).check(res, schema)]
    if not errs:
        semantic(res, errs, warns)
        if shap:
            check_per_lead(res, shap, errs)
        if draws_dir:
            check_npz_dir(res, draws_dir, errs)
        if npz_objs:
            for label, (z, subtree) in npz_objs.items():
                check_npz_obj(z, label, subtree, errs)
    return errs, warns


# ---------------------------------------------------------------- self-test (synthetic, no real data)
def _iv(v=0.5, n=2000):
    return {"value": v, "ci_low": v - 0.1, "ci_high": v + 0.1, "n_finite": n}


def _iv_noci(v):
    return {"value": v, "ci_low": None, "ci_high": None, "n_finite": None,
            "ci_low_why": "synthetic: no interval", "ci_high_why": "synthetic: no interval",
            "n_finite_why": "synthetic: no interval"}


def _players(names):
    return {n: {"I": _iv(), "share": _iv(), "signed_mean": _iv(), "sign_determined": True} for n in names}


FAM = ["own_history", "global_indices", "local_drivers", "context_and_calendar", "seasonal_normal"]


def _pairstats():
    d = {k: _iv() for k in ["spearman_J", "spearman_top20_union", "kendall_tau_b", "jaccard_top5", "jaccard_top10",
                            "rbo_p090", "rbo_p095", "tv_shares", "tv_family_shares", "sign_agreement",
                            "sign_n_determined", "sign_n_agree"]}
    d.update({"jaccard_top20": None, "jaccard_top20_why": "synthetic: J below 200",
              "top20_union": ["p1", "p2"], "sign_union_top10": ["p1", "p2"], "sign_determined_both": ["p1"]})
    return d


def synthetic():
    models = ["m_a", "m_b", "treeroute"]
    links = {"m_a": "identity|c=-|ub=1", "m_b": "log_c|c=1|ub=-", "treeroute": "identity|c=-|ub=1"}
    names = ["p1", "p2"]

    def level(variable):
        ms = {}
        for m in models:
            ms[m] = {"players": _players(names), "n_nonzero": _iv_noci(2), "ranking": names,
                     "top10": [["p1", 0.6], ["p2", 0.4]]}
            if variable:
                ms[m]["family_shares"] = dict((f, _iv()) for f in FAM)
        pairs = {}
        for a, b in itertools.combinations(sorted(models), 2):
            d = {"models": [a, b], "link_class": "same-link" if links[a] == links[b] else "cross-link",
                 "declined": [], "both_in_main_set": a in ("m_a", "treeroute") and b in ("m_a", "treeroute")}
            if links[a] != links[b]:
                d["cross_link_label"] = "not comparable in scale or rank"
            d.update(_pairstats())
            pairs[a + "|" + b] = d
        lv = {"active_set": {"J": names, "n_J": _iv_noci(2), "structural_zeros": ["p3"]},
              "models": ms, "pairs": pairs,
              "per_problem": {"kendall_w": _iv(), "kendall_w_m": 2, "kendall_w_n": 2,
                              "mean_pairwise_spearman": _iv(), "stability": dict((m, _iv()) for m in models)}}
        if variable:
            lv["families"] = {"variable_family": {"p1": "own_history", "p2": "local_drivers"},
                              "global_indices": [], "test_set_records": ["SHAP\\synthetic"], "test_set_columns": ["c"]}
        return lv

    def problem():
        return {"lead": 0, "models": models, "main_set": ["m_a", "treeroute"], "declined_by_guard": [],
                "links": links, "rows": 1000,
                "draws": {"path": "SHAP\\x.npy", "shape": [2000, 3], "dtype": "int64", "sha256_computed": "0" * 64,
                          "sha256_covers": "synthetic", "sha256_per_lead": "0" * 64, "sha256_match": True,
                          "region_source": "synthetic", "regions_in_draw_order": ["r1", "r2", "r3"],
                          "npz": "V\\A\\draws\\x.npz"},
                "levels": {"feature": level(False), "variable": level(True)},
                "main_row": {"level": "variable", "main_set": ["m_a", "treeroute"], "rivals": ["m_a"],
                             "kendall_w": _iv(), "spearman_top20_union_median": _iv(),
                             "spearman_top20_union_min": _iv_noci(0.5), "spearman_top20_union_max": _iv_noci(0.5),
                             "spearman_top20_union_per_rival": {"m_a": 0.5}, "rbo_p090_vs_consensus": _iv(),
                             "consensus_shares": {"p1": 0.6, "p2": 0.4},
                             "treeroute_top3": [["p1", 0.6], ["p2", 0.4]], "consensus_top3": [["p1", 0.6], ["p2", 0.4]],
                             "own_history_share_treeroute": _iv(), "own_history_share_median_rival": _iv(),
                             "own_history_share_per_rival": {"m_a": 0.5}, "median_rival_name": None,
                             "median_rival_name_why": "synthetic"},
                "nonzero_forecast": {"models_covered": [], "models_covered_why": "synthetic", "models": {}}}

    def run_facts():
        return {"log_file": "SHAP\\logs\\x.log", "log_setup_line_number": 1, "log_done_line_number": 2,
                "pairs_log": 16, "pairs_meta": 16, "total_seconds_log": 1.5, "total_seconds_done_json": 1.5,
                "tree_shap_seconds_log": 1.0, "tree_shap_seconds_meta": 1.0}

    def b1_full():
        def b1lev(variable):
            pb = {"pair": "treeroute|treeroute_B1", "J": names, "n_J": _iv_noci(2),
                  "main_shares": {"p1": 0.6, "p2": 0.4}, "main_ranking": names}
            pb.update(_pairstats())
            imp = {"players": _players(names), "n_nonzero": _iv_noci(2), "ranking": names}
            d = {"importance": imp, "top10": [["p1", 0.6], ["p2", 0.4]], "pair_main_b1": pb}
            if variable:
                d.update({"families": dict((f, _iv()) for f in FAM), "top3": [["p1", 0.6], ["p2", 0.4]],
                          "own_history_share": _iv()})
            else:
                imp["n_nonzero_before_merge"] = _iv_noci(2)
            return d
        run = run_facts()
        run.update({"duplicates_merged_main": [], "duplicates_merged_b1": [], "context_columns_summed": [],
                    "draws_sha256_match": True, "npz": "V\\A\\draws\\b1_x.npz"})
        return {"status": status("full"), "run": run, "feature": b1lev(False), "variable": b1lev(True)}

    def status(numbers):
        return {"folder_exists": numbers != "none", "has_done_json": numbers != "none", "has_failed_json": False,
                "finished": numbers != "none", "failed_stop": None, "failed_stop_why": "synthetic",
                "meta": None, "meta_why": "synthetic", "background_is_B1": None, "background_is_B1_why": "synthetic",
                "sample_sha256_registered": None, "sample_sha256_registered_why": "synthetic",
                "sample_sha256_is_registered": None, "sample_sha256_is_registered_why": "synthetic",
                "per_lead_models_lists_treeroute_B1": False, "numbers": numbers, "numbers_why": "synthetic"}

    ident = {"max_abs_diff_phi": 0.0, "max_abs_diff_phiv": 0.0, "same_rows": True, "same_players": True,
             "same_variables": True, "n_rows_main": 1000, "n_rows_b1": 1000, "n_players_main": 2, "n_players_b1": 2,
             "n_variables_main": 2, "n_variables_b1": 2, "rows_only_in_main": [], "rows_only_in_b1": [],
             "players_only_in_main": [], "players_only_in_b1": [], "variables_only_in_main": [],
             "variables_only_in_b1": [], "as_expected": True}
    ident.update(run_facts())
    choices = dict(("C%02d" % i, "synthetic") for i in range(1, 26))
    choices.update(dict(("I%02d" % i, "synthetic") for i in range(1, 7)))
    return {"schema_version": "round14_results_v1", "implementer": "A", "written_at": "2026-11-16T12:00:00+01:00",
            "software": {"python": "3.9.13", "numpy": "2.0.2"}, "choices": choices,
            "problems": dict((p, problem()) for p in P5),
            "b1": {"coral": {"status": status("none")}, "defo": {"status": status("identity"), "identity": ident},
                   "fire": b1_full(), "pm25": b1_full(), "ndvi": b1_full()}}


def _npz_for(subtree, drop=None, nan_first=False):
    scalars, pmaps = [], []
    _collect(subtree, [], scalars, pmaps)
    arrs = {}
    for path, iv in scalars:
        a = np.zeros(2000)
        if nan_first:
            a[0] = np.nan
        arrs["/".join(path)] = a
    for path, pm in pmaps:
        key = "/".join(path)
        names = [n for n in pm if not n.endswith("_why")]
        arrs[key + "/names"] = np.array(names)
        for s in PER_PLAYER:
            arrs[key + "/" + s] = np.zeros((2000, len(names)))
    if drop:
        arrs.pop(drop, None)
    buf = io.BytesIO()
    np.savez_compressed(buf, **arrs)
    buf.seek(0)
    return np.load(buf, allow_pickle=False)


def selftest(schema):
    import copy
    ok = True
    good = synthetic()
    e, w = run_all(good, schema, npz_objs={"fire.npz": (_npz_for(good["problems"]["fire"]), good["problems"]["fire"]),
                                           "b1_fire.npz": (_npz_for(good["b1"]["fire"]), good["b1"]["fire"])})
    print("synthetic valid instance: %d errors, %d warnings" % (len(e), len(w)))
    for x in e[:10]:
        print("   ", x)
    ok &= not e

    def mutated(fn):
        r = copy.deepcopy(good)
        fn(r)
        return r

    cases = [
        ("interval lacks n_finite", lambda r: r["problems"]["coral"]["levels"]["feature"]["pairs"]["m_a|m_b"]["spearman_J"].pop("n_finite")),
        ("null value without value_why", lambda r: r["problems"]["coral"]["levels"]["feature"]["pairs"]["m_a|m_b"]["spearman_J"].update(value=None)),
        ("pair key not alphabetical", lambda r: r["problems"]["defo"]["levels"]["variable"]["pairs"].update(
            {"treeroute|m_a": r["problems"]["defo"]["levels"]["variable"]["pairs"].pop("m_a|treeroute")})),
        ("cross-link pair without its label", lambda r: r["problems"]["fire"]["levels"]["feature"]["pairs"]["m_a|m_b"].pop("cross_link_label")),
        ("same-link pair with a cross-link label", lambda r: r["problems"]["fire"]["levels"]["feature"]["pairs"]["m_a|treeroute"].update(cross_link_label="not comparable in scale or rank")),
        ("b1 numbers full without feature", lambda r: r["b1"]["pm25"].pop("feature")),
        ("b1 defo with numbers full", lambda r: r["b1"]["defo"]["status"].update(numbers="full")),
        ("top10 with 11 entries", lambda r: r["problems"]["ndvi"]["levels"]["feature"]["models"]["m_a"].update(top10=[["p", 0.1]] * 11)),
        ("J not sorted", lambda r: r["problems"]["ndvi"]["levels"]["feature"]["active_set"].update(J=["p2", "p1"])),
        ("missing choice C25", lambda r: r["choices"].pop("C25")),
        ("unknown top-level key", lambda r: r.update(foo=1)),
        ("ci_low above ci_high", lambda r: r["problems"]["pm25"]["levels"]["variable"]["per_problem"]["kendall_w"].update(ci_low=2.0)),
        ("stability null without why", lambda r: r["problems"]["coral"]["levels"]["feature"]["per_problem"]["stability"].update(m_a=None)),
        ("missing pair", lambda r: r["problems"]["coral"]["levels"]["feature"]["pairs"].pop("m_b|treeroute")),
        ("b1 pair key wrong", lambda r: r["b1"]["fire"]["variable"]["pair_main_b1"].update(pair="treeroute_B1|treeroute")),
        ("family key unknown", lambda r: r["problems"]["coral"]["levels"]["variable"]["families"]["variable_family"].update(p1="history")),
    ]
    for label, fn in cases:
        e, w = run_all(mutated(fn), schema)
        hit = bool(e)
        ok &= hit
        print("%-45s -> %s (%d errors)%s" % (label, "caught" if hit else "MISSED", len(e), (": " + e[0][:110]) if e else ""))
    # per-draw file checks
    fire = good["problems"]["fire"]
    e = []
    check_npz_obj(_npz_for(fire, nan_first=True), "fire.npz", fire, e)
    print("%-45s -> %s (%d errors)" % ("npz finite count differs", "caught" if e else "MISSED", len(e)))
    ok &= bool(e)
    e = []
    check_npz_obj(_npz_for(fire, drop="levels/feature/pairs/m_a|m_b/spearman_J"), "fire.npz", fire, e)
    print("%-45s -> %s (%d errors)" % ("npz entry missing", "caught" if e else "MISSED", len(e)))
    ok &= bool(e)
    try:
        json.loads('{"a": NaN}', parse_constant=_reject_constant)
        print("NaN token -> MISSED")
        ok = False
    except ValueError:
        print("%-45s -> caught" % "NaN token")
    print("SELFTEST", "PASSED" if ok else "FAILED")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results")
    ap.add_argument("--draws")
    ap.add_argument("--shap")
    ap.add_argument("--schema", default=SCHEMA_PATH)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    with open(a.schema, "r", encoding="utf-8") as f:
        schema = json.load(f)
    if a.selftest:
        return selftest(schema)
    if not a.results:
        ap.error("--results or --selftest")
    res = load_strict(a.results)
    errs, warns = run_all(res, schema, draws_dir=a.draws, shap=a.shap)
    for x in errs:
        print("ERROR", x)
    for x in warns:
        print("WARN ", x)
    print("%s: %d errors, %d warnings" % (a.results, len(errs), len(warns)))
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
