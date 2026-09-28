"""
Loads a whole catalogue from a CSV file into the database.

Each row of the CSV is one part. The script creates the Model, Variant,
Aggregate, Assembly and Sub-Assembly above it if they do not exist yet,
so you can describe a full catalogue in a single spreadsheet.

Before you start:
  1. Point DATABASE_URL at your database.
  2. Create the company and its first admin:   python create_admin.py
  3. Fill in a copy of catalogue_template.csv (Excel and Google Sheets can save CSV).

Check the file without touching the database:

    python import_catalogue.py my_catalogue.csv --tenant "Acme Motors" --dry-run

Import it:

    python import_catalogue.py my_catalogue.csv --tenant "Acme Motors"

It is safe to run again. Anything that already exists is skipped, and nothing
is written at all if any row has a problem.

Columns
  Required: model, variant, aggregate, assembly, sub_assembly, part_number, description
  Optional: vin, engine_number      (filled in on the variant if it has none yet)
            art_image_url           (diagram image; every sub-assembly needs it on at least one row)
            hotspot_x, hotspot_y    (0 to 100, position of the part on the diagram; default 50)
            video_url, video_title, video_timestamp   (timestamp in whole seconds)
            service_doc_url
"""
import argparse
import csv
import json
import os
import sys

from sqlmodel import Session, SQLModel, create_engine, select

from models import (
    Aggregate, Art, Assembly, Model, Part, PartServiceDocLink, PartVideoLink,
    ServiceDoc, SubAssembly, Tenant, Variant, Video,
)

REQUIRED = ["model", "variant", "aggregate", "assembly", "sub_assembly", "part_number", "description"]
GROUP_COLUMNS = ["model", "variant", "aggregate", "assembly", "sub_assembly"]


