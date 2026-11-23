"""Parquet readers for store files (plan 4.2: boilerplate).

  - read_columns(path, columns): the named columns of one file, exactly as pyarrow reads them;
  - iter_columns(listing, columns, keys=None): the same, one file at a time, read only when the
    caller asks for the next one;
  - read_footer(path) / iter_footers(listing, keys=None): footer facts only (row counts, null
    counts, min/max per column). A footer read never touches a data page.

Values come back exactly as stored, as a pyarrow Table with the file's own types. Nothing here masks
a sentinel, joins, lags, fills, casts, converts to pandas or concatenates files: each of those is
science and waits for its signature (treeroute/_proposed/io_science.py). The only conversions are the
ones pyarrow's parquet reader makes by default: the logical types stored in the file (for example a
string or a timestamp) and the Arrow schema the writer saved in the footer.

Two pyarrow behaviours this module guards against, because they would fail silently:
  - ParquetFile.read(columns=[...]) drops a requested column that the file does not have, and reads
    a column named twice only once. read_columns refuses both before reading.
  - A float NaN is a value, not a null: a footer's null_count counts nulls only, and pyarrow's writer
    leaves NaN out of min/max. (pandas writes NaN as null, so for a file written from pandas the
    null_count does include the NaN.)

A file written by pandas with an index other than a plain range holds the index as a column (for
example '__index_level_0__'). The footer lists it like any column, and read_columns returns it only
when it is asked for by name. Whether such a column counts as one of the store's columns is not
decided here (owner question; it matters for the closed-world column check).

The Arrow reader runs on the calling thread (use_threads=False), so a read starts no thread pool the
launcher does not pin (G-THREADS). The values do not depend on it.
"""

import math
import os
from collections import Counter
from collections.abc import Mapping, Set
from dataclasses import dataclass
from typing import Any, Iterable, Iterator, List, Optional, Sequence, Tuple

import pyarrow as pa
import pyarrow.parquet as pq

from treeroute.errors import TreerouteError
from treeroute.io.listing import Key, ListingError, StoreListing, check_key

_USE_THREADS = False


class ReadError(TreerouteError):
    """A store file could not be read as asked. The message names the file."""


@dataclass(frozen=True)
class ColumnFooter:
    """Footer facts of one column, combined over the file's row groups.

    A row group "has no value" for the column when its footer says every value slot is null
    (recorded null_count equal to the chunk's num_values, which counts nulls too) or the chunk holds
    no value slot at all (num_values 0). Such a row group has no range to record, and pyarrow's
    writer records none, so it counts as covered with nothing to add.

    ``null_count`` is the sum over row groups, None unless every row group records it (a chunk with
    num_values 0 counts as recording 0). ``min`` and ``max`` combine the row groups that record them;
    they are None unless every other row group has no value, and None when no row group records
    them. A NaN in any row group's min or max makes the combined value NaN.
    """
    name: str                        # the column's path in the parquet schema (its name, for a flat table)
    physical_type: str
    logical_type: str                # 'NONE' when the column has no logical type
    arrow_type: Optional[str]        # the Arrow type pyarrow reads, for a top-level column
    null_count: Optional[int]
    min: Any
    max: Any
    row_groups_with_null_count: int  # row groups whose footer records a null count
    row_groups_with_min_max: int     # row groups whose footer records min and max
    row_groups_without_values: int   # row groups with no non-null value (see above)


@dataclass(frozen=True)
class FileFooter:
    """Footer facts of one parquet file."""
    path: str
    num_rows: int
    row_group_rows: Tuple[int, ...]
    created_by: Optional[str]
    columns: Tuple[ColumnFooter, ...]

    @property
    def names(self) -> Tuple[str, ...]:
        return tuple(c.name for c in self.columns)

    def column(self, name: str) -> ColumnFooter:
        for col in self.columns:
            if col.name == name:
                return col
        raise ReadError("%s has no column %r in its footer" % (self.path, name))


def _column_request(columns: Sequence[str]) -> Tuple[str, ...]:
    if isinstance(columns, (str, bytes)):
        raise ReadError("columns is a list of column names, not one string (got %r)" % (columns,))
    try:
        names = tuple(columns)
    except TypeError:
        raise ReadError("columns is a list of column names, got %r" % (columns,)) from None
    if not names:
        raise ReadError("name at least one column to read")
    bad = [c for c in names if not isinstance(c, str) or not c]
    if bad:
        raise ReadError("column names are non-empty strings, got %r" % (bad,))
    twice = sorted(c for c, n in Counter(names).items() if n > 1)
    if twice:
        raise ReadError("columns named more than once: %s" % ", ".join(twice))
    return names


