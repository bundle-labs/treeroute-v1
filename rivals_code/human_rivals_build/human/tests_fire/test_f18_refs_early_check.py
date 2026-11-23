"""T-F18 realdata: the EARLY refs byte check (SPEC_HUMAN_PARTB.txt 1.4, 3.9; owner command F3; ATTENTION B4).

After `prep --run $FIRE --rival geff_era5` and `manifest --product fire_refs_label_store`, BEFORE any init: with the
production config (read-only), H.Run(RUN) and registry/fire.yaml, held = (unit, time, y) of the lead-0 slim refit set
(slim.open_slim(cfg, run, 0).read_set("refit", extras=False): training labels only; a test file, not an adapter, so
R02 does not apply), refs.store_labels(cfg, run, registry["refs_label_store"], held) must not refuse (every
overlapping 2018 label byte-equal) and must return rows at time 24228 only, one per scored unit with a finite
Dec-2018 label in the store. The counts are printed for Part B section 1. The test skips itself, with the reason,
while the fire slim or that product manifest is missing.

Run (owner command F3, alone):
    $env:HUMAN_REAL = '1'
    py -3.9 -B -m pytest tests_fire/test_f18_refs_early_check.py -q -s -p no:cacheprovider --basetemp <FRESH>
    Remove-Item Env:HUMAN_REAL
"""

import numpy as np
import pandas as pd
import pytest

from tests_fire import fixtures_fire as FF

DEC_2018 = 24228


@pytest.mark.realdata
def test_f18_refs_label_store_matches_the_held_labels():
    import pyarrow.parquet as pq
    from rivals_human import config as C
    from rivals_human import index as IX
    from rivals_human import refs as R
    from rivals_human import slim as S
    from rivals_human.common import load
    cfg = C.load_config(str(FF.PRODUCTION_CONFIG))
    LY, H = load(cfg)
    run = H.Run(str(FF.RUN_DIR))
    sm = C.slim_lead_dir(cfg, run.package, run.name, 0) / C.SLIM_MANIFEST
    if not sm.is_file():
        pytest.skip("the fire slim of lead 0 is missing (%s): owner command F1 first" % sm)
    products = C.load_products(cfg)
    mp = IX.product_manifest_path(cfg, products, FF.STORE_PID)
    if not mp.is_file():
        pytest.skip("the product manifest of %s is missing (%s): prep --rival geff_era5, then manifest --product %s "
                    "(owner command F3)" % (FF.STORE_PID, mp, FF.STORE_PID))
    registry = C.load_registry(cfg, "fire")
    store = registry["refs_label_store"]
    assert int(run.cuts[0]["fit_cut"]) == DEC_2018
    sl = S.open_slim(cfg, run, 0)
    st = sl.read_set("refit", extras=False)
    held = pd.DataFrame({"unit": st.keys["unit"].astype(str).to_numpy(),
                         "time": st.keys["time"].to_numpy(np.int64), "y": np.asarray(st.y, np.float64)})
    assert int(held["time"].max()) == DEC_2018 - FF.OFFSET
    add = R.store_labels(cfg, run, store, held)                         # refuses on any differing overlapping label
    assert len(add) > 0
    assert (add["time"].to_numpy(np.int64) == DEC_2018).all()
    assert not add["unit"].duplicated().any()
    units = sl.units()
    scored = units.loc[units["is_scored"].astype(bool), ["unit", "group"]].astype(str)
    assert set(add["unit"]) <= set(scored["unit"])
    # one row per scored unit with a finite Dec-2018 label in the store (training year 2018 only)
    root = IX.product_root(cfg, products, FF.STORE_PID)
    finite_dec = set()
    for g in sorted(set(scored["group"])):
        t = pq.read_table(str(root / str(store["file_pattern"]).format(group=g, year=2018)),
                          columns=[store["unit_column"], store["month_column"], store["label_column"]]).to_pandas()
        t = t[(t[store["month_column"]] == 12) & t[store["unit_column"]].astype(str).isin(set(scored["unit"]))]
        finite_dec |= set(t.loc[np.isfinite(t[store["label_column"]].to_numpy(np.float64)),
                                store["unit_column"]].astype(str))
    assert set(add["unit"]) == finite_dec
    print("T-F18: held refit labels %d (to step %d); store rows added at %d: %d of %d scored units (finite Dec-2018 "
          "labels); every overlapping 2018 label byte-equal" % (len(held), int(held["time"].max()), DEC_2018,
                                                                 len(add), len(scored)))
