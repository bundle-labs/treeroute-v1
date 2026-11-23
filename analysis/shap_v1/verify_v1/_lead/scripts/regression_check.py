"""Check that every correction made in versions 1 and 2 of report.md is still present in a new version.

Usage: py -3.12 -X utf8 -I regression_check.py <new report text>
Each phrase stands for one correction or fix; a missing phrase is printed as MISSING.
"""
import sys

PHRASES = [
    ("v1/v3 re-read window", "18:34:26\nto 18:49:41"),
    ("tables.md never written", "`work\\tables.md` was never written"),
    ("per_lead.json holds statistics", "which also holds statistics"),
    ("section 14 earlier reads", "lines 829-831 and 936-938"),
    ("logs scope", "hold the\n   files outside V"),
    ("tau-b fire feature", "0.721 [0.640, 0.752]"),
    ("top20u fire variable", "0.391 [0.246, 0.499]"),
    ("spearman J ndvi", "0.844\n   [0.833, 0.851]"),
    ("tau-b ndvi variable", "0.774 [0.757, 0.788]"),
    ("b1_summary three digits", "carries three of these digits"),
    ("3,953", "3,953 rounded table entries"),
    ("14,412 of the 14,424", "14,412 of the 14,424 B1 keys"),
    ("2,000 replicates qualified", "not for coral's own-history"),
    ("exceptions besides C15", "except in three groups"),
    ("sign agreement touches S3.13", "does touch what S3.13 prints"),
    ("empty family withdrawn", "it is withdrawn"),
    ("coral median rival", "none for coral"),
    ("family TVD both levels", "the words favour showing it at both levels"),
    ("test-set columns", "x__hist_mean_all"),
    ("inspection scripts", "`a04_checks.py` (A) and `b_inspect3.py` (B)"),
    ("pre column", "the key, flag and `pre` columns"),
    ("largest not most", "is the largest family share under B1"),
    ("latent compare_shap", "np.argsort(-Iz)"),
    ("latent reconcile 1", "`classify()`"),
    ("latent reconcile 2", "AOd and BOd"),
    ("records compared by script", "compare_b1_records.py"),
    ("19 field pairs", "all 19 pairs of A and B fields are equal"),
    ("blindness label", "not a rule breach but a leak path"),
    ("blindness -I -B fix", "use `-I -B` for one-line checks too"),
    ("blindness listing 18:33", "By its own listing of SHAP outside V at 18:33"),
    ("transcripts scope", "the spec writer's, A's and B's in full"),
    ("BARDL 93 of 96 of J", "93 of the 96 variables of J (it reads three variables, nine"),
    ("BARDL largest RBO 0.95", "p 0.95 0.082"),
    ("non-BARDL RBO 2.3e-5", "by at most 2.3e-5"),
    ("skeptic 1e-12 note", "no collation dependence above 1e-12"),
    ("facts checker official main row", "official `AW4_main_row.json` files (A = B = official"),
    ("route b", "a corrected comparison: a new script"),
    ("main table consequence", "under the main-text table"),
    ("fewer than 2,000", "fewer than 2,000 finite draws"),
    ("percentile helper", "percentile_ci"),
    ("labelled 0", "(no own-history input)"),
    ("median label", "\"median of the rivals\""),
    ("PM2.5 note", "its interval is asymmetric"),
    ("point 5 consequences", "asymmetric the other way"),
    ("owner question C10", "Owner question C10 (not the spec's open"),
    ("C10 alternative", "leave the read to the PROTOCOL.md section 14 record only"),
    ("B-05 moot", "B-05 no longer arises"),
    ("A6 scope", "replace the reconciler's section-6 pair table"),
    ("A7 both rounds", "| 2 | findings | 10:"),
    ("A2 kept", "### A2. Status counts per group"),
    ("A3 kept", "### A3. The test-set records"),
]


def main():
    with open(sys.argv[1], encoding="utf-8") as f:
        t = f.read()
    flat = " ".join(t.split())
    missing = 0
    for name, ph in PHRASES:
        ok = ph in t or " ".join(ph.split()) in flat
        if not ok:
            missing += 1
        print("%-34s %s" % (name, "ok" if ok else "MISSING"))
    print("missing:", missing, "of", len(PHRASES))


if __name__ == "__main__":
    main()