def _path_text(path: Any) -> str:
    try:
        return os.fspath(path)
    except TypeError:
        raise ReadError("a file path is a string or path object, got %r" % (path,)) from None


def read_columns(path: Any, columns: Sequence[str]) -> pa.Table:
    """The named columns of one parquet file, in the order asked, exactly as pyarrow reads them.

    Every requested name must be a top-level column that appears exactly once in the file's schema;
    otherwise ReadError names the file and the columns (pyarrow itself would drop a missing column
    silently). A file pyarrow cannot open or decode raises ReadError naming the file.
    """
    names = _column_request(columns)
    where = _path_text(path)
    try:
        with pq.ParquetFile(where) as pf:
            in_file = Counter(pf.schema_arrow.names)
            missing = [c for c in names if c not in in_file]
            if missing:
                raise ReadError("%s has no column %s (it has %d columns)"
                                % (where, ", ".join(repr(c) for c in missing),
                                   sum(in_file.values())))
            doubled = [c for c in names if in_file[c] > 1]
            if doubled:
                raise ReadError("%s holds the column %s more than once; it cannot be read by name"
                                % (where, ", ".join(repr(c) for c in doubled)))
            table = pf.read(columns=list(names), use_threads=_USE_THREADS, use_pandas_metadata=False)
    except (pa.ArrowException, OSError) as exc:
        raise ReadError("%s could not be read: %s: %s" % (where, type(exc).__name__, exc)) from exc
    table = table.select(list(names))
    if table.column_names != list(names):
        raise ReadError("internal: %s gave columns %s for the request %s"
                        % (where, table.column_names, list(names)))
    return table


def _combine(values: List[Any], pick: Any) -> Any:
    for v in values:
        if isinstance(v, float) and math.isnan(v):
            return float("nan")
    return pick(values)


def read_footer(path: Any) -> FileFooter:
    """Row counts, null counts and min/max per column from the file's footer. No data page is read.

    Statistics are combined over row groups (see ColumnFooter). A file pyarrow cannot open raises
    ReadError naming the file.
    """
    where = _path_text(path)
    try:
        with pq.ParquetFile(where) as pf:
            md = pf.metadata
            arrow_types = {f.name: str(f.type) for f in pf.schema_arrow}
            rg_rows = tuple(md.row_group(i).num_rows for i in range(md.num_row_groups))
            columns = []
            for j in range(md.num_columns):
                col = md.schema.column(j)
                nulls: List[int] = []        # one per row group whose null count is known
                recorded_nulls = 0
                mins: List[Any] = []
                maxs: List[Any] = []
                without_values = 0           # row groups with no non-null value, no min/max
                for i in range(md.num_row_groups):
                    chunk = md.row_group(i).column(j)
                    slots = chunk.num_values  # value slots, nulls included
                    stats = chunk.statistics if chunk.is_stats_set else None
                    null_count: Optional[int] = None
                    if stats is not None and stats.has_null_count:
                        null_count = stats.null_count
                        recorded_nulls += 1
                    elif slots == 0:
                        null_count = 0
                    if null_count is not None:
                        nulls.append(null_count)
                    if stats is not None and stats.has_min_max:
                        mins.append(stats.min)
                        maxs.append(stats.max)
                    elif slots == 0 or (null_count is not None and null_count == slots):
                        without_values += 1
                every = md.num_row_groups
                ranged = bool(mins) and len(mins) + without_values == every
                columns.append(ColumnFooter(
                    name=col.path,
                    physical_type=col.physical_type,
                    logical_type=col.logical_type.type,
                    arrow_type=arrow_types.get(col.path),
                    null_count=sum(nulls) if len(nulls) == every else None,
                    min=_combine(mins, min) if ranged else None,
                    max=_combine(maxs, max) if ranged else None,
                    row_groups_with_null_count=recorded_nulls,
                    row_groups_with_min_max=len(mins),
                    row_groups_without_values=without_values))
            footer = FileFooter(path=where, num_rows=md.num_rows, row_group_rows=rg_rows,
                                created_by=md.created_by, columns=tuple(columns))
    except (pa.ArrowException, OSError) as exc:
        raise ReadError("%s: the footer could not be read: %s: %s"
                        % (where, type(exc).__name__, exc)) from exc
    if sum(rg_rows) != footer.num_rows:
        raise ReadError("%s: the row groups hold %d rows but the footer says %d"
                        % (where, sum(rg_rows), footer.num_rows))
    return footer


