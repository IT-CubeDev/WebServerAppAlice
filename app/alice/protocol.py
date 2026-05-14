from __future__ import annotations

from typing import Any


def build_alice_response(
    text: str,
    *,
    tts: str | None = None,
    end_session: bool = False,
    buttons: list[dict[str, Any]] | None = None,
    card: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resp: dict[str, Any] = {
        "text": text[:1024],
        "tts": (tts if tts is not None else text)[:1024],
        "end_session": end_session,
    }
    if buttons:
        resp["buttons"] = buttons
    if card:
        resp["card"] = card
    return {"response": resp, "version": "1.0"}
