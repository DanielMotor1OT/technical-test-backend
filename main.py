from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

app = FastAPI(
    title="ERP Nexus - Core Spares API (Technical Test)",
    description=(
        "Spare parts reception and recipe-based kit assembly API.\n\n"
        "**Project conventions:**\n"
        "- All contracts use `snake_case`.\n"
        "- Success responses follow `{ code: 1, message, result }`.\n"
        "- Error responses follow `{ code: 0, message, details }`."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Schemas (OpenAPI / Swagger)
# ---------------------------------------------------------------------------


class IssueSchema(BaseModel):
    type: str = Field(..., examples=["DAÑADO"])
    quantity: int = Field(..., examples=[2])
    observation: str = Field(..., examples=["Oxidados"])


class CountedItemSchema(BaseModel):
    item_id: int
    code: str
    description: str
    counted_quantity: int
    cost: float
    issues: List[IssueSchema]


class RecipePartSchema(BaseModel):
    item_id: int
    quantity: int


class RecipeSchema(BaseModel):
    recipe_id: int
    kit_code: str
    description: str
    parts: List[RecipePartSchema]


class AssembledKitSchema(BaseModel):
    assembly_id: str
    recipe_id: int
    kit_code: str
    description: str
    requested_quantity: int
    assembled_quantity: int
    unit_cost: float
    total_cost: float
    notice: Optional[str] = None


class ReceptionResultSchema(BaseModel):
    items: List[CountedItemSchema]
    recipes: List[RecipeSchema]
    assembled_kits: List[AssembledKitSchema]


class MetaSchema(BaseModel):
    total: int
    page: int
    per_page: int
    total_pages: int


class PaginatedKitsResultSchema(BaseModel):
    data: List[AssembledKitSchema]
    meta: MetaSchema


class CreateKitRequestSchema(BaseModel):
    recipe_id: int = Field(..., description="ID of the recipe to assemble", examples=[10])
    requested_quantity: int = Field(
        ...,
        gt=0,
        description="Positive integer quantity of requested kits",
        examples=[6],
    )


class DeleteKitResultSchema(BaseModel):
    assembly_id: str


class ApiEnvelopeReceptionSchema(BaseModel):
    code: int = Field(1, examples=[1])
    message: str
    result: ReceptionResultSchema


class ApiEnvelopeKitSchema(BaseModel):
    code: int = Field(1, examples=[1])
    message: str
    result: AssembledKitSchema


class ApiEnvelopePaginatedKitsSchema(BaseModel):
    code: int = Field(1, examples=[1])
    message: str
    result: PaginatedKitsResultSchema


class ApiEnvelopeDeleteKitSchema(BaseModel):
    code: int = Field(1, examples=[1])
    message: str
    result: DeleteKitResultSchema


class ApiEnvelopeMessageSchema(BaseModel):
    code: int = Field(1, examples=[1])
    message: str
    result: Optional[Dict[str, Any]] = None


class ApiErrorResponseSchema(BaseModel):
    code: int = Field(0, examples=[0])
    message: str
    details: Dict[str, List[str]] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Global exception handlers (core-api style)
# ---------------------------------------------------------------------------


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(_request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict):
        message = str(exc.detail.get("message", "Error en la solicitud"))
        details = exc.detail.get("details", {})
    else:
        message = str(exc.detail)
        details = {}

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": 0,
            "message": message,
            "details": details,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, exc: RequestValidationError):
    details: Dict[str, List[str]] = {}
    for err in exc.errors():
        loc = [str(part) for part in err.get("loc", []) if part != "body"]
        field_name = ".".join(loc) if loc else "payload"
        details.setdefault(field_name, []).append(err.get("msg", "Valor inválido"))

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "code": 0,
            "message": "Error de validación en los datos enviados",
            "details": details,
        },
    )


# ---------------------------------------------------------------------------
# Initial in-memory data
# ---------------------------------------------------------------------------

