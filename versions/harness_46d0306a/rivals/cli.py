"""Command line of the common-rival board (SPEC_RIVALS 2.1 and 3.1).

    py -3.9 -m rivals.cli export ... --config <rivals yaml>   (dispatched to rivals.export.main; it pins threads
                                                              itself through the engine's launcher, so the
                                                              shell must stay clean and nothing is set here)
    py -3.9 -m rivals.cli init   --run <run folder> --export <export lead_0 folder> --out <out_root> --config <yaml>
                                 [--extra-learners hgb_l1]
    py -3.9 -m rivals.cli probe  --out <board folder> --lead 0 --config <yaml>
    py -3.9 -m rivals.cli tune   --out <board folder> --resume --config <yaml>
    py -3.9 -m rivals.cli lock   --out <board folder> --config <yaml>
    py -3.9 -m rivals.cli refit  --out <board folder> --lead <L> --resume --config <yaml>
    py -3.9 -m rivals.cli score  --out <board folder> --lead <L> --config <yaml>
    py -3.9 -m rivals.cli board  --out <board folder> --config <yaml>
    py -3.9 -m rivals.cli status --out <board folder>                    (read-only; no lock)
    py -3.9 -m rivals.cli unlock --config <yaml>                         (moves a STALE heavy-job lock aside)

Every command except status takes --config <rivals.yaml> and refuses without it (robustness review 2: the
default config would take the build's test lock and write into the build folders). Every heavy command takes
the engine's heavy-job lock (from the config's machine_file) and refuses when it is held.
Exit codes: 0 done; 2 refused (one plain line says why and how to fix it).
"""
# Provenance: SPEC_RIVALS.md 2.1, 3.1, 3.10 (threads: OMP/MKL/OPENBLAS/NUMEXPR set to 8 BEFORE numpy
# is imported, then threadpoolctl limits; memory note "--jobs changes results"). Review fixes (rivals review):
# robustness 1 (engine refusals print one plain line; unlock; status), 2 (--config required), 13 (logs).

import os
import sys
import warnings

PIN_VARS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")
PIN_VALUE = "8"
HARNESS_COMMANDS = ("init", "probe", "tune", "lock", "refit", "score", "board", "status", "unlock")
NO_CONFIG_COMMANDS = ("status",)
EXIT_REFUSED = 2


def quiet_warnings():
    """The dask FutureWarning that every command printed (7 lines) says nothing to the owner."""
    warnings.filterwarnings("ignore", category=FutureWarning, module=r"dask(\..*)?")
    warnings.filterwarnings("ignore", message=r".*dask.*", category=FutureWarning)


def pin_threads():
    """Set the thread pins before numpy loads; refuse if numpy is already loaded with other pins."""
    if "numpy" in sys.modules:
        bad = [v for v in PIN_VARS if os.environ.get(v) != PIN_VALUE]
        if bad:
            raise SystemExit("REFUSED: numpy was imported before the thread pins (%s not %s); start "
                             "the command fresh with py -3.9 -m rivals.cli" % (", ".join(bad), PIN_VALUE))
        return
    for v in PIN_VARS:
        os.environ[v] = PIN_VALUE


