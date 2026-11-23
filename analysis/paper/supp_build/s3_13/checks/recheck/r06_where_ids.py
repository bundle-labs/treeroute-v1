# r06_where_ids.py - where do workflow-id, UUID-shaped and e-mail-shaped strings sit in the given text files: line number
# and whether inside an HTML comment (which the build strips); the string itself is never printed. For .docx files, the
# XML and .rels parts are decompressed (as the build reads them) and only counts per part are printed.
# Usage: py -3.9 -I -B r06_where_ids.py <file> [...]
import os
import re
import sys
import zipfile

PATS = {
    "workflow id": re.compile(r"\bwf_[0-9a-f]{6,}", re.I),
    "UUID-shaped id": re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I),
    "e-mail address": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
}
for p in sys.argv[1:]:
    name = os.path.basename(p)
    if p.lower().endswith(".docx"):
        with zipfile.ZipFile(p) as z:
            for n in z.namelist():
                if n.endswith((".xml", ".rels")):
                    t = z.read(n).decode("utf-8", "replace")
                    for k, rx in PATS.items():
                        c = len(rx.findall(t))
                        if c:
                            print("%s part %s: %s %d" % (name, n, k, c))
        print("%s: XML parts scanned" % name)
        continue
    t = open(p, "rb").read().decode("utf-8", "replace")
    spans = [(m.start(), m.end()) for m in re.finditer(r"<!--.*?-->", t, flags=re.S)]
    for k, rx in PATS.items():
        for m in rx.finditer(t):
            inside = any(a <= m.start() < b for a, b in spans)
            line = t.count("\n", 0, m.start()) + 1
            # context words only (no part of the match): the 30 characters before it, digits and hex masked
            before = re.sub(r"[0-9a-fA-F]", "#", t[max(0, m.start() - 30):m.start()].replace("\n", " "))
            print("%s: %s at line %d, %s; before: ...%s" % (name, k, line, "inside a comment" if inside else "VISIBLE", before))