def _chosen(listing: StoreListing, keys: Optional[Iterable[Key]]) -> List[Tuple[Key, str]]:
    """(key, path) pairs to read, checked before any file is opened.

    ``keys`` is an ordered collection of key tuples: a list, a tuple of tuples (such as
    ExpectedVsFound.expected_found) or any other iterable with a fixed order. Refused: one key on
    its own (a tuple whose items are not tuples), a set or a mapping (their order can change from
    one run to the next), and, for a listing without placeholders, the empty tuple (it could mean
    no keys or the one empty key; pass [] or [()]). Each key is checked with check_key, so numpy
    integers find their file; the pairs hold the keys as the listing holds them.
    """
    if not isinstance(listing, StoreListing):
        raise ReadError("listing must be a StoreListing (from treeroute.io.listing.list_store)")
    if keys is None:
        return list(listing.files)
    if isinstance(keys, (str, bytes)):
        raise ReadError("keys is a collection of key tuples, not a string (got %r)" % (keys,))
    if isinstance(keys, (Set, Mapping)):
        raise ReadError("keys must have a fixed order (a list or a tuple of key tuples), not a %s; "
                        "for example pass sorted(keys)" % type(keys).__name__)
    if isinstance(keys, tuple):
        if not keys and not listing.key_names:
            raise ReadError("keys=() is ambiguous for a listing without placeholders (no keys, or "
                            "the one empty key); pass [] or [()]")
        if keys and not any(isinstance(k, tuple) for k in keys):
            raise ReadError("keys is a collection of key tuples; %r is one key, pass [%r]"
                            % (keys, keys))
    try:
        wanted = list(keys)
    except TypeError:
        raise ReadError("keys is a collection of key tuples, got %r" % (keys,)) from None
    try:
        checked = [check_key(k, listing.key_names) for k in wanted]
    except ListingError as exc:
        raise ReadError("keys for the listing of %s: %s" % (listing.path_template, exc)) from exc
    twice = sorted(k for k, n in Counter(checked).items() if n > 1)
    if twice:
        raise ReadError("keys named more than once: %s%s"
                        % (twice[:5], " ..." if len(twice) > 5 else ""))
    have = listing.found()
    absent = [k for k in checked if k not in have]
    if absent:
        raise ReadError("%d of the %d keys asked for have no file in the listing of %s: %s%s"
                        % (len(absent), len(checked), listing.path_template, absent[:10],
                           " ..." if len(absent) > 10 else ""))
    return [listing.file_of(k) for k in checked]


def iter_columns(listing: StoreListing, columns: Sequence[str],
                 keys: Optional[Iterable[Key]] = None) -> Iterator[Tuple[Key, pa.Table]]:
    """(key, table) for each file of a listing, reading one file per step, only when asked.

    ``keys`` (tuples in the listing's key order, in a list or a tuple) picks files and their order;
    by default every found file, in key order. The columns and keys are checked when this is called,
    before any file is opened (see _chosen for what ``keys`` may be). Each table is what
    read_columns gives for that file; nothing is concatenated.
    """
    names = _column_request(columns)
    todo = _chosen(listing, keys)

    def steps() -> Iterator[Tuple[Key, pa.Table]]:
        for key, path in todo:
            yield key, read_columns(path, names)

    return steps()


def iter_footers(listing: StoreListing,
                 keys: Optional[Iterable[Key]] = None) -> Iterator[Tuple[Key, FileFooter]]:
    """(key, footer) for each file of a listing, one footer per step, only when asked.

    ``keys`` works as in iter_columns, so ExpectedVsFound.expected_found can be passed as it is.
    """
    todo = _chosen(listing, keys)

    def steps() -> Iterator[Tuple[Key, FileFooter]]:
        for key, path in todo:
            yield key, read_footer(path)

    return steps()
