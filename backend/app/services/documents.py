"""Jinja2 and Playwright pipeline for local previews and versioned PDFs."""

import hashlib
import html
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Literal

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markdown_it import MarkdownIt
from markupsafe import Markup
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.config import DEFAULT_OUTPUT_DIR, TEMPLATE_VERSION, TEMPLATES_DIR
from backend.app.logging_config import activity
from backend.app.models import (
    Booking,
    GeneratedDocument,
    Invoice,
    MasterAgreement,
    PhotographerProfile,
)
from backend.app.services.domain import (
    booking_values,
    get_booking,
    get_invoice,
    invoice_values,
    item_values,
    profile_values,
    snapshot,
)
from backend.app.services.pdf_forms import add_pdf_form_fields

DocumentType = Literal["agreement", "booking_confirmation", "invoice"]
_REFERENCE = re.compile(r"^[A-Z]{2,4}-\d{4}-\d{3,}$")
_SIGNATURE_HEADING = re.compile(
    r"(?mi)^(?P<heading>#{1,6}[ \t]+(?:\d+(?:\.\d+)*[.)]?[ \t]+)?signatures?\b[^\n]*)$"
)
_SIGNER_MARKER = re.compile(r"(?mi)^\*\*(?:photographer|client):?\*\*[ \t]*$")
_AGREEMENT_TOKEN = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")
_PDF_MARGIN_POINTS = {
    "top": 0.85 * 72,
    "right": 0.78 * 72,
    "bottom": 0.8 * 72,
    "left": 0.78 * 72,
}
_JINJA = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(("html", "xml")),
    trim_blocks=True,
    lstrip_blocks=True,
)


def money(cents: int) -> str:
    """Format integer minor units without converting through floating point."""
    sign = "-" if cents < 0 else ""
    whole, fraction = divmod(abs(cents), 100)
    return f"{sign}${whole:,}.{fraction:02d}"


_JINJA.filters["money"] = money
_JINJA.globals["money"] = money


