"""Command line of the human-rival tool (SPEC_HUMAN.txt 1.13). Run from the build root with py -3.9 -B:

    py -3.9 -B -m rivals_human.cli manifest --product <id> [--verify] --config <yaml>
    py -3.9 -B -m rivals_human.cli slim     --run <run> --export <export lead folder> --config <yaml>
    py -3.9 -B -m rivals_human.cli adapt    --run <run> --rival <id> --lead <L|all> [--stage train|test] --config <yaml>
    py -3.9 -B -m rivals_human.cli prep     --run <run> --rival <id> [--stage train|test] --config <yaml>
    py -3.9 -B -m rivals_human.cli check    --run <run> --rival <id> --config <yaml>
    py -3.9 -B -m rivals_human.cli init     --run <run> [--dry] [--allow-waiting] --config <yaml>
    py -3.9 -B -m rivals_human.cli tune     --out <board> --resume --config <yaml>
    py -3.9 -B -m rivals_human.cli lock     --out <board> [--without <id> ... --decision "<text>"] --config <yaml>
    py -3.9 -B -m rivals_human.cli refit    --out <board> --lead <L> --resume --config <yaml>
    py -3.9 -B -m rivals_human.cli refs     --out <board> --lead <L> --config <yaml>
    py -3.9 -B -m rivals_human.cli score    --out <board> --lead <L> --config <yaml>
    py -3.9 -B -m rivals_human.cli board    --out <board> --config <yaml>
    py -3.9 -B -m rivals_human.cli join     --runs <run folders> [--pending <run folders>] [--part <n>] --config <yaml>
    py -3.9 -B -m rivals_human.cli shas     --run <run> --config <yaml>          (read-only: hashes for the Part draft)
    py -3.9 -B -m rivals_human.cli status   --out <board>                        (read-only, no lock, no config)

Every command except status takes --config and refuses without it (the build config's machine file holds a TEST
heavy-job lock; the production config names the engine's machine file, so its lock is the engine's). Every heavy
command takes the engine heavy-job lock and the RAM watchdog. Threads pinned to 8 before numpy loads.
Exit codes: 0 done; 2 refused (one plain line says why and how to fix it).
"""
# Provenance: SPEC_HUMAN.txt 1.13; D:/treeroute/rivals_build/rivals/cli.py:22-46 (thread pins, refusal lines,
# --config required: robustness review 2 of the common build).

import os
import sys
import warnings

sys.dont_write_bytecode = True

PIN_VARS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")
PIN_VALUE = "8"
COMMANDS = ("manifest", "slim", "adapt", "prep", "check", "init", "tune", "lock", "refit", "refs", "score", "board", "join",
            "shas", "status")
EXIT_REFUSED = 2


def pin_threads():
    if "numpy" in sys.modules:
        bad = [v for v in PIN_VARS if os.environ.get(v) != PIN_VALUE]
        if bad:
            raise SystemExit("REFUSED: numpy was imported before the thread pins (%s not %s); start the command "
                             "fresh with py -3.9 -B -m rivals_human.cli" % (", ".join(bad), PIN_VALUE))
        return
    for v in PIN_VARS:
        os.environ[v] = PIN_VALUE


def _parser():
    import argparse
    p = argparse.ArgumentParser(prog="rivals_human.cli", description="the human-rival tool")
    sub = p.add_subparsers(dest="command", required=True)

    def add(name, help_text, config=True):
        sp = sub.add_parser(name, help=help_text)
        if config:
            sp.add_argument("--config", required=True, help="human_rivals.yaml (paths only); always given")
        return sp

    sp = add("manifest", "hash an on-disk product (1.8)")
    sp.add_argument("--product", required=True)
    sp.add_argument("--verify", action="store_true", help="re-check a download's own manifest")
    sp = add("slim", "copy the human columns of one export lead (1.3)")
    sp.add_argument("--run", required=True)
    sp.add_argument("--export", required=True, help="the export's lead_<L> folder")
    sp = add("adapt", "run a rival's adapter: index table per lead (1.4)")
    sp.add_argument("--run", required=True)
    sp.add_argument("--rival", required=True)
    sp.add_argument("--lead", default="all")
    sp.add_argument("--stage", default=None, choices=["all", "train", "test"])
    sp = add("prep", "run a rival's registry prep step (owner prep command)")
    sp.add_argument("--run", required=True)
    sp.add_argument("--rival", required=True)
    sp.add_argument("--stage", default="train", choices=["train", "test"], help="test: only after the human lock")
    sp = add("check", "re-check a rival's index tables (1.4, 1.5)")
    sp.add_argument("--run", required=True)
    sp.add_argument("--rival", required=True)
    sp = add("init", "write human_board.json once")
    sp.add_argument("--run", required=True)
    sp.add_argument("--dry", action="store_true", help="a DRY board (tune-only dry pass): refit, refs and score refuse")
    sp.add_argument("--allow-waiting", action="store_true",
                    help="init although a non-optional parity rival is waiting (owner decision; then lock --without)")
    sp = add("tune", "fit and score every candidate on its pick set")
    sp.add_argument("--out", required=True)
    sp.add_argument("--resume", action="store_true")
    sp = add("lock", "lock picks, coverage masks and hashes before any test row")
    sp.add_argument("--out", required=True)
    sp.add_argument("--without", nargs="*", default=[], help="waiting rivals left out by an owner decision")
    sp.add_argument("--decision", default="", help="the owner decision text (recorded in the lock and the Part)")
    sp = add("refit", "guard, refit and predict one lead (after the lock)")
    sp.add_argument("--out", required=True)
    sp.add_argument("--lead", type=int, required=True)
    sp.add_argument("--resume", action="store_true")
    sp = add("refs", "reference rows (parity proof first; after the lock)")
    sp.add_argument("--out", required=True)
    sp.add_argument("--lead", type=int, required=True)
    sp = add("score", "score one lead (the one reader of test labels)")
    sp.add_argument("--out", required=True)
    sp.add_argument("--lead", type=int, required=True)
    sp = add("board", "human_board.md from every scored lead")
    sp.add_argument("--out", required=True)
    sp = add("join", "ONE rival table from the common and human boards")
    sp.add_argument("--runs", nargs="*", default=[])
    sp.add_argument("--pending", nargs="*", default=[],
                    help="runs whose human rivals come in a later Part: common rows + one 'pending' row per lead")
    sp.add_argument("--part", default="")
    sp = add("shas", "print the hashes a Part draft lists (read-only)")
    sp.add_argument("--run", required=True)
    sp = add("status", "plain progress of a human board (read-only)", config=False)
    sp.add_argument("--out", required=True)
    return p


