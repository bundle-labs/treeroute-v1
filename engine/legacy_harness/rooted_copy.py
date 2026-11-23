"""Make and check the ROOTED COPY of the shipped adaptation.py (plan 4.4; legacy harness only).

The shipped adaptation.py hard-codes its output root (``OUT_ROOT = "D:/adaptation"``, line 139), and
D:/adaptation is a protected root (D:/treeroute/registry/protected_roots.txt). The harness therefore
runs a COPY, ``adaptation_rooted.py``, whose ONLY change is that one line:

    OUT_ROOT = "D:/adaptation"
 -> OUT_ROOT = os.environ.get("ADAPTATION_OUT_ROOT", "D:/treeroute/golden")

``os`` is imported at line 120 of the shipped file, before line 139, so the new line needs nothing
else. Every other byte (line endings included) is copied unchanged.

    py -3.9 rooted_copy.py check     # read-only: prove the copy differs from the source by that line only
    py -3.9 rooted_copy.py make      # write adaptation_rooted.py; refuses if it already exists

The function ``check(src, dst)`` returns ok only if (a) the two files have the same number of lines,
(b) exactly one line differs, and (c) that line is the expected OLD line in the source and the
expected NEW line in the copy, with the same line ending. launch_pinned.py --copy-of calls it and
refuses a copy that fails it, before anything runs.

The command ``py -3.9 rooted_copy.py check`` exits 0 only if (a)-(c) hold AND (d) the source's and
the copy's sha256 equal the ones registered in the NEWEST golden registry (goldens.json or the
highest goldens_vN.json; fire_smoke.source_sha256 / script_sha256). If no registry exists yet, (d)
is reported as not checked.

Outside the product: the engine never imports this module (G-IMPORT).
"""
import difflib
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(os.path.dirname(HERE))
SOURCE = os.path.join(PROJECT, "adaptation.py")
COPY = os.path.join(HERE, "adaptation_rooted.py")

OLD = b'OUT_ROOT = "D:/adaptation"'
NEW = b'OUT_ROOT = os.environ.get("ADAPTATION_OUT_ROOT", "D:/treeroute/golden")'
ENV_VAR = "ADAPTATION_OUT_ROOT"
DEFAULT_ROOT = "D:/treeroute/golden"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _split_keepends(data):
    return data.splitlines(keepends=True)


def _strip_eol(line):
    return line.rstrip(b"\r\n")


def make(src=SOURCE, dst=COPY):
    """Write the rooted copy. Refuses if dst exists or if the OLD line is not found exactly once."""
    if os.path.exists(dst):
        raise SystemExit("rooted_copy: %s already exists; it is never overwritten." % dst)
    with open(src, "rb") as f:
        data = f.read()
    lines = _split_keepends(data)
    hits = [i for i, ln in enumerate(lines) if _strip_eol(ln) == OLD]
    if len(hits) != 1:
        raise SystemExit("rooted_copy: expected the line %r exactly once in %s, found it %d times."
                         % (OLD.decode(), src, len(hits)))
    i = hits[0]
    eol = lines[i][len(_strip_eol(lines[i])):]
    lines[i] = NEW + eol
    out = b"".join(lines)
    with open(dst, "xb") as f:      # 'x': never overwrite
        f.write(out)
    return check(src, dst)


def check(src=SOURCE, dst=COPY):
    """Compare source and copy line by line. Returns a dict; 'ok' is True only for the one expected change."""
    with open(src, "rb") as f:
        a = _split_keepends(f.read())
    with open(dst, "rb") as f:
        b = _split_keepends(f.read())
    changed = [(i + 1, x, y) for i, (x, y) in enumerate(zip(a, b)) if x != y]
    same_len = len(a) == len(b)
    problems = []
    if not same_len:
        problems.append("line counts differ: source %d, copy %d" % (len(a), len(b)))
    if len(changed) != 1:
        problems.append("%d lines differ (expected exactly 1)" % len(changed))
    elif not (_strip_eol(changed[0][1]) == OLD and _strip_eol(changed[0][2]) == NEW):
        problems.append("the differing line is not the expected OUT_ROOT change")
    elif changed[0][1][len(OLD):] != changed[0][2][len(NEW):]:
        problems.append("the line ending of the changed line differs")
    udiff = "".join(difflib.unified_diff([x.decode("utf-8", "replace") for x in a],
                                         [y.decode("utf-8", "replace") for y in b],
                                         fromfile=src.replace("\\", "/"),
                                         tofile=dst.replace("\\", "/"), n=0))
    return {
        "ok": not problems,
        "problems": problems,
        "source": src.replace("\\", "/"),
        "source_sha256": sha256_file(src),
        "copy": dst.replace("\\", "/"),
        "copy_sha256": sha256_file(dst),
        "lines_source": len(a),
        "lines_copy": len(b),
        "changed_lines": [{"line": n, "source": _strip_eol(x).decode("utf-8", "replace"),
                           "copy": _strip_eol(y).decode("utf-8", "replace")} for n, x, y in changed],
        "unified_diff": udiff,
        "env_var": ENV_VAR,
        "default_root": DEFAULT_ROOT,
    }


def check_registered(res, here=HERE):
    """(d): compare a check() result with the newest golden registry's fire_smoke source/script
    sha256. Returns (registry_path or None, [problems])."""
    import goldens                      # lazy: goldens imports this module inside build_fire
    try:
        _n, path = goldens.latest_registry(here)
    except SystemExit:
        return None, []
    with open(path, encoding="utf-8") as f:
        fire = json.load(f)["goldens"]["fire_smoke"]
    problems = []
    if fire["source_sha256"] != res["source_sha256"]:
        problems.append("adaptation.py sha256 %s differs from the registered %s"
                        % (res["source_sha256"], fire["source_sha256"]))
    if fire["script_sha256"] != res["copy_sha256"]:
        problems.append("adaptation_rooted.py sha256 %s differs from the registered %s"
                        % (res["copy_sha256"], fire["script_sha256"]))
    return path, problems


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv not in (["check"], ["make"]):
        raise SystemExit("usage: py -3.9 rooted_copy.py check|make")
    res = make() if argv[0] == "make" else check()
    print(json.dumps({k: v for k, v in res.items() if k != "unified_diff"}, indent=1))
    print(res["unified_diff"])
    ok = res["ok"]
    if argv[0] == "check":
        reg, probs = check_registered(res)
        if reg is None:
            print("(d) NOT CHECKED: no golden registry exists yet")
        else:
            print("(d) against %s: %s" % (reg.replace("\\", "/"),
                                          "sha256 match" if not probs else "; ".join(probs)))
        ok = ok and not probs
        res["problems"] = res["problems"] + probs
    print("ROOTED COPY %s" % ("OK: exactly the one OUT_ROOT line differs" if ok
                              else "NOT OK: " + "; ".join(res["problems"])))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
