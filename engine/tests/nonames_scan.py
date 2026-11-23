"""G-NONAMES scanner (test helper; tests may name problems, the engine may not).

Engine code must contain no registered dataset name, no 4-digit year, no drive letter (as a path
prefix or a lone 'D:' string), no unit-named identifier and no month arithmetic with 12 ('% 12',
'* 12.0', '12 / x', divmod(x, 12), np.mod(x, 12), ...), in identifiers, string literals (docstrings,
help text, guard messages, manifest fields) or number literals. Comments are exempt: that is where
each constant's origin lives (plan 4.2).

Python files are scanned token by token (tokenize), so a comment never counts and a string always
does. Other text files under treeroute/ are scanned whole.
"""

import ast
import io
import re
import tokenize
from pathlib import Path

# The five acceptance problems and the regions, products and aliases that must never be hard-coded.
BASE_REGISTERED_NAMES = (
    "pm25", "pm2", "fire", "fires", "wildfire", "wildfires", "defo", "deforestation", "ndvi", "evi",
    "coral", "corals", "bleaching", "thar", "acag", "gfed", "modis", "hansen", "era5", "chirps",
    "worldpop", "mod13", "mcd43", "mod44b", "luh2",
)
PM25_PATTERN = re.compile(r"pm\s*2[._\s]?5", re.IGNORECASE)

# Physical-unit spellings that would mean a unit is hard-coded in an identifier or string.
UNIT_NAMES = ("ugm3", "ug_m3", "ugm-3", "mgkg", "degc", "kelvin", "celsius", "mmday")
UNIT_PATTERNS = (re.compile(r"u\s*g\s*/\s*m\s*(3|\^3|³)", re.IGNORECASE),
                 re.compile(r"[µμ]g", re.IGNORECASE))

YEAR_IN_TEXT = re.compile(r"(?<!\d)(19|20)\d{2}(?!\d)")
YEAR_NUMBER = re.compile(r"^(19|20)\d{2}(\.0*)?$")
DRIVE = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]")
LONE_DRIVE = re.compile(r"^\s*[A-Za-z]:\s*$")  # a string literal that is only 'D:'
MONTH_OPS = {"%", "*", "/", "//", "%=", "*=", "/=", "//="}
TWELVE = re.compile(r"^12(\.0*)?$")  # 12, 12., 12.0, 12.00
# calls that do month arithmetic when one argument is 12
MONTH_CALLS = {"divmod", "mod", "fmod", "remainder", "floor_divide", "true_divide", "divide",
               "multiply", "floordiv", "truediv", "mul"}
_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_WORD = re.compile(r"[A-Za-z0-9]+")
_DIGITS = re.compile(r"\d+")


def registered_names(datasets_dir=None):
    """Base names plus every dataset PACKAGE under datasets/: a folder holding a dataset.yaml adds
    its folder name and the name inside. Other folders (review sheets, tools, _stores) add none."""
    names = set(BASE_REGISTERED_NAMES)
    if datasets_dir is not None and Path(datasets_dir).is_dir():
        for ds in Path(datasets_dir).glob("*/dataset.yaml"):
            names.add(ds.parent.name.lower())
            for line in ds.read_text(encoding="utf-8").splitlines():
                if line.startswith("name:"):
                    names.add(line.split(":", 1)[1].strip().strip("'\"").lower())
    return names


def _identifier_parts(name):
    return [p.lower() for p in re.split(r"_+", _CAMEL.sub("_", name)) if p]


def _check_words(words, names, where, kind, out):
    for word in words:
        if word in names:
            out.append((where, "%s names %r" % (kind, word)))
        if word in UNIT_NAMES:
            out.append((where, "%s names the unit %r" % (kind, word)))


def scan_text(text, names, label):
    """Scan free text (a string literal or a non-Python file). Returns [(where, problem)]."""
    out = []
    lowered = text.lower()
    _check_words(_WORD.findall(lowered), names, label, "text", out)
    for rx in (PM25_PATTERN,) + UNIT_PATTERNS:
        if rx.search(text):
            out.append((label, "text matches %s" % rx.pattern))
    if YEAR_IN_TEXT.search(text):
        out.append((label, "text holds a 4-digit year %r" % YEAR_IN_TEXT.search(text).group(0)))
    if DRIVE.search(text):
        out.append((label, "text holds a drive letter %r" % DRIVE.search(text).group(0)))
    return out


def _literal_text(token_string):
    """The value of a plain string literal token, or None (f-strings and bytes are skipped)."""
    try:
        value = ast.literal_eval(token_string)
    except (ValueError, SyntaxError):
        return None
    return value if isinstance(value, str) else None


def _is_twelve(node):
    return (isinstance(node, ast.Constant) and not isinstance(node.value, bool)
            and isinstance(node.value, (int, float)) and node.value == 12)


def scan_month_calls(source, label="<source>"):
    """AST check: divmod(x, 12), np.mod(x, 12), math.fmod(x, 12.0) and the like."""
    out = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return out
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.id if isinstance(func, ast.Name) else (
            func.attr if isinstance(func, ast.Attribute) else None)
        if name in MONTH_CALLS and any(_is_twelve(arg) for arg in node.args):
            out.append(("%s:%d" % (label, node.lineno),
                        "month arithmetic with 12 (%s(..., 12))" % name))
    return out


def scan_python_source(source, names, label="<source>"):
    """Scan Python source token by token. Comments are exempt. Returns [(where, problem)]."""
    out = scan_month_calls(source, label)
    tokens = [t for t in tokenize.generate_tokens(io.StringIO(source).readline)
              if t.type not in (tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE, tokenize.INDENT,
                                tokenize.DEDENT, tokenize.ENDMARKER)]
    for i, tok in enumerate(tokens):
        where = "%s:%d" % (label, tok.start[0])
        if tok.type == tokenize.NAME:
            _check_words(_identifier_parts(tok.string), names, where, "identifier", out)
            for run in _DIGITS.findall(tok.string):
                if YEAR_NUMBER.match(run):
                    out.append((where, "identifier %r holds a 4-digit year" % tok.string))
        elif tok.type == tokenize.STRING:
            out.extend(scan_text(tok.string, names, where))
            value = _literal_text(tok.string)
            if value is not None and LONE_DRIVE.match(value):
                out.append((where, "string is a drive letter %r" % value.strip()))
        elif tok.type == tokenize.NUMBER:
            if YEAR_NUMBER.match(tok.string.replace("_", "")):
                out.append((where, "number literal %r looks like a year" % tok.string))
            if TWELVE.match(tok.string):
                before = tokens[i - 1].string if i > 0 else ""
                after = tokens[i + 1].string if i + 1 < len(tokens) else ""
                if before in MONTH_OPS or after in MONTH_OPS:
                    out.append((where, "month arithmetic with 12 ('%s %s' / '%s %s')"
                                % (before, tok.string, tok.string, after)))
    return out


def scan_tree(root, names, excluded_dirs=("_proposed", "__pycache__")):
    """Scan every file under ``root``. Returns [(where, problem)]."""
    root = Path(root)
    out = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if any(part in excluded_dirs for part in rel.parts):
            continue
        label = rel.as_posix()
        if path.suffix == ".py":
            out.extend(scan_python_source(path.read_text(encoding="utf-8"), names, label))
        elif path.suffix in (".pyc", ".pyd", ".so", ".dll"):
            continue
        else:
            out.extend(scan_text(path.read_text(encoding="utf-8"), names, label))
    return out
