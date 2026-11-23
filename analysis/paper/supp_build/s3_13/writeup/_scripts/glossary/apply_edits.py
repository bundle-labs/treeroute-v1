"""Apply the glossary writer's edits to the STAGED copies only (never a live file).

Usage: py -3.9 -I -B apply_edits.py <STAGE root>
Edits <STAGE>/paper/draft/GLOSSARY.md (UTF-8, CRLF) and <STAGE>/paper/PAPER_FACTS.md
(UTF-8, LF). Each anchor must occur exactly once; the script refuses to run twice
(it stops if its rows or lines are already present). Line endings, encoding and
every existing line are kept; only the lines listed below are added, and in
PAPER_FACTS.md one stale phrase of one line is replaced.
"""
import os
import sys

SNAP = "@@SNAP@@"

GLOSSARY_ROWS = [
    "| **SHAP value** (phi_ij, of player j on row i) | baseline Shapley value, feature attribution, phi__ and phiv__ columns | "
    "A player's interventional Shapley value on one explained row, in the model's own link space: a set of players is worth the "
    "model's output averaged over the row's background rows, with those players at the explained row's values and the others at "
    "each background row's; a row's SHAP values add up to the model's output there minus its mean over the background rows, up "
    "to a small unattributed part that S-RESID checks (Table S3.20). <!-- SHAP protocol D:/treeroute/analysis/shap_v1/PROTOCOL.md "
    "section 5 (value function, decision D3; stop rules S-ADD and S-RESID); Table 9 and Table S3.20 captions. phi_ij is the "
    "protocol's symbol; the bare phi is the link (row link; Section 2.7). --> | S3.13 (named Table 9) |",

    "| **interventional TreeSHAP** | SHAP walk, shapv1_treeshap.py | The exact computation of a tree model's SHAP values, tree by "
    "tree, over every pair of an explained row and one of its background rows (not the path-dependent TreeSHAP built into "
    "LightGBM); on treeroute v1 it is applied to the rebuilt specialist trees (and correctors, on corrected-answer arms), weighted "
    "by the router's coefficients, and the router's other terms are exactly linear; Ridge and BARDL get exact linear SHAP values. "
    "<!-- SHAP protocol section 5 (exact interventional TreeSHAP; treeroute; rivals; LightGBM's built-in pred_contrib, "
    "path-dependent, is a cross-check only); Tables S3.18 a and S3.21 --> | S3.13 |",

    "| **background** (**B2**; **B1** only as treeroute v1's sensitivity) | B(x), background_keys.parquet, router pool (coral) | "
    "The rows against which an explained row's SHAP values are taken: under B2, shared by every model, the same location's "
    "router fit rows of the explained row's calendar month at or before the cut (forest loss, annual: all of them; coral "
    "bleaching: the survey visit's saved router fit rows, a pool of earlier nearby survey visits), so that on the gridded "
    "problems columns constant within a location, such as the static columns, the month and the seasonal normal, are exactly 0; "
    "under B1, treeroute v1's sensitivity only and never pooled with the main set, all of the location's router fit rows at or "
    "before the cut, so that the month and the seasonal normal can take credit (not defined on coral bleaching). <!-- SHAP "
    "protocol section 5 (B2, what B2 means, B1); Table 9 caption; Table S3.19 note c; Table S3.28 caption. Not the protocol's "
    "coral wording \"other sites' visits\", which is inexact: some background visits are earlier visits at the explained "
    "visit's own reef site, and none is dated on or after it "
    "(paper/supp_build/s3_13/_brief/lead_checks/verify_v5_claims_out.txt). --> | Table 9 (Section 5.4); B1: S3.13 |",

    "| **player**, at the **feature level** or the **variable level** | grouped game (the variable level), merged player (a "
    "copied context column) | What a SHAP value is given to: at the feature level, one distinct input column, or normal (the "
    "seasonal normal, as an input or an offset), a router-context column that exactly copies a tree input being the same player "
    "as that input (as on NDVI); at the variable level, one variable, valued as a single player: the columns whose names agree "
    "once their lag, aggregate and window suffixes and catalog code are stripped (own-history columns keep their stem, such as "
    "hist_last; context columns are calendar, the month and its harmonics, or ctx: followed by their name, as in ctx:lat). "
    "<!-- SHAP protocol sections 5 (players and the two levels) and 8 (players; the variable rule; duplicates); Table S3.19 --> "
    "| S3.13 (variable level named Table 9) |",

    "| **active set** (J); **structural zero** | active (per_lead.json), n_J (results.json), structural_zero (per_lead.json) | "
    "J, at one level: the players to which some model gives more than 10\u207b\u00b9\u00b2 of its total mean absolute SHAP "
    "value (each region weighted equally; a plain mean gives the same set), over which the pair statistics and the shares are "
    "taken (the B1 pair has its own J); the other players are the structural zeros, exactly 0 on every row of every model at "
    "that level. <!-- SHAP protocol section 8 (active set J; statistics on J; shares over J); Table S3.19 caption and note; "
    "Table S3.28 caption (the pair's J); write-up brief item 1 (J under a plain mean) --> | S3.13 |",

    "| **importance** (I_m(j)); **share** (s_m(j)) | importance vector, region-weighted mean absolute phi | A player's "
    "importance to a model is its mean absolute SHAP value over the sample rows, with each region weighted equally, and "
    "rankings order the players by it; its share is its importance over the model's total importance over J, the base of "
    "S3.13's top-10 and top-3 shares, while family shares have another base (row family). <!-- SHAP protocol section 8 "
    "(importance vectors: I_m(j), s_m(j)); Table 9 caption; Tables S3.23-S3.27 and S3.29 captions --> | Table 9 (Section "
    "5.4); share: S3.13 (named Table 9) |",

    "| **family** (of variables; five); **family share**, as in the **own-history share** | own_history, global_indices, "
    "local_drivers, context_and_calendar, seasonal_normal (results.json keys) | One of five groups of variables: own history "
    "(the lags and trailing means of the location's own labels), global indices (variables all of whose columns take one value "
    "per step across the test set), local drivers (the variables in no other family), context and calendar (the router-context "
    "columns that copy no tree input) and the seasonal normal; a family's attribution on a row is the sum of its variables' SHAP "
    "values, and its family share is its mean absolute attribution (each region weighted equally) over the sum of the five "
    "families', so the own-history share is not the sum of the own-history variables' shares. <!-- SHAP protocol section 8 "
    "(families); Table 9 caption; Tables S3.23-S3.27 captions; ruling BB4 (a family with no variable keeps its defined 0, with "
    "a label). The family names are the protocol's; \"context\" alone (row router context) and \"drivers\" alone (row tree "
    "inputs) stay do-not-use names. --> | Table 9 (Section 5.4) |",

    "| **main set** | main_set (per_lead.json) | treeroute v1 and its rivals that explain in its link and passed their skill "
    "guard: the models of Kendall's W and of the main-text row (Table 9), whose rivals make the consensus; a rival that failed "
    "its skill guard is explained, labelled and kept out (decision D6), and on burned fraction the main set is treeroute v1 "
    "alone. <!-- SHAP protocol sections 7 (D6) and 8 (model sets; main-text row); Table 9 caption and note a; Table S3.18 --> "
    "| Table 9 (Section 5.4) |",

    "| **same-link** / **cross-link** (a pair of models) | same_link (code) | A pair is same-link when both models explain in "
    "the same link space (the same link, constant c and upper bound; within each problem, the same link), else cross-link; "
    "cross-link pairs are shown for completeness, labelled \"not comparable in scale or rank\" because shares and ranks depend "
    "on the link, and never pooled. <!-- SHAP protocol section 8 (model sets); Table S3.18 note on links; Tables S3.23-S3.27 "
    "captions --> | S3.13 (named Table 9) |",

    "| **Kendall's W** (of the main set) | kendall_w, kendall_w_main_set | Kendall's coefficient of concordance of the main "
    "set's rankings, with the tie correction; it needs two models, so it is undefined on burned fraction, and the mean pairwise "
    "Spearman correlation of the main set is given beside it (S3.13). <!-- SHAP protocol section 8 (per problem-lead "
    "statistics); Table 9 caption and note a; Tables S3.23-S3.27, panel c --> | Table 9 (Section 5.4) |",

    "| **rank-biased overlap** (RBO) | rbo_p0.9, rbo_p0.95, rbo_vs_consensus_p0.9 | A top-weighted overlap of two full "
    "rankings over J (equal length, ties broken by name), in its finite form, at p = 0.9 and 0.95; Table 9 gives treeroute "
    "v1's ranking against the rivals' consensus at p = 0.9. <!-- SHAP protocol section 8 (pairwise statistics: RBO; main-text "
    "row); Table 9 caption; Tables S3.23-S3.27 --> | Table 9 (Section 5.4) |",

    "| **consensus** (the rivals' consensus) | \u2014 | The mean of the main-set rivals' importance shares, recomputed on "
    "every bootstrap draw; Table 9 compares its ranking with treeroute v1's by RBO and prints its top 3 (the consensus top 3). "
    "<!-- SHAP protocol section 8 (main-text row: the mean of the rivals' shares, rebuilt per draw); Table 9 caption --> | "
    "Table 9 (Section 5.4) |",

    "| **stability** (under region resampling) | stability_under_region_resampling | The mean Spearman correlation of a "
    "model's full-sample importances with those of its own bootstrap replicates over region draws; descriptive, not a ceiling "
    "on between-model agreement. <!-- SHAP protocol section 8 (per problem-lead statistics); Tables S3.23-S3.27, note on "
    "stability --> | S3.13 |",

    "| **sign agreement** (on the top-10 union) | sign_agreement_top10, signs_compared, sign_n_determined | Of the players in "
    "the union of two models' top-10 sets whose sign is determined in both (the bootstrap 95% interval of the player's signed "
    "mean SHAP value excludes 0), the share whose signs agree, printed with that number of players (\"signs\"); undefined when "
    "no player qualifies. <!-- SHAP protocol section 8 (pairwise statistics: sign agreement; signed mean S_m(j)); Tables "
    "S3.23-S3.27, note on sign agreement; ruling BB1 (its intervals and finite draws) --> | S3.13 |",
]

