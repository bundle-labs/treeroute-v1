"""(Recheck copy of the build checker's b01, 2026-11-17: run from OUT/checks/recheck/scripts/, so CHK is the recheck
folder; figures limited to the files the build reads, see live_inputs.)
Make two copies of what the paper build reads, keeping the layout relative to ROOT:
  copy_live/  the live files only (baseline build)
  copy/       the same, with the staged paper files laid over them (test build)
Writes only under this check folder (checks/build/). Paths are derived from this file's place,
so no machine path is written anywhere. Run: py -3.9 -I -B b01_make_copies.py
"""
import hashlib
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent          # .../checks/build/scripts
CHK = HERE.parent                               # .../checks/build
OUT = CHK.parent.parent                         # .../supp_build/s3_13
STAGE = OUT / "stage"
ROOT = OUT.parent.parent.parent                 # the research-paper folder
assert (ROOT / "paper" / "build" / "build_docx.py").is_file(), "ROOT not found"
assert (ROOT / "engine").is_dir()


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


def live_inputs():
    """Relative paths (to ROOT) of every file the build can read."""
    rels = ["engine/OWNER_RULINGS_2026-10-06.md",
            "paper/build/build_docx.py", "paper/build/BUILD_README.md",
            "paper/build/reference.docx", "paper/build/citation_aliases.json"]
    if (ROOT / "paper/build/author.json").exists():
        rels.append("paper/build/author.json")
    d = ROOT / "paper" / "draft"
    rels += ["paper/draft/" + p.name for p in sorted(d.iterdir()) if p.is_file()]
    for sub in ("submission", "tables"):
        rels += ["paper/draft/%s/%s" % (sub, p.name) for p in sorted((d / sub).iterdir()) if p.is_file()]
    # recheck copy (2026-11-17): only the figure files the build reads (build_docx.py load_figures: each folder's
    # *_caption.md and <folder>.png; GRAPHICAL_ABSTRACT: ga/ga.tif and ga/ga.pdf, checked for existence), so that the
    # figure scripts and data CSVs, which hold an earlier account name, are not copied.
    fig = ROOT / "paper" / "figures"
    for d in sorted(p for p in fig.iterdir() if p.is_dir()):
        for p in sorted(d.glob("*_caption.md")):
            rels.append(p.relative_to(ROOT).as_posix())
        png = d / (d.name + ".png")
        if png.is_file() and any(d.glob("*_caption.md")):
            rels.append(png.relative_to(ROOT).as_posix())
    for name in ("ga.tif", "ga.pdf"):
        if (fig / "ga" / name).is_file():
            rels.append((fig / "ga" / name).relative_to(ROOT).as_posix())
    return rels


STAGED = {  # staged file -> its place relative to ROOT
    "paper/draft/S3_posthoc.md": "paper/draft/S3_posthoc.md",
    "paper/draft/05_rivals.md": "paper/draft/05_rivals.md",
    "paper/draft/tables/table_9.md": "paper/draft/tables/table_9.md",
    "paper/draft/TABLE_NUMBERS.md": "paper/draft/TABLE_NUMBERS.md",
    "paper/draft/S1_disclosures.md": "paper/draft/S1_disclosures.md",
    "paper/draft/S4_provenance.md": "paper/draft/S4_provenance.md",
    "paper/draft/GLOSSARY.md": "paper/draft/GLOSSARY.md",
    "paper/draft/REFERENCES.md": "paper/draft/REFERENCES.md",
    "paper/PAPER_FACTS.md": "paper/PAPER_FACTS.md",
    "paper/PAPER_OUTLINE.md": "paper/PAPER_OUTLINE.md",
}


def copy_tree(dst_root, rels):
    n = 0
    for r in rels:
        src = ROOT / r
        dst = dst_root / r
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        if sha(src) != sha(dst):
            raise SystemExit("copy mismatch: " + r)
        n += 1
    return n


def main():
    for name in ("copy", "copy_live"):
        if (CHK / name).exists():
            raise SystemExit(name + " exists already; not overwritten")
    rels = live_inputs()
    n_live = copy_tree(CHK / "copy_live", rels)
    n_copy = copy_tree(CHK / "copy", rels)
    print("live inputs copied: %d files into copy_live/ and copy/" % n_live)
    for s, r in sorted(STAGED.items()):
        src = STAGE / s
        dst = CHK / "copy" / r
        dst.parent.mkdir(parents=True, exist_ok=True)
        was = sha(dst) if dst.exists() else "absent"
        shutil.copy2(src, dst)
        assert sha(src) == sha(dst)
        print("overlay %-34s live %s -> staged %s" % (r, was[:12], sha(dst)[:12]))
    # the build writes only into paper/build and paper/build/_work of each copy
    print("ok")


if __name__ == "__main__":
    main()
