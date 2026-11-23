# Build this writer's three staged files from their hash-checked base copies (work/*.base):
#   STAGE/paper/draft/S1_disclosures.md   (LF, UTF-8 without BOM)
#   STAGE/paper/draft/S4_provenance.md    (CRLF, UTF-8 without BOM)
#   STAGE/paper/PAPER_FACTS.md            (LF, UTF-8 without BOM; base = the S3.13 writer's staged copy)
# Every edit is an exact replacement whose old text must occur exactly once. Hashes in S4 come from
# hashes_2026-11-17.json (written by hash_files.py, read-only). Quoted ruling words are checked
# against the rulings file. Reads only; writes only the three staged files.
import hashlib, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "work")
STAGE = os.path.normpath(os.path.join(HERE, "..", ".."))
ROOT = os.path.normpath(os.path.join(STAGE, "..", "..", "..", ".."))
RULINGS = os.path.join(ROOT, "engine", "OWNER_RULINGS_2026-10-06.md")

BASES = {
    "paper/draft/S1_disclosures.md": ("23d7c5d8167293ad1ea08561e1f0f471fe818da722e6e805e97094cc6c450862", "\n"),
    "paper/draft/S4_provenance.md": ("19112cd642e6a8d74773278a5c2a32a958ae584bd064a3485ffc3fe19fdc7d5f", "\r\n"),
    "paper/PAPER_FACTS.md": ("735e10c81ceee24e89d522c02f0dd86b344902f77147238d2972723702425a8b", "\n"),
}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def load(rel):
    want, eol = BASES[rel]
    p = os.path.join(WORK, rel.replace("/", "__") + ".base")
    b = open(p, "rb").read()
    if sha(b) != want:
        sys.exit("base hash differs: " + rel)
    if b.startswith(b"\xef\xbb\xbf"):
        sys.exit("BOM in base: " + rel)
    t = b.decode("utf-8")
    if eol == "\r\n":
        assert "\r\n" in t and t.replace("\r\n", "").find("\n") == -1 and t.replace("\r\n", "").find("\r") == -1
        t = t.replace("\r\n", "\n")
    else:
        assert "\r" not in t
    return t


def save(rel, t):
    _, eol = BASES[rel]
    assert "\r" not in t
    if eol == "\r\n":
        t = t.replace("\n", "\r\n")
    p = os.path.join(STAGE, *rel.split("/"))
    with open(p, "wb") as f:
        f.write(t.encode("utf-8"))
    print("wrote", rel, sha(t.encode("utf-8")))


def rep(t, old, new, what):
    n = t.count(old)
    if n != 1:
        sys.exit("edit %s: old text found %d times" % (what, n))
    return t.replace(old, new)


# ---------------------------------------------------------------- the ruling words quoted in S4.13
RW = open(RULINGS, "rb").read().decode("utf-8")
QUOTES = [
    'answers to the agent\'s question "Add SHAP to the paper now?": the answers of the author, not quoted (ruling AW1)',
    'a message of the author, not quoted (rulings AW2-AW4)',
    'the answer of the author, not quoted (ruling AW5), 2026-11-12, to the question "How many test rows per problem should SHAP explain?"',
    'The owner first asked a question, not quoted (ruling AX1)',
    'The owner then answered, not quoted (ruling AX1), and, while the file was being fetched, wrote again, not quoted',
    'Items 2-13 are not answered yet and stay open.',
    '"Which scope should the remaining SHAP runs use?": the answer of the author, not quoted (ruling AY)',
    '"Had you opened the 21:18 fire comparison files before ridge is added?", with two answers offered: the answer of the author, not quoted (ruling AZ1)',
    '"Open the SHAP results now, keeping item 16 at (a)?", with two answers offered: the answer of the author, not quoted (ruling BA)',
    '"Run the planned B1 sensitivity (about 10 h of computer time)?", with two answers offered: the answer of the author, not quoted (ruling BA3)',
    'The owner first asked a question, not quoted (ruling BA3)',
    '"Accept all six recommendations for how S3.13 presents these numbers?", with two answers offered: the answer of the author, not quoted (ruling BB)',
    'The owner answered at 20:59, not quoted (ruling BB).',
    'The owner answered in chat at about 04:35',
    'The owner answered at about 19:45.',
    'The owner answered at about 22:50',
    'The other decisions of the protocol\'s section 12 keep their defaults, which the protocol puts in force until ruled (among them D7, the Kraft LSTM left out, and D10, N = 1,000 with all regions).',
    'The owner had already run the coral pilot with this tolerance, from the command in RUN_COMMANDS.md, before this ruling; this answer rules it.',
    'The agent had recommended scope (ii).',
    'The answer came after the NDVI comparison had been computed and before any NDVI statistic was read.',
    'the agent added a defo run, first, as a check of the B1 code, and told the owner so',
    'it wrote it on 2026-11-15 at 23:03, before the first B1 run started (23:06)',
    'was read by an agent on 2026-11-13 at about 15:31, before the independent re-computation, and that its implementers A and B never opened it.',
    'owner question C10, asked on 2026-11-16 at about 01:50',
    'The agent\'s chat messages had quoted some of the round\'s statistics, rounded',
    '## AW. SHAP on all five problems (owner, 2026-11-12,',
    '## AX. Fourth batch (owner, 2026-11-13,',
    '## AY. SHAP decisions (owner, 2026-11-13,',
    '## AZ. SHAP ridge loader, question Q1 (owner, 2026-11-14,',
    '## BA. SHAP results and treeroute\'s B1 sensitivity (owner, 2026-11-15,',
    '## BB. SHAP presentation after the independent re-computation (owner, 2026-11-16,',
]
for q in QUOTES:
    if q not in RW:
        sys.exit("quote not in the rulings file: " + q)
# the rulings file has no lettered section after BB
import re
heads = re.findall(r"^## ([A-Z]{1,2})\. ", RW, flags=re.M)
assert heads[-1] == "BB", heads[-3:]

# ---------------------------------------------------------------- hashes for Table S4.11 / S4.14
H = {r["rel"]: r for r in json.load(open(os.path.join(HERE, "hashes_2026-11-17.json"), encoding="utf-8"))}
SCRIPTS = ["scripts/bardl_shap.py", "scripts/compare_shap.py", "scripts/make_sample.py", "scripts/ridge_shap.py",
           "scripts/rival_shap.py", "scripts/run_shap.py", "scripts/shapv1_common.py", "scripts/shapv1_rows.py",
           "scripts/shapv1_stats.py", "scripts/shapv1_treeshap.py", "scripts/tr_rebuild.py", "scripts/tr_shap.py",
           "scripts/tests/diag_coral_exactness.py", "scripts/tests/smoke_bardl.py", "scripts/tests/smoke_ridge.py",
           "scripts/tests/smoke_unit.py", "scripts/tests/smoke_world.py"]
BUILDERS = ["A/scripts/build_tables.py", "B/scripts/build_tables.py"]
for k in SCRIPTS + BUILDERS:
    assert k in H and len(H[k]["sha256"]) == 64, k
# recorded prefixes in the SHAP protocol's change log
for k, pre in (("scripts/bardl_shap.py", "6bfc9aaf"), ("scripts/tests/smoke_bardl.py", "0f7de758"),
               ("scripts/ridge_shap.py", "866fd329"), ("scripts/tests/smoke_ridge.py", "c48f3f66")):
    assert H[k]["sha256"].startswith(pre), k


def p8(k):
    return H[k]["sha256"][:8]


def full(k):
    return H[k]["sha256"]


# ================================================================ S1
s1 = load("paper/draft/S1_disclosures.md")

