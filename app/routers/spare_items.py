from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.data import SPARE_ITEMS_CATALOG, paginate
from app.schemas import (
    ApiEnvelopeSchema,
    ApiErrorResponseSchema,
    PaginatedDataSchema,
    SpareItemSchema,
    SpareItemType,
)

router = APIRouter(
    prefix="/api/v1/core-spares/spare-items",
    tags=["Core Spares - Spare Items"],
)


@router.get(
    "/",
    response_model=ApiEnvelopeSchema[PaginatedDataSchema[SpareItemSchema]],
    summary="List spare items catalog",
)
def list_spare_items(
    item_type: Optional[SpareItemType] = Query(
        None, description="Filter by spare item type: KIT, COMPONENT, or LOOSE"
    ),
    search: Optional[str] = Query(
        None, description="Search by code or description"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=50, description="Items per page"),
):
    filtered = SPARE_ITEMS_CATALOG
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
        "message": "Catálogo de repuestos obtenido correctamente",
        "result": paginate(filtered, page, per_page),
    }


@router.get(
    "/{item_id}/",
    response_model=ApiEnvelopeSchema[SpareItemSchema],
    responses={404: {"model": ApiErrorResponseSchema}},
    summary="Get spare item by ID",
)
def get_spare_item(item_id: int):
    item = next((i for i in SPARE_ITEMS_CATALOG if i["item_id"] == item_id), None)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "message": "Repuesto no encontrado",
                "details": {"item_id": [f"No existe un repuesto con item_id={item_id}"]},
            },
        )
    return {
        "code": 1,
        "message": "Repuesto obtenido correctamente",
        "result": item,
    }
