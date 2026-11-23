"""treeroute.route.neighbour: the strict pool of the neighbour kind (owner ruling U4; SPEC_NEIGHBOUR.md 1, 2;
SPEC_TABLE_MODE.md 4.1).

1. Date rule: no pool row is dated on or after the row's issue day, at leads 0, 183 and 365 (issue day =
   target day minus the lead), and none after the pass's cut.
2. Never a test row: only candidates enter (the kernel carries no score label at all); a planted near
   score row with a huge label changes no pool and no prediction.
3. Never the row itself.
4. 150 by map distance, then 50 in Z: equals a brute-force reference over all candidates (haversine).
5. Ties: two candidates at one site, the earlier row position wins (map step and feature step).
6. Under 12 eligible rows: no pool (exactly 11 and 12).
7. Drop set = own block plus every pool group's block, sorted, whole blocks.
8. The G-FITCUT assert fires on a planted bad pool; a candidate after the cut is refused.
9. A ContextKeptRows and a RouterRows are accepted; neighbour_pool_loro equals neighbour_pools.
Plus Z (pool_feature_z) and the refusals.

The builder make_pass() is shared with tests/test_route_neighbour_fit.py.
"""

import numpy as np
import pytest

from treeroute import engine_constants as K
from treeroute import split as SP
from treeroute.fit import context as FC
from treeroute.pipeline.stages import ContextKeptRows
from treeroute.route import neighbour as N
from treeroute.route.kinds import RouteGuardError, RouteRefusal

GROUPS = ("g_a", "g_b", "g_c", "g_d", "g_e", "g_f", "g_g", "g_h")


def blocks_for(groups=GROUPS, pair=("g_a", "g_b")):
    """Single-group blocks, except ``pair`` (one block of two) when given."""
    members, seen = [], set()
    for g in sorted(groups):
        if g in seen:
            continue
        if pair and g == pair[0]:
            members.append(tuple(sorted(pair)))
            seen.update(pair)
        else:
            members.append((g,))
            seen.add(g)
    members.sort(key=lambda b: b[0])
    return SP.OverlapBlocks(block_of_group={g: i for i, b in enumerate(members) for g in b},
                            members=tuple(members), linked_pairs=(), link_rule="test")


def make_pass(n_per_group=40, m_per_group=6, lead=0, n_feat=4, n_ctx=2, groups=GROUPS, weights=False,
              fallback=0.1234, cut=3000):
    """A synthetic neighbour pass (no RNG; fixed arithmetic): clustered sites per group, candidates dated
    at or before ``cut``, score rows dated after it, issue day = target day minus ``lead``."""
    cg, cd, clat, clon, cu = [], [], [], [], []
    for j, g in enumerate(groups):
        for r in range(n_per_group):
            cg.append(g)
            cd.append(int((r * 97 + j * 31) % (cut + 1)))
            clat.append(-30.0 + 7.0 * j + 0.9 * np.sin(1.3 * r + j))
            clon.append(120.0 + 6.0 * j + 0.9 * np.cos(0.7 * r + 2 * j))
    n = len(cg)
    cd = np.asarray(cd, np.int64)
    ck = np.arange(n, dtype=np.int64) * 2           # row positions, strictly ascending
    cu = np.asarray(["r%d" % k for k in ck], dtype=object)
    sg, sd, slat, slon = [], [], [], []
    for j, g in enumerate(groups):
        for r in range(m_per_group):
            sg.append(g)
            sd.append(cut + lead + 1 + int((r * 53 + j * 17) % 400))
            slat.append(-30.0 + 7.0 * j + 0.8 * np.cos(2.1 * r + j))
            slon.append(120.0 + 6.0 * j + 0.8 * np.sin(1.7 * r + j))
    m = len(sg)
    sk = np.arange(m, dtype=np.int64) * 2 + 1
    su = np.asarray(["r%d" % k for k in sk], dtype=object)
    sd = np.asarray(sd, np.int64)
    craw = np.column_stack([np.sin(0.11 * np.arange(n) * (f + 1)) + 0.05 * f for f in range(n_feat)])
    sraw = np.column_stack([np.sin(0.13 * np.arange(m) * (f + 1) + 0.3) for f in range(n_feat)])
    cz, sz, _, _ = N.pool_feature_z(craw, sraw, cd, cut)
    cctx = sctx = None
    if n_ctx:
        cctx = np.column_stack([np.cos(0.07 * np.arange(n) * (c + 1)) for c in range(n_ctx)])
        sctx = np.column_stack([np.cos(0.09 * np.arange(m) * (c + 1) + 0.2) for c in range(n_ctx)])
    cy = 0.5 + 0.3 * np.sin(0.05 * np.arange(n)) + 0.1 * craw[:, 0]
    cw = (1.0 + 0.5 * np.cos(0.21 * np.arange(n)) ** 2) if weights else None
    return N.NeighbourRows(
        cut=cut, lead=lead, cand_keys=ck, cand_day=cd, cand_unit=cu, cand_group=np.asarray(cg, dtype=object),
        cand_lat=np.asarray(clat), cand_lon=np.asarray(clon), cand_z=cz, cand_ctx=cctx, cand_y_link=cy,
        cand_w=cw, score_keys=sk, score_unit=su, score_issue=sd - lead, score_group=np.asarray(sg, dtype=object),
        score_lat=np.asarray(slat), score_lon=np.asarray(slon), score_z=sz, score_ctx=sctx,
        score_rows=np.arange(m), fallback_link=np.full(m, fallback))