S1_HIST = (
    "S3.13 write-up, 2026-11-17 (pre-edit copy draft/_snapshots/@@SNAP@@/): for the post hoc SHAP comparison of "
    "Part 628 (rulings AW, AY, AZ1, BA and BB; Supplement S3.13 and main-text Table 9), S1.7 gains rows PH22-PH30 "
    "after PH21: the comparison, its scope and sample and what it does not claim (PH22); the rebuild and exactness "
    "gates, E5 informational (PH23); the rivals left out, the Kraft LSTM under the open protocol decision D7 among "
    "them, and the loaders added after the freeze (PH24); treeroute v1's B1 sensitivity, its per-player values "
    "given through the re-computation's results file (PH25); the independent re-computation, what the comparison "
    "script does not do, and rulings BB1 and BB2 (PH26); the read of coral bleaching's comparison table before the "
    "re-computation, ruling BB6 and owner question C10, the row that Table S3.22's note d points to (PH27); the "
    "burned-fraction comparison opened for its layout before Ridge was added (PH28); the protocol's wording of "
    "coral bleaching's background (PH29); and how the tables were built (PH30). RP18 gains a clause on the "
    "agents' part in the SHAP analysis, and its Source column gains facts A9, A23 and A27, ruling BA2 and Part "
    "628. The key of the 'Where the paper states it' column now reads 'Tables 1-9', as Table 9 exists. S1.10's "
    "post hoc count goes from 21 to 30 and the total from 170 to 179 (counted by script). The new rows' numbers "
    "cite facts A9-A27 (PAPER_FACTS.md section 9, final, post hoc (Part 628)), as each row's comment names them. "
    "No existing row was removed or moved, and no existing number changed. "
)
s1 = rep(s1, "<!-- GPCC download outcome, fixes after the checks (2026-11-13; pre-edit copy draft/_snapshots/20261113T1440Z_gpcc/fix/paper/draft/S1_disclosures.md): ",
         "<!-- " + S1_HIST + "GPCC download outcome, fixes after the checks (2026-11-13; pre-edit copy draft/_snapshots/20261113T1440Z_gpcc/fix/paper/draft/S1_disclosures.md): ",
         "S1 history")

s1 = rep(s1, "Tables 1-8 and Table S3.1 are the paper's tables;", "Tables 1-9 and Table S3.1 are the paper's tables;", "S1 key")
s1 = rep(s1, "\"S1 only\" means the paper states it only here.\n",
         "\"S1 only\" means the paper states it only here. <!-- S3.13 write-up, 2026-11-17: \"Tables 1-8\" became \"Tables 1-9\", because the main text now has Table 9 (Section 5.4; draft/tables/table_9.md; draft/TABLE_NUMBERS.md) -->\n",
         "S1 key comment")

PH = []
PH.append(
    "| PH22 | Post hoc (rulings AK and AW), after the locked results had been seen and the test labels opened, SHAP "
    "values were computed for treeroute v1 and for its rivals, except those that PH24 lists, at the nowcast of the "
    "five problems only (ruling AY1: no forecast lead is explained), on a fixed sample of 1,000 test rows per problem, the "
    "same rows for every model, with percentile intervals over 2,000 paired bootstrap draws of regions. The analysis "
    "protocol was written before any SHAP value had been computed on a real data row, and its sections on the sample "
    "and the statistics were frozen when the first sample was registered (2026-11-12); smoke tests computed SHAP "
    "values on real rows only as plumbing (at most 250 coral bleaching rows before those sections were frozen and, "
    "later, rows of the registered samples in the checks of the Ridge and BARDL loaders), and no agreement statistic "
    "was read from them. The comparison is report-only: it reads the saved predictions, adoptions and skill-guard "
    "outcomes, re-decides nothing and changes no locked number or verdict. It does not claim that SHAP values show "
    "what causes the outcome (they show what a model uses to move its forecast away from its background), that "
    "agreement between rankings is correctness, that models in different links can be compared, or that a zero means "
    "that an input is irrelevant. <!-- S3.13 write-up, 2026-11-17: facts A9 (protocol version 1 before any SHAP value "
    "on a real data row; sections 3 and 8 frozen at the first registration, coral bleaching, 2026-11-12; the v2 and v3 "
    "smokes on 40-250 real coral bleaching rows, and the two loaders' checks on rows of the registered samples, plumbing "
    "only, with no agreement statistic read), A10 (N = 1,000 rows, the same for every model; B = 2,000 paired region "
    "draws; percentile 95% intervals) and A14 (the samples); rulings AK, AW1-AW5 and AY1; SHAP protocol section 1 "
    "(\"Post hoc (ruling AK)\") and section 10 (\"Not claimed\"), as S3.13's \"Not claimed\" paragraph and closing line "
    "state them --> | all | 5.4; Table 9; S3.13 | facts A9, A10, A14; Part 628; rulings AK, AW, AY1 |")
PH.append(
    "| PH23 | treeroute v1's fitted trees were not kept, so each problem's tree bank, with its correctors and "
    "placebos, and the sampled locations' routers were rebuilt with the run's own engine code, which read the run's "
    "saved adoption and skill-guard outcome; no model got a SHAP value before it had reproduced its saved "
    "predictions. Gate E5, the fingerprint of the rebuilt tree bank, correctors and placebos, differs from the run's "
    "on all five problems, while every checked tree answer and prediction matches, bit for bit or, on the arcsine arms "
    "of burned fraction and coral bleaching, within the D8 tolerance (a relative difference of at most 10⁻¹²); its "
    "cause is not established, and E5 is informational. The coral bleaching pilot ran with the D8 tolerance before the "
    "author ruled it (ruling AY3). On coral bleaching, gate E3a compares no data file before the labels are read (its "
    "static file list is empty, and its label-file list cannot be read before the labels), and gate E10 checks the "
    "exported trees on one sampled location's router fit rows and test rows only (on coral bleaching one survey "
    "visit's router fit rows and test row; on forest loss every sampled location). On PM2.5, NDVI and burned "
    "fraction, a dataset package file that had moved with the machine's reinstall (RP2) was accepted through a "
    "recorded path map, which gate E3m checks against the locks' records (ruling AY2). <!-- S3.13 write-up, "
    "2026-11-17: fact A12 (the rebuild of the tree bank with its correctors and placebos by the run's own engine "
    "snapshot, which read the saved adoption and guard outcome; S-EXACT for every model; E5 pass false on all five "
    "problems, informational, \"cause not established\"; coral E3a's static file list the SHA-256 of an empty list and "
    "its target file list not_before_read), fact A10 (D8: at most 1e-12 relative, arcsine arms only), fact A9 (ruling "
    "AY3: the coral pilot had already run with this tolerance); Table S3.21 rows E3a, E3m and E10 as the agreed "
    "tables give them; rulings AY2 and AY3; SHAP protocol sections 4 and 11; RP2 for the reinstall --> | all | S3.13 "
    "(Table S3.20 and Table S3.21) | facts A9, A10, A12; Part 628; rulings AY2, AY3 |")
PH.append(
    "| PH24 | Left out of the SHAP comparison, with the reasons S3.13 gives: the one-input calibration maps of a "
    "product or index (MERRA-2 PM2.5 lagged one month, in the same month and as the placebo entry; VT0007, "
    "calibrated; NOAA Coral Reef Watch's degree heating weeks, the nowcast rule), whose attribution would all fall on "
    "that one input; VT0007 as shipped and frozen, which are not functions of the rows' input columns; CAMS EAC4 and "
    "the burned-fraction published rivals, which were never run (rulings AG1 and AS); the naive baselines, which have "
    "no input feature; and the Kraft LSTM (NDVI), which is not bit-reproducible without its original deep-learning "
    "library and stays out under the default of the protocol's decision D7, which the author has not ruled (its skill "
    "guard failed at the nowcast). Rivals that run only at forecast leads, among them the Coral Reef Watch Outlook, are "
    "outside a comparison of the nowcast. Ridge outside coral bleaching and BARDL were explained through loaders added after "
    "the protocol's sample and statistics sections were frozen, with no change to them. BARDL reads three variables "
    "(nine columns) by design; the author kept it in the NDVI main set (ruling BA1) after the NDVI comparison had "
    "been computed and before any NDVI statistic was read, and beyond its inputs its top-k sets follow name order "
    "(ruling BB3). <!-- S3.13 write-up, 2026-11-17: Table S3.18 b (the rivals and naive baselines left out, with "
    "their reasons, and its note on the rivals that run only at forecast leads, among them the CRW Outlook); SHAP protocol sections 7 and 12 (D7: \"left out until ruled (not bit-reproducible)\"); ruling "
    "AY's lead paragraph (the protocol's other decisions keep their defaults, \"among them D7, the Kraft LSTM left "
    "out\"); fact RH4 (the Kraft LSTM's skill guard failed); fact A15 (BARDL's nine columns of three variables; the "
    "two loaders added after the freeze, sections 3 and 8 unchanged; BA1); rulings BA1 (\"The answer came after the "
    "NDVI comparison had been computed and before any NDVI statistic was read\") and BB3 --> | all | S3.13 (Table "
    "S3.18 and Table S3.24) | facts A15, RH4; Part 628; rulings AG1, AS, AY, BA1, BB3 |")
