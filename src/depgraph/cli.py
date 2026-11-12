"""Интерфейс командной строки инструмента."""

import sys
from dataclasses import asdict

from depgraph.config import ConfigError, parse_config

EXIT_OK = 0
EXIT_USAGE = 2


def format_config(config):
    """Представить параметры в виде строк формата «ключ: значение»."""
    return [f"{key}: {value}" for key, value in asdict(config).items()]


def main(argv=None):
    """Запустить инструмент и вернуть код завершения процесса."""
    try:
        config = parse_config(argv)
    except ConfigError as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return EXIT_USAGE
    for line in format_config(config):
        print(line)
    return EXIT_OK