def shas(run_folder, config) -> str:
    """Tool, harness, registry and product-manifest hashes of one run's package (read-only)."""
    from rivals_human import config as C
    from rivals_human import index as IX
    from rivals_human.common import load, tool_code_sha
    cfg = C.load_config(config)
    LY, H = load(cfg)
    run = H.Run(run_folder)
    reg = C.load_registry(cfg, run.package)
    prods = C.load_products(cfg)
    from rivals_human.common import check_common_board
    cb = check_common_board(H, cfg, run.package, run.name, required=False)
    lines = ["run %s fingerprint %s" % (run.name, run.fingerprint), "common harness %s" % H.harness_code_sha(),
             "common board %s" % ("none yet" if cb is None else "%s harness %s%s" % (
                 cb["sha256"], cb["board"].get("harness_code_sha256"),
                 "" if cb["harness_accepted_as"] is None else " (accepted older harness: %s)" % cb["harness_accepted_as"])),
             "human tool code %s" % tool_code_sha(), "registry %s %s" % (reg["_file"], H.sha256_file(reg["_file"])),
             "registry schema %s" % H.sha256_file(C.registry_dir(cfg) / C.SCHEMA_FILE),
             "product registry %s %s" % (cfg.path("on_disk_products"), H.sha256_file(cfg.path("on_disk_products")))]
    seen = set()
    for r in reg["rivals"]:
        for pid in r.get("products") or []:
            if pid in seen:
                continue
            seen.add(pid)
            p = IX.product_manifest_path(cfg, prods, pid)
            lines.append("product %s: %s" % (pid, ("%s %s" % (H.sha256_file(p), p)) if p.is_file()
                                              else "NO MANIFEST (%s)" % p))
    return "\n".join(lines)


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] not in COMMANDS and not argv[0].startswith("-"):
        print("REFUSED: unknown command %r (%s)" % (argv[0], ", ".join(COMMANDS)))
        return EXIT_REFUSED
    pin_threads()
    warnings.filterwarnings("ignore", category=FutureWarning, module=r"dask(\..*)?")
    try:
        args = _parser().parse_args(argv)
    except SystemExit as exc:
        return EXIT_REFUSED if exc.code not in (0, None) else 0
    from rivals_human import common
    try:
        c = getattr(args, "config", None)
        if args.command == "manifest":
            from rivals_human import manifest
            print(manifest.manifest(args.product, c, verify=args.verify))
        elif args.command == "slim":
            from rivals_human import slim
            print("slim lead folder: %s" % slim.slim(args.run, args.export, c))
        elif args.command == "adapt":
            from rivals_human import index
            for p in index.adapt(args.run, args.rival, args.lead, args.stage, c):
                print("index table: %s" % p)
        elif args.command == "prep":
            from rivals_human import index
            print("prep result: %s" % (index.prep(args.run, args.rival, c, stage=args.stage),))
        elif args.command == "check":
            import json
            from rivals_human import index
            print(json.dumps(index.check(args.run, args.rival, c), indent=1, sort_keys=True, default=str))
        elif args.command == "init":
            from rivals_human import board
            print("human board folder: %s" % board.init(args.run, c, dry=args.dry, allow_waiting=args.allow_waiting))
        elif args.command == "tune":
            from rivals_human import board
            board.tune(args.out, resume=args.resume, config=c)
        elif args.command == "lock":
            from rivals_human import board
            board.lock(args.out, config=c, without=args.without, decision=args.decision)
        elif args.command == "refit":
            from rivals_human import board
            board.refit(args.out, args.lead, resume=args.resume, config=c)
        elif args.command == "refs":
            from rivals_human import refs
            refs.refs(args.out, args.lead, config=c)
        elif args.command == "score":
            from rivals_human import board
            board.score(args.out, args.lead, config=c)
        elif args.command == "board":
            from rivals_human import board
            board.board_md(args.out, config=c)
        elif args.command == "join":
            from rivals_human import join
            print("rival table: %s" % join.join(args.runs, c, part=args.part, pending=args.pending))
        elif args.command == "shas":
            print(shas(args.run, c))
        elif args.command == "status":
            from rivals_human import board
            print(board.status(args.out), flush=True)
    except Exception as exc:
        if not isinstance(exc, common.refusal_types()):
            raise
        text = str(exc)
        print("REFUSED: %s" % text, flush=True)
        if "stale heavy-job lock" in text:
            print("FIX: the last job died; check no python job runs, move the stale lock aside (py -3.9 -B -m "
                  "rivals.cli unlock --config <the common production yaml>), then rerun with --resume", flush=True)
        return EXIT_REFUSED
    return 0


if __name__ == "__main__":
    sys.exit(main())
