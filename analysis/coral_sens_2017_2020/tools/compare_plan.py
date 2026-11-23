"""Compare a sensitivity plan folder (derived.json, plan.json) with the coral headline run's (read only; prints only).

    python -I -B compare_plan.py <sensitivity plan/run folder>

Prints the derived windows and cuts side by side (R3 Y_end, R4 Y0, R5 test years, R6 train end, R7 inner windows,
T-MARK counts, the bank cuts of R19, R10 leads, R12 router, R18 groups / donor-only / scored, R21 smoke groups),
then the list of the 120 derived entries whose value differs from the headline's, and plan.json's not-headline
fields. Day numbers are proleptic Gregorian ordinals (date.fromordinal).
"""
import datetime as dt
import json
import os
import sys

HEAD = r"D:\treeroute\runs\coral\headline\20261020_f3b8e3da"


def load(folder):
    return (json.load(open(os.path.join(folder, "derived.json"), encoding="utf-8")),
            json.load(open(os.path.join(folder, "plan.json"), encoding="utf-8")))


def day(x):
    try:
        return dt.date.fromordinal(int(x)).isoformat()
    except Exception:
        return x


def cut_of(entry):
    v = entry.get("value")
    if isinstance(v, dict):
        for k in ("cut", "cut_step", "cut_day", "fit_cut"):
            if k in v:
                return "%s (%s)" % (v[k], day(v[k]))
        return {k: v[k] for k in list(v)[:6]}
    return v


def main(sens):
    dh, ph = load(HEAD)
    ds, ps = load(sens)
    rows = [("R3 (Y_end)", dh["R3"]["value"], ds["R3"]["value"]),
            ("R4 (Y0)", dh["R4"]["value"], ds["R4"]["value"]),
            ("R5 (test window)", dh["R5"]["value"], ds["R5"]["value"]),
            ("R6 (train end)", dh["R6"]["value"], ds["R6"]["value"]),
            ("R7 (inner windows)", dh["R7"]["value"], ds["R7"]["value"]),
            ("R5:marks (T-MARK)", dh["R5:marks"]["value"], ds["R5:marks"]["value"]),
            ("R10 (leads)", dh["R10"]["value"], ds["R10"]["value"]),
            ("R12 (router)", dh["R12"]["value"], ds["R12"]["value"])]
    for k in sorted(x for x in dh if x.startswith("R19")):
        rows.append((k + " cut", cut_of(dh[k]), cut_of(ds.get(k, {}))))
    for name, a, b in rows:
        print("%-26s headline:    %s\n%-26s sensitivity: %s" % (name, json.dumps(a, default=str)[:900], "",
                                                                 json.dumps(b, default=str)[:900]))
    for key in ("groups", "donor_only_groups", "windows", "not_headline_reasons", "draft", "kind", "leads",
                "router_kind", "trees_per_group"):
        a, b = ph.get(key), ps.get(key)
        if isinstance(a, list) and len(a) > 8:
            print("plan.%-21s headline: %d items | sensitivity: %d items" % (key, len(a), len(b or [])))
        else:
            print("plan.%-21s headline: %s\n%-26s sensitivity: %s" % (key, json.dumps(a, default=str)[:600], "",
                                                                      json.dumps(b, default=str)[:600]))
    sc_h, sc_s = ph.get("scored_rows"), ps.get("scored_rows")
    if isinstance(sc_h, dict):
        print("plan.scored_rows: headline %d groups, %d rows | sensitivity %d groups, %d rows"
              % (sum(1 for v in sc_h.values() if v), sum(sc_h.values()), sum(1 for v in sc_s.values() if v),
                 sum(sc_s.values())))
        print("  scored groups (sensitivity): %s" % sorted(g for g, v in sc_s.items() if v))
    r21h, r21s = dh.get("R21", {}).get("value"), ds.get("R21", {}).get("value")
    print("R21 smoke groups: headline %s | sensitivity %s" % (json.dumps(r21h, default=str)[:300],
                                                              json.dumps(r21s, default=str)[:300]))
    only_h = sorted(set(dh) - set(ds))
    only_s = sorted(set(ds) - set(dh))
    same = sorted(k for k in set(dh) & set(ds) if dh[k].get("value") == ds[k].get("value"))
    diff = sorted(k for k in set(dh) & set(ds) if dh[k].get("value") != ds[k].get("value"))
    print("derived entries: headline %d, sensitivity %d; only headline %s; only sensitivity %s" % (len(dh), len(ds),
                                                                                                 only_h, only_s))
    print("entries with the SAME value (%d): %s" % (len(same), [k for k in same if not k.startswith("R23:fold=")]
                                                    + ["R23:fold=* x%d" % sum(k.startswith("R23:fold=") for k in same)]))
    print("entries whose value DIFFERS (%d): %s" % (len(diff), [k for k in diff if not k.startswith("R23:fold=")]
                                                    + ["R23:fold=* x%d" % sum(k.startswith("R23:fold=") for k in diff)]))


if __name__ == "__main__":
    main(sys.argv[1])
