from __future__ import annotations

from app import db
from app.models import Note, Tag


def assign_tags_from_string(note: Note, raw: str | None) -> None:
    if raw is None:
        return
    names = [p.strip().lower() for p in raw.split(",")]
    names = [n for n in names if n][:30]
    tags: list[Tag] = []
    for name in names:
        name = name[:40]
        tag = Tag.query.filter_by(name=name).first()
        if tag is None:
            tag = Tag(name=name)
            db.session.add(tag)
        tags.append(tag)
    note.tags = tags
