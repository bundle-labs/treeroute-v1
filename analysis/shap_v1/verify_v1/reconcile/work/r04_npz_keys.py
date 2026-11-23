"""Exploration: npz key names of A and B (one problem) and a B1 file."""
import numpy as np, collections

V = r"D:\treeroute\analysis\shap_v1\verify_v1"
for X in ("A", "B"):
    for f in ("fire", "b1_fire"):
        z = np.load(V + "\\%s\\draws\\%s.npz" % (X, f), allow_pickle=False)
        keys = list(z.keys())
        pat = collections.Counter()
        for k in keys:
            parts = k.split("/")
            q = []
            for i, p in enumerate(parts):
                if i > 0 and parts[i - 1] in ("pairs", "models", "players", "stability", "family_shares", "families"):
                    q.append("<%s>" % parts[i - 1])
                else:
                    q.append(p)
            pat["/".join(q)] += 1
        print("=====", X, f, len(keys))
        for k, v in sorted(pat.items()):
            print("  %4d %s" % (v, k))
        k0 = [k for k in keys if k.endswith("spearman_J")][:2]
        for k in k0:
            print("  example", k, z[k].shape, z[k].dtype, np.isfinite(z[k]).sum())
