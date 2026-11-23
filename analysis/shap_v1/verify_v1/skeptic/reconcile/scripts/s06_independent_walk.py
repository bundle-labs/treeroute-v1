"""Skeptic: an independent walk of A's and B's results.json (not the reconciler's flatten), to find anything the
reconciler's flatten drops or merges:
  - interval objects with keys besides value, ci_low, ci_high, n_finite and *_why;
  - keys the reconciler skips by name (SKIP_KEYS) and what they hold;
  - every leaf on which A and B differ (exact for non-floats, 1e-12 relative/absolute for floats), and the paths
    present in one file only;
  - the reconciler's flattened key sets: keys in A only, in B only.
Writes nothing but stdout."""
import json
import math
import os
import sys
import collections

V = r"D:\treeroute\analysis\shap_v1\verify_v1"
IV = {"value", "ci_low", "ci_high", "n_finite"}
SKIP = {"extra", "path", "region_source", "sha256_covers", "npz", "test_set_records", "log_file",
        "models_covered_why", "numbers_why"}


def load(X):
    with open(os.path.join(V, X, "results.json"), encoding="utf-8") as f:
        return json.load(f)


def walk(o, path, out, odd, skipped):
    if isinstance(o, dict):
        ks = set(o.keys())
        if IV <= ks:
            extra = [k for k in ks - IV if not k.endswith("_why")]
            if extra:
                odd.append(("/".join(path), sorted(extra)))
        for k, v in o.items():
            if k in SKIP:
                skipped[k].append("/".join(path + (k,)))
            walk(v, path + (k,), out, odd, skipped)
    elif isinstance(o, list):
        if o and all(isinstance(x, list) for x in o):
            for i, x in enumerate(o):
                walk(x, path + ("[%d]" % i,), out, odd, skipped)
        else:
            out["/".join(path)] = ("list", o)
    else:
        out["/".join(path)] = ("leaf", o)


RA, RB = load("A"), load("B")
fa, fb = {}, {}
odd_a, odd_b = [], []
sk_a, sk_b = collections.defaultdict(list), collections.defaultdict(list)
for k in RA:
    walk(RA[k], (k,), fa, odd_a, sk_a)
for k in RB:
    walk(RB[k], (k,), fb, odd_b, sk_b)
print("leaves: A %d, B %d" % (len(fa), len(fb)))
print("interval objects with extra keys: A %d, B %d" % (len(odd_a), len(odd_b)))
for x in (odd_a + odd_b)[:20]:
    print("   ", x)
print("skipped-by-name keys, A:", {k: len(v) for k, v in sk_a.items()}, "B:", {k: len(v) for k, v in sk_b.items()})
# what the skipped keys hold (A), first few per name
for k, lst in sk_a.items():
    for p in lst[:3]:
        node = RA
        for part in p.split("/"):
            node = node[part] if isinstance(node, dict) else node
        s = json.dumps(node)
        print("   A skipped %s: %s" % (p, s[:160]))


def is_float(x):
    return isinstance(x, float)


def eq(x, y):
    if x[0] != y[0]:
        return False
    a, b = x[1], y[1]
    if x[0] == "list":
        if len(a) != len(b):
            return False
        return all(eq(("leaf", u), ("leaf", v)) for u, v in zip(a, b))
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if a == b:
            return True
        d = abs(a - b)
        return d <= 1e-12 or d <= 1e-12 * max(abs(a), abs(b))
    return a == b


ignore_top = ("choices/", "software/", "written_at", "implementer", "notes", "schema_version")
only_a = sorted(k for k in fa if k not in fb and not k.startswith(ignore_top) and not k.split("/")[-1].endswith("_why")
                and "/extra" not in k)
only_b = sorted(k for k in fb if k not in fa and not k.startswith(ignore_top) and not k.split("/")[-1].endswith("_why")
                and "/extra" not in k)
diffs = [k for k in fa if k in fb and not k.startswith(ignore_top) and not k.split("/")[-1].endswith("_why")
         and "/extra" not in k and not eq(fa[k], fb[k])]
print("leaf paths only in A: %d; only in B: %d; differing: %d" % (len(only_a), len(only_b), len(diffs)))


def pat(k):
    parts = k.split("/")
    out = []
    for i, p in enumerate(parts):
        if i and parts[i - 1] in ("players", "pairs", "models", "stability", "variable_family", "family_shares",
                                  "consensus_shares", "main_shares", "spearman_top20_union_per_rival",
                                  "own_history_share_per_rival", "problems", "b1", "links", "families"):
            out.append("<*>")
        elif p.startswith("["):
            out.append("[i]")
        else:
            out.append(p)
    return "/".join(out)


for name, lst in (("only A", only_a), ("only B", only_b), ("differ", diffs)):
    c = collections.Counter(pat(k) for k in lst)
    print("==", name)
    for pt, n in c.most_common(60):
        print("   %6d %s" % (n, pt))
print("== differing leaves outside the known groups (feature tv_family_shares, empty families, test_set_columns):")
for k in diffs:
    if "tv_family_shares" in k or "test_set_columns" in k:
        continue
    if "family_shares/own_history" in k and k.startswith("problems/coral"):
        continue
    if "family_shares/context_and_calendar" in k and k.startswith("problems/defo"):
        continue
    if k.startswith("problems/coral/main_row/own_history_share"):
        continue
    print("   ", k, json.dumps(fa[k])[:150], "|", json.dumps(fb[k])[:150])
for k in only_a + only_b:
    if "tv_family_shares" in k:
        continue
    print("   one-side:", k, json.dumps(fa.get(k))[:150], "|", json.dumps(fb.get(k))[:150])

# test_set_records (skipped by the reconciler): equal?
for p in ("coral", "defo", "fire", "pm25", "ndvi"):
    ta = RA["problems"][p]["levels"]["variable"]["families"].get("test_set_records")
    tb = RB["problems"][p]["levels"]["variable"]["families"].get("test_set_records")
    ca = RA["problems"][p]["levels"]["variable"]["families"].get("test_set_columns")
    cb = RB["problems"][p]["levels"]["variable"]["families"].get("test_set_columns")
    print("test_set_records", p, "A=", ta, "B=", tb, "equal:", ta == tb)
    print("   test_set_columns A-only:", sorted(set(ca) - set(cb))[:12], "B-only:", sorted(set(cb) - set(ca))[:12],
          "n A %d n B %d" % (len(ca), len(cb)))
