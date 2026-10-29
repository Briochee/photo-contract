"""HTML templates rendered to PDFs entirely locally with Playwright Chromium."""
from pathlib import Path
from datetime import date
from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.sync_api import sync_playwright
try:
    import markdown
except ImportError:
    import mistune
    class MarkdownAdapter:
        @staticmethod
        def markdown(source, extensions=None):
            return mistune.html(source)
    markdown = MarkdownAdapter()
from core import ROOT, dollars, money, totals, due_date

ENV = Environment(loader=FileSystemLoader(str(ROOT / 'templates')),
                  autoescape=select_autoescape(['html', 'xml']))
ENV.filters['dollars'] = dollars


def contract_html(record):
    original = (
        ROOT
        / 'backend'
        / 'app'
        / 'defaults'
        / 'master_photography_services_agreement.md'
    ).read_text(encoding='utf-8')
    # Preserve all clauses verbatim. Only the Master section belongs in this PDF.
    master = original.split('\n---\n', 1)[0]
    # Replace strictly identified source placeholders only; do not edit legal provisions.
    replacements = {
        '**Photographer:** [Legal name / business name]': f'**Photographer:** {record["photographer"]}',
        '**Address:** [Address]': f'**Address:** {record["photographer_address"]}',
        '**Email:** [Email]': f'**Email:** {record["photographer_email"]}',
        '**Client:** [Legal entity name]': f'**Client:** {record["client"]}',
        '**Authorized Representative:** [Name / title]': f'**Authorized Representative:** {record["client_contact"]}',
    }
    # Escape dynamic values BEFORE Markdown conversion.
    from html import escape
    for source, target in replacements.items():
        master = master.replace(source, escape(str(target)), 1)
    # Client's address/email are the second occurrences in the master preamble.
    master = master.replace('**Address:** [Address]', '**Address:** ' + escape(record['client_address']), 1)
    master = master.replace('**Email:** [Email]', '**Email:** ' + escape(record['client_email']), 1)
    html_body = markdown.markdown(master, extensions=['tables'])
    return ENV.get_template('contract.html').render(r=record, contract_body=html_body)


def context(record):
    vals = totals(record['booking_lines'], record['invoice_extras'], record['tax_amount'])
    return dict(r=record, t=vals, due_date=due_date(record['invoice_date'], record['net_days']))


def render_html(kind, record):
    if kind == 'contract':
        return contract_html(record)
    if kind not in ('booking', 'invoice'):
        raise ValueError(kind)
    return ENV.get_template(f'{kind}.html').render(**context(record))


def export_pdfs(record, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    exported = {}
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
        except Exception:
            import shutil
            system_chromium = shutil.which('chromium') or shutil.which('chromium-browser')
            if not system_chromium:
                raise
            browser = p.chromium.launch(headless=True, executable_path=system_chromium)
        try:
            for kind, label in [('contract', 'Master-Agreement'), ('booking', 'Booking-Confirmation'), ('invoice', 'Invoice')]:
                page = browser.new_page(viewport={'width': 1024, 'height': 768}, device_scale_factor=1)
                page.set_content(render_html(kind, record), wait_until='load')
                dest = output_dir / f'{record["booking_ref"]}_{label}.pdf'
                page.pdf(path=str(dest), format='Letter', print_background=True,
                         margin={'top':'0.62in','right':'0.65in','bottom':'0.62in','left':'0.65in'},
                         display_header_footer=True,
                         header_template='<span></span>',
                         footer_template='<div style="font-family:Calibri,Arial,sans-serif;font-size:8px;color:#72283a;width:100%;border-top:1px solid #d4d4cf;text-align:right;padding:6px 45px 0 0">Page <span class="pageNumber"></span> of <span class="totalPages"></span></div>')
                exported[kind] = dest
                page.close()
        finally:
            browser.close()
    return exported
