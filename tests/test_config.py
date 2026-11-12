"""Тесты разбора и проверки параметров командной строки."""

import os
import tempfile
import unittest

from depgraph.config import (
    DEFAULT_MAX_DEPTH,
    MODE_REMOTE,
    MODE_TEST,
    ConfigError,
    parse_config,
)

NUGET_URL = "https://api.nuget.org/v3/index.json"


def remote_args(*extra):
    """Корректный набор аргументов для режима remote плюс добавки."""
    return [
        "--package", "Newtonsoft.Json",
        "--repo", NUGET_URL,
        "--package-version", "13.0.3",
        *extra,
    ]


class ValidConfigTest(unittest.TestCase):
    """Проверки корректных наборов параметров."""

    def test_remote_defaults(self):
        """Значения по умолчанию в режиме remote."""
        config = parse_config(remote_args())
        self.assertEqual(config.package, "Newtonsoft.Json")
        self.assertEqual(config.repo_mode, MODE_REMOTE)
        self.assertEqual(config.max_depth, DEFAULT_MAX_DEPTH)
        self.assertFalse(config.ascii_tree)
        self.assertEqual(config.substring, "")

    def test_all_options(self):
        """Все необязательные параметры заданы явно."""
        config = parse_config(
            remote_args("--ascii-tree", "--max-depth", "5", "--filter", "Sys")
        )
        self.assertTrue(config.ascii_tree)
        self.assertEqual(config.max_depth, 5)
        self.assertEqual(config.substring, "Sys")

    def test_test_mode_without_version(self):
        """В тестовом режиме версия не обязательна."""
        with tempfile.NamedTemporaryFile("w", suffix=".txt") as repo_file:
            config = parse_config(
                ["--package", "A", "--repo", repo_file.name,
                 "--repo-mode", MODE_TEST]
            )
        self.assertEqual(config.package_version, "")


class InvalidConfigTest(unittest.TestCase):
    """Каждый параметр проверяется на недопустимые значения."""

    def assert_error(self, args, fragment):
        """Убедиться, что разбор падает с сообщением, содержащим fragment."""
        with self.assertRaises(ConfigError) as context:
            parse_config(args)
        self.assertIn(fragment, str(context.exception))

    def test_missing_package(self):
        """Не задано имя пакета."""
        self.assert_error(["--repo", NUGET_URL], "имя пакета")

    def test_bad_package_name(self):
        """Недопустимые символы в имени пакета NuGet."""
        args = ["--package", "bad name!", "--repo", NUGET_URL,
                "--package-version", "1.0.0"]
        self.assert_error(args, "недопустимое имя")

    def test_too_long_package_name(self):
        """Слишком длинное имя пакета."""
        args = ["--package", "A" * 101, "--repo", NUGET_URL,
                "--package-version", "1.0.0"]
        self.assert_error(args, "длиннее")

    def test_test_mode_name_must_be_uppercase(self):
        """В тестовом режиме имена - заглавные латинские буквы."""
        with tempfile.NamedTemporaryFile("w") as repo_file:
            args = ["--package", "a1", "--repo", repo_file.name,
                    "--repo-mode", MODE_TEST]
            self.assert_error(args, "заглавные латинские")

    def test_bad_url(self):
        """Репозиторий в режиме remote должен быть URL."""
        args = ["--package", "X", "--repo", "not a url",
                "--package-version", "1.0"]
        self.assert_error(args, "URL")

    def test_missing_test_file(self):
        """Файл тестового репозитория не существует."""
        args = ["--package", "A", "--repo", "/no/such/file.txt",
                "--repo-mode", MODE_TEST]
        self.assert_error(args, "не найден")

    def test_directory_instead_of_file(self):
        """Вместо файла тестового репозитория передан каталог."""
        args = ["--package", "A", "--repo", os.getcwd(),
                "--repo-mode", MODE_TEST]
        self.assert_error(args, "каталог")

    def test_unknown_mode(self):
        """Неизвестный режим работы с репозиторием."""
        self.assert_error(
            remote_args("--repo-mode", "fast"), "недопустимое значение"
        )

    def test_missing_version(self):
        """В режиме remote версия обязательна."""
        args = ["--package", "X", "--repo", NUGET_URL]
        self.assert_error(args, "версия")

    def test_bad_version(self):
        """Версия не соответствует формату NuGet."""
        args = ["--package", "X", "--repo", NUGET_URL,
                "--package-version", "v1..2"]
        self.assert_error(args, "некорректная версия")

    def test_depth_not_a_number(self):
        """Глубина - не число."""
        self.assert_error(remote_args("--max-depth", "abc"), "целым числом")

    def test_depth_negative(self):
        """Глубина отрицательна."""
        self.assert_error(remote_args("--max-depth=-1"), "меньше нуля")

    def test_depth_too_large(self):
        """Глубина превышает допустимый предел."""
        self.assert_error(remote_args("--max-depth", "9999"), "больше")

    def test_filter_with_spaces(self):
        """Подстрока фильтра содержит пробел."""
        self.assert_error(remote_args("--filter", "a b"), "пробельных")

    def test_unknown_option(self):
        """Неизвестная опция командной строки."""
        self.assert_error(remote_args("--color"), "неизвестные параметры")

    def test_flag_with_value(self):
        """Флаг --ascii-tree не принимает значение."""
        self.assert_error(
            remote_args("--ascii-tree=yes"), "значение не ожидается"
        )


if __name__ == "__main__":
    unittest.main()
