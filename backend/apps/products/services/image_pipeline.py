"""
Конвертация изображений товара: RGB на белом фоне, выход WebP (легче для сети).
"""

from __future__ import annotations

from io import BytesIO

from PIL import Image

ALLOWED_IMAGE_FORMATS = frozenset({"JPEG", "PNG", "WEBP", "GIF", "BMP"})
MAX_IMAGE_PIXELS = 25_000_000


def validate_image_bytes(raw: bytes) -> None:
    """Проверка magic bytes и размера до обработки."""
    if not raw or len(raw) < 12:
        raise ValueError("empty or too small image")
    im = Image.open(BytesIO(raw))
    im.load()
    fmt = (im.format or "").upper()
    if fmt not in ALLOWED_IMAGE_FORMATS:
        raise ValueError(f"unsupported image format: {fmt}")
    w, h = im.size
    if w * h > MAX_IMAGE_PIXELS:
        raise ValueError("image too large")


def bytes_to_webp_on_white(
    raw: bytes,
    *,
    quality: int = 85,
    method: int = 4,
) -> bytes:
    """
    Принимает произвольное растровое изображение (JPEG/PNG/WebP и т.д.).
    RGBA/P — композиция на белый #FFFFFF, затем сохранение как WebP.
    """
    validate_image_bytes(raw)
    im = Image.open(BytesIO(raw))
    im = _to_rgb_white_background(im)
    out = BytesIO()
    im.save(out, format="WEBP", quality=quality, method=method)
    return out.getvalue()


def _to_rgb_white_background(im: Image.Image) -> Image.Image:
    if im.mode in ("RGBA", "LA"):
        bg = Image.new("RGB", im.size, (255, 255, 255))
        alpha = im.split()[-1]
        bg.paste(im.convert("RGBA"), mask=alpha)
        return bg
    if im.mode == "P":
        im = im.convert("RGBA")
        return _to_rgb_white_background(im)
    if im.mode != "RGB":
        return im.convert("RGB")
    return im
