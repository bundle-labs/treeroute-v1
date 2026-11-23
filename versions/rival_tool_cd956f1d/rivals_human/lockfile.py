"""The human board's lock and its ONE reader of test labels (SPEC_HUMAN.txt 1.11; PROT H8, H16).

Design copied from the common harness (H:1333-1368 ledger, :1371-1376 test-side traces, verify_lock,
lock, open_test_labels_rivals: the one reader), on the human file names, in the human out root:
- human_picks.json and human_picks.json.lock.json are written once; any change of the picks refuses later commands;
- <index_root>/_ledger/<run fingerprint>.jsonl (outside the board folder; shared by every board on the run's index
  tables, whatever its out_root; review issue 7) records "locked" and "test_labels_opened";
- a lock refuses once a test-side trace exists, or when the ledger shows test labels opened under other picks;
- open_test_labels is the only function that reads a saved test y; it refuses without a valid lock.
A LockToken (made only by verify_lock) is what a slim test read and a stage-test adapter run must show.
"""
# Provenance: harness.py:1907-1936 verify_lock (copied on the human file names).

import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

import pyarrow.parquet as pq

from rivals_human import config as C
from rivals_human.common import refuse

_TOKEN_KEY = object()


class LockToken(object):
    """Proof that a human lock was verified (made only by verify_lock)."""

    def __init__(self, key: object, out: Path, picks_sha256: str, run_fingerprint: str, doc: Mapping[str, Any]):
        if key is not _TOKEN_KEY:
            refuse("internal: a LockToken is made only by lockfile.verify_lock")
        self.out, self.picks_sha256, self.run_fingerprint, self.doc = Path(out), picks_sha256, run_fingerprint, doc


def require_token(token: Any, fingerprint: str, what: str) -> LockToken:
    if not isinstance(token, LockToken):
        refuse("%s needs a valid human lock (test-window labels hide in the test feature files, spec A2)" % what,
               fix="run lock first; tune and lock never open a test file")
    if token.run_fingerprint != fingerprint:
        refuse("%s: the lock is of run %s, not %s" % (what, token.run_fingerprint[:16], fingerprint[:16]))
    return token


def _sha_file(p: Any) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 22), b""):
            h.update(block)
    return h.hexdigest()


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


# ---------------------------------------------------------------------------------------------------- ledger
def _board_doc(out: Any) -> Dict[str, Any]:
    bp = Path(out) / C.BOARD_FILE
    if not bp.is_file():
        refuse("%s holds no %s (the ledger and the DRY mark are read from it)" % (out, C.BOARD_FILE),
               fix="run init first")
    return json.loads(bp.read_text(encoding="utf-8"))


def ledger_path(out: Any, fingerprint: str) -> Path:
    """<index_root>/_ledger/<run fingerprint>.jsonl, index_root read from the board's own human_board.json.
    The ledger is shared by every board that uses the run's index tables, whatever its out_root (review issue 7: a
    ledger per out_root let a second config, e.g. a DRY pass, lock new picks after test labels were opened)."""
    cfgd = _board_doc(out).get("config") or {}
    root = cfgd.get("index_root")
    if not root:
        refuse("%s/%s names no index_root in its config block" % (out, C.BOARD_FILE))
    return Path(str(root)) / C.LEDGER_DIR / ("%s.jsonl" % fingerprint)


def is_dry(out: Any) -> bool:
    return bool(_board_doc(out).get("dry"))


def ledger_read(out: Any, fingerprint: str) -> List[Dict[str, Any]]:
    p = ledger_path(out, fingerprint)
    if not p.is_file():
        return []
    rows = []
    for i, line in enumerate(p.read_text(encoding="utf-8").splitlines()):
        if line.strip():
            try:
                rows.append(json.loads(line))
            except ValueError:
                refuse("the ledger %s line %d is not JSON" % (p, i + 1), fix="the ledger is append-only; restore it")
    return rows


def ledger_append(ctx: Any, fingerprint: str, rec: Mapping[str, Any]) -> None:
    p = ledger_path(ctx.out, fingerprint)
    ctx.eng.writable(p)
    ctx.LY.append_line(p, ctx.H.dumps_canonical(dict(rec, utc=ctx.H.utc_now(), board=str(ctx.out))),
                       ctx.eng.registry)


def ledger_openings(out: Any, fingerprint: Optional[str]) -> List[Dict[str, Any]]:
    if not fingerprint:
        return []
    return [r for r in ledger_read(out, fingerprint) if r.get("event") == "test_labels_opened"]


def picks_content_sha(picks: Mapping[str, Any]) -> str:
    """The hash of WHAT was picked per rival (stat, family, link, form, coverage mask shas), independent of the
    board folder and the code hash."""
    import hashlib
    keep = ("stat", "family", "link", "form", "status", "coverage_sha256")
    rec = {r: {k: p.get(k) for k in keep} for r, p in sorted(picks.items())}
    return hashlib.sha256(_canonical(rec).encode("ascii")).hexdigest()


# ---------------------------------------------------------------------------------------------------- traces
def test_side_files(out: Any) -> List[Path]:
    """Any trace of a test row in the board folder: a test-label record, a lead's test predictions, reference rows."""
    out = Path(out)
    found = sorted(out.glob(C.TEST_LABELS_GLOB))
    found += sorted(out.glob("lead_*/preds_*.parquet"))
    found += sorted(out.glob("lead_*/" + C.REFS_FILE))
    return found


