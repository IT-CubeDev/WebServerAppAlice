from __future__ import annotations

import secrets
from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app import db, login_manager


note_tags = db.Table(
    "note_tags",
    db.Column("note_id", db.Integer, db.ForeignKey("note.id"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("tag.id"), primary_key=True),
)


class User(UserMixin, db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    api_token = db.Column(db.String(64), unique=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    notes = db.relationship(
        "Note",
        backref="author",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    alice_link = db.relationship(
        "AliceLink",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def ensure_api_token(self) -> str:
        if not self.api_token:
            self.api_token = secrets.token_urlsafe(32)
        return self.api_token

    def __repr__(self) -> str:
        return f"<User {self.username}>"


@login_manager.user_loader
def load_user(user_id: str):
    if not user_id:
        return None
    return User.query.get(int(user_id))


class AliceLink(db.Model):
    __tablename__ = "alice_link"

    id = db.Column(db.Integer, primary_key=True)
    yandex_user_id = db.Column(db.String(128), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), unique=True, nullable=False)

    user = db.relationship("User", back_populates="alice_link")

    def __repr__(self) -> str:
        return f"<AliceLink yandex={self.yandex_user_id[:8]}...>"


class AliceLinkToken(db.Model):
    __tablename__ = "alice_link_token"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(6), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)

    user = db.relationship("User", backref=db.backref("alice_tokens", lazy="dynamic"))


class Tag(db.Model):
    __tablename__ = "tag"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(40), unique=True, nullable=False, index=True)

    notes = db.relationship(
        "Note",
        secondary=note_tags,
        back_populates="tags",
    )

    def __repr__(self) -> str:
        return f"<Tag {self.name}>"


class Note(db.Model):
    __tablename__ = "note"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140), nullable=False)
    body = db.Column(db.Text, nullable=False, default="")
    image_filename = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)

    tags = db.relationship(
        "Tag",
        secondary=note_tags,
        back_populates="notes",
        lazy="joined",
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "body": self.body,
            "image_url": f"/uploads/{self.image_filename}" if self.image_filename else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "tags": [t.name for t in self.tags],
            "author_id": self.user_id,
        }

    def __repr__(self) -> str:
        return f"<Note {self.id} {self.title!r}>"
