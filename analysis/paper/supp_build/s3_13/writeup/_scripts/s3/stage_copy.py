"""Copy a live paper file into STAGE byte for byte, then check that both SHA-256 agree (writer s3).

Usage: py -3.9 -I -B stage_copy.py <relative path under ROOT>
Refuses to overwrite an existing staged copy (an earlier writer's copy is the start point then).
Writes only under STAGE.
"""
import hashlib
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..", ".."))
STAGE = os.path.join(ROOT, "paper", "supp_build", "s3_13", "stage")


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def main():
    rel = sys.argv[1]
    src = os.path.join(ROOT, rel)
    dst = os.path.join(STAGE, rel)
    if not os.path.abspath(dst).startswith(os.path.abspath(STAGE) + os.sep):
        sys.exit("refused: target outside STAGE")
    if os.path.exists(dst):
        print("exists, not copied:", rel, sha(dst))
        return
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(src, "rb") as f:
        data = f.read()
    with open(dst, "xb") as f:
        f.write(data)
    a, b = sha(src), sha(dst)
    print(rel, "live", a, "staged", b, "bytes", len(data), "EQUAL" if a == b else "DIFFERENT")
    if a != b:
        sys.exit(2)


if __name__ == "__main__":
    main()