def read_rows(path):
    """Reads the CSV. utf-8-sig means files saved by Excel (with a hidden marker at the start) work too."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        header = [(h or "").strip().lower() for h in (reader.fieldnames or [])]
        missing = [c for c in REQUIRED if c not in header]
        if missing:
            raise ValueError("The CSV is missing required column(s): " + ", ".join(missing))
        rows = []
        for raw in reader:
            line_number = reader.line_num  # the real line in the file, even after blank lines
            row = {}
            for key, value in raw.items():
                if key is None:  # extra cells beyond the header
                    continue
                row[key.strip().lower()] = (value or "").strip()
            if not any(row.values()):  # skip blank lines
                continue
            row["_line"] = line_number
            rows.append(row)
    return rows


def looks_like_url(value):
    return value.lower().startswith(("http://", "https://"))


def validate(rows):
    """Checks every row and returns a list of problems (empty list means the file is fine)."""
    errors = []
    if not rows:
        return ["The CSV has a header but no data rows."]

    images_by_group = {}
    for row in rows:
        line = row["_line"]
        for col in REQUIRED:
            if not row.get(col):
                errors.append(f"Line {line}: '{col}' is empty.")

        for col in ("hotspot_x", "hotspot_y"):
            value = row.get(col, "")
            if value:
                try:
                    number = float(value)
                except ValueError:
                    errors.append(f"Line {line}: '{col}' must be a number, got '{value}'.")
                    continue
                if not 0 <= number <= 100:
                    errors.append(f"Line {line}: '{col}' must be between 0 and 100, got {value}.")

        timestamp = row.get("video_timestamp", "")
        if timestamp and not (timestamp.isdigit()):
            errors.append(f"Line {line}: 'video_timestamp' must be whole seconds (for example 92), got '{timestamp}'.")
        if (timestamp or row.get("video_title")) and not row.get("video_url"):
            errors.append(f"Line {line}: 'video_title' or 'video_timestamp' given without a 'video_url'.")

        for col in ("art_image_url", "video_url", "service_doc_url"):
            value = row.get(col, "")
            if value and not looks_like_url(value):
                errors.append(f"Line {line}: '{col}' must start with http:// or https://, got '{value}'.")

        group = tuple(row.get(c, "") for c in GROUP_COLUMNS)
        images_by_group.setdefault(group, "")
        if row.get("art_image_url") and not images_by_group[group]:
            images_by_group[group] = row["art_image_url"]

    for group, image in images_by_group.items():
        if all(group) and not image:
            errors.append("Sub-assembly '" + " > ".join(group) + "' has no art_image_url on any of its rows.")
    return errors


def get_or_create(session, cls, filters, values, stats, label):
    obj = session.exec(select(cls).where(*filters)).first()
    if obj:
        return obj
    obj = cls(**values)
    session.add(obj)
    session.flush()  # assigns the id without saving permanently yet
    stats[label] += 1
    return obj


def run_import(session, tenant, rows, embed=None):
    """Creates everything from the rows. The caller commits, so any error leaves the database untouched."""
    stats = {k: 0 for k in [
        "models", "variants", "aggregates", "assemblies", "sub_assemblies", "arts",
        "parts_created", "parts_existing", "videos", "service_docs", "embeddings",
    ]}
    group_images = {}
    for row in rows:
        group = tuple(row[c] for c in GROUP_COLUMNS)
        if row.get("art_image_url") and group not in group_images:
            group_images[group] = row["art_image_url"]

    for row in rows:
        model = get_or_create(
            session, Model, [Model.name == row["model"], Model.tenant_id == tenant.id],
            {"name": row["model"], "tenant_id": tenant.id}, stats, "models")

        variant = get_or_create(
            session, Variant, [Variant.name == row["variant"], Variant.model_id == model.id],
            {"name": row["variant"], "model_id": model.id, "vin": row.get("vin") or None,
             "engine_number": row.get("engine_number") or None}, stats, "variants")
        if row.get("vin") and not variant.vin:
            variant.vin = row["vin"]
        if row.get("engine_number") and not variant.engine_number:
            variant.engine_number = row["engine_number"]

        aggregate = get_or_create(
            session, Aggregate, [Aggregate.name == row["aggregate"], Aggregate.variant_id == variant.id],
            {"name": row["aggregate"], "variant_id": variant.id}, stats, "aggregates")

        assembly = get_or_create(
            session, Assembly, [Assembly.name == row["assembly"], Assembly.aggregate_id == aggregate.id],
            {"name": row["assembly"], "aggregate_id": aggregate.id}, stats, "assemblies")

        sub_assembly = get_or_create(
            session, SubAssembly, [SubAssembly.name == row["sub_assembly"], SubAssembly.assembly_id == assembly.id],
            {"name": row["sub_assembly"], "assembly_id": assembly.id}, stats, "sub_assemblies")

        group = tuple(row[c] for c in GROUP_COLUMNS)
        art = get_or_create(
            session, Art, [Art.sub_assembly_id == sub_assembly.id],
            {"image_url": group_images[group], "sub_assembly_id": sub_assembly.id}, stats, "arts")

        part = session.exec(
            select(Part).where(Part.art_id == art.id, Part.part_number == row["part_number"])
        ).first()
        if part:
            stats["parts_existing"] += 1
        else:
            part = Part(
                part_number=row["part_number"],
                description=row["description"],
                art_id=art.id,
                hotspot_x=float(row["hotspot_x"]) if row.get("hotspot_x") else 50,
                hotspot_y=float(row["hotspot_y"]) if row.get("hotspot_y") else 50,
            )
            session.add(part)
            session.flush()
            stats["parts_created"] += 1

        if embed and not part.embedding:
            part.embedding = json.dumps(embed(part.description))
            stats["embeddings"] += 1

        if row.get("video_url"):
            video = get_or_create(
                session, Video, [Video.url == row["video_url"]],
                {"url": row["video_url"], "timestamp": row.get("video_timestamp") or "0",
                 "title": row.get("video_title") or None}, stats, "videos")
            if row.get("video_title") and not video.title:
                video.title = row["video_title"]
            link = session.exec(
                select(PartVideoLink).where(PartVideoLink.part_id == part.id, PartVideoLink.video_id == video.id)
            ).first()
            if not link:
                session.add(PartVideoLink(part_id=part.id, video_id=video.id,
                                          timestamp=row.get("video_timestamp") or None))

        if row.get("service_doc_url"):
            doc = get_or_create(
                session, ServiceDoc, [ServiceDoc.url == row["service_doc_url"]],
                {"url": row["service_doc_url"]}, stats, "service_docs")
            link = session.exec(
                select(PartServiceDocLink).where(
                    PartServiceDocLink.part_id == part.id, PartServiceDocLink.servicedoc_id == doc.id)
            ).first()
            if not link:
                session.add(PartServiceDocLink(part_id=part.id, servicedoc_id=doc.id))

        session.flush()
    return stats


def main():
    parser = argparse.ArgumentParser(description="Import a catalogue from a CSV file.")
    parser.add_argument("csv_file", help="Path to the CSV file")
    parser.add_argument("--tenant", required=True, help="Company name the catalogue belongs to (must already exist)")
    parser.add_argument("--dry-run", action="store_true", help="Only check the file; do not touch the database")
    parser.add_argument("--no-embeddings", action="store_true",
                        help="Skip the AI search index (fast, but Intelli-Search will not find these parts)")
    args = parser.parse_args()

    try:
        rows = read_rows(args.csv_file)
    except (OSError, ValueError) as e:
        sys.exit(f"Could not read the CSV: {e}")

    errors = validate(rows)
    if errors:
        print(f"Found {len(errors)} problem(s). Nothing was imported:")
        for message in errors:
            print("  - " + message)
        sys.exit(1)

    print(f"The CSV looks good: {len(rows)} part row(s).")
    if args.dry_run:
        print("Dry run only, so nothing was imported.")
        return

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        sys.exit("DATABASE_URL is not set. See README.md for setup instructions.")

    engine = create_engine(database_url)
    SQLModel.metadata.create_all(engine)

    embed = None
    if not args.no_embeddings:
        print("Loading the AI search model (the first run downloads it, this can take a minute)...")
        from sentence_transformers import SentenceTransformer
        embedder = SentenceTransformer("all-MiniLM-L6-v2")
        embed = lambda text: embedder.encode(text).tolist()

    with Session(engine) as session:
        tenant = session.exec(select(Tenant).where(Tenant.name == args.tenant)).first()
        if not tenant:
            sys.exit(f"Company '{args.tenant}' was not found. Create it first with: python create_admin.py")
        stats = run_import(session, tenant, rows, embed)
        session.commit()

    print("Import finished.")
    print(f"  Created:  {stats['models']} model(s), {stats['variants']} variant(s), {stats['aggregates']} aggregate(s), "
          f"{stats['assemblies']} assembly(ies), {stats['sub_assemblies']} sub-assembly(ies), {stats['arts']} diagram(s)")
    print(f"  Parts:    {stats['parts_created']} created, {stats['parts_existing']} already existed")
    print(f"  Content:  {stats['videos']} new video(s), {stats['service_docs']} new service document(s)")
    print(f"  Search:   {stats['embeddings']} part(s) added to the AI search index")


if __name__ == "__main__":
    main()