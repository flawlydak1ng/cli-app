"""Тесты интерфейса командной строки."""

import io
import os
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

from depgraph.cli import EXIT_ERROR, EXIT_OK, EXIT_USAGE, main
from depgraph.nuget import NuGetRepository
from tests.fake_nuget import INDEX_URL, make_fetch

DATA = os.path.join(os.path.dirname(__file__), "data")

PACKAGES = {
    "Alpha": {"1.0.0": [("Beta", "1.0"), ("Gamma", "[2.0,3.0)")]},
    "Beta": {"1.0.0": [("Gamma", "2.5.0")], "1.2.0": []},
    "Gamma": {"2.1.0": [], "2.5.0": []},
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


def remote_args(package, version, *extra):
    """Аргументы запуска для поддельного репозитория."""
    return ["--package", package, "--repo", INDEX_URL,
            "--package-version", version, *extra]


def test_args(package, filename, *extra):
    """Аргументы запуска в тестовом режиме."""
    return ["--package", package, "--repo", os.path.join(DATA, filename),
            "--repo-mode", "test", *extra]


class RemoteModeTest(unittest.TestCase):
    """Режим remote на поддельном сервере NuGet."""

    def test_transitive_graph_as_plantuml(self):
        """Граф строится с учётом транзитивности и описывается на PlantUML.

        У вершины берётся версия, которая встретилась при обходе первой:
        Gamma впервые запрошена из Beta как 2.5.0.
        """
        code, out, _ = run_main(remote_args("Alpha", "1.0"))
        lines = out.splitlines()
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(lines[0], "@startuml")
        self.assertEqual(lines[-1], "@enduml")
        self.assertIn('rectangle "Alpha 1.0.0" as n0 #LightBlue', lines)
        self.assertIn('rectangle "Gamma 2.5.0" as n2', lines)
        self.assertIn("n0 --> n1", lines)
        self.assertIn("n1 --> n2", lines)
        self.assertIn("n0 --> n2", lines)

    def test_ascii_tree_on_request(self):
        """Параметр --ascii-tree добавляет дерево после описания PlantUML."""
        _, out, _ = run_main(remote_args("Alpha", "1.0.0", "--ascii-tree"))
        head, _, tree = out.partition("ASCII-дерево зависимостей:\n")
        self.assertTrue(head.rstrip().endswith("@enduml"))
        self.assertIn("Alpha 1.0.0\n|-- Beta 1.0.0", tree)
        self.assertIn("`-- Gamma 2.5.0", tree)

    def test_no_tree_by_default(self):
        """Без --ascii-tree дерево не печатается."""
        _, out, _ = run_main(remote_args("Alpha", "1.0.0"))
        self.assertNotIn("ASCII", out)

    def test_filter_removes_package(self):
        """Подстрока фильтрации исключает пакет из анализа."""
        code, out, _ = run_main(
            remote_args("Alpha", "1.0.0", "--filter", "gam")
        )
        self.assertEqual(code, EXIT_OK)
        self.assertNotIn("Gamma", out)

    def test_missing_package_is_error(self):
        """Отсутствующий пакет: сообщение в stderr, код 1."""
        code, out, err = run_main(remote_args("Nope", "1.0.0"))
        self.assertEqual(code, EXIT_ERROR)
        self.assertEqual(out, "")
        self.assertIn("не найден", err)

    def test_config_error_goes_to_stderr(self):
        """Ошибка параметров печатается в stderr, код завершения 2."""
        code, out, err = run_main(["--repo", INDEX_URL])
        self.assertEqual(code, EXIT_USAGE)
        self.assertEqual(out, "")
        self.assertTrue(err.startswith("Ошибка:"))


class TestModeTest(unittest.TestCase):
    """Режим test: граф из файла с пакетами A, B, C, ..."""

    def test_diamond(self):
        """Граф-ромб без циклов."""
        code, out, _ = run_main(test_args("A", "simple.txt"))
        lines = out.splitlines()
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(len([ln for ln in lines if ln.startswith("rect")]), 5)
        self.assertIn("n0 --> n1", lines)
        self.assertNotIn("цикл", out)

    def test_cycle_is_reported(self):
        """Циклическая зависимость обнаруживается и не зацикливает обход."""
        code, out, _ = run_main(test_args("A", "cycle.txt"))
        self.assertEqual(code, EXIT_OK)
        self.assertIn("n2 -[#red,dashed]-> n0 : цикл", out)

    def test_depth_limit(self):
        """Глубина ограничивает граф."""
        _, out, _ = run_main(test_args("A", "chain.txt", "--max-depth", "2"))
        self.assertIn('rectangle "C" as n2', out)
        self.assertNotIn('"D"', out)

    def test_filter(self):
        """Фильтр исключает пакеты по подстроке."""
        _, out, _ = run_main(test_args("A", "simple.txt", "--filter", "D"))
        self.assertNotIn('"D"', out)
        self.assertIn('"E"', out)

    def test_root_missing_in_file(self):
        """Корневого пакета нет в файле."""
        code, _, err = run_main(test_args("Z", "simple.txt"))
        self.assertEqual(code, EXIT_ERROR)
        self.assertIn("не найден в тестовом репозитории", err)

    def test_root_excluded(self):
        """Корневой пакет исключён фильтром."""
        code, _, err = run_main(test_args("A", "simple.txt", "--filter", "A"))
        self.assertEqual(code, EXIT_ERROR)
        self.assertIn("исключён", err)


class ReverseModeTest(unittest.TestCase):
    """Режим --reverse в тестовом репозитории."""

    def test_reverse_dependencies(self):
        """Печатаются пакеты, зависящие от заданного."""
        code, out, _ = run_main(test_args("D", "simple.txt", "--reverse"))
        self.assertEqual(code, EXIT_OK)
        self.assertIn("Обратные зависимости пакета D", out)
        self.assertIn("D <- B, C", out)

    def test_reverse_ascii_tree(self):
        """Для обратных зависимостей тоже печатается ASCII-дерево."""
        args = test_args("D", "simple.txt", "--reverse", "--ascii-tree")
        _, out, _ = run_main(args)
        tree = out.partition("ASCII-дерево обратных зависимостей:\n")[2]
        self.assertEqual(
            tree.splitlines(),
            ["D", "|-- B", "|   `-- A", "`-- C", "    `-- A (см. выше)"],
        )

    def test_reverse_unknown_package(self):
        """Заданного пакета нет в файле."""
        code, _, err = run_main(test_args("Z", "simple.txt", "--reverse"))
        self.assertEqual(code, EXIT_ERROR)
        self.assertIn("не найден в тестовом репозитории", err)

    def test_reverse_excluded_root(self):
        """Заданный пакет исключён подстрокой фильтрации."""
        args = test_args("D", "simple.txt", "--reverse", "--filter", "D")
        code, _, err = run_main(args)
        self.assertEqual(code, EXIT_ERROR)
        self.assertIn("исключён", err)

    def test_reverse_requires_test_mode(self):
        """В режиме remote --reverse - ошибка параметров."""
        code, _, err = run_main(remote_args("Alpha", "1.0.0", "--reverse"))
        self.assertEqual(code, EXIT_USAGE)
        self.assertIn("--reverse работает только", err)


if __name__ == "__main__":
    unittest.main()