def kept_rows(rows):
    return ContextKeptRows(cut=int(rows.cut), cut_kind="fit", lead=int(rows.lead), unit_ids=rows.cand_unit,
                           times=rows.cand_day, row_positions=rows.cand_keys, y=rows.cand_y_link,
                           context=rows.cand_ctx if rows.cand_ctx is not None else np.zeros((rows.cand_keys.size, 0)))


def pool_one(rows, i, candidates=None, blocks=None):
    return N.neighbour_pool_loro(rows.score_unit[i], rows.score_group[i], rows.score_lat[i], rows.score_lon[i],
                                 rows.score_z[i], candidates if candidates is not None else kept_rows(rows),
                                 rows.cand_lat, rows.cand_lon, rows.cand_z, rows.cand_group,
                                 blocks if blocks is not None else blocks_for(),
                                 row_issue_day=int(rows.score_issue[i]))


def brute_pool(rows, i):
    """The pool by brute force: every eligible candidate, map angle then Z, ties by row position."""
    ok = np.flatnonzero((rows.cand_day < rows.score_issue[i]) & (rows.cand_unit != rows.score_unit[i]))
    if ok.size < 12:
        return None
    ang = N.haversine_angle(rows.score_lat[i], rows.score_lon[i], rows.cand_lat[ok], rows.cand_lon[ok])
    first = ok[np.lexsort((rows.cand_keys[ok], ang))][:150]
    dz = np.sqrt(((rows.cand_z[first] - rows.score_z[i]) ** 2).sum(1))
    rank = np.lexsort((np.arange(first.size), dz))       # ties keep the map order
    return first[rank][:50]


# ------------------------------------------------------------------------------ 1. date rule
@pytest.mark.parametrize("lead", [0, 183, 365])
def test_no_pool_row_on_or_after_the_issue_day_at_every_lead(lead):
    rows = make_pass(lead=lead, cut=3000 - lead)
    pools = N.neighbour_pools(rows, blocks_for())
    n_pool = 0
    for i, idx in enumerate(pools.index):
        assert rows.score_issue[i] == (rows.score_issue[i] + lead) - lead
        if idx is None:
            continue
        n_pool += 1
        assert int(rows.cand_day[idx].max()) < int(rows.score_issue[i])
        assert int(rows.cand_day[idx].max()) <= int(rows.cut)
    assert n_pool == len(pools.index)


def test_the_issue_day_filter_binds_on_rows_issued_after_the_cut():
    # every candidate is at or before the cut; a row issued early in the window sees fewer candidates
    rows = make_pass(lead=365, cut=3000)
    issue = int(rows.cut) + 1 - 1000          # pretend an issue day inside the candidates' dates
    with pytest.raises(RouteRefusal, match="issued before the pass's cut"):
        N.neighbour_pools(_with(rows, score_issue=np.full(rows.score_keys.size, issue)), blocks_for())
    # neighbour_pool_loro on its own applies the filter at any issue day
    sel, _ = N.neighbour_pool_loro(rows.score_unit[0], rows.score_group[0], rows.score_lat[0], rows.score_lon[0],
                                   rows.score_z[0], kept_rows(rows), rows.cand_lat, rows.cand_lon, rows.cand_z,
                                   rows.cand_group, blocks_for(), row_issue_day=issue)
    pos = np.searchsorted(rows.cand_keys, sel)
    assert int(rows.cand_day[pos].max()) < issue


