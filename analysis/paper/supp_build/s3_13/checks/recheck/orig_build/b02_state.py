"""Record (or compare) the state of the live folders the build could touch: ROOT/paper/build (with _work),
ROOT/paper/draft (top level, submission, tables), ROOT/paper/figures and ROOT/engine/OWNER_RULINGS_2026-10-06.md.
Names relative to ROOT, size, mtime (ns). Run: py -3.9 -I -B b02_state.py save|compare
Writes only work/live_state.json in this check folder.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHK = HERE.parent
OUT = CHK.parent.parent
ROOT = OUT.parent.parent.parent
STATE = CHK / "work" / "live_state.json"


def walk():
    res = {}
    targets = [ROOT / "paper" / "build", ROOT / "paper" / "figures"]
    for t in targets:
        for p in t.rglob("*"):
            if p.is_file():
                st = p.stat()
                res[p.relative_to(ROOT).as_posix()] = [st.st_size, st.st_mtime_ns]
    d = ROOT / "paper" / "draft"
    for sub in ("", "submission", "tables"):
        for p in (d / sub).iterdir():
            if p.is_file():
                st = p.stat()
                res[p.relative_to(ROOT).as_posix()] = [st.st_size, st.st_mtime_ns]
    for p in [ROOT / "paper" / "PAPER_FACTS.md", ROOT / "paper" / "PAPER_OUTLINE.md",
              ROOT / "engine" / "OWNER_RULINGS_2026-10-06.md", ROOT / "engine" / "PENDING_PARTS.md"]:
        st = p.stat()
        res[p.relative_to(ROOT).as_posix()] = [st.st_size, st.st_mtime_ns]
    return res


def main():
    mode = sys.argv[1]
    now = walk()
    if mode == "save":
        STATE.write_text(json.dumps(now, indent=0, sort_keys=True), encoding="utf-8")
        print("saved %d entries" % len(now))
        return
    old = json.loads(STATE.read_text(encoding="utf-8"))
    added = sorted(set(now) - set(old))
    gone = sorted(set(old) - set(now))
    changed = sorted(k for k in set(now) & set(old) if now[k] != old[k])
    print("entries: before %d, now %d" % (len(old), len(now)))
    print("added:", added or "none")
    print("removed:", gone or "none")
    print("changed:", changed or "none")


if __name__ == "__main__":
    main()
