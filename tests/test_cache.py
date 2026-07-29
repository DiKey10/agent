from app.cache import Cache


def test_roundtrip(tmp_path):
    cache = Cache(tmp_path)
    cache.set("recipe", "AbC123", {"title": "Naleśniki", "steps": [1, 2]})
    assert cache.get("recipe", "AbC123") == {"title": "Naleśniki", "steps": [1, 2]}


def test_miss_returns_none(tmp_path):
    assert Cache(tmp_path).get("recipe", "brak") is None


def test_namespaces_are_isolated(tmp_path):
    cache = Cache(tmp_path)
    cache.set("transcript", "same-key", "audio")
    cache.set("recipe", "same-key", "przepis")
    assert cache.get("transcript", "same-key") == "audio"
    assert cache.get("recipe", "same-key") == "przepis"


def test_corrupted_entry_is_treated_as_miss(tmp_path):
    cache = Cache(tmp_path)
    cache.set("recipe", "AbC123", {"ok": True})
    path = cache._path("recipe", "AbC123")
    path.write_text("{ to nie jest json", encoding="utf-8")

    assert cache.get("recipe", "AbC123") is None
    # Uszkodzony plik jest usuwany, wiec kolejny zapis dziala normalnie.
    cache.set("recipe", "AbC123", {"ok": True})
    assert cache.get("recipe", "AbC123") == {"ok": True}


def test_clear_namespace(tmp_path):
    cache = Cache(tmp_path)
    cache.set("recipe", "a", 1)
    cache.set("transcript", "b", 2)

    assert cache.clear("recipe") == 1
    assert cache.get("recipe", "a") is None
    assert cache.get("transcript", "b") == 2
