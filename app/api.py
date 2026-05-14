from __future__ import annotations

from functools import wraps

from flask import Blueprint, jsonify, request

from app import db
from app.models import Note, User
from app.utils.tags import assign_tags_from_string

bp = Blueprint("api", __name__, url_prefix="/api/v1")


def _token_from_request() -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip() or None
    return None


def require_api_token(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = _token_from_request()
        if not token:
            return jsonify({"error": "Нужен заголовок Authorization: Bearer <token>"}), 401
        user = User.query.filter_by(api_token=token).first()
        if user is None:
            return jsonify({"error": "Неверный токен"}), 401
        return f(user, *args, **kwargs)

    return wrapper


@bp.route("/notes", methods=["GET"])
@require_api_token
def list_notes(user: User):
    page = request.args.get("page", 1, type=int) or 1
    if page < 1:
        page = 1
    per = min(request.args.get("per_page", 20, type=int) or 20, 50)

    pagination = (
        Note.query.filter_by(user_id=user.id)
        .order_by(Note.created_at.desc())
        .paginate(page=page, per_page=per, error_out=False)
    )

    return jsonify(
        {
            "items": [n.to_dict() for n in pagination.items],
            "page": pagination.page,
            "pages": pagination.pages,
            "total": pagination.total,
        }
    )


@bp.route("/notes/<int:note_id>", methods=["GET"])
@require_api_token
def get_note(user: User, note_id: int):
    note = Note.query.filter_by(id=note_id, user_id=user.id).first()
    if note is None:
        return jsonify({"error": "Заметка не найдена"}), 404
    return jsonify(note.to_dict())


@bp.route("/notes", methods=["POST"])
@require_api_token
def create_note(user: User):
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    body = (data.get("body") or "").strip()
    tags_raw = data.get("tags")

    if not title:
        return jsonify({"error": "Поле title обязательно"}), 400
    if not body:
        return jsonify({"error": "Поле body обязательно"}), 400

    note = Note(title=title[:140], body=body[:20000], user_id=user.id)
    if isinstance(tags_raw, str):
        assign_tags_from_string(note, tags_raw)
    db.session.add(note)
    db.session.commit()
    return jsonify(note.to_dict()), 201


@bp.route("/notes/<int:note_id>", methods=["PUT", "PATCH"])
@require_api_token
def update_note(user: User, note_id: int):
    note = Note.query.filter_by(id=note_id, user_id=user.id).first()
    if note is None:
        return jsonify({"error": "Заметка не найдена"}), 404

    data = request.get_json(silent=True) or {}
    if "title" in data:
        t = (data.get("title") or "").strip()
        if not t:
            return jsonify({"error": "title не может быть пустым"}), 400
        note.title = t[:140]
    if "body" in data:
        b = (data.get("body") or "").strip()
        if not b:
            return jsonify({"error": "body не может быть пустым"}), 400
        note.body = b[:20000]
    if "tags" in data and isinstance(data.get("tags"), str):
        assign_tags_from_string(note, data.get("tags"))

    db.session.commit()
    return jsonify(note.to_dict())


@bp.route("/notes/<int:note_id>", methods=["DELETE"])
@require_api_token
def delete_note(user: User, note_id: int):
    note = Note.query.filter_by(id=note_id, user_id=user.id).first()
    if note is None:
        return jsonify({"error": "Заметка не найдена"}), 404
    db.session.delete(note)
    db.session.commit()
    return jsonify({"status": "deleted", "id": note_id})


@bp.route("/whoami", methods=["GET"])
@require_api_token
def whoami(user: User):
    return jsonify({"id": user.id, "username": user.username, "email": user.email})