PH.append(
    "| PH25 | treeroute v1's B1 sensitivity (ruling BA3) explains treeroute v1 on the same sample against all of "
    "each location's router fit rows at or before the cut, not only those of the explained row's calendar month, on "
    "PM2.5, NDVI and burned fraction; it is not defined on coral bleaching, and on forest loss, which is annual, its "
    "background equals the main one, so its run had to repeat the main run, and it did exactly (largest difference 0 "
    "at both levels). The author ruled it after every main comparison had been computed and before any agreement "
    "statistic of the PM2.5, NDVI, burned-fraction or forest-loss comparisons had been read. The protocol defined B1 "
    "but named none of its numbers: an agent wrote the list of B1 numbers before the first B1 run started and added "
    "the forest-loss run as a check of the B1 code, and the list was recorded in the protocol after the runs had "
    "started, with rules added then. B1 is labelled a sensitivity and kept apart: it enters no Kendall's W, consensus, "
    "main-set statistic or main-text row, and it is compared with no rival. The protocol lists every B1 player's "
    "importance, share and signed mean, each with its interval, for S3.13; S3.13 prints the pair statistics and B1's "
    "family shares, top 3, own-history share and top 10, and gives the per-player values through the re-computation's "
    "results file. <!-- S3.13 write-up, 2026-11-17: ruling BA3 and BA's lead paragraph (no statistic of the fire, "
    "PM2.5, defo or NDVI comparisons had been read; the list is the agent's, written on 2026-11-15 at 23:03, local "
    "time, before the first B1 run started, 23:06; the defo run added by the agent with the command, as a check of "
    "the B1 code); SHAP protocol section 10 (the B1 list, recorded 2026-11-16 at 02:08, \"with the rules that section "
    "10 names as added then\"; kept apart) and section 14; facts A9 (the B1 command), A21 (forest loss's identity "
    "check: largest difference 0 at both levels) and A22 (every B1 player's importance, share and signed mean, with "
    "its interval, in the re-computation's results file, key b1; S3.13 prints only the top 3 and top 10 of them). "
    "\"The re-computation's results file\", as S3.13 and Table S3.29 call it, not \"the archived results file\", "
    "because the archive is still a plan --> | PM2.5, NDVI, burned fraction, forest loss | S3.13 (Table S3.28, Table "
    "S3.29 and Table S3.30) | facts A9, A21, A22; Part 628; ruling BA3 |")
PH.append(
    "| PH26 | Post hoc (ruling BA2), before any number of the comparison was used, two implementations written "
    "independently from the protocol, each blind to the comparison script and its outputs (they read only the "
    "structural fields of each problem's comparison record and its saved region draws), re-computed the "
    "comparison's numbers and the B1 numbers, and a reconciliation compared them with each other and with the "
    "comparison's output files: every number that those files hold and both implementations also hold agrees within "
    "10⁻⁹, except in three explained cases. The comparison script departs from the protocol in three ways that bear on "
    "what is reported: it writes neither treeroute v1's top 3 nor its own-history share with its interval in burned "
    "fraction's main-text row, it gives the sign agreement no interval, and it gives no feature-level family-share "
    "distance. By ruling BB1 these entries come from the re-computation, so in them S3.13 and Table 9 differ from the "
    "comparison's files, and three sign-agreement intervals of burned fraction rest on 64, 1,140 and 1,380 of the "
    "2,000 draws; by ruling BB2 the feature-level family-share distance repeats the variable-level value. No analysis "
    "script was changed or run again for this. The author's six presentation rulings (BB1-BB6) came after the "
    "re-computation, when an agent's messages to the author had quoted some of its statistics, rounded. <!-- S3.13 "
    "write-up, 2026-11-17: facts A23 (two implementations blind to compare_shap.py, shapv1_stats.py and the compare "
    "outputs; agreement within 1e-9; the three explained cases; the three departures and two latent ones; no SHAP "
    "script edited or run), A24 (the three intervals on 64, 1,140 and 1,380 finite draws of the 2,000) and A26 (c) (the "
    "agent's chat messages had quoted some of the round's statistics, rounded, before the answer of the author, not quoted, ruling BB); "
    "rulings BA2, BB1 and BB2 and BB's lead paragraph --> | all | Table 9; S3.13 | facts A10, A23, A24, A26; Part 628; "
    "rulings BA2, BB1, BB2 |")
PH.append(
    "| PH27 | Coral bleaching's table of the main-text statistics (AW4_table.md, the current coral comparison's "
    "table, written on 2026-11-13 at 00:06) was read by an agent on 2026-11-13 at about 15:31, before the independent "
    "re-computation; the re-computation's implementers A and B never opened it (local times, UTC+1, as the records "
    "give them; S4.2 gives them in UTC). The read was first recorded in the SHAP protocol's change log on 2026-11-16. "
    "It is the subject of question C10 to the author (the records' \"owner question C10\"), which ruling BB6 settles: "
    "S3.13 discloses the read. <!-- S3.13 "
    "write-up, 2026-11-17: the row that Table S3.22's note d and S3.13's Presentation paragraph point to (\"Supplement "
    "S1.7 records who read it\"); fact A25 (written 2026-11-13 at 00:06, file time 00:06:12; read at about 15:31; "
    "implementers A and B never opened it) and fact A26 (b) (first recorded in the protocol's change log in its entry "
    "recorded on 2026-11-16 at 02:08; owner question C10 asked on 2026-11-16 at about 01:50); ruling BB6 (\"was read "
    "by an agent on 2026-11-13 at about 15:31, before the independent re-computation, and that its implementers A and "
    "B never opened it\"); in UTC the table was written on 2026-11-12 at 23:06 and read at about 14:31 (fact A28) --> "
    "| coral bleaching | S3.13 (Table S3.22, note d) | facts A25, A26; Part 628; ruling BB6 |")
PH.append(
    "| PH28 | The burned-fraction comparison written on 2026-11-13, before Ridge was added (four models), was opened "
    "once by an agent the same day, before the Ridge loader was built, for its layout only, and what was read held "
    "no agreement statistic: with treeroute v1 alone in the main set, its two main-text files hold only Kendall's W, "
    "undefined, the reference link, a note on the cross-link pairs and the model lists, and of its comparison record "
    "only the models, the main set and the declined "
    "list were read; its pair, importance and family files were not opened. The author had not opened it before "
    "Ridge was added (ruling AZ1). The Ridge loader repeats the rival board's own scoring bit for bit, so it had no "
    "free choice. <!-- "
    "S3.13 write-up, 2026-11-17: fact A26 (a) (opened on 2026-11-13 at about 21:20, local time, for its layout: the "
    "folder listing, AW4_main_row.json, AW4_table.md, and the models, main set and declined list of per_lead.json; "
    "AW3_table.md, pairs.parquet, importance.parquet, families.parquet and the bootstrap files not opened; the author's "
    "answer, not quoted (ruling AZ1), 2026-11-14 at about 04:35); fact A9 (the comparison of 2026-11-13 21:18, four models, without "
    "Ridge); ruling AZ1; SHAP protocol section 14, entry of 2026-11-14. S3.13's \"When and why\" states AZ1 only --> | "
    "burned fraction | S3.13 (in part) | facts A9, A26; Part 628; ruling AZ1 |")
PH.append(
    "| PH29 | Record conflict: the SHAP protocol describes coral bleaching's background (B2) as \"other sites' "
    "visits\", but of its 50,000 background survey visits (50 per explained survey visit), 980 are earlier visits at "
    "the explained survey visit's own reef site (for 415 of the 1,000 explained survey visits), and none is dated on "
    "or after its explained survey visit. The paper calls the background a pool of earlier nearby survey visits. "
    "<!-- S3.13 write-up, 2026-11-17: fact A11 "
    "(the protocol's \"other sites' visits\", PROTOCOL.md section 5, lines 375 and 381-382, and section 10, \"Not "
    "claimed\"; 980 of 50,000 at the same reef site, in 415 of the 1,000 sample rows; none dated on or after the "
    "explained visit; from paper/supp_build/s3_13/_brief/lead_checks/verify_v5_claims_out.txt). The protocol's own "
    "lines are not edited; the correction of its wording is the dated entry of 2026-11-17 that this write-up adds to "
    "its change log (staged separately). S3.13 gives the background and the count, not the protocol's wording --> | "
    "coral bleaching | S3.13 (in part) | fact A11; Part 628 |")
