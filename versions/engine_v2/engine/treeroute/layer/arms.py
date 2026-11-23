"""R24: the arms of the Type-2 layer, and the arms built at one forecast lead (R29).

SCIENCE bodies for the owner-approved signatures candidate_arms and lead_arms
(treeroute/_proposed/layer.py; owner rulings A-F). The shapes Tool, Weighting and ArmSpec are
FIELD-IDENTICAL copies of the approved shapes in the proposed common module, which engine code may not
import (G-IMPORT). The link enum is derive's copy (treeroute.derive.shapes.Link), the one R22 returns.

Arms (R24). Per link: plain and corrector, each unweighted and GLS-weighted (selectable); trees-off,
unweighted (intercept + normal only, R16; not selectable, it is the guard reference); one placebo per
link x weighting (the scrambled-residual corrector; never selectable, built once at the test pass,
plan 4.1 step 9). Fixed order: links in R22 order (identity, log_c, arcsine); within a link plain before
corrector, unweighted before GLS; then the trees-off arms; then the placebos. The order is the tie
rule of the adoption (D65: the first eligible arm in this order wins a tie in MAE).

Link keys. candidate_arms and lead_arms build arms of R22's links only. A link key that is not R22's
(the legacy harness replays the shipped log1p link, which R22 does not have) enters a decision ONLY
through a declared LegacyCandidates list: the harness names every arm in the shipped candidate order
and the reason, select_adoption and decide() check the tie order against it, and the declaration is
written into the locked adoption.json. Without it every decision function refuses a non-R22 key.
"""
# Provenance for the module: plan 2.4 R24, R29; pm25_adaptation.py:705-708 (ARM table: plain, corrector,
# placebo, trees-off per link), :824-825 (INNER_ARMS: every plain link, then every corrector link),
# :980-986 (TEST_ARMS); C13.

from dataclasses import dataclass
from enum import Enum
from numbers import Integral
from typing import Any, Iterable, Optional, Tuple

from treeroute.derive.shapes import Link
from treeroute.errors import RefusedError

# R22 order of the links (the fixed order of candidate_arms)
R22_ORDER = (Link.IDENTITY, Link.LOG_C, Link.ARCSINE)


class LayerRefusal(RefusedError):
    """A layer rule refused (R22-R29, G-CLIP, G-PLUMB, G-LOCK). Nothing catches it to carry on."""


# ---------------------------------------------------------------------------------------------------
# Shapes (field-identical to the approved shared shapes)
class Tool(Enum):
    """R24 arm tools."""
    PLAIN = "plain"
    CORRECTOR = "corrector"
    PLACEBO_CORRECTOR = "placebo_corrector"   # scrambled residual, never selectable
    TREES_OFF = "trees_off"                   # intercept + normal only (R16)


class Weighting(Enum):
    UNWEIGHTED = "unweighted"
    GLS = "gls"


@dataclass(frozen=True)
class ArmSpec:
    """One Type-2 candidate (R24)."""
    link: Any                          # Link (R22); another Enum key only inside a LegacyCandidates list
    tool: Tool
    weighting: Weighting
    selectable: bool                   # False for placebo and trees-off


SELECTABLE_TOOLS = (Tool.PLAIN, Tool.CORRECTOR)

# the tree-answer table each tool reads (fit/tables.py kinds); trees-off reads none
_TABLE_KIND = {Tool.PLAIN: "plain", Tool.CORRECTOR: "corrector",
               Tool.PLACEBO_CORRECTOR: "placebo_corrector", Tool.TREES_OFF: None}


# ---------------------------------------------------------------------------------------------------
def link_value(link: Any) -> str:
    """The value string of a link key (an Enum member with a non-empty string value)."""
    if not isinstance(link, Enum) or not isinstance(link.value, str) or not link.value:
        raise LayerRefusal("R22", "a link must be an Enum member with a string value (the R22 Link, "
                           "or a harness key), got %r" % (link,),
                           fix="pass treeroute.derive.shapes.Link members")
    return link.value


