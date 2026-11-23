# Round 14 spec: writes V\spec\results_schema.json (JSON Schema draft-07 of V\<X>\results.json).
# FORMAT ONLY: no statistic is defined or computed here. Run: py -3.9 -I -B make_schema.py
import json
import os
import sys

OUT = r"D:\treeroute\analysis\shap_v1\verify_v1\spec\results_schema.json"
P5 = ["coral", "defo", "fire", "pm25", "ndvi"]
FAMILIES = ["own_history", "global_indices", "local_drivers", "context_and_calendar", "seasonal_normal"]
CHOICE_IDS = ["C%02d" % i for i in range(1, 26)] + ["I%02d" % i for i in range(1, 7)]
PAIR_STATS = ["spearman_J", "spearman_top20_union", "kendall_tau_b", "jaccard_top5", "jaccard_top10",
              "jaccard_top20", "rbo_p090", "rbo_p095", "tv_shares", "tv_family_shares",
              "sign_agreement", "sign_n_determined", "sign_n_agree"]
PAIRKEY = r"^[^|]+\|[^|]+$"
HEX64 = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
WHY = {"type": "string", "minLength": 1, "description": "Why the sibling key is null (a plain sentence)."}
STR = {"type": "string", "minLength": 1}
BOOL = {"type": "boolean"}
NAMES = {"type": "array", "items": STR, "description": "Names; sorted ascending (Python sorted()) unless the key says rank order."}
NAMES1 = {"type": "array", "items": STR, "minItems": 1, "description": NAMES["description"]}
INTS = {"type": "array", "items": {"type": "integer"}}
NUM_MAP = {"type": "object", "additionalProperties": {"type": "number"}}


def ref(name):
    return {"$ref": "#/definitions/" + name}


def nullable(s):
    return {"oneOf": [s, {"type": "null"}]}


def nullwhy(k):
    return {"if": {"properties": {k: {"type": "null"}}, "required": [k]}, "then": {"required": [k + "_why"]}}


def obj(req, opt=None, nulls=(), desc=None, extra=True):
    props = dict(req)
    if opt:
        props.update(opt)
    for k in nulls:
        props[k + "_why"] = WHY
    if extra:
        props["extra"] = {"description": "Optional free diagnostics of the implementer; the reconciler does not match them."}
    s = {"type": "object", "required": list(req.keys()), "properties": props, "additionalProperties": False}
    if nulls:
        s["allOf"] = [nullwhy(k) for k in nulls]
    if desc:
        s["description"] = desc
    return s


def imap(value_schema, desc=None, min_props=0):
    # A map keyed by a name (model, player, variable); a null value needs a sibling "<key>_why" string
    # (checked by validate_results.py, since draft-07 cannot tie dynamic keys).
    s = {"type": "object", "patternProperties": {"_why$": WHY}, "additionalProperties": value_schema}
    if min_props:
        s["minProperties"] = min_props
    if desc:
        s["description"] = desc
    return s


def topk(k):
    return {"type": "array", "maxItems": k,
            "description": "Top-%d list in rank order (rank 1 first): [[name, share], ...], share = full-sample share." % k,
            "items": {"type": "array", "minItems": 2, "maxItems": 2, "additionalItems": False,
                      "items": [STR, {"type": "number"}]}}


IVN = nullable(ref("interval"))
INT_N = {"type": ["integer", "null"]}
NUM_N = {"type": ["number", "null"]}

D = {}

D["interval"] = obj(
    req={"value": {"type": ["number", "null"], "description": "The number on the full sample (every region once)."},
         "ci_low": {"type": ["number", "null"], "description": "Lower end of the percentile 95% interval over the draws."},
         "ci_high": {"type": ["number", "null"], "description": "Upper end of the percentile 95% interval over the draws."},
         "n_finite": {"type": ["integer", "null"], "minimum": 0, "maximum": 2000,
                      "description": "Number of the 2,000 draws on which the number is finite."}},
    nulls=["value", "ci_low", "ci_high", "n_finite"], extra=False,
    desc="Interval object {value, ci_low, ci_high, n_finite}. A number without an interval (by the implementer's "
         "reading) has ci_low, ci_high and n_finite null, each with its _why. It does not decide whether a number gets an interval.")

