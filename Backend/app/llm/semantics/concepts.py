"""Concepts: statements about what the system's own terms mean and how its figures relate.

TRACE (app/llm/trace) checks figures, derived results and rule values. The assistant's real mistakes were
mostly of another kind: a wrong *meaning* ("overdue units are part of the units on order", "reorder level and
reorder point are the same figure", "unserved demand is back-ordered"). Each such statement is a yes/no claim
about a named concept, and the truth of the concept is not written down by hand where it can be observed:

  probe     the system's own code is run on a small fixed example and the answer is read from what it does;
  declared  a fact the system's documentation states and the code cannot show (what a sales-order status
            means, that the supply data is simulated), kept next to the passage that states it.

A concept's `meaning` is shown to the extracting model, its value never is, for the reason the rule keys of
TRACE are listed without their values: an extractor that knew the answer could quietly correct a wrong
statement instead of reporting what the text says.
"""
from dataclasses import dataclass
from datetime import date, timedelta
from functools import lru_cache
from typing import Callable, Literal

from app.analytics import simulation, stock_risk
from app.core.clock import Clock
from app.models.entities import InventoryRecord, Product, PurchaseOrder, SalesOrder, Supplier
from app.models.enums import ProductStatus, PurchaseOrderStatus, RiskLevel, SalesStatus, SupplierStatus
from app.services.analytics_service import AnalyticsService

TODAY = date(2026, 10, 5)


class _Repo:
    """The one read the analytics need from a repository: list(), and get() by ID."""

    def __init__(self, items):
        self._items = list(items)

    def list(self):
        return list(self._items)

    def get(self, item_id):
        return next((item for item in self._items if item.id == item_id), None)


def _fixture(on_hand: int = 100) -> AnalyticsService:
    """One active product with steady sales, a supplier, and three purchase orders: 50 units on order and due in
    5 days, 30 units ordered and 3 days overdue, 20 units awaiting approval."""
    supplier = Supplier(id="S1", name="Fixture Supplier", contact_name="-", email="-", phone="-", country="-",
                        product_ids=["P1"], avg_delivery_days=7, delivery_reliability=90, status=SupplierStatus.ACTIVE)
    product = Product(id="P1", sku="FX-1", name="Fixture", category="Fixture", supplier_id="S1", price=10.0,
                      unit_cost=5.0, status=ProductStatus.ACTIVE)
    stock = InventoryRecord(id="I1", product_id="P1", warehouse="Main", current_stock=on_hand, safety_stock=10,
                            reorder_level=50, last_updated=TODAY)
    sales = [SalesOrder(id=f"SO-{day}", customer="C", product_id="P1", quantity=5, unit_price=10.0,
                        order_date=TODAY - timedelta(days=day), status=SalesStatus.COMPLETED) for day in range(1, 15)]

    def order(number, quantity, expected, status):
        return PurchaseOrder(id=f"PO-{number}", supplier_id="S1", product_id="P1", quantity=quantity, unit_price=5.0,
                             order_date=TODAY - timedelta(days=10), expected_delivery=expected, status=status,
                             created_by="fixture")

    orders = [order(1, 50, TODAY + timedelta(days=5), PurchaseOrderStatus.ORDERED),
              order(2, 30, TODAY - timedelta(days=3), PurchaseOrderStatus.ORDERED),
              order(3, 20, TODAY + timedelta(days=5), PurchaseOrderStatus.PENDING_APPROVAL)]
    return AnalyticsService(_Repo([product]), _Repo([stock]), _Repo(sales), _Repo(orders), _Repo([supplier]),
                            Clock(mode=TODAY.isoformat()))


def _risk(on_hand: int = 100):
    return _fixture(on_hand).get_stock_risk("P1")


# --- probes: each returns whether the stated relation holds in the system --------------------------------------


def _overdue_in_on_order() -> bool:
    risk = _risk()
    return risk.inbound_units >= 50 + 30  # on order would then include the 30 overdue units


