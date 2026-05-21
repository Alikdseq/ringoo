"""
Обход дерева frontend/public/<Brand>/… для импорта моделей (листьев с фото).
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

from django.utils.text import slugify

from apps.products.services.public_catalog_flat import longest_common_prefix

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}

_KNOWN_COLOR_DIR_NAMES = frozenset({
    "black",
    "white",
    "blue",
    "pink",
    "gold",
    "gray",
    "grey",
    "green",
    "purple",
    "red",
    "silver",
    "graphite",
    "lavender",
    "mint",
    "navy",
    "violet",
    "charcoal",
    "natural",
    "desert",
    "orange",
    "yellow",
    "teal",
    "ultramarine",
    "starlight",
    "midnight",
    "skyblue",
    "iceblue",
    "rosegold",
    "cobaltviolet",
    "pinkgold",
})


def display_title_from_dirname(name: str) -> str:
    t = name.strip().replace("_", " ")
    t = re.sub(r"\s+", " ", t)
    return t or name


def list_images(directory: Path) -> list[Path]:
    return sorted(
        f
        for f in directory.iterdir()
        if f.is_file() and f.suffix.lower() in IMAGE_EXT and not f.name.startswith(".")
    )


def list_subdirs(directory: Path) -> list[Path]:
    return sorted(
        d for d in directory.iterdir() if d.is_dir() and not d.name.startswith(".")
    )


def _subdir_looks_like_color_folder(subdir: Path) -> bool:
    """Подпапка с именем оттенка и без «длинного» общего префикса в именах файлов."""
    imgs = list_images(subdir)
    if not imgs or list_subdirs(subdir):
        return False

    name_key = slugify(subdir.name) or subdir.name.lower()
    if name_key in _KNOWN_COLOR_DIR_NAMES:
        return True

    # «Note 15 pro», «X9D», «S25 Ultra» — вложенная модель, не цвет
    if re.search(r"\d", subdir.name):
        return False
    if re.search(r"\b(pro|plus|max|lite|ultra|air|se|go)\b", subdir.name, re.I):
        return False
    if len(subdir.name.split()) >= 2:
        return False

    stems = [f.stem for f in imgs]
    lcp = longest_common_prefix(stems)
    # Несколько фото с общим длинным префиксом модели — это вложенная модель, не цвет
    if len(imgs) >= 2 and len(lcp) >= 10:
        return False

    return len(imgs) <= 6 and len(subdir.name) <= 24


def is_model_leaf(directory: Path) -> bool:
    """Папка модели: фото в корне, colors.json или только цветовые подпапки с фото."""
    if list_images(directory) or (directory / "colors.json").is_file():
        return True

    subdirs = list_subdirs(directory)
    if not subdirs:
        return False

    if not all(list_images(sd) for sd in subdirs):
        return False

    return all(_subdir_looks_like_color_folder(sd) for sd in subdirs)


def iter_model_directories(
    brand_path: Path,
    title_prefix: str = "",
) -> Iterator[tuple[Path, str]]:
    """
    Рекурсивно находит листья-каталоги моделей.
    title_prefix — сегменты пути (Honor, Redmi, …).
    """
    if is_model_leaf(brand_path):
        title = title_prefix or display_title_from_dirname(brand_path.name)
        yield brand_path, title.strip()
        return

    for entry in list_subdirs(brand_path):
        segment = display_title_from_dirname(entry.name)
        full_title = f"{title_prefix} {segment}".strip() if title_prefix else segment

        if is_model_leaf(entry):
            yield entry, full_title
            continue

        child_subdirs = list_subdirs(entry)
        if child_subdirs and not list_images(entry):
            yield from iter_model_directories(entry, full_title)
        elif list_images(entry) or (entry / "colors.json").is_file():
            yield entry, full_title


def model_slug_from_path(model_dir: Path, brand_root: Path, category_slug: str) -> str:
    try:
        rel = model_dir.relative_to(brand_root)
    except ValueError:
        rel = Path(model_dir.name)
    parts: list[str] = []
    for part in rel.parts:
        s = slugify(part) or re.sub(r"[^a-z0-9-]+", "-", part.lower()).strip("-")
        if not s or s == category_slug:
            continue
        if parts and parts[-1] == s:
            continue
        parts.append(s)
    tail = "-".join(parts) if parts else slugify(model_dir.name) or "model"
    return f"{category_slug}-{tail}"[:220]
