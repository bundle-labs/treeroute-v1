"""treeroute_report.table: the headline tables from SAVED row-level predictions (plan 7.1, 8.1 M7; R31-R35).

Synthetic run folders are built here with the engine's own report.metrics functions, the way pipeline/passes.py
(report) and pipeline/ladder.py (table) record a run, so the builder's recompute-and-check-equal has an
independent record to check. One test renders a REAL smoke folder (watermarked); it is skipped when no
finished smoke folder exists on this machine.
"""

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from conftest import ENGINE_DIR, make_registry
from treeroute.report import metrics as M
from treeroute_report import table as T
from treeroute_report.common import ReportRefusal, sha256_text

PKG = "toy_pkg"
GROUPS = ("grp_a", "grp_b", "grp_c", "grp_d")
UNITS_PER_GROUP = 3
YEARS = (2020, 2021)
STEPS_PER_YEAR = 12
TOL = 0.5
FLOOR = 0.25
LEADS = (6,)
CONTINUITY = {PKG: {"label": T.CONTINUITY_LABEL, "source": "synthetic", "n_groups": 2, "old_test_units": 200,
                    "continuity_groups": ["grp_a", "grp_c"]}}
OWN_BAND = "this run's own D75 contrasts (synthetic)"


# ------------------------------------------------------------------------------------ synthetic runs
def _frame(lead, seed_shift=0.0, declined=False):
    """Saved rows of one lead: 4 groups x 3 units x 24 months, identity arms, a placebo and 3 baselines."""
    rows = []
    for gi, g in enumerate(GROUPS):
        for u in range(UNITS_PER_GROUP):
            unit = "%s_u%d" % (g, u)
            for yi, year in enumerate(YEARS):
                for m in range(STEPS_PER_YEAR):
                    t = year * STEPS_PER_YEAR + m
                    base = 10.0 + gi + 2.0 * np.sin(2 * np.pi * m / STEPS_PER_YEAR) + 0.3 * u
                    noise = np.sin(1.7 * t + 3.1 * u + gi) * (1.0 + 0.2 * gi)
                    y = base + noise
                    rows.append({"unit": unit, "group": g, "time": t, "year": year, "lead": lead, "issue": t - lead,
                                 "y": y, "normal": base, "legal_min": 0.0, "legal_max": float("inf"),
                                 "plain": base + 0.6 * noise + 0.05 * gi + seed_shift,
                                 "corr": base + 0.7 * noise + 0.03 * u + seed_shift,
                                 "plac": base + 0.2 * noise + 0.1, "last5": base + 0.1 * np.cos(m)})
    f = pd.DataFrame(rows)
    f.loc[5, "y"] = np.nan                                  # one unlabelled row: saved, never scored
    out = f[["unit", "group", "time", "year", "lead", "issue", "y", "normal", "legal_min", "legal_max"]].copy()
    arms = {"identity_plain_unweighted": f["plain"], "identity_corrector_unweighted": f["corr"],
            "identity_trees_off_unweighted": f["normal"]}
    if lead:
        arms = {"identity_plain_unweighted": f["plain"], "identity_trees_off_unweighted": f["normal"]}
    for name, v in arms.items():
        out["arm__" + name] = v.values
        out["pre__" + name] = v.values
    if not lead:
        out["placebo__identity_placebo_corrector_unweighted"] = f["plac"].values
        out["pre__identity_placebo_corrector_unweighted"] = f["plac"].values
    out["base__guess_normal"] = f["normal"].values
    out["base__last5_normal"] = f["last5"].values
    out["base__predict_zero"] = 0.0
    if lead:
        out["base__persistence"] = (f["y"].shift(lead).fillna(f["normal"])).values
    return out


def _per_group_and_pooled(frame, kind):
    tg = M.score_table(frame, ("group",), TOL, FLOOR, kind)
    tp = M.score_table(frame, (), TOL, FLOOR, kind)
    cols = [c for c in frame.columns if c.startswith(("arm__", "placebo__"))]
    per_group = {c: M.metric_by_key(tg, c, "mae", "group") for c in cols}

    def pooled(col):
        sel = tp[(tp["line"] == "pooled") & (tp["column"] == col) & (tp["rows_basis"] == "all")]
        return float(sel["mae"].iloc[0])
    return per_group, pooled


