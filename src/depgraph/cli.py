"""Интерфейс командной строки инструмента."""

import sys

from depgraph.config import MODE_TEST, ConfigError, parse_config
from depgraph.errors import DepgraphError
from depgraph.graph import build_graph
from depgraph.model import Package
from depgraph.nuget import NuGetRepository
from depgraph.render import format_listing
from depgraph.testrepo import FileRepository
from depgraph.versions import parse_version

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_USAGE = 2


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


def run(config):
    """Выполнить анализ по параметрам и вернуть строки для вывода."""
    repository = open_repository(config)
    graph = build_graph(
        repository.dependencies,
        root_package(config),
        config.max_depth,
        config.substring,
    )
    return format_listing(graph, config.max_depth, config.substring)


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
