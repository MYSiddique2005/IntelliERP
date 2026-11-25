"""Concept checker: what the assistant says about the meaning of the system's terms.

The truth of a concept is read from the system's own code run on a fixture, so these tests also check that the
probes see what the system really does.
"""
from datetime import date

import pytest

from app.core.config import get_settings
from app.llm.semantics import SemanticVerifier
from app.llm.semantics.concepts import CONCEPTS, catalogue_text
from app.llm.semantics.extract import concept_claims, rule_value_assertions
from app.llm.semantics.extract_llm import RECORD_TOOL, extract, system_prompt
from tests.test_ai import call, llm, reply  # noqa: F401  (llm is a fixture)


def statuses(text):
    return [(v.subject, v.status) for v in SemanticVerifier().verdicts(text)]


def test_probes_read_what_the_system_does():
    holds = {key: concept.holds for key, concept in CONCEPTS.items()}
    assert holds == {
        "overdue_units_are_part_of_units_on_order": False,
        "awaiting_approval_units_are_units_on_order": False,
        "reorder_level_equals_reorder_point": False,
        "stock_on_order_prevents_critical_risk": False,
        "unserved_demand_is_backordered": False,
        "order_quantity_comes_from_supplier_minimum_or_pack_size": False,
        "processing_order_is_being_prepared": False,
        "supply_data_is_simulated": True,
    }


def test_a_probe_follows_the_code_it_probes(monkeypatch):
    """If the system did count overdue units as on order, the concept would hold: the truth is not hand-written."""
    from app.llm.semantics import concepts
    import app.services.analytics_service as service

    concepts._truth.cache_clear()
    original = service.AnalyticsService._stock_risk_items

    def counting_overdue_as_on_order(self, today, only_product_id=None):
        items = original(self, today, only_product_id)
        return [item.model_copy(update={"inbound_units": item.inbound_units + item.overdue_inbound_units}) for item in items]

    monkeypatch.setattr(service.AnalyticsService, "_stock_risk_items", counting_overdue_as_on_order)
    try:
        assert concepts._truth("overdue_units_are_part_of_units_on_order") is True
    finally:
        concepts._truth.cache_clear()


@pytest.mark.parametrize("text", [
    "63 overdue inbound units out of 73 inbound units.",
    "There are 73 units on order, of which 63 units are overdue.",
    "63 units of the on-order stock are currently overdue.",
    "Of the 1,830 units on order, 720 are overdue.",
])
def test_overdue_as_part_of_units_on_order_is_contradicted(text):
    assert statuses(text) == [("overdue_units_are_part_of_units_on_order", "contradicted")]


def test_the_figures_can_be_right_while_the_meaning_is_wrong():
    from app.llm.trace.schema import Assertion  # the numbers 63 and 73 may both be true; the relation is the error
    assert Assertion(quote="x", subject="P059", attribute="overdue_units", value="63").attribute == "overdue_units"
    assert statuses("63 overdue inbound units out of 73 on order.")[0][1] == "contradicted"


@pytest.mark.parametrize("text, expected", [
    ("Overdue orders are a subset of the open orders: 1 overdue open order out of 70 open orders.", []),
    ("Unmet demand is lost, not back-ordered.", [("unserved_demand_is_backordered", "supported")]),
    ("Unserved demand is lost or back-ordered in the projection.", [("unserved_demand_is_backordered", "contradicted")]),
    ("The reorder level and the reorder point are different figures.", [("reorder_level_equals_reorder_point", "supported")]),
    ("The reorder level and reorder point are used interchangeably.", [("reorder_level_equals_reorder_point", "contradicted")]),
    ("The units on order do not prevent it from being Critical.", [("stock_on_order_prevents_critical_risk", "supported")]),
    ("The 450 units on order prevent a product with 0 units on hand from being Critical.", [("stock_on_order_prevents_critical_risk", "contradicted")]),
    ("The supply data is simulated, not real.", []),
    ("Purchase orders and stock levels are real operational records rather than simulated data.", [("supply_data_is_simulated", "contradicted")]),
    ("A Processing order is approved and being picked and packed.", [("processing_order_is_being_prepared", "contradicted")]),
    ("The suggested quantity is a multiple of the supplier's minimum order quantity.", [("order_quantity_comes_from_supplier_minimum_or_pack_size", "contradicted")]),
])
def test_statements_are_read_with_their_negation(text, expected):
    assert statuses(text) == expected


