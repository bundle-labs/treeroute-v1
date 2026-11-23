"""Names, paths and constants of the human-rival tool (SPEC_HUMAN.txt 1.1, 1.7, 1.8, 6 "names and paths only from
config.py"). No science and no problem name lives here: every problem fact is read from the run, the slim copy, the
problem registry (registry/<package>.yaml) or the product registry (registry/_products.yaml).

This module imports no numeric library and never imports the common harness (rivals_human/common.py does that,
pinned by its code hash).
"""
# Provenance: SPEC_HUMAN.txt 1.1 (config keys), 1.6 (families and constants), 1.7 (registry fields), 1.8 (product
# manifests), 1.11 (file names), 6 (file ownership); D:/treeroute/rivals_build/rivals/layout.py:27 ROOT_KEYS, :80
# extra keys allowed, :84 load_roots.

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

# ---------------------------------------------------------------------------------------------------- where
PACKAGE_DIR = Path(__file__).resolve().parent                 # .../human/rivals_human
BUILD_ROOT = PACKAGE_DIR.parent                               # .../human (cwd of every command)
CONFIG_NAME = "human_rivals.yaml"
DEFAULT_CONFIG = BUILD_ROOT / CONFIG_NAME
ADAPTERS_DIR = BUILD_ROOT / "adapters"
DEFAULT_REGISTRY_DIR = BUILD_ROOT / "registry"
SCHEMA_FILE = "_schema.yaml"
PRODUCTS_FILE = "_products.yaml"

# the six common roots (layout.ROOT_KEYS, copied here so this module needs no import of the common package; checked
# equal to layout.ROOT_KEYS by common.load)
ROOT_KEYS = ("engine_root", "machine_file", "export_root", "export_ckpt_root", "out_root", "moved_root")
EXTRA_KEYS = ("common_build_root", "common_harness_sha256", "common_board_root", "slim_root", "index_root",
              "products_root", "on_disk_products", "table_root", "registry_dir")
PATH_EXTRA_KEYS = tuple(k for k in EXTRA_KEYS if k != "common_harness_sha256")

# ---------------------------------------------------------------------------------------------------- formats
FORMAT_SLIM = "human-slim/1"
FORMAT_INDEX = "human-index/1"
FORMAT_BOARD = "human-board/1"
FORMAT_PICKS = "human-picks/1"
FORMAT_PRODUCT_MANIFEST = "human-product-manifest/1"

# ---------------------------------------------------------------------------------------------------- file names
SLIM_DIR = "slim"
SLIM_MANIFEST = "slim_manifest.json"
SLIM_PROGRESS = "_progress"
INDEX_MANIFEST = "lead_%d.json"
INDEX_FILE = "lead_%d.parquet"                   # one-go table
INDEX_STAGE_FILE = "lead_%d__%s.parquet"          # staged table (stage train / test)
INDEX_WORK_DIR = "_work"
PRODUCTS_OUT_DIR = "_products"
PRODUCT_MANIFEST = "product_manifest.json"
BOARD_FILE = "human_board.json"
TRIALS_DIR = "trials"
TRIALS_CSV = "trials.csv"
PICKS_FILE = "human_picks.json"
PICKS_LOCK = "human_picks.json.lock.json"
TEST_LABELS_OPENED = "test_labels_opened_human_lead_%d.json"
TEST_LABELS_GLOB = "test_labels_opened_human_lead_*.json"
SCORES_DIR = "scores"
BOARD_LEAD_CSV = "human_board_lead_%d.csv"
BOARD_LEAD_GLOB = "human_board_lead_*.csv"
BOARD_MD = "human_board.md"
LOG_FILE = "human_rivals.log"
STATUS_FILE = "human_status.json"
LEDGER_DIR = "_ledger"
LEAD_DIR = "lead_%d"
COVERAGE_FILE = "coverage_%s.parquet"
PREDS_FILE = "preds_%s.parquet"
GUARD_FILE = "guard_%s.parquet"
MAP_FILE = "map_%s.json"
DONE_FILE = "done_%s.json"
REFS_FILE = "refs.parquet"
REFS_JSON = "refs.json"
EXPORT_COPY_DIR = "exports"
TABLE_MD = "RIVALS_TABLE.md"
TABLE_CSV = "RIVALS_TABLE.csv"
TABLE_INPUTS = "inputs_sha256.txt"

