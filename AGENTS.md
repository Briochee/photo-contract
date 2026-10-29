Version: 15

# Repository Guidelines

## Product and Architecture

Contract Studio manages local clients, agreements, bookings, invoices, and PDFs. It uses React/Vite/TypeScript (`frontend/`), FastAPI/SQLAlchemy/SQLite (`backend/`), and Electron (`frontend/desktop/`). Electron shows a local loading window before starting FastAPI; Jinja templates render PDFs through local Playwright Chromium. `scripts/build_macos_app.py` packages the locally installed Electron runtime, backend, and headless browser into a Finder-installable macOS app and imports existing local data on first launch. Packaged startup may repair imported document paths only to SHA-256-matching copies inside the configured library; keep document deletion restricted to that library. Keep the Electron user-data directory named `Photography Document Studio` for compatibility with existing installations. Streamlit sources remain optional legacy/migration tools; their dependencies are isolated in `legacy/requirements.txt`.

## Project References

- Read [docs/SETUP.md](docs/SETUP.md) for supported tools, setup, startup, testing, data paths, migration, and backup commands.
- The authoritative legal source is [docs/reference/master_photography_services_agreement.md](docs/reference/master_photography_services_agreement.md); keep its substantive wording unchanged and exclude the booking specimen and internal checklist from agreement PDFs.
- Follow [docs/reference/resume_design_library.md](docs/reference/resume_design_library.md) for local-first font use, paper/charcoal colors, burgundy accents, square edges, and restrained hard shadows.
- Keep runtime records and PDFs under the configurable `PHOTO_STUDIO_DATA_DIR` (default `data/`). Never commit client data, secrets, or generated records.

## Development Conventions

Use four spaces and type annotations in Python (`snake_case`, Ruff configured in `backend/pyproject.toml`). Keep API contracts in Pydantic schemas, authoritative money math in `backend/app/services/pricing.py`, persistence in SQLAlchemy models/repositories, and document layout in Jinja templates. Store money as integer USD cents and quantities as validated decimal strings. Draft bookings may change; accepted booking snapshots and issued invoices must remain immutable unless a recorded amendment or revision is created.

Use strict TypeScript, functional React components, CSS Modules, TanStack Query for server state, and React Hook Form with Zod for forms. Keep API calls centralized in `frontend/src/services/api.ts`. `npm run desktop --prefix frontend` builds the UI, runs migrations, and launches Electron with its backend child. Do not add remote fonts, assets, telemetry, cloud services, or runtime network dependencies.

Photographer business name and profile-level rates, payment terms, delivery method, and delivery deadline are optional. Keep blank values nullable across the API, database, and settings form; booking-level data remains authoritative once saved.

Bookings support any photography session or event. Keep event types free-form, with suggestions for personal, wedding, portrait, celebration, and corporate work. Place field help below controls and align labels so helper text does not shift form inputs.

Client detail pages may delete an agreement only when no booking references it. Keep generated PDF copies in the document library after deleting the agreement record.

The document library can delete a saved PDF and its library record while retaining the related client, booking, agreement, or invoice. Confirm permanent file removal. Draft invoices may be prepared and issued before acceptance evidence is recorded; issuing an invoice never marks contractual acceptance. Agreement and booking PDFs remain drafts until written acceptance is recorded, while issued invoice snapshots are immutable and corrected through replacement revisions.

Electron PDF previews use Chromium's local PDF viewer. Keep plugin support enabled for the app and permit popup windows only for blob URLs created by the local backend origin. Master agreement and booking confirmation PDFs contain AcroForm signature/date fields added after Chromium rendering; invoices do not require signatures. The app records acceptance evidence separately and does not verify identity from a filled PDF.

The master agreement takes effect on the date of the last signature. Draft creation dates are internal only; expose the agreement date after written acceptance is recorded, and preserve prior agreement text snapshots when the legal template version changes.

## Verification and Change Review

Run `pytest -q tests backend/tests`, `npm test --prefix frontend`, `npm run build --prefix frontend`, and `ruff check backend scripts` for relevant changes. Add focused tests for calculations, state transitions, API contracts, and legal-text preservation. PDF changes should be verified with the actual Playwright renderer when Chromium is available. Electron changes should be tested by launching the desktop app and confirming its backend health endpoint. Update `docs/SETUP.md` when setup or runtime steps change; update this file's version only when durable project instructions change.

Use short imperative commit summaries. Pull requests should state behavior and verification, link a related issue where available, and include screenshots for dashboard or PDF layout changes. Preserve unrelated worktree edits.
