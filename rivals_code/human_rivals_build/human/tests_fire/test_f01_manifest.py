"""T-F01 manifest and sha (SPEC_HUMAN_PARTB.txt 3.1, 3.2; ATTENTION B8; review R-9, R-11): adapters/fire_geff.py
reads the fetcher's own product_manifest.json and refuses anything but the fetcher's exact, complete layout.

- availability() is (True, ...) only for an existing manifest that lists files and says complete: true; a missing
  `complete` key (the fetcher's first or killed run, FP:726-735, :801), complete false, and a manifest path in the
  UNSET_OD6 placeholder folder (registry/_products.yaml 2.7) are (False, the product's waiting_line), and build refuses
  on each. The tool's own ctx.product_available says True on the no-`complete` manifest: the adapter must not use it.
- build refuses: a file on disk the manifest does not list, a tampered byte (sha256 through ctx.open_product), a
  manifest of another dataset, a request with another system_version (D2) or another leadtime_hour list (D3), a region
  named by two boxes, a slim group named by no box.
"""

import json
from pathlib import Path

import pytest

from tests_fire import fixtures_fire as FF


def _refusals(geff):
    return (geff.FireGeffRefusal,) + FF.tool_refusals()


def _edit_manifest(folder: Path, fn) -> None:
    p = Path(folder) / "product_manifest.json"
    m = json.loads(p.read_text(encoding="utf-8"))
    fn(m)
    p.write_text(json.dumps(m, indent=1, sort_keys=True), encoding="utf-8")


def _folder(toy, pid):
    return Path(toy.products[pid]["manifest"]).parent


# ------------------------------------------------------------------------------------------ availability
def test_f01_complete_manifest_is_available(geff, raw_subsets, tmp_path):
    toy = FF.era5_toy(tmp_path, raw_subsets)
    ok, line = geff.availability(toy.ctx(), toy.rival)
    assert ok is True, line
    assert isinstance(line, str) and line
    toy6 = FF.seas5_toy(tmp_path / "d3", raw_subsets)
    ok6, line6 = geff.availability(toy6.ctx(), toy6.rival)
    assert ok6 is True, line6


@pytest.mark.parametrize("complete", [None, False], ids=["no_complete_key", "complete_false"])
def test_f01_unfinished_manifest_waits_and_build_refuses(geff, raw_subsets, tmp_path, complete):
    toy = FF.era5_toy(tmp_path, raw_subsets, complete=complete)
    ctx = toy.ctx()
    if complete is None:
        # the tool's own check passes a manifest without `complete` (index.py:150): the reason 3.1 reads it itself
        assert ctx.product_available(FF.ERA5_PID) is True
        assert "complete" not in json.loads(Path(toy.products[FF.ERA5_PID]["manifest"]).read_text(encoding="utf-8"))
    ok, line = geff.availability(ctx, toy.rival)
    assert ok is False
    assert line == FF.ERA5_WAITING
    FF.refuses(geff.build, toy.ctx(), toy.rival, 0, "all", kinds=_refusals(geff))


def test_f01_unset_od6_placeholder_waits_and_build_refuses(geff, raw_subsets, tmp_path):
    toy = FF.era5_toy(tmp_path, raw_subsets)
    placeholder = (tmp_path / "human_products" / "cems_fire_historical_fwi" /
                   "geff_era5_v4_1_consolidated_fwi_2003-2022_UNSET_OD6" / "product_manifest.json")
    assert not placeholder.parent.exists()
    toy.products[FF.ERA5_PID]["manifest"] = str(placeholder)
    ok, line = geff.availability(toy.ctx(), toy.rival)
    assert (ok, line) == (False, FF.ERA5_WAITING)
    FF.refuses(geff.build, toy.ctx(), toy.rival, 0, "all", kinds=_refusals(geff))
    toy6 = FF.seas5_toy(tmp_path / "d3", raw_subsets)
    toy6.products[FF.SEAS5_PID]["manifest"] = str(tmp_path / "x_UNSET_OD6" / "product_manifest.json")
    assert geff.availability(toy6.ctx(), toy6.rival) == (False, FF.SEAS5_WAITING)
    FF.refuses(geff.build, toy6.ctx(), toy6.rival, 6, "all", kinds=_refusals(geff))


def test_f01_manifest_without_files_waits(geff, raw_subsets, tmp_path):
    toy = FF.era5_toy(tmp_path, raw_subsets)
    _edit_manifest(_folder(toy, FF.ERA5_PID), lambda m: m.update(files={}))
    ok, line = geff.availability(toy.ctx(), toy.rival)
    assert ok is False and line == FF.ERA5_WAITING


# ------------------------------------------------------------------------------------------ build refusals
def test_f01_a_file_not_in_the_manifest_refuses(geff, raw_subsets, tmp_path):
    toy = FF.era5_toy(tmp_path, raw_subsets)
    folder = _folder(toy, FF.ERA5_PID)
    extra = "hist_greece_mainland_2020-2020.nc"
    (folder / extra).write_bytes((folder / "hist_greece_mainland_2018-2019.nc").read_bytes())
    ctx = toy.ctx()
    ctx.extra_listed[FF.ERA5_PID] = [extra]          # the folder lists a file the fetcher's manifest does not
    FF.refuses(geff.build, ctx, toy.rival, 0, "all", kinds=_refusals(geff))


def test_f01_a_stray_file_on_disk_refuses_without_a_listing(geff, raw_subsets, tmp_path):
    # the real ctx.product_files lists the manifest's own names, so only the folder itself shows a stray file
    toy = FF.era5_toy(tmp_path, raw_subsets)
    folder = _folder(toy, FF.ERA5_PID)
    (folder / "hist_greece_mainland_2018-2019.nc.part").write_bytes(b"left over")
    FF.refuses(geff.build, toy.ctx(), toy.rival, 0, "all", kinds=_refusals(geff), words=("only on disk",))


