"""
Синонимы для поиска: русские названия брендов, опечатки и латиница.
Используется в каталоге, автодополнении и фильтре brand.
"""

from __future__ import annotations

# Каноническое слово (латиница / как в каталоге) → варианты ввода на русском и опечатки
BRAND_SEARCH_ALIASES: dict[str, list[str]] = {
    "iphone": [
        "айфон",
        "айфоны",
        "айфон",
        "ифон",
        "ифоны",
        "эпл",
        "эппл",
        "apple",
        "апл",
        "аппл",
    ],
    "samsung": [
        "самсунг",
        "самсун",
        "самс",
        "самсунг",
        "galaxy",
        "галакси",
        "галакси",
    ],
    "xiaomi": [
        "ксиоми",
        "ксиаоми",
        "сиоми",
        "сяоми",
        "шаоми",
        "ксaоми",
        "redmi",
        "редми",
        "редми",
        "poco",
        "поко",
        "поко",
    ],
    "huawei": [
        "хуавей",
        "хуавэй",
        "хуавеи",
        "хуавэй",
        "хуавей",
        "huawei",
        "honor",
        "хонор",
        "хонор",
    ],
    "tecno": [
        "текно",
        "тэкно",
        "техно",
    ],
    "infinix": [
        "инфиникс",
        "инфиник",
        "инфиникс",
    ],
    "realme": [
        "риалми",
        "реалми",
        "реалме",
        "realme",
    ],
    "dyson": ["дайсон", "дасон"],
    "macbook": ["макбук", "мак бук", "мак-бук", "макбук"],
}

# Пары «как ищут ↔ как в названии товара»
SEARCH_SYNONYM_PAIRS: list[tuple[str, str]] = [
    ("доска", "table"),
    ("стол", "table"),
    ("планшет", "tablet"),
]

# Разворачиваем BRAND_SEARCH_ALIASES в пары для обратного поиска
for _canonical, _variants in BRAND_SEARCH_ALIASES.items():
    for _v in _variants:
        SEARCH_SYNONYM_PAIRS.append((_v, _canonical))
    SEARCH_SYNONYM_PAIRS.append((_canonical, _canonical))


def get_search_terms(raw: str) -> list[str]:
    """
    Исходная строка + синонимы (в обе стороны) для icontains по title/sku/description.
    """
    if not raw:
        return []
    base = raw.strip()
    if not base:
        return []
    seen = {base.lower()}
    terms = [base]
    lower = base.lower()

    for a, b in SEARCH_SYNONYM_PAIRS:
        a_l, b_l = a.lower(), b.lower()
        if len(a_l) < 2 or len(b_l) < 2:
            continue
        if a_l in lower:
            if b_l not in seen:
                seen.add(b_l)
                terms.append(b)
        if b_l in lower:
            if a_l not in seen:
                seen.add(a_l)
                terms.append(a)

    # Отдельные токены запроса (например «samsung s26»)
    for token in lower.split():
        if len(token) < 2:
            continue
        for canonical, variants in BRAND_SEARCH_ALIASES.items():
            if token == canonical or token in variants:
                if canonical not in seen:
                    seen.add(canonical)
                    terms.append(canonical)
                for v in variants:
                    if v not in seen:
                        seen.add(v)
                        terms.append(v)

    return terms
