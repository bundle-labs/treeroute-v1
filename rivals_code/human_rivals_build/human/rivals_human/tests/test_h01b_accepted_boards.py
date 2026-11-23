"""T-H01b (ruling AG, Part 613): a common board made under an OLDER common harness is accepted only when the config
lists that harness with the owner's written reason; the imported harness must still equal the pin; malformed or
self-listing entries refuse at config load."""

import pytest

from rivals_human.tests import hooks as HK


def _with_accepted(cfg_path, accepted):
    import yaml
    data = yaml.safe_load(open(cfg_path, encoding="utf-8"))
    data["common_harness_accepted_boards"] = accepted
    with open(cfg_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f)
    return cfg_path


def test_an_accepted_older_board_passes_with_its_reason_and_others_refuse(tmp_path):
    board_root = tmp_path / "_out_common"
    cfg = HK.minimal_config(tmp_path, common_board_root=board_root)
    _with_accepted(cfg, {HK.OLD_COMMON_SHA: "ruling AG: Part 608 changed only the open-bound read"})
    LY, H = HK.common_modules(cfg)
    C = HK.tool("common")
    conf = HK.load_config(cfg)
    bp = board_root / "pkg" / "run1" / "board.json"
    HK.write_json(bp, {"harness_code_sha256": HK.OLD_COMMON_SHA, "run": {"name": "run1", "legal": [0.0, 1.0]}})
    rec = C.check_common_board(H, conf, "pkg", "run1", True)
    assert rec["harness_accepted_as"].startswith("ruling AG")
    # the premise of AG5: an accepted older board must have a bounded legal range (open bound or none: refuse)
    for legal in ([0.0, None], None):
        HK.write_json(bp, {"harness_code_sha256": HK.OLD_COMMON_SHA, "run": {"name": "run1", "legal": legal}})
        HK.refuses(("bounded",), C.check_common_board, H, conf, "pkg", "run1", True)
    HK.write_json(bp, {"harness_code_sha256": HK.COMMON_SHA, "run": {"name": "run1"}})
    assert C.check_common_board(H, conf, "pkg", "run1", True)["harness_accepted_as"] is None
    HK.write_json(bp, {"harness_code_sha256": "e" * 64, "run": {"name": "run1"}})
    HK.refuses(("harness", "pinned"), C.check_common_board, H, conf, "pkg", "run1", True)


def test_without_the_entry_an_older_board_refuses(tmp_path):
    board_root = tmp_path / "_out_common"
    cfg = HK.minimal_config(tmp_path, common_board_root=board_root)
    LY, H = HK.common_modules(cfg)
    C = HK.tool("common")
    conf = HK.load_config(cfg)
    HK.write_json(board_root / "pkg" / "run1" / "board.json", {"harness_code_sha256": HK.OLD_COMMON_SHA, "run": {"name": "run1", "legal": [0.0, 1.0]}})
    HK.refuses(("harness", "pinned"), C.check_common_board, H, conf, "pkg", "run1", True)


@pytest.mark.parametrize("accepted, words", [
    ({"abc": "reason"}, ("64 hex",)),
    ({HK.COMMON_SHA: "reason"}, ("pin itself",)),
    ({HK.OLD_COMMON_SHA: ""}, ("written reason",)),
    ({HK.OLD_COMMON_SHA: True}, ("written reason",)),
    (["not", "a", "mapping"], ("must map",)),
])
def test_malformed_entries_refuse_at_config_load(tmp_path, accepted, words):
    cfg = _with_accepted(HK.minimal_config(tmp_path), accepted)
    HK.refuses(words, HK.load_config, cfg)


def test_the_imported_harness_must_still_equal_the_pin_even_if_listed(tmp_path):
    """Listing the CURRENT harness as 'accepted' under a different pin does not let the tool import it."""
    cfg = _with_accepted(HK.minimal_config(tmp_path, common_sha=HK.OLD_COMMON_SHA), {HK.COMMON_SHA: "not allowed"})
    C = HK.tool("common")
    HK.refuses(("pinned", "sha"), C.load, str(cfg))