STRATUM = "toy_stratum"
STRATUM_EDGES = (2.0, 5.0, 8.0)


def _write_strata(folder, f0, kind, tamper):
    """per_stratum.csv as pipeline/passes.py _strata writes it (score_table by the right-closed bins), and the
    verdict's strata record; returns the record."""
    from treeroute.pipeline import record as REC

    vals = np.array([float(GROUPS.index(g) * UNITS_PER_GROUP + int(u.rsplit("_u", 1)[1]))
                     for g, u in zip(f0["group"].tolist(), f0["unit"].tolist())])
    sub = f0.copy()
    sub["stratum"] = M.stratum_bins(vals, STRATUM_EDGES)
    table = M.score_table(sub, ("stratum",), TOL, FLOOR, kind)
    table.insert(0, "stratum_column", STRATUM)
    for i, e in enumerate(STRATUM_EDGES):
        table["edge_q%d" % (25 * (i + 1))] = e
    if tamper != "stratum_missing":
        (folder / "per_stratum.csv").write_bytes(REC.csv_text(table).encode("utf-8"))
    edges = [2.0, 5.0, 9.0] if tamper == "stratum_edges" else list(STRATUM_EDGES)
    return {STRATUM: {"edges": edges, "donor_rows": 100, "bank_units_without_value": 0,
                      "test_rows": int(len(f0)), "test_rows_without_value": 0}}


