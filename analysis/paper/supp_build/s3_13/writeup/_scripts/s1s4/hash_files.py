# Read-only: SHA-256, size and file times (UTC) of named files for Table S4.11 / S4.14 (Part 628).
# Opens each named file only to hash its bytes; runs nothing; writes one JSON beside this script.
import hashlib, json, os, sys, datetime

SHAP = r"D:\treeroute\analysis\shap_v1"
OUT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))

FILES = [
    ("shap", r"scripts\bardl_shap.py"),
    ("shap", r"scripts\compare_shap.py"),
    ("shap", r"scripts\make_sample.py"),
    ("shap", r"scripts\ridge_shap.py"),
    ("shap", r"scripts\rival_shap.py"),
    ("shap", r"scripts\run_shap.py"),
    ("shap", r"scripts\shapv1_common.py"),
    ("shap", r"scripts\shapv1_rows.py"),
    ("shap", r"scripts\shapv1_stats.py"),
    ("shap", r"scripts\shapv1_treeshap.py"),
    ("shap", r"scripts\tr_rebuild.py"),
    ("shap", r"scripts\tr_shap.py"),
    ("shap", r"scripts\tests\diag_coral_exactness.py"),
    ("shap", r"scripts\tests\smoke_bardl.py"),
    ("shap", r"scripts\tests\smoke_ridge.py"),
    ("shap", r"scripts\tests\smoke_unit.py"),
    ("shap", r"scripts\tests\smoke_world.py"),
    ("out", r"A\scripts\build_tables.py"),
    ("out", r"B\scripts\build_tables.py"),
    # for the table-build fact only (not printed in S4): the builders' outputs and the agreed copy
    ("out", r"A\tables.md"),
    ("out", r"B\tables.md"),
    ("out", r"reconcile\tables_agreed.md"),
    ("out", r"A\cells.json"),
    ("out", r"B\cells.json"),
    ("out", r"reconcile\cells.json"),
    ("out", r"spec\TABLE_SPEC.md"),
]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    rows = []
    for root, rel in FILES:
        base = SHAP if root == "shap" else OUT
        p = os.path.join(base, rel)
        st = os.stat(p)
        rows.append({
            "root": root,
            "rel": rel.replace("\\", "/"),
            "bytes": st.st_size,
            "mtime_utc": datetime.datetime.utcfromtimestamp(st.st_mtime).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "sha256": sha(p),
        })
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hashes_2026-11-17.json")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(rows, f, indent=1)
        f.write("\n")
    for r in rows:
        print(r["root"], r["rel"], r["bytes"], r["mtime_utc"], r["sha256"])


if __name__ == "__main__":
    main()
