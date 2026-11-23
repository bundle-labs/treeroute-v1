"""Shared helpers of the post hoc SHAP analysis (rulings AW1-AW5; post hoc under ruling AK).

Standard library only at import time: the engine's launcher refuses to start when numpy is already loaded, so this
module must be importable before the thread pins. numpy is imported inside the functions that need it.

What lives here:
  - the folder layout of D:/treeroute/analysis/shap_v1 and the write guard (every write goes under ROOT; protected
    places are refused even through a junction);
  - privacy: every log line and every written text is passed through redact(), which replaces any C:/Users/<name>
    prefix by C:/Users/~ (no account name reaches a file);
  - the timestamped logger (logs/<name>.log, append);
  - atomic writes and finished-piece records (resume: a piece is skipped only when its file still has the SHA-256
    recorded beside it and its inputs hash is the same);
  - the deterministic generator: SHA-256 of a recorded salt and key, never a library RNG stream (AW5 "fixed,
    recorded generator"; the owner's no-seed rule);
  - the problem table: the five headline runs, their rival boards and exports (read-only paths).
"""
import datetime
import hashlib
import json
import os
import re
import sys
import time

sys.dont_write_bytecode = True

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir))
SCRIPTS = os.path.join(ROOT, "scripts")
LOGS = os.path.join(ROOT, "logs")
PROTOCOL = os.path.join(ROOT, "PROTOCOL.md")
SAMPLE_REGISTER = os.path.join(ROOT, "SAMPLE_REGISTER.txt")
DEFAULT_N = 1000
TREEROUTE = "D:/treeroute"

# Places this analysis never writes to (checked after resolving junctions and links). ROOT itself lies under
# D:/treeroute/analysis, which is allowed only below ROOT.
PROTECTED = (
    "D:/treeroute/runs", "D:/treeroute/registry", "D:/treeroute/rivals", "D:/treeroute/rivals_build",
    "D:/treeroute/rivals_human", "D:/treeroute/rivals_human_dry", "D:/treeroute/human_rivals_build",
    "D:/treeroute/human_products", "D:/treeroute/human_index", "D:/treeroute/rival_export",
    "D:/treeroute/rivals_table", "D:/treeroute/tmp", "D:/treeroute/engine_v2", "D:/treeroute/ckpt_20261013",
    "D:/treeroute/coral_build", "D:/treeroute/fit_build", "D:/treeroute/route_build",
    "D:/treeroute/analysis/ablation_perlocation", "D:/adaptation", "D:/pm25_adapt", "D:/pm25_forecast",
    "D:/pm25_rivals", "D:/run89full", "D:/defo_corrector", "D:/defo_tier2",
)

PROBLEMS = {
    # problem: headline run, engine package, router kind, leads reported, engine snapshot holding the run's code
    "coral": {"run": "D:/treeroute/runs/coral/headline/20261020_f3b8e3da", "package": "coral", "kind": "neighbour",
              "leads": (0, 183, 365), "engine": "D:/treeroute/engine_v2/engine_v1_ref",
              "board": "D:/treeroute/rivals/coral/20261020_f3b8e3da",
              "export": "D:/treeroute/rival_export/coral/20261020_f3b8e3da", "human": None},
    "pm25": {"run": "D:/treeroute/runs/pm25/headline/20261007_74e67609", "package": "pm25", "kind": "per_unit",
             "leads": (0, 6, 12), "engine": "D:/treeroute/ckpt_20261013/engine_before",
             "board": "D:/treeroute/rivals/pm25/20261007_74e67609",
             "export": "D:/treeroute/rival_export/pm25/20261007_74e67609", "human": None},
    "ndvi": {"run": "D:/treeroute/runs/ndvi/headline/20261016_d1de3158", "package": "ndvi", "kind": "per_unit",
             "leads": (0, 6, 12), "engine": "D:/treeroute/analysis/ablation_perlocation/ckproof/engine_65a177bc",
             "board": "D:/treeroute/rivals/ndvi/20261016_d1de3158",
             "export": "D:/treeroute/rival_export/ndvi/20261016_d1de3158",
             "human": "D:/treeroute/rivals_human/ndvi/20261016_d1de3158"},
    "fire": {"run": "D:/treeroute/runs/fire/headline/20261017_869d1f38", "package": "fire", "kind": "per_unit",
             "leads": (0, 6, 12), "engine": "D:/treeroute/analysis/ablation_perlocation/ckproof/engine_65a177bc",
             "board": "D:/treeroute/rivals/fire/20261017_869d1f38",
             "export": "D:/treeroute/rival_export/fire/20261017_869d1f38", "human": None},
    "defo": {"run": "D:/treeroute/runs/defo/headline/20261017_d71c61f4", "package": "defo", "kind": "region",
             "leads": (0, 1), "engine": "D:/treeroute/analysis/ablation_perlocation/ckproof/engine_65a177bc",
             "board": "D:/treeroute/rivals/defo/20261017_d71c61f4",
             "export": "D:/treeroute/rival_export/defo/20261017_d71c61f4", "human": None},
}

