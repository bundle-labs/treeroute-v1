# r12 (version 2, G2): the text sources SHAP\SAMPLE_REGISTER.txt, the five SHAP\logs\tr_shap_<p>_lead0.log and
# V\_lead\outputs\bardl_maxima.txt, read as version 2's section 1 says (open(path, encoding="utf-8-sig"), whose
# universal newlines turn every line end into "\n", then split on "\n"), must give exactly the lines that the
# reconciler's version-1 readers give: r03 (UTF-8, one leading BOM removed, CRLF -> LF, split on "\n") and r04 (the
# register and the logs: UTF-8, CRLF -> LF, split; the maxima: leading BOM stripped, CRLF -> LF, split). If they do,
# G2 changes no input of r03 or r04 and those readers stay as they are. Read-only; prints.
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
SHAP = Path("D:/treeroute/analysis/shap_v1")
V = SHAP / "verify_v1"
MAX = "V\\_lead\\outputs\\bardl_maxima.txt"
files = [("SHAP\\SAMPLE_REGISTER.txt", SHAP / "SAMPLE_REGISTER.txt")]
files += [("SHAP\\logs\\tr_shap_%s_lead0.log" % p, SHAP / "logs" / ("tr_shap_%s_lead0.log" % p))
          for p in ("pm25", "ndvi", "fire", "defo", "coral")]
files.append((MAX, V / "_lead" / "outputs" / "bardl_maxima.txt"))
alleq = True
for short, path in files:
    raw = path.read_bytes()
    with open(path, encoding="utf-8-sig") as fh:
        g2 = fh.read().split("\n")
    t = raw.decode("utf-8")
    r03 = (t[1:] if t.startswith("\ufeff") else t).replace("\r\n", "\n").split("\n")
    r04 = (t.lstrip("\ufeff") if short == MAX else t).replace("\r\n", "\n").split("\n")
    crlf = raw.count(b"\r\n")
    lone_cr = raw.count(b"\r") - crlf
    lone_lf = raw.count(b"\n") - crlf
    eq = (g2 == r03, g2 == r04)
    alleq = alleq and all(eq)
    print("%-36s %7d bytes; BOM %-3s; CRLF %4d; lone CR %d; lone LF %d; lines read (G2) %4d; r03 reader equal %s; r04 reader equal %s"
          % (short, len(raw), "yes" if raw.startswith(b"\xef\xbb\xbf") else "no", crlf, lone_cr, lone_lf, len(g2), eq[0], eq[1]))
print("all readers give the G2 lines:", alleq)
