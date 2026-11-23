"""treeroute.layer: the one Type-2 layer (plan 4.2 layer/ row; R22-R29). SCIENCE: owner-approved
signatures (treeroute/_proposed/layer.py, approved by the owner rulings file, sections A-F), agent
bodies, gated by the legacy harness (legacy_harness/layer_replay.py).

Modules:
  - arms.py    the arm shapes (Tool, Weighting, ArmSpec), R24's candidate list and the arms of a
               forecast lead (R29), arm names and the tree-answer table each arm reads.
  - links.py   R22's link transforms and their inverses, R23's c (one c per lead cut from donor
               rows, D63 a), and R28's legal clip with its pre-clip counts.
  - decide.py  R26's penalty search on the decision surface (edge picks flagged, never extended),
               the N2 guard, R27's MAE adoption with the decline to the arithmetic normal, R29's
               pinned lead adoption, G-PLUMB's runtime identities and decide(), which runs them on
               one decision surface. decide() never receives a test row.

The adoption records decide() returns are locked by labels/vault.py (lock_adoption,
lock_lead_adoption) before any test label opens.

Importing this package imports none of its modules (so labels/vault.py and fit/context.py can import
layer.arms and layer.decide without an import cycle): import the submodules by name.
"""

# Where each approved layer rule lives in the engine (the approved RULE_HOME names 'layer.<function>';
# the engine splits the layer into three modules).
RULE_HOME = {
    "R23": "layer.links.c_for_cut",
    "R24": "layer.arms.candidate_arms",
    "R26": "layer.decide.penalty_search",
    "R27": "layer.decide.select_adoption",
    "R28": "layer.links.clip_to_legal",
    "R29": "layer.decide.forecast_adoption",
}

__all__ = ["RULE_HOME"]
