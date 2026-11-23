# Read-only: compare report.md (v2) with report.md.before_fix1 (v1).
# Checks: the reconciler's text (first heading to end of section 7) unchanged; A2 and A3 unchanged.
# Prints a unified diff of the remaining parts, plus format and privacy checks.
import difflib
import hashlib
import re
import sys

V = r"D:\treeroute\analysis\shap_v1\verify_v1"
P2 = V + r"\reconcile\report.md"
P1 = V + r"\reconcile\report.md.before_fix1"

b2 = open(P2, "rb").read()
b1 = open(P1, "rb").read()
print("sha v2", hashlib.sha256(b2).hexdigest(), len(b2))
print("sha v1", hashlib.sha256(b1).hexdigest(), len(b1))

for name, b in (("v2", b2), ("v1", b1)):
    print(name, "BOM", b[:3] == b"\xef\xbb\xbf", "CR", b.count(b"\r"), "LF", b.count(b"\n"),
          "ends LF", b.endswith(b"\n"), "NUL", b.count(b"\x00"), "TAB", b.count(b"\t"))
    try:
        b.decode("utf-8", errors="strict")
        print(name, "utf-8 strict OK")
    except UnicodeDecodeError as e:
        print(name, "utf-8 FAIL", e)
    non_ascii = sorted(set(ch for ch in b.decode("utf-8") if ord(ch) > 127))
    print(name, "non-ascii chars:", [hex(ord(c)) for c in non_ascii])

t2 = b2.decode("utf-8").split("\n")
t1 = b1.decode("utf-8").split("\n")


def span(lines, start_pat, end_pat):
    s = next(i for i, l in enumerate(lines) if l.startswith(start_pat))
    e = next(i for i, l in enumerate(lines) if i > s and l.startswith(end_pat))
    return s, e


# reconciler's text: from first '# ' heading to the line before '## Lead's addendum'
s2, e2 = span(t2, "# ", "## Lead's addendum")
s1, e1 = span(t1, "# ", "## Lead's addendum")
rec2 = t2[s2:e2]
rec1 = t1[s1:e1]
print("reconciler text v2 lines", s2 + 1, "to", e2, "; v1 lines", s1 + 1, "to", e1)
print("reconciler text identical:", rec2 == rec1)
if rec2 != rec1:
    for l in difflib.unified_diff(rec1, rec2, "v1", "v2", lineterm="", n=0):
        print(l)


def section(lines, head):
    s = next(i for i, l in enumerate(lines) if l.startswith(head))
    e = next((i for i, l in enumerate(lines) if i > s and l.startswith("### ")), len(lines))
    return lines[s:e]


for head in ("### A2.", "### A3."):
    a = section(t1, head)
    b = section(t2, head)
    print(head, "identical:", a == b, "v1 lines", len(a), "v2 lines", len(b))
    if a != b:
        for l in difflib.unified_diff(a, b, "v1", "v2", lineterm="", n=0):
            print(l)

print("=== headings v1 ===")
for i, l in enumerate(t1):
    if l.startswith("#"):
        print(i + 1, l)
print("=== headings v2 ===")
for i, l in enumerate(t2):
    if l.startswith("#"):
        print(i + 1, l)

# lead's note v1 (before first heading)
print("=== v1 lead's note ===")
for l in t1[:s1]:
    print(l)

# privacy scan on v2: emails, uuids, wf ids, user paths, session words
txt = b2.decode("utf-8")
pats = {
    "email": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    "uuid": r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
    "wf_id": r"\bwf_[0-9a-zA-Z]+",
    "users_path": r"(?i)users\\",
    "appdata": r"(?i)appdata",
    "session": r"(?i)session",
    "agent_id": r"(?i)agent-[0-9a-f]{6,}",
    "hex8plus": r"\b[0-9a-f]{8,}\b",
    "host": r"(?i)\b(desktop|laptop)-[a-z0-9]+",
    "jsonl": r"(?i)\.jsonl",
    "transcript": r"(?i)transcript",
}
for k, p in pats.items():
    hits = sorted(set(re.findall(p, txt)))
    print("privacy", k, len(hits), hits[:40])