def make_run(root, kind="headline", draft=False, package=PKG, folder_name="20261010_abcdef12", tamper=None,
             finished=True, scored_override=None, lead_declined=True, legacy=False, seen=(), strata=False):
    """A finished run folder recorded like pipeline/passes.py report() and pipeline/ladder.py table()."""
    folder = Path(root) / package / kind / folder_name
    (folder / "ladder").mkdir(parents=True)
    f0 = _frame(0)
    f0.to_parquet(folder / "test_preds.parquet", index=False)
    per_group, pooled = _per_group_and_pooled(f0, kind if kind != "legacy" else "legacy")
    off, plain = "arm__identity_trees_off_unweighted", "arm__identity_plain_unweighted"
    corr, plac = "arm__identity_corrector_unweighted", "placebo__identity_placebo_corrector_unweighted"
    band, records = M.band_from_pairs(per_group, [(off, plain), (off, corr), (plac, corr)])
    tagged = []
    for rec in records:
        groups = sorted(per_group[rec["reference"]])
        dv = np.array([per_group[rec["reference"]][g] - per_group[rec["arm"]][g] for g in groups])
        tag, _ = M.contrast_tag(dv, band)
        tagged.append(dict(rec, tag=tag.value))
    adopted = corr
    verdict = M.single_verdict(per_group[off], per_group[adopted], pooled(off), pooled(adopted), band, False,
                               M.REFERENCE_OWN_LINK_TREES_OFF)
    contrast = {g: per_group[off][g] - per_group[adopted][g] for g in per_group[off]}
    blocks = {g: i for i, g in enumerate(GROUPS)}
    blocked = M.blocked_jackknife(contrast, blocks)
    rec = {"kind": kind, "package": package, "adopted": adopted[len("arm__"):], "declined": False, "reference": off,
           "verdict": M.verdict_record(verdict), "band": band, "band_source": OWN_BAND, "band_pairs": tagged,
           "blocked_jackknife": {"mean": blocked.mean, "se": blocked.se, "low": blocked.low, "high": blocked.high,
                                 "n_blocks": blocked.n_groups,
                                 "flag": M.blocked_jackknife_flag(verdict.contrast, blocked)},
           "pooled_mae_adopted": pooled(adopted), "pooled_mae_reference": pooled(off), "hit_tolerance": TOL,
           "measurement_error_floor": FLOOR}
    if tamper == "verdict":
        rec["verdict"]["contrast"]["mean"] += 1e-9
    if tamper == "band_pair":
        rec["band_pairs"][0]["se"] *= 1.5
    if tamper == "no_blocked_jackknife":
        del rec["blocked_jackknife"]
    if tamper == "band_elsewhere":
        rec["band_source"] = "registry/bands.csv (the package's first headline run)"
    if strata:
        rec["strata"] = _write_strata(folder, f0, kind, tamper)
    M.write_json_once(rec, folder / "verdict.json")
    # the ladder: lead 6 declined (trees-off adopted), every lead on the common rows
    frames = {0: f0}
    info = {0: {"adopted": adopted, "reference": off, "declined": False}}
    for lead in LEADS:
        d = folder / "ladder" / ("lead_%d" % lead)
        d.mkdir()
        fl = _frame(lead, seed_shift=0.01)
        fl.to_parquet(d / "test_preds.parquet", index=False)
        frames[lead] = fl
        ad = off if lead_declined else plain
        info[lead] = {"adopted": ad, "reference": off, "declined": lead_declined}
        (d / "lead.json").write_text(json.dumps({"test": {"adopted_column": ad, "reference_column": off},
                                                 "declined_at_lead": lead_declined}), encoding="utf-8")

    def keys_of(f, col):
        ok = np.isfinite(f["y"].to_numpy(dtype=np.float64)) & np.isfinite(f[col].to_numpy(dtype=np.float64))
        return np.asarray(["%s\t%d" % (u, t) for u, t in zip(f["unit"][ok].tolist(), f["time"][ok].tolist())],
                          dtype=object)
    common = M.common_rows({L: keys_of(f, info[L]["adopted"]) for L, f in frames.items()})
    verdicts = {}
    for L, f in sorted(frames.items()):
        k = np.asarray(["%s\t%d" % (u, t) for u, t in zip(f["unit"].tolist(), f["time"].tolist())], dtype=object)
        sub = f[np.isin(k, common)].reset_index(drop=True)
        pg, pl = _per_group_and_pooled(sub, kind)
        v = M.single_verdict(pg[info[L]["reference"]], pg[info[L]["adopted"]], pl(info[L]["reference"]),
                             pl(info[L]["adopted"]), band, info[L]["declined"], M.REFERENCE_OWN_LINK_TREES_OFF)
        verdicts[str(L)] = dict(M.verdict_record(v), adopted=info[L]["adopted"], reference=info[L]["reference"],
                                guard_passed=(None if L == 0 else not info[L]["declined"]), common_rows=int(len(sub)))
    if tamper == "ladder":
        verdicts[str(LEADS[0])]["groups_better"] += 1
    ladder = {"leads": list(LEADS), "band": band, "common_rows": int(len(common)), "verdicts": verdicts,
              "hit_tolerance": TOL, "measurement_error_floor": FLOOR, "readings": {"r1": "a reading for the owner"}}
    M.write_json_once(ladder, folder / "ladder" / "ladder.json")
    scored = {g: ["%s_u%d" % (g, u) for u in range(UNITS_PER_GROUP)] for g in GROUPS}
    if scored_override:
        scored.update(scored_override)
    derived = {"R14:overlap_blocks": {"value": {"block_of_group": blocks, "members": [[g] for g in GROUPS]}},
               "R18:units": {"value": {"bank": {g: ["%s_u%d" % (g, u) for u in range(UNITS_PER_GROUP)] for g in GROUPS},
                                       "scored": scored}},
               "R10": {"value": {"leads": list(LEADS)}},
               "R18:groups": {"inputs": {"seen_during_design": list(seen)}, "value": list(GROUPS)}}
    (folder / "derived.json").write_text(json.dumps(derived), encoding="utf-8")
    run_record = {"kind": kind, "package": package, "package_fingerprint": "f" * 64, "run_fingerprint": "e" * 64,
                  "draft": {"is_draft": bool(draft), "stamp": "DRAFT synthetic" if draft else ""},
                  "headline_eligible": kind == "headline" and not draft, "not_headline_reasons": [],
                  "limits": ["synthetic limit"], "departures": [], "listed_in_reports": ["x1"],
                  "strata": [STRATUM] if strata else []}
    if legacy:
        run_record["legacy"] = True
    if draft:
        run_record["DRAFT"] = "DRAFT: synthetic"
    (folder / "run_record.json").write_text(json.dumps(run_record), encoding="utf-8")
    if finished:
        (folder / "DONE.json").write_text(json.dumps({"fingerprint": "e" * 64}), encoding="utf-8")
    return folder


