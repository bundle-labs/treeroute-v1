"""Check a new version of report.md: every correction of the earlier versions present, every corrected wording gone.

Usage: py -3.12 -X utf8 -I -B regression_check2.py <report text> <regression_check.py>
Reads the first check's PHRASES (from regression_check.py) and adds the fourth version's; a phrase matches with
whitespace flattened. MUST-NOT phrases are the wordings that the checks found wrong.
"""
import ast
import sys

MORE = [
    ("Jaccard top-10 max 0.058", "top 10 0.058 (variable, bardl|lgbm)"),
    ("seven complete passes", "seven complete passes over the 50 files"),
    ("fire-only pass", "one fire-only pass at 18:45:43 (10 opens)"),
    ("byte reads by time", "5 at 18:43:43, 1 at 18:45:43, 5 at 18:46:03 and 5 at 18:49:41"),
    ("per_lead item 8", "item 8's nonzero-forecast rows and top-10 shares"),
    ("base-collation values", "share the base-collation (code-point) values"),
    ("bardl|lgbm example", "rival_bardl_h1|rival_lgbm, variable level: top-20-union Spearman 0.111 or 0.030"),
    ("section 3 pointer", "The main-row table is in section 3"),
    ("RBO bound 2.25e-5", "by at most 2.25e-5"),
    ("checked by hand", "was checked by hand, by the reconcile skeptic"),
    ("run records as source", "the run records (`meta.json`, the done records, the logs)"),
    ("scripts named", "`count_passes.py` (A1 item 3)"),
    ("maxima script", "bardl_maxima.py` gives the moves at full precision"),
    ("outputs named", "are saved in `V\\_lead\\outputs\\`"),
    ("keep-copy 3", "report.md.before_fix3"),
    ("A7 round 3 rows", "| 3 | final | regression 2:"),
    ("A7 header", "### A7. The report checks of the first three versions"),
    ("fourth version note", "this is the file's fourth version"),
    ("fourth version header", "## Lead's addendum (2026-11-16, fourth version)"),
]
MUST_NOT = [
    "top 10 0.059",
    "in six runs",
    "by at most 2.3e-5",
    "checks the same equalities",
    "A, B and the official files share these numbers",
    "this is the file's third version",
    "(2026-11-16, third version)",
    "this is its third version",
    "were checked against the official files\n> and `results.json` and stand",
]


def main():
    text_p, rc_p = sys.argv[1], sys.argv[2]
    with open(text_p, encoding="utf-8") as f:
        t = f.read()
    with open(rc_p, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    phrases = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(x, "id", "") == "PHRASES" for x in node.targets):
            phrases = ast.literal_eval(node.value)
    if phrases is None:
        raise SystemExit("PHRASES not found")
    flat = " ".join(t.split())
    superseded = [p for p in phrases if p[1] in MUST_NOT]
    for name, ph in superseded:
        print("superseded (now a must-not):", name, "|", ph)
    phrases = [p for p in phrases if p[1] not in MUST_NOT]
    missing = 0
    for name, ph in list(phrases) + MORE:
        ok = ph in t or " ".join(ph.split()) in flat
        missing += not ok
        if not ok:
            print("MISSING  %-30s %s" % (name, ph))
    present = 0
    for ph in MUST_NOT:
        if ph in t or " ".join(ph.split()) in flat:
            present += 1
            print("STILL THERE:", ph)
    print("phrases checked: %d, missing: %d; wordings that must be gone: %d, still there: %d"
          % (len(phrases) + len(MORE), missing, len(MUST_NOT), present))


if __name__ == "__main__":
    main()
