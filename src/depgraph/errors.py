"""Ошибки инструмента."""


class DepgraphError(Exception):
    """Базовая ошибка инструмента, о которой сообщается пользователю."""


class RepositoryError(DepgraphError):
    """Не удалось получить или разобрать данные репозитория."""


class PackageNotFoundError(RepositoryError):
    """Запрошенный пакет или версия отсутствуют в репозитории."""


class RootExcludedError(DepgraphError):
    """Анализируемый пакет исключён подстрокой фильтрации."""
