# n12: my own os.scandir/os.stat listing of the SHAP folder (smoke\bardl_fix pruned before any scandir of it, never
# entered) and of OUT, classified by the archive plan's stated rules (re-implemented here), to check the manifest's new
# counts and bytes. No file content is read. Also compares with the records writer's listing files (sizes, times) to
# find files changed after its listing (2026-11-17 09:34 UTC). Prints summary only; no path with a user name printed.
import collections
import datetime
import json
import os
import stat
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", ".."))
OUT = os.path.join(ROOT, r"paper\supp_build\s3_13")
SHAP = r"D:\treeroute\analysis\shap_v1"
WORK = os.path.join(OUT, r"stage\_scripts\records\work")
PRUNE = os.path.normcase(os.path.join(SHAP, "smoke", "bardl_fix"))


def walk(root, skip_top=()):
    files, reparse, pruned = [], [], []
    stack = [root]
    while stack:
        d = stack.pop()
        with os.scandir(d) as it:
            ents = list(it)
        for e in ents:
            st = e.stat(follow_symlinks=False)
            rp = bool(getattr(st, "st_file_attributes", 0) & 0x400) or stat.S_ISLNK(st.st_mode)
            rel = os.path.relpath(e.path, root).replace("\\", "/")
            if rp:
                reparse.append(rel)
                continue
            if stat.S_ISDIR(st.st_mode):
                if os.path.normcase(e.path) == PRUNE:
                    pruned.append(rel)
                    continue
                if d == root and e.name in skip_top:
                    pruned.append(rel)
                    continue
                stack.append(e.path)
            else:
                files.append((rel, st.st_size, st.st_mtime))
    return files, reparse, pruned


def ext_of(rel):
    b = rel.rsplit("/", 1)[-1]
    return ("." + b.rsplit(".", 1)[-1].lower()) if "." in b else "(none)"


def group(rel):
    p = rel.split("/")
    n = p[-1]
    if len(p) == 1:
        return "A top"
    t = p[0]
    if t == "scripts":
        return "A scripts"
    if t == "logs":
        return "A logs"
    if t == "_snapshots":
        return "A snapshots"
    if t == "engine_runs":
        return "K engine_runs"
    if t == "work":
        return "K work rf"
    if t == "smoke":
        return "L smoke"
    if t == "out":
        if len(p) == 3:
            return "A run summaries"
        if p[3] == "compare":
            return "K draws npy" if n == "bootstrap_draws.npy" else "A compare"
        if n in ("meta.json", "exactness.json", "ridge_shap_exactness.json", "rows.parquet.done.json"):
            return "A piece records"
        if n in ("rows.parquet", "background_keys.parquet"):
            if p[1] == "coral":
                return "K coral row-level"
            return "A gridded bg keys" if n == "background_keys.parquet" else "K gridded SHAP rows"
        return "?? out " + rel
    if t == "sample":
        if p[1] == "coral":
            return "A coral manifest" if n == "sample_manifest.json" else "K coral row-level"
        return "A gridded samples"
    if t == "rebuild":
        if n in ("gates.json", "DONE.json", "precheck.json"):
            return "A rebuild records"
        if n in ("bank.npz", "routers.npz"):
            return "K banks routers"
        if p[1] == "coral":
            return "K coral row-level"
        if n in ("preds_check.parquet", "rows.parquet"):
            return "A gridded rebuild checks"
        return "?? rebuild " + rel
    if t == "verify_v1":
        e = ext_of(rel)
        if e == ".npz":
            return "K verify npz"
        if e == ".gz":
            return "K verify gz"
        return "A verify_v1"
    return "?? " + rel


MIB25 = 25 * 1024 * 1024
t0 = datetime.datetime.utcnow()
sf, srp, spr = walk(SHAP)
t1 = datetime.datetime.utcnow()
print("SHAP listed %s-%s UTC: %d files, %s B; reparse %d; pruned %s" % (
    t0.strftime("%H:%M:%S"), t1.strftime("%H:%M:%S"), len(sf), format(sum(x[1] for x in sf), ","), len(srp), spr))
G = collections.OrderedDict()
for rel, size, mt in sf:
    g = group(rel)
    d = G.setdefault(g, [0, 0, 0, 0])
    d[0] += 1
    d[1] += size
    if g.startswith("A") and ext_of(rel) != ".parquet" and size < MIB25:
        d[2] += 1
        d[3] += size
tot = collections.Counter()
for g in sorted(G):
    d = G[g]
    print("  %-26s %6d %16s  gh %5d %14s" % (g, d[0], format(d[1], ","), d[2], format(d[3], ",")))
    c = g[0]
    tot[c + "f"] += d[0]
    tot[c + "b"] += d[1]
    tot["ghf"] += d[2]
    tot["ghb"] += d[3]
print("  archived %d / %s; kept out %d / %s; left out %d / %s; github %d / %s" % (
    tot["Af"], format(tot["Ab"], ","), tot["Kf"], format(tot["Kb"], ","), tot["Lf"], format(tot["Lb"], ","), tot["ghf"], format(tot["ghb"], ",")))
