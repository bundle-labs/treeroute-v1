"""Checks of writer main's staged files (S3.13 write-up, 2026-11-17). Read only; writes nothing.

Run: py -3.9 -I -B check_main.py
1. bytes of the three staged files (SHA-256, BOM, CR, final LF);
2. the line diff live -> staged of 05_rivals.md and TABLE_NUMBERS.md (only the planned insertions);
3. table_9.md = its header comment + the Table 9 block of tables_agreed.md, byte for byte;
4. every number token of the new 5.4 paragraph is in a fact it cites (A10, A14, A16, A17), each interval verbatim;
5. no AI term, "agent", absolute path, e-mail address, account or host name in the added visible text;
   no account or host name, user-folder path or e-mail address in any file or script of this writer;
6. the author-year citations of the staged 05_rivals.md and table_9.md resolve (the references writer's copy of
   the build's parser, STAGE/_scripts/refs/check_entries.py, functions only, against the staged REFERENCES.md);
7. the cross-references of the new paragraph and of table_9.md name existing sections, supplement sections and
   supplement tables (the build's regular expressions; the staged S3_posthoc.md in place of the live one);
8. the order of first citation of Tables 1-9 in the manuscript's running text (staged 05_rivals.md);
9. the glossary's do-not-use names (the lead's scan rule) in the added prose;
10. word counts (the build's count_words rule) of Section 5 and of 5.4, live and staged.
"""
import difflib
import hashlib
import importlib.util
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STAGE = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.dirname(STAGE)
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(OUT)))
D = os.path.join(ROOT, "paper", "draft")
SD = os.path.join(STAGE, "paper", "draft")


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


B = load_module("build_main", os.path.join(HERE, "build_main.py"))
CE = load_module("check_entries", os.path.join(STAGE, "_scripts", "refs", "check_entries.py"))

TAB_REF_RE = re.compile(r"\bTables?\s+(?P<first>S?\d+(?:\.\d+)?[a-z]?)(?P<more>(?:\s*(?:,|and|or|to|–|-)\s*S?\d+(?:\.\d+)?[a-z]?)*)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$", re.M)
CAPTION_TABLE_RE = re.compile(r"^\*\*Table\s+(S?\d+(?:\.\d+)?[a-z]?)\b", re.M)
SEC_REF_RE = re.compile(r"\bSections?\s+(?P<first>\d+(?:\.\d+)*)(?P<more>(?:\s*(?:,|and|or|to|–|-)\s*\d+(?:\.\d+)*)*)")
SUP_REF_RE = re.compile(r"\b(?:Supplements?|Sections?)\s+(?P<first>S\d+(?:\.\d+)*)(?P<more>(?:\s*(?:,|and|or|to|–|-)\s*S\d+(?:\.\d+)*)*)")
BARE_SUP_RE = re.compile(r"(?<!Table )(?<!Tables )(?<!Supplement )(?<!Supplements )(?<!Section )(?<!Sections )"
                         r"(?<![\w.])(S\d+\.\d+(?:\.\d+)?)(?=[,;)\s])")
AI_STRONG = re.compile(r"\bAI\b|(?i:\bartificial intelligence\b|\bgenerative\b|\blarge language models?\b|\bLLMs?\b|"
                       r"\bchatgpt\b|\bcopilot\b|\bclaude\b|\banthropic\b|\bmachine-generated\b)|\bGPT-?\d")
AI_WEAK = re.compile(r"(?i)\bagents?\b")
ABS_PATH = re.compile(r"[A-Za-z]:[\\/]")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")


def sha(b):
    return hashlib.sha256(b).hexdigest()


def rb(path):
    with open(path, "rb") as fh:
        return fh.read()


def vis(text):
    return re.sub(r"<!--.*?-->", lambda m: " " * len(m.group(0)), text, flags=re.S)


def count_words(md):
    """The build's count_words (paper/build/build_docx.py), copied."""
    t = re.sub(r"^\s*\|?\s*:?-{3,}.*$", " ", md, flags=re.M)
    t = re.sub(r"^:::.*$", " ", t, flags=re.M)
    t = t.replace("|", " ")
    t = re.sub(r"^#{1,6}\s+", "", t, flags=re.M)
    t = re.sub(r"\$\$.*?\$\$", " MATH ", t, flags=re.S)
    t = re.sub(r"\$[^$\n]+\$", " MATH ", t)
    return sum(1 for w in t.split() if re.search(r"[0-9A-Za-zÀ-ÿ\u0370-\u03ff]", w))


