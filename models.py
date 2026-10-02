from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

# status values used across the catalogue hierarchy for the
# Draft -> Review -> Published workflow
STATUS_DRAFT = "draft"
STATUS_REVIEW = "review"
STATUS_PUBLISHED = "published"


class Tenant(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str


class Model(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    tenant_id: Optional[int] = Field(default=None, foreign_key="tenant.id")
    status: str = STATUS_PUBLISHED
    image_url: Optional[str] = None  # shown on the model-card tiles


class Variant(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    vin: Optional[str] = None
    engine_number: Optional[str] = None
    model_id: Optional[int] = Field(default=None, foreign_key="model.id")
    status: str = STATUS_PUBLISHED
    market: Optional[str] = None  # "Domestic" | "Export"


class Aggregate(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    variant_id: Optional[int] = Field(default=None, foreign_key="variant.id")
    status: str = STATUS_PUBLISHED


class Assembly(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    aggregate_id: Optional[int] = Field(default=None, foreign_key="aggregate.id")
    status: str = STATUS_PUBLISHED


class SubAssembly(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    assembly_id: Optional[int] = Field(default=None, foreign_key="assembly.id")
    status: str = STATUS_PUBLISHED


class Art(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    image_url: str
    sub_assembly_id: Optional[int] = Field(default=None, foreign_key="subassembly.id")
    status: str = STATUS_PUBLISHED


class Part(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    part_number: str
    description: str
    art_id: Optional[int] = Field(default=None, foreign_key="art.id")
    embedding: Optional[str] = None
    hotspot_x: Optional[float] = None
    hotspot_y: Optional[float] = None

    # existing lifecycle flags
    is_alternate: bool = False
    is_obsolete: bool = False
    superseded_by: Optional[str] = None

    # new: commercial fields (RFQ / EPC parity)
    qty: float = 1
    unit: str = "Nos"  # "Nos" | "AR" | "Kg" | "Ltr"
    rate: Optional[float] = None

    # new: additional lifecycle flags from the EPC feature sheet
    is_nss: bool = False  # No Stock Supplied
    is_nls: bool = False  # No Longer Sold

    # new: EDM effectivity window
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None

    # new: kits (a kit part has child parts pointing back to it)
    is_kit: bool = False
    parent_part_id: Optional[int] = Field(default=None, foreign_key="part.id")

    # new: draft -> review -> publish + simple versioning
    status: str = STATUS_PUBLISHED
    version: int = 1


class Video(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    url: str
    timestamp: str
    title: Optional[str] = None


class ServiceDoc(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    url: str


class PartVideoLink(SQLModel, table=True):
    part_id: Optional[int] = Field(default=None, foreign_key="part.id", primary_key=True)
    video_id: Optional[int] = Field(default=None, foreign_key="video.id", primary_key=True)
    timestamp: Optional[str] = None


class PartServiceDocLink(SQLModel, table=True):
    part_id: Optional[int] = Field(default=None, foreign_key="part.id", primary_key=True)
    servicedoc_id: Optional[int] = Field(default=None, foreign_key="servicedoc.id", primary_key=True)


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    role: str
    password: str
    tenant_id: Optional[int] = Field(default=None, foreign_key="tenant.id")


# ---------------- New tables (Phase 2) ----------------

class Bookmark(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    part_id: Optional[int] = Field(default=None, foreign_key="part.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CartItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    part_id: Optional[int] = Field(default=None, foreign_key="part.id")
    quantity: float = 1


class Order(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    tenant_id: Optional[int] = Field(default=None, foreign_key="tenant.id")
    status: str = "placed"  # placed | sent_to_dms | fulfilled | cancelled
    created_at: datetime = Field(default_factory=datetime.utcnow)


class OrderItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: Optional[int] = Field(default=None, foreign_key="order.id")
    part_id: Optional[int] = Field(default=None, foreign_key="part.id")
    quantity: float = 1
    rate_at_order: Optional[float] = None


class HitLog(SQLModel, table=True):
    """One row per meaningful lookup, used to build the 3 RFQ hit-log reports
    (by model, by system/aggregate, by part)."""
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: Optional[int] = Field(default=None, foreign_key="tenant.id")
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    model_id: Optional[int] = Field(default=None, foreign_key="model.id")
    aggregate_id: Optional[int] = Field(default=None, foreign_key="aggregate.id")
    part_id: Optional[int] = Field(default=None, foreign_key="part.id")
    query_type: str = ""  # "browse" | "search_description" | "search_part_number" | "vin" | "engine" | "module" | "chatbot"
    query_text: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AuditLog(SQLModel, table=True):
    """Who changed what, for the admin console audit trail."""
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: Optional[int] = Field(default=None, foreign_key="tenant.id")
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    action: str = ""  # "create" | "update" | "delete" | "publish" | "revert"
    entity_type: str = ""  # "model" | "variant" | ... | "part"
    entity_id: Optional[int] = None
    detail: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)