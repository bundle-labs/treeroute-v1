"""Refresh the DRAFT development packages datasets/<name>_draft/ from the real packages datasets/<name>/ (dataset tool).

    cd "C:\\Users\\<user>\\Desktop\\data set for reserch paper\\engine"
    py -3.9 datasets/_tools/refresh_drafts.py check   pm25 fire ndvi defo     # compare, write nothing
    py -3.9 datasets/_tools/refresh_drafts.py refresh pm25 fire ndvi defo     # move the old drafts aside, rewrite

WHY (2026-10-06, agent C1). The drafts were the SHIPPED-verdict development copies of the time before the owner's ban
lists existed. Owner ruling J installed the ban lists on all four packages (OWNER_RULINGS_2026-10-05.md section J,
the author's answer, not quoted), and rulings K and L moved them on, so a draft that still carries the shipped
verdicts rehearses a run nobody will make. A refreshed draft is the real package as installed today, with the
engine's DRAFT stamp, so a full-size rehearsal of a draft reads today's ban lists and nothing it produces can enter a
headline table.

WHAT A DRAFT IS NOW (draft_files below is the one generator; tests/test_pipeline_draft.py checks every draft
against it, so a draft cannot drift from its package silently):
  - every file of the real package, byte for byte (catalog.yaml, split.yaml, exceptions.yaml, AUDIT_CHECKLIST.md,
    ingest/, features/, data/), except expected_derived.json (the real package's acceptance values, tests only);
  - dataset.yaml: the real text with name '<name>_draft', version '<version>-draft', the owner field marked as a
    DRAFT package's, the description prefixed by DRAFT_STAMP, and a header naming this generator;
  - ban.yaml: the real verdicts and reasons unchanged, every evidence field prefixed by DRAFT_STAMP and ' | '
    (treeroute.pipeline.draft reads the stamp: one stamped verdict makes the package a draft; every run of it is
    stamped DRAFT and the headline-table builder refuses it). The real file's header comment is kept, after a
    draft header.
  The stamp text starts with the engine's marker (treeroute.pipeline.draft.DRAFT_MARKER) and holds no '|' or '.',
  so the engine reads it whole from both places.

MOVING ASIDE, NEVER DELETING. 'refresh' renames the old draft folder to datasets/_moved_20261006/<name>_draft/
(same drive, a rename) and writes the new draft. When that folder already holds an earlier move, the draft goes to the
first free datasets/_moved_20261006/<name>_draft_<n>/ (n = 2, 3, ...; 2026-10-06: a later refresh after a package
change), so an earlier move is never overwritten. Nothing is deleted. The old fire draft's 1,000-cell sidecar copies
(data/fire_drivers, data/fire_history) went with the first move (tests/test_fire_package_data.py reads them there).
"""
# Provenance: OWNER_RULINGS_2026-10-05.md J (ban lists installed), K, L; treeroute/pipeline/draft.py (the DRAFT
# marker and how the engine reads it); the 2026-10-06 build rule "never delete; move aside into _moved_20261006".

import hashlib
import os
import sys
from pathlib import Path

import yaml

ENGINE = Path(__file__).resolve().parents[2]
if str(ENGINE) not in sys.path:
    sys.path.insert(0, str(ENGINE))

from treeroute.pipeline.draft import DRAFT_MARKER, draft_status  # noqa: E402

DATASETS = ENGINE / "datasets"
PACKAGES = ("pm25", "fire", "ndvi", "defo")
MOVED = DATASETS / "_moved_20261006"
DRAFT_STAMP = (DRAFT_MARKER + " copy of the installed package with its owner-ruled ban list (rulings J to L, "
               "2026-10-06); smoke, rehearsal and development only, never a headline run")
NOT_COPIED = ("expected_derived.json",)
SKIP_DIRS = ("__pycache__",)


class DraftError(Exception):
    """The draft cannot be generated or checked as declared (fail loudly)."""


def _q(text):
    return "'" + text.replace("'", "''") + "'"


