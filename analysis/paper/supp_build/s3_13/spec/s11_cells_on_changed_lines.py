# s11_cells_on_changed_lines.py - version 2 of TABLE_SPEC.md (2026-11-17). Read-only: which version-1 cells.json
# entries (builder A's file; B's differs only in panel f's part names) sit on a tables.md line that version 2
# changes, and whether their `cell` text changes. Prints only. Run: py -3.9 -I -B s11_cells_on_changed_lines.py
import collections
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")
CHANGED = [1, 5, 65, 66, 67, 121, 122, 144, 146, 155, 171, 174, 251, 256, 342, 344, 348, 451, 457, 543, 548, 661,
           711, 784]  # from s10_check_new_texts.py
with open("../A/cells.json", encoding="utf-8") as fh:
    doc = json.load(fh)
with open("../reconcile/tables_agreed.md", encoding="utf-8") as fh:
    lines = fh.read().split("\n")
print("keys:", list(doc), "spec:", doc["spec"], "entries:", len(doc["entries"]))
c = collections.Counter()
for e in doc["entries"]:
    if e["line"] in CHANGED:
        full_line = e["cell"] == lines[e["line"] - 1]
        c[(e["line"], e["table"], e["row"] if e["row"] == "note" else "<row>", "cell = whole line" if full_line
           else "cell = one table cell")] += 1
for k, n in sorted(c.items()):
    print(n, "entries on", k)
print("entries with part 'share' in panel f:", sum(1 for e in doc["entries"] if e["panel"] == "f"))
print("max line of an entry:", max(e["line"] for e in doc["entries"]), "of", len(lines) - 1, "lines")
