"""Full-size deep check of a table package: the engine's own deep data checks on EVERY kept group (read only).

    py -3.9 -I -B full_deep_check.py <package folder>

Ruling M2 makes the R21 four-group deep check the gate and allows a full-size deep check as a side record only.
For the 2017-2020 sensitivity package the R21 four-group check refuses by construction (T-MARK: none of the four
R21 groups has a 2020 visit, so a derive on them gives 2016-2019), so this side record is the data check that can
run (owner item, Part 627). Prints every guard line; writes no file. Exit 0 when no guard refuses.
"""
import sys

sys.dont_write_bytecode = True
ENGINE = r"C:\Users\moh the ghost\Desktop\data set for reserch paper\engine"
sys.path.insert(0, ENGINE)

from treeroute import launch  # noqa: E402

launch.pin_threads()

from treeroute import split as SP  # noqa: E402
from treeroute.check.deep import run_deep  # noqa: E402
from treeroute.package.load import load_package  # noqa: E402
from treeroute.package.table import table_groups, table_spec  # noqa: E402

pkg = sys.argv[1]
p = load_package(pkg)
groups = SP.groups_under_loro(SP.loro_split_sets(p.split), table_groups(p, table_spec(p)))
ctx = run_deep(pkg, echo=print, groups=list(groups))
bad = 0
for label, res in ctx.results:
    st = res.status.value
    bad += st == "block"
    print("%-22s %-6s %s" % (label, st, str(getattr(res, "message", ""))[:300]))
print("FULL-SIZE DEEP CHECK (side record, ruling M2): %s (%d groups; %d refusals)"
      % ("GREEN" if not bad else "REFUSED", len(groups), bad))
sys.exit(1 if bad else 0)
