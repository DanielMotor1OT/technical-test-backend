from decimal import Decimal
from uuid import uuid4
from fastapi import APIRouter, HTTPException, Query, status

from app.data import (
    RECEPTION_ITEMS_INITIAL,
    RECIPES_INITIAL,
    assembled_kits_db,
    get_available_map,
    paginate,
    round_money,
)
from app.schemas import (
    ApiEnvelopeSchema,
    ApiErrorResponseSchema,
    AssembledKitSchema,
    CreateKitRequestSchema,
    DeleteKitResultSchema,
    PaginatedDataSchema,
)

router = APIRouter(
    prefix="/api/v1/core-spares/receptions/current/kits",
    tags=["Core Spares - Kit Assemblies"],
)


@router.get(
    "/",
    response_model=ApiEnvelopeSchema[PaginatedDataSchema[AssembledKitSchema]],
    summary="List assembled kits in current reception",
)
def list_assembled_kits(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=50, description="Items per page"),
):
    return {
        "code": 1,
        "message": "Listado de kits armados obtenido correctamente",
        "result": paginate(assembled_kits_db, page, per_page),
    }


@router.get(
    "/{assembly_id}/",
    response_model=ApiEnvelopeSchema[AssembledKitSchema],
    responses={404: {"model": ApiErrorResponseSchema}},
    summary="Get assembled kit by ID",
)
def get_assembled_kit(assembly_id: str):
    kit = next(
        (k for k in assembled_kits_db if k["assembly_id"] == assembly_id),
        None,
    )
    if not kit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "message": f"No se encontró el armado con id '{assembly_id}'",
                "details": {"assembly_id": ["El registro no existe o ya fue anulado."]},
            },
        )
    return {
        "code": 1,
        "message": "Armado obtenido correctamente",
        "result": kit,
    }


@router.post(
    "/",
    response_model=ApiEnvelopeSchema[AssembledKitSchema],
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"model": ApiErrorResponseSchema},
        422: {"model": ApiErrorResponseSchema},
    },
    summary="Assemble kits from a recipe",
)
def create_assembled_kit(payload: CreateKitRequestSchema):
    recipe = next(
        (r for r in RECIPES_INITIAL if r["recipe_id"] == payload.recipe_id),
        None,
    )
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "message": "Receta no encontrada",
                "details": {
                    "recipe_id": [f"No existe una receta con recipe_id={payload.recipe_id}"]
                },
            },
        )

    available_map = get_available_map()
    items_by_id = {i["item_id"]: i for i in RECEPTION_ITEMS_INITIAL}

    max_possible = min(
        available_map.get(p["item_id"], 0) // p["quantity"]
        for p in recipe["parts"]
    )

    if max_possible == 0:
        missing = [
            f"{items_by_id[p['item_id']]['description']} (disponible: {available_map.get(p['item_id'], 0)}, requerido por kit: {p['quantity']})"
            for p in recipe["parts"]
            if available_map.get(p["item_id"], 0) < p["quantity"]
        ]
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": f"Stock insuficiente para armar al menos 1 {recipe['kit_code']}.",
                "details": {"stock": missing},
            },
        )

    assembled_quantity = min(payload.requested_quantity, max_possible)

    unit_cost = sum(
        Decimal(str(items_by_id[p["item_id"]]["cost"])) * p["quantity"]
        for p in recipe["parts"]
    )
    total_cost = unit_cost * assembled_quantity

    notice = None
    if assembled_quantity < payload.requested_quantity:
        notice = (
            f"Se solicitaron {payload.requested_quantity} kit(s), pero solo "
            f"alcanzaron piezas disponibles para armar {assembled_quantity}."
        )

    new_kit = {
        "assembly_id": str(uuid4())[:8],
        "recipe_id": recipe["recipe_id"],
        "kit_item_id": recipe["kit_item_id"],
        "kit_code": recipe["kit_code"],
        "description": recipe["description"],
        "requested_quantity": payload.requested_quantity,
        "assembled_quantity": assembled_quantity,
        "unit_cost": round_money(unit_cost),
        "total_cost": round_money(total_cost),
        "notice": notice,
    }
    assembled_kits_db.append(new_kit)

    return {
        "code": 1,
        "message": (
            notice
            if notice
            else f"Se armaron {assembled_quantity} kit(s) de {recipe['kit_code']} correctamente."
        ),
        "result": new_kit,
    }


@router.delete(
    "/{assembly_id}/",
    response_model=ApiEnvelopeSchema[DeleteKitResultSchema],
    responses={404: {"model": ApiErrorResponseSchema}},
    summary="Cancel an assembled kit and return its parts",
)
def delete_assembled_kit(assembly_id: str):
    index = next(
        (idx for idx, k in enumerate(assembled_kits_db) if k["assembly_id"] == assembly_id),
        None,
    )
    if index is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "message": f"No se encontró el armado con id '{assembly_id}'",
                "details": {"assembly_id": ["El registro no existe o ya fue anulado."]},
            },
        )

    assembled_kits_db.pop(index)
    return {
        "code": 1,
        "message": "Armado anulado y piezas devueltas correctamente.",
        "result": {"assembly_id": assembly_id},
    }