D["topk10"] = topk(10)
D["topk3"] = topk(3)

D["player_imp"] = obj(
    req={"I": ref("interval"), "share": ref("interval"), "signed_mean": ref("interval"),
         "sign_determined": {"type": ["boolean", "null"],
                             "description": "Whether this player's sign is determined (section 8), by the implementer's rule."}},
    nulls=["sign_determined"], extra=False,
    desc="One player (feature level) or variable (variable level): I_m(j), s_m(j), S_m(j).")

D["players_map"] = imap(ref("player_imp"), min_props=1,
                        desc="Keyed by player name without the phi__ prefix (feature level) or variable name without the phiv__ prefix (variable level).")

D["family_shares"] = obj(req={f: IVN for f in FAMILIES}, nulls=FAMILIES,
                         desc="A model's share per family (section 8's five families).")

D["families"] = obj(
    req={"variable_family": {"type": "object", "minProperties": 1, "additionalProperties": {"enum": FAMILIES},
                             "description": "Every variable the implementer classifies -> its family key."},
         "global_indices": NAMES,
         "test_set_records": {"type": "array", "items": STR, "minItems": 1,
                              "description": "Short paths of the records read for the lead's test set."},
         "test_set_columns": NAMES},
    desc="Family map of the problem (variable level).")

_pair_common = {k: IVN for k in PAIR_STATS}
_pair_common.update({"top20_union": nullable(NAMES), "sign_union_top10": nullable(NAMES),
                     "sign_determined_both": nullable(NAMES)})
_pair_nulls = PAIR_STATS + ["top20_union", "sign_union_top10", "sign_determined_both"]

_pair_req = {"models": {"type": "array", "items": STR, "minItems": 2, "maxItems": 2,
                        "description": "The two model names in the key's order (alphabetical)."},
             "link_class": {"enum": ["same-link", "cross-link"]},
             "declined": NAMES,
             "both_in_main_set": BOOL}
_pair_req.update(_pair_common)
D["pair"] = obj(req=_pair_req, opt={"cross_link_label": {"const": "not comparable in scale or rank"}},
                nulls=_pair_nulls, desc="One pair of models at one level (brief item 4).")
D["pair"]["allOf"].append({"if": {"properties": {"link_class": {"const": "cross-link"}}, "required": ["link_class"]},
                           "then": {"required": ["cross_link_label"]},
                           "else": {"not": {"required": ["cross_link_label"]}}})

_pb1_req = {"pair": {"const": "treeroute|treeroute_B1"},
            "J": NAMES1,
            "n_J": IVN,
            "main_shares": dict(NUM_MAP, description="The main run's full-sample shares over this pair's J."),
            "main_ranking": dict(NAMES, description="The main run's ranking over this pair's J, rank order.")}
_pb1_req.update(_pair_common)
D["pair_b1"] = obj(req=_pb1_req, nulls=_pair_nulls + ["n_J"],
                   desc="The pair (treeroute's main run, its B1 run) at one level (brief item 9).")


def model_level(variable):
    req = {"players": ref("players_map"),
           "n_nonzero": IVN,
           "ranking": dict(NAMES, description="The model's ranking over J, rank order (rank 1 first)."),
           "top10": nullable(ref("topk10"))}
    opt = {}
    if variable:
        req["family_shares"] = ref("family_shares")
    else:
        opt["family_shares"] = ref("family_shares")
    return obj(req=req, opt=opt, nulls=["n_nonzero", "top10"], desc="One model at one level (brief item 2).")


D["model_level_feature"] = model_level(False)
D["model_level_variable"] = model_level(True)

D["per_problem"] = obj(
    req={"kendall_w": IVN, "kendall_w_m": INT_N, "kendall_w_n": INT_N, "mean_pairwise_spearman": IVN,
         "stability": imap(IVN, min_props=1, desc="Keyed by model name: the model's stability under region resampling.")},
    nulls=["kendall_w", "kendall_w_m", "kendall_w_n", "mean_pairwise_spearman"],
    desc="Per problem-lead statistics at one level (brief item 5).")


