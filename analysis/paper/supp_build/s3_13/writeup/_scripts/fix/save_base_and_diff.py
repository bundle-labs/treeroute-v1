# save_base_and_diff.py - run once, before any fix edit: (1) records the SHA-256, size and form of the 13 staged files
# as they stood before the fix pass (work/base_hashes.json; never overwritten); (2) saves byte copies of them in
# work/base/, except for a file whose text holds a pre-existing name or id (S3_posthoc.md, REFERENCES.md and
# PENDING_PARTS.md hold such ids in old text, so no copy of them is kept; apply_fix.py reaches their pre-fix state by
# undoing its own recorded edits); (3) hashes each live counterpart (read only); (4) writes a line diff live -> staged
# of each file to work/diff_<name>.txt (changed lines only). Prints hashes and forms only.
# Run once, before the first edit. After the fix the fixer removed work/base/ and the diff_*.txt files: apply_fix.py reaches
# the pre-fix state by undoing its own recorded edits, and check_fix.py writes the fix's own diffs (fixdiff_*.txt).
# work/base_hashes.json, the record of the pre-fix hashes, is kept.
import difflib
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))  # -I leaves the script's folder off sys.path
from fix_lib import FILES, STAGE, BASE, WORK, sha, base_name, form
import privacy_two as P  # count-only patterns

HJ = WORK / 'base_hashes.json'
if HJ.exists():
    sys.exit('base_hashes.json exists: the pre-fix state was recorded already; not run again')
BASE.mkdir(parents=True, exist_ok=True)
rec = {}
for rel, live in FILES.items():
    sb = (STAGE / rel).read_bytes()
    bp = BASE / base_name(rel)
    has_ids = any(rx.search(P.decode(sb)) for rx in P.PATS.values())
    if not has_ids and not bp.exists():
        bp.write_bytes(sb)
    lb = live.read_bytes() if live is not None and live.exists() else None
    rec[rel] = {'base_sha': sha(sb), 'base_bytes': len(sb), 'copy_kept': not has_ids,
                'live_sha': sha(lb) if lb is not None else None, 'live_bytes': len(lb) if lb is not None else None,
                'form_base': form(sb)}
    if lb is not None:
        a = lb.decode('utf-8').splitlines()
        b = sb.decode('utf-8').splitlines()
        d = list(difflib.unified_diff(a, b, 'live', 'staged-before-fix', n=0, lineterm=''))
        (WORK / ('diff_' + base_name(rel) + '.txt')).write_text('\n'.join(d) + '\n', encoding='utf-8')
HJ.write_text(json.dumps(rec, indent=1), encoding='utf-8')
for rel, r in rec.items():
    print(rel, r['base_bytes'], r['base_sha'][:16], 'live', r['live_bytes'], (r['live_sha'] or '-')[:16],
          'copy' if r['copy_kept'] else 'no-copy')
