from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlmodel import SQLModel, Session, create_engine, select
from jose import jwt, JWTError
from datetime import datetime, timedelta
from passlib.context import CryptContext
from sentence_transformers import SentenceTransformer
from groq import Groq
import numpy as np
import json
import os
from models import (Tenant, Model, Variant, Aggregate, Assembly, SubAssembly, Art,
                     Part, Video, ServiceDoc, PartVideoLink, PartServiceDocLink, User)
from pydantic import BaseModel
from typing import List, Optional as OptionalType
class BulkPartInput(BaseModel):
    part_number: str
    description: str
    hotspot_x: OptionalType[float] = 50
    hotspot_y: OptionalType[float] = 50
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+psycopg2://neondb_owner:npg_dYFNtVK8Ur6h@ep-aged-rice-ayyy5kfu.c-5.us-east-2.aws.neon.tech/neondb?sslmode=require")
engine = create_engine(DATABASE_URL)
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://atomism-frontend.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET_KEY = os.environ.get("SECRET_KEY", "atomism-dev-secret-change-later")
ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SEED_DEMO_DATA = os.environ.get("SEED_DEMO_DATA", "true").lower() == "true"

groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

print("Loading embedding model, this happens once at startup...")
embedder = SentenceTransformer('all-MiniLM-L6-v2')
print("Embedding model loaded.")

@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)
    if not SEED_DEMO_DATA:
        return
    with Session(engine) as session:
        existing = session.exec(select(Tenant)).first()
        if not existing:
            tenant = Tenant(name="Royal Enfield")
            session.add(tenant)
            session.commit()
            session.refresh(tenant)

            model = Model(name="Classic 350", tenant_id=tenant.id)
            session.add(model)
            session.commit()
            session.refresh(model)

            variant = Variant(name="350cc Redditch Edition", vin="ME3ABCD12E1234567", engine_number="EN350REC2024001", model_id=model.id)
            session.add(variant)
            session.commit()
            session.refresh(variant)

            aggregate = Aggregate(name="Braking System", variant_id=variant.id)
            session.add(aggregate)
            session.commit()
            session.refresh(aggregate)

            assembly = Assembly(name="Front Brake Assembly", aggregate_id=aggregate.id)
            session.add(assembly)
            session.commit()
            session.refresh(assembly)

            subassembly = SubAssembly(name="Front Brake Caliper", assembly_id=assembly.id)
            session.add(subassembly)
            session.commit()
            session.refresh(subassembly)

            art = Art(image_url="https://example.com/brake-caliper-diagram.png", sub_assembly_id=subassembly.id)
            session.add(art)
            session.commit()
            session.refresh(art)

            part1 = Part(part_number="RE-BC-001", description="Front Brake Caliper Bolt", art_id=art.id, hotspot_x=30, hotspot_y=45)
            session.add(part1)
            session.commit()
            session.refresh(part1)

            part2 = Part(part_number="RE-BC-002", description="Front Brake Caliper Pin", art_id=art.id, hotspot_x=65, hotspot_y=60)
            session.add(part2)
            session.commit()
            session.refresh(part2)

            part1.embedding = json.dumps(embedder.encode(part1.description).tolist())
            part2.embedding = json.dumps(embedder.encode(part2.description).tolist())
            session.add(part1)
            session.add(part2)
            session.commit()

            video = Video(url="https://youtube.com/watch?v=example", timestamp="60", title="Front Brake Caliper Service")
            session.add(video)
            session.commit()
            session.refresh(video)

            servicedoc = ServiceDoc(url="https://example.com/brake-caliper-service.pdf")
            session.add(servicedoc)
            session.commit()
            session.refresh(servicedoc)

            session.add(PartVideoLink(part_id=part1.id, video_id=video.id, timestamp="45"))
            session.add(PartVideoLink(part_id=part2.id, video_id=video.id, timestamp="134"))
            session.add(PartServiceDocLink(part_id=part1.id, servicedoc_id=servicedoc.id))
            session.commit()

            technician = User(name="Raj Kumar", role="technician", password=pwd_context.hash("raj123"), tenant_id=tenant.id)
            session.add(technician)
            session.commit()

            admin = User(name="Priya Sharma", role="admin", password=pwd_context.hash("priya123"), tenant_id=tenant.id)
            session.add(admin)
            session.commit()

            approver = User(name="Vikram Rao", role="approver", password=pwd_context.hash("vikram123"), tenant_id=tenant.id)
            session.add(approver)
            session.commit()

