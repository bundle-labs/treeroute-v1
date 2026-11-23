import re, sys, zipfile
rx = re.compile(rb"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
for p in sys.argv[1:]:
    with zipfile.ZipFile(p) as z:
        for n in z.namelist():
            c = len(rx.findall(z.read(n)))
            if c:
                print(p.split("\\")[-3], n, "e-mail-shaped byte strings:", c)
    raw = open(p, "rb").read()
    print(p.split("\\")[-3], "raw file e-mail-shaped byte strings:", len(rx.findall(raw)))
