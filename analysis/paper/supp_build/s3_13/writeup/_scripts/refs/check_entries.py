"""Check the candidate reference entries the way the paper build reads them.

Usage: py -3.9 -I -B check_entries.py <draft/REFERENCES.md> <stage/refs_candidates.md>

Copies (does not import or run) the parts of paper/build/build_docx.py that read
section A entries (parse_references), make their author labels (author_labels),
sort the reference list (bibliography_md's sort_key) and resolve author-year
citations (CitationIndex.scan, without aliases). For each candidate it prints
whether the entry parses, its labels, any key or label clash with section A and
A2, and the section A entries it falls between under the build's sort key; then
it resolves a list of test citations. Reads the two files; writes nothing.
"""
import re
import sys
import unicodedata

YEAR_TOKEN_RE = re.compile(r"(?<![\w\-–/.])(?:(?P<y>(?:1[6-9]|20)\d\d[a-z]?)(?![\w])(?![\-–/.]\d)|(?P<nd>n\.d\.))")
INITIALS_RE = re.compile(r"^(?:[A-ZÀ-ÖØ-ÞĀ-Ž][a-zà-ÿ]{0,2}\.(?:\s*-\s*|\s*)?)+$")
SUFFIXES = {"Jr.", "Sr.", "II", "III"}
STOP_WORDS = set("""January February March April May June July August September October
November December Jan Feb Mar Apr Jun Jul Aug Sep Sept Oct Nov Dec In Since From Until Till
By Before After During Through To At On Of For And Or But The A An As Also Only Both Each
Every All Then Than Figure Figures Table Tables Section Sections Supplement Supplements Part
Parts Version Release Collection Spring Summer Autumn Fall Winter Year Years Window Test
Mid Early Late End Up Over Under Between Around About Near Per Via With Without Into
Onto Except Including Against Beside Besides Among""".split())

A_RE = re.compile(r"^- \*\*(?P<head>.+?)\*\*(?P<rest>.*?)\s+—\s+Key\s+`(?P<key>[^`]+)`")
A2_RE = re.compile(r"^- (?P<auth>.+?) \((?P<yr>(?:1[6-9]|20)\d\d[a-z]?|n\.d\.)\)\.\s+(?P<rest>.+)$")


def norm_space(s):
    return re.sub(r"\s+", " ", s).strip()


def norm_label(s):
    s = unicodedata.normalize("NFC", s).replace("’", "'").replace("&", "and")
    s = re.sub(r"\s*/\s*", "/", s)
    return norm_space(s).casefold()


def author_labels(auth):
    a = norm_space(auth)
    toks = [t.strip() for t in re.split(r",\s+", a)]

    def strip_amp(t):
        return t[2:].strip() if t.startswith("& ") else t
    personal = any(INITIALS_RE.match(strip_amp(t)) for t in toks[1:])
    if personal:
        etal = any(strip_amp(t) in ("et al.", "et al") for t in toks)
        names = [strip_amp(t) for t in toks
                 if not (strip_amp(t) in ("et al.", "et al") or strip_amp(t) in SUFFIXES or INITIALS_RE.match(strip_amp(t)))]
        n = 3 if etal else len(names)
    else:
        parts = [p.strip() for p in re.split(r",?\s+&\s+", a)]
        names = (re.split(r",\s+", parts[0]) + parts[1:]) if len(parts) > 1 else [a]
        n = len(names)
    if n == 1:
        base = names[0]
    elif n == 2:
        base = f"{names[0]} and {names[1]}"
    else:
        base = f"{names[0]} et al."
    variants = {base}
    if n == 1:
        m = re.match(r"^(.*?)\s*\(([^()]+)\)$", names[0])
        if m:
            variants |= {m.group(1).strip(), m.group(2).strip()}
    return sorted(variants, key=len, reverse=True)


