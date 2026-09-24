from sqlmodel import SQLModel, Field
from typing import Optional

class Tenant(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str

class Model(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    tenant_id: Optional[int] = Field(default=None, foreign_key="tenant.id")

class Variant(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    vin: Optional[str] = None
    engine_number: Optional[str] = None
    model_id: Optional[int] = Field(default=None, foreign_key="model.id")

class Aggregate(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    variant_id: Optional[int] = Field(default=None, foreign_key="variant.id")

class Assembly(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    aggregate_id: Optional[int] = Field(default=None, foreign_key="aggregate.id")

class SubAssembly(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    assembly_id: Optional[int] = Field(default=None, foreign_key="assembly.id")

class Art(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    image_url: str
    sub_assembly_id: Optional[int] = Field(default=None, foreign_key="subassembly.id")

class Part(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    part_number: str
    description: str
    art_id: Optional[int] = Field(default=None, foreign_key="art.id")
    embedding: Optional[str] = None
    hotspot_x: Optional[float] = None
    hotspot_y: Optional[float] = None

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