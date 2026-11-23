# Round 14, implementer A: try to reproduce the first draws of bootstrap_draws.npy from section 8's words
# ("the SHA-256 generator with the salt shap_v1|AW4|<problem>|<lead>") with a few simple constructions.
# Diagnostic only (identification I02); nothing in results.json depends on it.
import hashlib, os, sys
import numpy as np

SHAP = r"D:\treeroute\analysis\shap_v1"


def u64(text):
    return int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:8], "big")


def cands(p, G, b, k):
    s = "shap_v1|AW4|%s|0" % p
    yield "mod %s|b|k" % s, u64("%s|%d|%d" % (s, b, k)) % G
    yield "mul %s|b|k" % s, (u64("%s|%d|%d" % (s, b, k)) * G) >> 64
    yield "mod %s|b|k (draw,pick)" % s, u64("%s|draw|%d|pick|%d" % (s, b, k)) % G
    yield "mod %s|b*G+k" % s, u64("%s|%d" % (s, b * G + k)) % G
    yield "mul %s|b*G+k" % s, (u64("%s|%d" % (s, b * G + k)) * G) >> 64
    yield "mod %s|b:k" % s, u64("%s|%d:%d" % (s, b, k)) % G


def main():
    for p in ["coral", "defo", "fire", "pm25", "ndvi"]:
        d = np.load(os.path.join(SHAP, "out", p, "lead_0", "compare", "bootstrap_draws.npy"), allow_pickle=False)
        G = d.shape[1]
        hits = {}
        for b in range(3):
            for k in range(G):
                for name, v in cands(p, G, b, k):
                    hits.setdefault(name, 0)
                    hits[name] += int(v == d[b, k])
        tot = 3 * G
        print(p, {k: "%d/%d" % (v, tot) for k, v in hits.items()})
        # the matching construction on the whole matrix
        s = "shap_v1|AW4|%s|0" % p
        full = np.array([[u64("%s|%d|%d" % (s, b, k)) % G for k in range(G)] for b in range(d.shape[0])], dtype=np.int64)
        print("  whole matrix equals int.from_bytes(sha256('%s|<b>|<k>')[:8], 'big') %% G:" % s, bool(np.array_equal(full, d)),
              "(%d x %d)" % d.shape)


if __name__ == "__main__":
    main()