def parse_a_line(ln):
    m = A_RE.match(ln)
    if not m:
        return None, "not in the expected form"
    head = m.group("head").strip()
    hm = re.match(r"^(?P<auth>.+) \((?P<yr>[^()]+)\)\.?$", head)
    if not hm:
        return None, "cannot read authors and year"
    ym = re.search(r"(?:1[6-9]|20)\d\d[a-z]?|n\.d\.", hm.group("yr"))
    if not ym:
        return None, "no year"
    bib = (head + m.group("rest")).replace("**", "").strip()
    return dict(key=m.group("key"), authors=hm.group("auth"), year=ym.group(0),
                labels=author_labels(hm.group("auth")), bib=bib), None


def parse_references(text):
    entries = []
    sec = None
    for i, ln in enumerate(text.split("\n"), 1):
        if ln.startswith("## "):
            sec = "A" if ln.startswith("## A.") else None
            continue
        if ln.startswith("### "):
            sec = "A2" if ln.startswith("### A2.") else (sec if sec == "A" and not ln.startswith("### A") else None)
            continue
        if not sec or not ln.startswith("- "):
            continue
        if sec == "A":
            e, err = parse_a_line(ln)
            if e is None:
                print("REFERENCES.md line %d: %s" % (i, err))
                continue
            e.update(section="A", line=i)
            entries.append(e)
        else:
            m = A2_RE.match(ln)
            if not m:
                print("REFERENCES.md line %d: A2 entry not in the expected form" % i)
                continue
            key = "A2:" + re.sub(r"\W+", "", m.group("auth").split(",")[0]) + m.group("yr")
            entries.append(dict(key=key, authors=m.group("auth"), year=m.group("yr"),
                                labels=author_labels(m.group("auth")), bib="", section="A2", line=i))
    return entries


def sort_key(e):
    a = unicodedata.normalize("NFKD", e["authors"])
    a = "".join(ch for ch in a if not unicodedata.combining(ch)).casefold()
    return (a, e["year"])


def build_index(entries):
    index = {}
    for e in entries:
        for lab in e["labels"]:
            index.setdefault((norm_label(lab), e["year"]), []).append(e)
    labels = sorted({lab for (lab, _y) in index}, key=len, reverse=True)
    return index, labels


def scan(text, index, labels):
    out = []
    for m in YEAR_TOKEN_RE.finditer(text):
        yr = m.group("y") or "n.d."
        s = text[:m.start()]
        while True:
            mm = re.search(r"(?:(?:1[6-9]|20)\d\d[a-z]?|n\.d\.)\s*,\s*$", s)
            if not mm:
                break
            s = s[:mm.start()]
        s = s.rstrip()
        narrative = s.endswith("(")
        if narrative:
            s = s[:-1].rstrip()
            if s.endswith(("'s", "’s")):
                s = s[:-2]
        if s.endswith(","):
            s = s[:-1].rstrip()
        tail = norm_label(s[-220:])
        hit = None
        for lab in labels:
            if tail.endswith(lab) and (len(tail) == len(lab) or not tail[-len(lab) - 1].isalnum()):
                hit = lab
                break
        if hit:
            ents = index.get((hit, yr))
            if ents is None:
                out.append("UNRESOLVED '%s %s': no entry with that year" % (hit, yr))
                continue
            keys = sorted({e["key"] for e in ents})
            out.append(("AMBIGUOUS '%s %s': %s" % (hit, yr, keys)) if len(keys) > 1 else ("resolves '%s %s' -> %s" % (hit, yr, keys[0])))
            continue
        raw_tail = s[-120:]
        g = re.search(r"(?:^|[\s(\[;:,])(?P<auth>(?:(?:van|von|de|der|den|da|di|du|la|le|del|dos|ten|ter)\s+)*"
                      r"[A-ZÀ-ÖØ-Þ][\w'’.\-]*(?:\s+(?:and|&)\s+(?:(?:van|von|de|der|den|da|di|du|la|le)\s+)*"
                      r"[A-ZÀ-ÖØ-Þ][\w'’\-]*)?(?:\s+et\s+al\.)?)$", raw_tail)
        if not g:
            out.append("year %s: not read as a citation" % yr)
            continue
        auth = g.group("auth")
        names = [x.strip().split()[0] for x in re.split(r"\s+(?:and|&)\s+", auth.replace(" et al.", "")) if x.strip()]
        if any(nm in STOP_WORDS for nm in names):
            out.append("year %s: skipped (stop word)" % yr)
            continue
        strong = (" et al." in auth) or (" and " in auth) or (" & " in auth) or narrative
        first = auth.split()[0]
        if not strong:
            if first in STOP_WORDS or any(ch.isdigit() for ch in first):
                out.append("year %s: skipped" % yr)
                continue
            before = raw_tail[:g.start("auth")].rstrip()
            if not (before.endswith(("(", ";", ":")) or before == ""):
                out.append("year %s: not read as a citation" % yr)
                continue
        out.append("BUILD ERROR: unresolved citation '%s %s'" % (auth, yr))
    return out