GLOSSARY_COMMENT = (
    "<!-- S3.13 write-up, 2026-11-17 (pre-edit copy in draft/_snapshots/" + SNAP + "/): rows added at the end of the table "
    "for the post hoc SHAP comparison of Supplement S3.13 and Table 9 (Section 5.4): SHAP value, interventional TreeSHAP, "
    "background (B2; B1), player (feature and variable level), active set J and structural zero, importance and share, family "
    "and family share, main set, same-link and cross-link, Kendall's W, rank-biased overlap, consensus, stability, sign "
    "agreement. Definitions from the SHAP protocol (D:/treeroute/analysis/shap_v1/PROTOCOL.md sections 5 and 8, not its "
    "inexact coral wording \"other sites' visits\"), the captions and notes of the agreed tables "
    "(paper/supp_build/s3_13/reconcile/tables_agreed.md, version 5) and the write-up brief's facts; other names from the "
    "protocol and the comparison's file, column and key names. First defined: Table 9 (Section 5.4) where Table 9's caption "
    "defines the term, else S3.13, with \"(named Table 9)\" as in \"(named 2.1)\". No existing row changed. -->"
)

PF_REVISED = (
    "**Revised 2026-11-17 (S3.13 write-up).** For the write-up of the post hoc SHAP comparison (Part 628; Supplement S3.13 "
    "and main-text Table 9), the status key gains the status \"final, post hoc (Part 628)\", and L11's bullet \"Kept out by "
    "default beyond ruling AT7's words\" now gives the S9.2 calls of the ONI and GPCC SPI values in the burned-fraction "
    "published rivals' slim data as \"Kept out: cited, not shared\" (ruling AV10), in place of the stale \"Not until "
    "confirmed\". Neither change alters a number. Copy of this sheet before the S3.13 write-up, 2026-11-17: "
    "paper/draft/_snapshots/" + SNAP + "/."
)

