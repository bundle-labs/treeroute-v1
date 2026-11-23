"""Write catalog.yaml and ban.yaml of the coral package draft from columns.py (package-side tooling, not engine code).

    py -3.9 make_draft.py [--package D:/treeroute/coral_build/engine/datasets/coral_draft]

Written 2026-10-19 (SPEC_CORAL_TABLES.md section 6). One column list (columns.py) feeds the builder and both files,
so the closed world holds by construction: every written column has a catalog entry, and every non-key column has
one verdict. Overwrites only those two files, only under D:/treeroute/coral_build.
"""
import argparse
import os
import sys
from collections import Counter

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from columns import COLUMNS, NOT_WRITTEN  # noqa: E402

KEY_ROLES = ("key_row", "key_unit", "key_group", "key_lat", "key_lon", "key_time", "key_issue", "key_feature_end",
             "key_mark")
TARGET_FACTS = {
    "legal_range": [0, 100],
    "legal_range_source": ("percent of colonies (Reef Check: of the 4 transect segments, each a percentage, averaged) "
                           "bleached: a percentage by the survey protocols (GCBD Bleaching_tbl Percent_Bleached and "
                           "S1-S4; coral_smoke_regress.py:9-14); values outside [0, 100] are dropped by the recipe "
                           "(coral_smoke_regress.py:73)"),
    "window": {"length": 1, "unit": "day", "align": "backward"},
    "stamp": "event_date",
}

CATALOG_HEAD = """# catalog.yaml -- coral_draft package facts (SPEC_TABLE_MODE.md 1.3-1.5). GENERATED 2026-10-19 by
# D:/treeroute/coral_build/coral_tables/make_draft.py from columns.py; edit columns.py, not this file. UNSIGNED.
# Every written column of every lead file is declared here (closed world on columns, T-COLUMNS). A role is not a
# verdict: the verdicts are in ban.yaml. No store catalog: in a table the engine computes no lag (ruling U1), so the
# timing of each feature is in its 'provenance' text and the owner vouches for it (ruling U2, AUDIT_CHECKLIST.md B).
# Words in the provenance texts: T target date, A feature anchor (= T, or the month's first day for a month-precision
# visit), L lead in days, C = A - L the feature cut; every data value used is dated strictly before C, and C is never
# later than the issue date T - L.
# The target window is one day, stamp event_date: T is the label's last content day (SPEC_TABLE_MODE.md 1.3, 1.5).
# For a month-precision visit T is the month's last day, so the label is surely known after T, and its features end
# before the month starts (A). fact_status is 'unverified' everywhere (the schema default): nothing here is signed.
"""

BAN_HEAD = """# ban.yaml -- coral_draft verdicts (SPEC_TABLE_MODE.md 1.4; schema treeroute/package/schema.py:446-474). GENERATED
# 2026-10-19 by D:/treeroute/coral_build/coral_tables/make_draft.py from columns.py. UNSIGNED: the verdicts follow
# CORAL_ENGINE_PLAN.md:153-176 (section C3), whose open questions are Q9, Q10 and Q22 (:254-255, :267). The owner
# signs them before the coral freeze (ruling U6). A 'freeze' verdict is refused for tables (R9; SPEC 1.4).
# Closed world: one verdict per non-key column of catalog.yaml (%d entries). Counts: %s.
# Columns of the legacy 77 frame that are NOT written to the lead files (so they need no verdict here):
%s
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--package", default=r"D:\treeroute\coral_build\engine\datasets\coral_draft")
    A = ap.parse_args()
    if not os.path.abspath(A.package).lower().startswith(r"d:\treeroute\coral_build".lower()):
        raise SystemExit("refused: --package must be under D:\\treeroute\\coral_build")
    names = [c["name"] for c in COLUMNS]
    if len(set(names)) != len(names):
        raise SystemExit("duplicate column names in columns.py")
    cat = {}
    for c in COLUMNS:
        e = {"role": c["role"]}
        if c.get("calendar_part"):
            e["calendar_part"] = c["calendar_part"]
        if c["role"] == "target":
            e.update(TARGET_FACTS)
        if c.get("provenance"):
            e["provenance"] = c["provenance"]
        cat[c["name"]] = e
    ban = {}
    for c in COLUMNS:
        if c["role"] in KEY_ROLES:
            continue
        if c["verdict"] is None:
            raise SystemExit("non-key column %s has no verdict" % c["name"])
        ban[c["name"]] = {"verdict": c["verdict"], "reason": c["reason"], "evidence": c["evidence"]}
    counts = Counter(v["verdict"] + (":" + v["reason"] if v["verdict"] == "ban" else "") for v in ban.values())
    dump = dict(sort_keys=False, allow_unicode=False, width=4096, default_flow_style=False)
    with open(os.path.join(A.package, "catalog.yaml"), "w", encoding="utf-8", newline="\n") as f:
        f.write(CATALOG_HEAD)
        f.write(yaml.safe_dump({"columns": cat}, **dump))
    nw = "\n".join("#   - %s: %s" % (k, v) for k, v in NOT_WRITTEN.items())
    with open(os.path.join(A.package, "ban.yaml"), "w", encoding="utf-8", newline="\n") as f:
        f.write(BAN_HEAD % (len(ban), ", ".join("%s %d" % kv for kv in sorted(counts.items())), nw))
        f.write(yaml.safe_dump({"verdicts": ban}, **dump))
    print("catalog: %d columns | ban: %d verdicts %s" % (len(cat), len(ban), dict(counts)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
