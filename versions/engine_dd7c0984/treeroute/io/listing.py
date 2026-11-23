"""Store path templates and file listing (plan 4.2: boilerplate).

A store path template names one file per key, with key-role placeholders in folder or file names:

    data/target/group={group}/year={year}/part-0.parquet
    <store folder>/{group}_{year}.parquet
    <store folder>/{group}.parquet

What this module does:
  - parse_template: parse a template, raising TemplateError when it is malformed;
  - expand: fill a template's placeholders for one key;
  - list_store: list the files that exist and read each file's key back from its path. Entries
    below the store root that do not fit the template are reported (``not_read``), never dropped;
  - compare_expected: expected keys against found keys, as data;
  - check_key: check one key and give it plain Python types (numpy integers become int).

expand, check_key, compare_expected and StoreListing.path_of accept exactly the same values: a
non-empty string that stays inside its path segment for {group} and {unit}, and a non-negative
integer (int or numpy integer, never bool, float or string) for the integer placeholders.

What it does NOT do (science, awaiting owner signatures; plan 4.2): decide whether a missing file
stops a run, apply a store's absent_groups fact, map a file that holds several periods to those
periods, or read any file's content.

Placeholders are the key roles of plan 1.3: {group} and {unit} (text), and the calendar parts a
key_time column can hold, {year}, {month} and {day_of_year} (integers). An integer placeholder may
carry the format spec ``d`` or a zero-padded width ``0Nd`` (for example {month:02d}). A key is a
tuple of placeholder values in the fixed order group, unit, year, month, day_of_year, restricted to
the placeholders the template uses; for a {group} + {year} template that is the (group, period) pair.

Matching is exact and case-sensitive on every platform below the store root (the folder that holds
the first placeholder segment). A file whose name differs from the template only in letter case is
reported in ``not_read`` and its key is not found, even on a case-insensitive file system, so a
listing never depends on the platform. An integer is read back only if formatting it again gives the
same text, so '007' is not the key 7 under the spec ``d``.
"""

import operator
import os
import re
import string
from dataclasses import dataclass
from typing import Any, Dict, FrozenSet, Iterable, List, Mapping, Optional, Tuple, Union

from treeroute.errors import TreerouteError

# Placeholder name -> kind. The order is the order of the fields in a key.
PLACEHOLDERS: Tuple[Tuple[str, str], ...] = (
    ("group", "text"),
    ("unit", "text"),
    ("year", "int"),
    ("month", "int"),
    ("day_of_year", "int"),
)
_KIND = dict(PLACEHOLDERS)
_ORDER = {name: i for i, (name, _) in enumerate(PLACEHOLDERS)}
_INT_SPEC = re.compile(r"^(?:d|0[1-9]d)?$")
_DIGITS = re.compile(r"^[0-9]+$")

Key = Tuple[Any, ...]
PathLike = Union[str, "os.PathLike[str]"]

# NotRead kinds
NO_MATCH = "no_match"        # the name fits no reading of its template segment
WRONG_KIND = "wrong_kind"    # a folder where the template needs a file, or a file where it needs a folder
AMBIGUOUS = "ambiguous"      # the name fits its segment in more than one way


class ListingError(TreerouteError):
    """A listing request cannot be answered as asked (for example a key the listing does not hold)."""


class TemplateError(ListingError):
    """A store path template is malformed, or cannot be filled as asked."""


@dataclass(frozen=True)
class _Field:
    name: str
    kind: str
    spec: str


@dataclass(frozen=True)
class _Segment:
    """One path segment: fixed text and placeholder fields, never two fields side by side."""
    tokens: Tuple[Union[str, _Field], ...]

    @property
    def literal(self) -> Optional[str]:
        """The segment's text when it holds no placeholder, else None."""
        if any(isinstance(t, _Field) for t in self.tokens):
            return None
        return "".join(t for t in self.tokens if isinstance(t, str))

    @property
    def shown(self) -> str:
        """The segment as written in a template (for messages)."""
        return "".join(t if isinstance(t, str) else
                       "{%s%s}" % (t.name, ":" + t.spec if t.spec else "") for t in self.tokens)