@pytest.fixture
def world(tmp_path, monkeypatch):
    cont = tmp_path / "continuity.yaml"
    cont.write_text(json.dumps(CONTINUITY), encoding="utf-8")       # JSON is YAML
    hist = tmp_path / "history.yaml"
    hist.write_text(json.dumps({PKG: {"band": 0.0395, "label": "history", "source": "synthetic Part"}}),
                    encoding="utf-8")
    monkeypatch.setattr(T, "CONTINUITY_FILE", cont)
    monkeypatch.setattr(T, "HISTORY_FILE", hist)
    rows = tmp_path / "rows.yaml"
    rows.write_text(json.dumps({PKG: [{"label": "2021 only (test row)", "years": [2021]}]}), encoding="utf-8")
    monkeypatch.setattr(T, "ROWS_FILE", rows)
    protected = tmp_path / "shipped"
    protected.mkdir()
    reg = make_registry(tmp_path, [protected])
    runs = tmp_path / "runs"
    return {"runs": runs, "registry": reg, "protected": protected, "tmp": tmp_path}


def _tables(world, paths, out_name="out", watermark=False):
    return T.run_tables(paths, out=world["tmp"] / out_name, registry_dir=world["registry"], watermark=watermark,
                        echo=lambda *_: None)


# ------------------------------------------------------------------------------------------- builds
def test_builds_every_table_from_the_saved_rows(world):
    folder = make_run(world["runs"])
    res = _tables(world, [folder])
    paths = res["paths"]
    for key in ("headline", "per_year", "per_group", "continuity", "verdicts", "scores_long", "disclosures",
                "markdown", "manifest"):
        assert paths[key].is_file(), key
        text = paths[key].read_text(encoding="utf-8")
        assert sha256_text(text)[:12] in paths[key].name            # content-hashed names
    head = pd.read_csv(paths["headline"])
    assert sorted(set(head["lead"])) == [0, 6]
    assert set(head["rows"]) == {"all", "common"} and set(head["line"]) == {"pooled", "macro"}
    f0 = pd.read_parquet(folder / "test_preds.parquet")
    ok = f0["y"].notna()
    pooled0 = head[(head["lead"] == 0) & (head["rows"] == "all") & (head["line"] == "pooled")].iloc[0]
    exact = pytest.approx
    assert pooled0["mae_adopted"] == exact(M.mae(f0["y"][ok].values,
                                                 f0["arm__identity_corrector_unweighted"][ok].values), rel=1e-14)
    assert pooled0["mae_guess_normal"] == exact(M.mae(f0["y"][ok].values, f0["base__guess_normal"][ok].values),
                                                rel=1e-14)
    assert pooled0["mae_last5_normal"] == exact(M.mae(f0["y"][ok].values, f0["base__last5_normal"][ok].values),
                                                rel=1e-14)
    assert pooled0["anom_r2_guess_normal"] == 0.0
    macro0 = head[(head["lead"] == 0) & (head["rows"] == "all") & (head["line"] == "macro")].iloc[0]
    per = [M.mae(g["y"].dropna().values, g.loc[g["y"].notna(), "arm__identity_corrector_unweighted"].values)
           for _, g in f0.groupby("group")]
    assert abs(macro0["mae_adopted"] - float(np.mean(per))) < 1e-12
    for col in ("hit_adopted", "corr2_adopted", "calibration_ratio_adopted", "preclip_rate_adopted",
                "hit_floor_adopted", "mae_predict_zero", "detection_adopted", "detection_events_adopted"):
        assert np.isfinite(pooled0[col]), col
    det = M.top10_detection(f0["y"][ok].values, f0["arm__identity_corrector_unweighted"][ok].values)
    assert pooled0["detection_adopted"] == det.score and pooled0["detection_events_adopted"] == det.n_events
    years = pd.read_csv(paths["per_year"])
    assert sorted(set(years["year"])) == list(YEARS)
    assert "detection_adopted" in years.columns
    assert "strict top-10% detection" in paths["markdown"].read_text(encoding="utf-8")
    assert paths["per_stratum"].is_file() and pd.read_csv(paths["per_stratum"]).empty    # no stratum declared
    groups = pd.read_csv(paths["per_group"])
    assert sorted(set(groups["group"])) == list(GROUPS)
    assert (groups["noise_note"].str.contains("noisy")).all()
    cont = pd.read_csv(paths["continuity"])
    assert (cont["label"] == T.CONTINUITY_LABEL).all()
    assert (cont["groups_scored"] == 2).all() and (cont["groups_listed"] == 2).all()
    assert (cont["old_test_units"] == 200).all()
    ver = pd.read_csv(paths["verdicts"])
    assert ver["recomputed_equals_recorded"].all()
    assert list(ver["source"]) == ["verdict.json", "ladder/ladder.json", "ladder/ladder.json"]
    assert (ver["history_band"] == 0.0395).all()
    md = paths["markdown"].read_text(encoding="utf-8")
    assert "continuity, not a replication" in md and "never R2 alone" in md and T.WATERMARK not in md
    disc = pd.read_csv(paths["disclosures"])
    assert set(disc["kind"]) >= {"limit", "listed_in_reports", "ladder_reading:r1"}
    sub = pd.read_csv(paths["subsets"])
    year_row = sub[(sub["label"] == "2021 only (test row)") & (sub["lead"] == 0) & (sub["rows"] == "all")
                   & (sub["line"] == "pooled")].iloc[0]
    ok21 = ok & (f0["year"] == 2021)
    assert year_row["mae_adopted"] == pytest.approx(
        M.mae(f0["y"][ok21].values, f0["arm__identity_corrector_unweighted"][ok21].values), rel=1e-14)


