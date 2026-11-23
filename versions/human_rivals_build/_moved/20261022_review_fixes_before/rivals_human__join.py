"""The joiner: ONE rival table from the common boards and the human boards (SPEC_HUMAN.txt 1.12; PROT section 4;
PLAN 3.14).

Read-only inputs per run: the common board (board.json, board_lead_<L>.csv, scores/lead_<L>_pooled.csv,
test_labels_opened_rivals_lead_<L>.json) and the human board (human_board.json, human_board_lead_<L>.csv,
scores/lead_<L>_all_pooled.csv, test_labels_opened_human_lead_<L>.json).
Refuses unless, per problem and lead: the same run fingerprint, the same saved test_preds sha256, the same band, the
same "ours" pooled MAE on all rows (each board checked it against the run's score_pooled.csv at lead 0), and the
same common harness sha. No "best rival" line.
"""
# Provenance: SPEC_HUMAN.txt 1.12; PROT section 4 (:295-317); harness.py:2486-2514 (board_lead columns).

import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

import numpy as np
import pandas as pd

from rivals_human import config as C
from rivals_human.common import HumanCtx, load, refuse

SCHEMA = ("problem", "lead", "rival", "rival_type", "kind", "tier", "decides", "rows_basis", "rows", "rows_total",
          "groups", "groups_total", "contrast", "verdict", "d_mean", "d_low", "d_high", "rival_mae",
          "ours_mae_same_rows", "ours_mae_all_rows", "normal_mae_same_rows", "anomaly_r2", "corr2", "hit",
          "calibration_ratio", "timid_win", "guard_passed", "flags", "part")
OWN_HISTORY_WORDS = ("guess_normal", "last5", "damped")
TIER_ORDER = {"P": 0, "L": 0, "X": 1, "A": 2}
JOIN_RULES = [
    "\"ours beats rival X\" is claimed only from a guarded_vs_headline row with decides = True (tier P or L, or a "
    "common rival).",
    "On a covered-rows row the claim is \"on the k% of rows the product covers\" (rows / rows_total).",
    "A tier-A row reads as \"what that extra observation is worth\"; a tier-X row is a labelled statistical "
    "extension; neither decides.",
    "A timid win is printed with its flag; verdicts are not changed.",
    "A tier-L row's BEATS is worded with its own label (for example \"beats the nowcast rule fed old inputs\"), never "
    "as a win over the product itself.",
    "A joint claim (several forms of one method) is YES only when ours BEATS every form; otherwise each verdict is "
    "printed.",
]


def _pooled_mae(path: Path, column: str = "arm__ours") -> float:
    t = pd.read_csv(path)
    sel = t[(t["line"] == "pooled") & (t["column"] == column) & (t["rows_basis"] == "all")]
    if len(sel) != 1:
        refuse("%s has %d pooled lines for %s" % (path, len(sel), column))
    return float(sel["mae"].iloc[0]), int(sel["n"].iloc[0])


def _f(v: Any) -> Any:
    try:
        x = float(v)
        return x if np.isfinite(x) else None
    except (TypeError, ValueError):
        return v


def _bool(v: Any) -> Any:
    """A CSV boolean (True / False / 1 / 0 / 'True') as a bool; empty stays None."""
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return None
    if isinstance(v, str):
        return v.strip().lower() in ("true", "1", "yes")
    return bool(v)


