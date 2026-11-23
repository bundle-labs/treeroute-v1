# Skeptic (version 3 check, item 6): layout and privacy. Read-only; prints only. The account, host and domain names
# are read from the environment at run time and never printed or stored; a hit prints only the file and the kind.
#  - tables_agreed.md (and cells.json, the spec, CHANGES_v3.md, CHANGES_v2.md): BOM, CR, TAB, final newline, trailing
#    spaces, line count; tables_agreed.md: blank-line layout, absolute local paths outside HTML comments, "--" inside a
#    comment, every comment closed on its line;
#  - every text file under OUT: account / host / domain names, the home folder, user-folder paths, e-mail addresses.
import os, re, sys
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
files = {"tables_agreed.md": os.path.join(OUT, "reconcile", "tables_agreed.md"),
         "cells.json": os.path.join(OUT, "reconcile", "cells.json"),
         "TABLE_SPEC.md": os.path.join(OUT, "spec", "TABLE_SPEC.md"),
         "CHANGES_v3.md": os.path.join(OUT, "spec", "CHANGES_v3.md"),
         "CHANGES_v2.md": os.path.join(OUT, "spec", "CHANGES_v2.md")}
for name, f in files.items():
    b = open(f, "rb").read()
    t = b.decode("utf-8")
    body = t[:-1].split("\n") if t.endswith("\n") else t.split("\n")
    print("%-16s bytes %d | lines %d | BOM %s | CR %d | TAB %d | ends with exactly one LF %s | trailing-space lines %d | non-UTF-8 none"
          % (name, len(b), len(body), b.startswith(b"\xef\xbb\xbf"), b.count(b"\r"), b.count(b"\t"),
             t.endswith("\n") and not t.endswith("\n\n"), sum(1 for x in body if x != x.rstrip(" \t"))))

T = open(files["tables_agreed.md"], encoding="utf-8").read()
L = T[:-1].split("\n")
vis = [re.sub(r"<!--.*?-->", "", x) for x in L]
print("double blank lines: %d | first line is a comment: %s | last line: %r" % (
    sum(1 for i in range(1, len(L)) if L[i] == L[i - 1] == ""), L[0].startswith("<!--") and L[0].endswith("-->"), L[-1][:50]))
pat_abs = re.compile(r"(?i)\b[A-Z]:[\\/]|\\\\[A-Za-z]|/Users/|\\Users\\|/home/|AppData|Desktop|Downloads")
print("absolute local paths in visible text (outside HTML comments):", [i + 1 for i, x in enumerate(vis) if pat_abs.search(x)])
print("comments with a path outside D:/treeroute or relative paper/, engine/ paths:",
      [i + 1 for i, x in enumerate(L) for c in re.findall(r"<!--(.*?)-->", x)
       if re.search(r"(?i)\b[A-CE-Z]:[\\/]|/Users/|\\Users\\|AppData|Desktop|Downloads", c)])
cm = re.findall(r"<!--(.*?)-->", T)
print("HTML comments: %d | '--' inside a comment body: %d | unclosed '<!--' on a line: %d" % (
    len(cm), sum(1 for c in cm if "--" in c), sum(1 for x in L if x.count("<!--") != x.count("-->"))))

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