INITIAL_ITEMS: List[dict] = [
    {
        "item_id": 1,
        "code": "5010054265",
        "description": "Pata de apoyo",
        "counted_quantity": 6,
        "cost": 3.00,
        "issues": [],
    },
    {
        "item_id": 2,
        "code": "5091176586",
        "description": "Eje pata doble",
        "counted_quantity": 6,
        "cost": 1.00,
        "issues": [],
    },
    {
        "item_id": 3,
        "code": "5091377768",
        "description": "Resorte",
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
        "counted_quantity": 395,
        "cost": 0.59,
        "issues": [],
    },
]

INITIAL_RECIPES: List[dict] = [
    {
        "recipe_id": 10,
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
        "kit_code": "KIT-PAT",
        "description": "Kit pata con resortes",
        "parts": [
            {"item_id": 1, "quantity": 1},
            {"item_id": 3, "quantity": 4},
        ],
    },
]

assembled_kits_db: List[dict] = []


# ---------------------------------------------------------------------------
# Calculation helpers
# ---------------------------------------------------------------------------


def round_money(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def get_available_map() -> Dict[int, int]:
    """Calculates available quantity per item_id: counted - issues - used_in_kits."""
    recipes_by_id = {r["recipe_id"]: r for r in INITIAL_RECIPES}
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
    for item in INITIAL_ITEMS:
        issues_qty = sum(issue["quantity"] for issue in item["issues"])
        used_qty = used_by_item.get(item["item_id"], 0)
        available[item["item_id"]] = max(
            0, item["counted_quantity"] - issues_qty - used_qty
        )
    return available


# ---------------------------------------------------------------------------
# Endpoints (core-spares style)
# ---------------------------------------------------------------------------


@app.get(
    "/api/v1/core-spares/receptions/current/",
    response_model=ApiEnvelopeReceptionSchema,
    summary="Get current reception",
    tags=["Core Spares - Receptions"],
)
def get_current_reception():
    return {
        "code": 1,
        "message": "Recepción obtenida correctamente",
        "result": {
            "items": INITIAL_ITEMS,
            "recipes": INITIAL_RECIPES,
            "assembled_kits": assembled_kits_db,
        },
    }


@app.get(
    "/api/v1/core-spares/receptions/kits/",
    response_model=ApiEnvelopePaginatedKitsSchema,
    summary="List assembled kits (paginated)",
    tags=["Core Spares - Kits"],
)
def list_assembled_kits(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=50, description="Items per page"),
):
    total = len(assembled_kits_db)
    total_pages = max(1, (total + per_page - 1) // per_page)
    start = (page - 1) * per_page
    end = start + per_page

    return {
        "code": 1,
        "message": "Listado de kits armados obtenido correctamente",
        "result": {
            "data": assembled_kits_db[start:end],
            "meta": {
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": total_pages,
            },
        },
    }


@app.post(
    "/api/v1/core-spares/receptions/kits/",
    response_model=ApiEnvelopeKitSchema,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"model": ApiErrorResponseSchema},
        422: {"model": ApiErrorResponseSchema},
    },
    summary="Assemble kits from a recipe",
    tags=["Core Spares - Kits"],
)
def create_assembled_kit(payload: CreateKitRequestSchema):
    recipe = next(
        (r for r in INITIAL_RECIPES if r["recipe_id"] == payload.recipe_id),
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
    items_by_id = {i["item_id"]: i for i in INITIAL_ITEMS}

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


@app.delete(
    "/api/v1/core-spares/receptions/kits/{assembly_id}/",
    response_model=ApiEnvelopeDeleteKitSchema,
    responses={404: {"model": ApiErrorResponseSchema}},
    summary="Cancel an assembled kit and return its parts",
    tags=["Core Spares - Kits"],
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


@app.post(
    "/api/v1/core-spares/receptions/reset/",
    response_model=ApiEnvelopeMessageSchema,
    summary="Reset reception to initial state",
    tags=["Core Spares - Receptions"],
)
def reset_reception():
    assembled_kits_db.clear()
    return {
        "code": 1,
        "message": "Recepción reiniciada al estado inicial.",
        "result": None,
    }
