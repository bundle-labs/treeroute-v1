"""Spec writer's helper (read-only): reads every run-record field the spec names for Tables S3.18-S3.21 and S3.30,
and prints them compactly, so that the spec's selectors are known to exist.

Usage: py -3.9 -I -B s05_check_fields.py
Opens SHAP\\out\\<p>\\lead_0\\<piece>\\ records, SHAP\\rebuild\\<p>\\lead_0\\gates.json, SHAP\\sample\\<p>\\sample_manifest.json,
SHAP\\SAMPLE_REGISTER.txt, SHAP\\logs\\tr_shap_<p>_lead0.log and V\\A\\results.json (b1 keys only). Writes nothing.
"""
import json
import os
import re

SHAP = r"D:\treeroute\analysis\shap_v1"
PROBLEMS = ["pm25", "ndvi", "fire", "defo", "coral"]


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def main():
    reg = {}
    with open(os.path.join(SHAP, "SAMPLE_REGISTER.txt"), encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            kv = dict(t.split("=", 1) for t in line.split()[1:])
            reg[kv["problem"]] = kv
    A = load(os.path.join(SHAP, "verify_v1", "A", "results.json"))
    setup_re = re.compile(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \+\s*([0-9.]+)s\] (\w+) lead 0: (\d+) rows, (\d+) background pairs, (\d+) of (\d+) bank trees used")
    done_re = re.compile(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \+\s*([0-9.]+)s\] treeroute SHAP (\w+) lead 0 done in ([0-9.]+) s \(tree SHAP ([0-9.]+) s\)$")
    for p in PROBLEMS:
        base = os.path.join(SHAP, "out", p, "lead_0")
        PL = load(os.path.join(base, "compare", "per_lead.json"))
        man = load(os.path.join(SHAP, "sample", p, "sample_manifest.json"))
        print("=" * 100)
        print("%s register n=%s sample=%s.. | manifest n=%s regions=%s units=%s frame=%s bg0=%s | per_lead regions=%s rows=%s sample_eq=%s" % (
            p, reg[p]["n"], reg[p]["sample"][:8], man["n"], man["regions_in_sample"], man["units_in_sample"],
            man["frame_rows"], man["background_rows"]["0"], PL["regions"], PL["rows"],
            reg[p]["sample"] == man["sha256"]["sample.parquet"] == PL["sample_sha256"]))
        for m in PL["models"]:
            d = os.path.join(base, m)
            meta = load(os.path.join(d, "meta.json"))
            ex = load(os.path.join(d, "exactness.json")) if os.path.exists(os.path.join(d, "exactness.json")) else None
            rx = load(os.path.join(d, "ridge_shap_exactness.json")) if os.path.exists(os.path.join(d, "ridge_shap_exactness.json")) else None
            g = meta.get("guard", {})
            line = "  %-20s link=%-9s guard.passed=%s add=%.3g/%.3g szero=%s flagged=%s eval=%s pass=%s checks=%s" % (
                m, meta["link"], g.get("passed"), meta["max_abs_additivity_error"],
                meta["max_abs_additivity_error_variable"], meta["structural_zero_violations"],
                meta["rows_flagged_resid"], meta.get("max_abs_evaluator_minus_model"), meta["pass"],
                all(meta["checks_passed"].values()))
            print(line)
            if rx is not None:
                print("      ridge_shap_exactness: stage=%s pass=%s rows=%s bit_equal=%s raw.bit_equal=%s max=%s | rival_shap exactness: pass=%s bit_equal=%s rows=%s max=%s" % (
                    rx["stage"], rx["pass"], rx["rows"], rx["bit_equal_rows"], rx["raw"]["bit_equal_rows"],
                    rx["max_abs_diff"], ex["pass"], ex["bit_equal_rows"], ex["rows"], ex["max_abs_diff"]))
            elif ex is not None:
                raw = ex.get("raw")
                print("      exactness: pass=%s rows=%s bit_equal=%s max=%s raw=%s" % (
                    ex["pass"], ex["rows"], ex["bit_equal_rows"], ex["max_abs_diff"],
                    None if raw is None else (raw["bit_equal_rows"], raw["rows"])))
            if m == "treeroute":
                gj = load(os.path.join(SHAP, "rebuild", p, "lead_0", "gates.json"))
                G = gj["gates"]
                print("      gates:", ", ".join("%s=%s" % (k.split("_")[0], v["pass"]) for k, v in G.items()), "| stopped_at=%s" % gj["stopped_at"])
                e8 = G["E8_predictions"]["values"]
                print("      E8: rows=%s pre_bit=%s arm_bit=%s max_abs_pre=%r max_rel_pre=%r bit_identical=%s rule=%s units=%s" % (
                    e8["rows_checked"], e8["pre_bit_equal"], e8["arm_bit_equal"], e8["max_abs_pre"], e8["max_rel_pre"],
                    e8["bit_identical"], e8["tolerance_rule"][:40], e8["units"]))
                if "E5a_identity_twin" in G:
                    e5a = G["E5a_identity_twin"]["values"]
                    print("      E5a: rows=%s pre_bit=%s arm_bit=%s arm=%s" % (e5a["rows_checked"], e5a["pre_bit_equal"], e5a["arm_bit_equal"], e5a["arm"]))
                e4 = G["E4_donor_rows"]["values"]
                e9 = G["E9_coefficients_reproduce_the_kernel"]["values"]
                e10 = G["E10_exported_trees"]["values"]
                print("      E4 rows=%s hash_eq=%s | E9 fits=%s differ=%s region=%s | E10=%s | E0 ignored=%s | E3m=%s" % (
                    e4["rows"], e4["row_key_hash"][0] == e4["row_key_hash"][1], e9["fits_captured"],
                    e9["fits_whose_X_b_differs_from_the_kernel"], e9["region_proof"], e10,
                    G["E0_ram_preflight"]["values"]["ignored"], "E3m_recorded_path_map" in G))
                print("      meta: pairs=%s tree_shap_seconds=%s trees_used=%s arm=%s kind=%s d8=%s" % (
                    meta["pairs"], meta["tree_shap_seconds"], meta["trees_used"], meta["arm"], meta["kind"], meta.get("d8_licence")))
        # logs
        lf = os.path.join(SHAP, "logs", "tr_shap_%s_lead0.log" % p)
        with open(lf, encoding="utf-8") as f:
            lines = f.read().split("\n")
        setups = [(i + 1, setup_re.match(l)) for i, l in enumerate(lines) if setup_re.match(l)]
        dones = [(i + 1, done_re.match(l)) for i, l in enumerate(lines) if done_re.match(l)]
        last_setup = setups[-1]
        after = [d for d in dones if d[0] > last_setup[0]]
        print("  log: %d lines; last set-up line %d at %s pairs=%s rows=%s; done lines after it: %s" % (
            len([l for l in lines if l]), last_setup[0], last_setup[1].group(1), last_setup[1].group(5), last_setup[1].group(4),
            [(d[0], d[1].group(1), d[1].group(4), d[1].group(5)) for d in after]))
        if p in A["b1"] and A["b1"][p]["status"]["numbers"] != "none":
            run = A["b1"][p].get("run") or A["b1"][p].get("identity")
            print("  A b1 run facts:", {k: run[k] for k in ("log_setup_line_number", "log_done_line_number", "pairs_log", "total_seconds_log", "tree_shap_seconds_log")})
            b1d = os.path.join(base, "treeroute_B1")
            bm = load(os.path.join(b1d, "meta.json"))
            bd = load(os.path.join(b1d, "rows.parquet.done.json"))
            print("  B1 meta pairs=%s tree_shap_seconds=%s | done seconds=%s finished=%s" % (bm["pairs"], bm["tree_shap_seconds"], bd["seconds"], bd["finished"]))


if __name__ == "__main__":
    main()
