"""Add standard PDF signature and text fields to Chromium-rendered documents."""

import math
import re
from io import BytesIO
from typing import Any

from pypdf import PdfReader, PdfWriter
from pypdf.errors import PyPdfError
from pypdf.generic import (
    ArrayObject,
    BooleanObject,
    DictionaryObject,
    NameObject,
    NumberObject,
    RectangleObject,
    TextStringObject,
)

_CSS_PIXEL_TO_POINT = 72 / 96


def add_pdf_form_fields(
    pdf_content: bytes,
    form_fields: list[dict[str, Any]],
    *,
    left_margin_points: float,
    top_margin_points: float,
) -> bytes:
    """Attach AcroForm widgets from print-layout coordinates to the final page."""
    if not form_fields:
        return pdf_content

    try:
        return _build_form_pdf(
            pdf_content,
            form_fields,
            left_margin_points=left_margin_points,
            top_margin_points=top_margin_points,
        )
    except PyPdfError as exc:
        raise RuntimeError("Interactive signature fields could not be added to the PDF.") from exc


def _build_form_pdf(
    pdf_content: bytes,
    form_fields: list[dict[str, Any]],
    *,
    left_margin_points: float,
    top_margin_points: float,
) -> bytes:
    reader = PdfReader(BytesIO(pdf_content))
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)
    fields = ArrayObject()
    helvetica = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    resources = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject(
                {NameObject("/Helv"): writer._add_object(helvetica)}
            )
        }
    )
    acro_form = DictionaryObject(
        {
            NameObject("/Fields"): fields,
            NameObject("/NeedAppearances"): BooleanObject(True),
            NameObject("/SigFlags"): NumberObject(1),
            NameObject("/DA"): TextStringObject("/Helv 10 Tf 0 g"),
            NameObject("/DR"): resources,
        }
    )
    writer._root_object.update({NameObject("/AcroForm"): writer._add_object(acro_form)})

    # Signature fields are constrained to the dedicated final page by the document templates.
    page = writer.pages[-1]
    page_width = float(page.mediabox.width)
    page_height = float(page.mediabox.height)
    seen_names: set[str] = set()

    for spec in form_fields:
        name = spec.get("name")
        field_type = spec.get("type")
        if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9_.]{2,79}", name):
            raise ValueError("PDF form field has an invalid name")
        if name in seen_names:
            raise ValueError(f"PDF form field name is duplicated: {name}")
        if field_type not in {"signature", "text"}:
            raise ValueError(f"Unsupported PDF form field type: {field_type}")
        seen_names.add(name)

        x = _coordinate(spec, "x") * _CSS_PIXEL_TO_POINT + left_margin_points
        y = _coordinate(spec, "y") * _CSS_PIXEL_TO_POINT
        width = _coordinate(spec, "width") * _CSS_PIXEL_TO_POINT
        height = _coordinate(spec, "height") * _CSS_PIXEL_TO_POINT
        rect = [
            x,
            page_height - top_margin_points - y - height,
            x + width,
            page_height - top_margin_points - y,
        ]
        if (
            width <= 0
            or height <= 0
            or rect[0] < 0
            or rect[1] < 0
            or rect[2] > page_width
            or rect[3] > page_height
        ):
            raise ValueError(f"PDF form field falls outside the page: {name}")

        label = spec.get("label")
        if not isinstance(label, str) or not label.strip():
            raise ValueError(f"PDF form field is missing its label: {name}")
        widget = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Annot"),
                NameObject("/Subtype"): NameObject("/Widget"),
                NameObject("/FT"): NameObject("/Sig" if field_type == "signature" else "/Tx"),
                NameObject("/T"): TextStringObject(name),
                NameObject("/TU"): TextStringObject(label.strip()),
                NameObject("/Rect"): RectangleObject(rect),
                NameObject("/F"): NumberObject(4),
                NameObject("/Ff"): NumberObject(2),
                NameObject("/P"): writer.get_reference(page),
            }
        )
        if field_type == "text":
            widget.update(
                {
                    NameObject("/DA"): TextStringObject("/Helv 10 Tf 0 g"),
                    NameObject("/Q"): NumberObject(0),
                    NameObject("/MaxLen"): NumberObject(120),
                }
            )
        field_ref = writer._add_object(widget)
        annotations = page.get("/Annots")
        if annotations is None:
            annotations = ArrayObject()
            page[NameObject("/Annots")] = annotations
        annotations.append(field_ref)
        fields.append(field_ref)

    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def _coordinate(spec: dict[str, Any], key: str) -> float:
    """Validate a numeric CSS coordinate before converting it to a PDF rectangle."""
    value = spec.get(key)
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise ValueError(f"PDF form field coordinate {key} is not numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"PDF form field coordinate {key} is not finite")
    return result
