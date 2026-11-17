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

# Product.price: max_digits=12, decimal_places=2. Остаток — целое до PositiveIntegerField.
MONEY_QUANT = Decimal("0.01")
MONEY_MAX = Decimal("9999999999.99")
QTY_MAX = Decimal("2147483647")
from pathlib import Path
from typing import Iterable

import defusedxml.ElementTree as ET
from defusedxml.common import DefusedXmlException

# Папка «База» по инструкции 1С — в ответ сервиса не включается; если пришла — отбрасываем.
BASE_FOLDER_CODE = "00-00010097"

FOLDER_TAGS = frozenset({"Папка", "folder", "Folder"})
PRODUCT_TAGS = frozenset({"Товар", "product", "Product"})

# Разделители тысяч в выгрузках 1С (не десятичные).
_NUMERIC_SPACE_CHARS = (
    "\u0020",  # ordinary space
    "\u00a0",  # NBSP
    "\u202f",  # narrow NBSP
    "\u2007",  # figure space
    "\u2009",  # thin space
)


class OneCParseError(ValueError):
    """Невалидный или неожиданный XML каталога 1С."""


def _validate_thousand_groups(int_part: str, thousand_sep: str) -> str:
    """
    Проверяет группировку тысяч и возвращает только цифры целой части.
    Первая группа: 1–3 цифры; последующие: ровно 3.
    """
    if thousand_sep not in int_part:
        if not int_part.isdigit():
            raise ValueError("invalid integer digits")
        return int_part
    parts = int_part.split(thousand_sep)
    if any(p == "" for p in parts):
        raise ValueError("empty thousand group")
    if not parts[0].isdigit() or not (1 <= len(parts[0]) <= 3):
        raise ValueError("invalid leading thousand group")
    for part in parts[1:]:
        if not part.isdigit() or len(part) != 3:
            raise ValueError("invalid thousand group")
    return "".join(parts)


def _normalize_numeric_text(raw: str | None) -> str:
    """
    Нормализует числовой текст 1С к строке для Decimal (десятичная точка).

    Контракт выгрузки: разделители тысяч — Unicode/обычные пробелы из
    _NUMERIC_SPACE_CHARS; одиночная '.' или ',' после удаления пробелов —
    десятичный разделитель (как в quantity='1.000', price='36990.00').

    Пустая строка → ''. Некорректное/неоднозначное → ValueError.
    Не использует float. Не удаляет точки/запятые безусловно.
    """
    if raw is None:
        return ""
    text = str(raw).strip()
    if not text:
        return ""

    for space in _NUMERIC_SPACE_CHARS:
        text = text.replace(space, "")
    if any(ch.isspace() for ch in text):
        raise ValueError("unsupported whitespace in numeric text")

    sign = ""
    if text[0] in "+-":
        if text[0] == "+":
            raise ValueError("leading plus not allowed")
        sign = "-"
        text = text[1:]
    if not text:
        raise ValueError("sign without digits")

    if any(ch not in "0123456789.," for ch in text):
        raise ValueError("invalid numeric characters")

    has_dot = "." in text
    has_comma = "," in text

    if has_dot and has_comma:
        last_dot = text.rfind(".")
        last_comma = text.rfind(",")
        if last_dot > last_comma:
            decimal_sep, thousand_sep = ".", ","
        else:
            decimal_sep, thousand_sep = ",", "."
        if text.count(decimal_sep) != 1:
            raise ValueError("multiple decimal separators")
        int_part, frac_part = text.split(decimal_sep)
        if not frac_part.isdigit() or not frac_part:
            raise ValueError("invalid fractional part")
        int_digits = _validate_thousand_groups(int_part, thousand_sep)
        if not int_digits:
            raise ValueError("missing integer digits")
        return f"{sign}{int_digits}.{frac_part}"

    sep = "." if has_dot else ("," if has_comma else None)
    if sep is None:
        if not text.isdigit():
            raise ValueError("invalid integer")
        return f"{sign}{text}"

    parts = text.split(sep)
    if any(part == "" for part in parts):
        raise ValueError("empty numeric segment")
    if not all(part.isdigit() for part in parts):
        raise ValueError("non-digit numeric segment")

    if len(parts) == 1:
        return f"{sign}{parts[0]}"

    if len(parts) == 2:
        # Один разделитель = десятичный (тысячи уже сняты пробелами).
        int_part, frac_part = parts
        if not int_part:
            raise ValueError("missing integer digits")
        return f"{sign}{int_part}.{frac_part}"

    # Повтор одного разделителя: либо тысячи+дробь, либо только тысячи.
    last = parts[-1]
    head = parts[:-1]
    if len(last) != 3:
        int_digits = _validate_thousand_groups(sep.join(head), sep)
        return f"{sign}{int_digits}.{last}"

    # Все группы после первой длины 3 → целое с разрядами тысяч (напр. 1.000.000).
    if not (1 <= len(parts[0]) <= 3):
        raise ValueError("invalid leading thousand group")
    for part in parts[1:]:
        if len(part) != 3:
            raise ValueError("invalid thousand group")
    return f"{sign}{''.join(parts)}"


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
        try:
            normalized = _normalize_numeric_text(raw)
        except ValueError:
            return None
        if not normalized:
            return None
        try:
            return Decimal(normalized)
        except InvalidOperation:
            return None

    def parse_quantity(self) -> Decimal | None:
        """None = количество отсутствует или не число (не ноль)."""
        raw = (self.quantity_raw or "").strip()
        if not raw:
            return None
        try:
            normalized = _normalize_numeric_text(raw)
        except ValueError:
            return None
        if not normalized:
            return None
        try:
            return Decimal(normalized)
        except InvalidOperation:
            return None

    def price_problem(self) -> str | None:
        """
        None — цену можно писать. Иначе код причины, исходная строка не меняется.
        Пустая цена — empty (это не отрицательное число).
        """
        raw = (self.price_raw or "").strip()
        if not raw:
            return "empty"
        value = self.parse_price()
        if value is None or not value.is_finite():
            return "not_a_number"
        if value < 0:
            return "negative"
        if value > MONEY_MAX:
            return "overflow"
        try:
            if value != value.quantize(MONEY_QUANT):
                return "precision"
        except InvalidOperation:
            return "overflow"
        return None

    def quantity_problem(self) -> str | None:
        """
        None — целое количество от 0 до предела поля.
        Ноль допустим. Дробь, минус и переполнение — нет.
        """
        raw = (self.quantity_raw or "").strip()
        if not raw:
            return "empty"
        value = self.parse_quantity()
        if value is None or not value.is_finite():
            return "not_a_number"
        if value < 0:
            return "negative"
        if value > QTY_MAX:
            return "overflow"
        if value != value.to_integral_value():
            return "not_integer"
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


