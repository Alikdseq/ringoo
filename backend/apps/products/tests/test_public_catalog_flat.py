"""Группировка плоских папок с фото по цвету (имена файлов)."""

from pathlib import Path

import pytest

from apps.products.services.public_catalog_flat import (
    canonical_color_slug,
    group_flat_images_by_color,
)


def test_canonical_color_slug_merges_cam():
    assert canonical_color_slug("skyblue-cam") == "skyblue"
    assert canonical_color_slug("black-cam") == "black"
    assert canonical_color_slug("titanium-black") == "titanium-black"


def test_canonical_color_slug_merges_button_full_and_iphone_prefix():
    assert canonical_color_slug("black-button-1") == "black"
    assert canonical_color_slug("natural-full-2") == "natural"
    assert canonical_color_slug("iphone-16-pro-max-desert-full-1") == "desert"
    assert canonical_color_slug("back-black") == "black"
    assert canonical_color_slug("front-pink") == "pink"
    assert canonical_color_slug("iphone-15-back-black") == "black"
    assert canonical_color_slug("iphone-13-cam-black") == "black"
    assert canonical_color_slug("iphone-13-full-1-black") == "black"
    assert canonical_color_slug("black-2") == "black"
    assert canonical_color_slug("blue-10") == "blue"


@pytest.fixture
def tmp_samsung_s25(tmp_path: Path) -> list[Path]:
    names = [
        "Samsung-S-25-Ultra-Titanium-Black-back.png",
        "Samsung-S-25-Ultra-Titanium-Black-front.png",
        "Samsung-S-25-Ultra-Titanium-Gray-back.png",
        "Samsung-S-25-Ultra-Titanium-Gray-full.png",
    ]
    out = []
    for n in names:
        p = tmp_path / n
        p.write_bytes(b"\x89PNG\r\n\x1a\n")
        out.append(p)
    return out


@pytest.fixture
def tmp_iphone16(tmp_path: Path) -> list[Path]:
    names = [
        "iphone 16 cam black.jpeg",
        "iphone 16 full 1 black.jpeg",
        "iphone 16 cam pink.jpeg",
        "iphone 16 full 1 pink.jpeg",
    ]
    out = []
    for n in names:
        p = tmp_path / n
        p.write_bytes(b"x")
        out.append(p)
    return out


def test_group_flat_samsung_multi_color(tmp_samsung_s25):
    g = group_flat_images_by_color(tmp_samsung_s25)
    assert len(g) == 2
    assert "titanium-black" in g
    assert "titanium-gray" in g
    assert len(g["titanium-black"]) == 2
    assert len(g["titanium-gray"]) == 2


def test_group_flat_iphone_multi_color(tmp_iphone16):
    g = group_flat_images_by_color(tmp_iphone16)
    assert len(g) == 2
    assert "black" in g and "pink" in g


def test_group_flat_single_file_no_groups(tmp_path):
    p = tmp_path / "only.png"
    p.write_bytes(b"x")
    g = group_flat_images_by_color([p])
    assert g == {}


def test_group_flat_single_color_multi_shots(tmp_path):
    names = [
        "Poco-X6-Black-Back.webp",
        "Poco-X6-Black-Front.webp",
        "Poco-X6-Black-Full.webp",
    ]
    files = []
    for n in names:
        p = tmp_path / n
        p.write_bytes(b"x")
        files.append(p)
    g = group_flat_images_by_color(files)
    assert len(g) == 1
    assert "black" in next(iter(g))


@pytest.fixture
def tmp_realme_14(tmp_path: Path) -> list[Path]:
    names = [
        "Realme-14-Graphite-Full.webp",
        "Realme-14-Graphite-Back2.webp",
        "Realme-14-Blue-Front.webp",
        "Realme-14-Blue-Full.webp",
    ]
    out = []
    for n in names:
        p = tmp_path / n
        p.write_bytes(b"x")
        out.append(p)
    return out


@pytest.fixture
def tmp_xiaomi_15t(tmp_path: Path) -> list[Path]:
    names = [
        "Xiaomi-15T-RoseGold-Full.webp",
        "Xiaomi-15T-RoseGold-Back2.webp",
        "xiaomi-15-Metral-Full.webp",
        "xiaomi-15-Metral-Front.webp",
    ]
    out = []
    for n in names:
        p = tmp_path / n
        p.write_bytes(b"x")
        out.append(p)
    return out


def test_group_flat_realme_multi_color(tmp_realme_14):
    g = group_flat_images_by_color(tmp_realme_14)
    assert len(g) == 2
    assert "graphite" in g
    assert "blue" in g


def test_group_flat_xiaomi_multi_color(tmp_xiaomi_15t):
    g = group_flat_images_by_color(tmp_xiaomi_15t)
    # Разные префиксы моделей (15T vs 15) — две отдельные группы
    assert len(g) >= 2
    keys = set(g.keys())
    assert any("rosegold" in k or "rose" in k for k in keys)
    assert any("metral" in k or "metal" in k for k in keys)


def test_strip_shot_suffix_front2_full2():
    from apps.products.services.public_catalog_flat import strip_shot_suffix

    assert strip_shot_suffix("Realme-14-Graphite-Back2") == "Realme-14-Graphite"
    assert strip_shot_suffix("Tecno-Spark-Slim-White-Side") == "Tecno-Spark-Slim-White"
