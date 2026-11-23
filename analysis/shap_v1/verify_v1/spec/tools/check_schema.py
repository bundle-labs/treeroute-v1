# Round 14 spec: structural sanity check of V\spec\results_schema.json (no jsonschema package for meta-validation).
# Checks: every $ref resolves; every "type" name is a draft-07 type; in an object schema with
# additionalProperties false, every required key is declared in properties. Run: py -3.9 -I -B check_schema.py
import json
import os
import re
import sys

PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results_schema.json")
TYPES = {"object", "array", "string", "number", "integer", "boolean", "null"}


def main():
    with open(PATH, "r", encoding="utf-8") as f:
        s = json.load(f)
    probs, counts = [], {"refs": 0}

    def resolve(r):
        n = s
        for p in r[2:].split("/"):
            n = n[p]
        return n

    def walk(x, path):
        if isinstance(x, dict):
            if "$ref" in x:
                counts["refs"] += 1
                try:
                    resolve(x["$ref"])
                except (KeyError, TypeError):
                    probs.append(("unresolved $ref", path, x["$ref"]))
            t = x.get("type")
            if t is not None:
                for tt in (t if isinstance(t, list) else [t]):
                    if tt not in TYPES:
                        probs.append(("unknown type", path, tt))
            if x.get("additionalProperties") is False and "required" in x:
                declared = set(x.get("properties", {}))
                pats = list(x.get("patternProperties", {}))
                for r in x["required"]:
                    if r not in declared and not any(re.search(p, r) for p in pats):
                        probs.append(("required key not declared", path, r))
            for k, v in x.items():
                if k in ("properties", "patternProperties", "definitions"):
                    for kk, vv in v.items():
                        walk(vv, path + "/" + k + "/" + kk)
                elif k not in ("enum", "const", "required"):
                    walk(v, path + "/" + k)
        elif isinstance(x, list):
            for i, v in enumerate(x):
                walk(v, "%s[%d]" % (path, i))

    walk(s, "#")
    print("schema:", s.get("$schema"), "| definitions:", len(s.get("definitions", {})), "| $refs:", counts["refs"])
    print("problems:", probs if probs else "none")
    return 1 if probs else 0


if __name__ == "__main__":
    sys.exit(main())
