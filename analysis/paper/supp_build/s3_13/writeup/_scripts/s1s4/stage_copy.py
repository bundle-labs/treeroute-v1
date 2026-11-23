# Copy the live S1 and S4 drafts byte for byte into STAGE (SHA-256 checked), and keep base copies of
# all three of this writer's files (S1, S4 and the staged PAPER_FACTS.md) in work/ for the build script.
# Refuses to overwrite a staged file that already exists (an earlier writer's copy must be started from).
import hashlib, os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
STAGE = os.path.normpath(os.path.join(HERE, "..", ".."))
ROOT = os.path.normpath(os.path.join(STAGE, "..", "..", "..", ".."))
WORK = os.path.join(HERE, "work")

LIVE = {
    "paper/draft/S1_disclosures.md": "23d7c5d8167293ad1ea08561e1f0f471fe818da722e6e805e97094cc6c450862",
    "paper/draft/S4_provenance.md": "19112cd642e6a8d74773278a5c2a32a958ae584bd064a3485ffc3fe19fdc7d5f",
}
STAGED_FACTS = ("paper/PAPER_FACTS.md", "735e10c81ceee24e89d522c02f0dd86b344902f77147238d2972723702425a8b")


def sha(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def main():
    os.makedirs(WORK, exist_ok=True)
    assert os.path.isfile(os.path.join(ROOT, "paper", "PAPER_FACTS.md")), ROOT
    for rel, want in LIVE.items():
        src = os.path.join(ROOT, *rel.split("/"))
        dst = os.path.join(STAGE, *rel.split("/"))
        got = sha(src)
        if got != want:
            sys.exit("live hash changed: %s %s" % (rel, got))
        if os.path.exists(dst):
            sys.exit("staged copy already exists, start from it: %s" % dst)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)
        if sha(dst) != want:
            sys.exit("copy differs: %s" % rel)
        base = os.path.join(WORK, rel.replace("/", "__") + ".base")
        shutil.copyfile(src, base)
        if sha(base) != want:
            sys.exit("base copy differs: %s" % rel)
        print("staged", rel, want)
    rel, want = STAGED_FACTS
    p = os.path.join(STAGE, *rel.split("/"))
    if sha(p) != want:
        sys.exit("staged PAPER_FACTS.md is not the expected copy: %s" % sha(p))
    base = os.path.join(WORK, rel.replace("/", "__") + ".base")
    shutil.copyfile(p, base)
    if sha(base) != want:
        sys.exit("base copy of PAPER_FACTS differs")
    print("base kept", rel, want)


if __name__ == "__main__":
    main()
