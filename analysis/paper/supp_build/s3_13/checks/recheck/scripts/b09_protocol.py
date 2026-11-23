"""SHAP protocol format rules on the staged copy against the live file (the one named file SHAP/PROTOCOL.md):
LF only, no BOM, one final LF; the new lines ASCII and at most 120 characters; sections 3 and 8 byte-identical
(from each '## 3' / '## 8' heading to the next level-2 heading); the live text kept as a prefix; the placeholders.
Read-only; prints headings and hashes only. Run: py -3.9 -I -B b09_protocol.py
"""
import hashlib
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from b04_lib import STAGE, SHAP

live = (SHAP / "PROTOCOL.md").read_bytes()
staged = (STAGE / "shap" / "PROTOCOL.md").read_bytes()
print("live sha256", hashlib.sha256(live).hexdigest()[:12], len(live), "bytes; staged",
      hashlib.sha256(staged).hexdigest()[:12], len(staged), "bytes")
print("BOM:", staged.startswith(b"\xef\xbb\xbf"), "CR:", staged.count(b"\r"), "ends with one LF:",
      staged.endswith(b"\n") and not staged.endswith(b"\n\n"))
print("live is a byte prefix of staged:", staged.startswith(live))
lt, st = live.decode("utf-8"), staged.decode("utf-8")


def section(t, num):
    heads = [(m.start(), m.group(0)) for m in re.finditer(r"(?m)^## .*$", t)]
    for k, (pos, h) in enumerate(heads):
        if re.match(r"^## %d[ .]" % num, h):
            end = heads[k + 1][0] if k + 1 < len(heads) else len(t)
            return h, t[pos:end]
    return None, ""


for n in (3, 8):
    hl, sl = section(lt, n)
    hs, ss = section(st, n)
    print("section %d: heading %r; live %s (%d B), staged %s (%d B), identical: %s"
          % (n, hl, hashlib.sha256(sl.encode()).hexdigest()[:12], len(sl.encode()),
             hashlib.sha256(ss.encode()).hexdigest()[:12], len(ss.encode()), sl == ss))
new = st[len(lt):] if st.startswith(lt) else None
if new is not None:
    lines = new.split("\n")
    print("new lines:", len(lines) - 1, "; longest:", max(len(x) for x in lines), "; over 120:",
          sum(1 for x in lines if len(x) > 120), "; non-ASCII chars:", sum(1 for ch in new if ord(ch) > 127))
    print("placeholders in new text:", sorted(set(re.findall(r"@@[A-Z_]+@@", new))), "count @@SNAP@@:",
          new.count("@@SNAP@@"), "count @@LATER_READS@@:", new.count("@@LATER_READS@@"))
    lr = [x for x in lines if "@@LATER_READS@@" in x]
    print("@@LATER_READS@@ line(s):", [(len(x), x.startswith("@@")) for x in lr])
print("level-2 headings of the staged file:", [h for _, h in [(m.start(), m.group(0)) for m in re.finditer(r"(?m)^## .*$", st)]])
