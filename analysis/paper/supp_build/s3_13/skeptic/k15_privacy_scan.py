# Skeptic (version 2 check, item 5): privacy scan of every text file under OUT (the spec, the builders', the
# reconciler's and the skeptic's files). The account, host and domain names are read from the environment at run time
# and are never printed or stored; a hit prints only the file and the kind of hit. Read-only; prints only.
import os, re, sys
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
names = {k: os.environ.get(k, "") for k in ("USERNAME", "COMPUTERNAME", "USERDOMAIN")}
names["home folder name"] = os.path.basename(os.path.expanduser("~"))
names = {k: v for k, v in names.items() if len(v) >= 3}
home = os.path.expanduser("~").lower()
pats = {"user-folder path": re.compile(r"(?i)[a-z]:[\\/]+users[\\/]+(?!public)[^\\/\s\"']+"),
        "e-mail address": re.compile(r"[\w.+-]+@[\w-]+\.[a-z]{2,}", re.I),
        "uuid-like id": re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I)}
n_files = hits = 0
for d, _, fs in os.walk(OUT):
    for f in fs:
        if not f.lower().endswith((".py", ".md", ".json", ".txt", ".csv")):
            continue
        p = os.path.join(d, f)
        try:
            t = open(p, encoding="utf-8", errors="replace").read()
        except OSError as ex:
            print("cannot read", os.path.relpath(p, OUT), ex)
            continue
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
