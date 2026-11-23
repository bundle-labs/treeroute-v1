"""After the owner's sensitivity run: check it ran as prepared, then print its numbers beside the headline's (read only).

    python -I -B check_after_run.py [<run folder>]   (default: the newest folder under run\\coral_sens_2017_2020\\headline)

Checks (each prints OK or FAIL): finished (DONE.json, status finished); the same engine as the headline (manifest
engine_code_hash and every engine module hash, constants hash, library versions, Python, launch backend/threads);
the prepared package (fingerprint below); the data are the owner's full build (manifest data files = sha256 in
coral_data/full/build_manifest.json); the window (derived R3 2020, R5 2017-2020, R6 2016, R7 inner fit 1994-2013,
inner score 2014-2016); the not-headline mark (draft true, headline_eligible false, a DRAFT not-headline reason).
Then prints, for the sensitivity run and the headline run side by side: verdict tag, adopted arm, declined, contrast
mean and CI, band, groups, test rows, pooled MAE adopted vs the donor-row median, predict-zero, trees-off, and the
ladder verdicts at 183 and 365 days. It writes nothing. The numbers are for the owner's Part; nothing here is a
verdict on the headline (the sensitivity row cannot change the verdict, the adoption or any choice).
"""
import json
import os
import sys

S = r"D:\treeroute\analysis\coral_sens_2017_2020"
HEAD = r"D:\treeroute\runs\coral\headline\20261020_f3b8e3da"
PREPARED_FINGERPRINT = "6a8509e323a7349f1f5e1d6e7861f8c96165af4bcd39e2a9caade425989d76c2"
ENGINE_CODE_HASH = "85c64b55c02e638cfcb7cefb0fe92af4870d4faed5c21e3f46bbdcbcd0e3a678"


def rj(*p):
    path = os.path.join(*p)
    return json.load(open(path, encoding="utf-8")) if os.path.isfile(path) else None


def newest_run():
    root = os.path.join(S, "run", "coral_sens_2017_2020", "headline")
    dirs = [os.path.join(root, d) for d in os.listdir(root) if os.path.isdir(os.path.join(root, d))]
    return max(dirs, key=os.path.getmtime)


def main(folder):
    ok = True

    def check(cond, what):
        nonlocal ok
        ok &= bool(cond)
        print("%-4s %s" % ("OK" if cond else "FAIL", what))

    print("run folder: %s" % folder)
    done, status = rj(folder, "DONE.json"), rj(folder, "status.json") or {}
    check(done is not None and status.get("state") == "finished", "finished (DONE.json; status %s)" % status.get("state"))
    mh, ms = rj(HEAD, "manifest.json"), rj(folder, "manifest.json")
    check(ms["engine_code_hash"] == ENGINE_CODE_HASH == mh["engine_code_hash"], "engine_code_hash %s" % ms["engine_code_hash"][:16])
    for k in ("engine_modules", "engine_constants_hash", "versions", "python", "gls_random_state", "feature_list_hash"):
        check(ms[k] == mh[k], "manifest %s equals the headline's" % k)
    for k in ("backend", "workers", "env_pins"):
        check(ms["launch"][k] == mh["launch"][k], "launch %s equals the headline's: %s" % (k, json.dumps(ms["launch"][k])[:120]))
    check(ms["package_fingerprint"] == PREPARED_FINGERPRINT, "package fingerprint %s (prepared %s)"
          % (ms["package_fingerprint"][:16], PREPARED_FINGERPRINT[:16]))
    bm = rj(S, "coral_data", "full", "build_manifest.json")
    files = {os.path.basename(f["path"]): f["sha256"] for f in ms["config"]["data"]["files"]}
    check(bm is not None and all(bm["files"].get(n) == h for n, h in files.items()) and len(files) == 3,
          "data files are the full sensitivity build (sha256 = coral_data/full/build_manifest.json)")
    d = rj(folder, "derived.json")
    check(d["R3"]["value"] == 2020, "R3 Y_end %s" % d["R3"]["value"])
    check(d["R5"]["value"]["test_years"] == [2017, 2018, 2019, 2020], "R5 test years %s" % d["R5"]["value"]["test_years"])
    check(d["R6"]["value"] == 2016, "R6 train end %s" % d["R6"]["value"])
    r7 = d["R7"]["value"]
    check(r7["inner_fit"] == [1994, 2013] and r7["inner_score"] == [2014, 2015, 2016],
          "R7 inner fit %s, inner score %s" % (r7["inner_fit"], r7["inner_score"]))
    rec = rj(folder, "run_record.json")
    check(rec["draft"]["is_draft"] and not rec["headline_eligible"]
          and any(r.startswith("DRAFT package") for r in rec["not_headline_reasons"]),
          "not-headline mark: draft %s, headline_eligible %s, reasons %s"
          % (rec["draft"]["is_draft"], rec["headline_eligible"], rec["not_headline_reasons"]))
    print("PREPARED-AS-DECLARED CHECKS: %s" % ("PASS" if ok else "FAIL"))

    print("\nNumbers (sensitivity row | headline, for the owner's Part; the sensitivity row is not a verdict):")
    for name, f in (("sensitivity 2017-2020", folder), ("headline 2016-2019", HEAD)):
        v, lad = rj(f, "verdict.json"), rj(f, "ladder", "ladder.json")
        c = v["verdict"]["contrast"]
        print("%s: verdict %s | adopted %s | declined %s | contrast %.4g [%.4g, %.4g] | band %.4g | groups %d | "
              "test rows %d | pooled MAE adopted %.4f vs donor-row median %.4f | predict-zero %.4f | adopted-link "
              "trees-off %.4f"
              % (name, v["verdict"]["tag"], v["adopted"], v["declined"], c["mean"], c["low"], c["high"], v["band"],
                 v["n_groups"], v["test_rows"], v["pooled_mae_adopted"], v["pooled_mae_reference"],
                 v["beside"].get("base__predict_zero_mae@all", float("nan")),
                 v["beside"].get("adopted_link_neighbour_trees_off_mae", float("nan"))))
        if lad:
            print("   ladder: %s" % {L: (x.get("tag"), x.get("guard_passed")) for L, x in sorted(lad["verdicts"].items())})
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else newest_run()))
