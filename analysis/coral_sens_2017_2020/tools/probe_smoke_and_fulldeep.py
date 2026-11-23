"""VALIDATION ONLY (no model fit): two read-only probes of a sensitivity package through the LIVE engine's own code.

    py -3.9 -I -B probe_smoke_and_fulldeep.py <package folder> <run root for the smoke plan>

1. SMOKE PLAN: TablePipeline(kind=smoke).plan() -- the smoke's own load, group pick (R21), table read and derive
   steps, then (if they pass) its plan folder; plan() never fits a tree and never opens a test label. It shows
   whether the declared `smoke` step can pass its derive on the R21 smoke groups.
2. FULL-SIZE DEEP CHECK: check.deep.run_deep(groups=<every kept group>) -- the deep data checks on all groups, the
   "side record" ruling M2 allows (never the freeze gate). Results are printed; no report file is written.
sys.dont_write_bytecode is set first; the launcher's thread pins run before any numeric import.
"""
import sys
import traceback

sys.dont_write_bytecode = True
ENGINE = r"C:\Users\moh the ghost\Desktop\data set for reserch paper\engine"
sys.path.insert(0, ENGINE)

from treeroute import launch  # noqa: E402

launch.pin_threads()

from treeroute.package.load import load_package  # noqa: E402
from treeroute.pipeline.record import KIND_SMOKE  # noqa: E402
from treeroute.pipeline.table_run import TablePipeline  # noqa: E402
from treeroute.runs.machine import load_machine  # noqa: E402

pkg, root = sys.argv[1], sys.argv[2]
print("== 1. smoke plan (no fit) on %s" % pkg, flush=True)
try:
    folder = TablePipeline(pkg, root, KIND_SMOKE, load_machine(), print, launch.record()).plan()
    print("SMOKE PLAN: passed derive; plan folder %s" % folder)
except Exception as exc:  # the refusal is the finding
    print("SMOKE PLAN REFUSED: %s: %s" % (type(exc).__name__, exc))
    traceback.print_exc(limit=2)

print("== 2. full-size deep check (all kept groups; side record, ruling M2; no report written)", flush=True)
from treeroute import split as SP  # noqa: E402
from treeroute.check.deep import run_deep  # noqa: E402
from treeroute.package.table import table_groups, table_spec  # noqa: E402

p = load_package(pkg)
groups = SP.groups_under_loro(SP.loro_split_sets(p.split), table_groups(p, table_spec(p)))
ctx = run_deep(pkg, echo=print, groups=list(groups))
bad = 0
for label, res in ctx.results:
    st = res.status.value
    bad += st == "block"
    print("%-22s %-6s %s" % (label, st, str(getattr(res, "message", ""))[:300]))
print("FULL-SIZE DEEP CHECK: %s (%d groups; %d refusals)" % ("GREEN" if not bad else "REFUSED", len(groups), bad))
