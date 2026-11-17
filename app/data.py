from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List

from app.schemas import SpareItemType

SPARE_ITEMS_CATALOG: List[dict] = [
    {
        "item_id": 1,
        "code": "5010054265",
        "description": "Pata de apoyo",
        "item_type": SpareItemType.COMPONENT.value,
        "cost": 3.00,
    },
    {
        "item_id": 2,
        "code": "5091176586",
        "description": "Eje pata doble",
        "item_type": SpareItemType.COMPONENT.value,
        "cost": 1.00,
    },
    {
        "item_id": 3,
        "code": "5091377768",
        "description": "Resorte",
        "item_type": SpareItemType.COMPONENT.value,
        "cost": 0.50,
    },
    {
        "item_id": 4,
        "code": "0204050052F",
        "description": "Pastilla freno",
        "item_type": SpareItemType.LOOSE.value,
        "cost": 0.59,
    },
    {
        "item_id": 100,
        "code": "KIT-EPD",
        "description": "Kit eje pata doble",
        "item_type": SpareItemType.KIT.value,
        "cost": 5.00,
    },
    {
        "item_id": 101,
        "code": "KIT-PAT",
        "description": "Kit pata con resortes",
        "item_type": SpareItemType.KIT.value,
        "cost": 5.00,
    },
]

RECEPTION_ITEMS_INITIAL: List[dict] = [
    {
        "item_id": 1,
        "code": "5010054265",
        "description": "Pata de apoyo",
        "item_type": SpareItemType.COMPONENT.value,
        "counted_quantity": 6,
        "cost": 3.00,
        "issues": [],
    },
    {
        "item_id": 2,
        "code": "5091176586",
        "description": "Eje pata doble",
        "item_type": SpareItemType.COMPONENT.value,
        "counted_quantity": 6,
        "cost": 1.00,
        "issues": [],
    },
    {
        "item_id": 3,
        "code": "5091377768",
        "description": "Resorte",
        "item_type": SpareItemType.COMPONENT.value,
        "counted_quantity": 12,
        "cost": 0.50,
        "issues": [
            {"type": "DAÑADO", "quantity": 2, "observation": "Oxidados"}
        ],
    },
    {
        "item_id": 4,
        "code": "0204050052F",
        "description": "Pastilla freno",
        "item_type": SpareItemType.LOOSE.value,
        "counted_quantity": 395,
        "cost": 0.59,
        "issues": [],
    },
]

RECIPES_INITIAL: List[dict] = [
    {
        "recipe_id": 10,
        "kit_item_id": 100,
        "kit_code": "KIT-EPD",
        "description": "Kit eje pata doble",
        "parts": [
            {"item_id": 1, "quantity": 1},
            {"item_id": 2, "quantity": 1},
            {"item_id": 3, "quantity": 2},
        ],
    },
    {
        "recipe_id": 11,
        "kit_item_id": 101,
        "kit_code": "KIT-PAT",
        "description": "Kit pata con resortes",
        "parts": [
            {"item_id": 1, "quantity": 1},
            {"item_id": 3, "quantity": 4},
        ],
    },
]

assembled_kits_db: List[dict] = []


def round_money(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def paginate(items: List[dict], page: int, per_page: int) -> dict:
    total = len(items)
    total_pages = max(1, (total + per_page - 1) // per_page)
    start = (page - 1) * per_page
    end = start + per_page
    return {
        "data": items[start:end],
        "meta": {
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
        },
    }


def get_available_map() -> Dict[int, int]:
    """Calculates available quantity per item_id: counted - issues - used_in_kits."""
    recipes_by_id = {r["recipe_id"]: r for r in RECIPES_INITIAL}
    used_by_item: Dict[int, int] = {}

    for kit in assembled_kits_db:
        recipe = recipes_by_id.get(kit["recipe_id"])
        if not recipe:
            continue
        for part in recipe["parts"]:
            used_by_item[part["item_id"]] = (
                used_by_item.get(part["item_id"], 0)
                + part["quantity"] * kit["assembled_quantity"]
            )

    available: Dict[int, int] = {}
    for item in RECEPTION_ITEMS_INITIAL:
        issues_qty = sum(issue["quantity"] for issue in item["issues"])
        used_qty = used_by_item.get(item["item_id"], 0)
        available[item["item_id"]] = max(
            0, item["counted_quantity"] - issues_qty - used_qty
        )
    return available
