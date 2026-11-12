"""Поддельный сервер NuGet для тестов без доступа к сети."""

import json

from depgraph.errors import PackageNotFoundError

INDEX_URL = "https://fake.example/v3/index.json"
BASE = "https://fake.example/flat/"

INDEX = {
    "version": "3.0.0",
    "resources": [
        {"@id": "https://fake.example/search", "@type": "SearchQueryService"},
        {"@id": BASE, "@type": "PackageBaseAddress/3.0.0"},
    ],
}


def nuspec(*dependencies, framework="net8.0"):
    """Собрать текст .nuspec с одной группой зависимостей."""
    items = "".join(
        f'<dependency id="{name}" version="{rng}"/>'
        for name, rng in dependencies
    )
    return (
        '<package xmlns="http://schemas.microsoft.com/packaging/2013/05/'
        'nuspec.xsd"><metadata><dependencies>'
        f'<group targetFramework="{framework}">{items}</group>'
        "</dependencies></metadata></package>"
    ).encode()


def make_fetch(packages):
    """Создать функцию загрузки по описанию пакетов.

    packages: {имя: {версия: [(зависимость, диапазон), ...]}}.
    Возвращаемая функция считает обращения в атрибуте calls.
    """
    files = {INDEX_URL: json.dumps(INDEX).encode()}
    for name, releases in packages.items():
        key = name.lower()
        listing = {"versions": list(releases)}
        files[f"{BASE}{key}/index.json"] = json.dumps(listing).encode()
        for version, deps in releases.items():
            files[f"{BASE}{key}/{version}/{key}.nuspec"] = nuspec(*deps)

    def fetch(url):
        """Вернуть содержимое поддельного ресурса."""
        fetch.calls.append(url)
        if url not in files:
            raise PackageNotFoundError(f"ресурс не найден: {url}")
        return files[url]

    fetch.calls = []
    return fetch
