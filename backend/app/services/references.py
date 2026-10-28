"""Database-atomic yearly document reference allocation."""

from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from backend.app.models import ReferenceSequence


def allocate_reference(session: Session, kind: str, year: int) -> str:
    """Reserve the next unique reference within the caller's transaction."""
    prefix = {"booking": "BK", "invoice": "INV", "agreement": "AGR"}.get(kind)
    if prefix is None:
        raise ValueError("Unsupported reference type")
    statement = (
        insert(ReferenceSequence)
        .values(kind=kind, year=year, last_value=1)
        .on_conflict_do_update(
            index_elements=[ReferenceSequence.kind, ReferenceSequence.year],
            set_={"last_value": ReferenceSequence.last_value + 1},
        )
        .returning(ReferenceSequence.last_value)
    )
    sequence = session.execute(statement).scalar_one()
    return f"{prefix}-{year}-{sequence:03d}"
