"""The pm25 no-op hop evidence, re-checked read-only (ruling Z1 record). For each hop: the two compared smoke runs'
engines (stripped hash from manifest.json, mapped to the file sha through the freeze locks), and for hop 1 (whose
compare output was not saved) the gate files of compare_runs.py (derived.json, every *preds*.parquet, every csv)
compared by sha256 only. Prints one JSON document.
    py -3.9 -B hop_evidence.py <out json>"""
import hashlib, json, sys
from pathlib import Path
REG = Path("D:/treeroute/registry/freeze")
locks = {}
for p in sorted(REG.glob("FREEZE_*.lock.json")):
    e = json.loads(p.read_text(encoding="utf-8")).get("engine") or {}
    if e.get("engine_code_hash_comment_stripped"):
        locks[e["engine_code_hash_comment_stripped"]] = e["engine_code_sha256"]
def one(parent):
    runs = [p.parent for p in Path(parent).rglob("manifest.json") if (p.parent / "DONE.json").is_file()]
    assert len(runs) == 1, (parent, runs)
    m = json.loads((runs[0] / "manifest.json").read_text(encoding="utf-8"))
    s = m["engine_code_hash"]
    return {"run": runs[0].as_posix(), "kind": m["config"]["kind"], "package": m["config"]["package"],
            "engine_stripped": s, "engine_file_sha": locks.get(s), "engine_constants_sha256": m["config"]["engine_constants_sha256"]}
def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def gate(name):
    n = name.split("/")[-1]
    return n == "derived.json" or ("preds" in n and n.endswith(".parquet")) or n.endswith(".csv")
def gates(a, b):
    fa = {p.relative_to(a).as_posix(): p for p in Path(a).rglob("*") if p.is_file() and gate(p.name)}
    fb = {p.relative_to(b).as_posix(): p for p in Path(b).rglob("*") if p.is_file() and gate(p.name)}
    same = sorted(k for k in set(fa) & set(fb) if sha(fa[k]) == sha(fb[k]))
    bad = sorted((set(fa) | set(fb)) - set(same))
    return {"gate_files_byte_identical": len(same), "gate_files_differing_or_missing": bad,
            "gate_file_sha256": {k: sha(fa[k]) for k in same}}
hops = []
h1a, h1b = one("D:/treeroute/ckpt_20261013/runs_t1_before/pm25"), one("D:/treeroute/ckpt_20261013/runs_t1_after_final/pm25")
hops.append({"hop": 1, "old": h1a, "new": h1b, "recheck": gates(h1a["run"], h1b["run"]),
             "record": "engine PENDING_PARTS.md Part 586 (T1: 15 gate files byte-identical); compare script "
                       "D:/treeroute/ckpt_20261013/scratch2/compare_runs.py (its output was not saved)"})
h2a, h2b = one("D:/treeroute/install_20261015/smokes/old/pm25"), one("D:/treeroute/install_20261015/smokes/new/pm25")
hops.append({"hop": 2, "old": h2a, "new": h2b, "record": "D:/treeroute/install_20261015/smokes/compare_pm25.txt",
             "record_sha256": sha("D:/treeroute/install_20261015/smokes/compare_pm25.txt")})
h3a, h3b = one("D:/treeroute/s_20261016/smokes/old/pm25"), one("D:/treeroute/s_20261016/smokes/new_resume/pm25")
hops.append({"hop": 3, "old": h3a, "new": h3b,
             "record": ["D:/treeroute/s_20261016/smokes/compare_pm25_resume_vs_old_today.txt",
                        "D:/treeroute/s_20261016/smokes/compare_pm25_resume_vs_install.txt"],
             "record_sha256": [sha("D:/treeroute/s_20261016/smokes/compare_pm25_resume_vs_old_today.txt"),
                               sha("D:/treeroute/s_20261016/smokes/compare_pm25_resume_vs_install.txt")]})
doc = {"hops": hops}
text = json.dumps(doc, indent=1)
Path(sys.argv[1]).write_text(text + "\n", encoding="utf-8")
print(text)
