"""n01: byte-compare the spans that the second version of report.md says it keeps unchanged.

Read-only: reads report.md and report.md.before_fix1, prints results, writes nothing.
"""
import hashlib

V = r"D:\treeroute\analysis\shap_v1\verify_v1"
P2 = V + r"\reconcile\report.md"
P1 = V + r"\reconcile\report.md.before_fix1"

b2 = open(P2, "rb").read()
b1 = open(P1, "rb").read()
print("v2 sha256", hashlib.sha256(b2).hexdigest(), len(b2))
print("v1 sha256", hashlib.sha256(b1).hexdigest(), len(b1))


def span(b, start, end):
    i = b.find(start)
    assert i >= 0, start
    assert b.find(start, i + 1) < 0, ("start not unique", start)
    j = b.find(end, i)
    assert j >= 0, end
    assert b.find(end, j + 1) < 0, ("end not unique", end)
    return i, j, b[i:j]


START_REC = b"# Round 14 reconciliation"
END_REC = b"## Lead's addendum"
START_A2 = b"### A2. Status counts"
END_A3 = b"### A4. The three skeptics"

for name, s, e in [("reconciler text (first heading to end of section 7)", START_REC, END_REC),
                   ("A2 + A3", START_A2, END_A3)]:
    i1, j1, s1 = span(b1, s, e)
    i2, j2, s2 = span(b2, s, e)
    print(name)
    print("  v1 bytes [%d, %d) len %d sha %s" % (i1, j1, len(s1), hashlib.sha256(s1).hexdigest()))
    print("  v2 bytes [%d, %d) len %d sha %s" % (i2, j2, len(s2), hashlib.sha256(s2).hexdigest()))
    print("  identical:", s1 == s2)
    if s1 != s2:
        # first differing byte
        k = next(k for k in range(min(len(s1), len(s2))) if s1[k] != s2[k]) if any(
            s1[k] != s2[k] for k in range(min(len(s1), len(s2)))) else min(len(s1), len(s2))
        print("  first diff at offset", k, repr(s1[k - 40:k + 40]), repr(s2[k - 40:k + 40]))

# What precedes the first heading in each version (the lead's note), and whether the first heading is preceded only
# by the note.
i1 = b1.find(START_REC)
i2 = b2.find(START_REC)
print("v1 note bytes:", i1, "v2 note bytes:", i2)
print("v1 lines before heading:", b1[:i1].count(b"\n"), "v2:", b2[:i2].count(b"\n"))

# Also: is section 7's end the byte right before '## Lead's addendum' in both (blank line)?
for nm, b in [("v1", b1), ("v2", b2)]:
    j = b.find(END_REC)
    print(nm, "bytes before addendum heading:", repr(b[j - 80:j]))

# Format checks of v2
print("v2 BOM:", b2[:3] == b"\xef\xbb\xbf", "CR count:", b2.count(b"\r"), "LF count:", b2.count(b"\n"),
      "ends LF:", b2.endswith(b"\n"))
try:
    b2.decode("utf-8", errors="strict")
    print("v2 strict utf-8 OK")
except UnicodeDecodeError as ex:
    print("v2 utf-8 error", ex)
nonascii = sorted(set(ch for ch in b2.decode("utf-8") if ord(ch) > 127))
print("v2 non-ASCII characters:", [hex(ord(c)) for c in nonascii])
print("v2 tabs:", b2.count(b"\t"), "NUL:", b2.count(b"\x00"))

# Line numbers of the span ends in v2 (1-based) for reference
for lab, s in [("reconciler first heading", START_REC), ("addendum heading", END_REC), ("A2", START_A2),
               ("A4", END_A3), ("A6", b"### A6."), ("A7", b"### A7.")]:
    print(lab, "v2 line", b2[:b2.find(s)].count(b"\n") + 1,
          "v1 line", (b1[:b1.find(s)].count(b"\n") + 1) if b1.find(s) >= 0 else None)
