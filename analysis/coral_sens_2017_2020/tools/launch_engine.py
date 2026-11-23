"""Start the LIVE engine's own entry point (treeroute.launch.main) from OUTSIDE the engine tree, read only.

    py -3.9 -I -B -W "ignore:DataFrame is highly fragmented" -u launch_engine.py <command> <package path> --run-root <dir>

Why a launcher: `py -3.9 -I` (isolated mode) does not put the current folder on sys.path, so `-m treeroute` cannot be
used from the engine folder. This file does only what `py -3.9 -m treeroute` does (engine/treeroute/__main__.py:
`from treeroute import launch; launch.main()`), after putting the engine folder first on sys.path and setting
sys.dont_write_bytecode, so no .pyc is ever written into the LIVE engine tree. It imports no numeric module before
the launcher's thread pins (launch.py refuses otherwise). Nothing in the engine reads argv[0]; it is only recorded in
the run manifest ("argv").
"""
import sys

sys.dont_write_bytecode = True
ENGINE = r"C:\Users\moh the ghost\Desktop\data set for reserch paper\engine"
sys.path.insert(0, ENGINE)

from treeroute import launch  # noqa: E402

if __name__ == "__main__":
    launch.main()
