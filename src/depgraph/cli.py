"""Интерфейс командной строки инструмента."""

import sys

from depgraph.config import MODE_TEST, ConfigError, parse_config
from depgraph.errors import DepgraphError
from depgraph.graph import build_graph
from depgraph.model import Package
from depgraph.nuget import NuGetRepository
from depgraph.render import (
    format_ascii_tree,
    format_plantuml,
    format_reverse_listing,
)
from depgraph.reverse import reverse_neighbors
from depgraph.testrepo import FileRepository
from depgraph.versions import parse_version

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_USAGE = 2
TREE_TITLE = "ASCII-дерево зависимостей:"
REVERSE_TREE_TITLE = "ASCII-дерево обратных зависимостей:"


def open_repository(config):
    """Создать репозиторий в соответствии с режимом работы."""
    if config.repo_mode == MODE_TEST:
        return FileRepository.from_file(config.repo)
    return NuGetRepository(config.repo)


def root_package(config):
    """Корневой пакет анализа; версия приводится к нормализованному виду."""
    if not config.package_version:
        return Package(config.package)
    version = str(parse_version(config.package_version))
    return Package(config.package, version)


def add_tree(lines, graph, config, title):
    """Добавить ASCII-дерево к выводу, если задан параметр --ascii-tree."""
    if config.ascii_tree:
        lines = lines + ["", title, *format_ascii_tree(graph)]
    return lines


def run_direct(config):
    """Построить граф зависимостей пакета и описать его на PlantUML."""
    repository = open_repository(config)
    graph = build_graph(
        repository.dependencies,
        root_package(config),
        config.max_depth,
        config.substring,
    )
    return add_tree(format_plantuml(graph), graph, config, TREE_TITLE)


def run_reverse(config):
    """Найти пакеты, зависящие от заданного, тем же обходом DFS."""
    repository = open_repository(config)
    root = root_package(config)
    repository.check_package(root)
    graph = build_graph(
        reverse_neighbors(repository),
        root,
        config.max_depth,
        config.substring,
    )
    lines = format_reverse_listing(graph, config.max_depth, config.substring)
    return add_tree(lines, graph, config, REVERSE_TREE_TITLE)


def run(config):
    """Выполнить анализ по параметрам и вернуть строки для вывода."""
    if config.reverse:
        return run_reverse(config)
    return run_direct(config)


def main(argv=None):
    """Запустить инструмент и вернуть код завершения процесса."""
    try:
        config = parse_config(argv)
    except ConfigError as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return EXIT_USAGE
    try:
        lines = run(config)
    except DepgraphError as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return EXIT_ERROR
    for line in lines:
        print(line)
    return EXIT_OK