# details
ext = collections.Counter(ext_of(r) for r, s, m in sf if group(r).startswith("A"))
print("  archived by ext:", dict(sorted(ext.items())))
pyb = sum(s for r, s, m in sf if group(r).startswith("A") and ext_of(r) == ".py")
print("  archived .py bytes (SHAP):", format(pyb, ","))
smoke_eng = [(r, s) for r, s, m in sf if r.startswith("smoke/") and any(("engine_runs" in c or "engine_tmp" in c) for c in r.split("/")[1:-1])]
print("  smoke engine folders: %d files, %s B" % (len(smoke_eng), format(sum(s for r, s in smoke_eng), ",")))
k2 = collections.Counter(r.split("/")[1] for r, s, m in sf if group(r) == "K gridded SHAP rows")
print("  gridded SHAP rows per problem:", dict(k2))
rr = collections.Counter(r.split("/")[1] + ":" + r.split("/")[-1] for r, s, m in sf if group(r) == "A rebuild records")
print("  rebuild records:", sorted(rr))
kb = [(r, s) for r, s, m in sf if group(r) == "K banks routers"]
print("  banks/routers: %d files %s B" % (len(kb), format(sum(s for r, s in kb), ",")))
rf = collections.Counter(r.split("/")[1] for r, s, m in sf if group(r) == "K work rf")
print("  work rf files per problem:", dict(rf))
rowlevel = [(r, s) for r, s, m in sf if group(r) in ("A gridded bg keys", "A gridded samples", "A gridded rebuild checks") and ext_of(r) == ".parquet"]
print("  archived gridded row-level parquet: %d files %s B" % (len(rowlevel), format(sum(s for r, s in rowlevel), ",")))
big = sorted(((s, r) for r, s, m in sf if group(r).startswith("A")), reverse=True)[:4]
print("  largest archived:", [(format(s, ","), r) for s, r in big])
npz = collections.Counter("/".join(r.split("/")[:3]) for r, s, m in sf if group(r) == "K verify npz")
print("  verify npz by folder:", dict(npz))
newest = max(sf, key=lambda x: x[2])
print("  newest file mtime (UTC):", datetime.datetime.utcfromtimestamp(newest[2]).strftime("%Y-%m-%d %H:%M:%S"))
unk = [g for g in G if g.startswith("??")]
print("  unclassified:", unk[:5])

# compare with the records writer's listing
L = json.load(open(os.path.join(WORK, "listing_shap.json"), encoding="utf-8"))
old = {r[0].replace("\\", "/"): r[1] for r in L["files"]}
new = {r: s for r, s, m in sf}
print("  writer's listing: %d files %s B, %s-%s; pruned %s" % (len(old), format(sum(old.values()), ","), L["listed_utc_start"], L["listed_utc_end"], L["pruned_not_entered"]))
print("  only in mine: %d; only in writer's: %d; size differs: %d" % (
    len(set(new) - set(old)), len(set(old) - set(new)), sum(1 for k in set(new) & set(old) if new[k] != old[k])))

# OUT
of, orp, opr = walk(OUT)
G2 = collections.Counter()
B2 = collections.Counter()
for rel, size, mt in of:
    t = rel.split("/")[0]
    G2[t] += 1
    B2[t] += size
print("\nOUT now:", {k: (G2[k], format(B2[k], ",")) for k in sorted(G2)})
arch = [r for r in of if r[0].split("/")[0] in ("spec", "A", "B", "reconcile", "skeptic", "_brief")]
print("OUT archived folders now: %d files %s B; ext %s" % (len(arch), format(sum(r[1] for r in arch), ","),
      dict(collections.Counter(ext_of(r[0]) for r in arch))))
LO = json.load(open(os.path.join(WORK, "listing_out.json"), encoding="utf-8"))
oldo = {r[0].replace("\\", "/"): (r[1], r[2]) for r in LO["files"]}
print("writer's OUT listing: %d files %s B, %s-%s" % (len(oldo), format(sum(v[0] for v in oldo.values()), ","), LO["listed_utc_start"], LO["listed_utc_end"]))
oa = {k: v for k, v in oldo.items() if k.split("/")[0] in ("spec", "A", "B", "reconcile", "skeptic", "_brief")}
st_ = {k: v for k, v in oldo.items() if k.split("/")[0] == "stage"}
print("  writer's archived part: %d files %s B; stage %d files %s B" % (len(oa), format(sum(v[0] for v in oa.values()), ","), len(st_), format(sum(v[0] for v in st_.values()), ",")))
cur = {r: (s, m) for r, s, m in arch}
chg = [(k, oa[k][0], cur[k][0], oa[k][1], datetime.datetime.utcfromtimestamp(cur[k][1]).strftime("%Y-%m-%dT%H:%M:%SZ")) for k in sorted(set(cur) & set(oa)) if cur[k][0] != oa[k][0] or oa[k][1] != datetime.datetime.utcfromtimestamp(cur[k][1]).strftime("%Y-%m-%dT%H:%M:%SZ")]
print("  archived files changed since the writer's listing:", chg)
print("  archived files new since:", sorted(set(cur) - set(oa)), "gone:", sorted(set(oa) - set(cur)))