@dataclass(frozen=True)
class PathTemplate:
    """A parsed store path template. Build it with parse_template."""
    text: str
    key_names: Tuple[str, ...]
    segments: Tuple[_Segment, ...]
    absolute: bool

    def expand(self, values: Mapping[str, Any], base: Optional[PathLike] = None) -> str:
        """The path of one key. ``values`` maps every placeholder of the template to its value."""
        return expand(self, values, base)


@dataclass(frozen=True)
class NotRead:
    """An entry below the store root that the listing could not read a key from."""
    path: str
    kind: str
    detail: str


@dataclass(frozen=True)
class StoreListing:
    """The files of one store that exist, keyed by the values read back from their paths.

    ``files`` is sorted by key. ``not_read`` (sorted by path) holds every entry below the store root
    that does not fit the template; nothing is dropped silently. The listing refuses nothing: whether
    a missing file or an unreadable entry stops a run is a science decision (check_missing_files,
    awaiting its signature).
    """
    template: str
    path_template: str
    store_root: str
    store_root_exists: bool
    key_names: Tuple[str, ...]
    files: Tuple[Tuple[Key, str], ...]
    not_read: Tuple[NotRead, ...]

    def __post_init__(self) -> None:
        # One key -> position lookup, built once (not a dataclass field: equality, repr and
        # as_dict see only the listing's data).
        index: Dict[Key, int] = {}
        for i, (key, path) in enumerate(self.files):
            if key in index:
                raise ListingError("the listing of %s holds the key %r twice (%s and %s)"
                                   % (self.path_template, key, self.files[index[key]][1], path))
            index[key] = i
        object.__setattr__(self, "_index", index)
        object.__setattr__(self, "_found", frozenset(index))

    def found(self) -> FrozenSet[Key]:
        """The keys whose file exists."""
        return self._found  # type: ignore[attr-defined]

    def file_of(self, key: Key) -> Tuple[Key, str]:
        """(key, path) of a found key, the key as the listing holds it (plain Python types).

        ``key`` is checked with check_key first, so a numpy integer finds its file and a bool or a
        float does not (a bare dict lookup would match True to 1 and 1.0 to 1).
        """
        key = check_key(key, self.key_names)
        index: Dict[Key, int] = self._index  # type: ignore[attr-defined]
        if key not in index:
            raise ListingError("key %r has no file in the listing of %s" % (key, self.path_template))
        return self.files[index[key]]

    def path_of(self, key: Key) -> str:
        """The path of a found key (see file_of)."""
        return self.file_of(key)[1]

    def as_dict(self) -> Dict[str, Any]:
        """Plain types (lists, strings, numbers), for a report or a JSON file."""
        return {
            "template": self.template,
            "path_template": self.path_template,
            "store_root": self.store_root,
            "store_root_exists": self.store_root_exists,
            "key_names": list(self.key_names),
            "files": [[list(key), path] for key, path in self.files],
            "not_read": [{"path": e.path, "kind": e.kind, "detail": e.detail} for e in self.not_read],
        }


@dataclass(frozen=True)
class ExpectedVsFound:
    """Expected keys against found keys, as data. Each tuple is sorted."""
    key_names: Tuple[str, ...]
    expected_found: Tuple[Key, ...]
    missing: Tuple[Key, ...]       # expected, no file
    unexpected: Tuple[Key, ...]    # a file, not expected

    def as_dict(self) -> Dict[str, Any]:
        """Plain types, for a report or a JSON file."""
        return {
            "key_names": list(self.key_names),
            "expected_found": [list(k) for k in self.expected_found],
            "missing": [list(k) for k in self.missing],
            "unexpected": [list(k) for k in self.unexpected],
        }


