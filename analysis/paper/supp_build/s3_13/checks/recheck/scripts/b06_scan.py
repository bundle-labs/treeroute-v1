"""Scans of the new text of every staged file (token diff against the live file; a new file counts whole):
 privacy   account/host/user-folder names, user-folder paths, e-mail addresses, uuid-like and session/workflow ids,
           16-hex tokens (raw text, comments included), also over every other file of STAGE (changes files, scripts)
 ai        the build's AI_STRONG / AI_WEAK expressions and softer words, in the new VISIBLE text
 paths     absolute local paths in the new visible text
Read-only; prints cleaned contexts only. Run: py -3.9 -I -B b06_scan.py
"""
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from b04_lib import (PAIRS, STAGE, read_bytes, text_of, blank_comments, line_at, new_spans, in_spans, ctx,
                     NAME_PATS, USERPATH_RE, EMAIL_RE, UUID_RE, IDS_RE, HEX16_RE, ABS_PATH_RE, AI_STRONG, AI_WEAK,
                     AI_SOFT)


def privacy(label, t, spans=None):
    hits = []
    pats = [("name", p) for p in NAME_PATS] + [("user-folder path", USERPATH_RE), ("e-mail", EMAIL_RE),
                                               ("uuid", UUID_RE), ("id", IDS_RE), ("16-hex", HEX16_RE)]
    for kind, p in pats:
        for m in p.finditer(t):
            if spans is not None and not in_spans(m.start(), m.end(), spans):
                continue
            if kind == "16-hex" and re.search(r"(?i)sha|hash|prefix|fingerprint|digest|`$", t[max(0, m.start() - 40):m.start()]):
                continue    # a hash prefix named as such
            hits.append((kind, line_at(t, m.start()), ctx(t, m.start(), m.end(), 40)))
    for kind, ln, c in hits:
        print("  PRIVACY %s %s L%d: %s" % (label, kind, ln, c[:220]))
    return len(hits)


def main():
    print("#### privacy: new text of the staged files (raw, comments included)")
    seen_files = set()
    total = 0
    for rel, live in PAIRS:
        st = text_of(read_bytes(STAGE / rel))
        lt = text_of(read_bytes(live)) if live is not None else ""
        spans, _ = new_spans(lt, st)
        n = privacy(rel, st, spans)
        print("  %s: %d hit(s) in new text" % (rel, n))
        total += n
        seen_files.add((STAGE / rel).resolve())
    print("#### privacy: every other file under STAGE (whole content)")
    for p in sorted(STAGE.rglob("*")):
        if not p.is_file() or p.resolve() in seen_files:
            continue
        b = p.read_bytes()
        try:
            if b[:2] in (b"\xff\xfe", b"\xfe\xff"):
                t = b.decode("utf-16")
            else:
                t = b.decode("utf-8")
        except UnicodeDecodeError:
            t = b.decode("latin-1")
        t = t.replace("\r\n", "\n")
        rel = p.relative_to(STAGE).as_posix()
        base_copy = "/work/base/" in "/" + rel or rel.endswith(".base")
        n = privacy(rel, t)
        if n:
            print("  %s: %d hit(s)%s" % (rel, n, " (a base copy of a live file)" if base_copy else ""))
        total += n
    print("privacy hits in total:", total)

    print("#### AI terms and absolute paths in the new VISIBLE text")
    for rel, live in PAIRS:
        st = text_of(read_bytes(STAGE / rel))
        lt = text_of(read_bytes(live)) if live is not None else ""
        vs, vl = blank_comments(st), blank_comments(lt)
        spans, _ = new_spans(vl, vs)
        for label, rx in (("AI_STRONG", AI_STRONG), ("AI_WEAK", AI_WEAK), ("soft", AI_SOFT), ("abs path", ABS_PATH_RE)):
            for m in rx.finditer(vs):
                if in_spans(m.start(), m.end(), spans):
                    print("  %s %s L%d '%s': %s" % (rel, label, line_at(vs, m.start()), m.group(0), ctx(vs, m.start(), m.end(), 70)[:260]))
    print("#### AI terms anywhere in the visible text of the staged S3, 05, table_9, TABLE_NUMBERS, GLOSSARY (old text too)")
    for rel in ("paper/draft/S3_posthoc.md", "paper/draft/05_rivals.md", "paper/draft/tables/table_9.md",
                "paper/draft/TABLE_NUMBERS.md", "paper/draft/GLOSSARY.md"):
        vs = blank_comments(text_of(read_bytes(STAGE / rel)))
        n = 0
        for label, rx in (("AI_STRONG", AI_STRONG), ("AI_WEAK", AI_WEAK)):
            for m in rx.finditer(vs):
                n += 1
                print("  %s %s L%d '%s': %s" % (rel, label, line_at(vs, m.start()), m.group(0), ctx(vs, m.start(), m.end(), 70)[:260]))
        print("  %s: %d" % (rel, n))


if __name__ == "__main__":
    main()
