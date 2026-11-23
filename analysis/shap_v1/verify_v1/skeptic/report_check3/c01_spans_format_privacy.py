"""Report check 3: byte identity of the reconciler's text and of A2-A3 across the three versions of report.md,
plus format and privacy checks of the third version. Read-only. Prints no environment value.

Run: py -3.9 -I -B c01_spans_format_privacy.py
"""
import hashlib
import os
import re

R = r"D:\treeroute\analysis\shap_v1\verify_v1\reconcile"
FILES = [("v1", "report.md.before_fix1"), ("v2", "report.md.before_fix2"), ("v3", "report.md")]


def sha(b):
    return hashlib.sha256(b).hexdigest()


def span(b, start, end):
    i = b.find(start)
    j = b.find(end, i + 1) if i >= 0 else -1
    if i < 0 or j < 0:
        return None
    if b.count(start) != 1 or b.count(end) != 1:
        print("   WARNING: marker not unique", start, b.count(start), end, b.count(end))
    return b[i:j]


def main():
    data = {}
    for tag, name in FILES:
        with open(os.path.join(R, name), "rb") as f:
            data[tag] = f.read()
        print("%s %-22s %6d bytes sha256 %s" % (tag, name, len(data[tag]), sha(data[tag])))
    print()
    spans = [
        ("reconciler text", b"# Round 14 reconciliation", b"## Lead's addendum"),
        ("A2+A3", b"### A2.", b"### A4."),
        ("A2 only", b"### A2.", b"### A3."),
        ("A3 only", b"### A3.", b"### A4."),
    ]
    for label, s, e in spans:
        got = {t: span(data[t], s, e) for t in data}
        hs = {t: (sha(v)[:16] if v is not None else None) for t, v in got.items()}
        ln = {t: (len(v) if v is not None else None) for t, v in got.items()}
        same = len(set(got[t] for t in got)) == 1 and all(v is not None for v in got.values())
        print("%-16s v1 %s (%s B) | v2 %s (%s B) | v3 %s (%s B) | byte-identical in all three: %s"
              % (label, hs["v1"], ln["v1"], hs["v2"], ln["v2"], hs["v3"], ln["v3"], same))
    # the reconciler's text runs from the first heading to the end of section 7: check that what precedes
    # the first heading is only the lead's note (every line starts with '>' or is blank)
    for t in data:
        pre = data[t][: data[t].find(b"# Round 14 reconciliation")]
        bad = [ln for ln in pre.split(b"\n") if ln and not ln.startswith(b">")]
        print("%s: lines before the first heading that are not blockquote: %d" % (t, len(bad)))
    print()

    # format of v3
    b = data["v3"]
    print("v3 format:")
    print("   BOM:", b.startswith(b"\xef\xbb\xbf"))
    try:
        txt = b.decode("utf-8", errors="strict")
        print("   strict UTF-8 decode: OK")
    except UnicodeDecodeError as ex:
        print("   strict UTF-8 decode: FAILED", ex)
        txt = b.decode("utf-8", errors="replace")
    print("   CR bytes:", b.count(b"\r"), "| LF bytes:", b.count(b"\n"), "| ends with LF:", b.endswith(b"\n"),
          "| ends with two LF:", b.endswith(b"\n\n"))
    print("   non-ASCII bytes:", sum(1 for x in b if x > 127), "| tab:", b.count(b"\t"), "| NUL:", b.count(b"\0"))
    other_ctrl = sum(1 for x in b if x < 32 and x not in (10,))
    print("   other control bytes (besides LF):", other_ctrl)
    lines = txt.split("\n")
    print("   lines (LF-separated, last empty piece dropped):", len(lines) - (1 if lines[-1] == "" else 0))
    print("   trailing-space lines:", sum(1 for ln in lines if ln.endswith(" ")))
    print()

    # privacy of v3: environment values are compared but never printed
    print("v3 privacy (values never printed):")
    env = {}
    for k in ("USERNAME", "COMPUTERNAME", "USERDOMAIN", "LOGONSERVER", "USERDNSDOMAIN"):
        v = os.environ.get(k)
        if v:
            env[k] = v.strip("\\")
    prof = os.environ.get("USERPROFILE")
    if prof:
        env["USERPROFILE basename"] = os.path.basename(prof.rstrip("\\"))
    low = txt.lower()
    for k, v in env.items():
        if len(v) >= 3:
            hits = [i + 1 for i, ln in enumerate(lines) if v.lower() in ln.lower()]
            print("   %-22s present: %s %s" % (k, bool(hits), ("lines " + str(hits[:10])) if hits else ""))
        else:
            print("   %-22s too short to test" % k)
    pats = {
        "e-mail": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        "any @": r"@",
        "UUID": r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b",
        "wf_ id": r"\bwf_[0-9A-Za-z]+",
        "word workflow": r"(?i)workflow",
        "word session": r"(?i)session",
        "agent- id": r"(?i)agent-[0-9a-f]{6,}",
        "C: path": r"(?i)\bC:\\",
        "Users\\ path": r"(?i)users\\",
        "AppData": r"(?i)appdata",
        "URL": r"(?i)https?://|www\.",
        "claude.ai": r"(?i)claude\.ai",
        "transcript word": r"(?i)transcript",
        "jsonl agent log": r"(?i)agent-[^\s]*\.jsonl",
    }
    for k, p in pats.items():
        hits = [i + 1 for i, ln in enumerate(lines) if re.search(p, ln)]
        print("   %-18s lines: %s" % (k, hits[:20] if hits else "none"))
    # hex-like tokens of 8 or more hex digits; expected ones are named, others reported by line only
    expected = set()
    for t in ("v1", "v2"):
        expected.add(sha(data[t])[:16])
    for ln in lines:
        for m in re.finditer(r"\b(9989bd58|1edbc3d1|ccb17021|f2bb2a79)\b", ln):
            expected.add(m.group(1))
    run_dir = r"D:\treeroute\rival_export"
    run_hex = set()
    if os.path.isdir(run_dir):
        for p in os.listdir(run_dir):
            pdir = os.path.join(run_dir, p)
            if os.path.isdir(pdir):
                for q in os.listdir(pdir):
                    if "_" in q:
                        run_hex.add(q.split("_", 1)[1])
    expected |= run_hex
    toks = []
    for i, ln in enumerate(lines):
        for m in re.finditer(r"(?<![0-9A-Za-z])[0-9a-fA-F]{8,}(?![0-9A-Za-z])", ln):
            toks.append((i + 1, m.group(0)))
    unexpected = [(i, len(tk)) for i, tk in toks if tk.lower() not in expected and not tk.isdigit()]
    digits_only = [(i, len(tk)) for i, tk in toks if tk.isdigit()]
    print("   hex-like tokens (>= 8 hex digits): %d; expected (sample hashes, run folders, earlier-version SHA "
          "prefixes): %d; digit-only (dates/numbers): %d; unexpected: %s"
          % (len(toks), sum(1 for i, tk in toks if tk.lower() in expected), len(digits_only),
             unexpected if unexpected else "none"))
    print("   run-folder hex suffixes found in rival_export:", len(run_hex))
    # the two earlier-version SHA prefixes quoted in A7
    for t in ("v1", "v2"):
        pre16 = sha(data[t])[:16]
        print("   A7 quotes the %s SHA-256 prefix %s...: %s" % (t, pre16, (pre16 + "...") in txt))
    print("   A7 sizes quoted: 43,582 present %s; 63,078 present %s" % ("43,582 bytes" in txt, "63,078 bytes" in txt))


if __name__ == "__main__":
    main()
