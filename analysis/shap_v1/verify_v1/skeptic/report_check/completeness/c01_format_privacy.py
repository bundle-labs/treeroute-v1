"""Read-only format and privacy check of V\\reconcile\\report.md.

Prints only counts and line numbers, never a matched private string.
The private strings to look for are taken from the environment at run time,
so that no such string is written into this file.
"""
import hashlib
import os
import re
import sys

P = r"D:\treeroute\analysis\shap_v1\verify_v1\reconcile\report.md"

raw = open(P, "rb").read()
print("bytes", len(raw))
print("sha256", hashlib.sha256(raw).hexdigest())
print("starts_with_utf8_bom", raw[:3] == b"\xef\xbb\xbf")
print("count_CR", raw.count(b"\r"))
print("count_LF", raw.count(b"\n"))
print("ends_with_LF", raw.endswith(b"\n"))
try:
    txt = raw.decode("utf-8", errors="strict")
    print("utf8_strict_decode", "ok")
except UnicodeDecodeError as e:
    print("utf8_strict_decode", "FAIL", e)
    sys.exit(1)
print("count_NUL", txt.count("\x00"))
print("count_TAB", txt.count("\t"))
nonascii = sorted({c for c in txt if ord(c) > 127})
print("non_ascii_chars", [("U+%04X" % ord(c)) for c in nonascii])
for c in nonascii:
    lines = [i + 1 for i, l in enumerate(txt.split("\n")) if c in l]
    print("  U+%04X lines" % ord(c), lines[:20], "n=%d" % len(lines))

lines = txt.split("\n")

def report(label, pred):
    hits = [i + 1 for i, l in enumerate(lines) if pred(l)]
    print(label, "hits", len(hits), "lines", hits[:30])

# private strings from the environment (never printed)
cands = {}
for k in ("USERNAME", "USER", "COMPUTERNAME", "USERDOMAIN", "LOGONSERVER", "USERDNSDOMAIN"):
    v = os.environ.get(k)
    if v:
        cands[k] = v.strip("\\")
home = os.path.expanduser("~")
cands["home_basename"] = os.path.basename(home)
for k, v in cands.items():
    if not v or len(v) < 3:
        print("env", k, "skipped (empty or short)")
        continue
    vl = v.lower()
    report("env:%s (case-insensitive)" % k, lambda l, vl=vl: vl in l.lower())

# generic patterns
report("email-like", lambda l: re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", l) is not None)
report("uuid-like", lambda l: re.search(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", l) is not None)
report("wf_ id", lambda l: re.search(r"\bwf_[0-9a-zA-Z]+", l) is not None)
report("'workflow' word", lambda l: "workflow" in l.lower())
report("'session' word", lambda l: "session" in l.lower())
report("'transcript' word", lambda l: "transcript" in l.lower())
report(r"Users\ path", lambda l: re.search(r"[A-Za-z]:\\Users\\", l) is not None or "\\users\\" in l.lower() or "/users/" in l.lower())
report("AppData", lambda l: "appdata" in l.lower())
report("agent- jsonl", lambda l: re.search(r"agent-[0-9a-f]", l) is not None)
report("hex>=16 run", lambda l: re.search(r"\b[0-9a-f]{16,}\b", l) is not None)
report("'@' char", lambda l: "@" in l)
report("'host' word", lambda l: "host" in l.lower())
# 8-hex tokens (to list which short hashes are in the file; printed as tokens because they are data hashes)
toks = sorted(set(re.findall(r"\b[0-9a-f]{8}\b", txt)))
print("8-hex tokens", toks)
# trailing whitespace and long lines (format only)
print("lines_with_trailing_space", sum(1 for l in lines if l.rstrip(" ") != l))
print("max_line_len", max(len(l) for l in lines))
print("n_lines", len(lines))
