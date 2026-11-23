# Skeptic (version 4 check, item 2): the remaining source checks of the version-4 texts. Read-only; prints only.
#  - V4-3: the S3.19 source comment (line 71) and, from coral's sample manifest named there, what the Locations
#    column counts (units in the sample against sample rows);
#  - V4-2: coral's E3a static file list: rebuild script line 501 hashes fls([]) for the neighbour kind; is the
#    recorded 16-hex prefix the SHA-256 of the canonical empty list "[]"?
#  - V4-8: Table S3.18 a (lines 26-52) against the S3.22 rows "Rivals that explain in another link and passed their
#    skill guard" (line 155) and "Rivals declined by their skill guard" (line 156);
#  - V4-7: the rows of S3.18 panel b (lines 58-65): rivals and the naive-baseline row.
import hashlib, json, os, re, sys
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
SHAP = r"D:\treeroute\analysis\shap_v1"
L = open(os.path.join(OUT, "reconcile", "tables_agreed.md"), encoding="utf-8").read().split("\n")[:-1]
src71 = re.findall(r"<!--(.*?)-->", L[70])
print("line 71 source comment:", [re.sub(r"(?i)[a-z]:[\\/]users[\\/][^ ]+", "<user path>", s) for s in src71])
# sample manifest of coral
cands = [SHAP + r"\sample\coral\sample_manifest.json", SHAP + r"\sample\coral\lead_0\sample_manifest.json"]
for c in cands:
    if os.path.exists(c):
        M = json.load(open(c, encoding="utf-8"))
        flat = {k: v for k, v in M.items() if isinstance(v, (int, float, str, bool)) and not re.search(r"(?i)[a-z]:[\\/]", str(v))}
        print("coral sample manifest %s: keys %s" % (c.replace(SHAP, "SHAP"), list(M)))
        print("   scalar values:", json.dumps(flat, ensure_ascii=False)[:900])
        for k in M:
            if "unit" in k.lower() or "site" in k.lower() or "visit" in k.lower():
                v = M[k]
                print("   %s = %s" % (k, json.dumps(v, ensure_ascii=False)[:300]))
        break
else:
    print("coral sample manifest not found at the two guessed names")
print('V4-2: sha256("[]") = %s...; coral recorded static_files_sha256 prefix 4f53cda18c2baa0c; equal prefix: %s' % (
    hashlib.sha256(b"[]").hexdigest()[:16], hashlib.sha256(b"[]").hexdigest()[:16] == "4f53cda18c2baa0c"))
# S3.18 a vs S3.22
probs = ["PM2.5", "NDVI", "Burned fraction", "Forest loss", "Coral bleaching"]
rowsA = [x for x in L[25:52] if x.startswith("| ") and not x.startswith("| Problem") and not x.startswith("|---")]
cur = None
by = {p: [] for p in probs}
for x in rowsA:
    c = x[2:-2].split(" | ")
    if c[0] in probs:
        cur = c[0]
    by[cur].append(c)
hdr = L[25]
print("S3.18 a header:", hdr)
for p in probs:
    for c in by[p]:
        print("   %-16s %-45s | link %-12s | guard %-14s | main set %s" % (p, c[1][:45], c[3], c[4], c[5]))
print("S3.22 line 155:", L[154])
print("S3.22 line 156:", L[155])
# V4-7: panel b rows
for k in range(56, 66):
    c = L[k][2:-2].split(" | ") if L[k].startswith("| ") else None
    if c:
        print("S3.18 b line %d: problem %r | column 2: %r" % (k + 1, c[0], c[1][:90]))
