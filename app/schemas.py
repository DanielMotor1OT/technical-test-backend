from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class SpareItemType(str, Enum):
    KIT = "KIT"
    COMPONENT = "COMPONENT"
    LOOSE = "LOOSE"


class IssueSchema(BaseModel):
    type: str = Field(..., examples=["DAÑADO"])
    quantity: int = Field(..., examples=[2])
    observation: str = Field(..., examples=["Oxidados"])


class SpareItemSchema(BaseModel):
    item_id: int
    code: str
    description: str
    item_type: SpareItemType
    cost: float


class ReceptionItemSchema(BaseModel):
    item_id: int
    code: str
    description: str
    item_type: SpareItemType
    counted_quantity: int
    cost: float
    issues: List[IssueSchema]


class RecipePartSchema(BaseModel):
    item_id: int
    quantity: int


class RecipeSchema(BaseModel):
    recipe_id: int
    kit_item_id: int
    kit_code: str
    description: str
    parts: List[RecipePartSchema]


class AssembledKitSchema(BaseModel):
    assembly_id: str
    recipe_id: int
    kit_item_id: int
    kit_code: str
    description: str
    requested_quantity: int
    assembled_quantity: int
    unit_cost: float
    total_cost: float
    notice: Optional[str] = None


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


class MetaSchema(BaseModel):
    total: int
    page: int
    per_page: int
    total_pages: int


class PaginatedDataSchema(BaseModel, Generic[T]):
    data: List[T]
    meta: MetaSchema


class ApiEnvelopeSchema(BaseModel, Generic[T]):
    code: int = Field(1, examples=[1])
    message: str
    result: T


class ApiEnvelopeMessageSchema(BaseModel):
    code: int = Field(1, examples=[1])
    message: str
    result: Optional[Dict[str, Any]] = None


class ApiErrorResponseSchema(BaseModel):
    code: int = Field(0, examples=[0])
    message: str
    details: Dict[str, List[str]] = Field(default_factory=dict)
