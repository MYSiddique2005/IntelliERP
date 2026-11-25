"""Extraction of concept statements, and of rule values the first TRACE extractor tended to miss.

Rule extraction needs no model call. Every pattern asserts something about a concept in concepts.py (or a
company rule key in trace/policy.py) and is read with its negation: "not back-ordered" is the statement that
the concept does NOT hold, which is true. Whether a statement is true is decided in verify.py, not here.

Model extraction (extract_llm) records the same kind of claim from any wording, through one forced tool call.
"""
import re
from dataclasses import dataclass

from app.llm import claims as C
from app.llm.trace.schema import Assertion


@dataclass(frozen=True)
class ConceptClaim:
    key: str
    holds: bool  # what the text asserts
    quote: str
    origin: str = "rule"


_NEG = re.compile(r"\b(?:not|never|no longer|isn't|aren't|doesn't|don't|rather than|instead of|unlike|neither|nor|"
                  r"different|distinct|differ\w*|separate|exclud\w*|excl\.)\b", re.IGNORECASE)
_NUM = r"\d[\d,]*"
_ON_ORDER = r"(?:units on order|on[- ]order|on order|inbound|incoming|in transit|in the pipeline)"  # not "open orders": overdue orders ARE open orders

_OVERDUE_PARTS = (
    # "720 overdue inbound units out of 1,830 inbound units", "63 overdue units out of 73 total on order"
    re.compile(rf"{_NUM}\s+(?:overdue|late)\b[^.;]{{0,40}}?\bout of\s+(?:the\s+)?{_NUM}\s+(?:total\s+)?(?:units?\s+)?{_ON_ORDER}", re.I),
    # "73 units total, of which 63 units are overdue", "73 units on order ... of which 63 units are overdue"
    re.compile(rf"{_NUM}\s+(?:total\s+)?(?:inbound\s+|incoming\s+)?units?[^.;]{{0,25}}?\bof which\s+{_NUM}\s+(?:units?\s+)?(?:are|is)\s+(?:currently\s+|already\s+)?(?:overdue|late)", re.I),
    # "63 units of the on-order stock are currently overdue"
    re.compile(rf"{_NUM}\s+units?\s+of the\s+{_ON_ORDER}\s+(?:stock|units?|total|quantity)?\s*(?:are|is)\s+(?:currently\s+|already\s+)?(?:overdue|late)", re.I),
    # "overdue" as a part of the total on order: "of the 73 units on order, 63 are overdue"
    re.compile(rf"\bof the\s+{_NUM}\s+(?:total\s+)?(?:units?\s+)?{_ON_ORDER}[^.;]{{0,30}},\s*{_NUM}\s+(?:units?\s+)?(?:are|is)\s+(?:currently\s+)?(?:overdue|late)", re.I),
)
_LEVEL_POINT = re.compile(r"\bre-?order\s+level\b", re.I), re.compile(r"\bre-?order\s+point\b", re.I)
_SAME = re.compile(r"\b(?:interchangeabl\w*|synonym\w*|identical|refer(?:s)? to the same|(?:are|is) the same|the same (?:concept|thing|figure|value|number|as)|"
                   r"one and the same|equivalent|used (?:to mean|as) the same)\b", re.I)
_DIFFERENT = re.compile(r"\b(?:not the same|different|distinct|differ\w*|two (?:separate|different)|separate)\b", re.I)
_BACKORDER = re.compile(r"\b(?:unmet|unserved|unfulfilled|unsatisfied|lost|excess)\s+(?:demand|sales)\b[^.;]{0,90}?"
                        r"(?:back-?order(?:ed|s)?|delayed|deferred|served later|fulfilled later|carried (?:over|forward)|met later)", re.I)
_BACKORDER2 = re.compile(r"\b(?:lost,?\s+)?or\s+(?:back-?orders?|delayed)\b", re.I)
_PREVENT_CRITICAL = re.compile(rf"{_ON_ORDER}[^.;]{{0,80}}?\b(?:prevent\w*|avoid\w*|stop\w*|keep\w*|mitigat\w*|rul\w+ out)\b[^.;]{{0,50}}?\bcritical\b", re.I)
_PREVENT_CRITICAL2 = re.compile(r"\b(?:prevent\w*|avoid\w*|stop\w*)\s+(?:it\s+|the product\s+)?from\s+(?:reaching|becoming|being|going)\s+(?:a\s+)?critical\b", re.I)
_MOQ = re.compile(r"\b(?:multiple of|rounded to|based on|driven by)\s+(?:the\s+)?(?:supplier['’]s?\s+)?(?:minimum order quantity|MOQ|(?:standard\s+)?pack(?:\s+|-)?size|case size)", re.I)
_MOQ2 = re.compile(r"\bMOQ\b[^.;]{0,40}\b(?:or|and)\s+(?:standard\s+)?pack\s+size\b", re.I)
_SIMULATED = (
    re.compile(r"\b(?:operational|real|actual|live|genuine)\s+(?:records|data)\b[^.;]{0,80}?\brather than\s+(?:simulated|synthetic|fake)", re.I),
    re.compile(r"\b(?:purchase orders?|stock levels?|supply data|inventory data|deliver(?:y|ies)|supplier reliability)\b[^.;]{0,60}?\b(?:are|is)\s+(?:all\s+)?(?:real|actual|genuine|live)\b", re.I),
    re.compile(r"\b(?:not|isn't|aren't)\s+(?:simulated|synthetic|fake)\b", re.I),
)
_PROCESSING = re.compile(r"\bProcessing\b[^.;]{0,80}?\b(?:approved|prepar\w+|picked|picking|packed|packing|being processed)\b", re.I)

