# fix_lib.py - shared paths and helpers of the fixer (S3.13 write-up, 2026-11-17).
# Paths are derived at run time from this file's place (STAGE/_scripts/fix/), so no user-folder path is written here.
import hashlib
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent          # STAGE/_scripts/fix
STAGE = HERE.parents[1]                          # OUT/stage
OUT = STAGE.parent                               # ROOT/paper/supp_build/s3_13
ROOT = OUT.parents[2]                            # the research-paper folder
D = ROOT / 'paper' / 'draft'
SHAP = Path('D:/treeroute/analysis/shap_v1')
WORK = HERE / 'work'
BASE = WORK / 'base'

# staged file (relative to STAGE) -> live file (absolute); None = new file
FILES = {
    'paper/draft/S3_posthoc.md': D / 'S3_posthoc.md',
    'paper/draft/05_rivals.md': D / '05_rivals.md',
    'paper/draft/tables/table_9.md': None,
    'paper/draft/TABLE_NUMBERS.md': D / 'TABLE_NUMBERS.md',
    'paper/draft/S1_disclosures.md': D / 'S1_disclosures.md',
    'paper/draft/S4_provenance.md': D / 'S4_provenance.md',
    'paper/draft/GLOSSARY.md': D / 'GLOSSARY.md',
    'paper/draft/REFERENCES.md': D / 'REFERENCES.md',
    'paper/PAPER_FACTS.md': ROOT / 'paper' / 'PAPER_FACTS.md',
    'paper/PAPER_OUTLINE.md': ROOT / 'paper' / 'PAPER_OUTLINE.md',
    'engine/PENDING_PARTS.md': ROOT / 'engine' / 'PENDING_PARTS.md',
    '_archive_plan/ARCHIVE_MANIFEST_DRAFT.md': ROOT / '_archive_plan' / 'ARCHIVE_MANIFEST_DRAFT.md',
    'shap/PROTOCOL.md': SHAP / 'PROTOCOL.md',
}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def base_name(rel):
    return rel.replace('/', '__')


def form(b):
    """Encoding and line-ending facts of a byte string."""
    bom = b.startswith(b'\xef\xbb\xbf')
    crlf = b.count(b'\r\n')
    cr = b.count(b'\r') - crlf
    lf = b.count(b'\n') - crlf
    try:
        b.decode('utf-8')
        utf8 = True
    except UnicodeDecodeError:
        utf8 = False
    return {'bom': bom, 'crlf': crlf, 'bare_lf': lf, 'bare_cr': cr, 'utf8': utf8,
            'final_newline': b.endswith(b'\n'), 'double_final': b.endswith(b'\n\n') or b.endswith(b'\r\n\r\n')}


def visible(text):
    """Text with HTML comments removed (the build strips them)."""
    out, i = [], 0
    while True:
        j = text.find('<!--', i)
        if j < 0:
            out.append(text[i:])
            break
        out.append(text[i:j])
        k = text.find('-->', j + 4)
        if k < 0:
            raise ValueError('unclosed comment')
        i = k + 3
    return ''.join(out)
