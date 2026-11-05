# Setup and Local Development

## Requirements

- Python 3.12 or newer.
- Node.js 22.22.2+, 24.15.0+, or 26.0.0+ with npm (required by the frontend toolchain, including jsdom 30).
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

To use a separate local data directory, copy `.env.example` to `.env` and set `PHOTO_STUDIO_DATA_DIR` to an absolute or repository-relative path. The default is `data/`; SQLite is `data/studio.sqlite3` and generated PDFs plus uploaded PDF/JPG/PNG reference files are in `data/documents/`. Keep this directory private; reference files may contain tax identification or other sensitive information.

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

The repository keeps one Alembic baseline for the current schema and adds forward migrations for later data-model changes. Before any upgrade of an existing database, startup creates and integrity-checks a consistent SQLite backup in `data/backups/` (or the configured data directory's `backups/` folder). Databases stamped with the earlier `0001`–`0004` revisions are reconciled after backup while preserving records. Unrecognized revisions stop startup without modifying the database.

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

The result is `release/mac-arm64/Contract Studio.app` on Apple Silicon or `release/mac-x64/Contract Studio.app` on Intel. Drag the `.app` into `/Applications` and open it from Finder. The app keeps existing records in `~/Library/Application Support/Photography Document Studio/data/` for compatibility; set `PHOTO_STUDIO_DATA_DIR` before launching to choose another location. The app icon uses the local `frontend/assets/contract-studio-icon.png` artwork and is converted to `.icns` during the build. The app bundles `backend/app/defaults/master_photography_services_agreement.md` as its initial agreement.

If the configured project data directory contains `studio.sqlite3` when you build, the app imports a consistent SQLite backup and the existing local files on first launch. Startup reconciles legacy PDF paths to copies in the app's document library only when their SHA-256 hashes match. The source data stays untouched; leave it in place until the app has opened once.

This is an ad-hoc signed, local build for the Mac that produced it; it is not notarized for distribution to other Macs. If macOS blocks a locally built copy, approve it in System Settings → Privacy & Security. Public distribution requires a Developer ID signature and Apple notarization.

## Automated macOS Releases

The **macOS Release** GitHub Actions workflow runs when code is pushed to `main`. Create a GitHub Actions environment named `production` and add these five environment secrets there before a release: `CSC_LINK` (base64 Developer ID Application `.p12`), `CSC_KEY_PASSWORD` (the `.p12` password), `APPLE_API_KEY` (base64 App Store Connect `.p8`), `APPLE_API_KEY_ID`, and `APPLE_API_ISSUER`. The `.p12` must include its Developer ID Application private key. On macOS, encode and copy each file for its corresponding secret with `base64 < DeveloperID.p12 | tr -d '\n' | pbcopy` and `base64 < AuthKey_KEYID.p8 | tr -d '\n' | pbcopy`. Store the values under **Settings → Environments → production → Environment secrets**; do not commit them or put real values in `.env`. `PHOTO_STUDIO_NOTARIZE=1` is a build-mode flag, not a credential. The workflow reads the `production` environment secrets and fails before installing build dependencies if one is missing.

The `.p8` API key authenticates notarization; it does not sign the application. The `.p12` Developer ID Application certificate contains the signing identity and private key. `APPLE_TEAM_ID` is not needed for the API-key notarization flow: the App Store Connect key ID and issuer ID are used instead, while the Developer ID certificate's identity includes its team ID. If the `.p12` contains more than one signing identity, set the optional GitHub Actions environment variable `CSC_NAME` under **Settings → Environments → production → Environment variables** to the exact identity, such as `Developer ID Application: Photographer Name (ABCDE12345)`. You can inspect an imported certificate's name with `security find-identity -v -p codesigning`. With one identity, electron-builder selects it automatically.

electron-builder imports `CSC_LINK` into a temporary keychain in the GitHub runner's dedicated temp directory. The release workflow deletes any remaining temporary keychain on both success and failure. The runner is an ephemeral macOS VM and the workflow does not install the certificate in a personal Mac's login keychain.

Before a new release, bump `frontend/package.json` and its lockfile together, for example:

```bash
npm version patch --no-git-tag-version --prefix frontend
```

The workflow rejects a package version that is unchanged or older than the latest stable `vX.Y.Z` Git tag. A successful run publishes `Contract-Studio-macOS-arm64-vX.Y.Z.zip` and a `.sha256` checksum as downloadable assets on the matching GitHub Release. Local `npm run build:mac --prefix frontend` builds remain ad-hoc and do not require release credentials.

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

Backend tests use isolated in-memory SQLite databases. PDF rendering tests require the installed Playwright Chromium binary. Master agreements and booking confirmations include AcroForm text inputs for signer name, title, typed signature, and date, alongside certificate-based signature fields. Click the typed-signature field in a PDF reader that supports AcroForms to enter a name directly; use that reader's signing tool to draw or apply a certificate-based signature. Save the signed copy separately and record acceptance evidence in the app. These fields do not independently verify signer identity or mark a record accepted. Invoices do not require signatures.

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

The Documents page accepts standalone PDF, JPG, and PNG reference files up to 25 MB. Uploaded files receive generated storage names and are kept in the configured document library; their original names appear in the UI. From an agreement, booking, or invoice, you can also attach a related PDF, JPG, or PNG. Linked uploads remain accessible from Documents and do not change acceptance, issued status, or invoice amounts. Signed contract and booking PDFs can be uploaded again after finalization as new versions; the original acceptance evidence and snapshots remain unchanged. Files are not processed by an external service.

Settings provides a **Master agreement template** editor. Upload a `.md` or `.markdown` file (up to 1 MB), or edit the current Markdown text, then save to activate it immediately. No app rebuild or internet connection is required. New agreements snapshot the active version; existing agreements and PDFs retain their original text. Supported tokens include `{{photographer_name}}`, `{{client_legal_name}}`, `{{client_address}}`, and `{{client_email}}`; raw HTML is escaped and Markdown images are omitted in PDFs, so use Markdown text and tables for formatting. Restore the bundled template from Settings at any time. The active custom template is stored at `PHOTO_STUDIO_DATA_DIR/master_agreement_template.md` and included in local backups. **Clear all history and data** removes the custom template and reactivates the bundled version.

Settings also provides **Clear all history and data**. After confirmation, it removes business records, profile/preferences, the custom agreement template, the generated and uploaded document library, imported legacy files in the configured data directory, and current application logs. The bundled agreement becomes active again, while reference counters remain to prevent reused identifiers. Downloaded backups and original source files outside the configured data directory are not affected.

Master agreements move from draft to pending when their PDF is saved to the document library. The effective date remains empty until finalization; it is set to the date of the last signature. Finalize an agreement by uploading the signed PDF or recording that date with a reference (or the explicit `confirmed` override). Unsigned agreement PDFs show as pending signature. Uploaded signed PDFs are stored as separate immutable document versions.

Booking confirmations follow the same lifecycle: the booking remains a draft until its confirmation PDF is saved, then becomes pending until written acceptance is recorded or a signed confirmation PDF is uploaded. Either action finalizes the booking; uploaded signed PDFs are retained as immutable document versions. Draft invoices can be created and issued from any saved booking before acceptance; issuing an invoice does not finalize the booking.

Booking confirmation text supports standard Markdown in scope and priorities, special deliverables, exceptions, line-item descriptions, and notes on approved expenses. Common formatting includes bold, italics, headings, lists, quotes, links, and tables. Raw HTML is escaped and Markdown images are omitted so text cannot load external or local resources. Expense notes appear in the confirmation only for approved expenses.

## Sample Documents

The `examples/` directory contains fictional Chromium-generated agreement, booking, and invoice PDFs. To recreate them, move the existing PDFs out of that directory, then run:

```bash
python -m scripts.generate_examples
```