def visible_only(text):
    return re.sub(r"<!--.*?-->", "", text, flags=re.S)


def main():
    ok = True
    files = {"05_rivals.md": os.path.join(SD, "05_rivals.md"), "TABLE_NUMBERS.md": os.path.join(SD, "TABLE_NUMBERS.md"),
             "table_9.md": os.path.join(SD, "tables", "table_9.md")}
    print("== 1. bytes")
    raw = {}
    for k, p in files.items():
        b = rb(p)
        raw[k] = b.decode("utf-8")
        print("%-17s SHA-256 %s  %d bytes  BOM %s  CR %s  final LF %s" % (
            k, sha(b), len(b), b.startswith(b"\xef\xbb\xbf"), b"\r" in b, b.endswith(b"\n") and not b.endswith(b"\n\n")))
    print("== 2. line diffs live -> staged")
    live = {"05_rivals.md": rb(os.path.join(D, "05_rivals.md")).decode("utf-8"),
            "TABLE_NUMBERS.md": rb(os.path.join(D, "TABLE_NUMBERS.md")).decode("utf-8")}
    for k in ("05_rivals.md", "TABLE_NUMBERS.md"):
        print("%s live SHA-256 %s" % (k, sha(live[k].encode("utf-8"))))
        a, b = live[k].split("\n"), raw[k].split("\n")
        sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op == "equal":
                continue
            print("  %s live %d-%d -> staged %d-%d" % (op, i1 + 1, i2, j1 + 1, j2))
            if op == "replace":
                for x, y in zip(a[i1:i2], b[j1:j2]):
                    print("    replaced line keeps the old text as its prefix:", y.startswith(x))
    print("== 3. table_9.md")
    tab = B.read_checked(B.TABLES, B.TABLES_SHA)
    block, l0, l1 = B.table9_block(tab)
    hdr = raw["table_9.md"].split("\n", 1)[0]
    expect = hdr + "\n\n" + block
    print("file = header + blank line + block:", raw["table_9.md"] == expect)
    print("block occurrences: tables_agreed.md %d, table_9.md %d; lines %d-%d" % (
        tab.count(block), raw["table_9.md"].count(block), l0, l1))
    print("header: one comment line:", hdr.startswith("<!-- ") and hdr.endswith(" -->") and hdr.count("<!--") == 1
          and hdr.count("-->") == 1)
    ok &= raw["table_9.md"] == expect
    print("== 4. numbers of the new paragraph against its facts")
    s05 = raw["05_rivals.md"]
    pstart = s05.index("Table 9 compares, post hoc,")
    pend = s05.index("\n", pstart)
    para = s05[pstart:pend]
    pv = visible_only(para)
    facts_txt = rb(os.path.join(STAGE, "paper", "PAPER_FACTS.md")).decode("utf-8").split("\n")
    cited = {}
    fids = sorted({f for c in re.findall(r"<!--(.*?)-->", para) for f in re.findall(r"\bA\d+\b", c)})
    print("fact IDs cited in the paragraph's comments:", fids)
    for fid in fids:
        hits = [ln for ln in facts_txt if ln.startswith("- **%s (final, post hoc (Part 628))" % fid)]
        cited[fid] = hits[0] if len(hits) == 1 else None
        print("fact %s found once: %s" % (fid, len(hits) == 1))
    allf = " ".join(v for v in cited.values() if v)
    scan = pv.replace("PM2.5", " ").replace("treeroute v1", " ").replace("Table 9", " ").replace("S3.13", " ")
    scan = scan.replace("Lundberg and Lee 2017", " ")
    ivals = re.findall(r"−?\d+\.\d+ \[−?\d+\.\d+, −?\d+\.\d+\]", pv)
    for iv in ivals:
        where = [f for f, v in cited.items() if v and iv in v]
        print("interval %-22s in facts %s" % (iv, where))
        ok &= bool(where)
    toks = re.findall(r"(?<![\w.])−?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?", scan)
    missing = [t for t in toks if t not in allf]
    print("number tokens:", len(toks), "not found in the cited facts:", missing)
    ok &= not missing
    print("== 5. AI terms, agent, paths, privacy")
    added_visible = {
        "new paragraph": pv,
        "table_9.md": vis(raw["table_9.md"]),
        "TABLE_NUMBERS additions": "\n".join(l for l in raw["TABLE_NUMBERS.md"].split("\n")
                                             if l not in live["TABLE_NUMBERS.md"].split("\n")),
    }
    names = [n for n in (os.environ.get("USERNAME", ""), os.environ.get("COMPUTERNAME", ""),
                         os.environ.get("USERDOMAIN", "")) if len(n) >= 3]
    for k, txt in added_visible.items():
        print("%-24s AI %d, agent %d, absolute path %d, e-mail %d, account/host %d" % (
            k, len(AI_STRONG.findall(txt)), len(AI_WEAK.findall(txt)), len(ABS_PATH.findall(txt)),
            len(EMAIL.findall(txt)), sum(txt.lower().count(n.lower()) for n in names)))
    mine = [files[k] for k in files] + [os.path.join(HERE, f) for f in sorted(os.listdir(HERE)) if f.endswith(".py")]
    chg = os.path.join(STAGE, "changes_main.md")
    if os.path.exists(chg):
        mine.append(chg)
    for p in mine:
        txt = rb(p).decode("utf-8")
        if p in files.values():
            # only the text this writer added
            base = live.get(os.path.basename(p), "")
            txt = "\n".join(l for l in txt.split("\n") if l not in base.split("\n"))
        n_acc = sum(txt.lower().count(n.lower()) for n in names)
        n_users = len(re.findall(r"(?i)[\\/]users[\\/]", txt))
        n_mail = len(EMAIL.findall(txt))
        n_uuid = len(re.findall(r"(?i)\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", txt))
        n_wf = len(re.findall(r"\bwf_[0-9a-z]", txt))
        print("privacy %-28s account/host %d, user-folder path %d, e-mail %d, uuid-like id %d, wf_ id %d" % (
            os.path.basename(p), n_acc, n_users, n_mail, n_uuid, n_wf))
        ok &= n_acc == 0 and n_users == 0 and n_mail == 0 and n_uuid == 0 and n_wf == 0
    print("== 6. citations")
    ents = CE.parse_references(rb(os.path.join(SD, "REFERENCES.md")).decode("utf-8"))
    index, labels = CE.build_index(ents)
    for k in ("05_rivals.md", "table_9.md"):
        res = CE.scan(vis(raw[k]), index, labels)
        bad = [r for r in res if r.startswith(("UNRESOLVED", "AMBIGUOUS", "BUILD ERROR"))]
        print("%s: %d year tokens; unresolved/ambiguous: %s" % (k, len(res), bad if bad else "none"))
        ok &= not bad
    print("new paragraph:", CE.scan(pv, index, labels))
    live_res = CE.scan(vis(live["05_rivals.md"]), index, labels)
    print("live 05_rivals.md against the staged REFERENCES.md: %d year tokens" % len(live_res))
    print("== 7. cross-references")
    sup_heads, sup_tables, man_heads = set(), set(), set()
    for name in sorted(os.listdir(D)):
        if not name.endswith(".md") or not (name.startswith("S") or name[:2].isdigit()):
            continue
        sp = os.path.join(SD, name)
        txt = rb(sp if os.path.exists(sp) else os.path.join(D, name)).decode("utf-8")
        v = vis(txt)
        if name.startswith("S"):
            for h in HEADING_RE.finditer(v):
                m = re.match(r"^(S?\d+(?:\.\d+)*)\s", h.group(2) + " ")
                if m:
                    sup_heads.add(m.group(1))
            for m in CAPTION_TABLE_RE.finditer(v):
                sup_tables.add(re.match(r"^(S?\d+(?:\.\d+)?)", m.group(1)).group(1))
        elif name[:2].isdigit():
            for h in HEADING_RE.finditer(v):
                m = re.match(r"^(S?\d+(?:\.\d+)*)\s", h.group(2) + " ")
                if m:
                    man_heads.add(m.group(1))
    for k, v in (("new paragraph", pv), ("table_9.md", vis(raw["table_9.md"]))):
        probs = []
        for m in BARE_SUP_RE.finditer(v):
            if m.group(1) not in sup_heads:
                probs.append("bare %s" % m.group(1))
        for m in SEC_REF_RE.finditer(v):
            for n in [m.group("first")] + re.findall(r"\d+(?:\.\d+)*", m.group("more") or ""):
                if n not in man_heads:
                    probs.append("Section %s" % n)
        refs = []
        for m in SUP_REF_RE.finditer(v):
            for n in [m.group("first")] + re.findall(r"S\d+(?:\.\d+)*", m.group("more") or ""):
                refs.append(n)
                if n not in sup_heads:
                    probs.append("supplement %s" % n)
        for m in re.finditer(r"\bTables?\s+(S\d+\.\d+)", v):
            refs.append("Table " + m.group(1))
            if re.match(r"^(S?\d+(?:\.\d+)?)", m.group(1)).group(1) not in sup_tables:
                probs.append("Table %s" % m.group(1))
        print("%-14s references %s; problems: %s" % (k, sorted(set(refs)), probs if probs else "none"))
        ok &= not probs
    print("== 8. first citations of Tables 1-9 in the manuscript's running text")
    order = [os.path.join(ROOT, "paper", "draft", "submission", "software_data_availability.md")] + [
        os.path.join(D, f) for f in ("01_introduction.md", "02_method.md", "03_protocol.md", "04_results.md",
                                     "05_rivals.md", "06_limitations.md", "07_discussion.md", "08_conclusions.md")]
    first = {}
    pos = 0
    for p in order:
        sp = os.path.join(SD, os.path.basename(p))
        txt = vis(rb(sp if (os.path.exists(sp) and os.path.dirname(p) == D) else p).decode("utf-8"))
        for m in TAB_REF_RE.finditer(txt):
            nums = [m.group("first")] + re.findall(r"S?\d+(?:\.\d+)?[a-z]?", m.group("more") or "")
            for n in nums:
                base = re.match(r"^(S?\d+(?:\.\d+)?)", n).group(1)
                if base.startswith("S"):
                    continue
                first.setdefault(int(base), (pos, os.path.basename(p)))
                pos += 1
    seq = sorted(first, key=lambda n: first[n][0])
    print("first-citation order:", seq, "; Table 9 first cited in", first.get(9, ("-", "none"))[1])
    ok &= seq == sorted(seq) and 9 in first and first[9][1] == "05_rivals.md"
    nine_elsewhere = []
    for f in sorted(os.listdir(D)):
        if f[:2].isdigit() and f.endswith(".md") and f != "05_rivals.md":
            if re.search(r"\bTables?\s+9\b", vis(rb(os.path.join(D, f)).decode("utf-8"))):
                nine_elsewhere.append(f)
    print("other main-text files citing Table 9:", nine_elsewhere if nine_elsewhere else "none")
    print("== 9. glossary do-not-use names in the added prose (lead's scan rule)")
    gl = os.path.join(SD, "GLOSSARY.md")
    gnames = []
    with open(gl, encoding="utf-8") as fh:
        for line in fh:
            if not line.startswith("| **"):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 4:
                continue
            term = re.sub(r"\*\*", "", cells[0])
            others = re.sub(r"<!--.*?-->", "", cells[1])
            for raw_n in others.split(","):
                n = raw_n.strip()
                n = re.sub(r"\((banned|coral|C9 name|ours|nowcast row|rivals)\)", "", n).strip()
                n = n.strip('"').strip("'").strip()
                if n and n != "—":
                    gnames.append((n, term))
    for k in ("new paragraph", "TABLE_NUMBERS additions"):
        txt = re.sub(r"`[^`]*`", " ", added_visible[k])
        hits = []
        for n, term in gnames:
            rx = re.compile(r"(?<![\w-])" + re.escape(n) + r"(?![\w-])", re.I)
            for m in rx.finditer(txt):
                hits.append("%r (term %s): ...%s..." % (n, term, txt[max(0, m.start() - 30):m.end() + 30]))
        print("%s: %d hit(s)" % (k, len(hits)))
        for h in hits:
            print("   ", h)
    print("== 10. word counts (visible text; the build's rule)")
    for k, txt in (("live", live["05_rivals.md"]), ("staged", raw["05_rivals.md"])):
        v = visible_only(txt)
        s54 = v[v.index("## 5.4 Post hoc analyses"):]
        print("%-6s Section 5 running text %d words; 5.4 %d words" % (k, count_words(v), count_words(s54)))
    print("new paragraph: %d words" % count_words(pv))
    print("table_9.md (caption, table and notes; visible): %d words" % count_words(visible_only(raw["table_9.md"])))
    print("ALL CHECKS PASSED" if ok else "SOME CHECK FAILED")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
