"""Параметры командной строки: разбор и проверка."""

import argparse
import os
import re
from dataclasses import dataclass
from urllib.parse import urlparse

from depgraph.versions import parse_version

MODE_REMOTE = "remote"
MODE_TEST = "test"
REPO_MODES = (MODE_REMOTE, MODE_TEST)
URL_SCHEMES = ("http", "https")
DEFAULT_MAX_DEPTH = 3
MAX_ALLOWED_DEPTH = 500
MAX_ID_LENGTH = 100

NUGET_ID_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.\-]*$")
TEST_NAME_RE = re.compile(r"^[A-Z]+$")
BLANK_RE = re.compile(r"\s")

ARGPARSE_MESSAGES = (
    ("unrecognized arguments:", "неизвестные параметры:"),
    ("invalid choice:", "недопустимое значение:"),
    ("(choose from", "(допустимо:"),
    ("expected one argument", "требуется значение"),
    ("ignored explicit argument", "значение не ожидается:"),
    ("argument ", "параметр "),
)


class ConfigError(Exception):
    """Ошибка в параметрах, заданных пользователем."""


@dataclass(frozen=True)
class Config:
    """Параметры работы инструмента, заданные пользователем."""

    package: str
    repo: str
    repo_mode: str
    package_version: str
    ascii_tree: bool
    max_depth: int
    substring: str


class ConfigParser(argparse.ArgumentParser):
    """Разборщик аргументов, который сообщает об ошибках исключением."""

    def error(self, message):
        """Вместо завершения процесса выбросить ConfigError по-русски."""
        for english, russian in ARGPARSE_MESSAGES:
            message = message.replace(english, russian)
        raise ConfigError(message)


def parse_max_depth(text):
    """Преобразовать значение --max-depth в целое неотрицательное число."""
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"глубина должна быть целым числом, получено '{text}'"
        ) from None
    if value < 0:
        raise argparse.ArgumentTypeError("глубина не может быть меньше нуля")
    if value > MAX_ALLOWED_DEPTH:
        raise argparse.ArgumentTypeError(
            f"глубина не может быть больше {MAX_ALLOWED_DEPTH}"
        )
    return value


def build_parser():
    """Создать разборщик опций командной строки."""
    parser = ConfigParser(
        prog="depgraph",
        description="Визуализация графа зависимостей пакетов NuGet.",
        allow_abbrev=False,
    )
    parser.add_argument("--package", help="имя анализируемого пакета")
    parser.add_argument(
        "--repo",
        help="URL-адрес репозитория NuGet или путь к файлу тестового "
        "репозитория",
    )
    parser.add_argument(
        "--repo-mode",
        choices=REPO_MODES,
        default=MODE_REMOTE,
        help="режим работы с репозиторием: remote - реальный NuGet, "
        "test - файл тестового репозитория (по умолчанию remote)",
    )
    parser.add_argument("--package-version", help="версия пакета")
    parser.add_argument(
        "--ascii-tree",
        action="store_true",
        help="вывести зависимости в формате ASCII-дерева",
    )
    parser.add_argument(
        "--max-depth",
        type=parse_max_depth,
        default=DEFAULT_MAX_DEPTH,
        help="максимальная глубина анализа зависимостей "
        f"(по умолчанию {DEFAULT_MAX_DEPTH})",
    )
    parser.add_argument(
        "--filter",
        dest="substring",
        default="",
        help="не учитывать пакеты, имя которых содержит эту подстроку",
    )
    return parser


def check_package(name, repo_mode):
    """Проверить имя пакета с учётом режима работы."""
    if not name:
        raise ConfigError("не задано имя пакета (--package)")
    if repo_mode == MODE_TEST:
        if not TEST_NAME_RE.match(name):
            raise ConfigError(
                f"в тестовом режиме имя пакета - заглавные латинские "
                f"буквы, получено '{name}'"
            )
        return
    if len(name) > MAX_ID_LENGTH:
        raise ConfigError(f"имя пакета длиннее {MAX_ID_LENGTH} символов")
    if not NUGET_ID_RE.match(name):
        raise ConfigError(f"недопустимое имя пакета NuGet '{name}'")


def check_repo(repo, repo_mode):
    """Проверить URL-адрес или путь к файлу тестового репозитория."""
    if not repo:
        raise ConfigError("не задан репозиторий (--repo)")
    if repo_mode == MODE_REMOTE:
        parts = urlparse(repo)
        if parts.scheme not in URL_SCHEMES or not parts.netloc:
            raise ConfigError(f"некорректный URL-адрес репозитория '{repo}'")
        return
    if os.path.isdir(repo):
        raise ConfigError(f"'{repo}' - каталог, а нужен файл репозитория")
    if not os.path.isfile(repo):
        raise ConfigError(f"файл тестового репозитория '{repo}' не найден")


def check_version(version, repo_mode):
    """Проверить версию пакета: в режиме remote она обязательна."""
    if version is None:
        if repo_mode == MODE_REMOTE:
            raise ConfigError("не задана версия пакета (--package-version)")
        return
    try:
        parse_version(version)
    except ValueError:
        raise ConfigError(f"некорректная версия пакета '{version}'") from None


def check_substring(substring):
    """Проверить подстроку фильтрации: пробельных символов быть не должно."""
    if BLANK_RE.search(substring):
        raise ConfigError(
            "подстрока для фильтрации не должна содержать пробельных символов"
        )


def parse_config(argv=None):
    """Разобрать и проверить аргументы, вернуть объект Config."""
    args = build_parser().parse_args(argv)
    check_package(args.package, args.repo_mode)
    check_repo(args.repo, args.repo_mode)
    check_version(args.package_version, args.repo_mode)
    check_substring(args.substring)
    return Config(
        package=args.package,
        repo=args.repo,
        repo_mode=args.repo_mode,
        package_version=args.package_version or "",
        ascii_tree=args.ascii_tree,
        max_depth=args.max_depth,
        substring=args.substring,
    )
