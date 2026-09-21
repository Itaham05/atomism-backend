# Atomism Backend

A FastAPI backend for a multi-tenant parts, service, and training platform for vehicle OEMs. Built for the Parts/Service/Training Platform RFQ.

## Tech Stack

- **Language:** Python 3.11+
- **Framework:** FastAPI
- **Database:** PostgreSQL (via SQLModel/SQLAlchemy)
- **Auth:** JWT tokens with bcrypt password hashing
- **AI Search:** sentence-transformers (semantic search) + Groq API (natural-language answers)

## Features

- Full data hierarchy: Tenant (OEM) → Model → Variant → Aggregate → Assembly → Sub-Assembly → Art → Part → Video/Service Doc
- Multi-tenant data isolation, enforced at every level
- Five ways to find a part: browsing, VIN, part number, description search, and AI-powered natural-language search
- Role-based access: Technician (view only), Admin (full content management), Approver (view-only + user list)
- Full CRUD (create/update/delete) for every entity, with correct cascading deletes
- Bulk import endpoint for adding many Parts at once
- Interactive diagram hotspots linked to the parts list (BOM)
- "Never a dead link" behavior — video/PDF options only show when content actually exists

## Environment Variables

Create these before running. **None have safe defaults for production — set them explicitly.**

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes | PostgreSQL connection string, in the form `postgresql+psycopg2://user:password@host/dbname?sslmode=require` |
| `SECRET_KEY` | Yes | A random secret used to sign login tokens. Generate one with: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `GROQ_API_KEY` | Yes | Free API key from [console.groq.com](https://console.groq.com), used for the AI chatbot's generated answers |
| `SEED_DEMO_DATA` | No | `true` (default) seeds sample OEM/Model/Parts data on first run. Set to `false` once you're loading real data. |

## Running Locally

```bash
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux

pip install -r requirements.txt

# Set environment variables (see table above), then:
uvicorn main:app --reload
```

Visit `http://127.0.0.1:8000/docs` for interactive API documentation.

## Test Accounts (demo data)

| Username | Password | Role |
|---|---|---|
| Raj Kumar | raj123 | Technician |
| Priya Sharma | priya123 | Admin |
| Vikram Rao | vikram123 | Approver |

**Change or remove these before using real user data.**

## Deploying

This backend has been deployed and tested on [Railway](https://railway.app). Any host that supports Python/Uvicorn works. Key steps:
1. Push this repo to GitHub
2. Connect it to your hosting platform
3. Set all environment variables from the table above
4. Set the start command to: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Make sure the platform has at least 1GB of memory (the AI models need more than typical free-tier defaults)

## Using Your Own Database

1. Create a PostgreSQL database with any provider
2. Set `DATABASE_URL` to its connection string
3. Set `SEED_DEMO_DATA=false`
4. Start the app — it automatically creates all necessary tables on an empty database
5. Add your real data through the admin API endpoints, or the `/art/{art_id}/parts/bulk` endpoint for bulk-loading parts

## Known Limitations

See `LIMITATIONS.md` for a full list of what's built, what's simplified, and what a production version would need.