# Setup and Local Development

## Requirements

- Python 3.12 or newer.
- Node.js 22.12+ and npm (required by the Electron runtime package).
- Playwright's local Chromium browser for PDF rendering.
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

```bash
cd frontend
npm run dev
```

## Build and Run Locally

Launch the desktop application from the repository root after installing dependencies:

```bash
npm run desktop --prefix frontend
```

This builds the React UI, applies database migrations, starts FastAPI as an Electron-managed child process on an available loopback port, and opens the desktop window. The backend shuts down when the app closes. Electron uses `.venv/bin/python` (`.venv/Scripts/python.exe` on Windows) when present, then `python3` or `python` on `PATH`; set `PHOTO_STUDIO_PYTHON` to choose another interpreter. Runtime data remains under `PHOTO_STUDIO_DATA_DIR` (default `data/`). No separate backend terminal is needed. `npm install` downloads Electron; normal operation is local and offline.

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

Backend tests use isolated in-memory SQLite databases. PDF rendering tests require the installed Playwright Chromium binary.

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

## Sample Documents

The `examples/` directory contains fictional Chromium-generated agreement, booking, and invoice PDFs. To recreate them, move the existing PDFs out of that directory, then run:

```bash
python -m scripts.generate_examples
```