PF_STATUS_ANCHOR = "  - **final, post hoc (Part 622)**:"
PF_STATUS_LINE = (
    "  - **final, post hoc (Part 628)**: computed after the test labels were opened, by the post hoc SHAP analysis of Part "
    "628 (protocol D:/treeroute/analysis/shap_v1/PROTOCOL.md; rulings AW, AY, AZ1, BA and BB), from its output files and run "
    "records. An independent re-computation by two implementations that agree matches, within 1e-9, every number of the "
    "comparison's output files that both implementations also hold, and supplies the numbers that the comparison does not "
    "write (ruling BB1) and every number of treeroute v1's B1 sensitivity except the B1 runs' background pairs and seconds, "
    "which are read from their logs. Report-only: it never changes a verdict and is never a headline, and the paper labels "
    "every such number \"post hoc\"."
)

PF_STALE = 'which hold ONI and GPCC SPI values, both "Not until confirmed" in S9.2; Part B never ran.'
PF_NEW = (
    'which hold ONI and GPCC SPI values, both "Kept out: cited, not shared" in S9.2 (ruling AV10); Part B never ran. '
    '(Corrected 2026-11-17, S3.13 write-up: the two calls had read "Not until confirmed" until owner ruling AV10 '
    '(2026-11-12) kept those inputs out of the archive, cited, not shared; the correction was decided on 2026-11-13, '
    '"going ahead unless objected", and no objection came.)'
)


