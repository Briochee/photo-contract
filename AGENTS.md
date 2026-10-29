Version: 23

# Repository Guidelines

## Product and Architecture

Contract Studio manages local clients, agreements, bookings, invoices, and PDFs. It uses React/Vite/TypeScript (`frontend/`), FastAPI/SQLAlchemy/SQLite (`backend/`), and Electron (`frontend/desktop/`). Electron shows a local loading window before starting FastAPI; Jinja templates render PDFs through local Playwright Chromium. `scripts/build_macos_app.py` packages the locally installed Electron runtime, backend, and headless browser into a Finder-installable macOS app and imports existing local data on first launch. Package the frozen Python backend in PyInstaller onedir mode; onefile startup fails in this launch environment because its semaphore bootstrap is blocked. Packaged startup may repair imported document paths only to SHA-256-matching copies inside the configured library; keep document deletion restricted to that library. Keep the Electron user-data directory named `Photography Document Studio` for compatibility with existing installations. Streamlit sources remain optional legacy/migration tools; their dependencies are isolated in `legacy/requirements.txt`.

## Project References

- Read [docs/SETUP.md](docs/SETUP.md) for supported tools, setup, startup, testing, data paths, migration, and backup commands.
- The authoritative legal source is [docs/reference/master_photography_services_agreement.md](docs/reference/master_photography_services_agreement.md); keep its substantive wording unchanged and exclude the booking specimen and internal checklist from agreement PDFs.
- Follow [docs/reference/resume_design_library.md](docs/reference/resume_design_library.md) for local-first font use, paper/charcoal colors, burgundy accents, square edges, and restrained hard shadows.
- Keep runtime records and PDFs under the configurable `PHOTO_STUDIO_DATA_DIR` (default `data/`). Never commit client data, secrets, or generated records.

## Development Conventions

Use four spaces and type annotations in Python (`snake_case`, Ruff configured in `backend/pyproject.toml`). Keep API contracts in Pydantic schemas, authoritative money math in `backend/app/services/pricing.py`, persistence in SQLAlchemy models/repositories, and document layout in Jinja templates. Store money as integer USD cents and quantities as validated decimal strings. Bookings remain editable while draft or pending; saving a booking confirmation moves it to pending, and recording written acceptance finalizes it. Finalized booking snapshots and issued invoices remain immutable unless a recorded amendment or revision is created.

Use strict TypeScript, functional React components, CSS Modules, TanStack Query for server state, and React Hook Form with Zod for forms. Keep API calls centralized in `frontend/src/services/api.ts`. `npm run desktop --prefix frontend` builds the UI, runs migrations, and launches Electron with its backend child. Do not add remote fonts, assets, telemetry, cloud services, or runtime network dependencies.

Keep one Alembic baseline matching the current SQLite schema. Route desktop and development startup through `backend.app.migrations.upgrade_database`; recognized pre-squash revisions are backed up and reconciled before the baseline runs. Never discard the local database to recover from a migration error.

Photographer business name and profile-level rates, payment terms, delivery method, and delivery deadline are optional. Keep blank values nullable across the API, database, and settings form; booking-level data remains authoritative once saved.

Bookings support any photography session or event. Keep event types free-form, with suggestions for personal, wedding, portrait, celebration, and corporate work. Place field help below controls and align labels so helper text does not shift form inputs.

Client detail pages may delete an agreement only when no booking references it. Keep generated PDF copies in the document library after deleting the agreement record.

Only unaccepted draft or pending bookings may be deleted. Delete their unpaid draft invoices with them and detach, but preserve, generated PDFs; retain finalized bookings and bookings with issued invoices or payment records. Keep reference sequences intact so deleted references are never reused.

Settings may clear all local business records, profile/preferences, generated PDFs, imported legacy files, and logs only after explicit confirmation. Keep reference sequences to prevent reusing identifiers and never remove backups or original source files outside the configured data directory.

The document library can delete a saved PDF and its library record while retaining the related client, booking, agreement, or invoice. Confirm permanent file removal. Draft invoices may be prepared and issued before acceptance evidence is recorded; issuing an invoice never marks contractual acceptance. Saved agreement and booking PDFs remain pending until written acceptance is recorded; previews remain drafts. Issued invoice snapshots are immutable and corrected through replacement revisions.

Electron PDF previews use Chromium's local PDF viewer. Keep plugin support enabled for the app and permit popup windows only for blob URLs created by the local backend origin. Master agreement and booking confirmation PDFs contain AcroForm text inputs for signer details, typed signatures, and dates, plus certificate-based signature fields. Invoices do not require signatures. The app records acceptance evidence separately and does not verify identity from a filled PDF.

Master agreements move from draft to pending when their PDF is saved, then finalized when a signed PDF is uploaded or written-acceptance evidence is recorded. Keep the effective date empty until finalization; the last-signature date is the effective date, and `confirmed` is an explicit evidence override. Preserve prior agreement text snapshots when the legal template version changes. Saved unsigned agreement PDFs should show as pending signature in the document library.

## Verification and Change Review

Run `pytest -q tests backend/tests`, `npm test --prefix frontend`, `npm run build --prefix frontend`, and `ruff check backend scripts` for relevant changes. Add focused tests for calculations, state transitions, API contracts, and legal-text preservation. PDF changes should be verified with the actual Playwright renderer when Chromium is available. Electron changes should be tested by launching the desktop app and confirming its backend health endpoint. Update `docs/SETUP.md` when setup or runtime steps change; update this file's version only when durable project instructions change.

Use short imperative commit summaries. Pull requests should state behavior and verification, link a related issue where available, and include screenshots for dashboard or PDF layout changes. Preserve unrelated worktree edits.
