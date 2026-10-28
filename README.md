# Local Photography Document Studio

A self-contained, Python/Streamlit dashboard for generating a **Master Photography Services Agreement**, **Booking Confirmation**, and **Invoice**. PDFs are rendered from HTML/CSS using **Playwright Chromium**, not an external PDF service. The documents share a booking reference and invoice reference, and the pricing engine uses `Decimal` arithmetic.

## Quick start

Requires Python 3.10+ and a local Chromium installation for Playwright.

```bash
cd photography_documents_app
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium
streamlit run app.py
```

Open the local Streamlit URL printed in the terminal (usually `http://localhost:8501`). No remotely hosted backend is needed. Streamlit is a local browser UI served by a Python process running on your machine.

## Workflow

1. Click **New booking** to allocate a matching `BK-YYYY-NNN` / `INV-YYYY-NNN` pair from the local SQLite reference counter.
2. Enter photographer, client, assignment, coverage, and delivery details.
3. Edit the **Agreed booking fees** table. These appear identically in the booking confirmation and invoice; edits to an already accepted booking require a separate mutual written agreement.
4. Enter invoice-only extras, such as travel or overtime, **only after written approval**. The checkbox is required to generate documents. These items appear on the invoice, but not as unilateral amendments to the accepted booking confirmation.
5. Enter the manually verified tax amount and invoice payment instructions.
6. Save the record and generate PDFs. Download using the dashboard or locate files under `data/exports/BK-.../`.
7. Later, load the saved booking, update permitted details, and regenerate.

## Data & architecture

- `app.py` — Streamlit dashboard, editing, and export controls.
- `core.py` — Decimal math, approval validation, date logic, JSON persistence, and SQLite reference allocation.
- `render.py` — template loading and Playwright PDF output.
- `templates/` — Jinja HTML + print CSS (Letter format, page numbers).
- `assets/contract_source.md` — **verbatim copy** of the attached master agreement; its master agreement section is populated without rewriting clauses. The separate booking template is intentionally rendered from structured data.
- `assets/resume_design_library.md` — supplied visual reference, kept for future iteration.
- `data/` — local saved JSON and generated PDFs (contains client information; keep private and back up securely).
- `tests/` — pricing and validation tests (`pytest -q`).

## Visual and font decisions

Layout follows the design library's restrained paper/charcoal palette, burgundy photography accent, square controls, fine rules, compact metadata, and editorial spacing. Legal document legibility takes priority over portfolio ornamentation. **Calibri** is the first-choice font in both dashboard and PDFs, with Carlito/Arial fallbacks. Calibri is proprietary and **not included** in the repository: it must already be installed on the computer where Chromium renders PDFs. The PDF only uses it when the host has it installed.

## Legal cautions

The attached source is marked **draft for review — New York law**. It contains a separate booking specimen and an internal checklist, which are **not** inserted into the Master Agreement PDF. The app does not validate contract enforceability, client authorization, sales tax applicability, or city/state freelance-worker requirements. Invoice-only extras require you to confirm separate written advance approval. PDF signature lines are blank for physical or external electronic signing. PDFs are not cryptographically signed. A new booking reference is allocated on creating the draft even if never saved, so gaps in the numbering sequence are normal. Dates must use ISO `YYYY-MM-DD`.

## Privacy / offline notes

The app uses no cloud API, analytics, or network calls in document generation. The browser may serve local Streamlit pages; use your own firewall settings to restrict access. Google Fonts are **not required**; Calibri is selected locally. For fully offline installation, pre-install wheels and the Playwright Chromium browser before disconnecting.
