"""Write STAGE/paper/PAPER_FACTS.md: the earlier writers' staged sheet plus facts A9-A25 (writer s3).

Usage: py -3.9 -I -B make_facts.py
Starts from work/paper__PAPER_FACTS.md.base (the glossary writer's staged copy, SHA-256 8206f9ef...), inserts the
facts behind every number of Supplement S3.13's prose after A8 (section 9), each with its status "final, post hoc
(Part 628)", its source path and selector and, for a computed number, the value printed in the paper (formatted once,
by s3lib, from the stored value) with the stored value beside it; and extends the sheet's "Revised 2026-11-17
(S3.13 write-up)" paragraph. UTF-8 without BOM, LF, as the sheet. Writes only STAGE/paper/PAPER_FACTS.md.
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("s3lib", os.path.join(HERE, "s3lib.py"))
L = importlib.util.module_from_spec(spec)
spec.loader.exec_module(L)

BASE = os.path.join(HERE, "work", "paper__PAPER_FACTS.md.base")
BASE_SHA = "8206f9ef45fa9111d412a311679d2c726488999faa2c90b97d53d4a730342403"
DST = os.path.join(L.STAGE, "paper", "PAPER_FACTS.md")
A8_LAST = ("  - Caveats (added 2026-10-27, S5 revision; Parts 603-604; D:/treeroute/analysis/guidance/RESULT.txt and its "
           "skeptic addendum;")
REV_ANCHOR = " Copy of this sheet before the S3.13 write-up, 2026-11-17: paper/draft/_snapshots/@@SNAP@@/."
REV_ADD = (" Section 9 gains A9-A25 (final, post hoc (Part 628)): the facts behind every number of Supplement S3.13's "
           "prose, each with its source path and selector and, for a computed number, the value as the paper prints "
           "it beside the stored value.")
CJ = "paper/supp_build/s3_13/reconcile/cells.json"
TA = "paper/supp_build/s3_13/reconcile/tables_agreed.md"
SH = "D:/treeroute/analysis/shap_v1"


def r(x):
    return repr(x)


def trio(stored):
    return "%s [%s, %s]" % tuple(r(x) for x in stored)


def main():
    with open(BASE, "rb") as f:
        raw = f.read()
    if L.sha256_bytes(raw) != BASE_SHA:
        raise SystemExit("base copy changed")
    text = raw.decode("utf-8")
    if "\r" in text or raw.startswith(b"\xef\xbb\xbf"):
        raise SystemExit("base has CR or BOM")
    t, s, c = L.tokens()
    reg = {x["problem"]: x["time"] for x in s["register"]}
    pl = s["samples"]["per_lead"]
    regions = s["samples"]["regions"]
    locs = s["samples"]["locations"]
    frame = {p: c.one("S3.19", ln, row=p, column="frame_rows", part="value")["stored"][0]
             for p, ln in zip(L.PROBLEMS, (75, 76, 77, 78, 79))}
    lc = s["lead_check"]
    # exactness values (Tables S3.20 and S3.21)
    e8 = {}
    for p in L.PROBLEMS:
        e8[p] = (c.one("S3.21", 143, row="E8", column=p, part="bit_equal")["stored"][0],
                 c.one("S3.21", 143, row="E8", column=p, part="rows")["stored"][0])
    mr = {p: c.one("S3.21", 143, row="E8", column=p, part="max_rel")["stored"][0] for p in ("fire", "coral")}
    mr_p = {p: c.one("S3.21", 143, row="E8", column=p, part="max_rel")["printed"] for p in ("fire", "coral")}
    e5a = {p: (c.one("S3.21", 139, row="E5a", column=p, part="bit_equal")["stored"][0],
               c.one("S3.21", 139, row="E5a", column=p, part="rows")["stored"][0]) for p in ("fire", "coral")}
    szv = [e for e in c.entries if e["table"] == "S3.20" and e.get("column") == "s_zero_violations"]
    assert len(szv) == 25 and all(e["stored"] == [0] for e in szv), len(szv)  # 4 + 5 + 5 + 5 + 6 models
    rival_rows = [e for e in c.entries if e["table"] == "S3.20" and e.get("column") == "bit_identical"
                  and e.get("part") == "pre" and not e["row"].endswith(":treeroute")]
    rival_checked = {e["row"]: c.one("S3.20", e["line"], row=e["row"], column="rows_checked", part="value")["stored"][0]
                     for e in rival_rows}
    assert all(e["stored"][0] == rival_checked[e["row"]] for e in rival_rows), "a rival is not bit-identical"
    # main row and per-rival own-history shares (Table S3.22)
    ohr = {}
    for p in ("pm25", "ndvi", "defo"):
        ohr[p] = {e["part"]: (e["printed"], e["stored"][0]) for e in c.find("S3.22", 165, row="own_history_per_rival",
                                                                         column=p)}
    nzc = {e["column"]: e["stored"][0] for e in c.find("S3.27", 659, row="rows", part="count")}
    b1top = {p: c.one("S3.29", 727, row="top3", column=p, part="share_1") for p in ("pm25", "ndvi", "fire")}
    ident = {k: c.one("S3.30", ln, row=k, column="result", part=part)["stored"][0]
             for k, ln, part in (("max_abs_diff_phi", 777, "value"), ("max_abs_diff_phiv", 778, "value"))}
    idrows = [c.one("S3.30", 779, row="rows", column="result", part=x)["stored"][0] for x in ("main", "b1")]
    idpl = [c.one("S3.30", 780, row="players", column="result", part=x)["stored"][0] for x in ("main", "b1")]
    idvar = [c.one("S3.30", 781, row="variables", column="result", part=x)["stored"][0] for x in ("main", "b1")]
    defo_pairs = c.one("S3.30", 771, row="defo", column="pairs", part="value")["stored"][0]
    thin = {}
    for ln in (354, 355, 356):
        es = c.find("S3.25", ln, column="sign_agreement_top10")
        d = {e["part"]: e for e in es}
        thin[d["n_finite"]["row"]] = (d["n_finite"]["stored"][0], d["ci_low"]["printed"], d["ci_high"]["printed"],
                                      d["value"]["printed"], d["signs"]["printed"])
    F = []
    F.append(
        "- **A9 (final, post hoc (Part 628)). The SHAP comparison's timeline** (local time, as the rulings file, the "
        "SHAP protocol and its sample register record it). Ruling AW, 2026-11-12 (AW1-AW5): a SHAP analysis of "
        "treeroute v1's headline runs of all five problems and of every rival it can be run on, a table of how the "
        "models disagree, several agreement statistics (Spearman's rank correlation among them) with a bootstrap over "
        "regions, and a fixed sample of 1,000 test rows per problem and lead in scope; it amends outline decision O3 as "
        "confirmed by AT17 (e), which had left SHAP out of v1 and offered a labelled post hoc analysis if a reviewer "
        "asked. Ruling AY, 2026-11-13: AY1 scope (i), the nowcast of each problem; AY2 the recorded path map (gate "
        "E3m; protocol decision D14 (b)); AY3 a true relative tolerance of 1e-12 on arcsine arms only (decision D8), "
        "with which the coral pilot had already run. Ruling AZ1, 2026-11-14 (answered at about 04:35, before the ridge "
        "pieces of 04:46-04:48): the burned-fraction comparison of 2026-11-13 21:18 (four models, without Ridge) had "
        "not been read before Ridge was added. Ruling BA, 2026-11-15 (answered at about 19:45 for BA1 and BA2 and at "
        "about 22:50 for BA3), when no statistic of the PM2.5, NDVI, burned-fraction or forest-loss comparisons had "
        "been read. Ruling BB, 2026-11-16 (answered at 20:59), after the independent re-computation. Protocol: version "
        "1 (2026-11-12) was written before any SHAP value was computed on a real data row; the v2 and v3 smoke tests "
        "computed SHAP values on %d-%d rows of the real coral bleaching headline run (2 regions) and on synthetic "
        "engine worlds, as plumbing, with no statistic read as a result; sections 3 (sample) and 8 (statistics) were "
        "frozen when the first sample was registered; the later checks of the ridge and BARDL loaders computed SHAP "
        "values on rows of registered samples (ridge: the registered burned-fraction and coral samples; BARDL: 29 rows "
        "of the NDVI smoke sample, which equals the NDVI sample registered on 2026-11-14), as plumbing, and no agreement "
        "statistic was read from them (the BARDL smoke's family-share check value was not read). Sample registrations "
        "(SAMPLE_REGISTER.txt): coral %s, fire %s, PM2.5 %s, defo %s, NDVI %s. Runs: the coral pilot 2026-11-12 23:49 "
        "to 2026-11-13 00:06; the last nowcast comparison (NDVI, five models) 2026-11-15 19:11:39; the B1 command "
        "2026-11-15 23:06:16 to 2026-11-16 08:14:14; the independent re-computation (round 14) 2026-11-16 17:09 to "
        "about 19:20. So the runs went from 2026-11-12 to 2026-11-15, the B1 runs from 2026-11-15 to 2026-11-16 and "
        "the re-computation ran on 2026-11-16 (S3.0's index: 2026-11-12 to 2026-11-16). Sources: "
        "engine/OWNER_RULINGS_2026-10-06.md sections AW, AY, AZ, BA and BB; %s/PROTOCOL.md (SHA-256 32daa77b), "
        "preamble and sections 1, 3 and 14 (entries of 2026-11-14, of 2026-11-14 and 2026-11-15, and of 2026-11-16); "
        "%s/SAMPLE_REGISTER.txt lines 1-5 (time stamps)."
        % (s["smoke_rows"][0], s["smoke_rows"][1], reg["coral"], reg["fire"], reg["pm25"], reg["defo"], reg["ndvi"],
           SH, SH))
    F.append(
        "- **A10 (final, post hoc (Part 628)). The SHAP comparison's fixed settings.** N = %s explained test rows per "
        "problem, the same rows for every model (ruling AW5; per_lead.json rows = %d and SAMPLE_REGISTER.txt n=1000 on "
        "all five problems). B = %s paired bootstrap draws of regions with replacement, the same draws for every model, "
        "from the SHA-256 generator with the salt shap_v1|AW4|<problem>|0 (per_lead.json draws = %d and salt on all "
        "five problems); percentile 95%% intervals, each with its number of finite draws; no BCa and no p-value; with "
        "37-133 regions the intervals may under-cover (protocol section 8). J, per level: the players to which some "
        "model gives more than 1e-12 of its total mean |phi| (per_lead.json j_rule \"%s\"). Pair statistics, at the "
        "feature and the variable level over J: Spearman over J and over the union of the two top-20 sets; Kendall's "
        "tau-b; Jaccard of the top-5 and top-10 sets, and of the top-20 sets when J has %s or more players; RBO at "
        "p = 0.9 and 0.95; the total-variation distances between the shares and between the family shares; the sign "
        "agreement on the union of the two top-10 sets. Main set: Kendall's W with the tie correction and the mean "
        "pairwise Spearman; each model's stability under region resampling; the main-text row with treeroute v1's and "
        "the consensus's top 3. Two levels (feature, variable) and five families (own history, global indices, local "
        "drivers, context and calendar, the seasonal normal). Stop rules: S-ADD |base + sum phi + R - eta| <= 1e-9 at "
        "both levels; S-EVAL within 1e-9 (forest loss's region router: within the float32 summation bound); S-ZERO: a "
        "player whose columns equal the explained row's on every background row gets exactly 0, in every model, at both "
        "levels (so under B2 the columns that take the explained row's value on every background row, such as static "
        "columns, latitude, the month and the seasonal normal on the gridded problems, are exactly 0); D8 "
        "(ruling AY3): a relative difference of at most 1e-12 on arcsine arms only. Link space only (decision D4). "
        "Sources: %s/PROTOCOL.md sections 3, 5, 8 and 12; %s/out/<problem>/lead_0/compare/per_lead.json keys rows, "
        "draws, salt and j_rule (read 2026-11-17); rulings AW5 and AY3."
        % (t["N"], pl["pm25"]["rows"], t["B"], pl["pm25"]["draws"], pl["pm25"]["j_rule"], t["J200"], SH, SH))
    F.append(
        "- **A11 (final, post hoc (Part 628)). Coral bleaching's B2 background.** Each sample row's background is its "
        "survey visit's saved router fit rows, the neighbour router's pool of earlier nearby survey visits (Section "
        "2.4: the 50 visits most similar in tree inputs among the 150 nearest earlier training visits; M28, K19): 50 "
        "per sample row, %s background pairs in all (Table S3.19). Of the %s, %s are earlier visits at the explained "
        "visit's own reef site, in %s of the %s sample rows, and %s is dated on or after the explained visit. The "
        "protocol's wording \"other sites' visits\" (PROTOCOL.md section 5, lines 375 and 381-382, and section 10, "
        "\"Not claimed\") is therefore inexact; the paper says \"a pool of earlier nearby survey visits\". Sources: "
        "paper/supp_build/s3_13/_brief/lead_checks/verify_v5_claims_out.txt line 33 (from "
        "paper/supp_build/s3_13/_brief/lead_checks/verify_v5_claims.py, a read-only count over "
        "%s/out/coral/lead_0/treeroute/background_keys.parquet against rows.parquet; the reef site is a survey visit "
        "key's text before \"|\"); background pairs %s/out/coral/lead_0/treeroute/meta.json pairs = %d and background "
        "rows %s/sample/coral/sample_manifest.json background_rows[\"0\"].min = 50 (%s, Table S3.19, line 79 of %s)."
        % (t["CORAL_PAIRS"], t["CORAL_PAIRS"], t["CORAL_SAME"], t["CORAL_ROWS_SAME"], t["N"], L.WORDS[lc["later"]], SH, SH,
           lc["pairs"], SH, CJ, TA))
    F.append(
        "- **A12 (final, post hoc (Part 628)). Exactness checks and rebuild gates.** treeroute v1's fitted trees were "
        "not kept (the engine deletes its checkpoint folders when a run finishes), so each problem's tree bank, with "
        "its correctors and placebos, and the sampled locations' routers were rebuilt with the run's own engine "
        "snapshot (gated by its code hash, E1), which read the run's adoption (arm and penalty point) and guard outcome "
        "(never recomputed) and opened no test label; the random forests were rebuilt with the boards' own rf_forest. S-EXACT "
        "(Table S3.20): every rival bit-identical on every checked row (every test row of its saved predictions; "
        "rival_shap.py checks the pre-clip column only); treeroute v1 bit-identical on PM2.5 (%s of %s rows), NDVI "
        "(%s of %s) and forest loss (%s of %s); its arcsine arms on burned fraction %s of %s rows bit-identical and the "
        "rest within D8 (largest relative difference %s, stored %s), and on coral bleaching %s of %s (%s, stored %s), "
        "licensed by gate E5a (%s of %s and %s of %s rows bit-identical). S-ADD, S-EVAL, S-RESID and S-ZERO passed "
        "for every model, with 0 S-ZERO violations (all %d models). E5 (bank fingerprint, SHA-256 over every node "
        "array of every tree, corrector and placebo): pass false on all five problems, informational (\"cause not "
        "established (answers decide: E5a, E8, E10)\"). E3a on coral bleaching: static_files_sha256 4f53cda18c2baa0c "
        "on both sides, the start of the SHA-256 of an empty list (\"[]\"), and target_files_sha256 listed under "
        "not_before_read. E8 on coral bleaching: rows_checked %s, every test survey visit, not only the %s sampled. "
        "E10: as Table S3.21 states it. Sources: %s/rebuild/<problem>/lead_0/gates.json (gates.E5_bank_fingerprint.pass "
        "and values.role; gates.E8_predictions.values; gates.E5a_identity_twin.values; coral "
        "gates.E3a_inputs_before_read.values); %s/out/<problem>/lead_0/<model>/exactness.json, "
        "ridge_shap_exactness.json and meta.json; %s (Tables S3.20 and S3.21); SHAP protocol sections 4 and 11."
        % (L.intc(e8["pm25"][0]), L.intc(e8["pm25"][1]), L.intc(e8["ndvi"][0]), L.intc(e8["ndvi"][1]),
           L.intc(e8["defo"][0]), L.intc(e8["defo"][1]), L.intc(e8["fire"][0]), L.intc(e8["fire"][1]),
           mr_p["fire"], r(mr["fire"]), L.intc(e8["coral"][0]), L.intc(e8["coral"][1]), mr_p["coral"],
           r(mr["coral"]), L.intc(e5a["fire"][0]), L.intc(e5a["fire"][1]), L.intc(e5a["coral"][0]),
           L.intc(e5a["coral"][1]), len(szv), t["CORAL_E8"], t["N"], SH, SH, CJ))
    F.append(
        "- **A13 (final, post hoc (Part 628)). NDVI's merged router-context columns.** %s router-context columns of "
        "NDVI, c__ctx:top5:V01_mean_temp_C, c__ctx:top5:V07_total_ref_ET_mm_lag1, c__ctx:top5:era5l_d2m, "
        "c__ctx:top5:era5l_slhf_lag1 and c__ctx:top5:sph_kgkg_lag6, are exact copies of the tree inputs "
        "x__V01_mean_temp_C, x__V07_total_ref_ET_mm_lag1, x__era5l_d2m, x__era5l_slhf_lag1 and x__sph_kgkg_lag6 and "
        "are the same players (duplicates_merged: %d in the meta.json of NDVI's treeroute, treeroute_B1, Ridge, random "
        "forest and LightGBM pieces; 0 for BARDL and for every piece of the other four problems); per_lead.json puts "
        "them in local drivers, so NDVI's context-and-calendar family holds only calendar, whose four harmonics "
        "(c__ctx:cos1, cos2, sin1, sin2) are structural zeros under B2 (Table S3.19). Sources: "
        "paper/supp_build/s3_13/_brief/lead_checks/verify_v5_claims_out.txt lines 1-30 "
        "(%s/out/<problem>/lead_0/<model>/meta.json duplicates_merged); paper/supp_build/s3_13/_brief/fix_order_v5.md "
        "V5-1; SHAP protocol sections 5 and 8 (duplicates)."
        % (t["NDVI_DUPS"].capitalize(), lc["dups"][("ndvi", "treeroute")], SH))
    F.append(
        "- **A14 (final, post hoc (Part 628)). The registered samples.** %s test rows per problem, drawn from the frame "
        "(the labelled test rows that every compared model covers) by the SHA-256 generator "
        "shap_v1|AW5|<problem>|<what>|<key>, stratified by region x test year. PM2.5: frame %s rows, %d regions, %s "
        "locations (%d per region). NDVI: frame %s rows, %d regions, %s locations (%d per region). Burned fraction: "
        "frame %s rows, %d regions, %s locations (%d per region). Forest loss: frame %s rows, %d regions, %s locations "
        "(%d per region; all 42 regions, decision D10's default). Coral bleaching: frame %s rows, %d regions, %s survey "
        "visits (the engine's unit there). Regions per problem: %s to %s. On the gridded problems "
        "ceil(N / (G x Y)) locations per region, with Y = 4 test years, one row per location and test year, trimmed to "
        "exactly N by dropping rows in reverse hash order; on coral bleaching an equal allocation per region, capped by "
        "availability, with the rows left over given in turn to the regions that still have rows, the test years in "
        "turn. Each sample and its background files are registered with their SHA-256 in SAMPLE_REGISTER.txt, and every "
        "SHAP script refuses a sample or background file whose hash is not the registered one. Sources: "
        "%s/SAMPLE_REGISTER.txt (n); %s/sample/<problem>/sample_manifest.json (frame_rows, regions_in_sample, "
        "units_in_sample), as %s lists them (Table S3.19, lines 75-79 of %s); per_lead.json regions; SHAP protocol "
        "section 3."
        % (t["N"], L.intc(frame["pm25"]), regions["pm25"], L.intc(locs["pm25"]), locs["pm25"] // regions["pm25"],
           L.intc(frame["ndvi"]), regions["ndvi"], L.intc(locs["ndvi"]), locs["ndvi"] // regions["ndvi"],
           L.intc(frame["fire"]), regions["fire"], L.intc(locs["fire"]), locs["fire"] // regions["fire"],
           L.intc(frame["defo"]), regions["defo"], L.intc(locs["defo"]), locs["defo"] // regions["defo"],
           L.intc(frame["coral"]), regions["coral"], L.intc(locs["coral"]), t["REG_MIN"], t["REG_MAX"], SH, SH, CJ,
           TA))
    bd = s["bardl"]
    F.append(
        "- **A15 (final, post hoc (Part 628)). BARDL in the NDVI comparison.** BARDL, the published NDVI rival, reads "
        "%d input columns of %d variables by design (ruling AB: published inputs only): x__hist_last_1 to "
        "x__hist_last_3 (%d lags of the location's own label; variable hist_last), x__V02_total_precip_mm and its lags "
        "1 and 2 (total_precip_mm), and x__V30_soil_moisture_pct and its lags 1 and 2 (soil_moisture_pct), plus "
        "normal, its offset, which is exactly 0 under B2. It has %d nonzero variables and %d nonzero players "
        "(per_lead.json variable.nonzero_players.rival_bardl_h1 and feature.nonzero_players.rival_bardl_h1) against a "
        "J of %s variables and %s players (variable.active, feature.active), so it gives exactly 0 to %s of the %s "
        "variables and %s of the %s players. It shares treeroute v1's identity link and passed its skill guard at the "
        "nowcast, so it is in the NDVI main set (ruling BA1). Its loader (scripts/bardl_shap.py) and the ridge loader "
        "outside coral bleaching (scripts/ridge_shap.py) were added after the freeze, with no change to protocol "
        "sections 3 and 8. Sources: SHAP protocol preamble and sections 4.2, 5, 7, 10 and 14; "
        "%s/out/ndvi/lead_0/compare/per_lead.json, as %s lists it (Table S3.24, lines 314 and 330, and Table S3.19, "
        "line 76, of %s); Table S3.24 note ‡."
        % (bd["nonzero_players"], bd["nonzero_variables"], len(bd["hist_lags"]), bd["nonzero_variables"],
           bd["nonzero_players"], t["NDVI_JV"], t["NDVI_JF"], t["BARDL_ZERO_VARS"], t["NDVI_JV"],
           t["BARDL_ZERO_PLAYERS"], t["NDVI_JF"], SH, CJ, TA))
    F.append(
        "- **A16 (final, post hoc (Part 628)). Kendall's W of the main set, variable level, nowcast** (Table 9; Table "
        "S3.22): PM2.5 %s (stored %s); NDVI %s (stored %s); forest loss %s (stored %s); coral bleaching %s (stored %s); "
        "burned fraction undefined (main set treeroute v1 alone; stored null). Source: "
        "%s/out/<problem>/lead_0/compare/AW4_main_row.json kendall_w.value and kendall_w.ci, as %s lists them (Table "
        "S3.22, line 157 of %s)."
        % (t["W_PM25"], trio(s["W_PM25"]), t["W_NDVI"], trio(s["W_NDVI"]), t["W_DEFO"], trio(s["W_DEFO"]),
           t["W_CORAL"], trio(s["W_CORAL"]), SH, CJ, TA))
    F.append(
        "- **A17 (final, post hoc (Part 628)). treeroute v1 against its same-link rivals, variable level, nowcast** "
        "(Table 9; Table S3.22). Median top-20-union Spearman [95%% CI]: PM2.5 %s (stored %s); NDVI %s (stored %s); "
        "forest loss %s (stored %s); coral bleaching %s (stored %s); the PM2.5 and NDVI intervals include 0. RBO (p = "
        "0.9) with the rivals' consensus: PM2.5 %s (stored %s); NDVI %s (stored %s); forest loss %s (stored %s); coral "
        "bleaching %s (stored %s). Source: %s/out/<problem>/lead_0/compare/AW4_main_row.json "
        "treeroute_vs_same_link_rivals_median_spearman_top20_union.value and .ci, and [\"rbo_vs_consensus_p0.9\"].value "
        "and .ci, as %s lists them (Table S3.22, lines 159 and 161 of %s)."
        % (t["SP_PM25"], trio(s["SP_PM25"]), t["SP_NDVI"], trio(s["SP_NDVI"]), t["SP_DEFO"], trio(s["SP_DEFO"]),
           t["SP_CORAL"], trio(s["SP_CORAL"]), t["RBO_PM25"], trio(s["RBO_PM25"]), t["RBO_NDVI"],
           trio(s["RBO_NDVI"]), t["RBO_DEFO"], trio(s["RBO_DEFO"]), t["RBO_CORAL"], trio(s["RBO_CORAL"]), SH, CJ, TA))
    F.append(
        "- **A18 (final, post hoc (Part 628)). Own-history shares, variable level, nowcast** (Table 9; Table S3.22; a "
        "family share: the own-history family's mean absolute attribution over the sum of the five families', each "
        "region weighted equally). treeroute v1: PM2.5 %s (stored %s); NDVI %s (stored %s); forest loss %s (stored "
        "%s); burned fraction %s (stored %s; from the independent re-computation, ruling BB1); coral bleaching 0.00 "
        "[0.00, 0.00] (no own-history input). Median of the rivals: PM2.5 %s (stored %s), LightGBM's share (the rivals: "
        "Ridge %s, random forest %s, LightGBM %s); NDVI %s (stored %s), with four rivals the mean of the two middle "
        "shares (Ridge %s, random forest %s, LightGBM %s, BARDL %s); forest loss %s (stored %s), LightGBM's share "
        "(Ridge %s, random forest %s, LightGBM %s); coral bleaching 0.00 [0.00, 0.00] (no own-history input). Each "
        "interval is for one share. Sources: %s/out/<problem>/lead_0/compare/AW4_main_row.json "
        "own_history_share_treeroute and own_history_share_median_rival (value, ci); "
        "%s/verify_v1/A/results.json problems.fire.main_row.own_history_share_treeroute (value, ci_low, ci_high); "
        "%s/out/<problem>/lead_0/compare/families.parquet (family own history, column share); as %s lists them "
        "(Table S3.22, lines 164-166 of %s); ruling BB4 (the label \"median of the rivals\")."
        % (t["OH_TR_PM25"], trio(s["OH_TR_PM25"]), t["OH_TR_NDVI"], trio(s["OH_TR_NDVI"]), t["OH_TR_DEFO"],
           trio(s["OH_TR_DEFO"]), t["OH_TR_FIRE"], trio(s["OH_TR_FIRE"]), t["OH_MED_PM25"], trio(s["OH_MED_PM25"]),
           ohr["pm25"]["rival_ridge"][0], ohr["pm25"]["rival_rf"][0], ohr["pm25"]["rival_lgbm"][0],
           t["OH_MED_NDVI"], trio(s["OH_MED_NDVI"]), ohr["ndvi"]["rival_ridge"][0], ohr["ndvi"]["rival_rf"][0],
           ohr["ndvi"]["rival_lgbm"][0], ohr["ndvi"]["rival_bardl_h1"][0], t["OH_MED_DEFO"], trio(s["OH_MED_DEFO"]),
           ohr["defo"]["rival_ridge"][0], ohr["defo"]["rival_rf"][0], ohr["defo"]["rival_lgbm"][0], SH, SH, SH, CJ,
           TA))
    F.append(
        "- **A19 (final, post hoc (Part 628)). Rows with a forecast above 0, the arcsine-link models' view** (Tables "
        "S3.25 g and S3.27 g; of the %s sample rows). Burned fraction: treeroute v1 %s. Coral bleaching: treeroute v1 "
        "%s, random forest %s, LightGBM %s, absolute-error booster %s. Source: "
        "%s/out/<problem>/lead_0/compare/per_lead.json nonzero_forecast_rows.<model>.rows, as %s lists them (lines 448 "
        "and 659 of %s)."
        % (t["N"], t["FIRE_NZ"], L.intc(nzc["treeroute"]), L.intc(nzc["rival_rf"]), L.intc(nzc["rival_lgbm"]),
           L.intc(nzc["rival_hgb_l1"]), SH, CJ, TA))
    cc = s["coral_cc"]
    F.append(
        "- **A20 (final, post hoc (Part 628)). Coral bleaching's context-and-calendar family shares, variable level, "
        "nowcast** (Table S3.27 f). Main set: treeroute v1 %s (stored %s), random forest %s (stored %s), LightGBM %s "
        "(stored %s), absolute-error booster %s (stored %s); so from %s (treeroute v1) to %s (LightGBM). Cross-link "
        "models: Ridge %s, Tweedie booster %s. Source: %s/out/coral/lead_0/compare/families.parquet (family context "
        "and calendar, column share), as %s lists it (line 642 of %s)."
        % (cc["treeroute"][1], r(cc["treeroute"][0]), cc["rival_rf"][1], r(cc["rival_rf"][0]), cc["rival_lgbm"][1],
           r(cc["rival_lgbm"][0]), cc["rival_hgb_l1"][1], r(cc["rival_hgb_l1"][0]), t["CC_CORAL_TR"],
           t["CC_CORAL_LGBM"], cc["rival_ridge"][1], cc["rival_lgbm_tweedie"][1], SH, CJ, TA))
    F.append(
        "- **A21 (final, post hoc (Part 628)). Forest loss's B1 identity check** (Table S3.30 b). Forest loss is "
        "annual, so its B1 background equals its B2 one, and its B1 run (background pairs %s, as in the main run) must "
        "repeat the main run exactly: the largest absolute difference of the SHAP values is %s at the feature level "
        "and %s at the variable level (stored %s and %s), with rows %s / %s, players %s / %s and variables %s / %s "
        "(main run / B1 run), matched by sample row and by name, the same in both. So by protocol section 10 the B1 "
        "numbers of fire, PM2.5 and NDVI are reported. Sources: %s/verify_v1/A/results.json b1.defo.identity "
        "(max_abs_diff_phi, max_abs_diff_phiv, n_rows_*, n_players_*, n_variables_*) and %s/logs/tr_shap_defo_lead0.log "
        "line 24 (background pairs), as %s lists them (lines 771 and 777-781 of %s); SHAP protocol sections 10 and 14."
        % (L.intc(defo_pairs), "0", "0", r(ident["max_abs_diff_phi"]), r(ident["max_abs_diff_phiv"]),
           L.intc(idrows[0]), L.intc(idrows[1]), idpl[0], idpl[1], idvar[0], idvar[1], SH, SH, CJ, TA))
    F.append(
        "- **A22 (final, post hoc (Part 628)). treeroute v1's B1 run: the seasonal normal** (Table S3.29). Family "
        "share of the seasonal normal [95%% CI]: PM2.5 %s (stored %s); NDVI %s (stored %s); burned fraction %s (stored "
        "%s). The B1 run's top variable is normal on all three (shares %s, %s and %s; stored %r, %r and %r). Under B2 "
        "the seasonal normal's family share is exactly 0 for every model on these three problems (stored 0.0; Tables "
        "S3.23 f, S3.24 f and S3.25 f), and normal is a structural zero (Table S3.19). Every B1 player's importance, "
        "share and signed mean, with its interval, is in the re-computation's results file (key b1). Sources: "
        "%s/verify_v1/A/results.json b1.<problem>.variable.families.seasonal_normal (value, ci_low, ci_high) and "
        "b1.<problem>.variable.top3; %s/out/<problem>/lead_0/compare/families.parquet (family seasonal normal); as %s "
        "lists them (lines 721, 727, 249, 340 and 432 of %s); SHAP protocol sections 9 and 10."
        % (t["B1SN_PM25"], trio(s["B1SN_PM25"]), t["B1SN_NDVI"], trio(s["B1SN_NDVI"]), t["B1SN_FIRE"],
           trio(s["B1SN_FIRE"]), b1top["pm25"]["printed"], b1top["ndvi"]["printed"], b1top["fire"]["printed"],
           b1top["pm25"]["stored"][0], b1top["ndvi"]["stored"][0], b1top["fire"]["stored"][0], SH, SH, CJ, TA))
    F.append(
        "- **A23 (final, post hoc (Part 628)). The independent re-computation of the comparison (round 14, ruling BA2) "
        "and what compare_shap.py does not do.** Implementers A and B, each with its own code written from the "
        "protocol, blind to compare_shap.py, shapv1_stats.py and the compare outputs (before the reconciliation they "
        "had opened only per_lead.json, for its structural keys, and bootstrap_draws.npy); a reconciliation compared A "
        "with B and both with the compare files. Every number that the compare files hold and A and B also hold equals "
        "theirs within 1e-9, and the per-draw values of bootstrap_stats.parquet equal A's and B's on all %s draws, "
        "except in three groups: a family with no variable (A gives no number; B and the compare files give 0, "
        "section 8's sum rule; open choice C15), fire's undefined Kendall's W and mean pairwise Spearman (NaN with 0 "
        "finite replicates in the compare files, left undefined by A and B) and the sign agreement's intervals. A "
        "third, partial implementation (the round's numbers check, with its own code written from the protocol) gave "
        "the same values for the five main-text rows (fire's defined part), a sample of pairs, coral's treeroute "
        "importances, defo's identity check and a sample of the B1 numbers. compare_shap.py's three departures that "
        "bear on what is reported: it writes neither treeroute's top 3 nor its own-history share [CI] in fire's "
        "main-text row (main_text_row() writes them only when treeroute has a same-link rival); it does not evaluate "
        "the sign agreement on the draws (no interval; finite_replicates written as 0); it gives no feature-level "
        "family-share distance (a third departure by ruling BB2, with no new number). Two latent departures had no "
        "effect: the nonzero-forecast view's top 10 is not sorted by section 8's name rule (no tie occurred), and the "
        "printed AW3 header lists at most 30 structural zeros (the largest count is 29). No SHAP script was edited or "
        "run, and the compare files are unchanged. Sources: SHAP protocol section 14, entry of 2026-11-16 (round 14; "
        "results; what compare_shap.py does not do as the protocol says), and sections 9 and 10; "
        "engine/OWNER_RULINGS_2026-10-06.md section BB (preamble, BB1, BB2)."
        % (t["B"],))
    rid, lgb, rf = thin["rival_ridge|treeroute"], thin["rival_lgbm|treeroute"], thin["rival_rf|treeroute"]
    F.append(
        "- **A24 (final, post hoc (Part 628)). Sign-agreement intervals on fewer than 2,000 finite draws (ruling BB1).** "
        "%s intervals, all of burned fraction at the variable level against treeroute v1 (Table S3.25 a): Ridge, %s "
        "finite draws (full-sample value %s, %s signs), interval [%s, %s]; LightGBM, %s finite draws (value %s, %s "
        "sign), interval [%s, %s]; random forest, %s finite draws (value %s, %s sign), interval [%s, %s]. Every "
        "sign-agreement interval is from the independent re-computation (A = B). Sources: "
        "%s/verify_v1/A/results.json problems.fire.levels.variable.pairs[\"rival_ridge|treeroute\"], "
        "[\"rival_lgbm|treeroute\"] and [\"rival_rf|treeroute\"].sign_agreement (n_finite, ci_low, ci_high), and "
        "%s/out/fire/lead_0/compare/pairs.parquet (value, signs_compared), as %s lists them (lines 354-356 of %s); "
        "ruling BB1."
        % (t["THIN"].capitalize(), L.intc(rid[0]), rid[3], rid[4], rid[1], rid[2], L.intc(lgb[0]), lgb[3], lgb[4],
           lgb[1], lgb[2], L.intc(rf[0]), rf[3], rf[4], rf[1], rf[2], SH, SH, CJ, TA))
    F.append(
        "- **A25 (final, post hoc (Part 628)). The coral comparison table read before the re-computation (ruling "
        "BB6).** Coral bleaching's AW4_table.md, the current coral comparison's table of the AW4 statistics (written "
        "on 2026-11-13 at 00:06; file time 00:06:12), was read on 2026-11-13 at about 15:31, before the independent "
        "re-computation (2026-11-16, from 17:09); the re-computation's implementers A and B never opened it. "
        "Supplement S1.7 records who read it. Sources: engine/OWNER_RULINGS_2026-10-06.md BB6; SHAP protocol section "
        "10 (BB6) and section 14 (entry of 2026-11-14 and 2026-11-15, \"What was read\"); "
        "paper/supp_build/s3_13/_brief/reads_tables.md (the file time); Table S3.22 note d.")
    block = "\n".join(F)
    if "\n" + A8_LAST not in text:
        raise SystemExit("A8 anchor not found")
    i = text.index("\n" + A8_LAST) + 1
    j = text.index("\n", i)
    after = text[j:]
    if not after.startswith("\n\n---\n\n## 10. "):
        raise SystemExit("A8 is not the last fact of section 9")
    out = text[:j] + "\n" + block + after
    if out.count(REV_ANCHOR) != 1:
        raise SystemExit("Revised paragraph anchor")
    out = out.replace(REV_ANCHOR, REV_ADD + REV_ANCHOR)
    for k in range(9, 26):
        n = out.count("**A%d (" % k)
        if n != 1:
            raise SystemExit("A%d occurs %d times" % (k, n))
    data = out.encode("utf-8")
    with open(DST, "wb") as f:
        f.write(data)
    print("written", DST, "bytes", len(data), "sha256", L.sha256_bytes(data))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
