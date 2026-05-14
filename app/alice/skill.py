from __future__ import annotations

import re
from datetime import datetime, timedelta

from app import db
from app.alice.protocol import build_alice_response
from app.models import AliceLink, AliceLinkToken, Note, User
from app.services.weather import fetch_current_weather, weathercode_description
from app.utils.tags import assign_tags_from_string


def _yandex_user_id(session: dict) -> str | None:
    user = session.get("user") or {}
    return user.get("user_id")


def _extract_code(text: str) -> str | None:
    digits = re.sub(r"\D", "", text)
    if len(digits) >= 6:
        return digits[:6]
    return None


def _help_text() -> str:
    return (
        "Я умею: привязать шестизначный код с сайта. "
        "Список заметок. Запиши и текст заметки. "
        "Заметка, заголовок, вертикальная черта, текст. "
        "Погода. Помощь. Выход."
    )


def _bind(yandex_uid: str, code: str) -> dict:
    now = datetime.utcnow()
    token = AliceLinkToken.query.filter_by(code=code).first()
    if not token or token.expires_at < now:
        return build_alice_response("Код не подходит или устарел. Сгенерируйте новый на сайте.")

    user = User.query.filter_by(id=token.user_id).first()
    if not user:
        return build_alice_response("Ошибка профиля. Зарегистрируйтесь на сайте заново.")

    AliceLink.query.filter_by(yandex_user_id=yandex_uid).delete(synchronize_session=False)
    AliceLink.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    db.session.add(AliceLink(yandex_user_id=yandex_uid, user_id=user.id))
    AliceLinkToken.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    db.session.commit()

    return build_alice_response(
        f"Аккаунт {user.username} привязан. Скажите: список заметок или запиши и текст.",
        tts=f"Аккаунт {user.username} привязан.",
    )


def process_alice_request(body: dict, config: dict) -> dict:
    session = body.get("session") or {}
    request_data = body.get("request") or {}
    utter = (request_data.get("original_utterance") or request_data.get("command") or "").strip()
    utter_l = utter.lower()

    yuid = _yandex_user_id(session)
    if not yuid:
        return build_alice_response(
            "Войдите в аккаунт Яндекса в приложении и откройте навык снова.",
            end_session=True,
        )

    link = AliceLink.query.filter_by(yandex_user_id=yuid).first()

    if session.get("new"):
        if link:
            return build_alice_response(
                "Здравствуйте! Скажите список заметок, запиши текст, погода или помощь.",
            )
        return build_alice_response(
            "Привет! Откройте сайт навыка, войдите в аккаунт и получите код в разделе Алиса. "
            "Потом скажите: привязать и шесть цифр.",
        )

    if not link:
        code = _extract_code(utter_l)
        if code:
            return _bind(yuid, code)
        return build_alice_response(
            "Нужна привязка. Сайт, раздел Алиса, код шесть цифр. Потом скажите привязать и код.",
        )

    user = link.user

    if any(k in utter_l for k in ("справка", "помощь", "что ты умеешь", "умеешь")):
        return build_alice_response(_help_text())

    if utter_l in ("выход", "стоп", "хватит", "закрой навык"):
        return build_alice_response("До свидания!", end_session=True)

    if "погод" in utter_l:
        lat = float(config.get("WEATHER_LAT", 55.7558))
        lon = float(config.get("WEATHER_LON", 37.6173))
        w = fetch_current_weather(lat, lon)
        if w.get("error"):
            return build_alice_response(w["error"])
        desc = weathercode_description(w.get("weathercode"))
        t = w.get("temperature")
        msg = f"Сейчас около {t} градусов. {desc}."
        return build_alice_response(msg)

    if any(k in utter_l for k in ("список заметок", "мои заметки", "покажи заметки", "какие заметки")):
        notes = (
            Note.query.filter_by(user_id=user.id)
            .order_by(Note.created_at.desc())
            .limit(5)
            .all()
        )
        if not notes:
            return build_alice_response("Заметок пока нет. Скажите запиши и текст.")
        lines = [f"{n.id}. {n.title}" for n in notes]
        return build_alice_response("Последние заметки:\n" + "\n".join(lines))

    if utter_l.startswith("запиши"):
        idx = utter_l.find("запиши") + len("запиши")
        body_txt = utter[idx:].strip(" .,:;\n\t")
        if not body_txt:
            return build_alice_response("Скажите, например: запиши купить молоко.")
        title = f"Голос {datetime.utcnow().strftime('%d.%m %H:%M')}"
        note = Note(title=title[:140], body=body_txt[:20000], user_id=user.id)
        db.session.add(note)
        db.session.commit()
        return build_alice_response(f"Записала заметку: {title}.")

    if utter_l.startswith("заметка"):
        idx = utter_l.find("заметка") + len("заметка")
        rest = utter[idx:].strip(" .,:;\n\t")
        if "|" in rest:
            title, body_txt = rest.split("|", 1)
            title, body_txt = title.strip(), body_txt.strip()
        else:
            parts = rest.split(maxsplit=1)
            if len(parts) < 2:
                return build_alice_response("Скажите: заметка заголовок вертикальная черта текст.")
            title, body_txt = parts[0], parts[1]
        if not title or not body_txt:
            return build_alice_response("Нужны заголовок и текст.")
        note = Note(title=title[:140], body=body_txt[:20000], user_id=user.id)
        db.session.add(note)
        db.session.commit()
        return build_alice_response(f"Создала заметку {title}.")

    if utter_l.startswith("теги") or utter_l.startswith("добавь теги"):
        rest = re.sub(r"^(теги|добавь\s+теги)\s*", "", utter_l, count=1).strip()
        m = re.match(r"^(\d+)\s+(.+)$", rest)
        if not m:
            return build_alice_response("Скажите: теги номер заметки через пробел и теги через запятую.")
        note_id = int(m.group(1))
        tags_raw = m.group(2)
        note = Note.query.filter_by(id=note_id, user_id=user.id).first()
        if not note:
            return build_alice_response("Такой заметки нет.")
        assign_tags_from_string(note, tags_raw)
        db.session.commit()
        return build_alice_response("Теги обновлены.")

    base = (config.get("PUBLIC_BASE_URL") or "").rstrip("/")
    buttons = None
    if base:
        buttons = [{"title": "Открыть сайт", "url": base, "hide": True}]

    return build_alice_response(
        "Не поняла команду. Скажите помощь или откройте сайт.",
        buttons=buttons,
    )
