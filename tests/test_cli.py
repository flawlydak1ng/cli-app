"""Тесты интерфейса командной строки."""

import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

from depgraph.cli import (
    EXIT_ERROR,
    EXIT_OK,
    EXIT_USAGE,
    format_frameworks,
    main,
)
from depgraph.nuget import NuGetRepository
from tests.fake_nuget import INDEX_URL, make_fetch

PACKAGES = {
    "Alpha": {"1.0.0": [("Beta", "1.0.0")]},
    "Beta": {"1.0.0": []},
}


def run_main(args):
    """Запустить main на поддельном NuGet, вернуть код, stdout и stderr."""
    fetch = make_fetch(PACKAGES)

    def factory(url):
        """Репозиторий с подменённой загрузкой."""
        return NuGetRepository(url, fetch)

    out, err = io.StringIO(), io.StringIO()
    with mock.patch("depgraph.cli.NuGetRepository", factory):
        with redirect_stdout(out), redirect_stderr(err):
            code = main(args)
    return code, out.getvalue(), err.getvalue()


def args_for(package, version):
    """Аргументы запуска для поддельного репозитория."""
    return ["--package", package, "--repo", INDEX_URL,
            "--package-version", version]


class MainTest(unittest.TestCase):
    """Проверки вывода зависимостей и кодов завершения."""

    def test_prints_direct_dependencies(self):
        """Печатаются прямые зависимости пакета."""
        code, out, _ = run_main(args_for("Alpha", "1.0.0"))
        self.assertEqual(code, EXIT_OK)
        self.assertIn("Прямые зависимости пакета Alpha 1.0.0 (1):", out)
        self.assertIn("Beta 1.0.0", out)

    def test_frameworks_list_is_shortened(self):
        """Длинный список платформ сокращается."""
        names = ("net6.0", "net7.0", "net8.0", "net9.0", "net10.0")
        self.assertEqual(
            format_frameworks(names[:3]), "net6.0, net7.0, net8.0"
        )
        self.assertEqual(
            format_frameworks(names), "net6.0, net7.0, net8.0 и ещё 2"
        )

    def test_package_without_dependencies(self):
        """У пакета нет зависимостей."""
        code, out, _ = run_main(args_for("Beta", "1.0.0"))
        self.assertEqual(code, EXIT_OK)
        self.assertIn("нет", out)

    def test_missing_package_is_error(self):
        """Отсутствующий пакет: сообщение в stderr, код 1."""
        code, out, err = run_main(args_for("Nope", "1.0.0"))
        self.assertEqual(code, EXIT_ERROR)
        self.assertEqual(out, "")
        self.assertIn("не найден", err)

    def test_config_error_goes_to_stderr(self):
        """Ошибка параметров печатается в stderr, код завершения 2."""
        code, out, err = run_main(["--repo", INDEX_URL])
        self.assertEqual(code, EXIT_USAGE)
        self.assertEqual(out, "")
        self.assertTrue(err.startswith("Ошибка:"))


if __name__ == "__main__":
    unittest.main()