PH.append(
    "| PH30 | The tables of S3.13 and Table 9 were built twice from the stored values, each printed number formatted "
    "once, by two independent builders under one written specification, then reconciled with each other and with the "
    "comparison's own printed tables, and checked; versions 2 to 5 reworded captions, notes, labels and cells after "
    "four checks, and no number changed. The two builders' final tables are byte-identical. <!-- S3.13 write-up, "
    "2026-11-17: fact A27 (paper/supp_build/s3_13/reconcile/tables_agreed.md line 1; the briefs; "
    "paper/supp_build/s3_13/_brief/reads_tables.md; the SHA-256 of both builders' tables.md and cells.json and of the "
    "agreed copies). S3.13's header comment (stripped at submission) and Table 9's file comment say it; no visible "
    "text outside S1 does --> | all | S1 only | fact A27; Part 628 |")

PH21_END = "| all | S3.12; S5.3 | facts V3, K90, A8; Part 625; ruling AN2 |\n"
s1 = rep(s1, PH21_END, PH21_END + "".join(r + "\n" for r in PH), "S1.7 rows")

S17_OLD = "it gives no number, and its values are in Table 7 note (c) and S3.11. -->"
S17_NEW = ("it gives no number, and its values are in Table 7 note (c) and S3.11. PH22-PH30 were added in the S3.13 "
           "write-up (2026-11-17) for the post hoc SHAP comparison of Part 628 (rulings AW, AY, AZ1, BA and BB): no "
           "recomputed values; every number in them is from the facts each row's comment names (A9-A27, final, post "
           "hoc (Part 628)), printed as the fact prints it. PH27 is the row that Table S3.22's note d and S3.13 point "
           "to (ruling BB6). PH25 gives B1's per-player values through the re-computation's results file, as S3.13 "
           "does. -->")
s1 = rep(s1, S17_OLD, S17_NEW, "S1.7 comment")

RP18_OLD = "the audit's SUMMARY.txt holds the four AUDIT and the two CHALLENGE reports; fact A3 --> They chose the PM2.5 trend cut points"
RP18_NEW = (
    "the audit's SUMMARY.txt holds the four AUDIT and the two CHALLENGE reports; fact A3 --> For the post hoc SHAP "
    "comparison (Part 628; PH22-PH30), agents designed the analysis in a design workflow with adversarial reviews and "
    "wrote its protocol, its scripts with their smoke tests, and the commands with which the author ran its long "
    "computations, and later the Ridge and BARDL loaders, each reviewed; they ran the smoke tests and checks; in a "
    "further workflow they carried out the independent re-computation (a specification writer, implementers A and B, "
    "a reconciler and checkers), and an agent wrote its report from the reconciler's text, with an addendum; agents "
    "wrote the specification of the S3.13 tables and Table 9, built them as builders A and B, independently, and "
    "reconciled and checked them (PH30); and agents wrote and checked this write-up of the comparison. The model list "
    "above ends with fact M14b's scan of 2026-11-10, before this analysis. <!-- S3.13 write-up, 2026-11-17: "
    "engine/PENDING_PARTS.md Part 628 (\"A design workflow (8 agents: 4 maps, the design, 2 adversarial reviews, the "
    "fix ...) wrote everything under D:/treeroute/analysis/shap_v1: PROTOCOL.md v3, RUN_COMMANDS.md, scripts/ and "
    "smoke/\"); SHAP protocol section 1 (\"The long computations are commands for the owner (RUN_COMMANDS.md)\") and "
    "section 14 (the BARDL and ridge loaders, built and reviewed after the freeze; round 14 \"ran as one workflow of "
    "seven agents\": a spec writer, implementers A and B, a reconciler, a blindness skeptic, a numbers skeptic and a "
    "reconciliation skeptic, then the report checkers; \"The agent recovered the text from the refused Write call ... "
    "and wrote report.md ..., with an addendum of its own\"); paper/supp_build/s3_13/_brief/reads_tables.md (the table "
    "rounds: a spec writer and spec fixers, builders A and B, a reconciler, a checker and the lead); facts A9, A23 and "
    "A27; fact M14b (the scan of 2026-11-10, whose list ends with \"this session continues\"). No number is printed "
    "in this clause but the scan's date --> They chose the PM2.5 trend cut points")
s1 = rep(s1, RP18_OLD, RP18_NEW, "RP18 clause")

RP18_SRC_OLD = ("| all | 2.9; S4.1; S4.9 (in part); S4.10 | facts S5, A5, M55a, L6, RH9, C6, M14b, D24, D46; rulings A, AE3, "
                "AL1, Z1, AT11, AT17 (f), AT21, AU1; outline decision O8; Parts 582 and 611; "
                "engine/OWNER_RULINGS_2026-09-28.md section A |")
RP18_SRC_NEW = ("| all | 2.9; S4.1; S4.9 (in part); S4.10 | facts S5, A5, M55a, L6, RH9, C6, M14b, D24, D46, A9, A23, A27; "
                "rulings A, AE3, AL1, Z1, AT11, AT17 (f), AT21, AU1, BA2; outline decision O8; Parts 582, 611 and 628; "
                "engine/OWNER_RULINGS_2026-09-28.md section A |")
s1 = rep(s1, RP18_SRC_OLD, RP18_SRC_NEW, "RP18 source")

s1 = rep(s1, "| post hoc | 21 |\n", "| post hoc | 30 |\n", "S1.10 post hoc")
s1 = rep(s1, "| **Total** | **170** |\n", "| **Total** | **179** |\n", "S1.10 total")
s1 = rep(s1, "PH21 added 2026-10-28 (post hoc 20 to 21, total 169 to 170; Part 625), counted by hand. -->",
         "PH21 added 2026-10-28 (post hoc 20 to 21, total 169 to 170; Part 625), counted by hand. PH22-PH30 added "
         "2026-11-17 in the S3.13 write-up (post hoc 21 to 30, total 170 to 179; Part 628), counted by script from this "
         "file's table rows, by section; the other eight categories are unchanged. -->",
         "S1.10 comment")
save("paper/draft/S1_disclosures.md", s1)

# ================================================================ S4
s4 = load("paper/draft/S4_provenance.md")

S4_HIST = (
    "S3.13 write-up, 2026-11-17 (pre-edit copy draft/_snapshots/@@SNAP@@/): for the post hoc SHAP comparison of "
    "Part 628 (rulings AW, AY, AZ1, BA and BB; Supplement S3.13 and main-text Table 9). Table S4.13 gains rows AW, "
    "AX, AY, AZ, BA and BB from the rulings file's sections AW to BB, its last lettered sections, so S4.10 says "
    "\"every lettered ruling ..., A to BB\" and its pending marker for sections AW and AX is closed, S4.1's "
    "Identifiers item says \"A to BB\", and the opening paragraph again says \"every lettered ruling\". The S4.2 "
    "timeline gains ten rows for 2026-11-12 to 2026-11-16, in UTC with the local time in parentheses, and its opening "
    "paragraph one sentence; S4.1's Times item adds that the SHAP analysis's records give local time, UTC+1 (fact "
    "A28: each file's last write time equals the time its record gives, and its UTC file time is one hour earlier). "
    "Table S4.11 gains the Part 628 row (the 17 SHAP analysis scripts and the two S3.13 table builders' "
    "build_tables.py), its caption names Part 628's folders, and its comment gives their full SHA-256, hashed "
    "read-only on 2026-11-17; Table S4.14 gains the 19 full values in two groups, and S4.12 and the table's comment "
    "give the new date and counts (254 values, 253 distinct, no two sharing an 8-digit prefix; a recount found one "
    "value more before this pass than the comment's earlier count). Visible numbers "
    "added: the rulings' dates and the numbers in their summaries (the rulings file; facts A10 and A28), the "
    "timeline's dates and times (fact A28) and the 19 hash prefixes (Table S4.14). No existing hash, time or locked "
    "verdict changed; CRLF line endings kept. "
)
s4 = rep(s4, "<!-- GPCC download outcome, fixes after the checks (2026-11-13; pre-edit copy draft/_snapshots/20261113T1440Z_gpcc/fix/paper/draft/S4_provenance.md): ",
         "<!-- " + S4_HIST + "GPCC download outcome, fixes after the checks (2026-11-13; pre-edit copy draft/_snapshots/20261113T1440Z_gpcc/fix/paper/draft/S4_provenance.md): ",
         "S4 history")

