"""Privacy scan of this check folder itself (copy/, copy_live/, work/, scripts/): account, host and user-folder
names of the machine and the earlier account names found in the live files (taken in memory, never printed),
user-folder paths and the session-folder form. Prints file names and counts only. Read-only.
Run: py -3.9 -I -B b13_scan_copies.py
"""
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from b04_lib import CHK, PAIRS, NAME_PATS, USERPATH_RE, UUID_RE, read_bytes, text_of

cands = set()
for rel, live in PAIRS:
    if live is None:
        continue
    t = text_of(read_bytes(live))
    for m in re.finditer(r"(?i)[A-Za-z]:[\\/]+Users[\\/]+([^\\/\s`'\")]+)", t):
        cands.add(m.group(1))
    for m in re.finditer(r"(?i)[A-Za-z]--Users-([A-Za-z0-9_.-]+?)-(?:Desktop|Downloads|Documents|OneDrive)", t):
        cands.add(m.group(1))
cands = {c for c in cands if len(c) >= 3 and c.casefold() not in {"public", "default", "<user>", "user"}}
pats = list(NAME_PATS) + [re.compile(r"(?<![A-Za-z0-9])" + r"(?:[\s_.\-]|%20)*".join(re.escape(w) for w in re.split(r"[\s_.\-]+", c) if w)
                                     + r"(?![A-Za-z0-9])", re.I) for c in sorted(cands)]
other = [("user-folder path", USERPATH_RE), ("session-folder form", re.compile(r"(?i)[A-Za-z]--Users-")), ("uuid", UUID_RE)]
for p in sorted(CHK.rglob("*")):
    if not p.is_file():
        continue
    rel = p.relative_to(CHK).as_posix()
    b = p.read_bytes()
    if p.suffix.lower() in (".png", ".pdf", ".tif", ".docx"):
        t = b.decode("latin-1")
    else:
        try:
            t = b.decode("utf-8")
        except UnicodeDecodeError:
            t = b.decode("latin-1")
    n_name = sum(len(list(q.finditer(t))) for q in pats)
    n_other = {k: len(list(q.finditer(t))) for k, q in other}
    if n_name or any(n_other.values()):
        print("%s: names %d; %s" % (rel, n_name, ", ".join("%s %d" % kv for kv in n_other.items() if kv[1])))
print("done")
