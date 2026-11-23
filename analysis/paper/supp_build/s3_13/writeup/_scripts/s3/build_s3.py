"""Build STAGE/paper/draft/S3_posthoc.md: the live file plus Supplement S3.13 and its header and index edits (writer s3).

Usage: py -3.9 -I -B build_s3.py
- Reads the LIVE paper/draft/S3_posthoc.md (read only; SHA-256 checked), the agreed tables
  (paper/supp_build/s3_13/reconcile/tables_agreed.md, version 5) and the prose template s313_template.md.
- Inserts the 13 table blocks (Tables S3.18-S3.30) byte for byte, each with its caption, notes and source comment,
  in the agreed order; changes one caption (Table S3.21) for the listed point of the last table check.
- Fills every prose number from s3lib.tokens() (each formatted once from its stored value).
- Applies the header-comment and S3.0 edits at exact anchors (each must occur exactly once).
- Writes only STAGE/paper/draft/S3_posthoc.md (UTF-8 without BOM, LF, as the live file).
"""
import importlib.util
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("s3lib", os.path.join(HERE, "s3lib.py"))
L = importlib.util.module_from_spec(spec)
spec.loader.exec_module(L)

LIVE = os.path.join(L.ROOT, "paper", "draft", "S3_posthoc.md")
LIVE_SHA = "373537b8e454094559c1bb9ed7b0ba8423468f063f19f2ae39a21bb67c232191"
DST = os.path.join(L.STAGE, "paper", "draft", "S3_posthoc.md")
TEMPLATE = os.path.join(HERE, "s313_template.md")
ORDER = ["S3.%d" % i for i in range(18, 31)]

S321_OLD = ("The fitted trees were not kept, so each problem's tree bank and the sampled locations' routers were "
            "rebuilt with the run's own engine code;")
S321_NEW = ("The fitted trees were not kept, so each problem's tree bank with its correctors and placebos, and the "
            "sampled locations' routers, were rebuilt with the run's own engine code;")

H_EDIT = ("S3.13 write-up, 2026-11-17: new section S3.13 after S3.12, the post hoc SHAP comparison of Part 628 "
          "(rulings AK, AW, AY, AZ1, BA and BB). Its Tables S3.18 to S3.30 were inserted by script, byte for byte, "
          "from paper/supp_build/s3_13/reconcile/tables_agreed.md (version 5), in its order and with every caption, "
          "note and source comment, without that file's draft headings and line-1 comment; Table 9 (Section 5.4) is "
          "cited, not repeated. One caption was changed, for a point of the last table check: Table S3.21's now "
          "says that each problem's tree bank with its correctors and placebos, and the sampled locations' routers, "
          "were rebuilt; no table cell changed. S3.0's index gains the S3.13 row and its facts comment; the rulings "
          "and Parts listed below gain AW, AY, AZ1, BA, BB and 628; NUMBER SOURCES and STATUS gain S3.13's "
          "sentences. S3.13's prose numbers cite the new facts A9 to A25 of PAPER_FACTS.md section 9 (final, post "
          "hoc (Part 628)). No existing number changed; pre-edit copy draft/_snapshots/@@SNAP@@/. ")
RUL_OLD = ("Ruling AN2 (the alarm replay re-computed twice). Experiment log: engine/PENDING_PARTS.md Parts 601-606, "
           "611, 612, 622, 623, 624, 625.")
RUL_NEW = ("Ruling AN2 (the alarm replay re-computed twice). Rulings AW, AY, AZ1, BA and BB (the SHAP comparison of "
           "S3.13). Experiment log: engine/PENDING_PARTS.md Parts 601-606, 611, 612, 622, 623, 624, 625, 628.")
NS_ANCHOR = " No number was typed from memory or from a draft."
NS_ADD = (" Every number in Tables S3.18 to S3.30 (Section S3.13, Part 628) is copied byte for byte from "
          "paper/supp_build/s3_13/reconcile/tables_agreed.md, version 5: the tables were built twice from the "
          "stored values, each printed number formatted once, by two independent builders' scripts, "
          "paper/supp_build/s3_13/A/scripts/build_tables.py and paper/supp_build/s3_13/B/scripts/build_tables.py, "
          "under the rules of paper/supp_build/s3_13/spec/TABLE_SPEC.md, and then reconciled and checked (versions 2 "
          "to 5 reworded captions, notes, labels and cells after four checks and changed no number); "
          "paper/supp_build/s3_13/reconcile/cells.json gives each printed data number's source, selector and stored "
          "value, and each table's source comment names its files (under D:/treeroute/analysis/shap_v1: the "
          "comparison's files in out/, the independent re-computation's verify_v1/A/results.json and the B1 runs' "
          "logs). The prose numbers of S3.13 come from facts A9 to A25, each formatted once from the stored value "
          "that the fact names.")
ST_ANCHOR = " Pending items are marked [PENDING: ...]. -->"
ST_NEW = (" Pending items are marked [PENDING: ...]. S3.13 (Part 628) is post hoc and report-only as well: its facts "
          "are \"final, post hoc (Part 628)\", it holds no PENDING or OWNER marker, and treeroute v1's B1 "
          "sensitivity there is labelled a sensitivity and kept apart from the main comparison. -->")
IDX_ANCHOR = ("| S3.12 | The engine-v2 alarm replay, re-computed twice (values in Supplement S5.3 only) | 2026-10-28 (625) "
              "| The replay numbers had been computed once with treeroute v2's tools; ruling AN2 required two "
              "independent re-computations and a logged Part before Supplement S5 quotes them |\n")