def test_f01_a_subfolder_on_disk_refuses(geff, raw_subsets, tmp_path):
    toy = FF.era5_toy(tmp_path, raw_subsets)
    (_folder(toy, FF.ERA5_PID) / "old").mkdir()
    FF.refuses(geff.build, toy.ctx(), toy.rival, 0, "all", kinds=_refusals(geff), words=("only on disk",))


def test_f01_a_tampered_byte_refuses(geff, raw_subsets, tmp_path):
    toy = FF.era5_toy(tmp_path, raw_subsets)
    p = _folder(toy, FF.ERA5_PID) / "hist_greece_mainland_2018-2019.nc"
    b = bytearray(p.read_bytes())
    b[-10] ^= 0x01
    p.write_bytes(bytes(b))
    FF.refuses(geff.build, toy.ctx(), toy.rival, 0, "all", kinds=_refusals(geff), words=("sha",))


def test_f01_another_dataset_refuses(geff, raw_subsets, tmp_path):
    toy = FF.era5_toy(tmp_path, raw_subsets, dataset="cems-fire-historical")       # not cems-fire-historical-v1
    FF.refuses(geff.build, toy.ctx(), toy.rival, 0, "all", kinds=_refusals(geff))
    toy6 = FF.seas5_toy(tmp_path / "d3", raw_subsets, dataset=FF.ERA5_DATASET)
    FF.refuses(geff.build, toy6.ctx(), toy6.rival, 6, "all", kinds=_refusals(geff))


def test_f01_another_system_version_refuses(geff, raw_subsets, tmp_path):
    toy = FF.era5_toy(tmp_path, raw_subsets)

    def edit(m):
        for r in m["requests"].values():
            r["request"]["system_version"] = ["4_0"]
    _edit_manifest(_folder(toy, FF.ERA5_PID), edit)
    FF.refuses(geff.build, toy.ctx(), toy.rival, 0, "all", kinds=_refusals(geff))


def test_f01_another_leadtime_hour_refuses(geff, raw_subsets, tmp_path):
    toy = FF.seas5_toy(tmp_path, raw_subsets)

    def edit(m):
        r = sorted(m["requests"].values(), key=lambda r: r["file"])[0]
        r["request"]["leadtime_hour"] = [str(12 + 24 * k) for k in range(149, 184)]    # leads 149..183
    _edit_manifest(_folder(toy, FF.SEAS5_PID), edit)
    FF.refuses(geff.build, toy.ctx(), toy.rival, 6, "all", kinds=_refusals(geff))


def test_f01_another_release_version_refuses(geff, raw_subsets, tmp_path):
    toy = FF.seas5_toy(tmp_path, raw_subsets)

    def edit(m):
        for r in m["requests"].values():
            r["request"]["release_version"] = ["4"]
    _edit_manifest(_folder(toy, FF.SEAS5_PID), edit)
    FF.refuses(geff.build, toy.ctx(), toy.rival, 6, "all", kinds=_refusals(geff))


def test_f01_a_region_in_two_boxes_refuses(geff, raw_subsets, tmp_path):
    files = FF.seas5_raw_files(raw_subsets)
    for f in files:
        if f["file"] == "seas_cerrado_2019.nc":
            f["regions"] = ["cerrado", "great_plains"]                 # great_plains is also its own box
    toy = FF.seas5_toy(tmp_path, raw_subsets, files=files)
    FF.refuses(geff.build, toy.ctx(), toy.rival, 6, "all", kinds=_refusals(geff))


def test_f01_a_group_in_no_box_refuses(geff, raw_subsets, tmp_path):
    files = [f for f in FF.seas5_raw_files(raw_subsets) if "cerrado" not in f["file"]]
    toy = FF.seas5_toy(tmp_path, raw_subsets, files=files)              # the cerrado units stay in the slim
    assert "cerrado" in set(toy.units["group"])
    FF.refuses(geff.build, toy.ctx(), toy.rival, 6, "all", kinds=_refusals(geff))


def test_f01_request_file_differs_from_file_refuses(geff, raw_subsets, tmp_path):
    """Each file entry's request_id names a request whose `file` is that same name (3.2)."""
    toy = FF.era5_toy(tmp_path, raw_subsets)

    def edit(m):
        for r in m["requests"].values():
            r["file"] = "hist_somewhere_else_2018-2019.nc"
    _edit_manifest(_folder(toy, FF.ERA5_PID), edit)
    FF.refuses(geff.build, toy.ctx(), toy.rival, 0, "all", kinds=_refusals(geff))


def test_f01_stage_must_be_all(geff, raw_subsets, tmp_path):
    toy = FF.era5_toy(tmp_path, raw_subsets)
    for stage in ("train", "test"):
        FF.refuses(geff.build, toy.ctx(stage=stage), toy.rival, 0, stage, kinds=_refusals(geff))


def test_f01_module_surface(geff):
    """3.1: the fixed names B3's tests call."""
    assert geff.ADAPTER_FORMAT == "human-adapter-fire-geff/1"
    assert tuple(geff.KINDS) == ("era5_daily", "seas5_daily_leads")
    assert geff.EARTH_RADIUS_KM == 6371.0
    assert issubclass(geff.FireGeffRefusal, RuntimeError)
    for name in ("availability", "build", "wrap_lon", "haversine_km", "map_units", "month_days_in_window",
                 "fwi_percentile", "product_cell_id"):
        assert callable(getattr(geff, name, None)), name