def test_a_candidate_dated_on_the_issue_day_never_enters():
    rows = make_pass(lead=0)
    i = 0
    issue = int(rows.score_issue[i])
    # move every candidate of the row's own group to the issue day minus 0 (on it) or minus 1 (before it)
    on = _with(rows, cut=issue, cand_day=np.where(rows.cand_group == rows.score_group[i], issue, rows.cand_day))
    sel, _ = pool_one(on, i)
    pos = np.searchsorted(on.cand_keys, sel)
    assert not np.any(on.cand_day[pos] >= issue)
    before = _with(rows, cand_day=np.where(rows.cand_group == rows.score_group[i], issue - 1, rows.cand_day),
                   cut=issue - 1)
    sel_b, _ = pool_one(before, i)
    pos_b = np.searchsorted(before.cand_keys, sel_b)
    assert np.any(before.cand_group[pos_b] == rows.score_group[i])


# ------------------------------------------------------------------------------ 2. never a test row
def test_only_candidates_enter_and_no_score_label_exists():
    rows = make_pass()
    assert not any(f.startswith("score_y") for f in N.NeighbourRows.__dataclass_fields__)
    pools = N.neighbour_pools(rows, blocks_for())
    for idx in pools.index:
        assert idx is None or set(idx.tolist()) <= set(range(rows.cand_keys.size))


def test_a_planted_near_test_row_with_a_huge_label_changes_nothing():
    rows = make_pass()
    base = N.neighbour_pools(rows, blocks_for())
    # plant an extra SCORE row next to score row 0, same features (a test row is a score row, never a candidate)
    planted = _with(rows, score_keys=np.r_[rows.score_keys, 10 ** 6], score_unit=np.append(rows.score_unit, "planted").astype(object),
                    score_issue=np.r_[rows.score_issue, rows.score_issue[0]],
                    score_group=np.append(rows.score_group, rows.score_group[0]).astype(object),
                    score_lat=np.r_[rows.score_lat, rows.score_lat[0]], score_lon=np.r_[rows.score_lon, rows.score_lon[0]],
                    score_z=np.vstack([rows.score_z, rows.score_z[:1]]),
                    score_ctx=np.vstack([rows.score_ctx, rows.score_ctx[:1]]),
                    score_rows=np.arange(rows.score_keys.size + 1),
                    fallback_link=np.r_[rows.fallback_link, 1e9])
    again = N.neighbour_pools(planted, blocks_for())
    for a, b in zip(base.index, again.index):
        assert np.array_equal(a, b)


def test_a_candidate_after_the_cut_is_refused():
    rows = make_pass()
    late = _with(rows, cand_day=np.r_[rows.cand_day[:-1], int(rows.cut) + 1])
    with pytest.raises(RouteRefusal, match="after the pass's cut"):
        N.neighbour_pools(late, blocks_for())
    kr = kept_rows(rows)
    bad = ContextKeptRows(cut=kr.cut, cut_kind=kr.cut_kind, lead=kr.lead, unit_ids=kr.unit_ids,
                          times=np.r_[kr.times[:-1], kr.cut + 1], row_positions=kr.row_positions, y=kr.y,
                          context=kr.context)
    with pytest.raises(RouteRefusal, match="G-FITCUT"):
        pool_one(rows, 0, candidates=bad)


