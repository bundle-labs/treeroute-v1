"""Add two rows to STAGE/paper/draft/GLOSSARY.md: share distance and family-share distance; D8 tolerance (writer s3).

Usage: py -3.9 -I -B build_glossary.py
Starts from work/paper__draft__GLOSSARY.md.base (the glossary writer's staged copy, SHA-256 b40954b2...), inserts the
rows after the row "sign agreement" (the last row of the table) and extends that writer's S3.13 history comment by one
sentence. The file's UTF-8 without BOM and CRLF line endings are kept. Writes only STAGE/paper/draft/GLOSSARY.md.
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("s3lib", os.path.join(HERE, "s3lib.py"))
L = importlib.util.module_from_spec(spec)
spec.loader.exec_module(L)

BASE = os.path.join(HERE, "work", "paper__draft__GLOSSARY.md.base")
BASE_SHA = "b40954b2a89c77b15fc4b24d8b8f54081be58425101a1b33130f4bd97b3b50c9"
DST = os.path.join(L.STAGE, "paper", "draft", "GLOSSARY.md")
ROW = ("| **share distance** (TV); **family-share distance** | tvd, tvd_family (code) | For a pair of models, the "
       "total-variation distance between their shares over J (the share distance) and between their five family "
       "shares (the family-share distance); at the feature level the family-share distance is the variable-level "
       "value repeated, because families are sums of variable-level attributions (ruling BB2). <!-- SHAP protocol "
       "D:/treeroute/analysis/shap_v1/PROTOCOL.md section 8 (pairwise statistics: the total-variation distance between "
       "shares and between family shares); Tables S3.23-S3.28, columns \"Share distance (TV)\" and \"Family-share "
       "distance (TV)\" and note §; code names from the selectors of paper/supp_build/s3_13/reconcile/cells.json "
       "(statistic=tvd, tvd_family); ruling BB2. Row added by the writer of S3.13's prose, which names the two "
       "distances. --> | S3.13 |")
ROW2 = ("| **D8 tolerance** | arcsine tolerance, relative tolerance | The allowance for treeroute v1's "
        "rebuilt arcsine arms (burned fraction and coral bleaching) in the SHAP comparison's exactness checks: a "
        "relative difference of at most 10⁻¹² from the saved prediction, exact equality where the saved value is 0, "
        "licensed by gate E5a; every other arm and model must reproduce its saved predictions bit for bit (ruling "
        "AY3). Not the identity tolerance. <!-- SHAP protocol D:/treeroute/analysis/shap_v1/PROTOCOL.md sections 4.1 "
        "(gate E8) and 12 (decision D8; ruled 2026-11-13); rulings file AY3; Table S3.20 note c; Table S3.21 note on "
        "D8. Row added by the writer of S3.13's prose, which uses the term. --> | S3.13 |")
HIST_OLD = " No existing row changed. -->"
HIST_NEW = (" The writer of S3.13's prose then added two rows after sign agreement: share distance and family-share "
            "distance, and D8 tolerance. No existing row changed. -->")


def main():
    with open(BASE, "rb") as f:
        raw = f.read()
    if L.sha256_bytes(raw) != BASE_SHA:
        raise SystemExit("base copy changed")
    if raw.startswith(b"\xef\xbb\xbf"):
        raise SystemExit("BOM")
    text = raw.decode("utf-8")
    if text.count("\r\n") != text.count("\n"):
        raise SystemExit("not CRLF throughout")
    lines = text.split("\r\n")
    idx = [i for i, ln in enumerate(lines) if ln.startswith("| **sign agreement** (on the top-10 union) |")]
    if len(idx) != 1 or lines[idx[0] + 1] != "":
        raise SystemExit("sign agreement row not found as the last row")
    if any(ln.startswith("| **share distance**") or ln.startswith("| **D8 tolerance**") for ln in lines):
        raise SystemExit("row already present")
    lines.insert(idx[0] + 1, ROW)
    lines.insert(idx[0] + 2, ROW2)
    out = "\r\n".join(lines)
    if out.count(HIST_OLD) != 1:
        raise SystemExit("history anchor occurs %d times" % out.count(HIST_OLD))
    last = out.rstrip("\r\n").split("\r\n")[-1]
    if HIST_OLD not in last or not last.startswith("<!-- S3.13 write-up, 2026-11-17"):
        raise SystemExit("history anchor is not in the S3.13 comment")
    out = out.replace(HIST_OLD, HIST_NEW)
    data = out.encode("utf-8")
    with open(DST, "wb") as f:
        f.write(data)
    print("written", DST, "bytes", len(data), "sha256", L.sha256_bytes(data), "CRLF", data.count(b"\r\n"),
          "LF", data.count(b"\n"))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
