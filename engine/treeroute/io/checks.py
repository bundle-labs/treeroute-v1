"""Column-set and missing-file checks (plan 1.2, 1.3 absent_groups; plan 5 G-JOIN, G-CLOSED,
G-MISSING files).

SCIENCE bodies for the owner-approved signatures check_column_set and check_missing_files
(treeroute/_proposed/io_science.py). The file listing that feeds check_missing_files is boilerplate
(treeroute/io/listing.py: StoreListing.found()).
"""

from collections import Counter
from dataclasses import dataclass
from typing import Any, Mapping, Set, Tuple

import numpy as np

from treeroute.errors import RefusedError

_SHOW = 20


@dataclass(frozen=True)
class MissingFileReport:
    """Expected (group, period) pairs against the files found.

    ``missing``: every expected pair with no file (sorted). ``absent_by_fact``: the missing pairs
    whose group the store declares absent (they get NaN, counted by R30). ``unexpected``: files found
    that no expected pair asks for (report only)."""
    store: str
    missing: Tuple[Tuple[str, int], ...]
    absent_by_fact: Tuple[Tuple[str, int], ...]
    unexpected: Tuple[Tuple[str, int], ...]


def _names(values: Any, what: str, table: str) -> Tuple[str, ...]:
    if isinstance(values, str):
        raise RefusedError("G-JOIN", "table %s: %s is a list of column names, not one string" % (table, what))
    names = tuple(values)
    bad = [c for c in names if not isinstance(c, str) or not c]
    if bad:
        raise RefusedError("G-JOIN", "table %s: %s holds names that are not non-empty strings: %r"
                           % (table, what, bad[:_SHOW]))
    twice = sorted(c for c, n in Counter(names).items() if n > 1)
    if twice:
        raise RefusedError("G-JOIN", "table %s: %s names these columns more than once: %s"
                           % (table, what, twice))
    return names


# Provenance: plan 5 G-JOIN ("the observed column set equals the catalog"), G-CLOSED; the assembler
# that reverted 49 columns while printing OK (Part 326).
def check_column_set(observed: Tuple[str, ...], catalog: Tuple[str, ...], table: str) -> None:
    """The observed column set of a table must equal its catalog's column set.

    Rule: G-JOIN, G-CLOSED. Compared as sets (order carries no meaning). The caller passes the
    table's full declared set (store catalog columns plus the package's key columns, which store
    catalogs leave out).
    Refuses: any difference, naming every missing and every extra column; a column named twice in
    either list (a set comparison would hide it).
    """
    if not isinstance(table, str) or not table:
        raise RefusedError("G-JOIN", "table must be a non-empty name, got %r" % (table,))
    seen = set(_names(observed, "the observed columns", table))
    declared = set(_names(catalog, "the catalog columns", table))
    missing = sorted(declared - seen)
    extra = sorted(seen - declared)
    if missing or extra:
        parts = []
        if missing:
            parts.append("%d catalog columns are absent from the files: %s" % (len(missing), missing))
        if extra:
            parts.append("%d columns in the files are not in the catalog: %s" % (len(extra), extra))
        raise RefusedError("G-JOIN", "table %s: the observed column set differs from its catalog: %s"
                           % (table, "; ".join(parts)),
                           fix="declare every stored column in the catalog and remove listed columns "
                               "the files do not hold")


def _pairs(values: Any, what: str, store: str) -> Set[Tuple[str, int]]:
    out = set()
    for pair in values:
        ok = isinstance(pair, tuple) and len(pair) == 2 and isinstance(pair[0], str) and pair[0]
        period = pair[1] if ok else None
        ok = ok and not isinstance(period, (bool, np.bool_)) and isinstance(period, (int, np.integer))
        if not ok:
            raise RefusedError("G-MISSING", "store %s: %s must be (group, integer period) pairs, got %r"
                               % (store, what, pair))
        out.add((pair[0], int(period)))
    return out


# Provenance: plan 1.2 (missing-file check), 1.3 absent_groups; pm25_architecture.py:170-176 skipped
# missing files silently (the defect this replaces).
def check_missing_files(expected: Set[Tuple[str, int]], found: Set[Tuple[str, int]],
                        absent_groups: Mapping[str, str], store: str) -> MissingFileReport:
    """Expected (group, period) pairs from the target against the files found in a store.

    Rule: G-MISSING (files). A missing file stops the run unless the store declares that group
    absent (absent_groups); declared-absent pairs are reported in ``missing`` and ``absent_by_fact``
    (they get NaN, counted by R30). Nothing missing is skipped silently. Files nobody asked for are
    reported in ``unexpected``, not refused.
    NOT caught (owner decision pending: refuse, flag or allow): a file that EXISTS for a group the
    store declares absent is allowed and appears in no field of the report, so a stale absent_groups
    fact is invisible here.
    Refuses: any missing pair whose group is not declared absent; pairs that are not
    (group, integer period); absent_groups that is not a {group: reason} mapping of strings.
    """
    if not isinstance(store, str) or not store:
        raise RefusedError("G-MISSING", "store must be a non-empty name, got %r" % (store,))
    want = _pairs(expected, "expected", store)
    have = _pairs(found, "found", store)
    if not isinstance(absent_groups, Mapping):
        raise RefusedError("G-MISSING", "store %s: absent_groups must be a {group: reason} mapping" % store)
    bad = [g for g, r in absent_groups.items() if not isinstance(g, str) or not isinstance(r, str) or not r]
    if bad:
        raise RefusedError("G-MISSING", "store %s: absent_groups needs a group name and a reason for "
                           "each entry; bad entries: %r" % (store, bad[:_SHOW]))
    missing = tuple(sorted(want - have))
    absent = tuple(p for p in missing if p[0] in absent_groups)
    stop = [p for p in missing if p[0] not in absent_groups]
    if stop:
        groups = sorted({g for g, _ in stop})
        raise RefusedError(
            "G-MISSING", "store %s: %d expected files are missing in %d groups the store does not "
            "declare absent, e.g. %s" % (store, len(stop), len(groups), stop[:_SHOW]),
            fix="restore the files, or declare the group in the store's absent_groups with a reason")
    return MissingFileReport(store=store, missing=missing, absent_by_fact=absent,
                             unexpected=tuple(sorted(have - want)))
