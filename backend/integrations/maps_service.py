"""
Сервис интеграции с Yandex Maps API (задача 2.4.3).

Геокодирование адресов, расчёт расстояния между точками, поиск ближайших магазинов.

§5.2.3 (чек-лист): повторы при 429/502–504 через tenacity ниже; отдельный circuit breaker
(например по счётчику ошибок в Redis) имеет смысл при высокой нагрузке на геокодер.
"""

import json
import logging
import math
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

# Радиус Земли в км (приблизительно)
EARTH_RADIUS_KM = 6371.0


def _validate_yandex_geocode_response(data) -> bool:
    """Проверка минимальной структуры ответа Geocoder API 1.x."""
    if not isinstance(data, dict):
        return False
    if data.get("status") == "error":
        return False
    err = data.get("error")
    if err is not None and err != "":
        return False
    resp = data.get("response")
    if not isinstance(resp, dict):
        return False
    col = resp.get("GeoObjectCollection")
    return isinstance(col, dict)


def _geocode_error_retryable(exc: BaseException) -> bool:
    if isinstance(exc, urllib.error.HTTPError):
        return exc.code in (429, 502, 503, 504)
    if isinstance(exc, urllib.error.URLError):
        return not isinstance(exc, urllib.error.HTTPError)
    return isinstance(exc, (TimeoutError, OSError))


@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.3, min=0.3, max=4),
    retry=retry_if_exception(_geocode_error_retryable),
)
def _fetch_geocode_body(full_url: str, timeout: float) -> bytes:
    req = urllib.request.Request(full_url)
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310 — URL только https из кода
        return resp.read()


def _request_geocode(geocode_param):
    """
    Запрос к Yandex Geocoder API (1.x).
    Возвращает сырой JSON или None при ошибке.
    """
    api_key = getattr(settings, "YANDEX_GEOCODER_API_KEY", "") or ""
    if not api_key:
        logger.warning("YANDEX_GEOCODER_API_KEY is not set")
        return None

    url = "https://geocode-maps.yandex.ru/v1/"
    params = {
        "apikey": api_key,
        "geocode": geocode_param,
        "format": "json",
    }
    query = urllib.parse.urlencode(params)
    full_url = f"{url}?{query}"

    if not full_url.startswith("https://"):
        logger.warning("Geocoder: only HTTPS URLs allowed")
        return None

    timeout = getattr(settings, "EXTERNAL_API_TIMEOUT", 10)
    try:
        raw = _fetch_geocode_body(full_url, float(timeout))
    except urllib.error.HTTPError as e:
        logger.warning("Yandex Geocoder HTTPError %s: %s", e.code, e.reason)
        return None
    except urllib.error.URLError as e:
        logger.warning("Yandex Geocoder URLError: %s", e.reason)
        return None
    except (TimeoutError, OSError) as e:
        logger.warning("Yandex Geocoder network error: %s", e)
        return None

    try:
        data = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.warning("Yandex Geocoder parse error: %s", e)
        return None

    if not _validate_yandex_geocode_response(data):
        logger.warning("Yandex Geocoder: invalid or unexpected JSON shape")
        return None

    return data


def geocode_address(address):
    """
    Геокодирование адреса: адрес -> (latitude, longitude).

    Returns:
        tuple[float, float] | None: (lat, lon) или None при ошибке/пустом ответе.
    """
    if not address or not str(address).strip():
        logger.warning("geocode_address: empty address")
        return None

    data = _request_geocode(str(address).strip())
    if not data:
        return None

    try:
        collection = data.get("response", {}).get("GeoObjectCollection", {})
        members = collection.get("featureMember", [])
        if not members:
            return None
        geo = members[0].get("GeoObject", {})
        point = geo.get("Point", {})
        pos = point.get("pos")
        if not pos:
            return None
        # Yandex: "pos" в формате "долгота широта" (lon lat)
        parts = pos.strip().split()
        if len(parts) < 2:
            return None
        lon, lat = float(parts[0]), float(parts[1])
        return (lat, lon)
    except (KeyError, TypeError, ValueError) as e:
        logger.warning("geocode_address parse error: %s", e)
        return None


def distance_km(lat1, lon1, lat2, lon2):
    """
    Расстояние между двумя точками (формула гаверсинусов) в км.

    Args:
        lat1, lon1: широта и долгота первой точки.
        lat2, lon2: широта и долгота второй точки.

    Returns:
        float: расстояние в километрах.
    """
    lat1_rad = math.radians(float(lat1))
    lon1_rad = math.radians(float(lon1))
    lat2_rad = math.radians(float(lat2))
    lon2_rad = math.radians(float(lon2))
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))
    return EARTH_RADIUS_KM * c


def get_nearest_stores(latitude, longitude, limit=10, only_active=True):
    """
    Поиск ближайших магазинов к точке (lat, lon).

    У магазинов без координат расстояние не вычисляется (исключаются или считаются очень далеко).
    Возвращает список словарей: [{"store": Store, "distance_km": float}, ...], отсортированный по расстоянию.

    Args:
        latitude: широта точки.
        longitude: долгота точки.
        limit: максимум магазинов в ответе.
        only_active: только магазины с is_active=True.

    Returns:
        list[dict]: [{"store": Store, "distance_km": float}, ...]
    """
    from apps.stores.models import Store

    qs = Store.objects.all()
    if only_active:
        qs = qs.filter(is_active=True)

    results = []
    for store in qs:
        if store.latitude is None or store.longitude is None:
            continue
        dist = distance_km(
            latitude,
            longitude,
            float(store.latitude),
            float(store.longitude),
        )
        results.append({"store": store, "distance_km": round(dist, 2)})

    results.sort(key=lambda x: x["distance_km"])
    return results[:limit]


def geocode_and_nearest_stores(address, limit=10):
    """
    Геокодировать адрес и вернуть ближайшие магазины.

    Returns:
        tuple[tuple[float, float] | None, list]: (lat, lon) или None, и список [{"store", "distance_km"}, ...].
    """
    coords = geocode_address(address)
    if coords is None:
        return None, []
    lat, lon = coords
    nearest = get_nearest_stores(lat, lon, limit=limit)
    return coords, nearest
