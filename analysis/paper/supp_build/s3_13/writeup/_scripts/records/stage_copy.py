# Copy this writer's live files byte for byte into STAGE (at their ROOT-relative paths; PROTOCOL.md as shap/PROTOCOL.md)
# and into work/base/ (the base the build script edits from). Refuses to overwrite an existing staged copy that differs
# from the live file (an earlier writer's copy is then the start). Checks SHA-256 of every copy. Reads only the live files.
import os, sys, hashlib, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
STAGE = os.path.normpath(os.path.join(HERE, '..', '..'))
ROOT = os.path.normpath(os.path.join(STAGE, '..', '..', '..', '..'))
BASE = os.path.join(HERE, 'work', 'base')

FILES = [
    ('engine/PENDING_PARTS.md', os.path.join(ROOT, 'engine', 'PENDING_PARTS.md')),
    ('_archive_plan/ARCHIVE_MANIFEST_DRAFT.md', os.path.join(ROOT, '_archive_plan', 'ARCHIVE_MANIFEST_DRAFT.md')),
    ('paper/PAPER_OUTLINE.md', os.path.join(ROOT, 'paper', 'PAPER_OUTLINE.md')),
    ('shap/PROTOCOL.md', r'D:\treeroute\analysis\shap_v1\PROTOCOL.md'),
]


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    assert os.path.isdir(os.path.join(ROOT, 'engine')) and os.path.isdir(os.path.join(ROOT, 'paper')), 'ROOT check'
    for rel, live in FILES:
        dst = os.path.join(STAGE, *rel.split('/'))
        base = os.path.join(BASE, rel.replace('/', '__'))
        h_live = sha(live)
        if os.path.exists(dst):
            h_dst = sha(dst)
            print('%s: staged copy exists (%s); live %s' % (rel, h_dst[:16], h_live[:16]))
            if not os.path.exists(base):
                os.makedirs(os.path.dirname(base), exist_ok=True)
                shutil.copyfile(dst, base)
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        os.makedirs(os.path.dirname(base), exist_ok=True)
        shutil.copyfile(live, dst)
        shutil.copyfile(live, base)
        h_dst, h_base = sha(dst), sha(base)
        assert h_dst == h_live == h_base, rel
        print('%s: copied; sha256 %s (live = staged = base); %d bytes' % (rel, h_live, os.path.getsize(dst)))


if __name__ == '__main__':
    main()