def document_context(
    session: Session, document_type: DocumentType, entity_id: int
) -> tuple[str, str, dict[str, Any], str]:
    """Build a template context from current draft data or immutable accepted snapshots."""
    if document_type == "agreement":
        agreement = session.get(MasterAgreement, entity_id)
        if agreement is None:
            raise LookupError("Agreement not found")
        source = json.loads(agreement.source_snapshot_json)
        source["effective_date"] = (
            agreement.effective_date.isoformat() if agreement.effective_date else ""
        )
        legal = agreement.legal_text_snapshot
        legal = _substitute_header_lines(legal, source)
        legal = _substitute_agreement_tokens(legal, source)
        legal_html = _agreement_html(legal, source)
        context = {
            "title": "Master Photography Services Agreement",
            "document_type": "agreement",
            "reference": agreement.agreement_ref,
            "photographer_name": _person_name(source["photographer"]),
            "client_name": source["client"]["legal_name"],
            "template_version": agreement.template_version,
            "status_label": (
                "Finalized agreement"
                if agreement.status in {"accepted", "finalized"}
                else "Pending signature"
                if agreement.status == "pending"
                else "Draft preview"
            ),
            "legal_html": Markup(legal_html),
        }
        return agreement.agreement_ref, source["client"]["legal_name"], context, agreement.status

    if document_type == "booking_confirmation":
        booking = get_booking(session, entity_id)
        if booking is None:
            raise LookupError("Booking not found")
        if booking.status in {"accepted", "finalized"} and booking.accepted_snapshot_json:
            source = json.loads(booking.accepted_snapshot_json)
            data = source["booking"]
            photographer = source["photographer"]
            data["additional_expenses"] = [item_values(row) for row in booking.additional_expenses]
        else:
            data = booking_values(booking)
            profile = session.scalar(
                select(PhotographerProfile).order_by(PhotographerProfile.id).limit(1)
            )
            photographer = profile_values(profile)
        if booking.agreement:
            data["agreement_date"] = (
                booking.agreement.effective_date.isoformat()
                if booking.agreement.status in {"accepted", "finalized"}
                and booking.agreement.effective_date is not None
                else None
            )
        approved = [
            item
            for item in data["additional_expenses"]
            if item["authorization_status"] == "approved"
        ]
        pricing_items = [
            *data["line_items"],
            *[{**item, "is_additional_expense": True} for item in approved],
        ]
        context = {
            **data,
            "title": "Booking Confirmation",
            "document_type": "booking",
            "reference": data["booking_ref"],
            "booking_ref": data["booking_ref"],
            "agreement_ref": booking.agreement.agreement_ref if booking.agreement else "",
            "photographer_name": _person_name(photographer),
            "photographer": photographer,
            "client_name": data["client"]["legal_name"],
            "client": data["client"],
            "status_label": (
                "Finalized terms"
                if booking.status in {"accepted", "finalized"}
                else "Pending acceptance"
                if booking.status == "pending"
                else "Draft preview"
            ),
            "pricing_items": pricing_items,
            "total_agreed_cents": sum(item["amount_cents"] for item in pricing_items),
            "invoice_reference": _current_invoice_reference(booking),
        }
        return data["booking_ref"], data["client"]["legal_name"], context, booking.status

    invoice = get_invoice(session, entity_id)
    if invoice is None:
        raise LookupError("Invoice not found")
    if invoice.status == "issued" and invoice.issued_snapshot_json:
        context = json.loads(invoice.issued_snapshot_json)
        status = "issued"
    else:
        booking = invoice.booking
        profile = session.scalar(
            select(PhotographerProfile).order_by(PhotographerProfile.id).limit(1)
        )
        values = invoice_values(invoice)
        context = {
            **values,
            "title": "Invoice",
            "document_type": "invoice",
            "reference": invoice.invoice_ref,
            "photographer_name": _person_name(profile_values(profile)),
            "photographer": profile_values(profile),
            "client_name": booking.client.legal_name,
            "client": {
                "legal_name": booking.client.legal_name,
                "mailing_address": booking.client.mailing_address,
                "primary_contact_name": booking.client.primary_contact_name,
                "contact_email": booking.client.contact_email,
            },
            "booking_ref": booking.booking_ref,
            "payment_terms_days": booking.payment_terms_days,
            "payment_instructions": profile.payment_instructions if profile else "",
            "status_label": values["status"].replace("_", " ").title(),
        }
        status = invoice.status
    return invoice.invoice_ref, context["client_name"], context, status