def join(run_folders: Sequence[Any], config: Any = None, part: str = "") -> Path:
    cfg = C.load_config(config)
    LY, H = load(cfg)
    rows: List[Dict[str, Any]] = []
    inputs: List[Path] = []
    notes: List[str] = []
    for rf in run_folders:
        run = H.Run(rf)
        cdir = C.common_board_dir(cfg, run.package, run.name)
        hdir = C.board_dir(cfg, run.package, run.name)
        cb_p, hb_p = cdir / C.COMMON_BOARD_FILE, hdir / C.BOARD_FILE
        for p in (cb_p, hb_p):
            if not p.is_file():
                refuse("%s is missing" % p)
            inputs.append(p)
        cb, hb = C.read_json(cb_p), C.read_json(hb_p)
        if cb["run"]["fingerprint"] != run.fingerprint or hb["run"]["fingerprint"] != run.fingerprint:
            refuse("%s: the boards name fingerprints %s / %s, the run %s" % (run.name, cb["run"]["fingerprint"][:16],
                                                                             hb["run"]["fingerprint"][:16],
                                                                             run.fingerprint[:16]))
        if float(cb["run"]["band"]) != float(hb["run"]["band"]) or float(cb["run"]["band"]) != float(run.band):
            refuse("%s: the bands differ (common %r, human %r, run %r)" % (run.name, cb["run"]["band"],
                                                                         hb["run"]["band"], run.band))
        if cb["harness_code_sha256"] != hb["common_harness_sha256"]:
            refuse("%s: the human board pins harness %s, the common board ran %s"
                   % (run.name, hb["common_harness_sha256"][:16], cb["harness_code_sha256"][:16]))
        if hb["common_board"]["sha256"] != H.sha256_file(cb_p):
            refuse("%s: the common board.json changed since the human board's init" % run.name)
        registry = C.load_registry(cfg, run.package)
        for L in run.leads:
            ctl = cdir / (C.COMMON_TEST_LABELS_OPENED % L)
            htl = hdir / (C.TEST_LABELS_OPENED % L)
            cbl = cdir / (C.COMMON_BOARD_LEAD_CSV % L)
            hbl = hdir / (C.BOARD_LEAD_CSV % L)
            cpool = cdir / C.COMMON_SCORES_DIR / ("lead_%d_pooled.csv" % L)
            hpool = hdir / C.SCORES_DIR / ("lead_%d_all_pooled.csv" % L)
            missing = [str(p) for p in (ctl, cbl, cpool) if not p.is_file()]
            if missing:
                refuse("%s lead %d: the common board is not scored (%s)" % (run.name, L, missing[:2]))
            inputs += [ctl, cbl, cpool]
            c_sha = C.read_json(ctl)["test_preds_sha256"]
            human_scored = hbl.is_file()
            if human_scored:
                for p in (htl, hpool):
                    if not p.is_file():
                        refuse("%s lead %d: %s is missing" % (run.name, L, p))
                inputs += [htl, hbl, hpool]
                h_sha = C.read_json(htl)["test_preds_sha256"]
                if c_sha != h_sha:
                    refuse("%s lead %d: the boards scored different saved test rows (sha %s vs %s)"
                           % (run.name, L, c_sha[:16], h_sha[:16]))
            c_ours, c_n = _pooled_mae(cpool)
            if human_scored:
                h_ours, h_n = _pooled_mae(hpool)
                if not (np.isclose(c_ours, h_ours, rtol=1e-12, atol=0.0) and c_n == h_n):
                    refuse("%s lead %d: our pooled MAE differs (common %r on %d rows, human %r on %d rows)"
                           % (run.name, L, c_ours, c_n, h_ours, h_n))
            prob = run.package
            rows.append({"problem": prob, "lead": L, "rival": "ours (headline)", "rival_type": "ours", "kind": "-",
                         "tier": "-", "decides": False, "rows_basis": "all", "rows": c_n, "rows_total": c_n,
                         "rival_mae": c_ours, "ours_mae_all_rows": c_ours, "part": part})
            ct = pd.read_csv(cbl)
            for _, r in ct.iterrows():
                rows.append({"problem": prob, "lead": L, "rival": r["learner"], "rival_type": "common",
                             "kind": "learner", "tier": "-", "decides": bool(r["decides"]), "rows_basis": "all",
                             "rows": c_n, "rows_total": c_n, "groups": _f(r.get("n_groups")),
                             "contrast": r["contrast"], "verdict": r["ours_beats_rival"], "d_mean": _f(r["d_mean"]),
                             "d_low": _f(r["d_low"]), "d_high": _f(r["d_high"]), "rival_mae": _f(r["rival_mae"]),
                             "ours_mae_same_rows": _f(r["ours_mae"]), "ours_mae_all_rows": c_ours,
                             "corr2": _f(r.get("rival_corr2")), "hit": _f(r.get("rival_hit")),
                             "calibration_ratio": _f(r.get("rival_calibration_ratio")),
                             "timid_win": bool(r["timid_win"]), "guard_passed": bool(r["guard_passed"]),
                             "flags": "", "part": part})
            if not human_scored:
                rows.append({"problem": prob, "lead": L, "rival": "(human board not scored)", "rival_type": "human",
                             "verdict": "-", "flags": "not scored yet", "part": part})
                continue
            ht = pd.read_csv(hbl)
            human = ht[ht["rival_type"] == "human"] if len(ht) else ht
            if not len(human):
                reasons = sorted(set(C.lead_tiers(r)[L]["reason"] for r in registry["rivals"]
                                     if C.lead_tiers(r).get(L, {}).get("tier") == C.TIER_NONE))
                from rivals_human.board import no_rival_reason
                rows.append({"problem": prob, "lead": L, "rival": "no human rival", "rival_type": "human",
                             "verdict": "-", "flags": "no human rival: %s" % (no_rival_reason(registry, L)
                                                                             or "; ".join(reasons)), "part": part})
            hr = []
            for _, r in human.iterrows():
                d = {k: _f(r.get(k)) for k in SCHEMA if k in r.index}
                d.update(problem=prob, lead=L, rival_type="human", rows_basis="covered",
                         rows_total=_f(r.get("rows_total")), groups_total=_f(r.get("groups_total")),
                         decides=_bool(r.get("decides")), timid_win=_bool(r.get("timid_win")),
                         guard_passed=_bool(r.get("guard_passed")),
                         flags=r.get("flags") if isinstance(r.get("flags"), str) else "", part=part)
                if isinstance(r.get("label"), str) and r.get("label") and str(r.get("verdict")) == "BEATS":
                    d["verdict"] = "BEATS (%s)" % r["label"]
                d["_order"] = TIER_ORDER.get(str(r.get("tier")), 3)
                hr.append(d)
            hr.sort(key=lambda d: d["_order"])
            for d in hr:
                d.pop("_order", None)
            rows.extend(hr)
            for jc in registry.get("joint_claims") or []:
                sub = human[(human["rival"].isin(jc["rivals"])) & (human["contrast"] == "guarded_vs_headline")]
                if len(sub) == len(jc["rivals"]):
                    yes = bool((sub["verdict"] == "BEATS").all())
                    notes.append("%s lead %d: %s: %s" % (prob, L, jc["name"], "YES" if yes else
                                                         "NO (each form's verdict is printed)"))
            refs = ht[ht["rival_type"] == "reference"] if len(ht) else ht
            own = [r for _, r in refs.iterrows() if any(w in str(r["rival"]) for w in OWN_HISTORY_WORDS)]
            ref = [r for _, r in refs.iterrows() if not any(w in str(r["rival"]) for w in OWN_HISTORY_WORDS)]
            for kind_name, group in (("own_history", own), ("reference", ref)):
                for r in group:
                    d = {k: _f(r.get(k)) for k in SCHEMA if k in r.index}
                    d.update(problem=prob, lead=L, rival_type=kind_name, kind="-", tier="-", decides=False,
                             rows_basis=r.get("rows_basis", "all"), part=part,
                             flags=r.get("flags") if isinstance(r.get("flags"), str) else "")
                    rows.append(d)
    table = pd.DataFrame(rows)
    for c in SCHEMA:
        if c not in table.columns:
            table[c] = None
    table = table[list(SCHEMA)]
    stamp = H.utc_stamp()
    out = Path(cfg["table_root"]) / stamp
    ctx = HumanCtx(cfg, out, "join")
    ctx.mkdir(out)
    ctx.replace_bytes(out / C.TABLE_CSV, table.to_csv(index=False, lineterminator="\n").encode("utf-8"))
    md = ["# One rival table", "", "Runs: %s" % ", ".join(str(Path(r).name) for r in run_folders), "",
          "| " + " | ".join(SCHEMA) + " |", "|" + "---|" * len(SCHEMA)]
    for _, r in table.iterrows():
        md.append("| " + " | ".join("" if (v is None or (isinstance(v, float) and not np.isfinite(v))) else
                                    ("%.6g" % v if isinstance(v, float) else str(v)) for v in r.tolist()) + " |")
    md += ["", "Joint claims:"] + ["- " + n for n in notes] + ["", "Reading rules:"] + ["- " + x for x in JOIN_RULES]
    ctx.replace_bytes(out / C.TABLE_MD, ("\n".join(md) + "\n").encode("utf-8"))
    lines = ["%s  %s" % (H.sha256_file(p), str(p).replace("\\", "/")) for p in inputs]
    ctx.replace_bytes(out / C.TABLE_INPUTS, ("\n".join(lines) + "\n").encode("utf-8"))
    return out