# ---------------------------------------------------------------------------------------------------
# parsing
def _parse_segment(text: str, template: str) -> _Segment:
    try:
        parts = list(string.Formatter().parse(text))
    except ValueError as exc:
        raise TemplateError("template %r is malformed (unbalanced brace in %r): %s"
                            % (template, text, exc)) from None
    tokens: List[Union[str, _Field]] = []
    for literal, field_name, spec, conversion in parts:
        if literal:
            tokens.append(literal)
        if field_name is None:
            continue
        if field_name not in _KIND:
            raise TemplateError(
                "template %r uses the placeholder {%s}; the placeholders are %s"
                % (template, field_name, ", ".join("{%s}" % n for n, _ in PLACEHOLDERS)))
        if conversion is not None:
            raise TemplateError("template %r: {%s!%s} takes no conversion"
                                % (template, field_name, conversion))
        kind = _KIND[field_name]
        spec = spec or ""
        if kind == "text" and spec:
            raise TemplateError("template %r: the text placeholder {%s} takes no format spec (got %r)"
                                % (template, field_name, spec))
        if kind == "int" and not _INT_SPEC.match(spec):
            raise TemplateError(
                "template %r: the integer placeholder {%s} takes the spec 'd' or '0Nd' "
                "(zero-padded width N from 1 to 9), got %r" % (template, field_name, spec))
        if tokens and isinstance(tokens[-1], _Field):
            raise TemplateError(
                "template %r: {%s} and {%s} touch in %r; put fixed text between two placeholders so a "
                "file name can be read back" % (template, tokens[-1].name, field_name, text))
        tokens.append(_Field(field_name, kind, spec))
    return _Segment(tuple(tokens))


def parse_template(template: Union[str, PathTemplate]) -> PathTemplate:
    """Parse a store path template. Raises TemplateError if it is malformed.

    Separators may be '/' or '\\'. Braces are escaped by doubling them. Refused: an unbalanced
    brace, an unknown or positional placeholder, a conversion, a format spec on a text placeholder,
    an integer spec other than 'd' or '0Nd', two placeholders with no fixed text between them, an
    empty segment inside the path (a doubled separator), a template that ends with a separator
    (a template names files), and a '.' or '..' segment after the first placeholder segment (below
    the store root, where a folder listing never shows one, so list_store could not find a path that
    expand builds). A '.' or '..' above the store root is kept as written: both functions put it in
    the same prefix and the operating system resolves it the same way for both.
    """
    if isinstance(template, PathTemplate):
        return template
    if not isinstance(template, str):
        raise TemplateError("a template is a string, got %s" % type(template).__name__)
    if not template.strip():
        raise TemplateError("the template is empty")
    normal = template.replace("\\", "/")
    raw = normal.split("/")
    lead = 0
    while lead < len(raw) - 1 and raw[lead] == "":
        lead += 1  # leading separators: the root of an absolute path, or a share prefix
    if lead > 2:
        raise TemplateError("template %r starts with more than two separators" % template)
    body = raw[lead:]
    if body[-1] == "":
        raise TemplateError("template %r ends with a separator; a template names files, not a folder"
                            % template)
    if any(part == "" for part in body):
        raise TemplateError("template %r has an empty path segment (a doubled separator)" % template)
    segments = tuple([_Segment(("",))] * lead + [_parse_segment(part, template) for part in body])
    first = next((i for i, s in enumerate(segments) if s.literal is None), None)
    if first is not None:
        dots = [s.literal for s in segments[first + 1:] if s.literal in (".", "..")]
        if dots:
            raise TemplateError(
                "template %r has a %r segment below its store root (after the first placeholder); a "
                "folder listing never shows one, so list_store could not find what expand builds. "
                "Write the path without it" % (template, dots[0]))
    names = {t.name for seg in segments for t in seg.tokens if isinstance(t, _Field)}
    key_names = tuple(sorted(names, key=_ORDER.__getitem__))
    return PathTemplate(text=template, key_names=key_names, segments=segments,
                        absolute=os.path.isabs(normal))


