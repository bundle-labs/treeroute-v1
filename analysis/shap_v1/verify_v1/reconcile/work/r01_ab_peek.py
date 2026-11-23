"""Exploration (no official file): flatten A's and B's results.json and list the A-vs-B differences."""
import json, math, collections, sys

V = r"D:\treeroute\analysis\shap_v1\verify_v1"
TOL = 1e-9
SKIP_TOP = {"choices", "software", "written_at", "implementer", "notes", "schema_version"}
SKIP_KEYS = {"extra", "path", "region_source", "sha256_covers", "npz", "test_set_records", "log_file"}
ORDERED = {"ranking", "main_ranking", "regions_in_draw_order", "models", "main_set", "declined_by_guard", "shape"}
TOPK = {"top10", "top3", "treeroute_top3", "consensus_top3"}
SETS = {"J", "structural_zeros", "top20_union", "sign_union_top10", "sign_determined_both", "global_indices",
        "test_set_columns", "rivals", "models_covered", "declined", "context_columns_summed",
        "rows_only_in_main", "rows_only_in_b1", "players_only_in_main", "players_only_in_b1",
        "variables_only_in_main", "variables_only_in_b1", "duplicates_merged_main", "duplicates_merged_b1"}


def flatten(o, path, out):
    if isinstance(o, dict):
        for k, v in o.items():
            if k in SKIP_KEYS or k.endswith("_why"):
                continue
            flatten(v, path + (k,), out)
    elif isinstance(o, list):
        k = path[-1]
        if k in TOPK:
            out["/".join(path)] = ("topk", [x[0] for x in o], [x[1] for x in o])
        elif k in SETS:
            out["/".join(path)] = ("set", sorted(o))
        else:
            out["/".join(path)] = ("list", list(o))
    else:
        out["/".join(path)] = ("leaf", o)


def load(X):
    with open(V + "\\" + X + "\\results.json", encoding="utf-8") as f:
        R = json.load(f)
    out = {}
    for k, v in R.items():
        if k in SKIP_TOP:
            continue
        flatten(v, (k,), out)
    return out


def num_eq(a, b, exact=False):
    if a is None or b is None:
        return a is None and b is None
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b or a == b and type(a) == type(b)
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if exact:
            return a == b
        d = abs(a - b)
        return d <= TOL or d <= TOL * max(abs(a), abs(b))
    return a == b


def eq(key, x, y):
    if x[0] != y[0]:
        return False
    if x[0] == "leaf":
        return num_eq(x[1], y[1], exact=key.endswith("/n_finite"))
    if x[0] == "set":
        return x[1] == y[1]
    if x[0] == "list":
        return x[1] == y[1]
    if x[0] == "topk":
        return x[1] == y[1] and len(x[2]) == len(y[2]) and all(num_eq(a, b) for a, b in zip(x[2], y[2]))


A = load("A")
B = load("B")
print("A keys", len(A), "B keys", len(B))
onlyA = sorted(set(A) - set(B))
onlyB = sorted(set(B) - set(A))
print("only in A:", len(onlyA))
print("only in B:", len(onlyB))


def pattern(k):
    parts = k.split("/")
    out = []
    for i, p in enumerate(parts):
        if i > 0 and parts[i - 1] in ("players", "pairs", "models", "stability", "variable_family", "family_shares",
                                      "consensus_shares", "main_shares", "spearman_top20_union_per_rival",
                                      "own_history_share_per_rival", "links", "families", "checks_passed",
                                      "duplicates_merged", "problems", "b1"):
            out.append("<%s>" % parts[i - 1])
        else:
            out.append(p)
    return "/".join(out)


cA = collections.Counter(pattern(k) for k in onlyA)
cB = collections.Counter(pattern(k) for k in onlyB)
print("--- only-in-A patterns")
for k, v in cA.most_common(60):
    print(v, k)
print("--- only-in-B patterns")
for k, v in cB.most_common(60):
    print(v, k)
mm = [k for k in sorted(set(A) & set(B)) if not eq(k, A[k], B[k])]
print("common keys", len(set(A) & set(B)), "mismatching", len(mm))
cM = collections.Counter(pattern(k) for k in mm)
for k, v in cM.most_common(80):
    print(v, k)
show = int(sys.argv[1]) if len(sys.argv) > 1 else 40
for k in mm[:show]:
    print(k, "A=", str(A[k])[:150], "B=", str(B[k])[:150])
