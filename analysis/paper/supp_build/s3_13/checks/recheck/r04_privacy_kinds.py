# r04_privacy_kinds.py - count-only privacy scan. Names are taken from the environment at run time, in memory only, and
# never printed. Usage: py -3.9 -I -B r04_privacy_kinds.py <file or folder> [...]; a folder is walked (os.walk).
# For each file with a hit, prints its path relative to OUT (or its name) and the count per pattern kind; nothing else.
# Patterns: those of the fixer's privacy_two.py (account name, profile prefix, drive-letter Users path, session-folder
# form, host name, Windows default host form, UUID-shaped id, workflow id, e-mail address), plus the earlier account
# names found in the live paper and record files (user-folder paths and session-folder forms in them, as the build
# checker's b12 takes them), also in memory only.
import collections
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", ".."))
ROOT = os.path.normpath(os.path.join(OUT, "..", "..", ".."))
acct = os.path.basename(os.environ.get("USERPROFILE", "") or "")
host = os.environ.get("COMPUTERNAME", "") or ""
assert acct and host
PATS = collections.OrderedDict([
    ("account name", re.compile(re.escape(acct), re.I)),
    ("profile prefix", re.compile(r"users[\\/]+" + re.escape(acct[:3]), re.I)),
    ("drive-letter Users path", re.compile(r"[A-Za-z]:(\\\\|\\|/)+users(\\\\|\\|/)+", re.I)),
    ("session-folder form", re.compile(r"[A-Za-z]--users-", re.I)),
    ("host name", re.compile(re.escape(host), re.I)),
    ("default host form", re.compile(r"(DESKTOP|LAPTOP)-[A-Z0-9]{7}", re.I)),
    ("UUID-shaped id", re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I)),
    ("workflow id", re.compile(r"\bwf_[0-9a-f]{6,}", re.I)),
    ("e-mail address", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
])
LIVE = [os.path.join(ROOT, *p.split("/")) for p in (
    "paper/draft/S3_posthoc.md", "paper/draft/05_rivals.md", "paper/draft/S1_disclosures.md",
    "paper/draft/S4_provenance.md", "paper/draft/GLOSSARY.md", "paper/draft/REFERENCES.md", "paper/PAPER_FACTS.md",
    "paper/PAPER_OUTLINE.md", "engine/PENDING_PARTS.md", "_archive_plan/ARCHIVE_MANIFEST_DRAFT.md")]
cands = set()
for p in LIVE:
    t = open(p, "rb").read().decode("utf-8", "replace")
    for m in re.finditer(r"(?i)[A-Za-z]:[\\/]+Users[\\/]+([^\\/\s`'\")]+)", t):
        cands.add(m.group(1))
    for m in re.finditer(r"(?i)[A-Za-z]--Users-([A-Za-z0-9_.-]+?)-(?:Desktop|Downloads|Documents|OneDrive)", t):
        cands.add(m.group(1))
cands = {c for c in cands if len(c) >= 3 and c.casefold() not in {"public", "default", "<user>", "user"}}
for i, c in enumerate(sorted(cands)):
    words = [w for w in re.split(r"[\s_.\-]+", c) if w]
    PATS["earlier name %d" % (i + 1)] = re.compile(r"(?<![A-Za-z0-9])" + r"(?:[\s_.\-]|%20)*".join(map(re.escape, words))
                                                   + r"(?![A-Za-z0-9])", re.I)


def decode(b):
    if b.startswith(b"\xef\xbb\xbf"):
        b = b[3:]
    if b[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return b.decode("utf-16", "replace")
    return b.decode("utf-8", "replace")


def files(arg):
    if os.path.isdir(arg):
        for dp, dn, fn in os.walk(arg):
            for n in fn:
                yield os.path.join(dp, n)
    else:
        yield arg


tot = collections.Counter()
nfiles = 0
for arg in sys.argv[1:]:
    for p in files(arg):
        nfiles += 1
        b = open(p, "rb").read()
        t = decode(b) if not p.lower().endswith((".png", ".docx", ".tif", ".pdf", ".npz", ".parquet")) else b.decode("latin-1")
        hits = {k: len(rx.findall(t)) for k, rx in PATS.items()}
        hits = {k: v for k, v in hits.items() if v}
        if hits:
            rel = os.path.relpath(p, OUT) if os.path.normcase(p).startswith(os.path.normcase(OUT)) else os.path.basename(p)
            print("%s: %s" % (rel, "; ".join("%s %d" % kv for kv in hits.items())))
            tot.update(hits)
print("files scanned: %d; earlier names in the patterns: %d; hits in total: %s" % (nfiles, len(cands), dict(tot) or "none"))