def real_files(name):
    """{relative posix path: bytes} of the real package's files the draft copies verbatim (sorted)."""
    root = DATASETS / name
    out = {}
    for dirpath, dirnames, filenames in os.walk(str(root)):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for f in sorted(filenames):
            rel = Path(dirpath, f).relative_to(root).as_posix()
            if rel in NOT_COPIED or rel in ("dataset.yaml", "ban.yaml"):
                continue
            out[rel] = Path(dirpath, f).read_bytes()
    return out


def draft_dataset_text(name, real_text):
    """dataset.yaml of the draft from the real text: name, version, owner and description lines replaced."""
    lines = real_text.split("\n")
    done = set()
    for i, line in enumerate(lines):
        for key in ("name", "version", "owner", "description"):
            if line.startswith(key + ":") and key not in done:
                value = yaml.safe_load(line)[key]
                if key == "name":
                    if value != name:
                        raise DraftError("%s/dataset.yaml names %r" % (name, value))
                    new = "%s_draft" % name
                elif key == "version":
                    new = _q("%s-draft" % value)
                elif key == "owner":
                    new = _q("UNSIGNED -- DRAFT development package; not the owner's")
                else:
                    new = _q("%s. %s" % (DRAFT_STAMP, value))
                lines[i] = "%s: %s" % (key, new)
                done.add(key)
    missing = sorted({"name", "version", "owner", "description"} - done)
    if missing:
        raise DraftError("%s/dataset.yaml has no top-level %s line" % (name, missing))
    header = ["# dataset.yaml -- %s_draft: GENERATED from datasets/%s/dataset.yaml by datasets/_tools/refresh_drafts.py;"
              % (name, name),
              "# do not edit by hand (tests/test_pipeline_draft.py checks it against the generator).",
              "# " + DRAFT_STAMP + ".",
              "# Only name, version, owner and description differ from the real package; every store, include and",
              "# sha256 is the real package's. The real file's comments follow.",
              "#"]
    return "\n".join(header + lines)


def draft_ban_text(name, real_text):
    """ban.yaml of the draft: the real verdicts and reasons, every evidence prefixed by the stamp."""
    doc = yaml.safe_load(real_text)
    verdicts = doc.get("verdicts") if isinstance(doc, dict) else None
    if not isinstance(verdicts, dict) or set(doc) != {"verdicts"}:
        raise DraftError("%s/ban.yaml must hold exactly one top-level key 'verdicts'" % name)
    out = {}
    for col, v in verdicts.items():
        v = dict(v)
        old = v.get("evidence")
        v["evidence"] = "%s | %s" % (DRAFT_STAMP, old if old else "(no evidence in the real ban list)")
        out[col] = v
    comments = []
    for line in real_text.split("\n"):
        if not line.startswith("#"):
            break
        comments.append(line)
    header = ["# ban.yaml -- %s_draft: GENERATED from datasets/%s/ban.yaml by datasets/_tools/refresh_drafts.py;"
              % (name, name),
              "# do not edit by hand. " + DRAFT_STAMP + ".",
              "# Every verdict and reason is the real package's; every evidence field starts with the DRAFT stamp, so the",
              "# engine marks every run of this package DRAFT and the headline-table builder refuses it.",
              "# The real file's header follows.",
              "#"]
    body = yaml.safe_dump({"verdicts": out}, sort_keys=False, width=4096, allow_unicode=False, default_flow_style=False)
    return "\n".join(header + comments) + "\n" + body


def draft_files(name):
    """{relative posix path: bytes} of the draft of package ``name``, generated from the real package."""
    if name not in PACKAGES:
        raise DraftError("unknown package %r (one of %s)" % (name, PACKAGES))
    root = DATASETS / name
    files = real_files(name)
    files["dataset.yaml"] = draft_dataset_text(name, (root / "dataset.yaml").read_text(encoding="utf-8")).encode("utf-8")
    files["ban.yaml"] = draft_ban_text(name, (root / "ban.yaml").read_text(encoding="utf-8")).encode("utf-8")
    return dict(sorted(files.items()))


