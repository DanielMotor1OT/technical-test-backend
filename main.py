from typing import Dict, List

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.routers import kits, receptions, recipes, spare_items

app = FastAPI(
    title="ERP Nexus - Core Spares API (Technical Test)",
    description=(
        "Spare parts reception and recipe-based kit assembly API.\n\n"
        "**Project conventions:**\n"
        "- All contracts use `snake_case`.\n"
        "- Spare items are categorized by `item_type`: `KIT`, `COMPONENT`, `LOOSE`.\n"
        "- Success responses follow `{ code: 1, message, result }`.\n"
        "- Error responses follow `{ code: 0, message, details }`."
    ),
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


app.include_router(spare_items.router)
app.include_router(receptions.router)
app.include_router(recipes.router)
app.include_router(kits.router)
