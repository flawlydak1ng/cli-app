"""Ошибки получения данных из репозитория."""


class RepositoryError(Exception):
    """Не удалось получить или разобрать данные репозитория."""


class PackageNotFoundError(RepositoryError):
    """Запрошенный пакет или версия отсутствуют в репозитории."""
