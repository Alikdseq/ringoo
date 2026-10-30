"""
Парсер XML каталога 1С.

Подтверждённый файловый формат (integration1CandKassa/):
  <ПапкиНоменклатуры><Папка code= parentCode= name= />
  <Товары><Товар code= … sklad= skladID= series= seriesID= quantity= price= />

HTTP-ответ CatalogFolders/folders / CatalogProducts/products ещё не сверяли
с живым API. Парсер принимает и русские теги выгрузки, и иллюстративные
английские (folder/product + warehouseId/warehouseName) — без молчаливого
«угадывания» смешанных схем: неизвестные корневые теги дают понятную ошибку
только если не найдено ни одной строки.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable

import defusedxml.ElementTree as ET
from defusedxml.common import DefusedXmlException

# Папка «База» по инструкции 1С — в ответ сервиса не включается; если пришла — отбрасываем.
BASE_FOLDER_CODE = "00-00010097"

FOLDER_TAGS = frozenset({"Папка", "folder", "Folder"})
PRODUCT_TAGS = frozenset({"Товар", "product", "Product"})


class OneCParseError(ValueError):
    """Невалидный или неожиданный XML каталога 1С."""


@dataclass(frozen=True)
class OneCFolder:
    code: str
    parent_code: str
    name: str


@dataclass(frozen=True)
class OneCProductRow:
    """Одна строка выгрузки (товар × склад × опционально серия)."""

    code: str
    parent_code: str
    name: str
    type_name: str
    type_id: str
    sklad: str
    sklad_id: str
    series: str
    series_id: str
    quantity_raw: str
    price_raw: str

    @property
    def has_warehouse(self) -> bool:
        return bool(self.sklad or self.sklad_id)

    @property
    def has_series(self) -> bool:
        return bool(self.series or self.series_id)

    def parse_price(self) -> Decimal | None:
        raw = (self.price_raw or "").strip()
        if not raw:
            return None
        normalized = (
            raw.replace("\xa0", "")
            .replace(" ", "")
            .replace(",", ".")
        )
        try:
            return Decimal(normalized)
        except InvalidOperation:
            return None

    def parse_quantity(self) -> Decimal | None:
        """None = количество отсутствует (не ноль)."""
        raw = (self.quantity_raw or "").strip()
        if not raw:
            return None
        normalized = raw.replace("\xa0", "").replace(" ", "").replace(",", ".")
        try:
            return Decimal(normalized)
        except InvalidOperation:
            return None


@dataclass
class ParsedCatalog:
    folders: list[OneCFolder] = field(default_factory=list)
    product_rows: list[OneCProductRow] = field(default_factory=list)
    source_folders_path: str = ""
    source_products_path: str = ""
    parse_warnings: list[str] = field(default_factory=list)


def _attr(el: ET.Element, *keys: str) -> str:
    for key in keys:
        val = (el.get(key) or "").strip()
        if val:
            return val
    return ""


def _local_tag(el: ET.Element) -> str:
    return el.tag.split("}")[-1]


def _root_from_source(source: str | Path | bytes) -> ET.Element:
    try:
        if isinstance(source, (str, Path)) and not isinstance(source, bytes):
            path = Path(source)
            if path.is_file():
                return ET.parse(path).getroot()
            # строка XML
            text = source if isinstance(source, str) else str(source)
            if not text.strip():
                raise OneCParseError("Пустой XML")
            return ET.fromstring(text)
        if isinstance(source, bytes):
            if not source.strip():
                raise OneCParseError("Пустой XML")
            return ET.fromstring(source)
    except DefusedXmlException as exc:
        raise OneCParseError(f"Небезопасный XML отклонён: {exc}") from exc
    except ET.ParseError as exc:
        raise OneCParseError(f"Невалидный XML: {exc}") from exc
    raise OneCParseError("Неподдерживаемый источник XML")


def parse_folders_xml(source: str | Path | bytes) -> list[OneCFolder]:
    """
    source — путь к файлу или XML-строка/байты (ответ HTTP).
    Исключает папку «База» (00-00010097). Дубликаты code сохраняются как есть —
    импортёр отметит конфликт.
    """
    root = _root_from_source(source)
    folders: list[OneCFolder] = []
    for el in root.iter():
        if _local_tag(el) not in FOLDER_TAGS:
            continue
        code = _attr(el, "code")
        if not code or code == BASE_FOLDER_CODE:
            continue
        parent = _attr(el, "parentCode", "parent_code")
        # Если родитель — «База», на сайте это корневая категория
        if parent == BASE_FOLDER_CODE:
            parent = ""
        folders.append(
            OneCFolder(
                code=code,
                parent_code=parent,
                name=_attr(el, "name"),
            )
        )
    return folders


def parse_products_xml(source: str | Path | bytes) -> list[OneCProductRow]:
    root = _root_from_source(source)
    rows: list[OneCProductRow] = []
    for el in root.iter():
        if _local_tag(el) not in PRODUCT_TAGS:
            continue
        code = _attr(el, "code")
        if not code:
            continue
        rows.append(
            OneCProductRow(
                code=code,
                parent_code=_attr(el, "parentCode", "parent_code"),
                name=_attr(el, "name"),
                type_name=_attr(el, "type"),
                type_id=_attr(el, "typeID", "typeId"),
                sklad=_attr(el, "sklad", "warehouseName", "warehouse"),
                sklad_id=_attr(el, "skladID", "skladId", "warehouseId"),
                series=_attr(el, "series", "seriesName"),
                series_id=_attr(el, "seriesID", "seriesId"),
                quantity_raw=_attr(el, "quantity"),
                price_raw=_attr(el, "price"),
            )
        )
    return rows


def parse_catalog_files(
    folders_path: str | Path,
    products_path: str | Path,
) -> ParsedCatalog:
    folders_path = Path(folders_path)
    products_path = Path(products_path)
    return ParsedCatalog(
        folders=parse_folders_xml(folders_path),
        product_rows=parse_products_xml(products_path),
        source_folders_path=str(folders_path.resolve()),
        source_products_path=str(products_path.resolve()),
    )


def parse_catalog_xml_strings(
    folders_xml: str,
    products_xml: str,
    *,
    source_label: str = "http",
) -> ParsedCatalog:
    folders = parse_folders_xml(folders_xml)
    products = parse_products_xml(products_xml)
    warnings: list[str] = []
    if not folders:
        warnings.append(
            "В XML категорий не найдено ни одной папки "
            f"(ожидались теги {sorted(FOLDER_TAGS)})"
        )
    if not products:
        warnings.append(
            "В XML товаров не найдено ни одной строки "
            f"(ожидались теги {sorted(PRODUCT_TAGS)})"
        )
    return ParsedCatalog(
        folders=folders,
        product_rows=products,
        source_folders_path=f"{source_label}:CatalogFolders/folders",
        source_products_path=f"{source_label}:CatalogProducts/products",
        parse_warnings=warnings,
    )


def unique_product_codes(rows: Iterable[OneCProductRow]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for row in rows:
        if row.code in seen:
            continue
        seen.add(row.code)
        ordered.append(row.code)
    return ordered