def _parser():
    import argparse
    p = argparse.ArgumentParser(prog="rivals.cli", description="the common-rival board")
    sub = p.add_subparsers(dest="command", required=True)

    def add(name, help_text, config=True):
        sp = sub.add_parser(name, help=help_text)
        if config:
            sp.add_argument("--config", required=True, help="rivals.yaml (paths only); always given")
        return sp

    sp = add("init", "write board.json once")
    sp.add_argument("--run", required=True, help="the finished run folder")
    sp.add_argument("--export", required=True, help="the export's lead_0 folder of that run")
    sp.add_argument("--out", required=True, help="the out root; the board goes to <out>/<package>/<run>")
    sp.add_argument("--extra-learners", nargs="*", default=[], help="only hgb_l1 (R-C6)")
    sp = add("probe", "20-round LightGBM + 10-tree RF at the real shape: time and peak RAM")
    sp.add_argument("--out", required=True)
    sp.add_argument("--lead", type=int, default=0)
    sp = add("tune", "tune every learner on the inner window (lead 0)")
    sp.add_argument("--out", required=True)
    sp.add_argument("--resume", action="store_true")
    sp = add("lock", "lock the picks (hashed) before any test row is read")
    sp.add_argument("--out", required=True)
    sp = add("refit", "guard, refit and predict the test rows of one lead (after the lock)")
    sp.add_argument("--out", required=True)
    sp.add_argument("--lead", type=int, required=True)
    sp.add_argument("--resume", action="store_true")
    sp = add("score", "score one lead with the engine's own metric functions")
    sp.add_argument("--out", required=True)
    sp.add_argument("--lead", type=int, required=True)
    sp = add("board", "board.md from every scored lead")
    sp.add_argument("--out", required=True)
    sp = add("status", "plain progress of a board (read-only)", config=False)
    sp.add_argument("--out", required=True)
    add("unlock", "move a stale heavy-job lock aside (only when its process is dead)")
    return p


def _refusal_types():
    """The refusals that print one plain line: the harness's, the layout's and every engine refusal
    (treeroute.errors.RefusedError, which includes the heavy-job lock's PreflightRefusal)."""
    from rivals import harness as H
    from rivals import layout as LY
    types = [H.HarnessRefusal, LY.LayoutRefusal]
    try:
        from treeroute.errors import RefusedError
        types.append(RefusedError)
    except ImportError:
        pass
    return tuple(types)


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "export":
        if "--config" not in argv[1:] and not any(a.startswith("--config=") for a in argv[1:]):
            print("REFUSED: export needs --config <rivals yaml> (the production config names the engine's "
                  "machine file, so its heavy-job lock is the engine's)", flush=True)
            return EXIT_REFUSED
        quiet_warnings()
        from rivals import export
        return int(export.main(argv[1:]) or 0)
    if argv and argv[0] not in HARNESS_COMMANDS and not argv[0].startswith("-"):
        print("REFUSED: unknown command %r (export, %s)" % (argv[0], ", ".join(HARNESS_COMMANDS)))
        return EXIT_REFUSED
    pin_threads()
    quiet_warnings()
    try:
        args = _parser().parse_args(argv)
    except SystemExit as exc:
        return EXIT_REFUSED if exc.code not in (0, None) else 0
    from rivals import harness as H
    try:
        if args.command == "init":
            out = H.init(args.run, args.export, args.out, args.extra_learners, config=args.config)
            print("board folder: %s" % out)
        elif args.command == "probe":
            H.probe(args.out, args.lead, config=args.config)
        elif args.command == "tune":
            H.tune(args.out, resume=args.resume, config=args.config)
        elif args.command == "lock":
            H.lock(args.out, config=args.config)
        elif args.command == "refit":
            H.refit(args.out, args.lead, resume=args.resume, config=args.config)
        elif args.command == "score":
            H.score(args.out, args.lead, config=args.config)
        elif args.command == "board":
            H.board(args.out, config=args.config)
        elif args.command == "status":
            print(H.status(args.out), flush=True)
        elif args.command == "unlock":
            print(H.unlock(config=args.config), flush=True)
    except Exception as exc:
        if not isinstance(exc, _refusal_types()):      # types read now: the engine is imported by then
            raise
        text = str(exc)
        print("REFUSED: %s" % text, flush=True)
        if "stale heavy-job lock" in text:
            print("FIX: the last job died (power cut, sleep or a kill). Run:  py -3.9 -B -m rivals.cli unlock "
                  "--config %s  then rerun your command with --resume" % getattr(args, "config", "<yaml>"),
                  flush=True)
        return EXIT_REFUSED
    return 0


if __name__ == "__main__":
    sys.exit(main())