def _looks_like_xml_text(text: str) -> bool:
    """True if string is an XML document payload, not a filesystem path."""
    return text.lstrip("\ufeff \t\r\n").startswith("<")


def _root_from_source(source: str | Path | bytes) -> ET.Element:
    """
    source: XML string (e.g. HTTP body), filesystem path (str|Path), or bytes.
    XML strings must be detected before Path(...).is_file() — a large XML
    payload as a Path name raises OSError Errno 36 (File name too long).
    """
    try:
        if isinstance(source, bytes):
            if not source.strip():
                raise OneCParseError("Пустой XML")
            return ET.fromstring(source)

        if isinstance(source, Path):
            if not source.is_file():
                raise OneCParseError(f"XML-файл не найден: {source}")
            return ET.parse(source).getroot()

        if isinstance(source, str):
            if not source.strip():
                raise OneCParseError("Пустой XML")
            # HTTP API / in-memory XML: never pass the whole body to Path().
            if _looks_like_xml_text(source):
                # Strip BOM/leading whitespace so <?xml ...?> is at the start.
                return ET.fromstring(source.lstrip("\ufeff \t\r\n"))
            path = Path(source)
            try:
                is_file = path.is_file()
            except OSError as exc:
                raise OneCParseError(
                    f"Не удалось открыть источник XML как файл: {exc}"
                ) from exc
            if is_file:
                return ET.parse(path).getroot()
            raise OneCParseError(f"XML-файл не найден: {source}")

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
    """
    Разбор XML с диска. ONEC-026: пустые обязательные деревья → parse_warnings
    (как у HTTP-строк), чтобы plan_from_parsed не планировал mass-zero.
    """
    folders_path = Path(folders_path)
    products_path = Path(products_path)
    folders = parse_folders_xml(folders_path)
    products = parse_products_xml(products_path)
    warnings: list[str] = []
    if not folders:
        warnings.append("В XML категорий не найдено ни одной папки " f"(ожидались теги {sorted(FOLDER_TAGS)})")
    if not products:
        warnings.append("В XML товаров не найдено ни одной строки " f"(ожидались теги {sorted(PRODUCT_TAGS)})")
    return ParsedCatalog(
        folders=folders,
        product_rows=products,
        source_folders_path=str(folders_path.resolve()),
        source_products_path=str(products_path.resolve()),
        parse_warnings=warnings,
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
        warnings.append("В XML категорий не найдено ни одной папки " f"(ожидались теги {sorted(FOLDER_TAGS)})")
    if not products:
        warnings.append("В XML товаров не найдено ни одной строки " f"(ожидались теги {sorted(PRODUCT_TAGS)})")
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
