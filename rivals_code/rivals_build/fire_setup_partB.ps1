# ---------------------------------------------------- BEGIN FIRE SETUP BLOCK ----------------------------------------------------
Set-Location D:\treeroute\human_rivals_build\human
$env:PYTHONDONTWRITEBYTECODE = "1"
$HROOT   = "D:\treeroute\human_rivals_build\human"
$HCFG    = "$HROOT\human_rivals_production.yaml"
$HDRY    = "$HROOT\human_rivals_DRY.yaml"
$PRODREG = "$HROOT\registry\_products.yaml"
$FIREREG = "$HROOT\registry\fire.yaml"
$FIRE    = "D:\treeroute\runs\fire\headline\20261017_869d1f38"
$FEXP    = "D:\treeroute\rival_export\fire\20261017_869d1f38"
$HOUT    = "D:\treeroute\rivals_human\fire\20261017_869d1f38"
$DOUT    = "D:\treeroute\rivals_human_dry\fire\20261017_869d1f38"
$CORAL   = "D:\treeroute\runs\coral\headline\20261020_f3b8e3da"
$DEFO    = "D:\treeroute\runs\defo\headline\20261017_d71c61f4"
$PM      = "D:\treeroute\runs\pm25\headline\20261007_74e67609"
$NDVI    = "D:\treeroute\runs\ndvi\headline\20261016_d1de3158"
# ONLY after F6b (D3 not complete on 18 Nov AND OD-4.1 = yes): $true, and the decision text exactly as Part section 13
# (no double quotes inside). Leave $false / "" otherwise.
$D3_WITHOUT  = $false
$D3_DECISION = ""
# ONLY without a DRY pass (OD-11 = no): the shas of Part section 1; F8 / F9 then compare against these.
$SIGNED_SHAS = @{ tool = ""; registry = ""; schema = ""; products = "" }
$global:FIRE_STEPS_RUN = 0

$PY_MANIFEST_STATE = @'
import json, os, sys, yaml
reg, pid = sys.argv[1], sys.argv[2]
with open(reg, encoding="utf-8") as fh:
    prods = (yaml.safe_load(fh) or {}).get("products") or {}
path = (prods.get(pid) or {}).get("manifest")
if not path:
    print("STOP: %s has no manifest entry in %s" % (pid, reg))
    sys.exit(2)
print("%s manifest: %s" % (pid, path))
if "UNSET_OD6" in path:
    print("NOT READY: the folder is still the UNSET_OD6 placeholder (step F4b sets it)")
    sys.exit(3)
if not os.path.isfile(path):
    print("NOT READY: the manifest file does not exist yet")
    sys.exit(3)
with open(path, encoding="utf-8") as fh:
    man = json.load(fh)
files = man.get("files") or {}
gb = sum(int((v or {}).get("bytes") or 0) for v in files.values()) / 1e9
state = man["complete"] if "complete" in man else "MISSING (a first or killed fetcher run)"
print("%d files of %d requests, %.3f GB, complete = %s" % (len(files), len(man.get("requests") or {}), gb, state))
sys.exit(0 if man.get("complete") is True else 3)
'@

$PY_SET_FOLDER = @'
import hashlib, os, sys, yaml
reg, pid, suffix = sys.argv[1], sys.argv[2], sys.argv[3]
with open(reg, "rb") as fh:
    raw = fh.read()
prods = (yaml.safe_load(raw.decode("utf-8")) or {}).get("products") or {}
old = (prods.get(pid) or {}).get("manifest") or ""
if "_UNSET_OD6/" not in old:
    print("STOP: the manifest of %s is %r, not the UNSET_OD6 placeholder (already set?)" % (pid, old))
    sys.exit(2)
new = old.replace("_UNSET_OD6/", "_%s/" % suffix)
if not os.path.isfile(new):
    print("STOP: %s does not exist: the fetcher has not written that folder (check the suffix)" % new)
    sys.exit(2)
ob, nb = old.encode("utf-8"), new.encode("utf-8")
if raw.count(ob) != 1:
    print("STOP: the placeholder path occurs %d times in %s (expected 1)" % (raw.count(ob), reg))
    sys.exit(2)