s4 = rep(s4, "and the lettered rulings of the author (S4.10). <!-- Ruling AV (2026-11-13), close-out fixes: \"every\" dropped,",
         "and every lettered ruling of the author (S4.10). <!-- S3.13 write-up (2026-11-17): \"every\" restored, as Table "
         "S4.13 now has rows AW to BB, through the rulings file's last lettered section, BB --> <!-- Ruling AV "
         "(2026-11-13), close-out fixes: \"every\" dropped,",
         "S4 intro every")

TIMES_OLD = ("- **Times** are UTC. Where a record stores local time (UTC+3, the zone of the run machine), the local time "
             "follows in parentheses. <!-- read 2026-10-27:")
TIMES_NEW = ("- **Times** are UTC. Where a record stores local time, the local time follows in parentheses: UTC+3, the "
             "zone of the run machine, in the records of the runs and rival boards, and UTC+1 in those of the SHAP "
             "analysis of 2026-11-12 to 2026-11-16 (S4.2). <!-- S3.13 write-up (2026-11-17): fact A28: the SHAP "
             "analysis's records (its protocol, RUN_COMMANDS.md, SAMPLE_REGISTER.txt and the rulings file) give local "
             "time, UTC+1; each of the files A28 names was last written at the local time its record gives, and its UTC "
             "file time is one hour earlier. The bullet had read \"Where a record stores local time (UTC+3, the zone of "
             "the run machine), the local time follows in parentheses.\" --> <!-- read 2026-10-27:")
s4 = rep(s4, TIMES_OLD, TIMES_NEW, "S4.1 Times")

s4 = rep(s4, "A ruling is named by its letters (A to AV, Table S4.13); <!-- Round 4 (2026-11-11): ruling AU of 2026-11-11 added -->",
         "A ruling is named by its letters (A to BB, Table S4.13); <!-- S3.13 write-up (2026-11-17): rulings AW to BB "
         "added, in step with S4.10 --> <!-- Round 4 (2026-11-11): ruling AU of 2026-11-11 added -->",
         "S4.1 Identifiers")

S42_INTRO_OLD = "The coral bleaching protocol document was signed by the author after its run (S4.9). <!-- P7 -->\n"
S42_INTRO_NEW = ("The coral bleaching protocol document was signed by the author after its run (S4.9). <!-- P7 --> The rows "
                 "from 2026-11-12 on are the post hoc SHAP comparison of Supplement S3.13 (Part 628), which ran after "
                 "every lock and test-label opening above. <!-- S3.13 write-up, 2026-11-17: ruling AK; facts A9 and A28 "
                 "-->\n")
s4 = rep(s4, S42_INTRO_OLD, S42_INTRO_NEW, "S4.2 intro")

TL = [
    "| 2026-11-12 | Ruling AW: a post hoc SHAP analysis of treeroute v1 and of every rival it can be run on, on all "
    "five problems (AW1-AW5); its protocol written the same day, version 1 before any SHAP value was computed on a "
    "real data row and version 3 after the smoke tests and two design reviews, with its scripts and run commands "
    "(Part 628) | OWNER_RULINGS_2026-10-06.md AW; `analysis/shap_v1/PROTOCOL.md`, section 14 |",
    "| 2026-11-12 22:49:45 to 23:06:12 (23:49:45 to 00:06:12 local, the end on 2026-11-13) | SHAP pilot on the coral "
    "bleaching nowcast, the author's command: the coral sample registered at the start, which froze the protocol's "
    "sections on the sample and the statistics; every rebuild gate passed except the informational E5; the coral "
    "comparison written at the end, its table AW4_table.md among its files | `analysis/shap_v1/SAMPLE_REGISTER.txt`; "
    "PROTOCOL.md, sections 1 and 14 |",
    "| 2026-11-13 | Rulings AX (the GPCC download, AX1) and AY: the SHAP scope, the nowcast of each problem only (AY1); "
    "the recorded path map (AY2); the D8 tolerance, with which the coral pilot had already run (AY3) | "
    "OWNER_RULINGS_2026-10-06.md AX, AY |",
    "| 2026-11-13, about 14:31 (15:31 local) | Coral bleaching's comparison table AW4_table.md read by an agent, "
    "before the independent re-computation; first recorded in the SHAP protocol's change log on 2026-11-16 (ruling "
    "BB6; Supplement S1, PH27) | PROTOCOL.md, section 14 |",
    "| 2026-11-13 16:23:16 to 2026-11-15 18:11:39 (17:23:16 to 19:11:39 local) | SHAP runs of the burned-fraction, "
    "PM2.5, forest-loss and NDVI nowcasts, the author's commands: samples registered 2026-11-13 16:23:16 and 20:44:18 "
    "and 2026-11-14 03:37:20 and 13:37:52; Ridge outside coral bleaching and BARDL explained through loaders added "
    "after the protocol's sample and statistics sections were frozen; the burned-fraction comparison of 2026-11-13 20:18 (four models, without Ridge) opened by an "
    "agent for its layout only, at about 20:20 (Supplement S1, PH28); the last comparison (NDVI, five models) written "
    "at the end | SAMPLE_REGISTER.txt; PROTOCOL.md, section 14; `analysis/shap_v1/RUN_COMMANDS.md`, section 2 |",
    "| 2026-11-14 | Ruling AZ1, answered at about 03:35 (04:35 local): the author had not read the burned-fraction "
    "comparison of 2026-11-13 20:18 before Ridge was added | OWNER_RULINGS_2026-10-06.md AZ |",
    "| 2026-11-15 | Ruling BA: BARDL kept in the NDVI main set (BA1) and the comparison results may be opened (BA2), "
    "answered at about 18:45 (19:45 local), when no agreement statistic of the burned-fraction, PM2.5, forest-loss or "
    "NDVI comparisons had been read; treeroute v1's B1 sensitivity run as planned (BA3), answered at about 21:50 "
    "(22:50 local) | OWNER_RULINGS_2026-10-06.md BA |",
    "| 2026-11-15 22:06:16 to 2026-11-16 07:14:14 (23:06:16 to 08:14:14 local) | treeroute v1's B1 runs, the author's "
    "command, in the order forest loss (a check of the B1 code), burned fraction, PM2.5 and NDVI, all finished; the "
    "list of the B1 numbers "
    "to report written at 22:03 (23:03 local), before the first run | RUN_COMMANDS.md, section 2; PROTOCOL.md, "
    "sections 10 and 14 |",
    "| 2026-11-16 16:09 to about 18:20 (17:09 to about 19:20 local) | Independent re-computation of the SHAP "
    "comparison's numbers (ruling BA2) by two implementations written from the protocol, blind to the comparison "
    "script and its outputs, and a reconciliation: every number of the comparison's files that both implementations "
    "hold agrees within 10⁻⁹ (Supplement S3.13) | PROTOCOL.md, section 14; `analysis/shap_v1/verify_v1/` |",
    "| 2026-11-16 19:59 (20:59 local) | Ruling BB: how Supplement S3.13 and Table 9 present the SHAP comparison "
    "(BB1-BB6) | OWNER_RULINGS_2026-10-06.md BB |",
]
assert len(TL) == 10
AU_ROW_END = ("<!-- Ruling AV (2026-11-13), check fixes: the parenthesis after the decision list tells its Part B from the "
              "burned-fraction published rivals' Part B (S4.7.4, S4.11) --> |\n")
s4 = rep(s4, AU_ROW_END, AU_ROW_END + "".join(r + "\n" for r in TL), "S4.2 rows")