# ------------------------------------------------------------------------------ 3. never the row itself
def test_the_row_itself_never_enters_its_pool():
    rows = make_pass()
    i = 3
    # make candidate 0 the score row itself (same unit id), dated before its issue day, at its site and Z
    cu = rows.cand_unit.copy()
    cu[0] = rows.score_unit[i]
    clat, clon, cz = rows.cand_lat.copy(), rows.cand_lon.copy(), rows.cand_z.copy()
    clat[0], clon[0], cz[0] = rows.score_lat[i], rows.score_lon[i], rows.score_z[i]
    planted = _with(rows, cand_unit=cu, cand_lat=clat, cand_lon=clon, cand_z=cz)
    sel, _ = pool_one(planted, i)
    assert int(planted.cand_keys[0]) not in set(sel.tolist())
    other = _with(planted, cand_unit=rows.cand_unit)          # the same row under another id would enter first
    sel_o, _ = pool_one(other, i)
    assert int(sel_o[0]) == int(other.cand_keys[0])


# ------------------------------------------------------------------------------ 4. 150 then 50
@pytest.mark.parametrize("lead", [0, 365])
def test_pools_equal_a_brute_force_reference(lead):
    rows = make_pass(n_per_group=60, lead=lead, cut=3000 - lead)
    pools = N.neighbour_pools(rows, blocks_for())
    for i in range(rows.score_keys.size):
        want = brute_pool(rows, i)
        got = pools.index[i]
        assert (want is None) == (got is None)
        if want is not None:
            assert np.array_equal(got, want), i
            assert got.size == min(50, want.size)
            sel, _ = pool_one(rows, i)
            assert np.array_equal(sel, rows.cand_keys[want])


def test_the_map_step_keeps_150_and_the_feature_step_50():
    rows = make_pass(n_per_group=60)
    idx = N.neighbour_pools(rows, blocks_for()).index[0]
    assert idx.size == K.NEIGHBOUR_POOL_FEATURE == 50 and K.NEIGHBOUR_POOL_DISTANCE == 150


def test_haversine_angle_matches_the_legacy_formula_without_the_radius():
    lat1, lon1 = -18.5, 147.2
    lat2, lon2 = np.array([-18.5, -19.0, 10.0]), np.array([147.2, 148.0, -60.0])
    p = np.pi / 180.0
    a = np.sin((lat2 - lat1) * p / 2) ** 2 + np.cos(lat1 * p) * np.cos(lat2 * p) * np.sin((lon2 - lon1) * p / 2) ** 2
    km = 2 * 6371.0 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))
    ang = N.haversine_angle(lat1, lon1, lat2, lon2)
    assert ang[0] == 0.0
    assert np.allclose(ang * 6371.0, km, rtol=1e-14, atol=0)
    assert np.array_equal(np.argsort(ang, kind="stable"), np.argsort(km, kind="stable"))


# ------------------------------------------------------------------------------ 5. ties
def test_a_map_tie_goes_to_the_earlier_row_position(monkeypatch):
    rows = make_pass(n_per_group=20, groups=GROUPS[:2], m_per_group=1, n_ctx=0)
    i = 0
    ang = N.haversine_angle(rows.score_lat[i], rows.score_lon[i], rows.cand_lat, rows.cand_lon)
    order = np.argsort(ang, kind="stable")
    c1, c2 = int(order[4]), int(order[10])
    clat, clon = rows.cand_lat.copy(), rows.cand_lon.copy()
    clat[c2], clon[c2] = clat[c1], clon[c1]          # one site: the pair ties at ranks 4 and 5
    tied = _with(rows, cand_lat=clat, cand_lon=clon)
    monkeypatch.setattr(K, "NEIGHBOUR_POOL_DISTANCE", 5)
    idx = N.neighbour_pools(tied, blocks_for(GROUPS[:2])).index[i]
    early, late = min(c1, c2), max(c1, c2)
    assert idx.size == 5
    assert early in idx.tolist() and late not in idx.tolist()