# ---------------------------------------------------------------------------------------------------
# expanding
def _check_value(name: str, value: Any, where: str, error: type = TemplateError) -> Any:
    """One placeholder value, checked and given a plain Python type (str or int); raises ``error``.

    The one rule for every function that takes key values (expand, check_key and its callers).
    """
    if _KIND[name] == "text":
        if not isinstance(value, str) or not value:  # numpy str_ is a str
            raise error("%s: {%s} needs a non-empty string, got %r" % (where, name, value))
        if "/" in value or "\\" in value or value in (".", ".."):
            raise error("%s: {%s} = %r would leave its path segment" % (where, name, value))
        return str(value)
    # bool, and numpy bool (dtype kind 'b'), which operator.index still accepts with a warning
    if isinstance(value, bool) or getattr(getattr(value, "dtype", None), "kind", None) == "b":
        raise error("%s: {%s} needs an integer, got %r" % (where, name, value))
    try:
        number = operator.index(value)  # int and numpy integers; never float or str
    except TypeError:
        raise error("%s: {%s} needs an integer, got %r" % (where, name, value)) from None
    if number < 0:
        raise error("%s: {%s} needs a non-negative integer, got %r" % (where, name, value))
    return int(number)


def _format_field(field: _Field, value: Any) -> str:
    return value if field.kind == "text" else format(value, field.spec or "d")


def _prefix(tpl: PathTemplate, base: Optional[PathLike]) -> str:
    """'' for an absolute template; the absolute base folder plus '/' for a relative one."""
    if tpl.absolute:
        return ""
    if base is None:
        raise TemplateError("template %r is relative: give the folder it is relative to (the package "
                            "folder) as base" % tpl.text)
    return os.path.abspath(os.fspath(base)).replace("\\", "/").rstrip("/") + "/"


def _folder(text: str) -> str:
    """A folder path usable on its own: a drive ('X:') or an empty root gets its separator."""
    if text == "" or text.endswith(":"):
        return text + "/"
    return text


def expand(template: Union[str, PathTemplate], values: Mapping[str, Any],
           base: Optional[PathLike] = None) -> str:
    """Fill every placeholder of ``template`` from ``values`` and return the path (forward slashes).

    A relative template is joined to ``base``; an absolute template ignores ``base``. Every
    placeholder the template uses must be given, and nothing else. The path is checked to read back
    to exactly these values under list_store's rules, so a file created at this path is listed under
    the same key. The check is on the text: where the file system itself rewrites a name, the two
    can still differ on disk (on Windows, a name that differs only in letter case opens the same
    file, and a trailing dot or space is dropped from a name).
    """
    tpl = parse_template(template)
    if not isinstance(values, Mapping):
        raise TemplateError("values must be a mapping of placeholder name to value")
    given, wanted = set(values), set(tpl.key_names)
    if given != wanted:
        raise TemplateError("template %r needs values for %s; missing %s, not in the template %s"
                            % (tpl.text, sorted(wanted), sorted(wanted - given), sorted(given - wanted)))
    checked = {name: _check_value(name, values[name], "template %r" % tpl.text) for name in wanted}
    parts = []
    assigned: Dict[str, Any] = {}
    for seg in tpl.segments:
        part = "".join(t if isinstance(t, str) else _format_field(t, checked[t.name])
                       for t in seg.tokens)
        if seg.literal is None:
            readings = _readings(seg, part, assigned)
            want = {n: checked[n] for n in set(assigned) | {t.name for t in seg.tokens
                                                              if isinstance(t, _Field)}}
            if readings != [want]:
                raise TemplateError(
                    "template %r: the values %s give the name %r, which does not read back to them "
                    "alone (a value holds the template's fixed text)" % (tpl.text, checked, part))
            assigned = want
        parts.append(part)
    return _prefix(tpl, base) + "/".join(parts)