TL_COMMENT_ANCHOR = "\n\n## S4.3 Engine versions\n"
TL_COMMENT = ("\n<!-- S3.13 write-up (2026-11-17): the ten rows of 2026-11-12 to 2026-11-16 are the post hoc SHAP comparison "
              "(Part 628). Its records give local time, UTC+1 (fact A28: each file named there was last written at the "
              "local time its record gives, and its UTC file time is one hour earlier); the times are converted to UTC, "
              "with the local time in parentheses. Sources: engine/OWNER_RULINGS_2026-10-06.md sections AW to BB (dates "
              "from the headings; the answer times of AZ1, BA1-BA2, BA3 and BB from their lead paragraphs); "
              "D:/treeroute/analysis/shap_v1/PROTOCOL.md sections 1, 10 and 14, RUN_COMMANDS.md section 2 (the B1 "
              "command's status) and SAMPLE_REGISTER.txt (the registration stamps); the file times of the coral sample "
              "manifest, the coral and NDVI per_lead.json and the logs that A28 names; facts A9, A25, A26 and A28. The "
              "rulings rows give the rulings file's dates, as the rows above do; AZ1, BA and BB fall on the same date in "
              "UTC, and the records give no time for AW, AX and AY. \"Two design reviews\", \"four models\" and \"five "
              "models\": A28 and A26 -->")
s4 = rep(s4, TL_COMMENT_ANCHOR, TL_COMMENT + TL_COMMENT_ANCHOR, "S4.2 comment")

# Table S4.11
s4 = rep(s4, "**Table S4.11. Post hoc analysis code** (files in `analysis/paper_posthoc/`; full values in Table S4.14).",
         "**Table S4.11. Post hoc analysis code** (files in `analysis/paper_posthoc/`, except those of Part 628, whose "
         "folders its row names; full values in Table S4.14).",
         "S4.11 caption")
files_cell = ("scripts/bardl_shap.py; compare_shap.py; make_sample.py; ridge_shap.py; rival_shap.py; run_shap.py; "
              "shapv1_common.py; shapv1_rows.py; shapv1_stats.py; shapv1_treeshap.py; tr_rebuild.py; tr_shap.py; "
              "scripts/tests/diag_coral_exactness.py; smoke_bardl.py; smoke_ridge.py; smoke_unit.py; smoke_world.py; "
              "A/scripts/build_tables.py; B/scripts/build_tables.py")
hash_cell = "; ".join(p8(k) for k in SCRIPTS + BUILDERS)
ROW628 = ("| 628 | Post hoc SHAP comparison of treeroute v1 and its rivals at the nowcast (rulings AW, AY, AZ1, BA and BB): "
          "the analysis scripts (sample, rebuild, SHAP values, the rivals' loaders and the comparison), with their "
          "smoke and diagnosis tests, in `analysis/shap_v1/`, and the scripts of the two independent builders of the "
          "S3.13 tables and Table 9, in `paper/supp_build/s3_13/`. Results: Supplement S3.13 | " + files_cell + " | "
          + hash_cell + " |")
ROW625_END = "twelve row files (Table S4.14) | 9e674313; 90deaa81; df5d0306; 3d04553c; 42a97b0f; 258f5c1f; 6f1fdd71; 212dcce9 |\n"
s4 = rep(s4, ROW625_END, ROW625_END + ROW628 + "\n", "S4.11 row")

full_list = "; ".join("%s %s" % (k, full(k)) for k in SCRIPTS) + "; and of the table builders (paper/supp_build/s3_13/) " + \
    "; ".join("%s %s" % (k, full(k)) for k in BUILDERS)
S411_COMMENT_OLD = "No alarm number is given in this supplement (ruling AE3; decision O6). -->\n\n**The coral bleaching 2017-2020 sensitivity row (Part 627).**"
S411_COMMENT_NEW = ("No alarm number is given in this supplement (ruling AE3; decision O6). Part 628 (added 2026-11-17, S3.13 "
                    "write-up): the SHA-256 of each file's bytes, read-only, by a script "
                    "(paper/supp_build/s3_13/stage/_scripts/s1s4/hash_files.py) on 2026-11-17, under "
                    "D:/treeroute/analysis/shap_v1/: " + full_list + ". The four that the SHAP protocol's change log names "
                    "match it (bardl_shap.py 6bfc9aaf, smoke_bardl.py 0f7de758, ridge_shap.py 866fd329, smoke_ridge.py "
                    "c48f3f66), and the scripts' file times are those its entry of 2026-11-14 gives (2026-11-12, and "
                    "2026-11-13 and 2026-11-14 for the four loader and smoke files); the builders' scripts are those of "
                    "version 5 of the tables (2026-11-17). PROTOCOL.md, the analysis's specification, is not listed, "
                    "because this write-up adds a dated entry to its change log, which changes its hash; the independent "
                    "re-computation's files are in analysis/shap_v1/verify_v1/ (Supplement S3.13 names its results file) "
                    "and are not hashed here. No SHAP number is given in this supplement. -->\n\n**The coral bleaching "
                    "2017-2020 sensitivity row (Part 627).**")
s4 = rep(s4, S411_COMMENT_OLD, S411_COMMENT_NEW, "S4.11 comment")

# S4.10 sentence and the pending marker
S410_OLD = ("Table S4.13 lists the lettered rulings in the three rulings files, A to AV. [PENDING: the rulings file's "
            "sections AW, of 2026-11-12, and AX, of 2026-11-13, are added to this table and to the S4.2 timeline in a "
            "later pass] <!-- GPCC download outcome")
S410_NEW = ("Table S4.13 lists every lettered ruling in the three rulings files, A to BB. <!-- S3.13 write-up "
            "(2026-11-17): rows AW, AX, AY, AZ, BA and BB added from engine/OWNER_RULINGS_2026-10-06.md sections AW to "
            "BB, the file's last lettered sections, and the S4.2 timeline gains them, so \"every\" is restored and the "
            "pending marker is closed; the sentence had read \"Table S4.13 lists the lettered rulings in the three "
            "rulings files, A to AV. [PENDING: the rulings file's sections AW, of 2026-11-12, and AX, of 2026-11-13, "
            "are added to this table and to the S4.2 timeline in a later pass]\" --> <!-- GPCC download outcome")
s4 = rep(s4, S410_OLD, S410_NEW, "S4.10 sentence")

