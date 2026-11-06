"""Dry-run audit of 1C Товары.xml for color/variant identity (no writes)."""
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path


def main(path: str) -> int:
    root = ET.parse(path).getroot()
    items = list(root.iter("Товар"))
    if not items:
        items = [el for el in root.iter() if el.tag.endswith("Товар")]
    by_code: dict[str, list[dict]] = defaultdict(list)
    attrs_seen: set[str] = set()
    for el in items:
        attrs = {k: (v or "") for k, v in el.attrib.items()}
        attrs_seen.update(attrs.keys())
        code = attrs.get("code") or attrs.get("Code") or ""
        by_code[code].append(attrs)

    print("ITEMS", len(items))
    print("UNIQUE_CODES", len([c for c in by_code if c]))
    print("ATTRS", ",".join(sorted(attrs_seen)))
    has_char = any(
        a.lower() in ("characteristicguid", "characteristicaid", "характеристика", "charid")
        for a in attrs_seen
    )
    print("HAS_CHARACTERISTIC_ATTR", has_char)
    multi_sklad = 0
    multi_name = 0
    samples = []
    for code, rows in by_code.items():
        if not code:
            continue
        sklads = {r.get("skladID") or r.get("sklad") for r in rows}
        names = {r.get("name") for r in rows}
        if len(sklads) > 1:
            multi_sklad += 1
        if len(names) > 1:
            multi_name += 1
            if len(samples) < 5:
                samples.append((code, sorted(names)[:3], len(sklads)))
    print("CODES_ON_MULTIPLE_WAREHOUSES", multi_sklad)
    print("CODES_WITH_MULTIPLE_NAMES", multi_name)
    for s in samples:
        print("SAMPLE_MULTI_NAME", s)
    print(
        "CONCLUSION: "
        "Use Товар.code as candidate external id only after manual/owner confirmation; "
        "warehouse duplicates must not create new colors; "
        "no characteristic GUID in this XML."
    )
    return 0


if __name__ == "__main__":
    p = sys.argv[1] if len(sys.argv) > 1 else str(
        Path(__file__).resolve().parents[2]
        / "integration1CandKassa"
        / "Товары.xml"
    )
    raise SystemExit(main(p))