def check_arm(arm: Any, engine_link_only: bool = False) -> "ArmSpec":
    """Refuse anything that is not a well-formed ArmSpec: a tool and weighting of this module's enums,
    selectable exactly for plain and corrector, trees-off unweighted (R24), and a link key (R22's
    Link when engine_link_only). Returns the arm."""
    if not isinstance(arm, ArmSpec):
        raise LayerRefusal("R24", "an arm must be an ArmSpec, got %s" % type(arm).__name__)
    if not isinstance(arm.tool, Tool) or not isinstance(arm.weighting, Weighting):
        raise LayerRefusal("R24", "arm %r: tool and weighting must be the layer's Tool and Weighting "
                           "members" % (arm,))
    if engine_link_only and not isinstance(arm.link, Link):
        raise LayerRefusal("R22", "arm %r: the engine builds arms of R22's links only (Link), got %r"
                           % (arm, arm.link), fix="take the links from derived.json's R22 entry")
    link_value(arm.link)
    if not isinstance(arm.selectable, bool):
        raise LayerRefusal("R24", "arm %r: selectable must be a bool" % (arm,))
    want = arm.tool in SELECTABLE_TOOLS
    if arm.selectable != want:
        raise LayerRefusal("R24", "arm %r: a %s arm is %sselectable (R24: plain and corrector arms "
                           "are selectable; trees-off and the placebo never)"
                           % (arm, arm.tool.value, "" if want else "never "))
    if arm.tool is Tool.TREES_OFF and arm.weighting is not Weighting.UNWEIGHTED:
        raise LayerRefusal("R24", "trees-off is unweighted (R16, R24), got %r" % (arm,))
    return arm


def arm_name(arm: ArmSpec) -> str:
    """The arm's name in records and saved predictions: '<link>_<tool>_<weighting>'."""
    check_arm(arm)
    return "%s_%s_%s" % (link_value(arm.link), arm.tool.value, arm.weighting.value)


def table_kind(arm: ArmSpec) -> Optional[str]:
    """The tree-answer table the arm reads ('plain', 'corrector', 'placebo_corrector'); None for
    trees-off, which reads no tree answer."""
    return _TABLE_KIND[check_arm(arm).tool]


def trees_off_of(link: Any) -> ArmSpec:
    """The trees-off arm of a link (unweighted, not selectable): the arm's guard reference (R16)."""
    link_value(link)
    return ArmSpec(link=link, tool=Tool.TREES_OFF, weighting=Weighting.UNWEIGHTED, selectable=False)


def placebo_of(arm: ArmSpec) -> ArmSpec:
    """The placebo of a tree arm: the scrambled-residual corrector of the same link x weighting."""
    check_arm(arm)
    if arm.tool not in SELECTABLE_TOOLS:
        raise LayerRefusal("R24", "only a tree arm has a placebo, got %r" % (arm,))
    return ArmSpec(link=arm.link, tool=Tool.PLACEBO_CORRECTOR, weighting=arm.weighting,
                   selectable=False)


def _engine_links(links: Iterable[Any]) -> Tuple[Link, ...]:
    """R22's link set in R22 order; refuses an empty set, a non-Link, a repeat, no identity."""
    given = tuple(links)
    if not given:
        raise LayerRefusal("R24", "the link set is empty", fix="pass derived.json's R22 link set")
    bad = [x for x in given if not isinstance(x, Link)]
    if bad:
        raise LayerRefusal("R22", "the link set holds %r, not R22 links" % (bad,),
                           fix="pass derived.json's R22 link set (treeroute.derive.shapes.Link)")
    if len(set(given)) != len(given):
        raise LayerRefusal("R24", "the link set repeats a link: %r" % (given,))
    if Link.IDENTITY not in given:
        raise LayerRefusal("R24", "the link set %r has no identity link; identity is always a link "
                           "(R22) and its trees-off is the decline target (R16)" % (given,))
    return tuple(link for link in R22_ORDER if link in given)


