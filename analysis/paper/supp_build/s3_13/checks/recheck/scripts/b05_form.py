"""Form checks of every staged file against its live file: encoding, BOM, line endings, final newline,
what changed (token diff: inserted / deleted / replaced), deleted text, HTML comments (closed, stray, nested,
'--' inside), the edit-history comment with @@SNAP@@, placeholders in visible text, and long lines.
Read-only; prints to the screen (cleaned). Run: py -3.9 -I -B b05_form.py
"""
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))   # -I leaves the script folder off the path
from b04_lib import (PAIRS, STAGE, BUILT, read_bytes, text_of, blank_comments, comment_spans, line_at, new_spans,
                     deleted_tokens, in_spans, ctx, clean)


def endings(b):
    crlf = b.count(b"\r\n")
    lf = b.count(b"\n") - crlf
    cr = b.count(b"\r") - crlf
    return crlf, lf, cr


def main():
    for rel, live in PAIRS:
        sb = read_bytes(STAGE / rel)
        print("=" * 100)
        print(rel)
        try:
            sb.decode("utf-8")
            ok = "valid UTF-8"
        except UnicodeDecodeError as e:
            ok = "NOT UTF-8: %s" % e
        s_bom = sb.startswith(b"\xef\xbb\xbf")
        s_end = endings(sb)
        s_final = sb.endswith(b"\n")
        s_final2 = sb.endswith(b"\n\n") or sb.endswith(b"\r\n\r\n")
        if live is not None:
            lb = read_bytes(live)
            l_bom = lb.startswith(b"\xef\xbb\xbf")
            l_end = endings(lb)
            print("  staged: %s, BOM %s, CRLF %d, bare LF %d, bare CR %d, final newline %s, blank last line %s, %d bytes"
                  % (ok, s_bom, s_end[0], s_end[1], s_end[2], s_final, s_final2, len(sb)))
            print("  live:   BOM %s, CRLF %d, bare LF %d, bare CR %d, final newline %s, %d bytes"
                  % (l_bom, l_end[0], l_end[1], l_end[2], lb.endswith(b"\n"), len(lb)))
            same_kind = (l_bom == s_bom and ((l_end[0] > 0) == (s_end[0] > 0)) and ((l_end[1] > 0) == (s_end[1] > 0))
                         and l_end[2] == 0 == s_end[2] and lb.endswith(b"\n") == s_final)
            print("  encoding and line endings kept:", same_kind)
            lt, st = text_of(lb), text_of(sb)
        else:
            print("  NEW FILE: %s, BOM %s, CRLF %d, bare LF %d, bare CR %d, final newline %s, %d bytes"
                  % (ok, s_bom, s_end[0], s_end[1], s_end[2], s_final, len(sb)))
            lt, st = "", text_of(sb)
        spans, _ = new_spans(lt, st)
        dels = deleted_tokens(lt, st)
        n_new = sum(e - s for s, e in spans)
        print("  new text: %d spans, %d characters; deleted or replaced old token runs: %d" % (len(spans), n_new, len(dels)))
        for s, e, tag in dels:
            print("    %s old L%d: %s" % (tag, line_at(lt, s), ctx(lt, s, e, 0)[:300]))
        # lines touched
        lines = sorted({line_at(st, s) for s, e in spans} | {line_at(st, e - 1) for s, e in spans})
        if lines:
            print("  staged lines with new text: %d..%d (%d distinct lines with a span start or end)" % (lines[0], lines[-1], len(lines)))
        # HTML comments
        problems = []
        i = 0
        while True:
            j = st.find("<!--", i)
            k = st.find("-->", i)
            if k != -1 and (j == -1 or k < j):
                problems.append(("stray -->", k))
                i = k + 3
                continue
            if j == -1:
                break
            e = st.find("-->", j + 4)
            if e == -1:
                problems.append(("unclosed <!--", j))
                break
            body = st[j + 4:e]
            if "<!--" in body:
                problems.append(("nested <!--", j))
            if "--" in body:
                problems.append(("'--' inside a comment", j))
            i = e + 3
        for what, off in problems:
            new = in_spans(off, off + 4, spans) or any(s <= off <= e for s, e in spans)
            print("  COMMENT %s at L%d (%s): %s" % (what, line_at(st, off), "NEW" if new else "old", ctx(st, off, off + 4, 50)[:200]))
        n_c = len(comment_spans(st))
        print("  comments: %d; problems: %d" % (n_c, len(problems)))
        # edit-history and placeholders
        newtxt = "".join(st[s:e] + "\n" for s, e in spans)
        print("  new text holds '@@SNAP@@': %d; 'S3.13 write-up, 2026-11-17': %d; '@@LATER_READS@@': %d"
              % (newtxt.count("@@SNAP@@"), newtxt.count("S3.13 write-up, 2026-11-17"), newtxt.count("@@LATER_READS@@")))
        vis = blank_comments(st)
        for m in re.finditer(r"@@[A-Z_]+@@", vis):
            print("  PLACEHOLDER IN VISIBLE TEXT L%d: %s" % (line_at(st, m.start()), ctx(vis, m.start(), m.end(), 50)))
        snaps_in_comments = 0
        for a, b in comment_spans(st):
            snaps_in_comments += st[a:b].count("@@SNAP@@")
        print("  @@SNAP@@ total %d, inside comments %d" % (st.count("@@SNAP@@"), snaps_in_comments))
        # long new lines (PROTOCOL rule: prose lines <= 120)
        if rel == "shap/PROTOCOL.md":
            long_new = [ln for ln in lines if len(st.split("\n")[ln - 1]) > 120]
            nonascii = [line_at(st, s + k) for s, e in spans for k, ch in enumerate(st[s:e]) if ord(ch) > 127]
            print("  PROTOCOL new lines over 120 characters:", long_new or "none", "; non-ASCII in new text at lines:",
                  sorted(set(nonascii)) or "none")
        if rel == "engine/PENDING_PARTS.md":
            nonascii = [line_at(st, s + k) for s, e in spans for k, ch in enumerate(st[s:e]) if ord(ch) > 127]
            print("  non-ASCII in new text at lines:", sorted(set(nonascii)) or "none")


if __name__ == "__main__":
    main()