def test_the_seen_during_design_row_leaves_those_groups_out(world):
    folder = make_run(world["runs"], seen=("grp_b",))
    sub = pd.read_csv(_tables(world, [folder])["paths"]["subsets"])
    row = sub[sub["label"].str.startswith("without seen_during_design") & (sub["lead"] == 0)
              & (sub["rows"] == "all") & (sub["line"] == "pooled")].iloc[0]
    assert row["n_groups"] == len(GROUPS) - 1 and "grp_b" in row["label"]


def test_a_clean_rebuild_gives_the_same_files(world):
    folder = make_run(world["runs"])
    a = _tables(world, [folder], "out_a")["paths"]
    b = _tables(world, [folder], "out_b")["paths"]
    assert {k: p.name for k, p in a.items()} == {k: p.name for k, p in b.items()}
    for k in a:
        assert a[k].read_bytes() == b[k].read_bytes(), k
    again = _tables(world, [folder], "out_a")["paths"]         # an identical file is kept, not rewritten
    assert {k: p.name for k, p in again.items()} == {k: p.name for k, p in a.items()}


def test_the_run_root_form_finds_finished_headline_runs_and_skips_unfinished(world):
    make_run(world["runs"])
    make_run(world["runs"], folder_name="20261009_aaaaaaaa", finished=False)     # an older, aborted attempt
    res = _tables(world, [world["runs"]])
    assert [r.package for r in res["built"]["runs"]] == [PKG]
    assert [r.folder.name for r in res["built"]["runs"]] == ["20261010_abcdef12"]
    assert any("unfinished headline run skipped" in n and "20261009_aaaaaaaa" in n for n in res["built"]["notes"])


def test_a_package_with_only_unfinished_headline_runs_is_refused_under_a_run_root(world):
    make_run(world["runs"])
    make_run(world["runs"], package="toy_other", finished=False)
    with pytest.raises(ReportRefusal, match="toy_other .*unfinished headline runs and no finished one"):
        _tables(world, [world["runs"]])
    assert not (world["tmp"] / "out").exists()


def test_a_declared_stratum_is_copied_with_its_checks_and_marked_not_recomputed(world):
    folder = make_run(world["runs"], strata=True)
    paths = _tables(world, [folder])["paths"]
    st = pd.read_csv(paths["per_stratum"])
    engine = pd.read_csv(folder / "per_stratum.csv")
    assert len(st) == len(engine) and (st["source"] == T.STRATUM_SOURCE).all()
    assert (st["package"] == PKG).all() and set(st["stratum_column"]) == {STRATUM}
    assert np.allclose(st["mae"].to_numpy(), engine["mae"].to_numpy(), rtol=0, atol=0, equal_nan=True)
    md = paths["markdown"].read_text(encoding="utf-8")
    assert "## Per report stratum" in md and "NOT recomputed here" in md
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    assert any(i["file"] == "per_stratum" for i in manifest["inputs"])


