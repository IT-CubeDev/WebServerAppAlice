from __future__ import annotations

import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


def fetch_current_weather(latitude: float, longitude: float, timeout: float = 6.0) -> dict[str, Any]:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current_weather": "true",
    }
    try:
        response = requests.get(OPEN_METEO_URL, params=params, timeout=timeout)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        logger.warning("Ошибка запроса погоды: %s", exc)
        return {"error": "Не удалось получить погоду."}

    current = data.get("current_weather")
    if not isinstance(current, dict):
        return {"error": "Неожиданный формат ответа API."}

    return {
        "temperature": current.get("temperature"),
        "windspeed": current.get("windspeed"),
        "weathercode": current.get("weathercode"),
        "is_day": current.get("is_day"),
        "time": current.get("time"),
    }


def weathercode_description(code: int | None) -> str:
    if code is None:
        return "нет данных"
    mapping = {
        0: "Ясно",
        1: "Преимущественно ясно",
        2: "Переменная облачность",
        3: "Пасмурно",
        45: "Туман",
        61: "Дождь слабый",
        63: "Дождь",
        95: "Гроза",
    }
    return mapping.get(int(code), f"Код {code}")
