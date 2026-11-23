# Skeptic (version 4 check, item 5): layout and privacy (adapted from k22). Read-only; prints only. The account, host
# and domain names are read from the environment at run time and never printed or stored; a hit prints only the file
# and the kind.
#  - tables_agreed.md v4 (and cells.json, the spec, CHANGES_v4.md, CHANGES_v3.md): BOM, CR, TAB, final newline,
#    trailing spaces, line count; tables_agreed.md: blank-line layout, table column counts, absolute local paths outside
#    HTML comments, "--" inside a comment, every comment closed on its line;
#  - every text file under OUT: account / host / domain names, the home folder, user-folder paths, e-mail addresses,
#    uuid-like ids.
import os, re, sys
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
files = {"tables_agreed.md": os.path.join(OUT, "reconcile", "tables_agreed.md"),
         "cells.json": os.path.join(OUT, "reconcile", "cells.json"),
         "TABLE_SPEC.md": os.path.join(OUT, "spec", "TABLE_SPEC.md"),
         "CHANGES_v4.md": os.path.join(OUT, "spec", "CHANGES_v4.md"),
         "CHANGES_v3.md": os.path.join(OUT, "spec", "CHANGES_v3.md")}
for name, f in files.items():
    b = open(f, "rb").read()
    t = b.decode("utf-8")
    body = t[:-1].split("\n") if t.endswith("\n") else t.split("\n")
    print("%-16s bytes %d | lines %d | BOM %s | CR %d | TAB %d | ends with exactly one LF %s | trailing-space lines %d"
          % (name, len(b), len(body), b.startswith(b"\xef\xbb\xbf"), b.count(b"\r"), b.count(b"\t"),
             t.endswith("\n") and not t.endswith("\n\n"), sum(1 for x in body if x != x.rstrip(" \t"))))

T = open(files["tables_agreed.md"], encoding="utf-8", newline="").read()
L = T[:-1].split("\n")
vis = [re.sub(r"<!--.*?-->", "", x) for x in L]
print("double blank lines: %d | first line is one whole comment: %s | last line: %r" % (
    sum(1 for i in range(1, len(L)) if L[i] == L[i - 1] == ""), L[0].startswith("<!--") and L[0].endswith("-->") and L[0].count("<!--") == 1, L[-1][:50]))
# table blocks: every row has the header's number of cells
bad, nt, i = [], 0, 0
while i < len(L):
    if L[i].startswith("| ") and i + 1 < len(L) and re.fullmatch(r"\|(?:---\|)+", L[i + 1]):
        nt += 1
        ncol = L[i].count(" | ") + 1
        sep = L[i + 1].count("---")
        if sep != ncol:
            bad.append((i + 1, "separator", sep, ncol))
        j = i + 2
        while j < len(L) and L[j].startswith("| "):
            n = L[j][2:-2].count(" | ") + 1 if L[j].endswith(" |") else -1
            if n != ncol:
                bad.append((j + 1, n, ncol))
            j += 1
        i = j
    else:
        i += 1
print("tables: %d | rows whose cell count differs from the header's: %s" % (nt, bad[:6]))
pat_abs = re.compile(r"(?i)\b[A-Z]:[\\/]|\\\\[A-Za-z]|/Users/|\\Users\\|/home/|AppData|Desktop|Downloads")
print("absolute local paths in visible text (outside HTML comments):", [i + 1 for i, x in enumerate(vis) if pat_abs.search(x)])
print("comments with a path outside D:/treeroute or relative paper/, engine/ paths:",
      [i + 1 for i, x in enumerate(L) for c in re.findall(r"<!--(.*?)-->", x)
       if re.search(r"(?i)\b[A-CE-Z]:[\\/]|/Users/|\\Users\\|AppData|Desktop|Downloads", c)])
cm = re.findall(r"<!--(.*?)-->", T)
print("HTML comments: %d | '--' inside a comment body: %d | lines with unbalanced '<!--'/'-->': %d | '-->' or '<!--' inside a comment body: %d" % (
    len(cm), sum(1 for c in cm if "--" in c), sum(1 for x in L if x.count("<!--") != x.count("-->")),
    sum(1 for c in cm if "<!--" in c or "-->" in c)))
print("'agent' anywhere (any case) in tables_agreed.md: %d | in CHANGES_v4.md: %d" % (
    len(re.findall(r"(?i)agent", T)), len(re.findall(r"(?i)agent", open(files["CHANGES_v4.md"], encoding="utf-8").read()))))

names = {k: os.environ.get(k, "") for k in ("USERNAME", "COMPUTERNAME", "USERDOMAIN", "LOGONSERVER")}
names["home folder name"] = os.path.basename(os.path.expanduser("~"))
names = {k: v.strip("\\") for k, v in names.items() if len(v.strip("\\")) >= 3}
home = os.path.expanduser("~").lower()
pats = {"user-folder path": re.compile(r"(?i)[a-z]:[\\/]+users[\\/]+(?!public|~)[^\\/\s\"'`]+"),
        "e-mail address": re.compile(r"[\w.+-]+@[\w-]+\.[a-z]{2,}", re.I),
        "uuid-like id": re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I)}
n_files = hits = 0
for d, _, fs in os.walk(OUT):
    for f in fs:
        if not f.lower().endswith((".py", ".md", ".json", ".txt", ".csv")):
            continue
        p = os.path.join(d, f)
        t = open(p, encoding="utf-8", errors="replace").read()
        n_files += 1
        low = t.lower()
        found = [k for k, v in names.items() if v.lower() in low]
        if home in low:
            found.append("home path")
        found += [k for k, rx in pats.items() if rx.search(t)]
        if found:
            hits += 1
            print("HIT", os.path.relpath(p, OUT), sorted(set(found)))
print("text files scanned under OUT: %d; files with a hit: %d" % (n_files, hits))
