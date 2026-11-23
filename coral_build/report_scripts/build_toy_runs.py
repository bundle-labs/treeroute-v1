"""Build SYNTHETIC toy run folders for testing coral_report.py (never real data).

Uses the engine's own toy table package (engine/tests/table_toy.py) and its smoke helper, exactly as
tests/test_table_mode_pipeline.py and tests/test_table_donor_only.py do. Writes under
D:/treeroute/coral_build/report_scripts/toy_runs/<variant>/ and prints each finished run folder.

    py -3.9 build_toy_runs.py [--engine <LIVE engine folder>] [--root <toy_runs folder>]

Existing variant folders are never deleted: a variant whose folder exists is skipped (move it aside to rebuild).
"""
import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_ENGINE = Path(r"C:\Users\moh the ghost\Desktop\data set for reserch paper\engine")
VARIANTS = ("ok", "donor_only_group")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--engine", default=str(DEFAULT_ENGINE))
    ap.add_argument("--root", default=str(HERE / "toy_runs"))
    args = ap.parse_args(argv)
    engine = Path(args.engine)
    for p in (engine, engine / "tests"):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    from table_toy import build_toy_table_package, patch_sklearn, run_toy  # noqa: E402

    root = Path(args.root)
    root.mkdir(parents=True, exist_ok=True)
    undo = patch_sklearn()
    try:
        for v in VARIANTS:
            base = root / v
            if base.exists():
                print("SKIP %s (exists): move it aside to rebuild" % base)
                continue
            base.mkdir(parents=True)
            pkg = build_toy_table_package(base / "pk", v)
            folder = run_toy(pkg, base)
            (base / "RUN_FOLDER.txt").write_text(str(folder) + "\n", encoding="utf-8")
            print("TOY RUN %s -> %s" % (v, folder))
    finally:
        undo()


if __name__ == "__main__":
    main()
