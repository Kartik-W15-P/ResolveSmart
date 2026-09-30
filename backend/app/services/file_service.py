import os
import uuid
from pathlib import Path
from werkzeug.utils import secure_filename
from flask import current_app

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FALLBACK_UPLOAD_DIR = os.path.join(str(PROJECT_ROOT), "uploads", "complaints")


def allowed_file(filename: str) -> bool:
    """Validate file extension against allowlist."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_upload_dir() -> str:
    """Safely resolve the upload directory path."""
    try:
        configured_path = current_app.config.get("UPLOAD_FOLDER")
        if configured_path:
            return str(configured_path)
    except Exception:
        pass
    return FALLBACK_UPLOAD_DIR


def save_complaint_image(file_storage, complaint_id: int):
    """
    Validates, renames, and saves an uploaded image.
    Returns a tuple of (unique_filename, access_url_path).
    """
    if not file_storage or file_storage.filename == "":
        raise ValueError("No file selected")

    if not allowed_file(file_storage.filename):
        raise ValueError("Invalid file extension. Allowed: png, jpg, jpeg, webp")

    original_filename = secure_filename(file_storage.filename)
    extension = original_filename.rsplit(".", 1)[1].lower() if "." in original_filename else "png"
    unique_filename = f"comp_{complaint_id}_{uuid.uuid4().hex[:8]}.{extension}"

    upload_dir = get_upload_dir()
    os.makedirs(upload_dir, exist_ok=True)

    destination_path = os.path.join(upload_dir, unique_filename)
    file_storage.save(destination_path)

    access_path = f"/api/complaints/uploads/{unique_filename}"
    return unique_filename, access_path