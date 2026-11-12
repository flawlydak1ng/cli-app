"""Тестовый репозиторий: граф зависимостей из текстового файла.

Формат файла: по строке на пакет, «ИМЯ: ЗАВИСИМОСТЬ ЗАВИСИМОСТЬ ...».
Имена пакетов - заглавные латинские буквы. Всё после «#» - комментарий.
Пакет, упомянутый только как зависимость, считается пакетом без зависимостей.
"""

import re

from depgraph.errors import PackageNotFoundError, RepositoryError
from depgraph.model import Package

NAME_RE = re.compile(r"^[A-Z]+$")
COMMENT_MARK = "#"
DEFINITION_MARK = ":"
SEPARATORS_RE = re.compile(r"[\s,]+")


def parse_line(line, number):
    """Разобрать строку файла, вернуть (имя, [зависимости]) или None."""
    text = line.split(COMMENT_MARK, 1)[0].strip()
    if not text:
        return None
    name, mark, rest = text.partition(DEFINITION_MARK)
    name = name.strip()
    if not mark:
        raise RepositoryError(
            f"строка {number}: ожидалось «ИМЯ: зависимости», найдено '{text}'"
        )
    dependencies = [item for item in SEPARATORS_RE.split(rest) if item]
    for item in [name, *dependencies]:
        if not NAME_RE.match(item):
            raise RepositoryError(
                f"строка {number}: '{item}' - имя пакета должно состоять "
                "из заглавных латинских букв"
            )
    return name, list(dict.fromkeys(dependencies))


def parse_repository(text):
    """Разобрать содержимое файла в словарь «имя -> зависимости»."""
    graph = {}
    for number, line in enumerate(text.splitlines(), start=1):
        parsed = parse_line(line, number)
        if parsed is None:
            continue
        name, dependencies = parsed
        if name in graph:
            raise RepositoryError(f"строка {number}: пакет {name} уже описан")
        graph[name] = dependencies
    for dependencies in list(graph.values()):
        for item in dependencies:
            graph.setdefault(item, [])
    return graph


class FileRepository:
    """Репозиторий, описанный файлом: имена пакетов - заглавные буквы."""

    def __init__(self, graph):
        """Создать репозиторий из словаря «имя -> список зависимостей»."""
        self._graph = graph

    @classmethod
    def from_file(cls, path):
        """Прочитать репозиторий из файла."""
        try:
            with open(path, encoding="utf-8") as source:
                text = source.read()
        except (OSError, UnicodeDecodeError) as error:
            raise RepositoryError(
                f"не удалось прочитать файл '{path}': {error}"
            ) from None
        return cls(parse_repository(text))

    def package_names(self):
        """Имена всех пакетов репозитория в порядке описания."""
        return list(self._graph)

    def dependencies(self, package):
        """Прямые зависимости пакета (список Package)."""
        if package.name not in self._graph:
            raise PackageNotFoundError(
                f"пакет '{package.name}' не найден в тестовом репозитории"
            )
        return [Package(name) for name in self._graph[package.name]]
