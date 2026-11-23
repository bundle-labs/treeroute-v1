"""Exploration: list the schema paths whose value is an interval object (possibly nullable)."""
import json

V = r"D:\treeroute\analysis\shap_v1\verify_v1"
with open(V + r"\spec\results_schema.json", encoding="utf-8") as f:
    S = json.load(f)
D = S["definitions"]


def refs(node):
    """Return the set of definition names this node can be (via $ref, anyOf, oneOf)."""
    out = set()
    if not isinstance(node, dict):
        return out
    if "$ref" in node:
        out.add(node["$ref"].split("/")[-1])
    for k in ("anyOf", "oneOf", "allOf"):
        for sub in node.get(k, []):
            out |= refs(sub)
    return out


found = {}
for dn, dv in D.items():
    props = dv.get("properties", {})
    for pn, pv in props.items():
        r = refs(pv)
        if "interval" in r:
            found.setdefault(dn, []).append(pn)
    ap = dv.get("additionalProperties")
    if isinstance(ap, dict) and "interval" in refs(ap):
        found.setdefault(dn, []).append("<additionalProperties>")
    pp = dv.get("patternProperties", {})
    for pat, pv in pp.items():
        if "interval" in refs(pv):
            found.setdefault(dn, []).append("<pattern %s>" % pat)
for dn, v in found.items():
    print(dn, ":", v)
print("--- main_row props:", list(D["main_row"]["properties"].keys()))
print("--- pair props:", list(D["pair"]["properties"].keys()))
print("--- pair_b1 props:", list(D["pair_b1"]["properties"].keys()))
print("--- family_shares:", json.dumps(D["family_shares"])[:600])
print("--- families:", json.dumps(D["families"])[:900])
print("--- per_problem:", json.dumps(D["per_problem"])[:900])
print("--- nz_model:", list(D["nz_model"]["properties"].keys()))
print("--- b1_run:", list(D["b1_run"]["properties"].keys()))
print("--- b1_identity:", list(D["b1_identity"]["properties"].keys()))
print("--- b1_status:", list(D["b1_status"]["properties"].keys()))
print("--- b1_importance_feature:", list(D["b1_importance_feature"]["properties"].keys()))
print("--- b1_level_variable:", list(D["b1_level_variable"]["properties"].keys()))
print("--- draws:", list(D["draws"]["properties"].keys()))
