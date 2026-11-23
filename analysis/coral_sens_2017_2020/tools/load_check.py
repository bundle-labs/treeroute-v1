"""Load a coral package through the LIVE engine's own loader and print what the run will see (read only).

    py -3.9 -I -B load_check.py <package folder> [<package folder> ...]

Prints: name, version, input, fingerprint, DRAFT status (the not-headline mark), the store template and whether its
lead files exist, the split (excluded groups, seen_during_design count), and the engine's table leads. Writes nothing.
"""
import os
import sys

sys.dont_write_bytecode = True
ENGINE = r"C:\Users\moh the ghost\Desktop\data set for reserch paper\engine"
sys.path.insert(0, ENGINE)

from treeroute.package.load import load_package  # noqa: E402
from treeroute.package.table import lead_template, table_leads  # noqa: E402
from treeroute.pipeline.draft import draft_status  # noqa: E402

for path in sys.argv[1:]:
    p = load_package(path)
    d = draft_status(p)
    tmpl = lead_template(p)
    leads = tuple(table_leads())
    print("== %s" % path)
    print("name %s | version %s | input %s | fingerprint %s" % (p.dataset.name, p.dataset.version, p.dataset.input,
                                                                p.fingerprint))
    print("draft: is_draft=%s stamp=%r where=%s -> not-headline reason 'DRAFT package: %s'"
          % (d.is_draft, d.stamp, list(d.where), d.stamp))
    print("store template %s" % tmpl)
    for L in leads:
        f = tmpl.replace("{lead}", str(L))
        print("  lead %d: %s exists=%s" % (L, f, os.path.isfile(f)))
    print("split: excluded %d %s | seen_during_design %d" % (len(p.split.excluded), sorted(p.split.excluded),
                                                            len(p.split.seen_during_design)))