out = raw.replace(ob, nb)
chk = (yaml.safe_load(out.decode("utf-8")) or {}).get("products") or {}
if sorted(chk) != sorted(prods) or chk[pid].get("manifest") != new or any(chk[k] != prods[k] for k in prods if k != pid):
    print("STOP: the edit would change more than the manifest of %s; nothing written" % pid)
    sys.exit(2)
with open(reg, "wb") as fh:
    fh.write(out)
print("%s manifest: %s" % (pid, new))
print("_products.yaml sha256 %s -> %s" % (hashlib.sha256(raw).hexdigest(), hashlib.sha256(out).hexdigest()))
'@

$PY_BOARD_RECORD = @'
import csv, json, os, sys
hroot, out = sys.argv[1], sys.argv[2]
sys.path.insert(0, hroot)
from rivals_human import lockfile as LK
with open(os.path.join(out, "human_board.json"), encoding="utf-8") as fh:
    b = json.load(fh)
print("board %s (dry %s, allow_waiting %s)" % (out, b.get("dry"), b.get("allow_waiting")))
print("tool_code_sha256 %s" % b["tool_code_sha256"])
for k in ("registry", "schema", "products", "file"):
    print("registry.%s %s" % (k, b["registry"].get(k)))
print("engine %s; common board %s (harness %s)" % (b["engine"]["live_file_sha"], b["common_board"]["sha256"],
                                                   b["common_board"]["harness_code_sha256"]))
for lead, s in sorted(b["slim"].items(), key=lambda kv: int(kv[0])):
    print("slim lead %s %s" % (lead, s["manifest_sha256"]))
for rid, st in sorted(b["rivals"].items()):
    print("rival %s %s; products %s; index %s" % (rid, st["status"], json.dumps(st.get("products"), sort_keys=True),
                                                 json.dumps(st.get("index"), sort_keys=True)))
pp = os.path.join(out, "human_picks.json")
if not os.path.isfile(pp):
    print("no human_picks.json yet")
    sys.exit(0)
with open(pp, encoding="utf-8") as fh:
    picks = json.load(fh)
