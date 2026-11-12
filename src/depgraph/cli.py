"""Интерфейс командной строки инструмента."""

import sys

from depgraph.config import MODE_TEST, ConfigError, parse_config
from depgraph.errors import RepositoryError
from depgraph.nuget import NuGetRepository

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_USAGE = 2
MAX_SHOWN_FRAMEWORKS = 3


def format_frameworks(frameworks):
    """Сократить список целевых платформ до нескольких первых."""
    shown = ", ".join(frameworks[:MAX_SHOWN_FRAMEWORKS])
    hidden = len(frameworks) - MAX_SHOWN_FRAMEWORKS
    return f"{shown} и ещё {hidden}" if hidden > 0 else shown


def format_dependencies(package, version, dependencies):
    """Представить прямые зависимости пакета в виде строк для вывода."""
    title = f"Прямые зависимости пакета {package} {version}"
    if not dependencies:
        return [f"{title}: нет"]
    lines = [f"{title} ({len(dependencies)}):"]
    for dep in dependencies:
        lines.append(
            f"  {dep.name} {dep.version_range or '*'}"
            f"  [платформы: {format_frameworks(dep.frameworks)}]"
        )
    return lines


def run(config):
    """Выполнить анализ по параметрам и вернуть строки для вывода."""
    if config.repo_mode == MODE_TEST:
        raise RepositoryError("тестовый режим пока не поддерживается")
    repository = NuGetRepository(config.repo)
    dependencies = repository.direct_dependencies(
        config.package, config.package_version
    )
    return format_dependencies(
        config.package, config.package_version, dependencies
    )


def main(argv=None):
    """Запустить инструмент и вернуть код завершения процесса."""
    try:
        config = parse_config(argv)
    except ConfigError as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return EXIT_USAGE
    try:
        lines = run(config)
    except RepositoryError as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return EXIT_ERROR
    for line in lines:
        print(line)
    return EXIT_OK