def edit_glossary(path):
    with open(path, "rb") as f:
        raw = f.read()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise SystemExit("GLOSSARY: unexpected BOM")
    text = raw.decode("utf-8")
    if "\n" in text.replace("\r\n", ""):
        raise SystemExit("GLOSSARY: bare LF found; expected CRLF only")
    if "S3.13 write-up, 2026-11-17" in text or "| **SHAP value**" in text:
        raise SystemExit("GLOSSARY: edits already present; nothing done")
    if not text.endswith("\r\n"):
        raise SystemExit("GLOSSARY: no final CRLF")
    lines = text[:-2].split("\r\n")
    idx = [i for i, ln in enumerate(lines) if ln.startswith("| **reference gap** |")]
    if len(idx) != 1:
        raise SystemExit("GLOSSARY: anchor row count %d" % len(idx))
    i = idx[0]
    if lines[i + 1] != "":
        raise SystemExit("GLOSSARY: the table does not end after the anchor row")
    for r in GLOSSARY_ROWS:
        if r.count("|") != 5 or "--" in r.replace("<!--", "").replace("-->", ""):
            raise SystemExit("GLOSSARY: bad row: %r" % r[:60])
        if "\r" in r or "\n" in r:
            raise SystemExit("GLOSSARY: newline in a row")
    new_lines = lines[: i + 1] + GLOSSARY_ROWS + lines[i + 1:] + [GLOSSARY_COMMENT]
    out = "\r\n".join(new_lines) + "\r\n"
    with open(path, "wb") as f:
        f.write(out.encode("utf-8"))
    return len(GLOSSARY_ROWS) + 1


def edit_facts(path):
    with open(path, "rb") as f:
        raw = f.read()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise SystemExit("PAPER_FACTS: unexpected BOM")
    text = raw.decode("utf-8")
    if "\r" in text:
        raise SystemExit("PAPER_FACTS: CR found; expected LF only")
    if "final, post hoc (Part 628)" in text or "S3.13 write-up" in text:
        raise SystemExit("PAPER_FACTS: edits already present; nothing done")
    if text.count(PF_STALE) != 1:
        raise SystemExit("PAPER_FACTS: stale phrase count %d" % text.count(PF_STALE))
    lines = text.split("\n")
    st = [i for i, ln in enumerate(lines) if ln.startswith(PF_STATUS_ANCHOR)]
    if len(st) != 1:
        raise SystemExit("PAPER_FACTS: status anchor count %d" % len(st))
    hdr = [i for i, ln in enumerate(lines) if ln == "## How to use this sheet"]
    if len(hdr) != 1 or lines[hdr[0] - 1] != "" or not lines[hdr[0] - 2].startswith("**Revised 2026-11-10 (region map)"):
        raise SystemExit("PAPER_FACTS: revision-paragraph anchor not as expected")
    # status line after the Part 622 line
    s = st[0]
    lines = lines[: s + 1] + [PF_STATUS_LINE] + lines[s + 1:]
    # revision paragraph before the blank line that precedes "## How to use this sheet"
    h = [i for i, ln in enumerate(lines) if ln == "## How to use this sheet"][0]
    lines = lines[: h - 1] + ["", PF_REVISED] + lines[h - 1:]
    text2 = "\n".join(lines)
    text2 = text2.replace(PF_STALE, PF_NEW, 1)
    with open(path, "wb") as f:
        f.write(text2.encode("utf-8"))
    return 3


def main():
    stage = sys.argv[1]
    g = os.path.join(stage, "paper", "draft", "GLOSSARY.md")
    p = os.path.join(stage, "paper", "PAPER_FACTS.md")
    print("GLOSSARY lines added:", edit_glossary(g))
    print("PAPER_FACTS edits:", edit_facts(p))


if __name__ == "__main__":
    main()