def _awaiting_approval_on_order() -> bool:
    return _risk().inbound_units in (70, 100)  # 50 + the 20 units awaiting approval


def _level_equals_point() -> bool:
    risk = _risk()
    return risk.reorder_point == risk.reorder_level


def _on_order_prevents_critical() -> bool:
    return _risk(on_hand=0).risk_level != RiskLevel.CRITICAL  # nothing on hand, still selling, 50 units on order


def _unserved_demand_backordered() -> bool:
    projection = simulation.project(on_hand=0, daily_demand=10, arrivals={date(2026, 10, 8): 500}, safety_stock=0,
                                    today=TODAY, horizon_days=20)
    # Back-ordered demand would be served from the delivery, so no demand would stay unmet once 500 units arrive.
    return projection.unmet_demand_units == 0


def _order_multiple_from_supplier() -> bool:
    return any(name in Supplier.model_fields for name in ("moq", "min_order_quantity", "minimum_order_quantity", "pack_size"))


@dataclass(frozen=True)
class Concept:
    key: str
    meaning: str  # shown to the extracting model
    how: Literal["probe", "declared"]
    evidence: str  # what the truth rests on, shown with a verdict
    probe: Callable[[], bool] | None = None
    declared: bool | None = None

    @property
    def holds(self) -> bool:
        return _truth(self.key)


CONCEPTS: dict[str, Concept] = {c.key: c for c in (
    Concept("overdue_units_are_part_of_units_on_order",
            "overdue units (Ordered, past their expected date) are counted inside the units on order",
            "probe", "stock risk on a fixture: units on order exclude Ordered purchase orders past their date",
            _overdue_in_on_order),
    Concept("awaiting_approval_units_are_units_on_order",
            "units on purchase orders still Pending Approval or Approved count as units on order",
            "probe", "stock risk on a fixture: only Ordered, not delivered, not overdue purchase orders count",
            _awaiting_approval_on_order),
    Concept("reorder_level_equals_reorder_point",
            "the reorder level (a figure on the stock record) and the reorder point (demand x lead time + safety "
            "stock) are the same figure, or the two terms are used interchangeably",
            "probe", "stock risk on a fixture: the computed reorder point differs from the stock record's reorder level",
            _level_equals_point),
    Concept("stock_on_order_prevents_critical_risk",
            "units on order stop a product that has nothing on hand and is still selling from being Critical",
            "probe", "stock risk on a fixture: nothing on hand and still selling is Critical whatever is on order",
            _on_order_prevents_critical),
    Concept("unserved_demand_is_backordered",
            "demand that cannot be served from stock is back-ordered, delayed or served later from a delivery",
            "probe", "the what-if projection on a fixture: demand that cannot be served is lost, not carried forward",
            _unserved_demand_backordered),
    Concept("order_quantity_comes_from_supplier_minimum_or_pack_size",
            "the suggested order quantity is a multiple of the supplier's minimum order quantity or pack size",
            "probe", "the supplier record has no minimum order quantity or pack size; suggestions round up to a "
            "fixed multiple of 10", _order_multiple_from_supplier),
    Concept("processing_order_is_being_prepared",
            "a Processing sales order is approved and being prepared, picked or packed",
            "declared", "knowledge passage flow.sales-order: Processing means shipped and on its way to the customer",
            declared=False),
    Concept("supply_data_is_simulated",
            "the purchase orders, deliveries and stock levels are simulated (true) or real operational records (false)",
            "declared", "knowledge passage data.dataset: purchase orders, delivery dates and stock levels are "
            "simulated from the real sales", declared=True),
)}


@lru_cache(maxsize=None)
def _truth(key: str) -> bool:
    concept = CONCEPTS[key]
    return bool(concept.probe()) if concept.how == "probe" else bool(concept.declared)


def catalogue_text() -> str:
    """For the extracting model: every concept with its meaning, never its truth."""
    return "\n".join(f"- {c.key}: {c.meaning}" for c in CONCEPTS.values())
