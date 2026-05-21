"""Тест пайплайна изображений: альфа → белый фон, WebP."""

from io import BytesIO

import pytest
from PIL import Image

from apps.products.services.image_pipeline import bytes_to_webp_on_white


def test_webp_on_white_from_rgba():
    im = Image.new("RGBA", (20, 20), (255, 0, 0, 128))
    buf = BytesIO()
    im.save(buf, format="PNG")
    raw = buf.getvalue()

    webp = bytes_to_webp_on_white(raw)
    out = Image.open(BytesIO(webp))
    assert out.format == "WEBP"
    assert out.mode == "RGB"
    # углы после композита на белый — не чисто красный
    assert out.getpixel((0, 0))[0] > 200
