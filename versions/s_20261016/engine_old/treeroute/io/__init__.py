"""treeroute.io: store listing, parquet readers and the io science bodies (plan 4.2).

Boilerplate: listing.py parses and expands store path templates, lists the files that exist and
reports the expected keys against the found keys as data; readers.py reads named columns from those
parquet files exactly as pyarrow reads them, one file at a time, and reads footer statistics without
touching a data page. Science (bodies for the owner-approved signatures of
treeroute/_proposed/io_science.py): steps.py (the integer step index, step bounds, the keys-only
dense grid and its predecessor lookup), sentinel.py (sentinel masking at read), joins.py (1:1 joins,
the coarser-column join and its target-step periods), apply.py (applying computed lags, verdicts and
freezes, the own-history block with its leak-free fallback, features at the issue step), checks.py
(the column-set and missing-file checks) and aggregate.py (time aggregation with computed facts).
lastvalue.py holds the last-value rule (owner ruling J2 d, engine constant C18): a tree feature's short
gaps inside its record take the same unit's most recent earlier value, counted per column, after the
lags and verdicts and before R30.
Not built yet: the event functions event_history_block and asof_driver_join (milestone M8; they
raise NotImplementedError), aggregate_space and recompute_declared_operation.

Importing this package loads nothing. listing.py uses the standard library only. readers.py and the
science modules load numpy (and pyarrow or pandas), so they must be imported after the launcher has
pinned the thread pools.
"""
