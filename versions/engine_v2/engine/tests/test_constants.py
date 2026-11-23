"""Engine constants: ids, values, test-exposed flags, statuses; unset constants fail loudly."""

import json

import pytest

from treeroute import engine_constants as K
from treeroute.errors import UnsetConstantError


def test_every_3_1_convention_group_is_present():
    groups = set(K.groups())
    for i in range(1, 18):          # C1-C17 (C16, C17: leave one region out)
        assert "C%d" % i in groups
    assert "A7" in groups


def test_ids_unique_and_values_immutable():
    ids = [c.id for c in K.constants()]
    assert len(ids) == len(set(ids))
    for c in K.constants():
        assert c.status in K.STATUSES
        assert K._frozen(c.value), c.id


def test_table_is_json_and_hash_is_stable():
    text = json.dumps(K.table(), allow_nan=False)
    # owner ruling N (S12 a) set the last unset constant, C9.guard_tolerance_k: no row reads UNSET any more
    assert "UNSET" not in text and all(c.status != "unset" for c in K.constants())
    assert K.constants_hash() == K.constants_hash()
    assert len(K.constants_hash()) == 64


def test_unset_constant_refuses_every_use():
    """UPDATED 2026-10-06: owner ruling N (S12 a) set C9.guard_tolerance_k = 5.230771281733543e-08 (status cited),
    so the refusal is checked on the UNSET sentinel itself, which every unset constant would hold."""
    assert K.get("C9.guard_tolerance_k") == K.GUARD_TOLERANCE_K == 5.230771281733543e-08
    u = K.UNSET
    with pytest.raises(UnsetConstantError):
        bool(u)
    with pytest.raises(UnsetConstantError):
        u * 2.0
    with pytest.raises(UnsetConstantError):
        float(u)
    # comparisons and hashing refuse too, so 'tol == 0' cannot quietly give False
    for use in (lambda u: u == 0, lambda u: u != 0, lambda u: 0 == u, lambda u: hash(u),
                lambda u: {u: 1}, lambda u: u % 3, lambda u: -u, lambda u: abs(u),
                lambda u: round(u), lambda u: u ** 2, lambda u: u // 2):
        with pytest.raises(UnsetConstantError):
            use(u)
    assert repr(u) == "UNSET"


def test_test_exposed_flags_match_plan_7_2():
    exposed = {c.id for c in K.constants() if c.test_exposed}
    assert exposed == {"C7.region_router_row_budget", "C12.per_unit_trees_centre",
                       "C12.per_unit_context_centre", "C12.neighbour_trees_centre",
                       "C12.neighbour_context_centre", "C12.region_lambda_centre",
                       "A7.inner_cut_bank_refit"}
    # plan 7.2: "Per-unit and neighbour centre 0.5 / 0.25"
    assert (K.NEIGHBOUR_TREES_CENTRE, K.NEIGHBOUR_CONTEXT_CENTRE) == (0.5, 0.25)


def test_a7_is_the_inner_cut_bank_refit_as_ruled():
    """Owner rulings E, L6 option (b): the inner decision's bank and correctors are refit at the inner
    cut. The option (a) flag (one bank at the donor train end) is gone, so the manifest's constants table
    and constants_hash cannot record the option the owner did not pick."""
    a7 = {c.id: c for c in K.by_group("A7")}
    assert set(a7) == {"A7.inner_cut_bank_refit"}
    assert K.get("A7.inner_cut_bank_refit") is True and K.INNER_CUT_BANK_REFIT is True
    assert a7["A7.inner_cut_bank_refit"].status == "cited" and a7["A7.inner_cut_bank_refit"].test_exposed
    assert not hasattr(K, "ONE_BANK_AT_DONOR_TRAIN_END")
    assert all("donor_train_end" not in c.id for c in K.constants())


def test_c15_group_thresholds_are_cited_and_the_other_two_confirmed_by_the_owner():
    status = {c.id: c.status for c in K.by_group("C15")}
    # leave one region out: the four donor/test thresholds became two group thresholds (D44 restated,
    # not reopened: SIGNATURES_LORO_ADDENDUM.md; owner rulings A signed D44's proposed default)
    assert list(status) == [
        "C15.missing_flag_share", "C15.min_groups", "C15.flag_groups_below",
        "C15.fallback_min_units_for_search"]
    assert status["C15.min_groups"] == status["C15.flag_groups_below"] == "cited"
    # were 'proposed' (plan 9.1 item 2f); owner ruling N (S20 b, 2026-10-06) confirmed them: 'cited'
    assert status["C15.missing_flag_share"] == status["C15.fallback_min_units_for_search"] == "cited"
    assert (K.MIN_GROUPS, K.FLAG_GROUPS_BELOW) == (3, 14)


# ---- leave one region out (owner rulings D and E) ----
def test_no_constant_counts_donor_or_test_groups_any_more():
    ids = {c.id for c in K.constants()}
    for gone in ("C8.donor_folds_max", "C13.smoke_donor_groups", "C13.smoke_test_groups",
                 "C15.min_test_groups", "C15.min_donor_groups", "C15.flag_test_groups_below",
                 "C15.flag_donor_groups_below", "C13.trees_per_donor", "C13.smoke_trees_per_donor",
                 "C7.units_per_group"):
        assert gone not in ids, gone
    for name in ("DONOR_FOLDS_MAX", "SMOKE_DONOR_GROUPS", "SMOKE_TEST_GROUPS", "MIN_TEST_GROUPS",
                 "MIN_DONOR_GROUPS", "FLAG_TEST_GROUPS_BELOW", "FLAG_DONOR_GROUPS_BELOW", "UNITS_PER_GROUP"):
        assert not hasattr(K, name), name
    for c in K.constants():
        for word in ("donor_groups", "test_groups", "donor_folds", "per_donor", "smoke_donor", "smoke_test"):
            assert word not in c.id, c.id


def test_c8_is_leave_one_group_out_and_smoke_takes_the_first_four_groups():
    assert [c.id for c in K.by_group("C8")] == ["C8.neighbour_folds_leave_one_group_out"]
    assert K.get("C8.neighbour_folds_leave_one_group_out") is True
    # R21 under LORO: the first 4 groups in sorted order, 40 units each (all scored), 12 trees per group
    assert (K.SMOKE_GROUPS, K.SMOKE_UNITS_PER_GROUP, K.SMOKE_TREES_PER_GROUP) == (4, 40, 12)
    assert K.get("C13.smoke_groups") == 4


def test_trees_per_group_and_the_unregistered_aliases():
    assert K.get("C13.trees_per_group") == K.TREES_PER_GROUP == 100
    assert K.get("C13.smoke_trees_per_group") == K.SMOKE_TREES_PER_GROUP == 12
    # fit/bank.py and the legacy harness still import the old names: same values, not registered
    assert K.TREES_PER_DONOR == K.TREES_PER_GROUP and K.SMOKE_TREES_PER_DONOR == K.SMOKE_TREES_PER_GROUP
    assert len([c for c in K.constants() if c.id.startswith("C13.trees_per")]) == 1
    assert K.get("C7.bank_units_per_group") == K.BANK_UNITS_PER_GROUP == 100


def test_c16_scored_unit_budget_is_k_20_as_ruled():
    c16 = {c.id: c for c in K.by_group("C16")}
    assert set(c16) == {"C16.k_group_equivalents", "C16.scored_units_min"}
    assert (K.K_GROUP_EQUIVALENTS, K.SCORED_UNITS_MIN) == (20, 10)
    assert all(c.status == "cited" and not c.test_exposed for c in c16.values())
    # L1: max(10, floor(20 x n / G)) gives 15 / 50 / 2,040 / 15 per group on the four headline packages
    for n, g, want in ((100, 127, 15), (100, 40, 50), (4285, 42, 2040), (100, 133, 15)):
        assert max(K.SCORED_UNITS_MIN, (K.K_GROUP_EQUIVALENTS * n) // g) == want


def test_c17_rival_folds_is_ten():
    assert [c.id for c in K.by_group("C17")] == ["C17.rival_folds"]
    assert K.RIVAL_FOLDS == 10 and K.get("C17.rival_folds") == 10


def test_moved_fit_constants_have_ids_and_match_the_fit_modules():
    """Owner rulings E: D51 5 sigma, D52 50 rows and the block size 12,288 move into
    engine_constants.py. fit/ still holds its own copies (outside the loro build's write scope): they
    must equal the engine constants until fit/ reads them."""
    from treeroute.fit import bank, correctors, tables

    assert K.get("C13.oob_share_tolerance_sigmas") == K.OOB_SHARE_TOLERANCE_SIGMAS == 5.0
    assert K.get("C13.corrector_min_oob_rows") == K.CORRECTOR_MIN_OOB_ROWS == 50
    assert K.get("C14.table_row_block_rows") == K.TABLE_ROW_BLOCK_ROWS == 12288
    assert bank.OOB_SHARE_TOLERANCE_SIGMAS == K.OOB_SHARE_TOLERANCE_SIGMAS
    assert correctors.CORRECTOR_MIN_OOB_ROWS == K.CORRECTOR_MIN_OOB_ROWS
    assert tables.ROW_BLOCK_ROWS == K.TABLE_ROW_BLOCK_ROWS
    assert bank.TREES_PER_DONOR == K.TREES_PER_GROUP and bank.SMOKE_TREES_PER_DONOR == K.SMOKE_TREES_PER_GROUP


def test_every_constant_has_an_origin_comment():
    """Each registered constant's paragraph (the non-blank lines up to its own line) holds a comment;
    the constants leave one region out touched cite an origin, a ruling or a rule."""
    import inspect
    import re

    lines = inspect.getsource(K).splitlines()
    for c in K.constants():
        at = next(i for i, ln in enumerate(lines) if '_c("%s"' % c.id in ln)
        lo = at
        while lo > 0 and lines[lo - 1].strip():
            lo -= 1
        text = "\n".join(lines[lo:at + 1])
        assert "#" in text, c.id
        if c.id.split(".")[0] in ("C8", "C13", "C14", "C15", "C16", "C17"):
            assert re.search(r"origin|ruling|R\d+|D\d+", text), c.id


def test_thread_constants_match_the_a8_profile():
    assert (K.FOREST_THREADS, K.BLAS_THREADS, K.TREE_PREDICT_WORKERS, K.ROUTER_WORKERS,
            K.ROUTER_WORKER_BLAS_THREADS, K.SKLEARNEX_REQUIRED) == (4, 4, 8, 8, 1, True)


def test_grid_sizes():
    assert len(K.PENALTY_LEVELS) * len(K.PENALTY_RATIOS) == 35
    assert len(K.REGION_PENALTY_LEVELS) == 7
    assert min(K.PENALTY_LEVELS) == 0.1 and max(K.PENALTY_LEVELS) == 100.0


def test_get_reads_by_id():
    assert K.get("C13.trees_per_group") == K.TREES_PER_GROUP == 100
    with pytest.raises(KeyError):
        K.get("C99.nothing")


def test_duplicate_or_mutable_registration_is_refused():
    with pytest.raises(ValueError):
        K._c("C1.test_years", 4)
    with pytest.raises(ValueError):
        K._c("T.mutable_probe", [1, 2])


def test_extra_numbers_named_by_the_rules_are_registered():
    # owner ruling N (S20 b, 2026-10-06) confirmed the 'extra' numbers: they are 'cited' now, none is left 'extra'
    assert not [c.id for c in K.constants() if c.status == "extra"]
    extra = {c.id: c.value for c in K.constants() if c.id.startswith(("S1.", "S2.", "S5."))}
    assert extra["S2.recent_normal_years"] == 5  # R31
    assert extra["S5.cadence_constancy_tolerance"] == 0.001  # G-CADENCE 0.1%
    assert extra["S5.support_min_distinct_values"] == 2  # G-SUPPORT "at least 2"
    assert extra["S2.link_distinct_values_above"] == 2  # R22 "more than 2"
    assert extra["S1.unit_id_latlon_decimals"] == 4  # plan 1.2
    assert "S2.link_min_distinct_values" not in extra  # renamed: the old id read as ">= 2"


def test_the_lead_constant_is_6_and_12_months_and_the_g1_flag_share_is_registered():
    """Owner ruling I1: C6.lead_months is 6 and 12 months (lead 0 runs as the contract, C6.lead_zero_contract).
    Owner ruling G1's 5% flag share is the engine constant C10.context_missing_flag_share (moved out of
    pipeline/stages.py), each with its origin comment beside it."""
    from pathlib import Path

    from treeroute.pipeline import stages as ST

    assert K.get("C6.lead_months") == K.LEAD_MONTHS == (6, 12) and K.get("C6.lead_zero_contract") is True
    assert K.get("C10.context_missing_flag_share") == K.CONTEXT_MISSING_FLAG_SHARE == 0.05
    assert not hasattr(ST, "CONTEXT_MISSING_FLAG_SHARE")              # one home only
    lines = Path(K.__file__).read_text(encoding="utf-8").splitlines()
    for name, ruling in (("LEAD_MONTHS = _c(", "ruling I1"), ("CONTEXT_MISSING_FLAG_SHARE = _c(", "ruling G1")):
        at = next(i for i, line in enumerate(lines) if line.startswith(name))
        assert ruling in "\n".join(lines[max(0, at - 5):at]), name
