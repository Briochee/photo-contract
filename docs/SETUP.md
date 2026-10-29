# Setup and Local Development

## Requirements

- Python 3.12 or newer.
- Node.js 22.12+ and npm (required by the Electron runtime package).
- Playwright's local Chromium browser for PDF rendering and pypdf for fillable signature fields.
- macOS, Windows, or Linux. Calibri is used when installed locally; Carlito/Arial are fallbacks. Fonts are not downloaded.

## Install

From the repository root, create and activate a virtual environment:

```bash
python3 -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Install the application runtime and Chromium browser, then the frontend packages and Electron runtime:

```bash
python -m pip install -r requirements.txt
python -m playwright install chromium
cd frontend
npm install
cd ..
```

For tests and linting, also install `python -m pip install -r backend/dev-requirements.txt`. The Electron application does not install Streamlit or its legacy-only dependencies.

To use a separate local data directory, copy `.env.example` to `.env` and set `PHOTO_STUDIO_DATA_DIR` to an absolute or repository-relative path. The default is `data/`; SQLite is `data/studio.sqlite3` and PDFs are in `data/documents/`. Keep this directory private.

## Development

The preserved Streamlit fallback is optional. Install its isolated dependencies with `python -m pip install -r legacy/requirements.txt`, then run `streamlit run app.py`; `.streamlit/config.toml` binds it to `127.0.0.1`.

Apply database migrations and start both development servers with:

```bash
python scripts/dev.py
```

The frontend is at `http://127.0.0.1:5173`, FastAPI is at `http://127.0.0.1:8000`, and OpenAPI docs are at `http://127.0.0.1:8000/docs`. Alternatively, run backend and frontend separately:

```bash
python scripts/migrate.py
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

The repository keeps one Alembic baseline for the current schema. On first launch after this consolidation, databases stamped with the earlier `0001`–`0004` revisions are copied to `data/backups/` (or the configured data directory's `backups/` folder), then upgraded while preserving records. Unrecognized revisions stop startup without modifying the database.

```bash
cd frontend
npm run dev
```

## Build and Run Locally

Launch the desktop application from the repository root after installing dependencies:

```bash
npm run desktop --prefix frontend
```

This builds the React UI, opens the Contract Studio loading window immediately, then applies database migrations and starts FastAPI as an Electron-managed child process on an available loopback port. The loading screen stays visible until the workspace is ready; the backend shuts down when the app closes. In development, Electron uses `.venv/bin/python` (`.venv/Scripts/python.exe` on Windows) when present, then `python3` or `python` on `PATH`; set `PHOTO_STUDIO_PYTHON` to choose another interpreter. Runtime data remains under `PHOTO_STUDIO_DATA_DIR` (default `data/`). `npm install` downloads Electron; normal operation is local and offline.

## Build a Finder-Installable macOS App

Build on the Mac and CPU architecture where the app will run. The build bundles the Python backend in PyInstaller onedir mode, the installed Chromium headless runtime for PDF generation, frontend, templates, and legal source; the installed app does not need Python, Node.js, or a separate server. Keep the backend in onedir mode because onefile's semaphore bootstrap is blocked in the macOS launch environment.

Install build-time dependencies once from the repository root:

```bash
source .venv/bin/activate
python -m pip install -r requirements-packaging.txt
python -m playwright install chromium
npm install --prefix frontend
```

Build the app bundle:

```bash
npm run build:mac --prefix frontend
```

The result is `release/mac-arm64/Contract Studio.app` on Apple Silicon or `release/mac-x64/Contract Studio.app` on Intel. Drag the `.app` into `/Applications` and open it from Finder. The app keeps existing records in `~/Library/Application Support/Photography Document Studio/data/` for compatibility; set `PHOTO_STUDIO_DATA_DIR` before launching to choose another location. The app icon uses the local `frontend/assets/contract-studio-icon.png` artwork and is converted to `.icns` during the build.

If the configured project data directory contains `studio.sqlite3` when you build, the app imports a consistent SQLite backup and the existing local files on first launch. Startup reconciles legacy PDF paths to copies in the app's document library only when their SHA-256 hashes match. The source data stays untouched; leave it in place until the app has opened once.

This is an ad-hoc signed, local build for the Mac that produced it; it is not notarized for distribution to other Macs. If macOS blocks a locally built copy, approve it in System Settings → Privacy & Security. Public distribution requires a Developer ID signature and Apple notarization.

Build the static frontend and start the single-origin application:

```bash
npm run build --prefix frontend
python scripts/start.py
# Optional: open a browser automatically
python scripts/start.py --open
```

FastAPI serves the built UI at `http://127.0.0.1:8000`. Startup applies Alembic migrations; it does not install packages automatically.

## Tests and Static Checks

```bash
python -m pytest -q tests backend/tests
python -m ruff check backend scripts
npm test --prefix frontend
npm run lint --prefix frontend
npm run format:check --prefix frontend
npm run build --prefix frontend
```

Backend tests use isolated in-memory SQLite databases. PDF rendering tests require the installed Playwright Chromium binary. Master agreements and booking confirmations include AcroForm signature, date, and signer-detail fields; complete them in a PDF reader that supports AcroForms and digital-signature fields, such as Adobe Acrobat Reader. Save the signed copy separately and record acceptance evidence in the app. These fields do not independently verify signer identity or mark a record accepted. Invoices do not require signatures.

## Existing Streamlit Data, Backup, and Restore

Import old `data/BK-*.json`, `data/references.sqlite3`, and existing booking PDFs without deleting source files:

```bash
python -m scripts.import_legacy
```

Review the printed report for skipped records or issues before retiring the old app. The importer preserves references and leaves legacy files in place. Make a backup from Settings or by saving the downloaded archive. Restore only into a new or empty directory:

```bash
python scripts/restore_backup.py backup.zip /path/to/restored-data
```

Then set `PHOTO_STUDIO_DATA_DIR=/path/to/restored-data` in `.env` and restart. Backups contain personal and financial data; store them securely. The optional former Streamlit UI requires `legacy/requirements.txt` and `streamlit run app.py`.

Settings also provides **Clear all history and data**. After confirmation, it removes business records, profile/preferences, the generated-document library, imported legacy files in the configured data directory, and current application logs. It retains reference counters to prevent reused identifiers. Downloaded backups and original source files outside the configured data directory are not affected.

Master agreements move from draft to pending when their PDF is saved to the document library. The effective date remains empty until finalization; it is set to the date of the last signature. Finalize an agreement by uploading the signed PDF or recording that date with a reference (or the explicit `confirmed` override). Unsigned agreement PDFs show as pending signature. Uploaded signed PDFs are stored as separate immutable document versions.

## Sample Documents

The `examples/` directory contains fictional Chromium-generated agreement, booking, and invoice PDFs. To recreate them, move the existing PDFs out of that directory, then run:

```bash
python -m scripts.generate_examples
```