# Scope options of the owner (ruling AW5: "the scope (which leads) is still the owner's choice"). 'kept' marks the
# problem-leads whose kept (reported) prediction is a tree arm; at the others the kept value is a feature-free
# baseline (the seasonal normal or coral's donor-row median), so treeroute has no SHAP there.
KEPT_TREE_LEADS = {"coral": (0, 183), "pm25": (0, 6), "ndvi": (0,), "fire": (0,), "defo": (0, 1)}
SCOPES = {
    "i": {p: (0,) for p in PROBLEMS},
    "ii": {"coral": (0, 183), "pm25": (0, 6), "ndvi": (0, 6), "fire": (0, 6), "defo": (0, 1)},
    "iii": {p: PROBLEMS[p]["leads"] for p in PROBLEMS},
}


def engine_live_root():
    """The LIVE engine folder, found from the home folder at run time (no account name is written anywhere)."""
    return os.path.join(os.path.expanduser("~"), "Downloads", "claude things", "data set for reserch paper", "engine")


def package_dir(problem):
    return os.path.join(engine_live_root(), "datasets", PROBLEMS[problem]["package"])


# ---------------------------------------------------------------------------------------------------------------
# privacy and paths
_USER_RE = re.compile(r"([A-Za-z]:[\\/]+Users[\\/]+)([^\\/\"'\r\n]+)", re.IGNORECASE)


def redact(text):
    """Replace every C:/Users/<account> prefix with C:/Users/~ (logs and written texts never carry an account)."""
    return _USER_RE.sub(lambda m: m.group(1) + "~", str(text))


def norm(path):
    return os.path.normcase(os.path.abspath(str(path))).replace("\\", "/").rstrip("/")


def _under(path, root):
    p, r = norm(path), norm(root)
    return p == r or p.startswith(r + "/")


def assert_writable(path):
    """Refuse a write target outside ROOT, or inside a protected place (checked on the path as given and on the
    path with every junction and link resolved). Returns the absolute path."""
    targets = [os.path.abspath(str(path))]
    try:
        targets.append(os.path.realpath(str(path)))
    except OSError:
        pass
    for t in targets:
        if not _under(t, ROOT):
            raise SystemExit("REFUSED: %s lies outside the analysis folder %s" % (redact(t), ROOT))
        for p in PROTECTED:
            if _under(t, p) and not _under(ROOT, p):
                raise SystemExit("REFUSED: %s lies under the protected place %s" % (redact(t), p))
    return targets[0]


def makedirs(path):
    assert_writable(path)
    os.makedirs(path, exist_ok=True)
    return path


# ---------------------------------------------------------------------------------------------------------------
# logging
class Log(object):
    """Timestamped log lines to logs/<name>.log (append) and the console, every line redacted."""

    def __init__(self, name, folder=LOGS):
        makedirs(folder)
        self.path = assert_writable(os.path.join(folder, name + ".log"))
        self.t0 = time.time()

    def __call__(self, msg):
        line = "[%s +%7.1fs] %s" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), time.time() - self.t0,
                                    redact(msg))
        print(line, flush=True)
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    def file_only(self, msg):
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write("[%s] %s\n" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), redact(msg)))