print("picks content sha %s" % LK.picks_content_sha(picks["picks"]))
print("owner decision: %s" % picks.get("owner_decision"))
zero = {}
tp = os.path.join(out, "trials.csv")
if os.path.isfile(tp):
    with open(tp, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            zero[(row.get("rival"), row.get("candidate"), row.get("lead"), row.get("score_set"))] = row.get("predict_zero_mae")
for rid, p in sorted(picks["picks"].items()):
    key = (rid, str(p.get("candidate")), str(p.get("pick_lead")), str(p.get("pick_set")))
    print("pick %s: status %s; candidate %s (stat %s, family %s, link %s, form %s); %s rows of lead %s: %s; MAE %s; "
          "predict-zero MAE %s" % (rid, p.get("status"), p.get("candidate"), p.get("stat"), p.get("family"),
                                   p.get("link"), p.get("form"), p.get("pick_set"), p.get("pick_lead"),
                                   p.get("pick_rows"), p.get("pick_mae"), zero.get(key, "n/a")))
'@

$PY_FIRE_CHECK = @'
import hashlib, json, os, sys
mode, hroot = sys.argv[1], sys.argv[2]
sys.path.insert(0, hroot)
KEYS = ("tool", "registry", "schema", "products")


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for blk in iter(lambda: fh.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def load(path):
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def stop(msg):
    print("STOP: " + msg)
    sys.exit(4)


def reference(dry_out, signed):
    b = load(os.path.join(dry_out, "human_board.json"))
    if b is not None:
        r = b["registry"]
        return "the F7 DRY board", {"tool": b["tool_code_sha256"], "registry": r["registry"], "schema": r["schema"],
                                    "products": r["products"]}, b
    if all(signed.get(k) not in (None, "", "-") for k in KEYS):
        return "Part section 1 ($SIGNED_SHAS)", signed, None
    stop("no F7 DRY board in %s and $SIGNED_SHAS is not filled (OD-11 = no needs it)" % dry_out)


def compare(name, ref, got):
    bad = [k for k in KEYS if ref[k] != got[k]]
    for k in KEYS:
        print("%-8s %s  %s" % (k, got[k], "equal" if k not in bad else "DIFFERS from %s" % ref[k]))
    if bad:
        stop("%s differ from %s (no edit after F7: spec 8 rule 2)" % (", ".join(bad), name))
    print("EQUAL to %s" % name)


if mode == "shas":
    dry_out, regdir, prodreg = sys.argv[3:6]
    signed = dict(zip(KEYS, sys.argv[6:10]))
    from rivals_human.common import tool_code_sha
    got = {"tool": tool_code_sha(), "registry": sha(os.path.join(regdir, "fire.yaml")),
           "schema": sha(os.path.join(regdir, "_schema.yaml")), "products": sha(prodreg)}
    name, ref, _ = reference(dry_out, signed)
    compare(name, ref, got)
elif mode == "board":
    real_out, dry_out = sys.argv[3:5]
    signed = dict(zip(KEYS, sys.argv[5:9]))
    b = load(os.path.join(real_out, "human_board.json"))
    if b is None:
        stop("no human_board.json in %s" % real_out)
    if b.get("dry"):
        stop("%s is a DRY board, not the real one" % real_out)
    r = b["registry"]
    got = {"tool": b["tool_code_sha256"], "registry": r["registry"], "schema": r["schema"], "products": r["products"]}
    name, ref, dry = reference(dry_out, signed)
    compare(name, ref, got)
    if dry is not None:
        def facts(x):
            return {"engine": x["engine"]["live_file_sha"], "common_board": x["common_board"]["sha256"],
                    "registry_file": x["registry"].get("file"),
                    "slim": {lead: s["manifest_sha256"] for lead, s in x["slim"].items()},
                    "rivals": {rid: {"status": st["status"], "products": st.get("products"), "index": st.get("index")}
                               for rid, st in x["rivals"].items()}}
        fa, fb = facts(b), facts(dry)
        bad = [k for k in fa if json.dumps(fa[k], sort_keys=True) != json.dumps(fb[k], sort_keys=True)]
        for k in bad:
            print("%s real: %s" % (k, json.dumps(fa[k], sort_keys=True)))
            print("%s DRY:  %s" % (k, json.dumps(fb[k], sort_keys=True)))
        if bad:
            stop("the real board's %s differ from the F7 DRY board's" % ", ".join(bad))
        print("EQUAL: engine, common board, slims, product pins, index tables and rival status as in the F7 DRY board")
elif mode == "picks":
    real_out, dry_out = sys.argv[3:5]
    from rivals_human import lockfile as LK
    real = load(os.path.join(real_out, "human_picks.json"))
    if real is None:
        stop("no human_picks.json in %s" % real_out)
    got = LK.picks_content_sha(real["picks"])
    print("picks content %s" % got)
    dry = load(os.path.join(dry_out, "human_picks.json"))
    if dry is None:
        print("no F7 DRY picks (OD-11 = no): nothing to compare; this sha goes into Part section 7")
    else:
        want = LK.picks_content_sha(dry["picks"])
        if got != want:
            stop("the picks differ from the F7 DRY pass (%s): spec 8 F9 stop (coral precedent, Part 617)" % want)
        print("EQUAL to the F7 DRY picks")
elif mode == "refs":
    out, lead = sys.argv[3], sys.argv[4]
    rec = load(os.path.join(out, "lead_%s" % lead, "refs.json"))
    if rec is None:
        stop("no lead_%s\\refs.json in %s" % (lead, out))
    res = str(rec.get("result"))
    print("lead %s refs.json result: %s" % (lead, res))
    if not res.startswith("parity proof passed"):
        stop("lead %s refs.json does not start with 'parity proof passed' (spec B4: score would not refuse)" % lead)
else:
    stop("unknown mode %r" % mode)
'@

function Invoke-HumanTool([string]$cfg, [string[]]$cliArgs) {
    $line = "rivals_human.cli " + ($cliArgs -join " ")
    Write-Host ("[{0}] START {1}" -f (Get-Date -Format s), $line)
    Push-Location $HROOT
    try {
        & py -3.9 -B -m rivals_human.cli @cliArgs --config $cfg
        $code = $LASTEXITCODE
    } finally {
        Pop-Location
    }
    Write-Host ("[{0}] END {1} (exit {2})" -f (Get-Date -Format s), $line, $code)
    if ($code -ne 0) { throw "STOP: $line exited $code. Do not go on; send the output to the agent." }
    $global:FIRE_STEPS_RUN++
}
function Invoke-HumanCli { Invoke-HumanTool $HCFG ([string[]]$args) }
function Invoke-HumanDryCli { Invoke-HumanTool $HDRY ([string[]]$args) }
function Invoke-FirePython([string]$code, [string[]]$pyArgs) {
    $out = @($code | & py -3.9 -I -B - @pyArgs)
    $exit = $LASTEXITCODE
    foreach ($l in $out) { Write-Host $l }
    return $exit
}
function Complete-FireStep([string]$step, [int]$expected) {
    if ($global:FIRE_STEPS_RUN -ne $expected) { throw "STOP: $step ran $($global:FIRE_STEPS_RUN) of $expected commands" }
    Write-Host ("[{0}] {1} DONE ({2} commands ran)" -f (Get-Date -Format s), $step, $global:FIRE_STEPS_RUN)
}
function Get-SignedShaArgs {
    foreach ($k in "tool", "registry", "schema", "products") { if ($SIGNED_SHAS[$k]) { $SIGNED_SHAS[$k] } else { "-" } }
}
function Test-FetcherManifestComplete([string]$ProductId) {
    $code = Invoke-FirePython $PY_MANIFEST_STATE @($PRODREG, $ProductId)
    return ($code -eq 0)
}
function Assert-FetcherRerunAllowed([string]$Product) {
    if (@("D2", "D3") -notcontains $Product) { throw "STOP: give D2 or D3" }
    if ($Product -eq "D3" -and $D3_WITHOUT) { throw "STOP: D3 was stopped at the cut-off (F6b); it is never restarted for this board" }
    foreach ($b in "$DOUT\human_board.json", "$HOUT\human_board.json") {
        if (Test-Path $b) { throw "STOP: $b exists: never run the fetcher for D2 or D3 again (spec B8; it rewrites product_manifest.json, which that board pinned)" }
    }
    Write-Host "OK: no fire human board exists yet: a stopped $Product run may be resumed with the SAME command (DOWNLOAD_COMMANDS.md)"
}
function Set-FireProductFolder([string]$ProductId, [string]$Suffix) {
    $global:FIRE_STEPS_RUN = 0
    $allowed = @{ "cems_geff_era5_fwi" = @("merged", "region"); "cems_geff_seas5_fwi" = @("region_y1", "merged_y1", "region_y4", "merged_y4") }
    if (-not $allowed.ContainsKey($ProductId)) { throw "STOP: F4b edits only cems_geff_era5_fwi or cems_geff_seas5_fwi" }
    if ($allowed[$ProductId] -notcontains $Suffix) { throw "STOP: $Suffix is not a folder suffix the fetcher writes for $ProductId ($($allowed[$ProductId] -join ', '))" }
    foreach ($b in "$DOUT\human_board.json", "$HOUT\human_board.json") {
        if (Test-Path $b) { throw "STOP: $b exists: the product folder is never changed after the first init (the product registry sha is pinned)" }
    }
    $stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
    $keep = "D:\treeroute\human_rivals_build\_moved\${stamp}_F4b_$ProductId\registry"
    New-Item -ItemType Directory -Path $keep -Force | Out-Null
    Copy-Item -LiteralPath $PRODREG -Destination "$keep\_products.yaml"
    Write-Host "copy of the current _products.yaml kept in $keep"
    $code = Invoke-FirePython $PY_SET_FOLDER @($PRODREG, $ProductId, $Suffix)
    if ($code -ne 0) { throw "STOP: F4b did not apply (exit $code); _products.yaml is unchanged" }
    $global:FIRE_STEPS_RUN++
    Complete-FireStep "F4b $ProductId" 1
}
function Invoke-FireRefsByteCheck {
    $tests = @(Get-ChildItem -LiteralPath "$HROOT\tests_fire" -Filter "test_f18_*.py" -File -ErrorAction SilentlyContinue)
    if ($tests.Count -ne 1) { throw "STOP: expected exactly one tests_fire\test_f18_*.py, found $($tests.Count)" }
    $bt = "D:\treeroute\human_rivals_build\pt\tests\owner_f18_" + (Get-Date -Format yyyyMMdd_HHmmss)
    if (Test-Path $bt) { throw "STOP: the pytest folder $bt exists; call again in a second" }
    Push-Location $HROOT
    $env:HUMAN_REAL = "1"
    try {
        $out = @(& py -3.9 -B -m pytest $tests[0].FullName -q -rA -p no:cacheprovider --basetemp $bt)
        $code = $LASTEXITCODE
    } finally {
        Remove-Item Env:HUMAN_REAL -ErrorAction SilentlyContinue
        Pop-Location
    }
    foreach ($l in $out) { Write-Host $l }
    $summary = "$($out | Where-Object { $_ -match '\d+ (passed|failed|skipped|error)' } | Select-Object -Last 1)"
    if ($code -ne 0 -or $summary -notmatch '\d+ passed' -or $summary -match 'skipped|failed|error') {
        throw "STOP: T-F18 did not pass cleanly (exit $code; '$summary'). A skip = the fire slim or the fire_refs_label_store manifest is missing; a failure = the store is not byte-equal to the slim labels. Do not go on."
    }
    $global:FIRE_STEPS_RUN++
}
function Show-FireBoardRecord([string]$out) {
    $code = Invoke-FirePython $PY_BOARD_RECORD @($HROOT, $out)
    if ($code -ne 0) { throw "STOP: could not read the board record of $out" }
}
function Assert-FireShasEqualReference {
    $code = Invoke-FirePython $PY_FIRE_CHECK (@("shas", $HROOT, $DOUT, "$HROOT\registry", $PRODREG) + @(Get-SignedShaArgs))
    if ($code -ne 0) { throw "STOP: the fire shas differ from the reference (read above). Do not sign; do not go on." }
}
function Assert-FireBoardEqualReference {
    $code = Invoke-FirePython $PY_FIRE_CHECK (@("board", $HROOT, $HOUT, $DOUT) + @(Get-SignedShaArgs))
    if ($code -ne 0) { throw "STOP: the real board's human_board.json differs from the reference (read above). Do not go on." }
}
function Assert-FirePicksEqualDry {
    $code = Invoke-FirePython $PY_FIRE_CHECK @("picks", $HROOT, $HOUT, $DOUT)
    if ($code -ne 0) { throw "STOP: the real picks differ from the F7 DRY picks (read above). Do not refit or score." }
}
function Assert-FireRefsParity([int]$Lead) {
    $code = Invoke-FirePython $PY_FIRE_CHECK @("refs", $HROOT, $HOUT, "$Lead")
    if ($code -ne 0) { throw "STOP: lead $Lead refs did not pass its parity proof (read above). Do not score." }
}
function Show-FireCutoffState {
    $left = ([datetime]::new(2026, 11, 18) - (Get-Date).Date).Days
    Write-Host "days to the 18 Nov lead-6 cut-off (Q24): $left"
    foreach ($p in "cems_geff_era5_fwi", "cems_geff_seas5_fwi") { $null = Test-FetcherManifestComplete $p }
}
function Get-FireBoardStatus([string]$out = $HOUT) {
    Push-Location $HROOT
    try { & py -3.9 -B -m rivals_human.cli status --out $out } finally { Pop-Location }
}
function Invoke-FireStepF1 {
    $global:FIRE_STEPS_RUN = 0
    if (-not (Test-Path $FIREREG)) { throw "STOP: $FIREREG does not exist (the Part B build is not installed)" }
    foreach ($L in 0, 6, 12) {
        if (-not (Test-Path "$FEXP\lead_$L\export_manifest.json")) { throw "STOP: the fire export lead_$L is not on disk: it was deleted before the slim (spec B1); tell the agent" }
    }
    foreach ($L in 0, 6, 12) { Invoke-HumanCli slim --run $FIRE --export "$FEXP\lead_$L" }
    Complete-FireStep "F1 (slim fire leads 0, 6, 12)" 3
}
function Invoke-FireStepF2 {
    $global:FIRE_STEPS_RUN = 0
    foreach ($P in "fire_static_cells", "fire_target_2018") { Invoke-HumanCli manifest --product $P }
    Complete-FireStep "F2 (manifests fire_static_cells, fire_target_2018)" 2
}
function Invoke-FireStepF3 {
    $global:FIRE_STEPS_RUN = 0
    Invoke-HumanCli prep --run $FIRE --rival geff_era5 --stage train
    Invoke-HumanCli manifest --product fire_refs_label_store
    Invoke-FireRefsByteCheck
    Complete-FireStep "F3 (refs label store + T-F18 early byte check)" 3
}
function Invoke-FireStepF5 {
    $global:FIRE_STEPS_RUN = 0
    if (-not (Test-FetcherManifestComplete "cems_geff_era5_fwi")) { throw "STOP: D2 is not complete yet, or F4b was not done (read above). Wait; never re-run the fetcher to check." }
    Invoke-HumanCli manifest --product cems_geff_era5_fwi --verify
    Invoke-HumanCli adapt --run $FIRE --rival geff_era5 --lead 0
    Invoke-HumanCli check --run $FIRE --rival geff_era5
    Complete-FireStep "F5 (D2 verified, geff_era5 lead 0 adapted and checked)" 3
}
function Invoke-FireStepF6 {
    $global:FIRE_STEPS_RUN = 0
    if ($D3_WITHOUT) { throw "STOP: D3 was stopped at the cut-off (F6b): F6 never runs for this board" }
    if (-not (Test-FetcherManifestComplete "cems_geff_seas5_fwi")) { throw "STOP: D3 is not complete yet, or F4b was not done (read above). Wait; never re-run the fetcher to check." }
    Invoke-HumanCli manifest --product cems_geff_seas5_fwi --verify
    Invoke-HumanCli adapt --run $FIRE --rival geff_seas5 --lead 6
    Invoke-HumanCli check --run $FIRE --rival geff_seas5
    Complete-FireStep "F6 (D3 verified, geff_seas5 lead 6 adapted and checked)" 3
}
function Invoke-FireDryPass([switch]$DecisionsWritten) {
    $global:FIRE_STEPS_RUN = 0
    if (-not $DecisionsWritten) { throw "STOP: F7 runs only after EVERY owner decision except OD-11 is ruled AND written (spec B9). Then call: Invoke-FireDryPass -DecisionsWritten" }
    $d3 = Test-FetcherManifestComplete "cems_geff_seas5_fwi"
    if ($d3 -and $D3_WITHOUT) { throw "STOP: D3 is complete but `$D3_WITHOUT is `$true: settle which holds first" }
    if (-not $d3 -and -not $D3_WITHOUT) { throw "STOP: the D3 outcome is not final: wait for D3 (then F6) or for the 18 Nov cut-off (then F6b)" }
    if ($D3_WITHOUT -and -not $D3_DECISION) { throw "STOP: `$D3_DECISION is empty (F6b)" }
    if (Test-Path "$HOUT\human_board.json") { throw "STOP: the real fire board exists ($HOUT): the DRY pass is over; tell the agent" }
    $n = 0
    if (-not (Test-Path "$DOUT\human_board.json")) {
        $initArgs = @("init", "--run", $FIRE, "--dry")
        if ($D3_WITHOUT) { $initArgs += "--allow-waiting" }
        Invoke-HumanDryCli @initArgs
        $n++
    } else { Write-Host "DRY human_board.json exists: init already done (resuming THIS F7 pass)" }
    if (-not (Test-Path "$DOUT\human_picks.json.lock.json")) {
        Invoke-HumanDryCli tune --out $DOUT --resume
        $lockArgs = @("lock", "--out", $DOUT)
        if ($D3_WITHOUT) { $lockArgs += @("--without", "geff_seas5", "--decision", $D3_DECISION) }
        Invoke-HumanDryCli @lockArgs
        $n += 2
    } else { Write-Host "DRY picks already locked" }
    Show-FireBoardRecord $DOUT
    Complete-FireStep "F7 (DRY pass: copy the lines above into Part section 7)" $n
}
function Invoke-FireStepF8 {
    $global:FIRE_STEPS_RUN = 0
    $file = "D:\treeroute\human_rivals_build\SHAS_FOR_PART_B_" + (Get-Date -Format yyyyMMdd_HHmmss) + ".txt"
    $lines = @(Invoke-HumanCli shas --run $FIRE)
    foreach ($l in $lines) { Write-Host $l }
    $lines | Set-Content -Encoding ascii -LiteralPath $file
    Write-Host "saved: $file (fill Part section 1 from it)"
    Assert-FireShasEqualReference
    Complete-FireStep "F8 (shas equal the F7 DRY board: you may sign Part B)" 1
}
function Invoke-FireBoard([switch]$Signed) {
    $global:FIRE_STEPS_RUN = 0
    if (-not $Signed) { throw "STOP: F9 runs only after you signed Part B (Part section 13). Then call: Invoke-FireBoard -Signed" }
    if ($D3_WITHOUT -and -not $D3_DECISION) { throw "STOP: `$D3_DECISION is empty (F6b)" }
    Assert-FireShasEqualReference
    $n = 0
    if (-not (Test-Path "$HOUT\human_board.json")) {
        $initArgs = @("init", "--run", $FIRE)
        if ($D3_WITHOUT) { $initArgs += "--allow-waiting" }
        Invoke-HumanCli @initArgs
        $n++
    } else { Write-Host "human_board.json exists: init already done" }
    Assert-FireBoardEqualReference
    if (-not (Test-Path "$HOUT\human_picks.json.lock.json")) {
        Invoke-HumanCli tune --out $HOUT --resume
        $lockArgs = @("lock", "--out", $HOUT)
        if ($D3_WITHOUT) { $lockArgs += @("--without", "geff_seas5", "--decision", $D3_DECISION) }
        Invoke-HumanCli @lockArgs
        $n += 2
    } else { Write-Host "picks already locked" }
    Assert-FirePicksEqualDry
    foreach ($L in 0, 6, 12) { Invoke-HumanCli refit --out $HOUT --lead $L --resume; $n++ }
    foreach ($L in 12, 6, 0) { Invoke-HumanCli refs --out $HOUT --lead $L; $n++; Assert-FireRefsParity $L }
    foreach ($L in 0, 6, 12) { Invoke-HumanCli score --out $HOUT --lead $L; $n++ }
    Invoke-HumanCli board --out $HOUT
    $n++
    Complete-FireStep "F9 (fire human board: $HOUT\human_board.md)" $n
}
function Invoke-FireJoin([string]$PartText) {
    $global:FIRE_STEPS_RUN = 0
    if (-not $PartText) { throw "STOP: give the Part numbers, e.g. Invoke-FireJoin -PartText '617 (NDVI board under Part 618), <Part B number>'" }
    Invoke-HumanCli join --runs $CORAL $DEFO $PM $NDVI $FIRE --part $PartText
    Complete-FireStep "F10 (one rival table: D:\treeroute\rivals_table\<stamp>\RIVALS_TABLE.md)" 1
}
$FIRE_FUNCTIONS = @("Invoke-HumanTool", "Invoke-HumanCli", "Invoke-HumanDryCli", "Invoke-FirePython", "Complete-FireStep",
    "Get-SignedShaArgs", "Test-FetcherManifestComplete", "Assert-FetcherRerunAllowed", "Set-FireProductFolder",
    "Invoke-FireRefsByteCheck", "Show-FireBoardRecord", "Assert-FireShasEqualReference", "Assert-FireBoardEqualReference",
    "Assert-FirePicksEqualDry", "Assert-FireRefsParity", "Show-FireCutoffState", "Get-FireBoardStatus", "Invoke-FireStepF1",
    "Invoke-FireStepF2", "Invoke-FireStepF3", "Invoke-FireStepF5", "Invoke-FireStepF6", "Invoke-FireDryPass",
    "Invoke-FireStepF8", "Invoke-FireBoard", "Invoke-FireJoin")
$FIRE_BAD = @($FIRE_FUNCTIONS | Where-Object { (Get-Command $_ -ErrorAction SilentlyContinue).CommandType -ne "Function" })
if ($FIRE_BAD.Count -gt 0) { Write-Host "STOP: these names do not resolve to the functions above: $($FIRE_BAD -join ', ')" } else { Write-Host "OK: $($FIRE_FUNCTIONS.Count) fire functions defined" }
# ----------------------------------------------------- END FIRE SETUP BLOCK -----------------------------------------------------
