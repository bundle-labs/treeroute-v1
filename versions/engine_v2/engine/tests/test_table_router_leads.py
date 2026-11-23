"""NeighbourPass refuses a context, feature pool or lead table at another lead than the pass (R11).

FIX_REPORT.md (leakage review item 2): the issue days come from the lead table and the features from the context's
pool; features of one lead must never meet the issue days of another. The check runs first in _prepare, so plain
stand-ins are enough here; the toy end-to-end test (test_table_mode_pipeline.py) runs the real objects.
"""
from types import SimpleNamespace

import numpy as np
import pytest

from treeroute.pipeline.table_router import NeighbourPass, NeighbourPassRefusal, PassPart


def _pass(ctx_lead, pool_lead, table_lead, lead=183):
    state = SimpleNamespace(p=SimpleNamespace(table=SimpleNamespace()))
    ctx = SimpleNamespace(lead=ctx_lead, features=SimpleNamespace(lead=pool_lead))
    part = PassPart(name="all", score_index=np.arange(1), c=None, model=None, fallback_donor=None)
    return NeighbourPass(state, "probe", ctx, None, ("g",), lead, SimpleNamespace(lead=table_lead),
                         np.arange(1), [part], {})


@pytest.mark.parametrize("ctx_lead, pool_lead, table_lead, what", [
    (0, 183, 183, "context"), (183, 0, 183, "feature pool"), (183, 183, 0, "lead table")])
def test_a_part_at_another_lead_is_refused(ctx_lead, pool_lead, table_lead, what):
    with pytest.raises(NeighbourPassRefusal, match="R11.*%s is at lead" % what):
        _pass(ctx_lead, pool_lead, table_lead)
