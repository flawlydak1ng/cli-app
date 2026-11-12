"""Получение данных о пакетах из репозитория NuGet (протокол V3)."""

import json
from http import HTTPStatus
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from depgraph.errors import PackageNotFoundError, RepositoryError
from depgraph.nuspec import parse_dependencies
from depgraph.versions import (
    lowest_match,
    parse_range,
    parse_version,
)

BASE_ADDRESS_TYPE = "PackageBaseAddress"
USER_AGENT = "depgraph/0.1 (educational project)"
TIMEOUT_SECONDS = 30


def http_get(url):
    """Скачать содержимое URL-адреса, ошибки приводятся к RepositoryError."""
    request = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return response.read()
    except HTTPError as error:
        if error.code == HTTPStatus.NOT_FOUND:
            raise PackageNotFoundError(f"ресурс не найден: {url}") from None
        raise RepositoryError(
            f"репозиторий ответил кодом {error.code} на {url}"
        ) from None
    except URLError as error:
        raise RepositoryError(
            f"не удалось подключиться к репозиторию: {error.reason}"
        ) from None
    except OSError as error:
        raise RepositoryError(f"ошибка сети: {error}") from None


def load_json(fetch, url):
    """Скачать и разобрать JSON-документ (ожидается JSON-объект)."""
    try:
        data = json.loads(fetch(url))
    except ValueError:
        raise RepositoryError(f"репозиторий вернул не JSON: {url}") from None
    if not isinstance(data, dict):
        raise RepositoryError(f"ожидался JSON-объект: {url}")
    return data


def find_base_address(index):
    """Найти в индексе службы адрес ресурса PackageBaseAddress."""
    for resource in index.get("resources", []):
        if str(resource.get("@type", "")).startswith(BASE_ADDRESS_TYPE):
            return resource["@id"].rstrip("/") + "/"
    raise RepositoryError("в индексе службы нет ресурса PackageBaseAddress")


class NuGetRepository:
    """Клиент репозитория NuGet, работающий через службу V3 index.json."""

    def __init__(self, index_url, fetch=http_get):
        """Запомнить адрес службы и функцию загрузки (её можно подменить)."""
        self._index_url = index_url
        self._fetch = fetch
        self._base_address = None
        self._versions = {}

    def base_address(self):
        """Адрес ресурса PackageBaseAddress из индекса службы."""
        if self._base_address is None:
            index = load_json(self._fetch, self._index_url)
            self._base_address = find_base_address(index)
        return self._base_address

    def versions(self, name):
        """Список всех версий пакета, имеющихся в репозитории."""
        key = name.lower()
        if key not in self._versions:
            url = f"{self.base_address()}{key}/index.json"
            try:
                data = load_json(self._fetch, url)
            except PackageNotFoundError:
                raise PackageNotFoundError(
                    f"пакет '{name}' не найден в репозитории"
                ) from None
            self._versions[key] = [
                parse_version(text) for text in data.get("versions", [])
            ]
        return self._versions[key]

    def direct_dependencies(self, name, version):
        """Прямые зависимости заданной версии пакета (список Dependency)."""
        try:
            normalized = str(parse_version(version)).lower()
        except ValueError as error:
            raise RepositoryError(str(error)) from None
        key = name.lower()
        url = f"{self.base_address()}{key}/{normalized}/{key}.nuspec"
        try:
            manifest = self._fetch(url)
        except PackageNotFoundError:
            raise PackageNotFoundError(
                f"пакет '{name}' версии {version} не найден в репозитории"
            ) from None
        return parse_dependencies(manifest)

    def resolve_version(self, name, version_range):
        """Выбрать версию зависимости: наименьшую из подходящих диапазону."""
        try:
            parsed = parse_range(version_range)
        except ValueError as error:
            raise RepositoryError(f"{name}: {error}") from None
        chosen = lowest_match(parsed, self.versions(name))
        if chosen is None:
            raise PackageNotFoundError(
                f"для '{name}' нет версии из диапазона '{version_range}'"
            )
        return str(chosen)
