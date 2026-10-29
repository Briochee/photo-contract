"""Photographer profile and local application preferences."""

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask

from backend.app.config import DEFAULT_OUTPUT_DIR
from backend.app.database import get_session
from backend.app.logging_config import activity
from backend.app.models import AppSetting, PhotographerProfile
from backend.app.schemas import ClearAllDataInput, ProfileInput
from backend.app.services.backup import create_backup, remove_backup
from backend.app.services.data_reset import DataResetError, clear_application_data
from backend.app.services.domain import profile_values, set_profile

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/backup", include_in_schema=True)
def download_backup():
    try:
        path = create_backup()
    except OSError as exc:
        raise HTTPException(503, "A local data backup could not be created") from exc
    return FileResponse(
        path,
        media_type="application/zip",
        filename="contract-studio-backup.zip",
        background=BackgroundTask(remove_backup, path),
    )


@router.get("")
def get_settings(session: Session = Depends(get_session)):
    profile = session.scalar(select(PhotographerProfile).order_by(PhotographerProfile.id).limit(1))
    stored = {
        row.key: json.loads(row.value_json) for row in session.scalars(select(AppSetting)).all()
    }
    return {
        "profile": profile_values(profile),
        "output_directory": str(DEFAULT_OUTPUT_DIR),
        "preferences": {**{"pdf_page_size": "Letter"}, **stored},
    }


@router.patch("")
def update_settings(payload: ProfileInput, session: Session = Depends(get_session)):
    try:
        profile = set_profile(session, payload)
        session.commit()
    except (TypeError, ValueError) as exc:
        session.rollback()
        raise HTTPException(422, str(exc)) from exc
    return {
        "profile": profile_values(profile),
        "output_directory": str(DEFAULT_OUTPUT_DIR),
        "preferences": {"pdf_page_size": "Letter"},
    }


@router.delete("/data")
def clear_all_data(
    payload: ClearAllDataInput, session: Session = Depends(get_session)
) -> dict[str, bool]:
    """Remove all local business data after the caller provides the exact confirmation token."""
    try:
        result = clear_application_data(session)
    except (DataResetError, OSError, SQLAlchemyError) as exc:
        activity.error("application_data_clear_failed error=%s", type(exc).__name__)
        raise HTTPException(
            503, "Application data could not be cleared safely. No reset was completed."
        ) from exc

    activity.info("application_data_cleared reference_sequences_retained=true")
    return result