def test_a_feature_tie_at_one_site_goes_to_the_earlier_row_position(monkeypatch):
    rows = make_pass(n_per_group=20, groups=GROUPS[:2], m_per_group=1, n_ctx=0)
    i = 0
    dz = np.sqrt(((rows.cand_z - rows.score_z[i]) ** 2).sum(1))
    order = np.argsort(dz, kind="stable")
    x, y = int(order[2]), int(order[9])
    early, late = min(x, y), max(x, y)
    clat, clon, cz = rows.cand_lat.copy(), rows.cand_lon.copy(), rows.cand_z.copy()
    clat[late], clon[late], cz[late] = clat[early], clon[early], cz[early]   # one site, one Z
    # the feature cut falls between them: keep only as many as rank below the pair plus one
    tied = _with(rows, cand_lat=clat, cand_lon=clon, cand_z=cz)
    dz2 = np.sqrt(((tied.cand_z - tied.score_z[i]) ** 2).sum(1))
    rank = int(np.count_nonzero(dz2 < dz2[early]))
    monkeypatch.setattr(K, "NEIGHBOUR_POOL_FEATURE", rank + 1)
    idx = N.neighbour_pools(tied, blocks_for(GROUPS[:2])).index[i]
    assert early in idx.tolist() and late not in idx.tolist()


# ------------------------------------------------------------------------------ 6. the minimum
@pytest.mark.parametrize("n_eligible,has_pool", [(11, False), (12, True), (13, True)])
def test_under_12_eligible_rows_there_is_no_pool(n_eligible, has_pool):
    rows = make_pass(n_per_group=10, groups=GROUPS[:2], m_per_group=1)
    issue = int(rows.score_issue[0])
    day = np.full(rows.cand_day.size, issue)        # on the issue day: not eligible
    day[:n_eligible] = 5
    sub = _with(rows, cand_day=day, cut=issue)
    sel, drop = pool_one(sub, 0, blocks=blocks_for(GROUPS[:2], pair=None))
    assert (sel is not None) == has_pool
    if has_pool:
        assert sel.size == n_eligible
    else:
        assert drop == (rows.score_group[0],)
    assert K.NEIGHBOUR_POOL_MIN_ROWS == 12


def test_no_candidate_at_all_gives_no_pool():
    rows = make_pass(groups=GROUPS[:2], m_per_group=1)
    empty = _with(rows, cand_keys=np.zeros(0, np.int64), cand_day=np.zeros(0, np.int64),
                  cand_unit=np.zeros(0, dtype=object), cand_group=np.zeros(0, dtype=object),
                  cand_lat=np.zeros(0), cand_lon=np.zeros(0), cand_z=np.zeros((0, rows.score_z.shape[1])),
                  cand_ctx=np.zeros((0, rows.score_ctx.shape[1])), cand_y_link=np.zeros(0))
    pools = N.neighbour_pools(empty, blocks_for(GROUPS[:2]))
    assert all(p is None for p in pools.index)


# ------------------------------------------------------------------------------ 7. drop set
def test_the_drop_set_is_the_own_block_plus_every_pool_block_whole_and_sorted():
    rows = make_pass()
    blocks = blocks_for()
    pools = N.neighbour_pools(rows, blocks)
    saw_pair = False
    for i, (idx, drop) in enumerate(zip(pools.index, pools.drop)):
        groups = set(rows.cand_group[idx].tolist()) | {rows.score_group[i]}
        want = set()
        for g in groups:
            want.update(SP.block_of_group(blocks, g))
        assert drop == tuple(sorted(want))
        assert ("g_a" in drop) == ("g_b" in drop)            # a block is never split
        saw_pair = saw_pair or "g_a" in drop
        sel, drop1 = pool_one(rows, i)
        assert drop1 == drop
    assert saw_pair


# ------------------------------------------------------------------------------ 8. the assert
def test_the_assert_fires_on_a_planted_future_or_self_pool_row(monkeypatch):
    rows = make_pass()
    late = int(np.argmax(rows.cand_day))
    i = 0
    planted_issue = int(rows.cand_day[late])
    monkeypatch.setattr(N, "_pool_of_row", lambda *a, **k: np.full(12, late))
    with pytest.raises(RouteGuardError, match="on or after the issue day"):
        N.neighbour_pool_loro(rows.score_unit[i], rows.score_group[i], rows.score_lat[i], rows.score_lon[i],
                              rows.score_z[i], kept_rows(rows), rows.cand_lat, rows.cand_lon, rows.cand_z,
                              rows.cand_group, blocks_for(), row_issue_day=planted_issue)
    monkeypatch.setattr(N, "_pool_of_row", lambda *a, **k: np.arange(12))
    cu = rows.cand_unit.copy()
    cu[3] = rows.score_unit[i]
    with pytest.raises(RouteGuardError, match="the row itself"):
        N.neighbour_pools(_with(rows, cand_unit=cu), blocks_for())


