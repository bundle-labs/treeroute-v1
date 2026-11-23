"""First step of writer main (S3.13 write-up, 2026-11-17): byte-for-byte staged copies of the live files it edits.

Run: py -3.9 -I -B stage_copy_main.py
For D/05_rivals.md and D/TABLE_NUMBERS.md: reads the live bytes, checks their SHA-256 against the value taken before
any edit, writes the same bytes to STAGE at the same path relative to ROOT (only if no staged copy exists yet; an
existing staged copy is accepted only if it is still byte-identical to the live file) and a base copy to work/ for
re-runs, then re-reads both and checks the SHA-256 again. D/tables/table_9.md must be absent (a new file).
Writes only under STAGE.
"""
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STAGE = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.dirname(STAGE)
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(OUT)))
WORK = os.path.join(HERE, "work")

FILES = {
    ("paper", "draft", "05_rivals.md"): "c439966f79efcf9dc9c23362dfa389f1dca6b3d65dd6871e53b8540b39b2fb59",
    ("paper", "draft", "TABLE_NUMBERS.md"): "4bd98584a116a68e2b50c8d9aab51ba2f02a963c548fb9d0f5a3fef617c0be36",
}
NEW = ("paper", "draft", "tables", "table_9.md")


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    os.makedirs(WORK, exist_ok=True)
    for rel, want in FILES.items():
        live = os.path.join(ROOT, *rel)
        with open(live, "rb") as fh:
            data = fh.read()
        got = sha(data)
        if got != want:
            sys.exit("live %s has SHA-256 %s, expected %s: stop" % ("/".join(rel), got, want))
        dst = os.path.join(STAGE, *rel)
        base = os.path.join(WORK, "__".join(rel) + ".base")
        if os.path.exists(dst):
            with open(dst, "rb") as fh:
                cur = sha(fh.read())
            if cur != want:
                # a re-run: the staged copy was already edited by build_main.py; keep it, check the base copy
                if not os.path.exists(base):
                    sys.exit("staged %s differs from the live file and no base copy exists: stop" % "/".join(rel))
                with open(base, "rb") as fh:
                    if sha(fh.read()) != want:
                        sys.exit("base copy of %s differs from the live file: stop" % "/".join(rel))
                print("%-28s live SHA-256 %s: staged copy already edited (not overwritten); base copy equal"
                      % ("/".join(rel), want))
                continue
            print("staged %s already a byte-for-byte copy" % "/".join(rel))
        else:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "wb") as fh:
                fh.write(data)
        with open(base, "wb") as fh:
            fh.write(data)
        for p in (dst, base):
            with open(p, "rb") as fh:
                if sha(fh.read()) != want:
                    sys.exit("copy check failed: %s" % p)
        print("%-28s live SHA-256 %s (%d bytes): staged copy and base copy equal" % ("/".join(rel), want, len(data)))
    live_new = os.path.join(ROOT, *NEW)
    print("%-28s live: %s" % ("/".join(NEW), "PRESENT (stop)" if os.path.exists(live_new) else "absent (new file)"))
    if os.path.exists(live_new):
        sys.exit(1)


if __name__ == "__main__":
    main()
