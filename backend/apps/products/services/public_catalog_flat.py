"""
Разбор «плоских» папок модели: все фото в одной директории, цвет выводится из суффикса имени файла.
Поддержка стиля Samsung (общий префикс + Titanium-Color-back) и iPhone (префикс «iphone N …» + оттенок в конце).
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

from django.utils.text import slugify

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}

# Подписи и HEX для кружков (по slug оттенка)
COLOR_HEX_HINTS: dict[str, str] = {
    "black": "#1C1C1E",
    "titanium-black": "#2C2C2E",
    "titanium-gray": "#8E8E93",
    "titanium-silverblue": "#A8C8E0",
    "titanium-whitesilver": "#E8E8ED",
    "white": "#F5F5F7",
    "silver": "#C0C0C0",
    "gray": "#8E8E93",
    "grey": "#8E8E93",
    "blue": "#007AFF",
    "pink": "#F2B8C6",
    "red": "#C62828",
    "green": "#34C759",
    "purple": "#AF52DE",
    "gold": "#E6C200",
    "yellow": "#FFCC00",
    "teal": "#5AC8D0",
    "ultramarine": "#3A5BA0",
    "natural": "#D4C4B0",
    "desert": "#C4A574",
    "starlight": "#E3E3E8",
    "midnight": "#1F2933",
    "skyblue": "#5EB3E8",
    "orange": "#f97316",
    "orange-titanium": "#f97316",
    "cosmic-orange": "#f97316",
    "titanium-orange": "#f97316",
    "оранж": "#f97316",
    "оранжевый": "#f97316",
    "graphite": "#4B5563",
    "rosegold": "#E8B4B8",
    "rose-gold": "#E8B4B8",
    "lavender": "#C4B5FD",
    "iceblue": "#7DD3FC",
    "ice-blue": "#7DD3FC",
    "charcoal": "#36454F",
    "cobaltviolet": "#6D28D9",
    "cobalt-violet": "#6D28D9",
    "pinkgold": "#E8B4B8",
    "pink-gold": "#E8B4B8",
    "blackyellow": "#1C1C1E",
    "black-yellow": "#1C1C1E",
    "metral": "#9CA3AF",
    "metal": "#9CA3AF",
    "mint": "#6EE7B7",
    "navy": "#1E3A5F",
    "violet": "#7C3AED",
    "sage": "#9CAF88",
    "mistblue": "#93C5FD",
    "silvershadow": "#C0C0C0",
    "silver-shadow": "#C0C0C0",
    "default": "#A3A3A3",
}

_SHOT_SUFFIX_RE = re.compile(
    r"[-_]?(back2|front2|full2|side|back|front|full)$",
    flags=re.I,
)


def strip_shot_suffix(stem: str) -> str:
    """Убирает суффиксы кадра (-Front2, -Back, -Full, -Side) в конце имени файла."""
    s = stem
    while True:
        next_s = _SHOT_SUFFIX_RE.sub("", s).rstrip("-_")
        if next_s == s:
            break
        s = next_s
    return s


def longest_common_prefix(strings: list[str]) -> str:
    if not strings:
        return ""
    s0 = strings[0]
    for i, ch in enumerate(s0):
        for s in strings[1:]:
            if i >= len(s) or s[i] != ch:
                return s0[:i]
    return s0


def _normalize_remainder(remainder: str) -> str:
    """Из хвоста имени файла получить человекочитаемое имя оттенка."""
    r = remainder.strip(" -_")
    if not r:
        return ""
    while True:
        n = _SHOT_SUFFIX_RE.sub("", r).strip("-_ ")
        if n == r:
            break
        r = n
    # iPhone: cam / full / side + опциональные цифры
    r = re.sub(r"^(cam|full|side)\s*", "", r, flags=re.I)
    r = re.sub(r"^\d+\s*", "", r)
    r = re.sub(r"^(cam|full|side)", "", r, flags=re.I)
    r = r.strip(" -_")
    return r


def _shot_rank(filename: str) -> tuple[int, str]:
    """Порядок кадров: сначала full, затем front, затем back — для главного превью."""
    n = filename.lower()
    if "full" in n:
        return (0, filename)
    if "front" in n:
        return (1, filename)
    if "back2" in n:
        return (2, filename)
    if "back" in n:
        return (3, filename)
    return (4, filename)


def guess_hex_for_slug(slug: str) -> str | None:
    s = slug.lower()
    if s in COLOR_HEX_HINTS:
        return COLOR_HEX_HINTS[s]
    for key, hx in COLOR_HEX_HINTS.items():
        if key in s or s in key:
            return hx
    return None


_COLOR_LABEL_OVERRIDES: dict[str, str] = {
    "skyblue": "Sky Blue",
    "silvershadow": "Silver Shadow",
    "silver-shadow": "Silver Shadow",
    "cobaltviolet": "Cobalt Violet",
    "cobalt-violet": "Cobalt Violet",
    "pinkgold": "Pink Gold",
    "pink-gold": "Pink Gold",
    "iceblue": "Ice Blue",
    "rosegold": "Rose Gold",
    "lightgrey": "Light Grey",
    "graygreen": "Gray Green",
    "charcoal": "Charcoal",
}


def label_from_color_slug(slug: str) -> str:
    key = slug.lower().strip()
    if key in _COLOR_LABEL_OVERRIDES:
        return _COLOR_LABEL_OVERRIDES[key]
    return slug.replace("-", " ").replace("_", " ").strip().title() or slug


def canonical_color_slug(slug: str) -> str:
    """
    Один оттенок в каталоге: объединяет варианты съёмки и дубликаты slug.
    Примеры: black-button-1 / black-full-2 / black-cam → black;
    back-black / front-black → black; iphone-16-pro-max-desert-full-1 → desert.
    Не ломает titanium-black (суффиксы только известные «кадровые»).
    """
    if not slug or not str(slug).strip():
        return slug
    s = str(slug).strip().lower().replace(" ", "-")
    s = re.sub(r"-+", "-", s).strip("-")

    prev_outer = None
    while prev_outer != s:
        prev_outer = s
        prev = None
        while prev != s:
            prev = s
            s = re.sub(r"-button-\d+$", "", s, flags=re.I)
            s = re.sub(r"-full-\d+$", "", s, flags=re.I)
            s = re.sub(r"-full$", "", s, flags=re.I)
            s = re.sub(r"-cam(s)?$", "", s, flags=re.I)
            s = re.sub(r"-came$", "", s, flags=re.I)
            s = re.sub(r"-back2$", "", s, flags=re.I)
            s = re.sub(r"-front2$", "", s, flags=re.I)
            s = re.sub(r"-full2$", "", s, flags=re.I)
            s = re.sub(r"-back$", "", s, flags=re.I)
            s = re.sub(r"-front$", "", s, flags=re.I)
            s = re.sub(r"-side$", "", s, flags=re.I)
            s = re.sub(r"-product$", "", s, flags=re.I)
            # django / файлы: black-2, black-3 — один оттенок
            s = re.sub(r"-\d{1,2}$", "", s)
            s = s.rstrip("-_")
        s = re.sub(r"^(back|front)-", "", s, flags=re.I)
        # cam-black, full-1-black (после снятия префикса модели или в «коротком» slug)
        s = re.sub(r"^(cam|full|side)(-\d+)?-", "", s, flags=re.I)
        s = re.sub(
            r"^iphone-\d{1,2}e?(?:-(?:pro-max|pro|plus|air))*-",
            "",
            s,
            flags=re.I,
        )
        s = re.sub(r"^iphone-", "", s, flags=re.I)
        s = re.sub(r"-+", "-", s).strip("-")

    return (s or slug).lower()


def group_flat_images_by_color(files: list[Path]) -> dict[str, list[Path]]:
    """
    Группирует файлы изображений по выведенному ключу цвета (slug).
    Один файл — без группировки (пустой dict → вызывающий кладёт всё в общие).
    """
    if len(files) < 2:
        return {}

    adjusted = [(f, strip_shot_suffix(f.stem)) for f in files]
    stems_adj = [s for _, s in adjusted]
    lcp = longest_common_prefix(stems_adj)
    if len(lcp) < 4:
        lcp = ""

    groups: dict[str, list[Path]] = defaultdict(list)
    for f, s_adj in adjusted:
        rem = s_adj[len(lcp) :].lstrip("-_") if lcp and s_adj.startswith(lcp) else s_adj
        label_raw = _normalize_remainder(rem)
        if not label_raw and lcp:
            tail = lcp.rstrip("-_").split("-")[-1]
            if tail and (guess_hex_for_slug(slugify(tail) or tail) or tail.lower() in COLOR_HEX_HINTS):
                label_raw = tail
        if not label_raw:
            key = slugify(f.stem) or "variant"
        else:
            key = slugify(label_raw) or slugify(f.stem) or "variant"
        # Серия Samsung «Titanium + оттенок»: в префиксе уже есть Titanium, в остатке — только Black/Gray…
        if (
            key
            and "titanium" in lcp.lower()
            and not label_raw.lower().startswith("titanium")
            and not key.startswith("titanium-")
        ):
            key = f"titanium-{key}"
        key = canonical_color_slug(key)
        groups[key].append(f)

    if not groups:
        return {}

    sorted_groups: dict[str, list[Path]] = {}
    for key, lst in groups.items():
        sorted_groups[key] = sorted(lst, key=lambda p: _shot_rank(p.name))

    if len(sorted_groups) == 1:
        only_key = next(iter(sorted_groups))
        # Один оттенок, несколько кадров — всё равно привязываем к ProductColor.
        if not only_key or only_key == "variant":
            return {}
        return sorted_groups

    return sorted_groups