# ------------------------------------------------------------------------------ 9. candidate kinds
def test_a_router_rows_and_a_context_kept_rows_give_the_same_pool():
    rows = make_pass()
    with FC._issuing():
        rr = FC.RouterRows(cut=int(rows.cut), cut_kind=FC.CutKind.FIT, lead=0, unit_ids=rows.cand_unit,
                           times=rows.cand_day, row_positions=rows.cand_keys, y=rows.cand_y_link,
                           context=rows.cand_ctx.astype(np.float32))
    for i in range(0, rows.score_keys.size, 7):
        a = pool_one(rows, i, candidates=rr)
        b = pool_one(rows, i, candidates=kept_rows(rows))
        assert np.array_equal(a[0], b[0]) and a[1] == b[1]


def test_candidates_out_of_row_position_order_are_refused():
    rows = make_pass()
    kr = kept_rows(rows)
    shuffled = ContextKeptRows(cut=kr.cut, cut_kind=kr.cut_kind, lead=kr.lead, unit_ids=kr.unit_ids,
                               times=kr.times, row_positions=kr.row_positions[::-1].copy(), y=kr.y,
                               context=kr.context)
    with pytest.raises(RouteRefusal, match="strictly ascending"):
        pool_one(rows, 0, candidates=shuffled)
    with pytest.raises(RouteRefusal, match="strictly ascending"):
        N.neighbour_pools(_with(rows, cand_keys=rows.cand_keys[::-1].copy()), blocks_for())


def test_the_issue_day_is_required_and_must_be_an_integer():
    rows = make_pass()
    args = (rows.score_unit[0], rows.score_group[0], rows.score_lat[0], rows.score_lon[0], rows.score_z[0],
            kept_rows(rows), rows.cand_lat, rows.cand_lon, rows.cand_z, rows.cand_group, blocks_for())
    with pytest.raises(TypeError):
        N.neighbour_pool_loro(*args)
    with pytest.raises(RouteRefusal, match="U4"):
        N.neighbour_pool_loro(*args, row_issue_day=3.5)


def test_pool_records_list_pool_keys_drop_sets_and_fallbacks():
    rows = make_pass()
    sub = _with(rows, score_issue=np.r_[np.full(1, int(rows.cut)), rows.score_issue[1:]])
    pools = N.neighbour_pools(sub, blocks_for())
    rec = N.pool_records(sub, pools)
    assert rec["score_key"].tolist() == sub.score_keys.tolist()
    for i, idx in enumerate(pools.index):
        assert rec["pool_keys"][i].tolist() == ([] if idx is None else sub.cand_keys[idx].tolist())
        assert rec["drop_groups"][i] == list(pools.drop[i])
        assert rec["pool_fallback"][i] == (idx is None)


# ------------------------------------------------------------------------------ Z
def test_pool_feature_z_fills_missing_with_zero_and_uses_candidate_constants_only():
    craw = np.array([[1.0, np.nan], [3.0, 2.0], [5.0, 4.0]])
    sraw = np.array([[100.0, np.nan]])
    cz, sz, mean, sd = N.pool_feature_z(craw, sraw, np.array([1, 2, 3]), 3)
    filled = np.array([[1.0, 0.0], [3.0, 2.0], [5.0, 4.0]])
    assert np.allclose(mean, filled.mean(0)) and np.allclose(sd, filled.std(0) + 1e-9)
    assert np.allclose(cz, (filled - filled.mean(0)) / (filled.std(0) + 1e-9))
    assert np.allclose(sz, (np.array([[100.0, 0.0]]) - mean) / sd)
    with pytest.raises(RouteRefusal, match="after the cut"):
        N.pool_feature_z(craw, sraw, np.array([1, 2, 4]), 3)
    with pytest.raises(RouteRefusal, match="infinite"):
        N.pool_feature_z(np.array([[np.inf], [1.0]]), np.array([[0.0]]), np.array([1, 2]), 3)


