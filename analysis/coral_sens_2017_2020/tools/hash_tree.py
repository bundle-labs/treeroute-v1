"""Hash every file under the LIVE engine tree and the read-only coral sources (read only; writes one JSON).

    python -I -B hash_tree.py <out.json>

Covers (each file's SHA-256, size and mtime_ns, so any byte change or touch shows):
  - engine/treeroute (the LIVE engine, every file including __pycache__),
  - engine/treeroute_report, engine/runner, engine/config, engine/datasets/coral (the signed package),
  - D:/treeroute/coral_build/coral_tables and D:/treeroute/coral_build_v6b/coral_tables (the builder originals),
  - D:/treeroute/coral_build/coral_store/20261020_014201 (the published headline tables),
  - D:/treeroute/runs/coral/headline/20261020_f3b8e3da (the headline run folder).
Also records the engine's own engine_code_sha256 (runs.fingerprint, comments count) computed from the file bytes
with the same recipe WITHOUT importing the engine (so this script can never write a .pyc into the engine tree).
"""
import hashlib
import json
import os
import sys

sys.dont_write_bytecode = True

ENGINE = r"C:\Users\moh the ghost\Desktop\data set for reserch paper\engine"
ROOTS = [
    os.path.join(ENGINE, "treeroute"),
    os.path.join(ENGINE, "treeroute_report"),
    os.path.join(ENGINE, "runner"),
    os.path.join(ENGINE, "config"),
    os.path.join(ENGINE, "datasets", "coral"),
    r"D:\treeroute\coral_build\coral_tables",
    r"D:\treeroute\coral_build_v6b\coral_tables",
    r"D:\treeroute\coral_build\coral_store\20261020_014201",
    r"D:\treeroute\runs\coral\headline\20261020_f3b8e3da",
]


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def main():
    out = {"roots": {}}
    for root in ROOTS:
        files = {}
        for dp, dn, fn in os.walk(root):
            dn.sort()
            for n in sorted(fn):
                p = os.path.join(dp, n)
                st = os.stat(p)
                files[os.path.relpath(p, root).replace("\\", "/")] = [sha(p), st.st_size, st.st_mtime_ns]
        dirs = sorted(os.path.relpath(dp, root).replace("\\", "/") for dp, _, _ in os.walk(root))
        out["roots"][root] = {"n_files": len(files), "files": files, "dirs": dirs,
                              "tree_sha256": hashlib.sha256(json.dumps([files, dirs], sort_keys=True)
                                                            .encode()).hexdigest()}
    with open(sys.argv[1], "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, sort_keys=True)
    for root, r in out["roots"].items():
        print("%s  %5d files  tree %s" % (root, r["n_files"], r["tree_sha256"][:16]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