def render_pdf(document_type: DocumentType, context: dict[str, Any]) -> bytes:
    """Render a self-contained HTML template to a US Letter PDF using local Chromium."""
    template_name = {
        "agreement": "agreement.html",
        "booking_confirmation": "booking.html",
        "invoice": "invoice.html",
    }[document_type]
    html_document = _JINJA.get_template(template_name).render(**context)
    pdf_content = b""
    form_fields: list[dict[str, Any]] = []
    header = (
        '<div style="width:100%;font-size:8px;color:#66645d;padding:0 0.78in;display:flex;'
        'justify-content:space-between;border-bottom:1px solid #b7b6af;">'
        f"<span>{html.escape(str(context.get('photographer_name', 'Photography services')))}</span>"
        f"<span>{html.escape(str(context.get('reference', '')))}</span></div>"
    )
    footer = (
        '<div style="width:100%;font-size:8px;color:#66645d;display:flex;'
        "justify-content:space-between;"
        'padding:0 0.78in;border-top:1px solid #d1d0ca;">'
        f"<span>{html.escape(str(context.get('client_name', '')))}</span>"
        f"<span>{html.escape(str(context.get('reference', '')))} · "
        '<span class="pageNumber"></span> / '
        '<span class="totalPages"></span></span></div>'
    )
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            try:
                page = browser.new_page(
                    viewport={
                        "width": round(
                            8.5 * 96
                            - (_PDF_MARGIN_POINTS["left"] + _PDF_MARGIN_POINTS["right"]) * 96 / 72
                        ),
                        "height": round(
                            11 * 96
                            - (_PDF_MARGIN_POINTS["top"] + _PDF_MARGIN_POINTS["bottom"]) * 96 / 72
                        ),
                    }
                )
                page.set_content(html_document, wait_until="load")
                page.evaluate("document.fonts.ready")
                page.emulate_media(media="print")
                form_fields = page.locator("[data-pdf-field]").evaluate_all(
                    """elements => elements.map(element => {
                      const page = element.closest('[data-pdf-signature-page]');
                      if (!page) throw new Error('PDF input is outside its signature page');
                      const bounds = element.getBoundingClientRect();
                      const pageBounds = page.getBoundingClientRect();
                      return {
                        name: element.dataset.pdfField,
                        type: element.dataset.pdfFieldType,
                        label: element.dataset.pdfFieldLabel,
                        x: bounds.left - pageBounds.left,
                        y: bounds.top - pageBounds.top,
                        width: bounds.width,
                        height: bounds.height,
                      };
                    })"""
                )
                pdf_content = page.pdf(
                    format="Letter",
                    print_background=True,
                    prefer_css_page_size=True,
                    display_header_footer=True,
                    header_template=header,
                    footer_template=footer,
                    margin={
                        key: f"{value / 72:.2f}in" for key, value in _PDF_MARGIN_POINTS.items()
                    },
                )
            finally:
                browser.close()
        return add_pdf_form_fields(
            pdf_content,
            form_fields,
            left_margin_points=_PDF_MARGIN_POINTS["left"],
            top_margin_points=_PDF_MARGIN_POINTS["top"],
        )
    except PlaywrightError as exc:
        raise RuntimeError(
            "Chromium could not render the PDF. Check the local Playwright browser installation."
        ) from exc
    except (ValueError, TypeError, KeyError) as exc:
        raise RuntimeError("The PDF's fillable fields could not be prepared safely.") from exc


def _agreement_html(legal: str, snapshot_data: dict[str, Any]) -> str:
    """Render Markdown while keeping the final signature section on a fillable page."""
    markdown = MarkdownIt("commonmark", {"html": False, "typographer": False}).disable("image")
    headings = list(_SIGNATURE_HEADING.finditer(legal))
    if headings:
        heading = headings[-1]
        agreement_body = legal[: heading.start()]
        signature_section = legal[heading.start() :]
        section_markers = list(_SIGNER_MARKER.finditer(signature_section))
        if len(section_markers) >= 2:
            signature_prose = signature_section[: section_markers[0].start()]
        else:
            signature_prose = signature_section
        body_html = markdown.render(agreement_body)
        signature_intro = markdown.render(signature_prose)
    else:
        body_html = markdown.render(legal)
        signature_intro = markdown.render("## Signatures")

    photographer = snapshot_data.get("photographer", {})
    client = snapshot_data.get("client", {})
    signature_fields = _JINJA.get_template("agreement_signatures.html").render(
        photographer_legal_name=_plain_text(photographer.get("legal_name"))
        or _person_name(photographer),
        client_legal_name=_plain_text(client.get("legal_name")),
    )
    return (
        body_html
        + '<section class="signature-page" data-pdf-signature-page>'
        + signature_intro
        + signature_fields
        + "</section>"
    )


def _substitute_agreement_tokens(source: str, snapshot_data: dict[str, Any]) -> str:
    """Replace only documented scalar tokens, escaping values before Markdown parsing."""
    photographer = snapshot_data.get("photographer", {})
    client = snapshot_data.get("client", {})
    values = {
        "photographer_name": _person_name(photographer),
        "photographer_legal_name": _plain_text(photographer.get("legal_name")),
        "photographer_business_name": _plain_text(photographer.get("business_name")),
        "photographer_address": _plain_text(photographer.get("mailing_address")),
        "photographer_email": _plain_text(photographer.get("email")),
        "photographer_phone": _plain_text(photographer.get("phone")),
        "client_legal_name": _plain_text(client.get("legal_name")),
        "client_display_name": _plain_text(client.get("display_name")),
        "client_address": _plain_text(client.get("mailing_address")),
        "client_contact_name": _plain_text(client.get("primary_contact_name")),
        "client_contact_title": _plain_text(client.get("primary_contact_title")),
        "client_email": _plain_text(client.get("contact_email")),
        "client_phone": _plain_text(client.get("contact_phone")),
        "agreement_effective_date": _plain_text(snapshot_data.get("effective_date")),
    }

    def replace(match: re.Match[str]) -> str:
        value = values.get(match.group(1).casefold())
        return match.group(0) if value is None else _md_text(value)

    return _AGREEMENT_TOKEN.sub(replace, source)