# the common board's file names (read-only; the joiner reads them)
COMMON_BOARD_FILE = "board.json"
COMMON_BOARD_LEAD_CSV = "board_lead_%d.csv"
COMMON_TEST_LABELS_OPENED = "test_labels_opened_rivals_lead_%d.json"
COMMON_SCORES_DIR = "scores"

# ---------------------------------------------------------------------------------------------------- columns
KEYS = ("unit", "group", "time", "issue", "lead")
JOIN_KEYS = ("unit", "time", "issue", "lead")
SAVED_KEYS = ("unit", "time", "lead")
COL_INFO_END = "info_end"
COL_TARGET_OBS_END = "target_obs_end"
COL_PRODUCT_CELL = "product_cell"
COL_SRC = "src"
INDEX_FIXED_COLUMNS = KEYS + (COL_INFO_END, COL_TARGET_OBS_END, COL_PRODUCT_CELL, COL_SRC)
X_PREFIX = "x__"
SRC_SEPARATOR = ";"
SEASON_KEY = "season_key"
RUNNER_COLUMNS = KEYS + ("pre", COL_INFO_END, COL_TARGET_OBS_END)

# ---------------------------------------------------------------------------------------------------- vocabulary
KINDS = ("I", "N", "M")
TIERS = ("P", "L", "A", "X")
TIER_NONE = "none"
DECIDING_TIERS = ("P", "L")
FAMILY_ORDER = ("F0", "F1", "F2", "F3", "F4", "F5", "F6")
# 1.6: which kinds a family serves. "M" here is an M-kind rival that ships an index table (its as-shipped form F0 and
# the isotonic-calibrated forms F2 / F4, spec 1.6 and 3); an M rival with a runner takes no family at all.
FAMILY_KINDS = {"F0": ("N", "M"), "F1": ("N",), "F2": ("I", "N", "M"), "F3": ("I", "N"), "F4": ("I", "N", "M"),
                "F5": ("I", "N"), "F6": ("I",)}
PICK_NOWCAST = "nowcast_inner"
PICK_LOWEST_LEAD = "lowest_covered_lead_guard"
STAGE_ALL, STAGE_TRAIN, STAGE_TEST = "all", "train", "test"
SETS_TRAIN = ("refit", "tune", "inner", "guardfit", "guard")
FIT_SETS = ("refit", "tune", "guardfit")
SCORE_SETS_HIDDEN = ("inner", "guard", "test")
COVERAGE_X = "x_finite"
COVERAGE_ALL = "all_rows"

# ---------------------------------------------------------------------------------------------------- constants
SHRINK_K = 10                       # A4: F5 shrinkage strength in rows (the engine's 10-row floor); never tuned
MIN_FIT_ROWS = 100                  # Q2.HQ9: a map needs >= 100 covered labelled fit rows ...
MIN_FIT_GROUPS = 3                  # ... in >= 3 groups, else "not calibratable at this lead"
MIN_UNIT_ROWS = 3                   # Q2.HQ9: a unit (x season key) mean / a per-unit map needs >= 3 covered rows
MIN_GROUP_TEST_ROWS = 10            # Q2.HQ9: a group enters the deciding contrast with >= 10 covered test rows
MAX_STATS = 3                       # PROT H1: at most 3 statistics per rival
N_RANGE_SLACK = 1e-9                # 1.4: N-kind values below legal_min - slack refuse
L1_MAX_BLOCKS = 20000               # the printed L1 isotonic map: x is binned into at most this many rank blocks
THREADS = 8                         # 1.13: threads pinned to 8 (as the common board)
VERDICT_REFERENCE_LABEL = "reference"
NO_SAFETY_NET = "no safety net"

# T1/T2 timing and the join of an index row: every key column
TIMING_TOL = 0


class ConfigRefusal(Exception):
    """A config, registry or schema rule refused (fail loud)."""

    def __init__(self, message: str, fix: Optional[str] = None) -> None:
        super().__init__("refused [HUMAN-CONFIG]: %s%s" % (message, "" if not fix else "  FIX: " + fix))


