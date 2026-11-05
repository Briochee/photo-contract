# Contract Studio

Contract Studio is a local-first desktop workspace for photographers who manage client assignments and the paperwork around them. Use it for corporate coverage, weddings, headshots, portraits, celebrations, and other photography sessions. It keeps client details, agreements, bookings, invoices, payments, and supporting files together on your computer.

## What You Can Do

- Maintain client and photographer profiles, with reusable business defaults.
- Create master agreements from the bundled Markdown template or upload your own; each agreement keeps its text snapshot.
- Build bookings with event details, coverage, deliverables, fees, expenses, exceptions, and acceptance status.
- Prepare invoices from booking charges, configure tax, record payments, and retain immutable issued versions.
- Generate, preview, and download agreement, booking confirmation, and invoice PDFs. Upload signed copies and keep other reference documents, such as a W-9, in the local document library.
- Back up and restore the local database and document collection.

Draft and pending records can be prepared before signatures are collected. Recording acceptance or attaching a signed copy updates the applicable status; generating or issuing a document alone does not record client acceptance. Issued invoices and finalized agreement and booking snapshots are retained as historical records.

## Run the Desktop App

Follow [docs/SETUP.md](docs/SETUP.md) for supported runtimes, dependency installation, migration, and troubleshooting. After setup, launch the application with:

```bash
npm run desktop --prefix frontend
```

Electron opens the interface and starts the local FastAPI backend automatically. No separate server, account, cloud service, or internet connection is required during normal use.

## Development

Start the Vite frontend and FastAPI backend together with:

```bash
python scripts/dev.py
```

The development UI runs at `http://127.0.0.1:5173`, the API at `http://127.0.0.1:8000`, and OpenAPI documentation at `http://127.0.0.1:8000/docs`. Run tests and static checks as described in [docs/SETUP.md](docs/SETUP.md).

## Local Data and Documents

SQLite records, the active agreement template, logs, and generated or uploaded documents live under `PHOTO_STUDIO_DATA_DIR` (default: `data/`). The installed Mac app uses its Application Support directory by default so its data is separate from the app bundle. Keep local records, `.env`, and backups private; they may contain client contact, financial, or tax information.

To import data from the previous Streamlit application, run `python -m scripts.import_legacy` and review its report. It preserves the source files. Backup and restore steps are in [docs/SETUP.md](docs/SETUP.md).

## Architecture

The React, Vite, and TypeScript frontend communicates with a local FastAPI backend. SQLAlchemy and SQLite store the business records; Pydantic validates API data; Jinja2 templates and local Playwright Chromium render print-ready PDFs. Electron packages the frontend and backend into a macOS app. The original Streamlit code remains only as an optional migration and legacy tool.

## Repository Map

```text
frontend/             React application and Electron desktop shell
backend/app/          FastAPI API, models, services, and document templates
backend/alembic/      SQLite schema migrations
backend/tests/        Backend and document regression tests
scripts/              Startup, packaging, migration, and data utilities
examples/             Fictional PDFs produced by the document renderer
docs/SETUP.md         Installation, development, packaging, backup, and test guide
```
