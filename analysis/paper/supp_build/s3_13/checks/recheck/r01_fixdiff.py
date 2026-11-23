# r01_fixdiff.py - recheck of the fix pass (S3.13 write-up, 2026-11-17). Read-only on STAGE and on the other checkers'
# folders. For each file the fixer edited: the staged bytes must have the fixer's post-fix SHA-256; undoing the recorded
# edits (work/applied_edits.json, new -> old, reverse order; each new text must occur exactly once) must reach the
# pre-fix SHA-256 of work/base_hashes.json. The pre-fix text is kept in memory only. Then: (1) the pre-fix hash is
# compared with the build checker's copy (the files it built and scanned), (2) the line diff pre-fix -> post-fix is
# written to fixdiff/<name>.txt in this folder (changed lines only, with the line numbers of the post-fix file).
# Run: py -3.9 -I -B r01_fixdiff.py
import difflib
import hashlib
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", ".."))
STAGE = os.path.join(OUT, "stage")
FIXW = os.path.join(STAGE, "_scripts", "fix", "work")
BUILDCOPY = os.path.join(OUT, "checks", "build", "copy")


def sha(b):
    return hashlib.sha256(b).hexdigest()


ap = json.load(open(os.path.join(FIXW, "applied_edits.json"), encoding="utf-8"))
bh = json.load(open(os.path.join(FIXW, "base_hashes.json"), encoding="utf-8"))
os.makedirs(os.path.join(HERE, "fixdiff"), exist_ok=True)
for rel, edits in ap["edits"].items():
    p = os.path.join(STAGE, *rel.split("/"))
    b = open(p, "rb").read()
    post = sha(b)
    res = ap["result"][rel]
    t = b.decode("utf-8")
    ok_undo = True
    for eid, old, new in reversed(edits):
        n = t.count(new)
        if n != 1:
            ok_undo = False
            print("  %s: %s new text occurs %d times" % (rel, eid, n))
            break
        t = t.replace(new, old)
    pre = sha(t.encode("utf-8"))
    print("%-42s post %s (record %s, %s) | undo -> %s (base %s, %s) | edits %d" % (
        rel, post[:12], res["post_sha"][:12], post == res["post_sha"], pre[:12], bh[rel]["base_sha"][:12],
        pre == bh[rel]["base_sha"] and ok_undo, len(edits)))
    bc = os.path.join(BUILDCOPY, *rel.split("/"))
    if os.path.exists(bc):
        print("   build checker's copy: %s, equal to pre-fix: %s" % (sha(open(bc, "rb").read())[:12],
                                                                     sha(open(bc, "rb").read()) == pre))
    # every edit's new text occurs once in the post-fix file, every old text no longer occurs (unless inside new)
    post_t = b.decode("utf-8")
    for eid, old, new in edits:
        c_new = post_t.count(new)
        c_old = post_t.count(old)
        if c_new != 1 or (c_old and old not in new):
            print("   EDIT %s: new x%d, old x%d" % (eid, c_new, c_old))
    a = t.replace("\r\n", "\n").split("\n")
    s = post_t.replace("\r\n", "\n").split("\n")
    sm = difflib.SequenceMatcher(None, a, s, autojunk=False)
    lines = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        lines.append("@@ pre %d-%d -> post %d-%d (%s)" % (i1 + 1, i2, j1 + 1, j2, tag))
        for x in a[i1:i2]:
            lines.append("- " + x)
        for x in s[j1:j2]:
            lines.append("+ " + x)
    with open(os.path.join(HERE, "fixdiff", rel.replace("/", "__") + ".txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print("   changed line groups:", sum(1 for x in lines if x.startswith("@@")))