def level(variable):
    req = {"active_set": obj(req={"J": NAMES1, "n_J": IVN, "structural_zeros": NAMES}, nulls=["n_J"],
                             desc="Brief item 1."),
           "models": {"type": "object", "minProperties": 1,
                      "additionalProperties": ref("model_level_variable" if variable else "model_level_feature"),
                      "description": "Keyed by model name: every model of per_lead.json key models."},
           "pairs": {"type": "object", "minProperties": 1, "propertyNames": {"pattern": PAIRKEY},
                     "additionalProperties": ref("pair"),
                     "description": "Keyed 'a|b' (the two model names in alphabetical order): every pair of models."},
           "per_problem": ref("per_problem")}
    if variable:
        req["families"] = ref("families")
    return obj(req=req, desc=("Variable level." if variable else "Feature level."))


D["level_feature"] = level(False)
D["level_variable"] = level(True)

D["draws"] = obj(
    req={"path": STR,
         "shape": {"type": "array", "items": {"type": "integer"}, "minItems": 2, "maxItems": 2},
         "dtype": STR,
         "sha256_computed": HEX64,
         "sha256_covers": dict(WHY, description="Which bytes the computed SHA-256 covers (identification I03)."),
         "sha256_per_lead": HEX64,
         "sha256_match": BOOL,
         "region_source": dict(WHY, description="Where a row's region is read (identification I01)."),
         "regions_in_draw_order": {"type": "array", "items": {"type": ["string", "integer"]}, "minItems": 1,
                                   "description": "The regions in the order the draw integers refer to (identification I02)."},
         "npz": dict(STR, description="Short path of this problem's per-draw file, V\\<X>\\draws\\<problem>.npz.")},
    desc="The saved draw matrix and its check (brief item 6).")

D["main_row"] = obj(
    req={"level": {"const": "variable"},
         "main_set": NAMES1,
         "rivals": NAMES,
         "kendall_w": IVN,
         "spearman_top20_union_median": IVN,
         "spearman_top20_union_min": IVN,
         "spearman_top20_union_max": IVN,
         "spearman_top20_union_per_rival": nullable(NUM_MAP),
         "rbo_p090_vs_consensus": IVN,
         "consensus_shares": nullable(NUM_MAP),
         "treeroute_top3": nullable(ref("topk3")),
         "consensus_top3": nullable(ref("topk3")),
         "own_history_share_treeroute": IVN,
         "own_history_share_median_rival": IVN,
         "own_history_share_per_rival": nullable(NUM_MAP),
         "median_rival_name": {"type": ["string", "null"]}},
    nulls=["kendall_w", "spearman_top20_union_median", "spearman_top20_union_min", "spearman_top20_union_max",
           "spearman_top20_union_per_rival", "rbo_p090_vs_consensus", "consensus_shares", "treeroute_top3",
           "consensus_top3", "own_history_share_treeroute", "own_history_share_median_rival",
           "own_history_share_per_rival", "median_rival_name"],
    desc="The main-text row, variable level (brief item 7).")

D["nz_model"] = obj(
    req={"level": {"const": "variable"},
         "rows_used": {"type": "integer", "minimum": 0},
         "regions_used": {"type": "integer", "minimum": 0},
         "J": NAMES,
         "players": ref("players_map"),
         "n_nonzero": IVN,
         "ranking": NAMES,
         "top10": nullable(ref("topk10"))},
    nulls=["n_nonzero", "top10"],
    desc="One arcsine-link model's variable-level importances on its rows with pre > 0 (brief item 8).")

D["nonzero_forecast"] = obj(
    req={"models_covered": NAMES,
         "models_covered_why": WHY,
         "models": {"type": "object", "additionalProperties": ref("nz_model")}},
    desc="Brief item 8, keyed by model name.")

