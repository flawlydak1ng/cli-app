"""Основные структуры данных: пакет."""

from typing import NamedTuple


class Package(NamedTuple):
    """Пакет: имя и версия (в тестовом репозитории версия пустая)."""

    name: str
    version: str = ""

    @property
    def key(self):
        """Ключ пакета: имена NuGet не зависят от регистра."""
        return self.name.lower()

    @property
    def label(self):
        """Подпись пакета для вывода: имя и версия."""
        return f"{self.name} {self.version}" if self.version else self.name