_DRAFTS = re.compile(r"\b(?:one|1|a single|single|only one|just one)\s+(?:draft\s+)?(?:purchase orders?|recommendations?|drafts?)\b[^.;]{0,70}?"
                     r"\b(?:per|in response to|for|from|in)\s+(?:one\s+|each\s+|a\s+|every\s+|the\s+)?(?:single\s+)?(?:chat\s+)?(?:message|turn|request|prompt)", re.I)
_RISING = re.compile(rf"(\d+(?:\.\d+)?)\s*(?:%|percent)\s+or\s+more", re.I)


def _negated_before(sentence: str, start: int) -> bool:
    return bool(_NEG.search(sentence[max(0, start - 28):start]))


def concept_claims(text: str) -> list[ConceptClaim]:
    found: list[ConceptClaim] = []

    def add(key: str, holds: bool, quote: str) -> None:
        found.append(ConceptClaim(key, holds, quote.strip()[:300]))

    for sentence in C.sentences(text):
        for pattern in _OVERDUE_PARTS:
            if (match := pattern.search(sentence)) and not _NEG.search(match.group(0)):
                add("overdue_units_are_part_of_units_on_order", True, match.group(0))
                break
        if _LEVEL_POINT[0].search(sentence) and _LEVEL_POINT[1].search(sentence):
            if _SAME.search(sentence) and not _DIFFERENT.search(sentence):
                add("reorder_level_equals_reorder_point", True, sentence)
            elif _DIFFERENT.search(sentence) and not _SAME.search(sentence):
                add("reorder_level_equals_reorder_point", False, sentence)
        for pattern in (_BACKORDER, _BACKORDER2):
            if match := pattern.search(sentence):
                if "demand" in sentence.lower() or "backorder" in match.group(0).lower().replace("-", ""):
                    add("unserved_demand_is_backordered", not _negated_before(sentence, match.start()) and not _NEG.search(match.group(0)), match.group(0))
                    break
        if re.search(r"\b(?:on order|inbound|incoming|deliver\w+|pipeline|open (?:purchase )?orders?)\b", sentence, re.I):
            zero_stock = re.search(r"\b(?:0|zero|no)\s+(?:units\s+)?(?:on hand|in stock|stock)|nothing on hand|out of stock|stock(?: on hand)? (?:is|of) (?:0|zero)", sentence, re.I)
            # With stock on hand a Critical rating is not in question, so "inbound units prevent Critical" is only a claim
            # about the concept when nothing is on hand (the case the rule is about) or the sentence says "from reaching Critical".
            match = _PREVENT_CRITICAL2.search(sentence) or (_PREVENT_CRITICAL.search(sentence) if zero_stock else None)
            if match:
                add("stock_on_order_prevents_critical_risk", not _negated_before(sentence, match.start()), match.group(0))
        for pattern in (_MOQ, _MOQ2):
            if match := pattern.search(sentence):
                add("order_quantity_comes_from_supplier_minimum_or_pack_size", not _negated_before(sentence, match.start()), match.group(0))
                break
        for pattern in _SIMULATED:
            if match := pattern.search(sentence):
                if re.search(r"\bnot\b", match.group(0), re.I) and "simulated" in match.group(0).lower():
                    add("supply_data_is_simulated", True, match.group(0))  # "not simulated" is written as a denial; see below
                    found[-1] = ConceptClaim("supply_data_is_simulated", False, match.group(0))
                else:
                    add("supply_data_is_simulated", False, match.group(0))
                break
        if match := _PROCESSING.search(sentence):
            add("processing_order_is_being_prepared", not _negated_before(sentence, match.start()), match.group(0))
    return found


def rule_value_assertions(text: str) -> list[Assertion]:
    """Statements of a company rule's value the first extractor often did not record (existing TRACE attributes)."""
    found: list[Assertion] = []
    for sentence in C.sentences(text):
        if (match := _DRAFTS.search(sentence)) and not _NEG.search(match.group(0)):
            value = "1"
            found.append(Assertion(quote=match.group(0)[:200], subject="max_drafts_per_message", attribute="policy_value",
                                   comparator="eq", value=value))
        if (match := _RISING.search(sentence)) and re.search(r"\b(?:demand|rising|surge|sharply|increase|growth|trend)\b", sentence, re.I):
            found.append(Assertion(quote=match.group(0), subject="rising_sharply_pct", attribute="policy_value",
                                   comparator="eq", value=match.group(1)))
    return found