def create_token(user: User):
    expire = datetime.utcnow() + timedelta(hours=8)
    data = {"sub": user.name, "role": user.role, "user_id": user.id, "tenant_id": user.tenant_id, "exp": expire}
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

def require_admin(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admins can do this")
    return current_user

def require_admin_or_approver(current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ("admin", "approver"):
        raise HTTPException(status_code=403, detail="Only admins or approvers can do this")
    return current_user

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    with Session(engine) as session:
        user = session.exec(select(User).where(User.name == form_data.username)).first()
        if not user or not pwd_context.verify(form_data.password, user.password):
            raise HTTPException(status_code=401, detail="Incorrect name or password")
        token = create_token(user)
        return {"access_token": token, "token_type": "bearer"}

@app.get("/me")
def read_current_user(current_user: dict = Depends(get_current_user)):
    return current_user

@app.get("/models")
def get_models(current_user: dict = Depends(get_current_user)):
    with Session(engine) as session:
        return session.exec(select(Model).where(Model.tenant_id == current_user["tenant_id"])).all()

@app.post("/models")
def create_model(name: str, admin: dict = Depends(require_admin)):
    with Session(engine) as session:
        if not name.strip():
            raise HTTPException(status_code=422, detail="name cannot be empty")
        new_model = Model(name=name, tenant_id=admin["tenant_id"])
        session.add(new_model)
        session.commit()
        session.refresh(new_model)
        return new_model

@app.put("/models/{model_id}")
def update_model(model_id: int, name: str, admin: dict = Depends(require_admin)):
    with Session(engine) as session:
        m = session.get(Model, model_id)
        if not m or m.tenant_id != admin["tenant_id"]:
            raise HTTPException(status_code=404, detail="Model not found")
        m.name = name
        session.add(m)
        session.commit()
        session.refresh(m)
        return m

@app.delete("/models/{model_id}")
def delete_model(model_id: int, admin: dict = Depends(require_admin)):
    with Session(engine) as session:
        m = session.get(Model, model_id)
        if not m or m.tenant_id != admin["tenant_id"]:
            raise HTTPException(status_code=404, detail="Model not found")
        variants = session.exec(select(Variant).where(Variant.model_id == model_id)).all()
        for v in variants:
            aggregates = session.exec(select(Aggregate).where(Aggregate.variant_id == v.id)).all()
            for agg in aggregates:
                assemblies = session.exec(select(Assembly).where(Assembly.aggregate_id == agg.id)).all()
                for asm in assemblies:
                    subs = session.exec(select(SubAssembly).where(SubAssembly.assembly_id == asm.id)).all()
                    for sub in subs:
                        arts = session.exec(select(Art).where(Art.sub_assembly_id == sub.id)).all()
                        for art in arts:
                            parts = session.exec(select(Part).where(Part.art_id == art.id)).all()
                            for part in parts:
                                video_links = session.exec(select(PartVideoLink).where(PartVideoLink.part_id == part.id)).all()
                                doc_links = session.exec(select(PartServiceDocLink).where(PartServiceDocLink.part_id == part.id)).all()
                                for link in video_links:
                                    session.delete(link)
                                for link in doc_links:
                                    session.delete(link)
                                session.flush()
                                session.delete(part)
                            session.flush()
                            session.delete(art)
                        session.flush()
                        session.delete(sub)
                    session.flush()
                    session.delete(asm)
                session.flush()
                session.delete(agg)
            session.flush()
            session.delete(v)
        session.flush()
        session.delete(m)
        session.commit()
        return {"deleted": True, "model_id": model_id}

@app.get("/models/{model_id}/variants")
def get_variants(model_id: int, current_user: dict = Depends(get_current_user)):
    with Session(engine) as session:
        model = session.get(Model, model_id)
        if not model or model.tenant_id != current_user["tenant_id"]:
            raise HTTPException(status_code=404, detail="Model not found")
        return session.exec(select(Variant).where(Variant.model_id == model_id)).all()

def get_owned_variant(variant_id: int, session: Session, current_user: dict):
    variant = session.get(Variant, variant_id)
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")
    model = session.get(Model, variant.model_id)
    if not model or model.tenant_id != current_user["tenant_id"]:
        raise HTTPException(status_code=404, detail="Variant not found")
    return variant

@app.post("/models/{model_id}/variants")
def create_variant(model_id: int, name: str, vin: str = None, admin: dict = Depends(require_admin)):
    with Session(engine) as session:
        model = session.get(Model, model_id)
        if not model or model.tenant_id != admin["tenant_id"]:
            raise HTTPException(status_code=404, detail="Model not found")
        if not name.strip():
            raise HTTPException(status_code=422, detail="name cannot be empty")
        new_variant = Variant(name=name, vin=vin, model_id=model_id)
        session.add(new_variant)
        session.commit()
        session.refresh(new_variant)
        return new_variant

@app.put("/variants/{variant_id}")
def update_variant(variant_id: int, name: str = None, vin: str = None, admin: dict = Depends(require_admin)):
    with Session(engine) as session:
        v = get_owned_variant(variant_id, session, admin)
        if name is not None:
            v.name = name
        if vin is not None:
            v.vin = vin
        session.add(v)
        session.commit()
        session.refresh(v)
        return v

@app.delete("/variants/{variant_id}")
def delete_variant(variant_id: int, admin: dict = Depends(require_admin)):
    with Session(engine) as session:
        v = get_owned_variant(variant_id, session, admin)
        aggregates = session.exec(select(Aggregate).where(Aggregate.variant_id == v.id)).all()
        for agg in aggregates:
            assemblies = session.exec(select(Assembly).where(Assembly.aggregate_id == agg.id)).all()
            for asm in assemblies:
                subs = session.exec(select(SubAssembly).where(SubAssembly.assembly_id == asm.id)).all()
                for sub in subs:
                    arts = session.exec(select(Art).where(Art.sub_assembly_id == sub.id)).all()
                    for art in arts:
                        parts = session.exec(select(Part).where(Part.art_id == art.id)).all()
                        for part in parts:
                            for link in session.exec(select(PartVideoLink).where(PartVideoLink.part_id == part.id)).all():
                                session.delete(link)
                            for link in session.exec(select(PartServiceDocLink).where(PartServiceDocLink.part_id == part.id)).all():
                                session.delete(link)
                            session.flush()
                            session.delete(part)
                        session.flush()
                        session.delete(art)
                    session.flush()
                    session.delete(sub)
                session.flush()
                session.delete(asm)
            session.flush()
            session.delete(agg)
        session.flush()
        session.delete(v)
        session.commit()
        return {"deleted": True, "variant_id": variant_id}

@app.get("/variants/by-vin/{vin}")
def get_variant_by_vin(vin: str, current_user: dict = Depends(get_current_user)):
    with Session(engine) as session:
        variant = session.exec(select(Variant).where(Variant.vin == vin)).first()
        if not variant:
            return None
        model = session.get(Model, variant.model_id)
        if not model or model.tenant_id != current_user["tenant_id"]:
            return None
        return variant
@app.get("/variants/by-engine/{engine_number}")
def get_variant_by_engine(engine_number: str, current_user: dict = Depends(get_current_user)):
    with Session(engine) as session:
        variant = session.exec(select(Variant).where(Variant.engine_number == engine_number)).first()
        if not variant:
            return None
        model = session.get(Model, variant.model_id)
        if not model or model.tenant_id != current_user["tenant_id"]:
            return None
        return variant

@app.get("/aggregates/search")
def search_aggregates(q: str, current_user: dict = Depends(get_current_user)):
    with Session(engine) as session:
        matches = session.exec(select(Aggregate).where(Aggregate.name.ilike(f"%{q}%"))).all()
        result = []
        for agg in matches:
            try:
                get_owned_aggregate(agg.id, session, current_user)
                result.append(agg)
            except HTTPException:
                continue
        return result

@app.get("/variants/{variant_id}/aggregates")
def get_aggregates(variant_id: int, current_user: dict = Depends(get_current_user)):
    with Session(engine) as session:
        get_owned_variant(variant_id, session, current_user)
        return session.exec(select(Aggregate).where(Aggregate.variant_id == variant_id)).all()

def get_owned_aggregate(aggregate_id: int, session: Session, current_user: dict):
    aggregate = session.get(Aggregate, aggregate_id)
    if not aggregate:
        raise HTTPException(status_code=404, detail="Aggregate not found")
        get_owned_variant(aggregate.variant_id, session, current_user)
    return aggregate

def get_part_tenant_id(part, session: Session):
    """Walk Part -> Art -> SubAssembly -> Assembly -> Aggregate -> Variant -> Model to find the owning tenant_id."""
    if not part or not part.art_id:
        return None
    art = session.get(Art, part.art_id)
    if not art or not art.sub_assembly_id:
        return None
    sub = session.get(SubAssembly, art.sub_assembly_id)
    if not sub or not sub.assembly_id:
        return None
    asm = session.get(Assembly, sub.assembly_id)
    if not asm or not asm.aggregate_id:
        return None
    agg = session.get(Aggregate, asm.aggregate_id)
    if not agg or not agg.variant_id:
        return None
    variant = session.get(Variant, agg.variant_id)
    if not variant or not variant.model_id:
        return None
    model = session.get(Model, variant.model_id)
    return model.tenant_id if model else None

@app.post("/variants/{variant_id}/aggregates")
def create_aggregate(variant_id: int, name: str, admin: dict = Depends(require_admin)):
    with Session(engine) as session:
        get_owned_variant(variant_id, session, admin)
        if not name.strip():
            raise HTTPException(status_code=422, detail="name cannot be empty")
        new_agg = Aggregate(name=name, variant_id=variant_id)
        session.add(new_agg)
        session.commit()
        session.refresh(new_agg)
        return new_agg

@app.put("/aggregates/{aggregate_id}")
def update_aggregate(aggregate_id: int, name: str, admin: dict = Depends(require_admin)):
    with Session(engine) as session:
        agg = get_owned_aggregate(aggregate_id, session, admin)
        agg.name = name
        session.add(agg)
        session.commit()
        session.refresh(agg)
        return agg

@app.delete("/aggregates/{aggregate_id}")
def delete_aggregate(aggregate_id: int, admin: dict = Depends(require_admin)):
    with Session(engine) as session:
        agg = get_owned_aggregate(aggregate_id, session, admin)
        assemblies = session.exec(select(Assembly).where(Assembly.aggregate_id == agg.id)).all()
        for asm in assemblies:
            subs = session.exec(select(SubAssembly).where(SubAssembly.assembly_id == asm.id)).all()
            for sub in subs:
                arts = session.exec(select(Art).where(Art.sub_assembly_id == sub.id)).all()
                for art in arts:
                    parts = session.exec(select(Part).where(Part.art_id == art.id)).all()
                    for part in parts:
                        for link in session.exec(select(PartVideoLink).where(PartVideoLink.part_id == part.id)).all():
                            session.delete(link)
                        for link in session.exec(select(PartServiceDocLink).where(PartServiceDocLink.part_id == part.id)).all():
                            session.delete(link)
                        session.flush()
                        session.delete(part)
                    session.flush()
                    session.delete(art)
                session.flush()
                session.delete(sub)
            session.flush()
            session.delete(asm)
        session.flush()
        session.delete(agg)
        session.commit()
        return {"deleted": True, "aggregate_id": aggregate_id}

@app.get("/aggregates/{aggregate_id}/assemblies")
def get_assemblies(aggregate_id: int, current_user: dict = Depends(get_current_user)):
    with Session(engine) as session:
        get_owned_aggregate(aggregate_id, session, current_user)
        return session.exec(select(Assembly).where(Assembly.aggregate_id == aggregate_id)).all()

def get_owned_assembly(assembly_id: int, session: Session, current_user: dict):
    assembly = session.get(Assembly, assembly_id)
    if not assembly:
        raise HTTPException(status_code=404, detail="Assembly not found")
    get_owned_aggregate(assembly.aggregate_id, session, current_user)
    return assembly

@app.post("/aggregates/{aggregate_id}/assemblies")
def create_assembly(aggregate_id: int, name: str, admin: dict = Depends(require_admin)):
    with Session(engine) as session:
        get_owned_aggregate(aggregate_id, session, admin)
        if not name.strip():
            raise HTTPException(status_code=422, detail="name cannot be empty")
        new_asm = Assembly(name=name, aggregate_id=aggregate_id)
        session.add(new_asm)
        session.commit()
        session.refresh(new_asm)
        return new_asm

@app.put("/assemblies/{assembly_id}")
def update_assembly(assembly_id: int, name: str, admin: dict = Depends(require_admin)):
    with Session(engine) as session:
        asm = get_owned_assembly(assembly_id, session, admin)
        asm.name = name
        session.add(asm)
        session.commit()
        session.refresh(asm)
        return asm

@app.delete("/assemblies/{assembly_id}")
def delete_assembly(assembly_id: int, admin: dict = Depends(require_admin)):
    with Session(engine) as session:
        asm = get_owned_assembly(assembly_id, session, admin)
        subs = session.exec(select(SubAssembly).where(SubAssembly.assembly_id == asm.id)).all()
        for sub in subs:
            arts = session.exec(select(Art).where(Art.sub_assembly_id == sub.id)).all()
            for art in arts:
                parts = session.exec(select(Part).where(Part.art_id == art.id)).all()
                for part in parts:
                    for link in session.exec(select(PartVideoLink).where(PartVideoLink.part_id == part.id)).all():
                        session.delete(link)
                    for link in session.exec(select(PartServiceDocLink).where(PartServiceDocLink.part_id == part.id)).all():
                        session.delete(link)
                    session.flush()
                    session.delete(part)
                session.flush()
                session.delete(art)
            session.flush()
            session.delete(sub)
        session.flush()
        session.delete(asm)
        session.commit()
        return {"deleted": True, "assembly_id": assembly_id}

@app.get("/assemblies/{assembly_id}/subassemblies")
def get_subassemblies(assembly_id: int, current_user: dict = Depends(get_current_user)):
    with Session(engine) as session:
        get_owned_assembly(assembly_id, session, current_user)
        return session.exec(select(SubAssembly).where(SubAssembly.assembly_id == assembly_id)).all()

def get_owned_subassembly(sub_assembly_id: int, session: Session, current_user: dict):
    subassembly = session.get(SubAssembly, sub_assembly_id)
    if not subassembly:
        raise HTTPException(status_code=404, detail="Sub-assembly not found")
    get_owned_assembly(subassembly.assembly_id, session, current_user)
    return subassembly

@app.post("/assemblies/{assembly_id}/subassemblies")
def create_subassembly(assembly_id: int, name: str, admin: dict = Depends(require_admin)):
    with Session(engine) as session:
        get_owned_assembly(assembly_id, session, admin)
        if not name.strip():
            raise HTTPException(status_code=422, detail="name cannot be empty")
        new_sub = SubAssembly(name=name, assembly_id=assembly_id)
        session.add(new_sub)
        session.commit()
        session.refresh(new_sub)
        return new_sub

@app.put("/subassemblies/{sub_assembly_id}")
def update_subassembly(sub_assembly_id: int, name: str, admin: dict = Depends(require_admin)):
    with Session(engine) as session:
        sub = get_owned_subassembly(sub_assembly_id, session, admin)
        sub.name = name
        session.add(sub)
        session.commit()
        session.refresh(sub)
        return sub

@app.delete("/subassemblies/{sub_assembly_id}")
def delete_subassembly(sub_assembly_id: int, admin: dict = Depends(require_admin)):
    with Session(engine) as session:
        sub = get_owned_subassembly(sub_assembly_id, session, admin)
        arts = session.exec(select(Art).where(Art.sub_assembly_id == sub.id)).all()
        for art in arts:
            parts = session.exec(select(Part).where(Part.art_id == art.id)).all()
            for part in parts:
                for link in session.exec(select(PartVideoLink).where(PartVideoLink.part_id == part.id)).all():
                    session.delete(link)
                for link in session.exec(select(PartServiceDocLink).where(PartServiceDocLink.part_id == part.id)).all():
                    session.delete(link)
                session.flush()
                session.delete(part)
            session.flush()
            session.delete(art)
        session.flush()
        session.delete(sub)
        session.commit()
        return {"deleted": True, "sub_assembly_id": sub_assembly_id}

@app.get("/subassemblies/{sub_assembly_id}/art")
def get_art(sub_assembly_id: int, current_user: dict = Depends(get_current_user)):
    with Session(engine) as session:
        get_owned_subassembly(sub_assembly_id, session, current_user)
        return session.exec(select(Art).where(Art.sub_assembly_id == sub_assembly_id)).first()

@app.get("/art/{art_id}/parts")
def get_parts(art_id: int, current_user: dict = Depends(get_current_user)):
    with Session(engine) as session:
        art = session.get(Art, art_id)
        if not art:
            raise HTTPException(status_code=404, detail="Art not found")
        get_owned_subassembly(art.sub_assembly_id, session, current_user)
        return session.exec(select(Part).where(Part.art_id == art_id)).all()

def part_belongs_to_tenant(part: Part, session: Session, tenant_id: int) -> bool:
    art = session.get(Art, part.art_id)
    if not art:
        return False
    subassembly = session.get(SubAssembly, art.sub_assembly_id)
    if not subassembly:
        return False
    assembly = session.get(Assembly, subassembly.assembly_id)
    if not assembly:
        return False
    aggregate = session.get(Aggregate, assembly.aggregate_id)
    if not aggregate:
        return False
    variant = session.get(Variant, aggregate.variant_id)
    if not variant:
        return False
    model = session.get(Model, variant.model_id)
    if not model:
        return False
    return model.tenant_id == tenant_id

@app.get("/parts/by-number/{part_number}")
def get_part_by_number(part_number: str, current_user: dict = Depends(get_current_user)):
    with Session(engine) as session:
        part = session.exec(select(Part).where(Part.part_number == part_number)).first()
        if not part or not part_belongs_to_tenant(part, session, current_user["tenant_id"]):
            return None
        return part

@app.get("/parts/search")
def search_parts(q: str, current_user: dict = Depends(get_current_user)):
    with Session(engine) as session:
        all_matches = session.exec(select(Part).where(Part.description.ilike(f"%{q}%"))).all()
        return [p for p in all_matches if part_belongs_to_tenant(p, session, current_user["tenant_id"])]

@app.get("/parts/{part_id}/videos")
def get_videos(part_id: int, current_user: dict = Depends(get_current_user)):
    with Session(engine) as session:
        part = session.get(Part, part_id)
        if not part or get_part_tenant_id(part, session) != current_user["tenant_id"]:
            raise HTTPException(status_code=404, detail="Part not found")
        links = session.exec(select(PartVideoLink).where(PartVideoLink.part_id == part_id)).all()
        videos = []
        for link in links:
            video = session.get(Video, link.video_id)
            if video:
                videos.append({
                    "id": video.id,
                    "url": video.url,
                    "title": video.title,
                    "timestamp": link.timestamp or video.timestamp,
                })
        if not videos:
            return {"available": False, "videos": []}
        return {"available": True, "videos": videos}

@app.get("/videos/{video_id}/parts")
def get_parts_for_video(video_id: int):
    with Session(engine) as session:
        links = session.exec(select(PartVideoLink).where(PartVideoLink.video_id == video_id)).all()
        part_ids = [link.part_id for link in links]
        return session.exec(select(Part).where(Part.id.in_(part_ids))).all()

@app.get("/parts/{part_id}/servicedocs")
def get_servicedocs(part_id: int, current_user: dict = Depends(get_current_user)):
    with Session(engine) as session:
        part = session.get(Part, part_id)
        if not part or get_part_tenant_id(part, session) != current_user["tenant_id"]:
            raise HTTPException(status_code=404, detail="Part not found")
        links = session.exec(select(PartServiceDocLink).where(PartServiceDocLink.part_id == part_id)).all()
        doc_ids = [link.servicedoc_id for link in links]
        docs = session.exec(select(ServiceDoc).where(ServiceDoc.id.in_(doc_ids))).all()
        if not docs:
            return {"available": False, "servicedocs": []}
        return {"available": True, "servicedocs": docs}

@app.get("/users")
def get_users(current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ("admin", "approver"):
        raise HTTPException(status_code=403, detail="Not authorized to view users")
    with Session(engine) as session:
        return session.exec(select(User)).all()

@app.post("/parts")
def create_part(part_number: str, description: str, art_id: int, hotspot_x: float = 50, hotspot_y: float = 50, admin: dict = Depends(require_admin)):
    with Session(engine) as session:
        if not part_number.strip() or not description.strip():
            raise HTTPException(status_code=422, detail="part_number and description cannot be empty")
        art = session.get(Art, art_id)
        if not art:
            raise HTTPException(status_code=404, detail="art_id does not exist")
        embedding = json.dumps(embedder.encode(description).tolist())
        new_part = Part(part_number=part_number, description=description, art_id=art_id, embedding=embedding, hotspot_x=hotspot_x, hotspot_y=hotspot_y)
        session.add(new_part)
        session.commit()
        session.refresh(new_part)
        return new_part

@app.put("/parts/{part_id}")
def update_part(part_id: int, part_number: str = None, description: str = None, admin: dict = Depends(require_admin)):
    with Session(engine) as session:
        part = session.get(Part, part_id)
        if not part:
            raise HTTPException(status_code=404, detail="Part not found")
        if part_number is not None:
            part.part_number = part_number
        if description is not None:
            part.description = description
            part.embedding = json.dumps(embedder.encode(description).tolist())
        session.add(part)
        session.commit()
        session.refresh(part)
        return part

@app.delete("/parts/{part_id}")
def delete_part(part_id: int, admin: dict = Depends(require_admin)):
    with Session(engine) as session:
        part = session.get(Part, part_id)
        if not part:
            raise HTTPException(status_code=404, detail="Part not found")
        for link in session.exec(select(PartVideoLink).where(PartVideoLink.part_id == part_id)).all():
            session.delete(link)
        for link in session.exec(select(PartServiceDocLink).where(PartServiceDocLink.part_id == part_id)).all():
            session.delete(link)
        session.flush()
        session.delete(part)
        session.commit()
        return {"deleted": True, "part_id": part_id}

@app.post("/art/{art_id}/parts/bulk")
def bulk_create_parts(art_id: int, parts: List[BulkPartInput], admin: dict = Depends(require_admin)):
    with Session(engine) as session:
        art = session.get(Art, art_id)
        if not art:
            raise HTTPException(status_code=404, detail="art_id does not exist")

        created = []
        errors = []
        for i, p in enumerate(parts):
            if not p.part_number.strip() or not p.description.strip():
                errors.append({"row": i, "error": "part_number and description cannot be empty"})
                continue
            embedding = json.dumps(embedder.encode(p.description).tolist())
            new_part = Part(
                part_number=p.part_number,
                description=p.description,
                art_id=art_id,
                embedding=embedding,
                hotspot_x=p.hotspot_x,
                hotspot_y=p.hotspot_y,
            )
            session.add(new_part)
            created.append(p.part_number)

        session.commit()
        return {
            "created_count": len(created),
            "created_part_numbers": created,
            "errors": errors,
        }

    
@app.get("/chatbot/ask")
def chatbot_ask(q: str, current_user: dict = Depends(get_current_user)):
    query_vec = embedder.encode(q)
    with Session(engine) as session:
        parts = session.exec(select(Part)).all()
        best_part = None
        best_score = -1
        for part in parts:
            if not part.embedding:
                continue
            if get_part_tenant_id(part, session) != current_user["tenant_id"]:
                continue
            part_vec = np.array(json.loads(part.embedding))
            score = np.dot(query_vec, part_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(part_vec))
            if score > best_score:
                best_score = score
                best_part = part
        if not best_part:
            return {"answer": "I couldn't find a matching part for that."}

        citation = None
        video_link = session.exec(select(PartVideoLink).where(PartVideoLink.part_id == best_part.id)).first()
        if video_link:
            video = session.get(Video, video_link.video_id)
            if video:
                citation = {
                    "type": "video",
                    "url": video.url,
                    "timestamp": video_link.timestamp or video.timestamp,
                    "label": video.title or "Training video",
                }
        if not citation:
            doc_link = session.exec(select(PartServiceDocLink).where(PartServiceDocLink.part_id == best_part.id)).first()
            if doc_link:
                doc = session.get(ServiceDoc, doc_link.servicedoc_id)
                if doc:
                    citation = {"type": "servicedoc", "url": doc.url, "label": "Service document"}

        citation_hint = ""
        if citation and citation["type"] == "video" and citation.get("timestamp"):
            citation_hint = f" Mention that timestamp {citation['timestamp']} in the video shows this exact step."

        completion = groq_client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": "You are a helpful assistant for vehicle technicians. Keep answers to one short, friendly sentence. Do not show your reasoning, only give the final answer."},
                {"role": "user", "content": f"A technician asked: '{q}'. The matching part is '{best_part.description}' (part number {best_part.part_number}).{citation_hint} Tell them which part this is and that the video and service document are available below."}
            ],
            max_tokens=200,
            reasoning_effort="low",
        )
        generated = completion.choices[0].message.content
        if not generated or not generated.strip():
            generated = f"This sounds like it could be the {best_part.description} ({best_part.part_number}) — check the video and service document below."

        return {
            "answer": generated,
            "best_match": {
                "part_number": best_part.part_number,
                "description": best_part.description,
                "id": best_part.id
            },
            "confidence": float(best_score),
            "citation": citation
        }