@pytest.mark.parametrize("tamper,match", [("stratum_edges", "edges"), ("stratum_missing", "holds no per_stratum.csv")])
def test_refuses_a_stratum_table_that_does_not_match_the_records(world, tamper, match):
    folder = make_run(world["runs"], strata=True, tamper=tamper)
    with pytest.raises(ReportRefusal, match=match):
        _tables(world, [folder])


def test_two_finished_headline_runs_of_one_package_are_refused_under_a_run_root(world):
    make_run(world["runs"])
    make_run(world["runs"], folder_name="20261011_bbbbbbbb")
    with pytest.raises(ReportRefusal, match="2 finished headline runs"):
        _tables(world, [world["runs"]])


# ----------------------------------------------------------------------------------------- refusals
def test_refuses_a_draft_run(world):
    folder = make_run(world["runs"], draft=True)
    with pytest.raises(Exception, match="G-DRAFT"):
        _tables(world, [folder])


def test_refuses_a_smoke_run_without_the_test_flag(world):
    folder = make_run(world["runs"], kind="smoke")
    with pytest.raises(Exception, match="G-LEGACY"):
        _tables(world, [folder])


def test_refuses_a_legacy_run(world):
    folder = make_run(world["runs"], legacy=True)
    with pytest.raises(Exception, match="G-LEGACY.*legacy"):
        _tables(world, [folder])


def test_refuses_an_unfinished_run(world):
    folder = make_run(world["runs"], finished=False)
    with pytest.raises(Exception, match="has not finished"):
        _tables(world, [folder])


def test_refuses_saved_rows_that_do_not_score_the_derived_units(world):
    folder = make_run(world["runs"], scored_override={"grp_b": ["grp_b_u0", "grp_b_u1"]})
    with pytest.raises(Exception, match="G-SPLIT"):
        _tables(world, [folder])


def test_refuses_a_recorded_verdict_that_differs_from_the_saved_rows(world):
    folder = make_run(world["runs"], tamper="verdict")
    with pytest.raises(ReportRefusal, match="R34-RECOMPUTE.*nowcast verdict"):
        _tables(world, [folder])


def test_refuses_a_recorded_band_pair_that_differs(world):
    folder = make_run(world["runs"], tamper="band_pair")
    with pytest.raises(ReportRefusal, match="R34-RECOMPUTE.*band pair"):
        _tables(world, [folder])


def test_refuses_a_recorded_lead_verdict_that_differs(world):
    folder = make_run(world["runs"], tamper="ladder")
    with pytest.raises(ReportRefusal, match="R34-RECOMPUTE.*lead-6 verdict"):
        _tables(world, [folder])


def test_refuses_a_verdict_without_the_blocked_jackknife(world):
    folder = make_run(world["runs"], tamper="no_blocked_jackknife")
    with pytest.raises(ReportRefusal, match="R34-RECOMPUTE.*no blocked_jackknife"):
        _tables(world, [folder])


def test_a_band_from_another_source_is_marked_taken_as_recorded(world):
    paths = _tables(world, [make_run(world["runs"], tamper="band_elsewhere")])["paths"]
    ver = pd.read_csv(paths["verdicts"])
    assert (ver["band_check"] == T.BAND_AS_RECORDED).all()
    md = paths["markdown"].read_text(encoding="utf-8")
    assert "The band of %s was TAKEN AS RECORDED" % PKG in md and T.BAND_AS_RECORDED in md


def test_an_own_band_is_marked_recomputed(world):
    paths = _tables(world, [make_run(world["runs"])])["paths"]
    assert (pd.read_csv(paths["verdicts"])["band_check"] == T.BAND_RECOMPUTED).all()
    assert "The band was recomputed from each run's own contrasts and is equal." in \
        paths["markdown"].read_text(encoding="utf-8")