def rss_gb():
    try:
        import psutil
        mi = psutil.Process().memory_info()
        return round(getattr(mi, "peak_wset", mi.rss) / 2 ** 30, 2)
    except Exception:
        return None


# ---------------------------------------------------------------------------------------------------------------
# hashing, atomic writes, finished pieces
def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(path, block=1 << 22):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(block)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _default(o):
    try:
        import numpy as np
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return float(o)
        if isinstance(o, np.bool_):
            return bool(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
    except ImportError:
        pass
    if hasattr(o, "value"):
        return o.value
    return str(o)


def dumps(obj):
    return json.dumps(obj, indent=1, sort_keys=True, default=_default, allow_nan=True)


def _sanitize(obj):
    """A JSON round trip (numpy types and NaN made comparable)."""
    return json.loads(json.dumps(obj, default=_default, allow_nan=True, sort_keys=True))


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=_default)


def write_text(path, text):
    """Atomic text write (redacted)."""
    path = assert_writable(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(redact(text))
    os.replace(tmp, path)
    return path


def write_json(path, obj):
    return write_text(path, dumps(obj))


def read_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def write_parquet(path, frame):
    """Atomic parquet write of a pandas frame (one write, row groups as pyarrow makes them)."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    path = assert_writable(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    pq.write_table(pa.Table.from_pandas(frame, preserve_index=False), tmp)
    os.replace(tmp, path)
    return path


def write_npz(path, **arrays):
    import numpy as np
    path = assert_writable(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp.npz"
    np.savez(tmp, **arrays)
    os.replace(tmp, path)
    return path


def inputs_hash(obj):
    return sha256_bytes(canonical(obj).encode("utf-8"))


def piece_done(path, inputs):
    """True when <path> exists, its sidecar <path>.done.json names the same inputs hash, and the file still has
    the SHA-256 recorded at the end of its write. Anything else is redone (and logged by the caller)."""
    side = path + ".done.json"
    if not (os.path.isfile(path) and os.path.isfile(side)):
        return False
    try:
        rec = read_json(side)
    except (OSError, ValueError):
        return False
    if rec.get("inputs") != inputs_hash(inputs):
        return False
    return rec.get("sha256") == sha256_file(path)


def mark_done(path, inputs, extra=None):
    rec = {"file": os.path.basename(path), "sha256": sha256_file(path), "bytes": os.path.getsize(path),
           "inputs": inputs_hash(inputs), "finished": datetime.datetime.now().isoformat(timespec="seconds")}
    if extra:
        rec.update(extra)
    write_json(path + ".done.json", rec)
    return rec


# ---------------------------------------------------------------------------------------------------------------
# the deterministic generator (SHA-256 of a recorded salt and a key; no library random stream)
def hash_key(salt, key):
    """A 64-bit integer from SHA-256('<salt>|<key>'): the sort key of every deterministic choice."""
    return int.from_bytes(hashlib.sha256(("%s|%s" % (salt, key)).encode("utf-8")).digest()[:8], "big")


def hash_order(salt, keys):
    """The keys sorted by hash_key (ties, which do not occur in practice, by the key text)."""
    return sorted(keys, key=lambda k: (hash_key(salt, k), str(k)))


def draw_matrix(salt, n_clusters, n_draws):
    """Cluster bootstrap draws (n_draws x n_clusters, int64): entry (b, i) = SHA-256 counter value mod n_clusters.
    The modulo bias is below n_clusters / 2^64. Saved with its SHA-256 by the caller."""
    import numpy as np
    out = np.empty((int(n_draws), int(n_clusters)), dtype=np.int64)
    for b in range(int(n_draws)):
        for i in range(int(n_clusters)):
            out[b, i] = hash_key(salt, "%d|%d" % (b, i)) % int(n_clusters)
    return out


# ---------------------------------------------------------------------------------------------------------------
# thread pins (set BEFORE numpy loads)
PIN_VARS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS",
            "BLIS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")


def pin_threads(n):
    """Set the BLAS/OpenMP pins to n before numpy loads (refuse when numpy is already loaded with other pins)."""
    if "numpy" in sys.modules:
        bad = [v for v in PIN_VARS if os.environ.get(v) != str(n)]
        if bad:
            raise SystemExit("REFUSED: numpy was imported before the thread pins (%s)" % ", ".join(bad))
        return
    for v in PIN_VARS:
        os.environ[v] = str(n)


def versions():
    """Installed versions of the libraries the analysis reads (importlib.metadata)."""
    from importlib import metadata
    out = {"python": sys.version.split()[0]}
    for name in ("numpy", "scipy", "pandas", "pyarrow", "scikit-learn", "scikit-learn-intelex", "daal", "tbb",
                 "lightgbm", "threadpoolctl", "psutil", "pydantic", "pydantic-core", "typer", "click", "PyYAML"):
        try:
            out[name] = metadata.version(name)
        except Exception:
            out[name] = None
    return out


def register_lines(register=None):
    """The register's lines as dicts (key=value fields; the first field is the timestamp)."""
    reg = register or SAMPLE_REGISTER
    out = []
    if not os.path.isfile(reg):
        return out
    with open(reg, encoding="utf-8") as fh:
        for ln in fh:
            parts = ln.split()
            if not parts:
                continue
            rec = {"_stamp": parts[0], "_line": ln.rstrip("\n")}
            for p in parts[1:]:
                if "=" in p:
                    k, v = p.split("=", 1)
                    rec[k] = v
            out.append(rec)
    return out


def registered(problem, sample_file, register=None):
    """True when the sample file's SHA-256 is in the register (stop rule S-SAMPLE)."""
    if not os.path.isfile(sample_file):
        return False
    sha = sha256_file(sample_file)
    return any(r.get("problem") == problem and r.get("sample") == sha for r in register_lines(register))


def sample_identity(problem, sample_root, register=None, lead=None):
    """The registered identity of the sample in sample_root: its SHA-256, the background file's SHA-256 at the lead
    (when given), the register line and the manifest's parameters. Refuses (S-SAMPLE) a sample that is not in the
    register, or a background file whose hash is not the registered one."""
    sfile = os.path.join(sample_root, "sample.parquet")
    if not os.path.isfile(sfile):
        raise SystemExit("STOP S-SAMPLE: %s does not exist" % sfile)
    sha = sha256_file(sfile)
    lines = [r for r in register_lines(register) if r.get("problem") == problem and r.get("sample") == sha]
    if not lines:
        raise SystemExit("STOP S-SAMPLE: %s is not in the sample register" % sfile)
    rec = lines[-1]
    out = {"sample_sha256": sha, "register_line": rec.get("_line"), "tag": rec.get("tag"), "n": rec.get("n")}
    man = os.path.join(sample_root, "sample_manifest.json")
    if os.path.isfile(man):
        m = read_json(man)
        out.update({"manifest_n": m.get("n"), "n_asked": m.get("n_asked"),
                    "defo_regions": m.get("defo_regions", 0), "manifest_sha256": sha256_file(man)})
    if lead is not None:
        bname = "background_lead_%d.parquet" % int(lead)
        bfile = os.path.join(sample_root, bname)
        if not os.path.isfile(bfile):
            raise SystemExit("STOP S-SAMPLE: %s does not exist" % bfile)
        bsha = sha256_file(bfile)
        want = rec.get(bname)
        if want is not None and want != bsha:
            raise SystemExit("STOP S-SAMPLE: %s has SHA-256 %s, the register has %s" % (bname, bsha[:16], want[:16]))
        if want is None:
            raise SystemExit("STOP S-SAMPLE: the register line of this sample has no %s" % bname)
        out["background_sha256"] = bsha
    return out


# ---------------------------------------------------------------------------------------------------------------
# exactness: a true relative tolerance (D8), the same rule for every caller
def relative_check(saved, rebuilt, rel_tol):
    """Bit identity, or |rebuilt - saved| <= rel_tol * |saved| (a true relative bound; exact equality required
    where saved is 0 or not finite). Returns (ok, max_rel, rows_failing, max_ulps). NaN must sit in the same places."""
    import numpy as np
    s = np.asarray(saved, np.float64)
    r = np.asarray(rebuilt, np.float64)
    same_nan = bool(np.array_equal(np.isnan(s), np.isnan(r)))
    fin = np.isfinite(s) & np.isfinite(r)
    nonfin_equal = bool(np.array_equal(s[~fin & ~np.isnan(s)], r[~fin & ~np.isnan(s)]))
    d = np.abs(s[fin] - r[fin])
    a = np.abs(s[fin])
    zero = a == 0
    rel = np.where(zero, np.where(d == 0, 0.0, np.inf), d / np.where(zero, 1.0, a))
    fail = int(np.count_nonzero(rel > float(rel_tol)))
    ulps = ulp_distance(s[fin], r[fin])
    return (same_nan and nonfin_equal and fail == 0, float(rel.max()) if rel.size else 0.0, fail,
            int(ulps.max()) if ulps.size else 0)


def ulp_distance(a, b):
    """Units in the last place between float64 arrays a and b (finite values)."""
    import numpy as np
    ia = np.asarray(a, np.float64).view(np.int64)
    ib = np.asarray(b, np.float64).view(np.int64)
    big = np.int64(-0x8000000000000000)
    ia = np.where(ia < 0, big - ia, ia)
    ib = np.where(ib < 0, big - ib, ib)
    return np.abs(ia.astype(object) - ib.astype(object)).astype(np.float64) if ia.size else np.zeros(0)


# ---------------------------------------------------------------------------------------------------------------
# players: exact duplicates, variables and families (PROTOCOL.md 8; rules on names and data, not hand lists)
CALENDAR_CTX = re.compile(r"^(month|doy_sin|doy_cos|doy|(sin|cos)\d+)$")
_SUFFIXES = (re.compile(r"_lag\d+$"), re.compile(r"_(mean|min|max)$"), re.compile(r"_roll\d+$"),
             re.compile(r"_wytd$"), re.compile(r"_\d+mo$"), re.compile(r"_\d+m$"), re.compile(r"_\d+$"),
             re.compile(r"_all$"))
_VCODE = re.compile(r"^V\d\d_")


def ctx_name(player):
    """The context name of a c__ player (c__ctx:<n> or c__ctx_<n>), else None."""
    m = re.match(r"^c__ctx[:_](.+)$", player)
    return m.group(1) if m else None


def duplicate_target(player, players):
    """The tree column an exact-duplicate context column copies, by the name rule c__ctx:top5:<v> -> x__<v> (the
    caller must also prove equality on the data); None when the rule does not apply."""
    m = re.match(r"^c__ctx:top5:(.+)$", player)
    if m and ("x__" + m.group(1)) in players:
        return "x__" + m.group(1)
    return None


def variable_of(player):
    """The variable of a player (PROTOCOL.md 8, variable level): the name with its lag, aggregate (mean/min/max),
    window (_<k>, _<k>m, _<k>mo, _roll<k>, _wytd, _all) suffixes stripped repeatedly and a catalog code V<nn>_
    dropped; context columns map to 'calendar' (month and harmonics) or ctx:<name>; the seasonal normal is
    'normal'. A duplicate context column (c__ctx:top5:<v>) is the variable of x__<v>."""
    if player == "normal":
        return "normal"
    if player.startswith("c__"):
        n = ctx_name(player) or player[3:]
        m = re.match(r"^top5:(.+)$", n)
        if m:
            return variable_of("x__" + m.group(1))
        return "calendar" if CALENDAR_CTX.match(n) else "ctx:" + n
    name = player[3:] if player.startswith("x__") else player
    if name.startswith("hist_"):                 # own history: hist_last_<k>, hist_mean_<k|all>
        return re.sub(r"_(\d+|all)$", "", name)
    prev = None
    while prev != name:
        prev = name
        for rx in _SUFFIXES:
            new = rx.sub("", name)
            if new and new != name:
                name = new
                break
    name = _VCODE.sub("", name) or name
    return name


def family_of(variable, members, global_cols):
    """The family of a variable: 'own history' (hist_*), 'global indices' (every member column is global by the
    data rule), 'context and calendar' (calendar, ctx:*), 'seasonal normal', or 'local drivers'."""
    if variable == "normal":
        return "seasonal normal"
    if variable == "calendar" or variable.startswith("ctx:"):
        return "context and calendar"
    if variable.startswith("hist_"):
        return "own history"
    cols = [m for m in members if m.startswith("x__")]
    if cols and all(c in global_cols for c in cols):
        return "global indices"
    return "local drivers"


def variable_map(players):
    """{player: variable} and the sorted variable list."""
    vm = {p: variable_of(p) for p in players}
    return vm, sorted(set(vm.values()))


# ---------------------------------------------------------------------------------------------------------------
# privacy scan (files under ROOT that hold a C:/Users/<account> path; engine-written folders reported apart)
ENGINE_WRITTEN = ("engine_runs", "engine_tmp", "rebuild_engine_runs", "rebuild_engine_tmp")


def private_names():
    """The account and host names this machine and the runs' manifests carry (read at run time, never written): the
    current account (the home folder), the accounts in the five runs' recorded machine paths, the host name."""
    names = {os.path.basename(os.path.expanduser("~"))}
    for P in PROBLEMS.values():
        try:
            mf = (read_json(os.path.join(P["run"], "manifest.json")).get("machine") or {}).get("file") or ""
        except (OSError, ValueError):
            continue
        m = _USER_RE.search(mf)
        if m:
            names.add(m.group(2))
    if os.environ.get("COMPUTERNAME"):
        names.add(os.environ["COMPUTERNAME"])
    return sorted(n for n in names if n and len(n) >= 3 and n != "~")


def privacy_scan(root=None, max_bytes=50 << 20, names=None):
    """(files holding an account or host name outside the engine-written folders, count inside them). With
    names=None the names are those of private_names(); every file is searched case-insensitively, as UTF-8 bytes and
    as UTF-16-LE bytes, for a C:/Users/<account> path with an account other than '~' or for any of the names."""
    root = root or ROOT
    bad, engine = [], 0
    pats = [re.compile(rb"[A-Za-z]:[\\/]+Users[\\/]+%s" % re.escape(n.encode("utf-8")), re.IGNORECASE)
            for n in (names if names is not None else private_names())]
    pats += [re.compile(re.escape(n.encode("utf-16-le")), re.IGNORECASE)
             for n in (names if names is not None else private_names())]
    pats += [re.compile(re.escape(n.encode("utf-8")), re.IGNORECASE)
             for n in (names if names is not None else private_names())]
    for d, dirs, files in os.walk(root):
        for f in files:
            p = os.path.join(d, f)
            try:
                if os.path.getsize(p) > max_bytes:
                    continue
                with open(p, "rb") as fh:
                    data = fh.read()
                hit = any(rx.search(data) for rx in pats)
            except OSError:
                continue
            if hit:
                rel = os.path.relpath(p, root).replace("\\", "/")
                if any(part in ENGINE_WRITTEN for part in rel.split("/")):
                    engine += 1
                else:
                    bad.append(rel)
    return bad, engine


def export_files(problem, lead, part):
    """{group: file path} of one part (train, test, guardside) of a rival export lead, from its manifest (file
    names escape some characters, so the manifest is the only map)."""
    d = os.path.join(PROBLEMS[problem]["export"], "lead_%d" % int(lead))
    man = read_json(os.path.join(d, "export_manifest.json"))
    return {str(f["group"]): os.path.join(d, *str(f["path"]).split("/")) for f in man["files"]
            if str(f.get("part")) == part and "group" in f}


def out_dir(problem, lead, *parts):
    return os.path.join(ROOT, "out", problem, "lead_%d" % int(lead), *parts)


def sample_dir(problem):
    return os.path.join(ROOT, "sample", problem)


def rebuild_dir(problem, lead):
    return os.path.join(ROOT, "rebuild", problem, "lead_%d" % int(lead))
