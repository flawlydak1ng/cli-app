"""Тесты интерфейса командной строки."""

import io
import unittest
from contextlib import redirect_stderr, redirect_stdout

from depgraph.cli import EXIT_OK, EXIT_USAGE, main

NUGET_URL = "https://api.nuget.org/v3/index.json"


def run_main(args):
    """Запустить main и вернуть код, stdout и stderr."""
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(args)
    return code, out.getvalue(), err.getvalue()


class MainTest(unittest.TestCase):
    """Проверки вывода параметров и кодов завершения."""

    def test_prints_key_value_pairs(self):
        """Параметры печатаются в формате «ключ: значение»."""
        code, out, _ = run_main(
            ["--package", "Serilog", "--repo", NUGET_URL,
             "--package-version", "3.1.1", "--max-depth", "2"]
        )
        self.assertEqual(code, EXIT_OK)
        self.assertIn("package: Serilog", out)
        self.assertIn("repo: " + NUGET_URL, out)
        self.assertIn("repo_mode: remote", out)
        self.assertIn("package_version: 3.1.1", out)
        self.assertIn("ascii_tree: False", out)
        self.assertIn("max_depth: 2", out)
        self.assertIn("substring: ", out)

    def test_error_goes_to_stderr(self):
        """Ошибка параметров печатается в stderr, код завершения 2."""
        code, out, err = run_main(["--repo", NUGET_URL])
        self.assertEqual(code, EXIT_USAGE)
        self.assertEqual(out, "")
        self.assertTrue(err.startswith("Ошибка:"))


if __name__ == "__main__":
    unittest.main()