# ---------------------------------------------------------------------------------------------------
# reading a name back
def _value_from_text(field: _Field, text: str) -> Any:
    """The value a placeholder holds in ``text``, or None if the text cannot be that placeholder."""
    if field.kind == "text":
        return text if text not in (".", "..") else None
    if not _DIGITS.match(text):
        return None
    value = int(text)
    return value if format(value, field.spec or "d") == text else None


def _readings(segment: _Segment, name: str, assigned: Mapping[str, Any],
              limit: int = 2) -> List[Dict[str, Any]]:
    """The ways ``name`` fits ``segment`` given the values already read (at most ``limit``). Each
    reading is the full assignment: the earlier values plus this segment's."""
    tokens = segment.tokens
    out: List[Dict[str, Any]] = []
    acc: Dict[str, Any] = dict(assigned)

    def walk(i: int, pos: int) -> None:
        if len(out) >= limit:
            return
        if i == len(tokens):
            if pos == len(name):
                out.append(dict(acc))
            return
        tok = tokens[i]
        if isinstance(tok, str):
            if name.startswith(tok, pos):
                walk(i + 1, pos + len(tok))
            return
        follower = tokens[i + 1] if i + 1 < len(tokens) else None  # fixed text, or the end
        ends: List[int] = []
        if follower is None:
            ends.append(len(name))
        else:
            k = name.find(str(follower), pos + 1)
            while k >= 0:
                ends.append(k)
                k = name.find(str(follower), k + 1)
        for end in ends:
            if end <= pos:
                continue
            value = _value_from_text(tok, name[pos:end])
            if value is None:
                continue
            if tok.name in acc:  # the placeholder appeared earlier: the values must agree
                if acc[tok.name] == value:
                    walk(i + 1, end)
            else:
                acc[tok.name] = value
                walk(i + 1, end)
                del acc[tok.name]

    walk(0, 0)
    return out


def _describe(reading: Mapping[str, Any], names: Iterable[str]) -> str:
    return ", ".join("%s=%r" % (n, reading[n]) for n in names if n in reading)