def main():
    ref_text = open(sys.argv[1], encoding="utf-8").read().replace("\r\n", "\n")
    cand_text = open(sys.argv[2], encoding="utf-8").read().replace("\r\n", "\n")
    existing = parse_references(ref_text)
    a_entries = [e for e in existing if e["section"] == "A"]
    print("section A entries: %d; A2 entries: %d" % (len(a_entries), len(existing) - len(a_entries)))
    cands = []
    in_entries = False
    for ln in cand_text.split("\n"):
        if ln.startswith("## "):
            in_entries = ln.startswith("## Entries")
            continue
        if in_entries and ln.startswith("- **"):
            e, err = parse_a_line(ln)
            if e is None:
                print("CANDIDATE NOT PARSED (%s): %s" % (err, ln[:80]))
                continue
            cands.append(e)
    print("candidates parsed: %d" % len(cands))
    old_keys = {e["key"] for e in existing}
    old_pairs = {(norm_label(l), e["year"]): e["key"] for e in existing for l in e["labels"]}
    for c in cands:
        print("\n%s | authors: %s | year: %s | labels: %s" % (c["key"], c["authors"], c["year"], c["labels"]))
        print("  key clash: %s" % (c["key"] in old_keys))
        for l in c["labels"]:
            k = (norm_label(l), c["year"])
            print("  label '%s %s' clash: %s" % (l, c["year"], old_pairs.get(k, "none")))
        ck = sort_key(c)
        later = [e for e in a_entries if sort_key(e) > ck]
        earlier = [e for e in a_entries if sort_key(e) <= ck]
        prev_e = max(earlier, key=sort_key) if earlier else None
        next_e = min(later, key=sort_key) if later else None
        print("  sorts after: %s | before: %s" % (prev_e["key"] if prev_e else "-", next_e["key"] if next_e else "-"))
        print("  bib as printed: %s" % norm_space(c["bib"]))
    allc = [c for c in cands]
    order = sorted(allc, key=sort_key)
    print("\norder of the candidates among themselves: %s" % [c["key"] for c in order])
    index, labels = build_index(existing + cands)
    tests = [
        "exact TreeSHAP (Lundberg et al. 2020)",
        "SHAP values (Lundberg and Lee 2017)",
        "Lundberg and Lee's (2017) definition",
        "the interventional game (Janzing et al. 2020)",
        "Janzing et al. (2020) argue",
        "rank-biased overlap (Webber et al. 2010)",
        "eq. 32 of Webber, Moffat and Zobel 2010",
        "Kendall's W (Kendall and Babington Smith 1939)",
        "Kendall and Babington Smith (1939)",
        "Kendall's W (Kendall 1939)",
        "Kendall's (1939) W",
        "(Lundberg and Lee 2017; Lundberg et al. 2020; Janzing et al. 2020)",
    ]
    print("\ncitation tests:")
    for t in tests:
        print("  %-70s %s" % (t, scan(t, index, labels)))


if __name__ == "__main__":
    main()
