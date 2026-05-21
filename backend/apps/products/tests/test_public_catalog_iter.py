"""Обход дерева public/<Brand> для импорта моделей."""

from pathlib import Path

import pytest

from apps.products.services.public_catalog_iter import iter_model_directories


@pytest.fixture
def huawei_tree(tmp_path: Path) -> Path:
    honor = tmp_path / "Honor"
    x9d = honor / "X9D"
    x9d.mkdir(parents=True)
    (x9d / "Honor-X9D-Gold-Full.webp").write_bytes(b"x")
    (x9d / "Honor-X9D-Gold-Back.webp").write_bytes(b"x")
    return tmp_path


@pytest.fixture
def xiaomi_tree(tmp_path: Path) -> Path:
    redmi = tmp_path / "Redmi"
    note = redmi / "Note 15 pro"
    note.mkdir(parents=True)
    (note / "Redmi-Note-15Pro-Blue-Full.jpeg").write_bytes(b"x")
    return tmp_path


def test_iter_huawei_nested(huawei_tree: Path):
    models = list(iter_model_directories(huawei_tree))
    assert len(models) == 1
    path, title = models[0]
    assert path.name == "X9D"
    assert "Honor" in title and "X9D" in title


def test_iter_xiaomi_nested(xiaomi_tree: Path):
    models = list(iter_model_directories(xiaomi_tree))
    assert len(models) == 1
    _, title = models[0]
    assert "Redmi" in title
    assert "Note" in title