# Provenance: plan 2.4 R24; C13; ARM table at pm25_adaptation.py:705-708, INNER_ARMS at :824-825.
def candidate_arms(links: Tuple[Link, ...]) -> Tuple[ArmSpec, ...]:
    """R24: the nowcast candidate list.

    Rule: R24. Per link (R22 order): plain unweighted, plain GLS, corrector unweighted, corrector GLS
    (selectable); then each link's trees-off (unweighted, not selectable: the guard reference); then
    each link's placebo, unweighted then GLS (never selectable). The order is fixed: it is the tie rule
    of select_adoption (D65).
    Returns the candidate arms in that order.
    Refuses: a link set without identity; an empty set; a repeated link; anything but R22's Link.
    """
    ordered = _engine_links(links)
    selectable = [ArmSpec(link=link, tool=tool, weighting=weighting, selectable=True)
                  for link in ordered
                  for tool in (Tool.PLAIN, Tool.CORRECTOR)
                  for weighting in (Weighting.UNWEIGHTED, Weighting.GLS)]
    trees_off = [trees_off_of(link) for link in ordered]
    placebos = [ArmSpec(link=link, tool=Tool.PLACEBO_CORRECTOR, weighting=weighting, selectable=False)
                for link in ordered for weighting in (Weighting.UNWEIGHTED, Weighting.GLS)]
    return tuple(selectable + trees_off + placebos)


def selectable_order(links: Tuple[Link, ...]) -> Tuple[ArmSpec, ...]:
    """The selectable arms of candidate_arms(links), in candidate order (the tie order, D65)."""
    return tuple(a for a in candidate_arms(links) if a.selectable)


# Provenance: plan 2.4 R24, R29 (at forecast leads only the pinned arm's placebo is built, at the
# longest lead; other arms are diagnostic).
def lead_arms(pinned: ArmSpec, lead: int, longest_lead: int) -> Tuple[ArmSpec, ...]:
    """The arms built at one forecast lead: the pinned arm and its link's trees-off; its placebo only
    at the longest lead.

    Rule: R24, R29. Returns (pinned, trees-off of its link) and, when lead equals longest_lead, the
    pinned arm's placebo (its link x weighting) last.
    Refuses: lead 0 or below (the nowcast uses candidate_arms); a lead above the longest lead; a
    pinned arm that is not a selectable tree arm.
    """
    check_arm(pinned)
    if not pinned.selectable:
        raise LayerRefusal("R29", "the pinned arm %r is not a tree arm; R29 pins the nowcast's adopted "
                           "arm or its best tree arm" % (pinned,))
    lead = _positive_int(lead, "lead", "R29")
    longest = _positive_int(longest_lead, "longest_lead", "R29")
    if lead > longest:
        raise LayerRefusal("R29", "lead %d is beyond the longest lead %d of the lead plan"
                           % (lead, longest), fix="pass R10's longest lead")
    arms = [pinned, trees_off_of(pinned.link)]
    if lead == longest:
        arms.append(placebo_of(pinned))
    return tuple(arms)


