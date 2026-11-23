"""Visible text of the lines that the S3.13 write-up added to S1 and S4 (read only): occurrences of 'owner'.

Uses the diffs in work/ (made by c04_diff_live_staged.py); only '+' lines, HTML comments removed.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
W = os.path.join(HERE, "work")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for name in ("paper__draft__S1_disclosures.md.diff.txt", "paper__draft__S4_provenance.md.diff.txt"):
        with open(os.path.join(W, name), "r", encoding="utf-8") as fh:
            lines = fh.read().split("\n")
        for ln in lines:
            if not ln.startswith("+") or ln.startswith("+++"):
                continue
            vis = re.sub(r"<!--.*?-->", "", ln[1:])
            for m in re.finditer(r"\bowner\b", vis):
                s = max(0, m.start() - 80)
                print("%s: ...%s..." % (name[:24], vis[s:m.end() + 60]))
    print("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
