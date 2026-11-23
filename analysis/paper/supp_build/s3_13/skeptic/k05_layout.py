# Skeptic: file identity and layout of the agreed tables; privacy scan of the agreed file. Read-only; prints only.
import hashlib, os, re, sys
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
f_ag = os.path.join(OUT, "reconcile", "tables_agreed.md")
f_a = os.path.join(OUT, "A", "tables.md")
f_b = os.path.join(OUT, "B", "tables.md")
raw = open(f_ag, "rb").read()
for name, f in [("agreed", f_ag), ("A", f_a), ("B", f_b)]:
    print(name, hashlib.sha256(open(f, "rb").read()).hexdigest(), len(open(f, "rb").read()))
print("BOM:", raw.startswith(b"\xef\xbb\xbf"), "CR:", b"\r" in raw, "TAB:", b"\t" in raw, "ends with one LF:",
      raw.endswith(b"\n") and not raw.endswith(b"\n\n"))
txt = raw.decode("utf-8")
L = txt.split("\n")[:-1]
print("lines:", len(L), "trailing spaces:", sum(1 for x in L if x != x.rstrip(" ")),
      "double blank lines:", sum(1 for i in range(1, len(L)) if L[i] == "" and L[i - 1] == ""))
# a table row is followed by a table row, a blank line, or the end
bad_tab = [i + 1 for i in range(len(L) - 1) if L[i].startswith("|") and L[i + 1] not in ("",) and not L[i + 1].startswith("|")]
print("table rows directly followed by text (no blank line):", bad_tab[:10])
print("cells printing '−0.00':", sum(x.count("−0.00") for x in L))
print("ASCII hyphen-minus before a digit inside table cells:",
      sum(len(re.findall(r"(?<![\w`])-\d", x)) for x in L if x.startswith("|")))
print("'nan' tokens:", sum(len(re.findall(r"\bnan\b", x, re.I)) for x in L))
acct = os.environ.get("USERNAME", "") or os.path.basename(os.path.expanduser("~"))   # read at run time, never stored
for pat in [r"[A-Za-z]:\\Users", r"/Users/", re.escape(acct) if acct else r"(?!x)x", r"AppData", r"Desktop", r"\\\\",
            r"session", r"workflow id"]:
    hits = [i + 1 for i, x in enumerate(L) if re.search(pat, x)]
    print("privacy pattern", "(account name)" if acct and pat == re.escape(acct) else pat, "lines:", hits[:5])
print("cells.json beside the agreed file:", os.path.exists(os.path.join(OUT, "reconcile", "cells.json")))
