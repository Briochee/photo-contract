"""Finalize bookings from uploaded signed confirmations while preserving document versions."""

import hashlib
import os
import re
import tempfile
from datetime import UTC, date, datetime, time
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.config import DATA_DIR, DEFAULT_OUTPUT_DIR
from backend.app.logging_config import activity
from backend.app.models import Booking, GeneratedDocument, PhotographerProfile
from backend.app.services.domain import booking_values, get_booking, profile_values, snapshot

MAX_SIGNED_CONFIRMATION_BYTES = 25 * 1024 * 1024
_SAFE_BOOKING_REFERENCE = re.compile(r"^BK-\d{4}-\d{3,}$")


class BookingFinalizationConflict(ValueError):
    """Represent a booking state that cannot be finalized through an upload."""


def store_signed_booking_confirmation(
    session: Session,
    booking_id: int,
    signed_date: date,
    upload_filename: str,
    content: bytes,
) -> tuple[Booking, GeneratedDocument]:
    """Finalize a booking and atomically add its signed confirmation as an immutable document.

    The uploaded bytes are written under a generated name in the document library. The current
    booking and photographer details are snapshotted before the database transaction commits.
    """
    if not upload_filename.casefold().endswith(".pdf") or not content.startswith(b"%PDF-"):
        raise ValueError("Upload a valid signed booking confirmation PDF")
    if not content or len(content) > MAX_SIGNED_CONFIRMATION_BYTES:
        raise ValueError("The signed PDF must be 25 MB or smaller")

    session.rollback()
    temporary_path: Path | None = None
    destination: Path | None = None
    destination_created = False
    try:
        session.connection().exec_driver_sql("BEGIN IMMEDIATE")
        booking = get_booking(session, booking_id)
        if booking is None:
            raise LookupError("Booking not found")
        if booking.status == "finalized":
            raise BookingFinalizationConflict("This booking has already been finalized")
        if booking.status not in {"draft", "pending"}:
            raise BookingFinalizationConflict(
                "This booking cannot be finalized from its current status"
            )
        if not booking.line_items:
            raise ValueError("Add at least one agreed charge before finalizing the booking")
        if not _SAFE_BOOKING_REFERENCE.fullmatch(booking.booking_ref):
            raise ValueError("The booking reference cannot be used as a safe filename")

        root = DEFAULT_OUTPUT_DIR
        data_root = DATA_DIR.resolve()
        if root.is_symlink() or root.resolve().parent != data_root:
            raise ValueError("The configured document library is outside the local data folder")
        root.mkdir(parents=True, exist_ok=True)
        root = root.resolve()

        previous_version = (
            session.scalar(
                select(func.max(GeneratedDocument.version)).where(
                    GeneratedDocument.document_type == "booking_confirmation",
                    GeneratedDocument.reference == booking.booking_ref,
                )
            )
            or 0
        )
        version = previous_version + 1
        filename = f"{booking.booking_ref}_Signed-Booking-Confirmation_v{version}.pdf"
        destination = root / filename
        if destination.parent != root:
            raise ValueError("The signed PDF path is outside the document library")

        with tempfile.NamedTemporaryFile(dir=root, suffix=".tmp", delete=False) as temporary:
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path = Path(temporary.name)
        os.link(temporary_path, destination)
        destination_created = True
        temporary_path.unlink()

        booking.status = "finalized"
        booking.accepted_at = datetime.combine(signed_date, time.min, tzinfo=UTC)
        booking.acceptance_reference = f"Uploaded signed PDF: {filename}"[:200]
        profile = session.scalar(
            select(PhotographerProfile).order_by(PhotographerProfile.id).limit(1)
        )
        booking.accepted_snapshot_json, _ = snapshot(
            {"booking": booking_values(booking), "photographer": profile_values(profile)}
        )
        document = GeneratedDocument(
            document_type="booking_confirmation",
            client_id=booking.client_id,
            booking_id=booking.id,
            reference=booking.booking_ref,
            version=version,
            status="final",
            file_path=str(destination),
            content_hash=hashlib.sha256(content).hexdigest(),
            template_version="signed-pdf-upload",
            source_snapshot_json=booking.accepted_snapshot_json,
        )
        session.add(document)
        session.commit()
    except Exception:
        session.rollback()
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        if destination_created and destination is not None:
            destination.unlink(missing_ok=True)
        raise

    session.refresh(booking)
    session.refresh(document)
    activity.info(
        "booking_finalized reference=%s method=uploaded_pdf version=%d",
        booking.booking_ref,
        document.version,
    )
    return booking, document
