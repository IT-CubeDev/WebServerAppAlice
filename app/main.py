from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from pathlib import Path

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_login import current_user, login_required

from app import db
from app.forms import NoteForm
from app.models import AliceLinkToken, Note
from app.services.weather import fetch_current_weather, weathercode_description
from app.utils.files import save_upload
from app.utils.tags import assign_tags_from_string

bp = Blueprint("main", __name__)


def _upload_dir() -> Path:
    return Path(current_app.config["UPLOAD_FOLDER"])


def _delete_note_image(note: Note) -> None:
    if not note.image_filename:
        return
    path = _upload_dir() / note.image_filename
    try:
        if path.is_file():
            path.unlink()
    except OSError:
        current_app.logger.warning("Не удалось удалить файл %s", path)


def _generate_alice_code() -> str:
    for _ in range(30):
        code = "".join(secrets.choice("0123456789") for _ in range(6))
        if not AliceLinkToken.query.filter_by(code=code).first():
            return code
    return secrets.token_hex(3)[:6].upper()


@bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return render_template("main/index.html")


@bp.route("/dashboard")
@login_required
def dashboard():
    notes_total = Note.query.filter_by(user_id=current_user.id).count()
    weather = fetch_current_weather(
        float(current_app.config["WEATHER_LAT"]),
        float(current_app.config["WEATHER_LON"]),
    )
    weather_desc = None
    if "error" not in weather:
        weather_desc = weathercode_description(weather.get("weathercode"))

    return render_template(
        "main/dashboard.html",
        notes_total=notes_total,
        weather=weather,
        weather_desc=weather_desc,
    )


@bp.route("/alice", methods=["GET", "POST"])
@login_required
def alice_panel():
    if request.method == "POST":
        AliceLinkToken.query.filter_by(user_id=current_user.id).delete(synchronize_session=False)
        code = _generate_alice_code()
        exp = datetime.utcnow() + timedelta(minutes=15)
        db.session.add(AliceLinkToken(code=code, user_id=current_user.id, expires_at=exp))
        db.session.commit()
        flash(f"Код для Алисы: {code} (действует 15 минут). Скажите: привязать {code}", "success")

    active = (
        AliceLinkToken.query.filter(
            AliceLinkToken.user_id == current_user.id,
            AliceLinkToken.expires_at > datetime.utcnow(),
        )
        .order_by(AliceLinkToken.expires_at.desc())
        .first()
    )
    linked = current_user.alice_link is not None
    return render_template("main/alice.html", active_token=active, linked=linked)


@bp.route("/notes")
@login_required
def note_list():
    page = request.args.get("page", 1, type=int) or 1
    if page < 1:
        page = 1
    per_page = int(current_app.config.get("NOTES_PER_PAGE", 8))

    pagination = (
        Note.query.filter_by(user_id=current_user.id)
        .order_by(Note.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )
    return render_template("main/note_list.html", pagination=pagination)


@bp.route("/notes/new", methods=["GET", "POST"])
@login_required
def note_create():
    form = NoteForm()
    if form.validate_on_submit():
        note = Note(
            title=form.title.data.strip(),
            body=form.body.data.strip(),
            user_id=current_user.id,
        )
        assign_tags_from_string(note, form.tags.data)

        file = form.image.data
        if file and getattr(file, "filename", None):
            allowed = set(current_app.config["ALLOWED_EXTENSIONS"])
            saved = save_upload(file, _upload_dir(), allowed)
            if saved:
                note.image_filename = saved
            else:
                flash("Файл изображения не принят.", "warning")

        db.session.add(note)
        db.session.commit()
        flash("Заметка создана.", "success")
        return redirect(url_for("main.note_detail", note_id=note.id))

    return render_template("main/note_form.html", form=form, title="Новая заметка")


@bp.route("/notes/<int:note_id>")
@login_required
def note_detail(note_id: int):
    note = Note.query.filter_by(id=note_id, user_id=current_user.id).first_or_404()
    return render_template("main/note_detail.html", note=note)


@bp.route("/notes/<int:note_id>/edit", methods=["GET", "POST"])
@login_required
def note_edit(note_id: int):
    note = Note.query.filter_by(id=note_id, user_id=current_user.id).first_or_404()
    form = NoteForm(obj=note)
    if request.method == "GET":
        form.tags.data = ", ".join(t.name for t in note.tags)

    if form.validate_on_submit():
        note.title = form.title.data.strip()
        note.body = form.body.data.strip()
        assign_tags_from_string(note, form.tags.data)

        file = form.image.data
        if file and getattr(file, "filename", None):
            allowed = set(current_app.config["ALLOWED_EXTENSIONS"])
            saved = save_upload(file, _upload_dir(), allowed)
            if saved:
                _delete_note_image(note)
                note.image_filename = saved
            else:
                flash("Новый файл не принят.", "warning")

        db.session.commit()
        flash("Сохранено.", "success")
        return redirect(url_for("main.note_detail", note_id=note.id))

    return render_template("main/note_form.html", form=form, title="Редактирование заметки")


@bp.route("/notes/<int:note_id>/delete", methods=["POST"])
@login_required
def note_delete(note_id: int):
    note = Note.query.filter_by(id=note_id, user_id=current_user.id).first_or_404()
    _delete_note_image(note)
    db.session.delete(note)
    db.session.commit()
    flash("Удалено.", "info")
    return redirect(url_for("main.note_list"))


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST" and request.form.get("action") == "rotate_token":
        current_user.api_token = secrets.token_urlsafe(32)
        db.session.commit()
        flash("API-токен обновлён.", "success")
        return redirect(url_for("main.profile"))

    if not current_user.api_token:
        current_user.ensure_api_token()
        db.session.commit()

    return render_template("main/profile.html")


@bp.route("/uploads/<path:filename>")
@login_required
def uploaded_file(filename: str):
    if ".." in filename or filename.startswith(("/", "\\")):
        abort(404)

    note = Note.query.filter_by(image_filename=filename, user_id=current_user.id).first()
    if note is None:
        abort(404)

    return send_from_directory(_upload_dir(), filename, as_attachment=False)
