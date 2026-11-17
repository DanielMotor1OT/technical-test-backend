from fastapi import APIRouter, HTTPException, Query, status

from app.data import RECIPES_INITIAL, paginate
from app.schemas import (
    ApiEnvelopeSchema,
    ApiErrorResponseSchema,
    PaginatedDataSchema,
    RecipeSchema,
)

router = APIRouter(
    prefix="/api/v1/core-spares/recipes",
    tags=["Core Spares - Recipes"],
)


@router.get(
    "/",
    response_model=ApiEnvelopeSchema[PaginatedDataSchema[RecipeSchema]],
    summary="List kit recipes",
)
def list_recipes(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=50, description="Items per page"),
):
    return {
        "code": 1,
        "message": "Recetas obtenidas correctamente",
        "result": paginate(RECIPES_INITIAL, page, per_page),
    }


@router.get(
    "/{recipe_id}/",
    response_model=ApiEnvelopeSchema[RecipeSchema],
    responses={404: {"model": ApiErrorResponseSchema}},
    summary="Get recipe by ID",
)
def get_recipe(recipe_id: int):
    recipe = next((r for r in RECIPES_INITIAL if r["recipe_id"] == recipe_id), None)
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "message": "Receta no encontrada",
                "details": {"recipe_id": [f"No existe una receta con recipe_id={recipe_id}"]},
            },
        )
    return {
        "code": 1,
        "message": "Receta obtenida correctamente",
        "result": recipe,
    }