# ---------------------------------------------------------------------------------------------------
# listing
def list_store(template: Union[str, PathTemplate], base: Optional[PathLike] = None) -> StoreListing:
    """List the files of a store and read each file's key back from its path.

    A relative template is joined to ``base`` (the package folder); an absolute template ignores it.
    The store root is the folder that holds the first placeholder segment. Nothing above it is
    listed. Below it, every entry of every folder the template passes through is accounted for:
    it gives a key, or it lies on the way to one, or it is reported in ``not_read``.

    A template without placeholders names one file: its key is the empty tuple, found when the file
    exists. If that path is a folder, nothing is found and the folder is reported in ``not_read`` as
    WRONG_KIND, as it would be below a placeholder.

    Raises TemplateError for a malformed template, and lets a file-system error (for example a
    folder that cannot be read) propagate. Refuses nothing else: what is on disk is reported, never
    refused.
    """
    tpl = parse_template(template)
    prefix = _prefix(tpl, base)
    segs = tpl.segments
    texts = [s.shown for s in segs]
    path_template = prefix + tpl.text.replace("\\", "/")
    first = next((i for i, s in enumerate(segs) if s.literal is None), None)

    if first is None:  # one file
        path = prefix + "/".join(texts)
        root = _folder(path.rsplit("/", 1)[0]) if "/" in path else "."
        single_not_read: Tuple[NotRead, ...] = ()
        if os.path.isdir(path):
            single_not_read = (NotRead(path, WRONG_KIND, "the template needs a file here"),)
        files = (((), path),) if os.path.isfile(path) else ()
        return StoreListing(template=tpl.text, path_template=path_template, store_root=root,
                            store_root_exists=os.path.isdir(root), key_names=(), files=files,
                            not_read=single_not_read)

    root = _folder(prefix + "/".join(texts[:first])) if first else _folder(prefix.rstrip("/"))
    found: Dict[Key, str] = {}
    not_read: List[NotRead] = []
    root_exists = os.path.isdir(root)
    if not root_exists and os.path.exists(root):
        not_read.append(NotRead(root, WRONG_KIND, "the store root is a file, not a folder"))

    def visit(folder: str, i: int, assigned: Dict[str, Any]) -> None:
        seg = segs[i]
        last = i == len(segs) - 1
        with os.scandir(folder) as it:
            entries = sorted(it, key=lambda e: e.name)
        for entry in entries:
            path = folder.rstrip("/") + "/" + entry.name
            if seg.literal is not None:
                if entry.name != seg.literal:
                    not_read.append(NotRead(path, NO_MATCH, "the template expects only %r here"
                                            % seg.literal))
                    continue
                readings = [dict(assigned)]
            else:
                readings = _readings(seg, entry.name, assigned)
                if not readings:
                    not_read.append(NotRead(path, NO_MATCH, "does not fit %r" % texts[i]))
                    continue
            if entry.is_dir() == last:
                not_read.append(NotRead(path, WRONG_KIND, "the template needs a %s here"
                                        % ("file" if last else "folder")))
                continue
            if len(readings) > 1:
                not_read.append(NotRead(path, AMBIGUOUS, "fits %r in more than one way: %s"
                                        % (texts[i], " | ".join(_describe(r, tpl.key_names)
                                                                for r in readings))))
                continue
            if last:
                key = tuple(readings[0][n] for n in tpl.key_names)
                if key in found:  # cannot happen: a key formats to exactly one path
                    raise ListingError("internal: key %r read from both %s and %s"
                                       % (key, found[key], path))
                found[key] = path
            else:
                visit(path, i + 1, readings[0])

    if root_exists:
        visit(root, first, {})
    return StoreListing(template=tpl.text, path_template=path_template, store_root=root,
                        store_root_exists=root_exists, key_names=tpl.key_names,
                        files=tuple(sorted(found.items())),
                        not_read=tuple(sorted(not_read, key=lambda e: e.path)))


def check_key(key: Any, key_names: Tuple[str, ...]) -> Key:
    """One key, checked against ``key_names`` and returned with plain Python types.

    A key is a tuple with one value per name, in that order. Each value follows expand's rule, so a
    numpy integer (for example from a pandas column) becomes int and a numpy string becomes str,
    while a bool, a float or a numeric string is refused. Raises ListingError.
    """
    if not isinstance(key, tuple) or len(key) != len(key_names):
        raise ListingError("a key is a tuple of %d values in the order %s, got %r"
                           % (len(key_names), key_names, key))
    return tuple(_check_value(name, value, "key %r" % (key,), ListingError)
                 for name, value in zip(key_names, key))


def compare_expected(listing: StoreListing, expected: Iterable[Key]) -> ExpectedVsFound:
    """Expected keys against the listing's found keys, as data (no refusal).

    Each expected key is a tuple in the listing's ``key_names`` order, for example (group, year),
    checked with check_key (numpy integers are accepted and become int). Duplicates count once.
    Raises ListingError only for a key of the wrong shape or type.
    """
    if not isinstance(listing, StoreListing):
        raise ListingError("listing must be a StoreListing (from list_store)")
    if isinstance(expected, (str, bytes)):
        raise ListingError("expected is a collection of key tuples, not a string")
    try:
        items = iter(expected)
    except TypeError:
        raise ListingError("expected is a collection of key tuples, got %r" % (expected,)) from None
    wanted = {check_key(k, listing.key_names) for k in items}
    have = listing.found()
    return ExpectedVsFound(key_names=listing.key_names,
                           expected_found=tuple(sorted(wanted & have)),
                           missing=tuple(sorted(wanted - have)),
                           unexpected=tuple(sorted(have - wanted)))
