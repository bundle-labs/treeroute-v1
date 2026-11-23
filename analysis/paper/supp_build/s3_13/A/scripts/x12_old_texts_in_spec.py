# -*- coding: utf-8 -*-
# Exploration only (prints to console; writes nothing): where the version-3 texts that version 4 replaces (the OLD
# printed texts quoted in OUT\spec\CHANGES_v4.md) and their NEW texts still occur in OUT\spec\TABLE_SPEC.md
# (version 4): fenced, backticked, or plain; with the spec line numbers.
# Run as: py -3.9 -I -B <this script>
import sys
import os

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(os.path.dirname(HERE))
with open(os.path.join(OUT, "spec", "TABLE_SPEC.md"), "r", encoding="utf-8") as f:
    SL = f.read().split("\n")
with open(os.path.join(OUT, "spec", "CHANGES_v4.md"), "r", encoding="utf-8") as f:
    CH = f.read().split("\n")
infence = []
inb = False
for x in SL:
    if x.startswith("```"):
        inb = not inb
        infence.append(False)
        continue
    infence.append(inb)
flat = " ".join(SL)
i = 0
sec = None
while i < len(CH):
    line = CH[i]
    if line.startswith("## "):
        sec = line[3:].split(".")[0]
    if line.startswith("```"):
        j = i + 1
        body = []
        while not CH[j].startswith("```"):
            body.append(CH[j])
            j += 1
        k = i - 1
        while k >= 0 and CH[k].strip() == "":
            k -= 1
        para = []
        while k >= 0 and CH[k].strip() != "" and not CH[k].startswith("```"):
            para.insert(0, CH[k].strip())
            k -= 1
        label = " ".join(para)
        text = " ".join(x.strip() for x in body)
        hits = [(n + 1, "fenced" if infence[n] else ("backticked" if ("`" + text + "`") in SL[n] else "plain"))
                for n, x in enumerate(SL) if text in x]
        print("%s | %s | %d lines | %r" % (sec, label[-60:], len(body), text[:70]))
        print("    in the v4 spec: %s%s" % (", ".join("L%d %s" % h for h in hits) or "nowhere",
                                           ("; backticked across a line break" if not hits and ("`" + text + "`") in flat
                                            else "")))
        i = j + 1
        continue
    i += 1