# ---------------------------------------------------------------------------------------------------- config file
class HumanConfig(object):
    """The parsed human_rivals.yaml: the six common roots (as a mapping the common harness reads) and the extra keys."""

    def __init__(self, data: Mapping[str, Any], source: str):
        self.source = source
        missing = [k for k in ROOT_KEYS + EXTRA_KEYS if data.get(k) in (None, "")]
        if missing:
            raise ConfigRefusal("%s has no %s" % (source, ", ".join(missing)),
                                fix="give every key of SPEC_HUMAN.txt 1.1 (paths absolute)")
        for k in ROOT_KEYS + PATH_EXTRA_KEYS:
            if not Path(str(data[k])).is_absolute():
                raise ConfigRefusal("%s: %s must be an absolute path, got %r" % (source, k, data[k]))
        sha = str(data["common_harness_sha256"])
        if len(sha) != 64 or any(ch not in "0123456789abcdef" for ch in sha):
            raise ConfigRefusal("%s: common_harness_sha256 must be a full sha256 (64 hex), got %r" % (source, sha))
        self.data = dict(data)

    def __getitem__(self, key: str) -> Any:
        return self.data[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def path(self, key: str) -> Path:
        return Path(str(self.data[key]))

    def roots_mapping(self) -> Dict[str, Any]:
        """The mapping the common harness reads (layout.roots_from_mapping: the six roots plus extra keys)."""
        return {k: str(self.data[k]) for k in ROOT_KEYS}

    def as_dict(self) -> Dict[str, Any]:
        out = {k: str(v).replace("\\", "/") for k, v in self.data.items()}
        out["_file"] = str(self.source).replace("\\", "/")
        return out


def load_config(path: Any = None) -> HumanConfig:
    """Read human_rivals.yaml (a path, a mapping, or None = the build folder's file)."""
    if isinstance(path, HumanConfig):
        return path
    if isinstance(path, Mapping):
        return HumanConfig(path, "<mapping>")
    import yaml
    p = Path(path) if path is not None else DEFAULT_CONFIG
    if not p.is_file():
        raise ConfigRefusal("the config file %s is missing" % p, fix="write human_rivals.yaml (SPEC_HUMAN.txt 1.1)")
    with open(p, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, Mapping):
        raise ConfigRefusal("%s is not a mapping of keys to values" % p)
    return HumanConfig(data, str(p))


# ---------------------------------------------------------------------------------------------------- paths
def slim_lead_dir(cfg: HumanConfig, package: str, run_name: str, lead: int) -> Path:
    return cfg.path("slim_root") / str(package) / str(run_name) / SLIM_DIR / (LEAD_DIR % int(lead))


def slim_run_dir(cfg: HumanConfig, package: str, run_name: str) -> Path:
    return cfg.path("slim_root") / str(package) / str(run_name) / SLIM_DIR


def index_rival_dir(cfg: HumanConfig, package: str, run_name: str, rival: str) -> Path:
    return cfg.path("index_root") / str(package) / str(run_name) / str(rival)


def index_work_dir(cfg: HumanConfig, package: str, run_name: str, rival: str) -> Path:
    return cfg.path("index_root") / str(package) / str(run_name) / INDEX_WORK_DIR / str(rival)


def board_dir(cfg: HumanConfig, package: str, run_name: str) -> Path:
    return cfg.path("out_root") / str(package) / str(run_name)


def common_board_dir(cfg: HumanConfig, package: str, run_name: str) -> Path:
    return cfg.path("common_board_root") / str(package) / str(run_name)


def product_out_manifest(cfg: HumanConfig, product_id: str) -> Path:
    """Where `manifest` writes the manifest of a product that was on disk before the plan (never in its folder)."""
    return cfg.path("out_root") / PRODUCTS_OUT_DIR / str(product_id) / PRODUCT_MANIFEST


def registry_dir(cfg: HumanConfig) -> Path:
    return cfg.path("registry_dir")


def read_json(path: Any) -> Any:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------------------------------- registries
def _yaml(path: Path) -> Any:
    import yaml
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_schema(cfg: HumanConfig) -> Dict[str, Any]:
    p = registry_dir(cfg) / SCHEMA_FILE
    if not p.is_file():
        raise ConfigRefusal("the registry schema %s is missing" % p)
    return _yaml(p)


def _type_ok(value: Any, spec: Mapping[str, Any]) -> bool:
    t = spec.get("type")
    if value is None:
        return bool(spec.get("nullable"))
    if t == "str":
        return isinstance(value, str)
    if t == "int":
        return isinstance(value, int) and not isinstance(value, bool)
    if t == "bool":
        return isinstance(value, bool)
    if t == "list":
        return isinstance(value, list)
    if t == "map":
        return isinstance(value, dict)
    if t == "str_or_map":
        return isinstance(value, (str, dict))
    if t == "any":
        return True
    raise ConfigRefusal("the registry schema names an unknown type %r" % t)


def validate_against(obj: Mapping[str, Any], fields: Mapping[str, Any], what: str) -> None:
    """Every required field present, every field of the right type and enum, no unknown field."""
    if not isinstance(obj, Mapping):
        raise ConfigRefusal("%s is not a mapping" % what)
    unknown = sorted(set(obj) - set(fields))
    if unknown:
        raise ConfigRefusal("%s holds fields the schema does not know: %s" % (what, unknown))
    for name, spec in fields.items():
        if name not in obj:
            if spec.get("required"):
                raise ConfigRefusal("%s lacks the required field %r" % (what, name))
            continue
        v = obj[name]
        if not _type_ok(v, spec):
            raise ConfigRefusal("%s field %r must be %s, got %r" % (what, name, spec.get("type"), v))
        enum = spec.get("enum")
        if enum is not None and v is not None:
            vals = v if isinstance(v, list) else [v]
            bad = [x for x in vals if x not in enum]
            if bad:
                raise ConfigRefusal("%s field %r holds %s outside %s" % (what, name, bad, enum))


def load_registry(cfg: HumanConfig, package: str) -> Dict[str, Any]:
    """registry/<package>.yaml, validated against registry/_schema.yaml and the 1.7 rules (no run facts here; the
    lead and link checks against the run are in board.check_registry_against_run)."""
    p = registry_dir(cfg) / ("%s.yaml" % package)
    if not p.is_file():
        raise ConfigRefusal("no rival registry for this package: %s" % p,
                            fix="the adapter builder writes registry/<package>.yaml (SPEC_HUMAN.txt 1.7)")
    reg = _yaml(p)
    schema = load_schema(cfg)
    validate_against(reg, schema["package_fields"], str(p))
    if str(reg["package"]) != str(package):
        raise ConfigRefusal("%s names package %r, not %r" % (p, reg["package"], package))
    seen = set()
    for i, r in enumerate(reg["rivals"]):
        what = "%s rival #%d (%s)" % (p.name, i, r.get("id") if isinstance(r, Mapping) else "?")
        validate_against(r, schema["rival_fields"], what)
        if r["id"] in seen:
            raise ConfigRefusal("%s names rival %r twice" % (p, r["id"]))
        seen.add(r["id"])
        check_rival(r, what)
    for jc in reg.get("joint_claims") or []:
        validate_against(jc, schema["joint_claim_fields"], "%s joint claim" % p.name)
        for rid in jc["rivals"]:
            if rid not in seen:
                raise ConfigRefusal("%s joint claim %r names unknown rival %r" % (p, jc["name"], rid))
    for r in reg["rivals"]:
        if r.get("placebo_of") and r["placebo_of"] not in seen:
            raise ConfigRefusal("%s rival %r is a placebo of unknown rival %r" % (p, r["id"], r["placebo_of"]))
    reg["_file"] = str(p)
    return reg


def lead_tiers(rival: Mapping[str, Any]) -> Dict[int, Dict[str, Any]]:
    """{lead: {"tier": P|L|A|X|none, "reason": str, "label": str}} from the registry's `leads` mapping (a lead's
    value is a tier word, or a mapping with tier / reason / label)."""
    out = {}
    for k, v in (rival.get("leads") or {}).items():
        lead = int(k)
        if isinstance(v, str):
            rec = {"tier": v, "reason": "", "label": ""}
        elif isinstance(v, Mapping):
            rec = {"tier": str(v.get("tier")), "reason": str(v.get("reason") or ""), "label": str(v.get("label") or "")}
        else:
            raise ConfigRefusal("rival %s lead %s: %r is not a tier or a mapping" % (rival.get("id"), k, v))
        if rec["tier"] not in TIERS + (TIER_NONE,):
            raise ConfigRefusal("rival %s lead %d: tier %r is not one of %s" % (rival.get("id"), lead, rec["tier"],
                                                                              TIERS + (TIER_NONE,)))
        if rec["tier"] == TIER_NONE and not rec["reason"]:
            raise ConfigRefusal("rival %s lead %d is 'none' without a reason (spec 1.7: horizon gap)"
                                % (rival.get("id"), lead))
        rec["decides"] = rec["tier"] in DECIDING_TIERS
        out[lead] = rec
    return out


def check_rival(r: Mapping[str, Any], what: str) -> None:
    """The 1.7 / 1.6 rules a registry entry must keep, independent of the run."""
    kind = r["kind"]
    stats = list(r.get("stats") or [])
    if len(stats) > MAX_STATS:
        raise ConfigRefusal("%s lists %d stats; at most %d (PROT H1)" % (what, len(stats), MAX_STATS))
    if any(not str(s).startswith(X_PREFIX) for s in stats):
        raise ConfigRefusal("%s: every stat is an index column named %s<stat>, got %s" % (what, X_PREFIX, stats))
    fams = list(r.get("families") or [])
    if r.get("runner"):
        if kind != "M":
            raise ConfigRefusal("%s: only an M rival has a runner" % what)
        if fams or stats or r.get("adapter"):
            raise ConfigRefusal("%s: an M rival with a runner has no families, stats or adapter (the method is the fit, "
                                "F0 only; PROT H7)" % what)
    else:
        if not r.get("adapter"):
            raise ConfigRefusal("%s has neither an adapter nor a runner" % what)
        if not stats:
            raise ConfigRefusal("%s: an index-table rival needs at least one stat" % what)
        if not fams and not r.get("placebo_of"):
            raise ConfigRefusal("%s lists no family" % what)
        for f in fams:
            if f not in FAMILY_KINDS:
                raise ConfigRefusal("%s: unknown family %r" % (what, f))
            if kind not in FAMILY_KINDS[f]:
                raise ConfigRefusal("%s: family %s does not serve kind %s (spec 1.6: %s serves %s)"
                                    % (what, f, kind, f, FAMILY_KINDS[f]))
        if fams != sorted(fams, key=FAMILY_ORDER.index):
            raise ConfigRefusal("%s: families must be listed in the fixed order F0..F6, got %s" % (what, fams))
    tiers = lead_tiers(r)
    if not tiers:
        raise ConfigRefusal("%s names no lead" % what)
    for L in r.get("score_without_net") or []:
        if int(L) not in tiers or tiers[int(L)]["tier"] == TIER_NONE:
            raise ConfigRefusal("%s: score_without_net lead %s has no row" % (what, L))
    pick = r.get("pick") or PICK_NOWCAST
    if pick == PICK_NOWCAST and tiers.get(0, {}).get("tier", TIER_NONE) == TIER_NONE and not r.get("placebo_of"):
        raise ConfigRefusal("%s is picked at the nowcast but has no lead-0 row; a forecast-only product is picked on "
                            "its lowest covered lead (pick: %s)" % (what, PICK_LOWEST_LEAD))


def load_products(cfg: HumanConfig) -> Dict[str, Any]:
    """The product registry (1.8): {product id: {path, files | patterns, manifest, licence, source, ...}}."""
    p = cfg.path("on_disk_products")
    if not p.is_file():
        raise ConfigRefusal("the product registry %s is missing" % p)
    reg = _yaml(p)
    schema = load_schema(cfg)
    if not isinstance(reg, Mapping) or not isinstance(reg.get("products"), Mapping):
        raise ConfigRefusal("%s holds no 'products' mapping" % p)
    out = {}
    for pid, rec in reg["products"].items():
        validate_against(rec, schema["product_fields"], "%s product %r" % (p.name, pid))
        out[pid] = _expand_roots(cfg, dict(rec), "%s product %r" % (p.name, pid))
    return out


def _expand_roots(cfg: HumanConfig, rec: Dict[str, Any], what: str) -> Dict[str, Any]:
    """A product `path` / `manifest` may start from a config root written as {<key>} (e.g. {index_root}/...), so a
    product the tool itself writes (a prep output) sits under the build roots with the build config and under the
    production roots with the production config. Any other brace refuses (fail loud)."""
    for field in ("path", "manifest"):
        v = rec.get(field)
        if not isinstance(v, str) or "{" not in v:
            continue
        for k in ROOT_KEYS + PATH_EXTRA_KEYS:
            v = v.replace("{%s}" % k, str(cfg.data[k]).replace("\\", "/").rstrip("/"))
        if "{" in v or "}" in v:
            raise ConfigRefusal("%s: %s %r names an unknown root (known: %s)"
                                % (what, field, rec[field], ", ".join(ROOT_KEYS + PATH_EXTRA_KEYS)))
        rec[field] = v
    return rec


def code_files() -> List[Path]:
    """The files of the human tool's code hash: rivals_human/*.py, then adapters/*.py (tests excluded)."""
    files = sorted(PACKAGE_DIR.glob("*.py"))
    if ADAPTERS_DIR.is_dir():
        files += sorted(ADAPTERS_DIR.glob("*.py"))
    return files


def relpath_text(path: Any) -> str:
    return str(path).replace(os.sep, "/")
