Version: 7

# Repository Guidelines

## Product and Architecture

Photography Document Studio manages local clients, agreements, bookings, invoices, and PDFs. It uses React/Vite/TypeScript (`frontend/`), FastAPI/SQLAlchemy/SQLite (`backend/`), and Electron (`desktop/`). Electron manages FastAPI's lifecycle; Jinja templates render PDFs through local Playwright Chromium. Streamlit sources remain optional legacy/migration tools; their dependencies are isolated in `legacy/requirements.txt`.

## Project References

- Read [docs/SETUP.md](docs/SETUP.md) for supported tools, setup, startup, testing, data paths, migration, and backup commands.
- The authoritative legal source is [docs/reference/master_photography_services_agreement.md](docs/reference/master_photography_services_agreement.md); keep its substantive wording unchanged and exclude the booking specimen and internal checklist from agreement PDFs.
- Follow [docs/reference/resume_design_library.md](docs/reference/resume_design_library.md) for local-first font use, paper/charcoal colors, burgundy accents, square edges, and restrained hard shadows.
- Keep runtime records and PDFs under the configurable `PHOTO_STUDIO_DATA_DIR` (default `data/`). Never commit client data, secrets, or generated records.

## Development Conventions

Use four spaces and type annotations in Python (`snake_case`, Ruff configured in `backend/pyproject.toml`). Keep API contracts in Pydantic schemas, authoritative money math in `backend/app/services/pricing.py`, persistence in SQLAlchemy models/repositories, and document layout in Jinja templates. Store money as integer USD cents and quantities as validated decimal strings. Draft bookings may change; accepted booking snapshots and issued invoices must remain immutable unless a recorded amendment or revision is created.

Use strict TypeScript, functional React components, CSS Modules, TanStack Query for server state, and React Hook Form with Zod for forms. Keep API calls centralized in `frontend/src/services/api.ts`. `npm run desktop --prefix frontend` builds the UI, runs migrations, and launches Electron with its backend child. Do not add remote fonts, assets, telemetry, cloud services, or runtime network dependencies.

Photographer business name and profile-level rates, payment terms, delivery method, and delivery deadline are optional. Keep blank values nullable across the API, database, and settings form; booking-level data remains authoritative once saved.

## Verification and Change Review

Run `pytest -q tests backend/tests`, `npm test --prefix frontend`, `npm run build --prefix frontend`, and `ruff check backend scripts` for relevant changes. Add focused tests for calculations, state transitions, API contracts, and legal-text preservation. PDF changes should be verified with the actual Playwright renderer when Chromium is available. Electron changes should be tested by launching the desktop app and confirming its backend health endpoint. Update `docs/SETUP.md` when setup or runtime steps change; update this file's version only when durable project instructions change.

Use short imperative commit summaries. Pull requests should state behavior and verification, link a related issue where available, and include screenshots for dashboard or PDF layout changes. Preserve unrelated worktree edits.