D["problem"] = obj(
    req={"lead": {"const": 0},
         "models": dict(NAMES1, description="Copied from per_lead.json key models, same order."),
         "main_set": dict(NAMES1, description="Copied from per_lead.json key main_set, same order."),
         "declined_by_guard": dict(NAMES, description="Copied from per_lead.json key declined_by_guard, same order."),
         "links": {"type": "object", "additionalProperties": STR, "description": "Copied from per_lead.json key links."},
         "rows": {"type": "integer", "description": "Copied from per_lead.json key rows."},
         "draws": ref("draws"),
         "levels": obj(req={"feature": ref("level_feature"), "variable": ref("level_variable")}, extra=False),
         "main_row": ref("main_row"),
         "nonzero_forecast": ref("nonzero_forecast")},
    desc="One problem, lead 0 (brief items 1-8).")

_META8 = ["pass", "checks_passed", "rows", "background", "pairs", "trees_used", "sample_sha256", "duplicates_merged"]
D["b1_meta"] = obj(
    req={"pass": {"type": ["boolean", "null"]}, "checks_passed": {"type": ["object", "null"]},
         "rows": INT_N, "background": {"type": ["string", "null"]}, "pairs": INT_N, "trees_used": INT_N,
         "sample_sha256": {"type": ["string", "null"]}, "duplicates_merged": {"type": ["object", "null"]}},
    nulls=_META8, extra=False,
    desc="The B1 piece's meta.json fields, copied verbatim (brief item 9, first sub-item).")

D["b1_status"] = obj(
    req={"folder_exists": BOOL, "has_done_json": BOOL, "has_failed_json": BOOL, "finished": BOOL,
         "failed_stop": {"type": ["string", "null"]},
         "meta": nullable(ref("b1_meta")),
         "background_is_B1": {"type": ["boolean", "null"]},
         "sample_sha256_registered": {"type": ["string", "null"]},
         "sample_sha256_is_registered": {"type": ["boolean", "null"]},
         "per_lead_models_lists_treeroute_B1": BOOL,
         "numbers": {"enum": ["none", "identity", "full"]},
         "numbers_why": WHY},
    nulls=["failed_stop", "meta", "background_is_B1", "sample_sha256_registered", "sample_sha256_is_registered"],
    desc="Brief item 9, first sub-item, and the check that per_lead.json's models does not list treeroute_B1.")

_RUN_FACTS = {"log_file": STR,
              "log_setup_line_number": INT_N, "log_done_line_number": INT_N,
              "pairs_log": INT_N, "pairs_meta": INT_N,
              "total_seconds_log": NUM_N, "total_seconds_done_json": NUM_N,
              "tree_shap_seconds_log": NUM_N, "tree_shap_seconds_meta": NUM_N}
_RUN_NULLS = [k for k in _RUN_FACTS if k != "log_file"]

_id_req = {"max_abs_diff_phi": NUM_N, "max_abs_diff_phiv": NUM_N,
           "same_rows": BOOL, "same_players": BOOL, "same_variables": BOOL,
           "n_rows_main": {"type": "integer"}, "n_rows_b1": {"type": "integer"},
           "n_players_main": {"type": "integer"}, "n_players_b1": {"type": "integer"},
           "n_variables_main": {"type": "integer"}, "n_variables_b1": {"type": "integer"},
           "rows_only_in_main": INTS, "rows_only_in_b1": INTS,
           "players_only_in_main": NAMES, "players_only_in_b1": NAMES,
           "variables_only_in_main": NAMES, "variables_only_in_b1": NAMES,
           "as_expected": BOOL}
_id_req.update(_RUN_FACTS)
D["b1_identity"] = obj(req=_id_req, nulls=["max_abs_diff_phi", "max_abs_diff_phiv"] + _RUN_NULLS,
                       desc="Defo's identity check with its pairs and seconds (brief item 9).")

_run_req = dict(_RUN_FACTS)
_run_req.update({"duplicates_merged_main": NAMES, "duplicates_merged_b1": NAMES, "context_columns_summed": NAMES,
                 "draws_sha256_match": BOOL, "npz": STR})
D["b1_run"] = obj(req=_run_req, nulls=_RUN_NULLS,
                  desc="The B1 run's pairs, seconds and merged context columns (fire, pm25, ndvi).")