IDX_ROW = ("| S3.13 | SHAP comparison of treeroute v1 and its rivals at the nowcast, with treeroute v1's B1 sensitivity "
           "| 2026-11-12 to 2026-11-16 (628) | SHAP had been left out of treeroute v1's results; we asked what each "
           "model uses and how far treeroute v1 and its rivals agree (ruling AW) |\n")
FC_EDITS = [
    ("S3.12 V3, K90 (final, post hoc (Part 625)). Dates:",
     "S3.12 V3, K90 (final, post hoc (Part 625)); S3.13 A9 (dates), A10 (final, post hoc (Part 628)). Dates:"),
    ("625: 2026-10-28, POST HOC);",
     "625: 2026-10-28, POST HOC; 628: 2026-11-12, DRAFT, with its dated addendum of 2026-11-17);"),
    ("AN (2026-10-28). -->",
     "AN (2026-10-28), AW (2026-11-12), AY (2026-11-13), AZ (2026-11-14), BA (2026-11-15), BB (2026-11-16); "
     "S3.13's run dates are those of the SHAP protocol's change log and sample register (A9). -->"),
]
SEC_ANCHOR = ("The alarm is not part of treeroute v1: no locked number, verdict or adoption changes, and it has never "
              "run on new data. <!-- V2, K90 -->\n\n<!-- Cross-check pass")


def table_blocks():
    with open(L.TABLES, encoding="utf-8", newline="") as f:
        text = f.read()
    if "\r" in text:
        raise SystemExit("tables_agreed.md holds CR")
    lines = text.split("\n")
    starts = []
    for i, ln in enumerate(lines):
        m = re.match(r"^\*\*Table (S3\.\d+) \(post hoc", ln)
        if m:
            starts.append((i, m.group(1)))
    names = [n for _, n in starts]
    if names != ORDER:
        raise SystemExit("unexpected table order: %r" % names)
    blocks = {}
    for k, (i, name) in enumerate(starts):
        j = len(lines)
        for jj in range(i + 1, len(lines)):
            if lines[jj].startswith("**Table ") or lines[jj].startswith("## "):
                j = jj
                break
        blk = lines[i:j]
        while blk and blk[-1] == "":
            blk.pop()
        blocks[name] = "\n".join(blk)
        if blocks[name] not in text:
            raise SystemExit("block not verbatim: " + name)
    return blocks, text


def replace_once(s, old, new, what):
    n = s.count(old)
    if n != 1:
        raise SystemExit("%s: anchor occurs %d times" % (what, n))
    return s.replace(old, new)


def main():
    with open(LIVE, "rb") as f:
        raw = f.read()
    if L.sha256_bytes(raw) != LIVE_SHA:
        raise SystemExit("live S3_posthoc.md changed since it was staged: stop")
    if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw:
        raise SystemExit("live file has a BOM or CR")
    live = raw.decode("utf-8")
    blocks, tables_text = table_blocks()
    blocks["S3.21"] = replace_once(blocks["S3.21"], S321_OLD, S321_NEW, "S3.21 caption")
    tok, _src, _cells = L.tokens()
    with open(TEMPLATE, encoding="utf-8", newline="") as f:
        tpl = f.read()
    if "\r" in tpl:
        raise SystemExit("template holds CR")
    used = set(re.findall(r"\{\{([A-Z0-9_]+)\}\}", tpl))
    missing = used - set(tok)
    if missing:
        raise SystemExit("tokens without a value: %r" % sorted(missing))
    sec = re.sub(r"\{\{([A-Z0-9_]+)\}\}", lambda m: tok[m.group(1)], tpl)
    for name in ORDER:
        sec = replace_once(sec, "@@TABLE %s@@" % name, blocks[name], "table marker " + name)
    if "{{" in sec or "@@TABLE" in sec:
        raise SystemExit("unfilled marker left")
    sec = sec.rstrip("\n")
    out = live
    if not out.startswith("<!-- Tier 1 length plan (2026-11-12, ruling AU7): cross-cutting pass:"):
        raise SystemExit("line 1 does not start as expected")
    out = "<!-- " + H_EDIT + out[len("<!-- "):]
    out = replace_once(out, RUL_OLD, RUL_NEW, "rulings list")
    out = replace_once(out, NS_ANCHOR, NS_ADD + NS_ANCHOR, "NUMBER SOURCES")
    out = replace_once(out, ST_ANCHOR, ST_NEW, "STATUS")
    out = replace_once(out, IDX_ANCHOR, IDX_ANCHOR + IDX_ROW, "index row")
    for old, new in FC_EDITS:
        out = replace_once(out, old, new, "facts comment")
    out = replace_once(out, SEC_ANCHOR,
                       SEC_ANCHOR.replace("\n\n<!-- Cross-check pass", "\n\n" + sec + "\n\n<!-- Cross-check pass"),
                       "section insertion")
    if not out.endswith("-->\n"):
        raise SystemExit("file end changed")
    data = out.encode("utf-8")
    os.makedirs(os.path.dirname(DST), exist_ok=True)
    with open(DST, "wb") as f:
        f.write(data)
    print("written", DST)
    print("bytes", len(data), "sha256", L.sha256_bytes(data), "lines", out.count("\n"))
    print("tables_agreed.md sha256", L.sha256_bytes(tables_text.encode("utf-8")))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