def generate_document(
    session: Session, document_type: DocumentType, entity_id: int
) -> GeneratedDocument:
    """Render and atomically register a versioned PDF, removing the file if persistence fails."""
    session.rollback()
    temporary_path: Path | None = None
    destination: Path | None = None
    destination_created = False
    try:
        # Serialize version selection and file creation across simultaneous local requests.
        session.connection().exec_driver_sql("BEGIN IMMEDIATE")
        reference, _client_name, context, entity_status = document_context(
            session, document_type, entity_id
        )
        promote_agreement_to_pending = document_type == "agreement" and entity_status == "draft"
        promote_booking_to_pending = (
            document_type == "booking_confirmation" and entity_status == "draft"
        )
        if promote_agreement_to_pending:
            context["status_label"] = "Pending signature"
            entity_status = "pending"
        if promote_booking_to_pending:
            context["status_label"] = "Pending acceptance"
            entity_status = "pending"
        if not _REFERENCE.fullmatch(reference):
            raise ValueError("The generated document reference is not a safe filename")
        type_slug = {
            "agreement": "Master-Agreement",
            "booking_confirmation": "Booking-Confirmation",
            "invoice": "Invoice",
        }[document_type]
        existing = (
            session.scalar(
                select(func.max(GeneratedDocument.version)).where(
                    GeneratedDocument.document_type == document_type,
                    GeneratedDocument.reference == reference,
                )
            )
            or 0
        )
        version = existing + 1
        filename = f"{reference}_{type_slug}_v{version}.pdf"
        DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        destination = (DEFAULT_OUTPUT_DIR / filename).resolve()
        if destination.parent != DEFAULT_OUTPUT_DIR.resolve():
            raise ValueError(
                "Document output path is outside the configured local output directory"
            )

        content = render_pdf(document_type, context)
        with tempfile.NamedTemporaryFile(
            dir=destination.parent, suffix=".tmp", delete=False
        ) as temporary:
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path = Path(temporary.name)
        # A hard link publishes the completed file without replacing any existing version.
        os.link(temporary_path, destination)
        destination_created = True
        temporary_path.unlink()
        source_json, _ = snapshot(context)
        document = GeneratedDocument(
            document_type=document_type,
            client_id=_context_client_id(session, document_type, entity_id),
            booking_id=entity_id
            if document_type == "booking_confirmation"
            else _invoice_booking_id(session, entity_id)
            if document_type == "invoice"
            else None,
            invoice_id=entity_id if document_type == "invoice" else None,
            reference=reference,
            version=version,
            status=(
                "final"
                if entity_status in {"accepted", "finalized", "issued"}
                else "pending"
                if document_type in {"agreement", "booking_confirmation"}
                and entity_status == "pending"
                else "draft"
            ),
            file_path=str(destination),
            content_hash=hashlib.sha256(content).hexdigest(),
            template_version=str(context.get("template_version", TEMPLATE_VERSION)),
            source_snapshot_json=source_json,
        )
        session.add(document)
        if promote_agreement_to_pending:
            agreement = session.get(MasterAgreement, entity_id)
            if agreement is not None:
                agreement.status = "pending"
        if promote_booking_to_pending:
            booking = session.get(Booking, entity_id)
            if booking is not None:
                booking.status = "pending"
        session.commit()
    except Exception:
        session.rollback()
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        if destination_created and destination is not None:
            destination.unlink(missing_ok=True)
        raise
    session.refresh(document)
    activity.info(
        "document_generated type=%s reference=%s version=%d hash=%s",
        document.document_type,
        document.reference,
        document.version,
        document.content_hash,
    )
    return document


