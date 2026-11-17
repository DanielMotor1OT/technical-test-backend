from typing import Optional
from fastapi import APIRouter, Query

from app.data import RECEPTION_ITEMS_INITIAL, assembled_kits_db, paginate
from app.schemas import (
    ApiEnvelopeMessageSchema,
    ApiEnvelopeSchema,
    PaginatedDataSchema,
    ReceptionItemSchema,
    SpareItemType,
)

router = APIRouter(
    prefix="/api/v1/core-spares/receptions/current",
    tags=["Core Spares - Receptions"],
)


@router.get(
    "/items/",
    response_model=ApiEnvelopeSchema[PaginatedDataSchema[ReceptionItemSchema]],
    summary="List counted items in current reception",
)
def list_reception_items(
    item_type: Optional[SpareItemType] = Query(
        None, description="Filter by item_type (COMPONENT or LOOSE)"
    ),
    search: Optional[str] = Query(
        None, description="Search by code or description"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=50, description="Items per page"),
):
    filtered = RECEPTION_ITEMS_INITIAL
    if item_type is not None:
        filtered = [i for i in filtered if i["item_type"] == item_type.value]
    if search:
        term = search.strip().lower()
        filtered = [
            i
            for i in filtered
            if term in i["code"].lower() or term in i["description"].lower()
        ]

    return {
        "code": 1,
        "message": "Ítems de la recepción obtenidos correctamente",
        "result": paginate(filtered, page, per_page),
    }


@router.post(
    "/reset/",
    response_model=ApiEnvelopeMessageSchema,
    summary="Reset current reception to initial state",
)
def reset_reception():
    assembled_kits_db.clear()
    return {
        "code": 1,
        "message": "Recepción reiniciada al estado inicial.",
        "result": None,
    }