def _positive_int(value: Any, what: str, rule: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise LayerRefusal(rule, "%s must be a whole number, got %r" % (what, value))
    value = int(value)
    if value < 1:
        raise LayerRefusal(rule, "%s must be at least 1 (lead 0 is the nowcast, which uses "
                           "candidate_arms), got %d" % (what, value))
    return int(value)


# ---------------------------------------------------------------------------------------------------
# Provenance: plan 4.4 (legacy variants live in the harness); pm25_adaptation.py:900-905 (NORMAL_OF: per
# link, plain then corrector, the order the shipped min() breaks ties in).
@dataclass(frozen=True)
class LegacyCandidates:
    """A DECLARED legacy candidate list, for harness replays only: the decision surface's arms in the
    shipped candidate order (selectable tree arms, then the trees-off arms, no placebo), where a link key
    that is not R22's is allowed, and the reason. It is the only way a non-R22 link key enters a
    decision: select_adoption and decide() check the tie order against it, and decide() writes the
    declaration (reason, arms) into the adoption document the vault locks.

    Refuses on construction: an empty reason; no arm; a malformed or repeated arm; a placebo; a
    selectable arm after a trees-off arm; a selectable arm whose link has no trees-off in the list; no
    identity-link trees-off (the decline target)."""
    arms: Tuple[ArmSpec, ...]
    reason: str

    def __post_init__(self):
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise LayerRefusal("R22", "a legacy candidate list names its reason (why the replay needs a "
                                      "link R22 does not have)")
        arms = tuple(self.arms) if isinstance(self.arms, (tuple, list)) else None
        if not arms:
            raise LayerRefusal("R24", "a legacy candidate list needs its arms, in the shipped order")
        for arm in arms:
            check_arm(arm)
            if arm.tool is Tool.PLACEBO_CORRECTOR:
                raise LayerRefusal("R24", "a placebo is never a candidate of the decision surface: %s"
                                   % arm_name(arm))
        if len(set(arms)) != len(arms):
            raise LayerRefusal("R24", "the legacy candidate list repeats an arm")
        kinds = [a.selectable for a in arms]
        if kinds != sorted(kinds, reverse=True):
            raise LayerRefusal("R24", "the legacy candidate list puts a tree arm after a trees-off arm; "
                                      "the order is every selectable arm, then the trees-off arms")
        off_links = [a.link for a in arms if a.tool is Tool.TREES_OFF]
        missing = sorted({link_value(a.link) for a in arms if a.selectable and a.link not in off_links})
        if missing:
            raise LayerRefusal("R27", "legacy link(s) %s have tree arms but no trees-off (N2)" % missing)
        if Link.IDENTITY not in off_links:
            raise LayerRefusal("R16", "the legacy candidate list has no identity-link trees-off: the "
                                      "decline target")
        object.__setattr__(self, "arms", arms)

    def selectable(self) -> Tuple[ArmSpec, ...]:
        """The selectable arms, in the declared order (the tie order)."""
        return tuple(a for a in self.arms if a.selectable)

    def link_keys(self) -> Tuple[str, ...]:
        """The link keys, in first-appearance order."""
        out = []
        for a in self.arms:
            if link_value(a.link) not in out:
                out.append(link_value(a.link))
        return tuple(out)


def is_r22_link(link: Any) -> bool:
    """True when the key is one of R22's links (treeroute.derive.shapes.Link)."""
    return isinstance(link, Link)


def decision_candidates(links: Optional[Tuple[Link, ...]],
                        legacy: Optional[LegacyCandidates]) -> Tuple[ArmSpec, ...]:
    """The arms a nowcast decision surface must carry, in candidate order: candidate_arms(links)
    without its placebos (every selectable arm, then each link's trees-off), or a declared legacy
    list's arms. Exactly one of links and legacy is given."""
    if (links is None) == (legacy is None):
        raise LayerRefusal("R24", "pass either R22's link set or a declared LegacyCandidates list")
    if legacy is not None:
        if not isinstance(legacy, LegacyCandidates):
            raise LayerRefusal("R22", "a legacy candidate list must be a LegacyCandidates declaration, "
                               "got %s" % type(legacy).__name__)
        return legacy.arms
    return tuple(a for a in candidate_arms(links) if a.tool is not Tool.PLACEBO_CORRECTOR)


__all__ = ["R22_ORDER", "LayerRefusal", "Tool", "Weighting", "ArmSpec", "SELECTABLE_TOOLS",
           "link_value", "check_arm", "arm_name", "table_kind", "trees_off_of", "placebo_of",
           "candidate_arms", "selectable_order", "lead_arms", "LegacyCandidates", "is_r22_link",
           "decision_candidates"]
