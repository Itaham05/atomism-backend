# Known Limitations

This document lists what's built, what's simplified for the prototype stage, and what a production version would need. Written for whoever inherits or hosts this project next.

## Security

- **JWT tokens don't support revocation** — once issued, a token stays valid until it expires (8 hours), even if the user's access should be revoked immediately (e.g. an employee leaving). A production system would need a token blocklist or shorter-lived tokens with refresh tokens.
- **No password reset flow** — if a user forgets their password, an admin currently has no way to reset it except manually updating the database.
- **No account lockout** — there's no limit on failed login attempts, so the login endpoint has no protection against brute-force password guessing.
- **No rate limiting** — any endpoint, including the AI chatbot (which costs money per call via Groq), can be called as many times as someone wants. A production deployment should add rate limiting, especially on `/login` and `/chatbot/ask`.
- **No audit logging** — there's no record of who created, edited, or deleted what, or when. For a system multiple admins will use, this is worth adding.

## Data & Content Management

- **Admin CRUD covers every entity, but the UI only exposes it for Parts** — the backend has full create/update/delete for Model, Variant, Aggregate, Assembly, and Sub-Assembly too, but the React frontend currently only has forms/buttons for managing Parts. Extending the UI to the other levels is straightforward (same pattern already used for Parts) but not yet built.
- **No formal review/publish workflow** — the RFQ describes content going through a review step before publishing. The Approver role exists and can view content, but there's no "pending approval" state or publish action yet — everything created is immediately live.
- **Bulk import only covers Parts** — the `/art/{art_id}/parts/bulk` endpoint lets you import many parts at once, but there's no equivalent bulk tool for Models, Variants, or the rest of the hierarchy.
- **No hotspot-tagging UI** — Part hotspot coordinates (`hotspot_x`, `hotspot_y`) must currently be entered as numbers by hand. A real content-authoring tool would let someone click directly on the diagram image to place a hotspot visually.

## AI Features

- **Chatbot answers depend on a third-party API (Groq)** — if Groq's service is down, changes its free-tier terms, or the API key is invalid, the chatbot stops working entirely. There's a fallback sentence for when no part matches, but not for when the Groq call itself fails.
- **Semantic search only considers a Part's description** — it doesn't yet search Video transcripts, Service Doc content, or other fields, so it can only find things that are reflected in how a Part is described.
- **No usage cost monitoring** — Groq's free tier has usage limits; there's currently no tracking or alerting if the app is approaching them.

## Roles & Permissions

- **Only 3 of the RFQ's 6 personas are implemented**: Technician, Admin (covering OEM Admin/Content Manager), and Approver. Platform Super Admin (managing multiple OEM tenants) and End Customer (a restricted public-facing view) are not built.
- **The Approver role has no distinct UI** — it works correctly at the API level (can view, cannot edit) but the frontend doesn't show anything different for this role yet.
- **Tenant onboarding is manual** — there's no signup flow for a new OEM to join the platform; a new Tenant currently has to be created directly in the database.

## Infrastructure

- **Demo hosting is on free tiers** — the deployed version runs on Railway's free/trial tier and Vercel's free tier. Railway's free tier has usage limits and the trial credit used during development will eventually run out; a production deployment should move to a paid tier with a proper SLA.
- **No automated backups** — relies entirely on the database provider's (Neon) own default backup behavior, nothing custom configured.
- **No automated tests** — there is no test suite. All testing during development was manual, through the API docs interface and the live frontend.
- **No monitoring or error tracking** — if something breaks for a real user, there's currently no alerting system that would notify anyone; errors are only visible by checking hosting platform logs directly.

## What This Prototype Does Prove

Despite the above, this prototype demonstrates a working, tested implementation of:
- The full multi-tenant data hierarchy from the RFQ, including proper isolation between tenants
- Real authentication and role-based access control, enforced consistently
- A working semantic search + AI-generated-answer chatbot
- The core "click a hotspot, see the matching part, get its video/PDF" interaction from Section 5.3
- A genuinely deployed, publicly reachable full-stack application, not just a local demo

This is a solid foundation for a production build, not a finished product — the gaps above are the honest list of what separates the two.