"""Print the LIVE engine's own code hashes through its own fingerprint module (read only).

    py -3.9 -I -B engine_hashes.py

engine_code_sha256 (file bytes; the check-report / install hash, expected 930d961c...) and engine_code_hash
(comment-stripped tokens; the run manifest's hash, expected 85c64b55... as in the headline manifest).
sys.dont_write_bytecode is set before the engine is imported, so no .pyc is written into the engine tree.
"""
import sys

sys.dont_write_bytecode = True
ENGINE = r"C:\Users\moh the ghost\Desktop\data set for reserch paper\engine"
sys.path.insert(0, ENGINE)

from treeroute.runs.fingerprint import engine_code_hash, engine_code_sha256  # noqa: E402

print("engine_code_sha256 %s" % engine_code_sha256())
print("engine_code_hash   %s" % engine_code_hash())