def on_disk(name):
    """{relative posix path: bytes} of the draft folder as it is (no __pycache__)."""
    root = DATASETS / ("%s_draft" % name)
    out = {}
    for dirpath, dirnames, filenames in os.walk(str(root)):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for f in sorted(filenames):
            out[Path(dirpath, f).relative_to(root).as_posix()] = Path(dirpath, f).read_bytes()
    return out


def differences(name):
    """[text] of every way the draft folder differs from what draft_files generates (empty when current)."""
    want, have = draft_files(name), on_disk(name)
    out = ["missing %s" % r for r in sorted(set(want) - set(have))]
    out += ["extra %s" % r for r in sorted(set(have) - set(want))]
    out += ["differs %s" % r for r in sorted(set(want) & set(have)) if want[r] != have[r]]
    return out


def verify(name):
    """Load the draft and the real package through the engine: the draft is stamped on every verdict and its verdicts
    and reasons are the real ones. Returns the engine's DraftStatus of the draft."""
    from treeroute.package.load import load_package
    draft, real = load_package(DATASETS / ("%s_draft" % name)), load_package(DATASETS / name)
    st = draft_status(draft)
    if not (st.is_draft and st.stamped_verdicts == len(draft.ban.verdicts) and st.stamp == DRAFT_STAMP):
        raise DraftError("%s_draft: the engine reads %r" % (name, st.record()))
    if draft_status(real).is_draft:
        raise DraftError("the real package %s reads as a draft" % name)
    for col, v in real.ban.verdicts.items():
        d = draft.ban.verdicts.get(col)
        if d is None or (d.verdict, d.reason) != (v.verdict, v.reason):
            raise DraftError("%s_draft: verdict of %s differs from the real package" % (name, col))
    if set(draft.ban.verdicts) != set(real.ban.verdicts):
        raise DraftError("%s_draft: the verdict columns differ from the real package" % name)
    return st


def aside_path(name):
    """The folder the current draft of ``name`` is moved to: datasets/_moved_20261006/<name>_draft/, or, when an
    earlier move holds that name, the first free <name>_draft_<n>/ (n = 2, 3, ...). Never an existing folder."""
    base = MOVED / ("%s_draft" % name)
    if not base.exists():
        return base
    n = 2
    while (MOVED / ("%s_draft_%d" % (name, n))).exists():
        n += 1
    return MOVED / ("%s_draft_%d" % (name, n))


def refresh(name, echo=print):
    files = draft_files(name)
    dst = DATASETS / ("%s_draft" % name)
    if dst.exists():
        aside = aside_path(name)
        if aside.exists():                             # aside_path never returns one; a race would show here
            raise DraftError("%s already exists; nothing was moved (never overwritten)" % aside)
        MOVED.mkdir(exist_ok=True)
        os.rename(str(dst), str(aside))
        echo("moved the old %s aside to %s" % (dst.name, aside))
    for rel, data in files.items():
        path = dst / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(str(path), "xb") as fh:              # a fresh folder: never overwrites
            fh.write(data)
    st = verify(name)
    echo("%s: %d files written (sha256 of the file list %s); engine reads DRAFT, %d stamped verdicts"
         % (dst.name, len(files), hashlib.sha256("\n".join(files).encode("utf-8")).hexdigest()[:12],
            st.stamped_verdicts))
    return st


def main(argv):
    if len(argv) < 2 or argv[0] not in ("check", "refresh"):
        raise SystemExit("usage: py -3.9 datasets/_tools/refresh_drafts.py check|refresh <package> [<package> ...]")
    bad = 0
    for name in argv[1:]:
        if argv[0] == "refresh":
            refresh(name)
        else:
            diff = differences(name)
            print("%s_draft: %s" % (name, "current" if not diff else "; ".join(diff[:20])))
            bad += bool(diff)
    if bad:
        raise SystemExit(1)


if __name__ == "__main__":
    main(sys.argv[1:])