def test_refuses_a_headline_run_missing_a_continuity_group(world, monkeypatch):
    cont = dict(CONTINUITY)
    cont[PKG] = dict(CONTINUITY[PKG], continuity_groups=["grp_a", "grp_zz"])
    path = world["tmp"] / "continuity2.yaml"
    path.write_text(json.dumps(cont), encoding="utf-8")
    monkeypatch.setattr(T, "CONTINUITY_FILE", path)
    folder = make_run(world["runs"])
    with pytest.raises(ReportRefusal, match="continuity groups not scored"):
        _tables(world, [folder])


def test_refuses_a_package_without_a_continuity_entry(world):
    folder = make_run(world["runs"], package="toy_unlisted")
    with pytest.raises(ReportRefusal, match="no entry"):
        _tables(world, [folder])


def test_refuses_an_output_folder_under_a_protected_root(world):
    folder = make_run(world["runs"])
    with pytest.raises(Exception, match="G-NOOVERWRITE"):
        T.run_tables([folder], out=world["protected"] / "tables", registry_dir=world["registry"],
                     echo=lambda *_: None)


# ---------------------------------------------------------------------------------- smoke watermark
def test_the_test_flag_renders_a_smoke_run_with_the_watermark(world):
    folder = make_run(world["runs"], kind="smoke")
    paths = _tables(world, [folder], watermark=True)["paths"]
    for key, path in paths.items():
        assert path.name.startswith(T.SMOKE_PREFIX), key
    head = pd.read_csv(paths["headline"])
    assert (head["watermark"] == T.WATERMARK).all()
    assert T.WATERMARK in paths["markdown"].read_text(encoding="utf-8")


def test_the_test_flag_refuses_a_non_smoke_run(world):
    folder = make_run(world["runs"])
    with pytest.raises(ReportRefusal, match="smoke runs only"):
        _tables(world, [folder], watermark=True)


def _real_smoke_folder():
    root = Path("D:/treeroute/runs")
    found = []
    for pkg in ("pm25", "fire", "ndvi", "defo"):
        kind_dir = root / pkg / "smoke"
        if kind_dir.is_dir():
            found += [p for p in kind_dir.iterdir() if (p / "DONE.json").is_file() and (p / "verdict.json").is_file()]
    return sorted(found, key=lambda p: p.name)[-1] if found else None


def test_a_real_smoke_folder_renders_watermarked_and_its_records_recompute_equal(tmp_path):
    folder = _real_smoke_folder()
    if folder is None:
        pytest.skip("no finished smoke folder under D:/treeroute/runs on this machine")
    reg = make_registry(tmp_path, [tmp_path / "shipped"])
    res = T.run_tables([folder], out=tmp_path / "out", registry_dir=reg, watermark=True, echo=lambda *_: None)
    ver = pd.read_csv(res["paths"]["verdicts"])
    assert ver["recomputed_equals_recorded"].all() and len(ver) >= 1
    md = res["paths"]["markdown"].read_text(encoding="utf-8")
    assert md.startswith("# Headline tables -- " + T.WATERMARK)
    head = pd.read_csv(res["paths"]["headline"])
    assert (head["watermark"] == T.WATERMARK).all()
    rec = json.loads((folder / "verdict.json").read_text(encoding="utf-8"))
    pooled0 = head[(head["lead"] == 0) & (head["rows"] == "all") & (head["line"] == "pooled")].iloc[0]
    # the CSV prints 16 significant digits (the engine's csv_text); the exact check ran in memory
    assert pooled0["mae_adopted"] == pytest.approx(rec["pooled_mae_adopted"], rel=1e-14)


def test_the_command_refuses_a_smoke_folder_without_the_flag(tmp_path):
    folder = _real_smoke_folder()
    if folder is None:
        pytest.skip("no finished smoke folder under D:/treeroute/runs on this machine")
    reg = make_registry(tmp_path, [tmp_path / "shipped"])
    proc = subprocess.run([sys.executable, "-m", "treeroute_report.table", str(folder), "--out", str(tmp_path / "o"),
                           "--registry-dir", str(reg)], cwd=str(ENGINE_DIR), capture_output=True, text=True,
                          timeout=300)
    assert proc.returncode == T.EXIT_REFUSED, proc.stdout + proc.stderr
    assert "G-LEGACY" in proc.stderr and not (tmp_path / "o").exists()
