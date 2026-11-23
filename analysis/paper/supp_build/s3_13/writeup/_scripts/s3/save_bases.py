"""Save the earlier writers' staged PAPER_FACTS.md and GLOSSARY.md as this writer's base copies (writer s3).

Usage: py -3.9 -I -B save_bases.py
The copies go to STAGE/_scripts/s3/work/ and are checked against the SHA-256 the glossary writer returned,
so that this writer's scripts can be re-run from the same start. Writes only under STAGE.
"""
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STAGE = os.path.abspath(os.path.join(HERE, "..", ".."))
WORK = os.path.join(HERE, "work")
BASES = {
    os.path.join("paper", "PAPER_FACTS.md"): "8206f9ef45fa9111d412a311679d2c726488999faa2c90b97d53d4a730342403",
    os.path.join("paper", "draft", "GLOSSARY.md"): "b40954b2a89c77b15fc4b24d8b8f54081be58425101a1b33130f4bd97b3b50c9",
}


def main():
    os.makedirs(WORK, exist_ok=True)
    for rel, want in BASES.items():
        name = rel.replace(os.sep, "__") + ".base"
        dst = os.path.join(WORK, name)
        if os.path.exists(dst):
            with open(dst, "rb") as f:
                got = hashlib.sha256(f.read()).hexdigest()
            print("exists:", name, got, "OK" if got == want else "MISMATCH")
            continue
        with open(os.path.join(STAGE, rel), "rb") as f:
            data = f.read()
        got = hashlib.sha256(data).hexdigest()
        if got != want:
            sys.exit("staged %s has %s, not the returned %s: stop" % (rel, got, want))
        with open(dst, "xb") as f:
            f.write(data)
        print("saved:", name, got, len(data))


if __name__ == "__main__":
    main()
