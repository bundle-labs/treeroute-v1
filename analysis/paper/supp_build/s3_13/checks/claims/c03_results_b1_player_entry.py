"""Print the key structure (no values) of one B1 player entry in the re-computation's results file.

Read only: prints, for b1.pm25.variable.importance.players[<first>], the type and the keys of I, share,
signed_mean and sign_determined, and whether every player entry has the same structure. No number printed.
"""
import json
import sys

PATH = r"D:\treeroute\analysis\shap_v1\verify_v1\A\results.json"


def keys_of(v):
    if isinstance(v, dict):
        return "dict" + str(sorted(v.keys()))
    if isinstance(v, list):
        return "list(len %d)" % len(v)
    return type(v).__name__


def main():
    with open(PATH, "r", encoding="utf-8") as fh:
        res = json.load(fh)
    for p in ("pm25", "ndvi", "fire"):
        for lev in ("variable", "feature"):
            players = res["b1"][p][lev]["importance"]["players"]
            sigs = set()
            for name, ent in players.items():
                sig = tuple((k, keys_of(ent[k])) for k in sorted(ent.keys()))
                sigs.add(sig)
            print("b1.%s.%s: %d players, %d distinct entry structures" % (p, lev, len(players), len(sigs)))
            for s in sigs:
                for k, t in s:
                    print("    ", k, "->", t)
    return 0


if __name__ == "__main__":
    sys.exit(main())