R413 = [
    "| AW | 2026-11-12 | A post hoc SHAP analysis of treeroute v1's runs of all five problems is added to the paper, "
    "labelled post hoc wherever it appears and changing no reported headline number; the fitted trees were not kept, "
    "so they are rebuilt first and must reproduce the saved predictions; this amends outline decision O3 as confirmed "
    "by AT17 (e), which had left SHAP out of v1 (AW1); SHAP is also run on every rival it can be run on, and the paper "
    "says which were left out and why (AW2); a table shows how the models disagree, problem by problem (AW3); several "
    "agreement statistics, Spearman's rank correlation among them, with uncertainty from a bootstrap over regions "
    "(AW4); a fixed sample of 1,000 test rows per problem and lead in scope, the same rows for every model, the scope "
    "still the author's choice (AW5). | answers to the question \"Add SHAP to the paper now?\": the answers of the author, not quoted (ruling AW1); "
    "for AW2-AW4: a message of the author, "
    "not quoted "
    "(rulings AW2-AW4); for AW5: the answer of the author, not quoted (ruling AW5) <!-- "
    "Sources: engine/OWNER_RULINGS_2026-10-06.md, section AW (heading and items AW1-AW5); AW5's 1,000 rows: fact A10. "
    "Row added in the S3.13 write-up, 2026-11-17 --> |",
    "| AX | 2026-11-13 | Fourth batch, the author's answer to item 1 of a decision list of 13 items: NOAA's own October "
    "2026 copy of one SPI file, gpcc-spi-gamma-01.nc, is read to find the GPCC product behind the SPI files, which "
    "replaces the premise of AV22 (AX1); read the same day, the whole file names no GPCC product, version or DOI, and "
    "by the lead agent's reading, since the list did not say what follows, the paper states that the product is not "
    "recorded (Supplement S9.6, item 3). Items 2-13 are not answered. | the answer of the author, not quoted (ruling AX1), after a question "
    "of the author, not quoted; while the file was being fetched, a second message, "
    "not quoted <!-- Sources: engine/OWNER_RULINGS_2026-10-06.md, section AX (heading, lead paragraph and AX1; the "
    "list is _archive_plan/OWNER_DECISIONS_2026-11-13.md); PAPER_FACTS L7, dated note of 2026-11-13. Row added in the "
    "S3.13 write-up, 2026-11-17 --> |",
    "| AY | 2026-11-13 | SHAP decisions: scope (i), the nowcast of each problem only, the coral bleaching pilot already "
    "run included, where the agent had recommended scope (ii) (AY1); for PM2.5, NDVI and burned fraction, the moved "
    "static table of the dataset package is hashed under the run's recorded engine path and accepted by gate E3m only "
    "when its content SHA-256, size and time stamp equal the locks' records (AY2); the D8 tolerance, a relative "
    "difference of at most 10⁻¹² (a true relative bound) on arcsine arms only, licensed by gate E5a, in place of bit "
    "identity, with which the author had already run the coral pilot (AY3); the protocol's other decisions keep their defaults, among them D7 (the Kraft LSTM left out) "
    "and D10 (1,000 rows, all regions). | the answer of the author, not quoted (ruling AY) <!-- Sources: engine/OWNER_RULINGS_2026-10-06.md, "
    "section AY (heading, lead paragraph and AY1-AY3); 10⁻¹² and 1,000: fact A10. Row added in the S3.13 write-up, "
    "2026-11-17 --> |",
    "| AZ | 2026-11-14 | The author had not opened the burned-fraction SHAP comparison written on 2026-11-13 at 20:18 "
    "(21:18 local; four models, without Ridge) before Ridge was added; recorded in the SHAP protocol's change log "
    "(AZ1). | the answer of the author, not quoted (ruling AZ1) <!-- Sources: engine/OWNER_RULINGS_2026-10-06.md, section AZ (heading, lead paragraph and "
    "AZ1); the time in UTC: fact A28. Row added in the S3.13 write-up, 2026-11-17 --> |",
    "| BA | 2026-11-15 | SHAP results and treeroute v1's B1 sensitivity: BARDL stays in the NDVI main set, as the "
    "frozen plan has it (BA1, the protocol's decision D16), answered after the NDVI comparison had been computed and "
    "before any NDVI statistic had been read; the comparison results may be opened (BA2); treeroute v1's B1 "
    "sensitivity is run as planned on burned fraction, PM2.5 and NDVI and reported only as a labelled sensitivity in "
    "Supplement S3.13, never pooled with the main set (BA3). The list of B1 numbers is the agent's, written before the "
    "first B1 run started, and the agent added a forest-loss run as a check of the B1 code. | the answers of the author, not quoted (ruling BA); "
    "the second after a question, not quoted <!-- Sources: "
    "engine/OWNER_RULINGS_2026-10-06.md, section BA (heading, lead paragraph and BA1-BA3). Row added in the S3.13 "
    "write-up, 2026-11-17 --> |",
    "| BB | 2026-11-16 | SHAP presentation after the independent re-computation, the author's answer to six points, "
    "each the agent's proposed option: the numbers that the comparison script does not write (burned fraction's "
    "treeroute v1 top 3 and own-history share with its interval, and every sign-agreement interval) are taken from the "
    "re-computation, and the three intervals on fewer than 2,000 finite draws are printed with that number (BB1); the "
    "feature-level family-share distance is shown, the variable-level value repeated (BB2); NDVI's pairs with BARDL "
    "are kept, with a footnote on the name-order fill of its top-k sets (BB3); a family with no variable keeps its "
    "defined 0 with a label, the rivals' median has one label, \"median of the rivals\", and a note explains PM2.5's "
    "asymmetric RBO interval (BB4); the main models' top-10 shares and family shares have no intervals (BB5); S3.13 "
    "discloses that coral bleaching's comparison table was read before the re-computation, by an agent (BB6; "
    "Supplement S1, PH27). | the answer of the author, not quoted (ruling BB) <!-- Sources: engine/OWNER_RULINGS_2026-10-06.md, section BB (heading, lead "
    "paragraph and BB1-BB6); 2,000: facts A10 and A24. Row added in the S3.13 write-up, 2026-11-17 --> |",
]
AV_ROW_END = "Row added in the ruling AV pass, 2026-11-13. --> |\n"
s4 = rep(s4, AV_ROW_END, AV_ROW_END + "".join(r + "\n" for r in R413), "S4.13 rows")

S413_C_OLD = "and AU5-AU7 were added in round 5; the quotes above are those of the first AU pass. -->"
S413_C_NEW = ("and AU5-AU7 were added in round 5; the quotes above are those of the first AU pass. Rows AW-BB added in the "
              "S3.13 write-up (2026-11-17): from engine/OWNER_RULINGS_2026-10-06.md sections AW (heading and items "
              "AW1-AW5), AX (heading, lead paragraph and AX1), AY (heading, lead paragraph and AY1-AY3), AZ (heading, "
              "lead paragraph and AZ1), BA (heading, lead paragraph and BA1-BA3) and BB (heading, lead paragraph and "
              "BB1-BB6), the file's last lettered sections; the author's words as the headings and items quote them, "
              "in item order, checked by script against the file; the summaries follow the items' words, with \"the "
              "author\" for \"the owner\" (AT20) and AZ1's time in UTC with the local time (S4.1; fact A28); no number of "
              "the comparison is given. -->")
s4 = rep(s4, S413_C_OLD, S413_C_NEW, "S4.13 comment")

s4 = rep(s4, "(the Part 625 files on 2026-10-28; the Part 627 sensitivity row on 2026-11-10)",
         "(the Part 625 files on 2026-10-28; the Part 627 sensitivity row on 2026-11-10; the Part 628 files on 2026-11-17)",
         "S4.12 date")

G1 = "| **Post hoc SHAP comparison, Part 628: analysis scripts (`analysis/shap_v1/`; Table S4.11; read 2026-11-17)** | | |"
G2 = ("| **Post hoc SHAP comparison, Part 628: the S3.13 table builders' scripts (`paper/supp_build/s3_13/`; Table "
      "S4.11; read 2026-11-17)** | | |")
rows14 = [G1] + ["| %s | file | `%s` |" % (k, full(k)) for k in SCRIPTS] + [G2] + \
         ["| %s | file | `%s` |" % (k, full(k)) for k in BUILDERS]
LAST627 = "| run/coral_sens_2017_2020/headline/20261029_75f66839/test_preds.parquet | file | `26474c84991676abf7be0db5ee8b469c4ae51c91b26111435549b2f990705f62` |\n"
s4 = rep(s4, LAST627, LAST627 + "".join(r + "\n" for r in rows14), "S4.14 rows")

S414_C_OLD = ("the only 8-digit strings of the visible text with no entry here are dates and run-folder names (among them "
              "the new 20261029_75f66839) and f22a6a24. -->")
S414_C_NEW = ("the only 8-digit strings of the visible text with no entry here are dates and run-folder names (among them "
              "the new 20261029_75f66839) and f22a6a24. S3.13 write-up (2026-11-17): 19 values added for Part 628, the 17 "
              "scripts of D:/treeroute/analysis/shap_v1/scripts/ and scripts/tests/ and the two S3.13 table builders' "
              "build_tables.py (SHA-256 of each file's bytes, read-only, by "
              "paper/supp_build/s3_13/stage/_scripts/s1s4/hash_files.py). A recount by script on 2026-11-17 "
              "(paper/supp_build/s3_13/stage/_scripts/s1s4/count_s414.py) finds 235 values, 234 distinct, before this "
              "pass, one more than the count above gives (the one shared value is still coral's driver and static file "
              "lists); the difference is in that count, not in any value. With the 19, the table holds 254 values, 253 "
              "distinct, still with no two distinct values sharing an 8-digit prefix (checked by script on 2026-11-17 "
              "against every 8-digit hexadecimal string in this file); the visible text gains no other 8-digit string. "
              "-->")
s4 = rep(s4, S414_C_OLD, S414_C_NEW, "S4.14 comment")
save("paper/draft/S4_provenance.md", s4)

# ================================================================ PAPER_FACTS
pf = load("paper/PAPER_FACTS.md")
REV_OLD = "Copy of this sheet before the S3.13 write-up, 2026-11-17: paper/draft/_snapshots/@@SNAP@@/."
REV_NEW = ("Section 9 also gains A26-A28 (final, post hoc (Part 628)) for Supplements S1 and S4: what of the comparison's "
           "results was read before the independent re-computation and when the presentation rulings came (A26), how "
           "the S3.13 tables and Table 9 were built (A27), and the comparison's times in UTC (A28). "
           "Copy of this sheet before the S3.13 write-up, 2026-11-17: paper/draft/_snapshots/@@SNAP@@/.")
pf = rep(pf, REV_OLD, REV_NEW, "facts revised paragraph")

