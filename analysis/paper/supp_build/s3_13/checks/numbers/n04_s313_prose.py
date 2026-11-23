# n04: extract S3.13's prose (tables removed) from the staged S3_posthoc.md, and list every number token of the
# visible text (HTML comments removed) per segment, with the fact IDs of the comment that follows the segment.
import os
import re

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", ".."))
OUT = os.path.join(ROOT, r"paper\supp_build\s3_13")
STAGE = os.path.join(OUT, "stage")
HERE = os.path.dirname(os.path.abspath(__file__))
S3 = os.path.join(STAGE, r"paper\draft\S3_posthoc.md")
AGREED = os.path.join(OUT, r"reconcile\tables_agreed.md")

s3 = open(S3, "rb").read().decode("utf-8")
agreed = open(AGREED, "rb").read().decode("utf-8")
lines = agreed.split("\n")
cap_re = re.compile(r"^\*\*Table (9|S3\.\d+)[ .]")
starts = [i for i, l in enumerate(lines) if cap_re.match(l)]
blocks = []
for s in starts:
    e = len(lines)
    for j in range(s + 1, len(lines)):
        if cap_re.match(lines[j]) or lines[j].startswith("## "):
            e = j
            break
    while e > s and lines[e - 1].strip() == "":
        e -= 1
    blocks.append("\n".join(lines[s:e]))

i0 = s3.index("\n## S3.13 ")
sec = s3[i0 + 1:]
# the S3.21 caption as staged
for b in blocks:
    if b.startswith("**Table S3.21"):
        b2 = b.replace("tree bank and the sampled locations' routers were rebuilt",
                       "tree bank with its correctors and placebos, and the sampled locations' routers, were rebuilt")
        sec = sec.replace(b2, "[[TABLE S3.21]]")
    elif not b.startswith("**Table 9."):
        name = cap_re.match(b).group(1)
        n = sec.count(b)
        sec = sec.replace(b, "[[TABLE %s]]" % name)
with open(os.path.join(HERE, "s313_prose.txt"), "w", encoding="utf-8", newline="\n") as f:
    f.write(sec)
print("S3.13 section chars:", len(sec))
print("remaining '|' table lines:", sum(1 for l in sec.split("\n") if l.startswith("|")))

# segments: visible text followed by a comment
num_re = re.compile(r"(?<![\w.])[−-]?\d[\d,]*(?:\.\d+)?(?:\s?[×x]\s?10[⁻\-]?[⁰¹²³⁴⁵⁶⁷⁸⁹\d]+)?%?|10[⁻][⁰¹²³⁴⁵⁶⁷⁸⁹]+")
out = []
pos = 0
for m in re.finditer(r"<!--(.*?)-->", sec, flags=re.S):
    vis = sec[pos:m.start()]
    com = m.group(1)
    pos = m.end()
    toks = num_re.findall(vis)
    ids = re.findall(r"\b(A\d+|[A-Z]{1,2}\d+[a-z]?)\b", com)
    out.append((vis, com, toks, ids))
tail = sec[pos:]
out.append((tail, "", num_re.findall(tail), []))
with open(os.path.join(HERE, "s313_numbers.txt"), "w", encoding="utf-8", newline="\n") as f:
    for k, (vis, com, toks, ids) in enumerate(out):
        if not toks:
            continue
        f.write("=== seg %d\nVIS: %s\nTOKENS: %s\nCOMMENT: %s\n\n" % (k, vis.strip()[:4000], toks, com.strip()[:600]))
print("segments:", len(out), "with numbers:", sum(1 for o in out if o[2]))
