"""Load and safely replace the local master-agreement Markdown template."""

import hashlib
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, TypedDict

from backend.app.config import ACTIVE_AGREEMENT_TEMPLATE, LEGAL_SOURCE, TEMPLATE_VERSION

MAX_TEMPLATE_BYTES = 1_048_576


class AgreementTemplate(TypedDict):
    content: str
    template_version: str
    content_hash: str
    source: Literal["bundled", "custom"]
    updated_at: str | None


def get_agreement_template() -> AgreementTemplate:
    """Return the active text, source version, content hash, and local update time."""
    custom_path = _safe_template_path()
    if custom_path.exists() and not custom_path.is_file():
        raise OSError("The saved agreement template path is not a regular file")
    if custom_path.is_file():
        try:
            content = custom_path.read_text(encoding="utf-8")
            updated_at = datetime.fromtimestamp(custom_path.stat().st_mtime, UTC).isoformat()
        except (OSError, UnicodeError) as exc:
            raise OSError("The saved agreement template could not be read") from exc
        source: Literal["bundled", "custom"] = "custom"
    else:
        try:
            bundled_text = LEGAL_SOURCE.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise OSError("The bundled agreement template could not be read") from exc
        if "\n---\n" not in bundled_text:
            raise ValueError("The bundled agreement template is missing its content boundary")
        content = bundled_text.split("\n---\n", maxsplit=1)[0].rstrip() + "\n"
        updated_at = None
        source = "bundled"

    _validate_content(content)
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    version = TEMPLATE_VERSION if source == "bundled" else f"custom-{digest[:12]}"
    return {
        "content": content,
        "template_version": version,
        "content_hash": digest,
        "source": source,
        "updated_at": updated_at,
    }


def save_agreement_template(content: str) -> AgreementTemplate:
    """Validate and atomically persist a custom agreement template in the data folder."""
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    if not content.endswith("\n"):
        content += "\n"
    _validate_content(content)

    path = _safe_template_path()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, prefix=".agreement-template-", delete=False
        ) as temporary:
            if hasattr(os, "fchmod"):
                os.fchmod(temporary.fileno(), 0o600)
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path = Path(temporary.name)
        os.replace(temporary_path, path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    return get_agreement_template()


def reset_agreement_template() -> AgreementTemplate:
    """Remove the custom template and reactivate the bundled default."""
    path = _safe_template_path()
    path.unlink(missing_ok=True)
    return get_agreement_template()


def _safe_template_path() -> Path:
    """Ensure the active template is a regular file directly inside local data storage."""
    root = ACTIVE_AGREEMENT_TEMPLATE.parent.resolve()
    path = root / ACTIVE_AGREEMENT_TEMPLATE.name
    if path.is_symlink() or path.resolve().parent != root:
        raise OSError("The saved agreement template path is unsafe")
    return path


def _validate_content(content: str) -> None:
    """Reject blank, binary-like, or oversized agreement content before saving or rendering."""
    if not content.strip():
        raise ValueError("Enter or upload non-empty Markdown for the master agreement")
    if "\x00" in content:
        raise ValueError("The agreement template must be plain UTF-8 Markdown text")
    if len(content.encode("utf-8")) > MAX_TEMPLATE_BYTES:
        raise ValueError("The agreement template must be 1 MB or smaller")
