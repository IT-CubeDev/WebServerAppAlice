from __future__ import annotations

import uuid
from pathlib import Path

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename


def allowed_file(filename: str, allowed: set[str]) -> bool:
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[-1].lower()
    return ext in allowed


def save_upload(file: FileStorage, upload_folder: Path, allowed: set[str]) -> str | None:
    # uuid + secure_filename
    if not file or not file.filename:
        return None
    if not allowed_file(file.filename, allowed):
        return None
    raw = secure_filename(file.filename)
    if not raw:
        return None
    unique = f"{uuid.uuid4().hex}_{raw}"
    path = upload_folder / unique
    upload_folder.mkdir(parents=True, exist_ok=True)
    file.save(path)
    return unique