# ---------------------------------------------------------------------------------------------------- verify
def verify_lock(out: Any, allow_dry: bool = False) -> LockToken:
    """The lock is valid: the lock file exists and its sha matches human_picks.json; every test-label record names
    THIS picks sha; the ledger shows no test label opened under other picks (harness verify_lock on the human names).
    A DRY board (init --dry) never gets a token for test-side work (refit, refs, score, stage-test adapt / prep)."""
    out = Path(out)
    lp, pp = out / C.PICKS_LOCK, out / C.PICKS_FILE
    if not lp.is_file() or not pp.is_file():
        refuse("the human picks are not locked (%s missing)" % (lp if not lp.is_file() else pp), fix="run lock")
    if is_dry(out) and not allow_dry:
        refuse("%s is a DRY board (tune-only dry pass): it never refits, scores or reads a test row" % out,
               fix="init a real board under the production config")
    lk = json.loads(lp.read_text(encoding="utf-8"))
    sha = _sha_file(pp)
    if lk.get("sha256") != sha:
        refuse("%s changed after the lock (sha %s vs locked %s)" % (C.PICKS_FILE, sha[:16], str(lk.get("sha256"))[:16]))
    for rp in sorted(out.glob(C.TEST_LABELS_GLOB)):
        rec = json.loads(rp.read_text(encoding="utf-8"))
        named = [rec.get("picks_sha256")] + [h.get("picks_sha256") for h in rec.get("history") or []]
        other = sorted(set(str(x) for x in named if x != sha))
        if other:
            refuse("%s shows test labels opened under picks %s, not the locked picks %s; picks are never re-locked "
                   "after a test label was opened" % (rp.name, [o[:16] for o in other], sha[:16]))
    doc = json.loads(pp.read_text(encoding="utf-8"))
    if doc.get("format") != C.FORMAT_PICKS:
        refuse("%s is not a %s file" % (pp, C.FORMAT_PICKS))
    mine = picks_content_sha(doc["picks"])
    for r in ledger_openings(out, doc.get("run_fingerprint")):
        if r.get("picks_content_sha256") != mine:
            refuse("the human ledger %s shows test labels opened at %s under other picks (content %s, board %s); "
                   "these picks (content %s) are refused" % (ledger_path(out, doc["run_fingerprint"]), r.get("utc"),
                                                             str(r.get("picks_content_sha256"))[:16], r.get("board"),
                                                             mine[:16]))
    return LockToken(_TOKEN_KEY, out, sha, str(doc["run_fingerprint"]), doc)


def write_lock(ctx: Any, doc: Mapping[str, Any]) -> LockToken:
    """Write human_picks.json then its lock (write-once), append "locked" to the ledger."""
    out = ctx.out
    content = picks_content_sha(doc["picks"])
    for r in ledger_openings(out, doc["run_fingerprint"]):
        if r.get("picks_content_sha256") != content:
            refuse("the human ledger shows test labels opened at %s under other picks (content %s, board %s); these "
                   "picks (content %s) are NOT locked" % (r.get("utc"), str(r.get("picks_content_sha256"))[:16],
                                                          r.get("board"), content[:16]),
                   fix="OWNER ITEM: nothing is locked; report this")
    ctx.write_once_json(out / C.PICKS_FILE, doc)
    sha = _sha_file(out / C.PICKS_FILE)
    lk = {"file": C.PICKS_FILE, "sha256": sha, "utc": ctx.H.utc_now(), "picks_content_sha256": content,
          "rule": "PROT H8/H16: every human rival's pick and coverage mask are locked before any test file or test "
                  "label is read; a changed human_picks.json is refused by every later command"}
    ctx.write_once_json(out / C.PICKS_LOCK, lk)
    ledger_append(ctx, doc["run_fingerprint"], {"event": "locked", "picks_sha256": sha, "picks_content_sha256": content,
                                                "dry": is_dry(out)})
    return verify_lock(out, allow_dry=True)


# ---------------------------------------------------------------------------------------------------- the ONE reader
def open_test_labels(ctx: Any, run: Any, lead: int, need_files: Sequence[Path] = ()) -> Dict[str, Any]:
    """The ONE reader of test y (spec 1.11). Refuses without a valid lock or when a needed prediction file is
    missing; appends "test_labels_opened" to the ledger, reads the lead's saved test_preds WITH y, records its
    sha256 in test_labels_opened_human_lead_<L>.json. Returns {"frame", "sha256", "token"}."""
    token = verify_lock(ctx.out)
    missing = [str(p) for p in need_files if not Path(p).is_file()]
    if missing:
        refuse("lead %d: missing %s" % (int(lead), missing[:3]), fix="refit (and refs) --lead %d first" % int(lead))
    path = run.test_preds_path(int(lead))
    content = picks_content_sha(token.doc["picks"])
    ledger_append(ctx, run.fingerprint, {"event": "test_labels_opened", "lead": int(lead),
                                         "picks_sha256": token.picks_sha256, "picks_content_sha256": content})
    sha = _sha_file(path)
    frame = pq.read_table(str(path)).to_pandas()
    rec = {"utc": ctx.H.utc_now(), "picks_sha256": token.picks_sha256, "picks_content_sha256": content,
           "rows": int(len(frame)), "file": str(path), "lead": int(lead), "test_preds_sha256": sha}
    rp = ctx.out / (C.TEST_LABELS_OPENED % int(lead))
    history = json.loads(rp.read_text(encoding="utf-8")).get("history", []) if rp.is_file() else []
    ctx.replace_json(rp, dict(rec, history=history + [rec]))
    return {"frame": frame, "sha256": sha, "token": token}