def b1_importance(feature):
    req = {"players": ref("players_map"), "n_nonzero": IVN,
           "ranking": dict(NAMES, description="The B1 run's ranking over the pair's J, rank order.")}
    nulls = ["n_nonzero"]
    if feature:
        req["n_nonzero_before_merge"] = IVN
        nulls.append("n_nonzero_before_merge")
    return obj(req=req, nulls=nulls, desc="The B1 run's I(j), s(j), S(j) (shares over the pair's J) and nonzero count.")


D["b1_importance_feature"] = b1_importance(True)
D["b1_importance_variable"] = b1_importance(False)
D["b1_level_feature"] = obj(
    req={"importance": ref("b1_importance_feature"), "top10": nullable(ref("topk10")), "pair_main_b1": ref("pair_b1")},
    nulls=["top10"])
D["b1_level_variable"] = obj(
    req={"importance": ref("b1_importance_variable"), "top10": nullable(ref("topk10")), "pair_main_b1": ref("pair_b1"),
         "families": ref("family_shares"), "top3": nullable(ref("topk3")), "own_history_share": IVN},
    nulls=["top10", "top3", "own_history_share"])


def b1_problem(kind):
    props = {"status": ref("b1_status"), "extra": {"description": "Optional free diagnostics."}}
    allowed = {"coral": ["none"], "defo": ["none", "identity"], "full": ["none", "full"]}[kind]
    allof = [{"properties": {"status": {"properties": {"numbers": {"enum": allowed}}}}}]
    if kind == "defo":
        props["identity"] = ref("b1_identity")
        allof.append({"if": {"properties": {"status": {"properties": {"numbers": {"const": "identity"}},
                                                       "required": ["numbers"]}}},
                      "then": {"required": ["identity"]}})
    if kind == "full":
        props["run"] = ref("b1_run")
        props["feature"] = ref("b1_level_feature")
        props["variable"] = ref("b1_level_variable")
        allof.append({"if": {"properties": {"status": {"properties": {"numbers": {"const": "full"}},
                                                       "required": ["numbers"]}}},
                      "then": {"required": ["run", "feature", "variable"]}})
    return {"type": "object", "required": ["status"], "properties": props, "additionalProperties": False,
            "allOf": allof}


D["b1_problem_coral"] = b1_problem("coral")
D["b1_problem_defo"] = b1_problem("defo")
D["b1_problem_full"] = b1_problem("full")

SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "$id": "round14_results_schema_v1",
    "title": "Round 14 results.json (one file per implementer, V\\<X>\\results.json)",
    "description": "Format of the independent re-computation of the SHAP comparison numbers of scope (i), lead 0, "
                   "and of treeroute's B1 sensitivity. See V\\spec\\SPEC.md. Format only: it defines no statistic.",
    "type": "object",
    "required": ["schema_version", "implementer", "written_at", "software", "choices", "problems", "b1"],
    "properties": {
        "schema_version": {"const": "round14_results_v1"},
        "implementer": {"enum": ["A", "B"]},
        "written_at": {"type": "string",
                       "pattern": r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:\d{2})?$"},
        "software": {"type": "object", "required": ["python", "numpy"], "additionalProperties": STR},
        "choices": {"type": "object", "required": CHOICE_IDS,
                    "patternProperties": {"^[CIX][0-9]{2}$": WHY}, "additionalProperties": False,
                    "description": "One short line per open choice / identification of SPEC.md section 3 "
                                   "(X01, X02, ... for further choices the implementer found)."},
        "problems": {"type": "object", "required": P5, "properties": {p: ref("problem") for p in P5},
                     "additionalProperties": False},
        "b1": {"type": "object", "required": P5,
               "properties": {"coral": ref("b1_problem_coral"), "defo": ref("b1_problem_defo"),
                              "fire": ref("b1_problem_full"), "pm25": ref("b1_problem_full"),
                              "ndvi": ref("b1_problem_full")},
               "additionalProperties": False},
        "notes": {"type": "string"},
        "extra": {"description": "Optional free diagnostics."}},
    "additionalProperties": False,
    "definitions": D,
}


def main():
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(SCHEMA, f, indent=1, ensure_ascii=False, allow_nan=False)
        f.write("\n")
    print("wrote", OUT, os.path.getsize(OUT), "bytes;", len(D), "definitions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
