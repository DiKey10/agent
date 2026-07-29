"""Cache adresowany trescia.

Kazdy krok pipeline'u (pobranie, transkrypcja, ekstrakcja) zapisuje wynik pod
kluczem zbudowanym z shortcode'u rolki i nazwy kroku. Dzieki temu ponowne
przetworzenie tego samego linku nic nie kosztuje - ani czasu, ani tokenow.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class Cache:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, namespace: str, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]
        directory = self.root / namespace
        directory.mkdir(parents=True, exist_ok=True)
        return directory / f"{digest}.json"

    def get(self, namespace: str, key: str) -> Any | None:
        path = self._path(namespace, key)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            # Uszkodzony wpis traktujemy jak brak wpisu.
            path.unlink(missing_ok=True)
            return None

    def set(self, namespace: str, key: str, value: Any) -> None:
        path = self._path(namespace, key)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)

    def clear(self, namespace: str | None = None) -> int:
        target = self.root / namespace if namespace else self.root
        if not target.exists():
            return 0
        removed = 0
        for path in target.rglob("*.json"):
            path.unlink()
            removed += 1
        return removed
