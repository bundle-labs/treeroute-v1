"""Compare two hash_tree.py records (read only): every file's SHA-256, size and mtime, and the folder list.

    python -I -B compare_hashes.py <before.json> <after.json>

Exit 0 when nothing was added, removed, changed or touched under any root; 1 otherwise (each difference printed).
"""
import json
import sys

a = json.load(open(sys.argv[1], encoding="utf-8"))["roots"]
b = json.load(open(sys.argv[2], encoding="utf-8"))["roots"]
bad = 0
for root in sorted(set(a) | set(b)):
    ra, rb = a.get(root), b.get(root)
    if ra is None or rb is None:
        print("ROOT %s only in %s" % (root, "after" if ra is None else "before"))
        bad += 1
        continue
    fa, fb = ra["files"], rb["files"]
    added, removed = sorted(set(fb) - set(fa)), sorted(set(fa) - set(fb))
    changed = sorted(k for k in set(fa) & set(fb) if fa[k][0] != fb[k][0] or fa[k][1] != fb[k][1])
    touched = sorted(k for k in set(fa) & set(fb) if fa[k][2] != fb[k][2] and k not in changed)
    dirs = ra["dirs"] != rb["dirs"]
    n = len(added) + len(removed) + len(changed) + len(touched) + int(dirs)
    bad += n
    print("%s  %s  files %d -> %d  tree %s -> %s%s" % ("SAME " if not n else "DIFF ", root, ra["n_files"], rb["n_files"],
                                                     ra["tree_sha256"][:16], rb["tree_sha256"][:16],
                                                     "" if not n else " | added %s removed %s changed %s touched %s "
                                                     "dirs_changed %s" % (added, removed, changed, touched, dirs)))
print("RESULT: %s" % ("UNCHANGED" if not bad else "CHANGED (%d differences)" % bad))
sys.exit(1 if bad else 0)
