"""Table order and references in the staged S3_posthoc.md (visible text): captions of Tables S3.N, the first
citation of each in all visible text and in running text only (not captions, table rows or notes), ranges
expanded; then every 'Table S3.N' cited in the staged paper files against the captions of all staged/live
supplements; and the bare S-numbers the build's BARE_SUP_RE would read. Read-only.
Run: py -3.9 -I -B b08_tables.py
"""
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from b04_lib import (STAGE, ROOT, read_bytes, text_of, blank_comments, line_at, ctx, BARE_SUP_RE, SUP_REF_RE,
                     SEC_REF_RE)

REF_RE = re.compile(r"\bTables?\s+(S3\.\d+)([a-z])?((?:\s*(?:,|and|or|to|–|-)\s*S?3?\.?\d+(?:\.\d+)?[a-z]?)*)")


def blocks_with_offsets(t):
    out, start = [], 0
    for m in re.finditer(r"\n\s*\n", t):
        out.append((start, t[start:m.start()]))
        start = m.end()
    out.append((start, t[start:]))
    return out


def kind_of(b):
    s = b.lstrip()
    if s.startswith("**Table"):
        return "caption"
    if s.startswith("|"):
        return "table"
    if re.match(r"^[ᵃᵇᶜᵈᵉᶠᵍʰⁱʲᵏˡᵐⁿᵒᵖʳˢᵗᵘᵛʷˣʸᶻ†‡§¶]", s):
        return "note"
    if s.startswith("**") and re.match(r"^\*\*[a-z]\. ", s):
        return "panel"
    return "text"


def expand(first, more):
    nums = [int(first.split(".")[1])]
    toks = re.findall(r"(–|-|to|,|and|or)?\s*S?3?\.?(\d+)", more or "")
    for sep, n in toks:
        n = int(n)
        if sep in ("–", "-", "to") and n > nums[-1]:
            nums.extend(range(nums[-1] + 1, n + 1))
        else:
            nums.append(n)
    return nums


def main():
    st = text_of(read_bytes(STAGE / "paper/draft/S3_posthoc.md"))
    vis = blank_comments(st)
    caps = {}
    for off, b in blocks_with_offsets(vis):
        m = re.match(r"\s*\*\*Table\s+S3\.(\d+)", b)
        if m:
            caps.setdefault(int(m.group(1)), off)
    first_any, first_text = {}, {}
    for off, b in blocks_with_offsets(vis):
        k = kind_of(b)
        for m in REF_RE.finditer(b):
            nums = expand(m.group(1), m.group(3))
            for n in nums:
                first_any.setdefault(n, off + m.start())
                if k == "text":
                    first_text.setdefault(n, off + m.start())
    print("captions S3.N (line):", ", ".join("S3.%d (L%d)" % (n, line_at(st, o)) for n, o in sorted(caps.items())))
    print("%-7s %-9s %-14s %-14s %s" % ("table", "caption", "first cite", "first in text", "cited before caption?"))
    for n in sorted(set(caps) | set(first_any)):
        c = caps.get(n)
        fa = first_any.get(n)
        ft = first_text.get(n)
        print("S3.%-4d %-9s %-14s %-14s %s" % (n, "L%d" % line_at(st, c) if c is not None else "-",
                                            "L%d" % line_at(st, fa) if fa is not None else "-",
                                            "L%d" % line_at(st, ft) if ft is not None else "-",
                                            (fa is not None and c is not None and fa < c)))
    order = [n for n, _ in sorted(first_any.items(), key=lambda kv: kv[1])]
    print("order of first citation (any visible text):", order)
    order_t = [n for n, _ in sorted(first_text.items(), key=lambda kv: kv[1])]
    print("order of first citation (running text):", order_t)
    new = [n for n in order if n >= 17]
    print("S3.17 onward in first-citation order:", new, "increasing:", new == sorted(new))
    # every Table S3.N / S-number cited in staged paper files exists?
    sup_caps = set()
    sup_heads = set()
    for p in sorted((ROOT / "paper/draft").glob("S*.md")):
        sp = STAGE / "paper/draft" / p.name
        t = blank_comments(text_of(read_bytes(sp if sp.exists() else p)))
        for m in re.finditer(r"(?m)^\*\*Table\s+(S\d+\.\d+)", t):
            sup_caps.add(m.group(1))
        for m in re.finditer(r"(?m)^#{1,6}\s+(S\d+(?:\.\d+)*)\s", t):
            sup_heads.add(m.group(1))
    for p in sorted((ROOT / "paper/draft/tables").glob("table_S*.md")):
        t = blank_comments(text_of(read_bytes(p)))
        for m in re.finditer(r"(?m)^\*\*Table\s+(S\d+\.\d+)", t):
            sup_caps.add(m.group(1))
    print("supplement headings found:", len(sup_heads), "; supplement table captions found:", len(sup_caps))
    for rel in ("paper/draft/S3_posthoc.md", "paper/draft/05_rivals.md", "paper/draft/tables/table_9.md",
                "paper/draft/S1_disclosures.md", "paper/draft/S4_provenance.md"):
        t = blank_comments(text_of(read_bytes(STAGE / rel)))
        bad = []
        for m in re.finditer(r"\bTables?\s+(S\d+\.\d+)", t):
            if m.group(1) not in sup_caps:
                bad.append(("table", m.group(1), line_at(t, m.start())))
        for m in BARE_SUP_RE.finditer(t):
            if m.group(1) not in sup_heads:
                bad.append(("bare", m.group(1), line_at(t, m.start()), ctx(t, m.start(), m.end(), 50)))
        for m in SUP_REF_RE.finditer(t):
            nums = [m.group("first")] + re.findall(r"S\d+(?:\.\d+)*", m.group("more") or "")
            for n in nums:
                if n not in sup_heads:
                    bad.append(("supplement", n, line_at(t, m.start())))
        print(rel, "cross-reference problems:", bad or "none")


if __name__ == "__main__":
    main()
