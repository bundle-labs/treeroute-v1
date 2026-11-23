"""Diff three REVIEW build reports: the live build's last one (ROOT/paper/build), the baseline rebuilt from the
live files (copy_live) and the test build with the staged files (copy). Prints to the screen only.
Run: py -3.9 -I -B b03_report_diff.py
"""
import difflib
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHK = HERE.parent
OUT = CHK.parent.parent
ROOT = OUT.parent.parent.parent
NAME = "build_report_REVIEW.md"
live = (ROOT / "paper" / "build" / NAME).read_text(encoding="utf-8").splitlines()
base = (CHK / "copy_live" / "paper" / "build" / NAME).read_text(encoding="utf-8").splitlines()
test = (CHK / "copy" / "paper" / "build" / NAME).read_text(encoding="utf-8").splitlines()


def show(a, b, la, lb):
    print("=" * 30, la, "->", lb)
    for ln in difflib.unified_diff(a, b, la, lb, n=0, lineterm=""):
        print(ln[:400])


show(live, base, "live last REVIEW", "baseline rebuild")
show(base, test, "baseline rebuild", "staged test build")