def test_a_column_constant_on_the_candidates_is_zero_on_both_sides():
    craw = np.array([[1.0, 7.0], [3.0, 7.0], [5.0, 7.0]])
    sraw = np.array([[2.0, 9.0], [4.0, 7.0]])
    cz, sz, _, _ = N.pool_feature_z(craw, sraw, np.array([1, 2, 3]), 3)
    assert np.all(cz[:, 1] == 0.0) and np.all(sz[:, 1] == 0.0)
    assert np.allclose(sz[:, 0], (sraw[:, 0] - 3.0) / (craw[:, 0].std() + 1e-9))
    assert N.constant_z_columns(cz) == 1


def test_a_planted_constant_column_gives_the_pools_of_the_table_without_it():
    """FIX_REPORT.md correctness item 1: a tree column constant on every candidate, with other values on the score
    rows, must not turn the feature step into map order."""
    rows = make_pass()
    n, m = rows.cand_keys.size, rows.score_keys.size
    craw = np.column_stack([np.sin(0.11 * np.arange(n) * (f + 1)) + 0.05 * f for f in range(4)])
    sraw = np.column_stack([np.sin(0.13 * np.arange(m) * (f + 1) + 0.3) for f in range(4)])
    cz0, sz0, _, _ = N.pool_feature_z(craw, sraw, rows.cand_day, rows.cut)
    planted_c = np.column_stack([craw, np.zeros(n)])
    planted_s = np.column_stack([sraw, np.linspace(1.0, 5.0, m)])
    cz1, sz1, _, _ = N.pool_feature_z(planted_c, planted_s, rows.cand_day, rows.cut)
    p0 = N.neighbour_pools(_with(rows, cand_z=cz0, score_z=sz0), blocks_for())
    p1 = N.neighbour_pools(_with(rows, cand_z=cz1, score_z=sz1), blocks_for())
    for a, b in zip(p0.index, p1.index):
        assert (a is None and b is None) or np.array_equal(a, b)
    assert p0.drop == p1.drop


def test_a_handed_in_pool_is_asserted_again_by_the_kernel():
    """FIX_REPORT.md leakage item 1: the fingerprint covers the rows, not the index or the drop sets."""
    rows = make_pass(n_ctx=0)
    blocks = blocks_for()
    i, late = 0, int(np.argmax(rows.cand_day))
    cd = rows.cand_day.copy()
    cd[late] = int(rows.cut)                       # a candidate dated on row 0's issue day
    rows = _with(rows, cand_day=cd, score_issue=np.r_[int(rows.cut), rows.score_issue[1:]])
    good = N.neighbour_pools(rows, blocks)
    chk = N._check_neighbour_rows(rows)
    assert good.index[i] is not None and late not in good.index[i].tolist()

    def forged(index=None, drop=None):
        return N.NeighbourPools(fingerprint=good.fingerprint, index=tuple(index or good.index),
                                drop=tuple(drop or good.drop))

    idx = list(good.index)
    idx[i] = np.r_[good.index[i][:-1], late].astype(np.int32)
    with pytest.raises(RouteGuardError, match="on or after the issue day"):
        N._pools_for(chk, blocks, forged(index=idx))
    own = tuple(blocks.members[blocks.block_of_group[rows.score_group[i]]])
    assert good.drop[i] != own                     # the pool holds other groups
    drop = list(good.drop)
    drop[i] = own
    with pytest.raises(RouteRefusal, match="drop set"):
        N._pools_for(chk, blocks, forged(drop=drop))
    short = list(good.index)
    short[i] = good.index[i][:5]
    with pytest.raises(RouteRefusal, match="C11"):
        N._pools_for(chk, blocks, forged(index=short))
    rep = list(good.index)
    rep[i] = np.r_[good.index[i][:-1], good.index[i][0]].astype(np.int32)
    with pytest.raises(RouteRefusal, match="repeats"):
        N._pools_for(chk, blocks, forged(index=rep))
    nopool = list(good.index)
    nopool[i] = None
    with pytest.raises(RouteRefusal, match="no pool"):
        N._pools_for(chk, blocks, forged(index=nopool))
    assert N._pools_for(chk, blocks, good)[1] is good


# ------------------------------------------------------------------------------ helpers
def _with(rows, **changes):
    fields = {f: getattr(rows, f) for f in N.NeighbourRows.__dataclass_fields__}
    fields.update(changes)
    return N.NeighbourRows(**fields)
