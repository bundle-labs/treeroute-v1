# Fill the staged files' SHA-256 and sizes into STAGE/changes_records.md (tokens @@STAGED_<NAME>@@), from the files
# as they are now. Writes UTF-8 without BOM, LF. Refuses if a token is missing or left over.
import os, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
STAGE = os.path.normpath(os.path.join(HERE, '..', '..'))
MAP = {
    'PENDING': 'engine/PENDING_PARTS.md',
    'MANIFEST': '_archive_plan/ARCHIVE_MANIFEST_DRAFT.md',
    'PROTOCOL': 'shap/PROTOCOL.md',
    'OUTLINE': 'paper/PAPER_OUTLINE.md',
}
p = os.path.join(STAGE, 'changes_records.md')
with open(p, encoding='utf-8', newline='') as f:
    t = f.read()
for k, rel in MAP.items():
    tok = '@@STAGED_%s@@' % k
    with open(os.path.join(STAGE, *rel.split('/')), 'rb') as f:
        b = f.read()
    val = '%s (%s)' % (hashlib.sha256(b).hexdigest(), format(len(b), ','))
    assert t.count(tok) == 1, tok
    t = t.replace(tok, val)
    print(rel, val)
assert '@@STAGED_' not in t
t = t.replace('\r\n', '\n')
with open(p, 'w', encoding='utf-8', newline='\n') as f:
    f.write(t)
print('changes_records.md', hashlib.sha256(t.encode('utf-8')).hexdigest())
