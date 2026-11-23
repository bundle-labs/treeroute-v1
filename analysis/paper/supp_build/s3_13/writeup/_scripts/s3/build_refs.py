"""Build STAGE/paper/draft/REFERENCES.md: the live file plus the five entries S3.13 cites (writer s3).

Usage: py -3.9 -I -B build_refs.py
Reads the LIVE paper/draft/REFERENCES.md (read only; SHA-256 checked) and STAGE/refs_candidates.md (the references
writer's checked candidates, SHA-256 checked), copies the five entry lines unchanged into section A at the places
the candidates' table gives (the build's sort key: authors, then year), and adds a dated edit-history entry at the
head of the file's line-3 comment. UTF-8 without BOM, LF, as the live file. Writes only
STAGE/paper/draft/REFERENCES.md.
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("s3lib", os.path.join(HERE, "s3lib.py"))
L = importlib.util.module_from_spec(spec)
spec.loader.exec_module(L)

LIVE = os.path.join(L.ROOT, "paper", "draft", "REFERENCES.md")
LIVE_SHA = "79598da01eb582eedb4a8170e2f520246cde0ba7343dabcaa70128aa636d7c50"
CAND = os.path.join(L.STAGE, "refs_candidates.md")
CAND_SHA = "526ba5bc7dffe10e5b92a270e20ac6e4d17bcc44229fc919ec3af35e9b37e927"
DST = os.path.join(L.STAGE, "paper", "draft", "REFERENCES.md")
# key of the new entry -> (key of the entry it follows, key of the entry it precedes)
PLACES = [
    ("Janzing2020_interventional", "Jacox2022_MHWforecasts", "Johnson2019"),
    ("KendallBabingtonSmith1939_W", "Ke2017_LightGBM", "Knapp2010"),
    ("LundbergLee2017_SHAP", "LuTian2017_fert", "Mansour2009_multisourceDA"),
    ("Lundberg2020_TreeSHAP", "LundbergLee2017_SHAP", "Mansour2009_multisourceDA"),
    ("Webber2010_RBO", "Watkins2015", "Weiss2018_traveltime"),
]
HIST_ANCHOR = "Re-format when the journal is chosen (ruling AL). <!-- "
HIST = ("S3.13 write-up (2026-11-17; pre-edit copy draft/_snapshots/@@SNAP@@/): five entries added to section A for "
        "the method paragraph of Supplement S3.13, each copied unchanged from the write-up's checked candidates "
        "(paper/supp_build/s3_13/stage/refs_candidates.md; each was checked on 2026-11-17 as its Check note says) and "
        "placed where the build's sort key (authors, then year) puts it: Janzing2020_interventional, "
        "KendallBabingtonSmith1939_W, LundbergLee2017_SHAP, Lundberg2020_TreeSHAP and Webber2010_RBO. No other entry "
        "changed, and no printed number changed. ")


def key_of(line):
    k = line.split("— Key `", 1)
    if len(k) != 2:
        return None
    return k[1].split("`", 1)[0]


def main():
    with open(LIVE, "rb") as f:
        raw = f.read()
    if L.sha256_bytes(raw) != LIVE_SHA:
        raise SystemExit("live REFERENCES.md changed since it was staged: stop")
    with open(CAND, "rb") as f:
        craw = f.read()
    if L.sha256_bytes(craw) != CAND_SHA:
        raise SystemExit("refs_candidates.md is not the references writer's version")
    if b"\r" in raw or b"\r" in craw or raw.startswith(b"\xef\xbb\xbf"):
        raise SystemExit("CR or BOM")
    lines = raw.decode("utf-8").split("\n")
    cand = {key_of(ln): ln for ln in craw.decode("utf-8").split("\n") if ln.startswith("- **") and key_of(ln)}
    want = [p[0] for p in PLACES]
    if sorted(cand) != sorted(want):
        raise SystemExit("candidate keys: %r" % sorted(cand))
    a_start = lines.index("## A. Final reference list (verified)")
    a_end = next(i for i in range(a_start + 1, len(lines)) if lines[i].startswith("### A2."))
    for new, after, before in PLACES:
        idx = [i for i in range(a_start, a_end) if key_of(lines[i]) == after]
        if len(idx) != 1:
            raise SystemExit("anchor %s found %d times" % (after, len(idx)))
        i = idx[0]
        if key_of(lines[i + 1]) != before:
            raise SystemExit("%s is not followed by %s but by %s" % (after, before, key_of(lines[i + 1])))
        if any(key_of(ln) == new for ln in lines):
            raise SystemExit("key already present: " + new)
        lines.insert(i + 1, cand[new])
        a_end += 1
    out = "\n".join(lines)
    if out.count(HIST_ANCHOR) != 1:
        raise SystemExit("history anchor")
    out = out.replace(HIST_ANCHOR, HIST_ANCHOR + HIST)
    data = out.encode("utf-8")
    with open(DST, "wb") as f:
        f.write(data)
    print("written", DST, "bytes", len(data), "sha256", L.sha256_bytes(data))
    for new, after, before in PLACES:
        j = [i for i, ln in enumerate(lines) if key_of(ln) == new][0]
        print("%-28s line %d, after %s, before %s" % (new, j + 1, key_of(lines[j - 1]), key_of(lines[j + 1])))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
