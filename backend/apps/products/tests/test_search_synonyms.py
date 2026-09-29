from apps.products.search_synonyms import get_search_terms


def test_samsung_russian():
    terms = get_search_terms("самсунг s26")
    assert "samsung" in [t.lower() for t in terms]


def test_xiaomi_typos():
    terms = get_search_terms("ксиаоми")
    lowered = [t.lower() for t in terms]
    assert "xiaomi" in lowered


def test_redmi_maps_xiaomi():
    terms = get_search_terms("редми note")
    assert "xiaomi" in [t.lower() for t in terms]


def test_iphone_russian():
    terms = get_search_terms("айфон 16")
    assert "iphone" in [t.lower() for t in terms]