def _context_client_id(session: Session, document_type: DocumentType, entity_id: int) -> int:
    if document_type == "agreement":
        entity = session.get(MasterAgreement, entity_id)
    elif document_type == "booking_confirmation":
        entity = session.get(Booking, entity_id)
    else:
        entity = session.get(Invoice, entity_id)
    if entity is None:
        raise LookupError("Document source was not found")
    return (
        entity.client_id
        if document_type == "agreement"
        else entity.booking.client_id
        if document_type == "invoice"
        else entity.client_id
    )


def _invoice_booking_id(session: Session, invoice_id: int) -> int:
    invoice = session.get(Invoice, invoice_id)
    if invoice is None:
        raise LookupError("Invoice not found")
    return invoice.booking_id


def _person_name(profile: dict[str, Any]) -> str:
    """Format the photographer's legal and business names without implying an entity type."""
    legal_name = _plain_text(profile.get("legal_name"))
    business_name = _plain_text(profile.get("business_name"))
    if legal_name and business_name and legal_name.casefold() != business_name.casefold():
        return f"{legal_name} / {business_name}"
    return legal_name or business_name or "Photographer"


def _contact_name(client: dict[str, Any]) -> str:
    name = _plain_text(client.get("primary_contact_name"))
    title = _plain_text(client.get("primary_contact_title"))
    return f"{name} / {title}" if name and title else name or title


def _plain_text(value: object) -> str:
    """Convert optional snapshot values to display text without leaking object representations."""
    return value.strip() if isinstance(value, str) else ""


def _md_text(value: object) -> str:
    """Escape substituted values before passing them through the Markdown parser."""
    return html.escape(_plain_text(value), quote=True).replace("\n", "  \n")


def _current_invoice_reference(booking: Booking) -> str:
    current = [invoice for invoice in booking.invoices if not invoice.revisions]
    return current[-1].invoice_ref if current else ""


def _substitute_header_lines(source: str, snapshot_data: dict[str, Any]) -> str:
    """Populate agreement header placeholders from the immutable client/profile snapshot."""
    client = snapshot_data.get("client", {})
    photographer = snapshot_data.get("photographer", {})
    current_party: Literal["photographer", "client"] | None = None
    output: list[str] = []

    for line in source.splitlines():
        match = re.match(r"^\*\*(?P<label>[^*]+):\*\*\s*\[(?P<field>[^\]]+)\](?P<tail>\s*)$", line)
        if match is None:
            output.append(line)
            continue

        label = re.sub(r"[^a-z0-9]+", "", match.group("label").casefold())
        field = re.sub(r"[^a-z0-9]+", "", match.group("field").casefold())
        if label in {"photographer", "photographername"}:
            current_party = "photographer"
            value = _person_name(photographer)
        elif label in {"client", "clientname", "clientlegalname"}:
            current_party = "client"
            value = _plain_text(client.get("legal_name"))
        elif label in {"effectivedate", "date"} or field == "date":
            value = _plain_text(snapshot_data.get("effective_date"))
        elif label in {"authorizedrepresentative", "clientrepresentative"}:
            value = _contact_name(client)
        elif label in {"address", "mailingaddress"}:
            party = client if current_party == "client" else photographer
            value = _plain_text(party.get("mailing_address"))
        elif label in {"email", "contactemail"}:
            party = client if current_party == "client" else photographer
            key = "contact_email" if current_party == "client" else "email"
            value = _plain_text(party.get(key))
        elif field in {"legalnamebusinessname", "legalnamecompanyname"}:
            value = _person_name(photographer)
        else:
            output.append(line)
            continue

        output.append(match.group(0).split("[")[0] + _md_text(value) + match.group("tail"))

    return "\n".join(output) + "\n"