A26 = (
    "- **A26 (final, post hoc (Part 628)). What was read of the comparison's results before the independent "
    "re-computation, and when the presentation rulings came** (Supplement S1, PH26-PH28; local time, UTC+1, as the "
    "records give it; A28 gives UTC). (a) The burned-fraction comparison written on 2026-11-13 at 21:18 (four models, "
    "without Ridge) was opened once by an agent, on 2026-11-13 at about 21:20, before the Ridge loader was built, for "
    "its layout only: the folder listing, AW4_main_row.json, AW4_table.md, and the models, main set and declined list "
    "of per_lead.json. With treeroute v1 alone in the main set, the comparison script writes in those two AW4 files "
    "only Kendall's W, undefined (NaN), the reference link, the cross-link note and the model lists, every other cell "
    "empty; the comparison's other files (AW3_table.md, pairs.parquet, importance.parquet, families.parquet and the "
    "bootstrap files) were not opened. The author had not opened it before Ridge was added (ruling AZ1, answered on "
    "2026-11-14 at about 04:35), and the Ridge loader has no free choice: it repeats the rival board's own scoring bit "
    "for bit. (b) The read of coral bleaching's AW4_table.md on 2026-11-13 at about 15:31 (A25) was first recorded in "
    "the SHAP protocol's change log in its entry recorded on 2026-11-16 at 02:08 (\"Not recorded before\"); owner "
    "question C10, asked on 2026-11-16 at about 01:50, is answered by ruling BB6. (c) Before the author's answer, not quoted "
    "(rulings BB1-BB6; 2026-11-16 at 20:59), the agent's chat messages to the author (19:34 to 20:58) had "
    "summarized the re-computation and quoted some of its statistics, rounded. Sources: "
    "D:/treeroute/analysis/shap_v1/PROTOCOL.md section 14 (entry of 2026-11-14: owner question Q1 and the bullet that "
    "begins \"Separately, that comparison was opened once\"; entry of 2026-11-14 and 2026-11-15: its opening sentence "
    "and \"What was read\"; entry of 2026-11-16: \"What was read\"); engine/OWNER_RULINGS_2026-10-06.md sections AZ "
    "(lead paragraph, AZ1) and BB (lead paragraph, BB6).")
A27 = (
    "- **A27 (final, post hoc (Part 628)). How the S3.13 tables and Table 9 were built** (Supplement S1, PH30; RP18). "
    "Tables S3.18 to S3.30 and Table 9 were built twice from the stored values (the compare files, "
    "D:/treeroute/analysis/shap_v1/verify_v1/A/results.json, bardl_maxima.txt and the B1 runs' logs), each printed "
    "number formatted once, by two independent builders, A and B, each with its own script "
    "(paper/supp_build/s3_13/A/scripts/build_tables.py, SHA-256 " + p8("A/scripts/build_tables.py") + "..., and "
    "B/scripts/build_tables.py, " + p8("B/scripts/build_tables.py") + "...), under one specification "
    "(paper/supp_build/s3_13/spec/TABLE_SPEC.md, version 5); by their records the builders opened neither the "
    "comparison's printed tables (AW3_table.md, AW4_table.md) nor the re-computation's report. A reconciler compared "
    "the two builds with each other and, through its scripts, with the printed tables, and a checker checked each "
    "version. Versions 2 to 5 reworded captions, notes, labels and cells after four checks and changed no number. The "
    "final outputs of A and B and the agreed copy are byte-identical: A/tables.md, B/tables.md and "
    "reconcile/tables_agreed.md SHA-256 " + H["reconcile/tables_agreed.md"]["sha256"][:8] + "..., and A/cells.json, "
    "B/cells.json and reconcile/cells.json " + H["reconcile/cells.json"]["sha256"][:8] + "... (hashed read-only on "
    "2026-11-17 by paper/supp_build/s3_13/stage/_scripts/s1s4/hash_files.py). Sources: "
    "paper/supp_build/s3_13/reconcile/tables_agreed.md line 1; paper/supp_build/s3_13/_brief/brief_text.md (\"Goal\") "
    "and brief_tables.md (\"Goal\" and \"Rules\"); paper/supp_build/s3_13/_brief/reads_tables.md; the SHA-256 above.")
A28 = (
    "- **A28 (final, post hoc (Part 628)). The SHAP comparison's times in UTC** (Supplement S4.1 and S4.2, which print "
    "UTC with the local time in parentheses). The SHAP analysis's records (its protocol, RUN_COMMANDS.md, "
    "SAMPLE_REGISTER.txt and the rulings file) give local time, UTC+1: each of these files was last written at the "
    "local time the records give, and its UTC file time is one hour earlier (LastWriteTime and LastWriteTimeUtc, read "
    "on 2026-11-17 without opening the files): PROTOCOL.md and RUN_COMMANDS.md 2026-11-16 23:31:06 (22:31:06 UTC; \"recorded on "
    "2026-11-16 at 23:31\"); SAMPLE_REGISTER.txt 2026-11-14 14:37:52 (13:37:52 UTC; its last line, the NDVI "
    "registration, is stamped 2026-11-14T14:37:52); sample/coral/sample_manifest.json 2026-11-12 23:49:45 (22:49:45 "
    "UTC; the coral registration's stamp); logs/run_coral_scope_i.log and out/coral/lead_0/compare/per_lead.json "
    "2026-11-13 00:06:12 (2026-11-12 23:06:12 UTC; the pilot's end, \"00:06\"); out/ndvi/lead_0/compare/per_lead.json "
    "2026-11-15 19:11:39 (18:11:39 UTC); and logs/tr_shap_<problem>_lead0.log of forest loss, burned fraction, PM2.5 "
    "and NDVI at 2026-11-15 23:14:02 and 23:58:00 and 2026-11-16 04:56:11 and 08:14:14 (22:14:02, 22:58:00, 03:56:11 "
    "and 07:14:14 UTC), the B1 runs' \"done in\" times of RUN_COMMANDS.md. In UTC, from the local times of A9, A25 and "
    "A26 and the sources named there: the protocol, version 1 before any SHAP value on a real data row and version 3 "
    "after the smoke tests and two design reviews, 2026-11-12; the coral sample registered on 2026-11-12 at 22:49:45 "
    "and the coral pilot from then to 23:06:12, which wrote coral bleaching's comparison, AW4_table.md among its "
    "files; the burned-fraction, PM2.5, forest-loss and NDVI samples registered on 2026-11-13 at 16:23:16 and 20:44:18 "
    "and on 2026-11-14 at 03:37:20 and 13:37:52; the burned-fraction comparison of 2026-11-13 20:18 (four models, "
    "without Ridge), opened for its layout at about 20:20; coral bleaching's AW4_table.md read on 2026-11-13 at about "
    "14:31; ruling AZ1 answered on 2026-11-14 at about 03:35; the last nowcast comparison (NDVI, five models) on "
    "2026-11-15 at 18:11:39; rulings BA1 and BA2 answered at about 18:45 and BA3 at about 21:50 on 2026-11-15; the "
    "list of the B1 numbers written at 22:03; the B1 runs from 22:06:16 to 2026-11-16 07:14:14; owner question C10 "
    "asked on 2026-11-16 at about 00:50 and the coral read first recorded at 01:08; the independent re-computation from "
    "16:09 to about 18:20; ruling BB answered at 19:59. The rulings rows of S4.2 give the rulings file's dates, as its "
    "other rulings rows do: AZ1, BA and BB fall on the same date in UTC, and the records give no time for AW, AX and "
    "AY. Sources: those of A9, A25 and A26; D:/treeroute/analysis/shap_v1/PROTOCOL.md section 14 (the v1, v2 and v3 "
    "entries; \"v3 2026-11-12, after two design reviews\"; the NDVI comparison of \"five models\" at 19:11:39) and "
    "RUN_COMMANDS.md section 2 (\"Status.\" of the B1 command); the file times above, under "
    "D:/treeroute/analysis/shap_v1.")
A25_END_MARK = "paper/supp_build/s3_13/_brief/reads_tables.md (the file time); Table S3.22 note d.\n"
pf = rep(pf, A25_END_MARK, A25_END_MARK + A26 + "\n" + A27 + "\n" + A28 + "\n", "facts A26-A28")
save("paper/PAPER_FACTS.md", pf)
print("done")
