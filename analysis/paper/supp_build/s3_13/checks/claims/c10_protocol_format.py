"""Format checks of the staged SHAP protocol against the live one (read only).

Checks: no BOM; LF only (no CR); exactly one final LF (no blank line at the end); the staged file equals the
live file with lines inserted only (the live text is a prefix, line by line, of the staged text up to the
insertion point, and nothing after it changed); the length of every new line (characters, and with the
@@SNAP@@ placeholders replaced by a 30-character folder name); non-ASCII characters in new lines; sections 3
and 8 (from their heading to the next '## ' heading) byte-identical, with their SHA-256 and size.
"""
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(os.path.dirname(HERE))
LIVE = r"D:\treeroute\analysis\shap_v1\PROTOCOL.md"
STAGED = os.path.join(OUT, "stage", "shap", "PROTOCOL.md")


def section(data, num):
    head = ("\n## %d. " % num).encode()
    i = data.find(head)
    if i < 0:
        return None
    i += 1
    j = data.find(b"\n## ", i)
    return data[i:j + 1] if j >= 0 else data[i:]


def main():
    with open(LIVE, "rb") as fh:
        live = fh.read()
    with open(STAGED, "rb") as fh:
        staged = fh.read()
    print("BOM:", staged.startswith(b"\xef\xbb\xbf"), "| CR count:", staged.count(b"\r"),
          "| ends with LF:", staged.endswith(b"\n"), "| ends with two LF:", staged.endswith(b"\n\n"))
    print("live sha256", hashlib.sha256(live).hexdigest()[:16], "size", len(live),
          "| staged sha256", hashlib.sha256(staged).hexdigest()[:16], "size", len(staged))
    L = live.decode("utf-8").split("\n")
    S = staged.decode("utf-8").split("\n")
    # find the first differing line
    k = 0
    while k < len(L) and k < len(S) and L[k] == S[k]:
        k += 1
    # the tail of the live file must equal the tail of the staged file
    tail = len(L) - k
    same_tail = S[len(S) - tail:] == L[k:] if tail > 0 else True
    inserted = S[k:len(S) - tail] if tail > 0 else S[k:]
    print("first new line index (1-based):", k + 1, "| live lines after it:", tail, "| tail equal:", same_tail,
          "| inserted lines:", len(inserted))
    longest = 0
    for idx, ln in enumerate(inserted):
        n1 = len(ln)
        n2 = len(ln.replace("@@SNAP@@", "X" * 30))
        longest = max(longest, n2)
        flags = []
        if n1 > 120:
            flags.append("LONG %d" % n1)
        if n2 > 120:
            flags.append("LONG-with-snap %d" % n2)
        na = [c for c in ln if ord(c) > 127]
        if na:
            flags.append("non-ASCII %r" % "".join(na))
        if "@@" in ln:
            flags.append("placeholder")
        if flags:
            print("  line %d: %s" % (k + 1 + idx, "; ".join(flags)))
    print("longest new line with a 30-char snapshot name:", longest)
    for num in (3, 8):
        a = section(live, num)
        b = section(staged, num)
        print("section %d: live %s (%d B) staged %s (%d B) equal %s" % (
            num, hashlib.sha256(a).hexdigest()[:16], len(a), hashlib.sha256(b).hexdigest()[:16], len(b), a == b))
    return 0


if __name__ == "__main__":
    sys.exit(main())
