"""Report check 3: what the third version's lead text (note + addendum) dropped from the second and the first.
Splits the lead's note and the addendum (minus A2-A3, which are byte-identical) into sentences, normalises
whitespace, and lists the sentences of an earlier version that the third version does not contain verbatim,
each with its closest third-version sentence. Read-only. Run: py -3.9 -I -B c06_addendum_diff.py
"""
import difflib
import os
import re

R = r"D:\treeroute\analysis\shap_v1\verify_v1\reconcile"


def lead_text(path):
    with open(path, "rb") as f:
        t = f.read().decode("utf-8")
    i = t.find("# Round 14 reconciliation")
    note = t[:i]
    j = t.find("## Lead's addendum")
    add = t[j:]
    a2 = add.find("### A2.")
    a4 = add.find("### A4.")
    add = add[:a2] + add[a4:]
    txt = note + "\n" + add
    txt = re.sub(r"^> ?", "", txt, flags=re.M)
    return txt


def sentences(txt):
    # table rows are kept whole; prose is joined and split on sentence ends
    out = []
    prose = []
    for ln in txt.split("\n"):
        if ln.startswith("|"):
            out.append(ln.strip())
        else:
            prose.append(ln.strip())
    p = " ".join(x for x in prose if x)
    p = re.sub(r"\s+", " ", p)
    for s in re.split(r"(?<=[.;:!?])\s+(?=[A-Z(*\-0-9`\"])", p):
        s = s.strip()
        if len(s) > 3:
            out.append(s)
    return out


def main():
    v1 = sentences(lead_text(os.path.join(R, "report.md.before_fix1")))
    v2 = sentences(lead_text(os.path.join(R, "report.md.before_fix2")))
    v3 = sentences(lead_text(os.path.join(R, "report.md")))
    v3set = set(v3)
    v3join = " ".join(v3)
    for tag, old in (("v2", v2), ("v1", v1)):
        missing = [s for s in old if s not in v3set and s not in v3join]
        print("== %s sentences or table rows not in v3 verbatim: %d of %d" % (tag, len(missing), len(old)))
        for s in missing:
            best = difflib.get_close_matches(s, v3, n=1, cutoff=0.0)
            ratio = difflib.SequenceMatcher(None, s, best[0]).ratio() if best else 0.0
            print("-- [%s] %s" % (tag, s[:400]))
            print("   closest v3 (%.2f): %s" % (ratio, best[0][:400] if best else ""))
        print()


if __name__ == "__main__":
    main()
