"""treeroute_report.table._stratum_md_rows: the edges label (FIX_REPORT.md, grid-identity review item 2).

Finite edges print as before (the grid bytes); absent or all-NaN edges print "per value" (a string stratum of the
table option, alone or joined with a numeric stratum); some edges missing is refused (R34).
"""
import math

import pandas as pd
import pytest

from treeroute.report import metrics as M
from treeroute_report import table as RT


def _frame(edges):
    row = {"line": M.LINE_KEY, "rows_basis": M.ROWS_BASIS_ALL, "package": "p", "stratum_column": "s",
           "stratum": "a", "adopted": "arm__x", "reference": "base__y", "column": "arm__x", "n": 3, "mae": 1.0,
           "anom_r2": 0.1, "corr2": 0.2, "hit": 0.3, "detection": 0.4}
    row.update(edges)
    return pd.DataFrame([row])


def test_finite_edges_print_exactly():
    out = RT._stratum_md_rows(_frame({"edge_q25": 0.25, "edge_q50": 0.5, "edge_q75": 0.75}))
    assert out[0]["edges"] == "0.25 / 0.5 / 0.75"


@pytest.mark.parametrize("edges", [{}, {"edge_q25": math.nan, "edge_q50": math.nan, "edge_q75": math.nan}])
def test_absent_or_nan_edges_print_per_value(edges):
    assert RT._stratum_md_rows(_frame(edges))[0]["edges"] == "per value"


def test_some_edges_missing_is_refused():
    with pytest.raises(RT.TableRefusal, match="R34"):
        RT._stratum_md_rows(_frame({"edge_q25": 0.25, "edge_q50": math.nan, "edge_q75": 0.75}))