def test_rule_values_missed_by_the_first_extractor_are_judged_by_the_frozen_verifier():
    class Source:
        separation_of_duties = True

        @staticmethod
        def today():
            return date(2026, 10, 5)

    verdicts = SemanticVerifier(source=Source()).verdicts(
        "The assistant can create one draft purchase order in response to one chat message. Demand counts as rising sharply at 20% or more.")
    assert {(v.subject, v.status) for v in verdicts} == {("max_drafts_per_message", "contradicted"), ("rising_sharply_pct", "contradicted")}
    assert [a.subject for a in rule_value_assertions("Demand is rising by 15% or more.")] == ["rising_sharply_pct"]


def test_the_extraction_prompt_gives_meanings_but_never_truths():
    prompt = system_prompt()
    assert all(key in prompt for key in CONCEPTS) and "simulated" in prompt
    assert "holds=false" in prompt
    for concept in CONCEPTS.values():
        assert concept.evidence not in prompt  # the evidence (and so the truth) stays out of the prompt
    assert catalogue_text().count("\n") == len(CONCEPTS) - 1


class _Conversation:
    def __init__(self, replies):
        self.replies = replies

    def reply(self):
        return self.replies


class _Provider:
    name, model = "scripted", "test-model"

    def __init__(self, tool_arguments):
        self.arguments, self.require_tool = tool_arguments, None

    def start(self, system, tools, history, message, require_tool=False):
        self.require_tool = require_tool
        assert [tool.name for tool in tools] == [RECORD_TOOL]
        return _Conversation(reply("", call(RECORD_TOOL, self.arguments)))


def test_model_extraction_records_claims_through_one_forced_tool_call():
    provider = _Provider({"claims": [
        {"quote": "late units sit inside what is on order", "concept": "overdue_units_are_part_of_units_on_order", "holds": True},
        {"quote": "x", "concept": "not_a_concept", "holds": True},
        {"quote": "", "concept": "supply_data_is_simulated", "holds": True},
    ]})
    result = extract(provider, "late units sit inside what is on order")
    assert provider.require_tool is True
    assert [(c.key, c.holds, c.origin) for c in result.claims] == [("overdue_units_are_part_of_units_on_order", True, "model")]
    assert result.invalid == 2
    verdicts = SemanticVerifier(provider=_Provider({"claims": [
        {"quote": "late units sit inside what is on order", "concept": "overdue_units_are_part_of_units_on_order", "holds": True}]})
    ).contradicted("late units sit inside what is on order")
    assert [v.subject for v in verdicts] == ["overdue_units_are_part_of_units_on_order"] and verdicts[0].source == "model"


def test_the_assistant_reports_a_wrong_meaning_when_the_check_is_on(client, auth, llm, monkeypatch):
    wrong = "Of the 73 units on order for this product, 63 units are overdue."
    monkeypatch.setattr(get_settings(), "llm_semantics", "rules")
    llm(reply(wrong), reply(wrong))
    body = client.post("/api/v1/ai/chat", json={"message": "What is on order for P001?"}, headers=auth("admin")).json()
    assert any("overdue_units_are_part_of_units_on_order" in claim for claim in body["contradicted_claims"])
    assert body["verification"]["semantics"]["mode"] == "rules"


def test_the_check_is_off_by_default(client, auth, llm):
    wrong = "Of the 73 units on order for this product, 63 units are overdue."
    llm(reply(wrong))
    body = client.post("/api/v1/ai/chat", json={"message": "What is on order for P001?"}, headers=auth("admin")).json()
    assert not any("overdue_units_are_part_of" in claim for claim in body["contradicted_claims"])
    assert "semantics" not in (body["verification"] or {})
