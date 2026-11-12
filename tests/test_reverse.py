"""Тесты обратных зависимостей."""

import os
import unittest

from depgraph.graph import build_graph
from depgraph.model import Package
from depgraph.render import format_reverse_listing
from depgraph.reverse import reverse_neighbors
from depgraph.testrepo import FileRepository

DATA = os.path.join(os.path.dirname(__file__), "data")


def load(filename):
    """Загрузить тестовый репозиторий из tests/data."""
    return FileRepository.from_file(os.path.join(DATA, filename))


def dependents(filename, name, max_depth=10, substring=""):
    """Имена пакетов, зависящих от name, в порядке обхода DFS."""
    neighbors = reverse_neighbors(load(filename))
    graph = build_graph(neighbors, Package(name), max_depth, substring)
    return [pkg.name for key, pkg in graph.nodes.items()
            if key != graph.root.key], graph


class ReverseNeighborsTest(unittest.TestCase):
    """Обращение графа репозитория."""

    def test_direct_dependents(self):
        """Прямые «родители» пакета."""
        neighbors = reverse_neighbors(load("simple.txt"))
        self.assertEqual(neighbors(Package("D")), [Package("B"), Package("C")])
        self.assertEqual(neighbors(Package("A")), [])

    def test_unknown_package_has_no_dependents(self):
        """Для неизвестного имени соседей нет."""
        neighbors = reverse_neighbors(load("simple.txt"))
        self.assertEqual(neighbors(Package("Q")), [])


class ReverseGraphTest(unittest.TestCase):
    """Обход обращённого графа тем же алгоритмом DFS."""

    def test_transitive_dependents(self):
        """От D зависят B и C напрямую и A транзитивно."""
        names, _ = dependents("simple.txt", "D")
        self.assertEqual(names, ["B", "A", "C"])

    def test_depth_limit(self):
        """Глубина 1: только прямые зависимые пакеты."""
        names, graph = dependents("simple.txt", "D", max_depth=1)
        self.assertEqual(names, ["B", "C"])
        self.assertEqual(graph.frontier, {"b", "c"})

    def test_filter(self):
        """Пакеты с подстрокой в имени не учитываются."""
        names, _ = dependents("simple.txt", "D", substring="B")
        self.assertEqual(names, ["C", "A"])

    def test_no_dependents(self):
        """На корневой пакет репозитория никто не ссылается."""
        names, _ = dependents("simple.txt", "A")
        self.assertEqual(names, [])

    def test_cycle(self):
        """Цикл в обращённом графе обнаруживается."""
        names, graph = dependents("cycle.txt", "A")
        self.assertEqual(names, ["C", "B"])
        self.assertEqual(graph.cycles, [("b", "a")])

    def test_self_loop(self):
        """Пакет, зависящий сам от себя, - собственная обратная зависимость."""
        _, graph = dependents("self_loop.txt", "A")
        self.assertEqual(graph.cycles, [("a", "a")])


class ReverseListingTest(unittest.TestCase):
    """Текстовое представление обратных зависимостей."""

    def test_listing(self):
        """Заголовок, перечень пакетов и строки «X <- Y»."""
        _, graph = dependents("simple.txt", "D")
        lines = format_reverse_listing(graph, 10, "")
        self.assertIn("Зависят от него (3): B, A, C", lines)
        self.assertIn("D <- B, C", lines)
        self.assertIn("A (от него никто не зависит)", lines)

    def test_listing_without_dependents(self):
        """У пакета нет зависимых пакетов."""
        _, graph = dependents("simple.txt", "A")
        lines = format_reverse_listing(graph, 10, "")
        self.assertIn("Пакетов, зависящих от него, нет", lines)


if __name__ == "__main__":
    unittest.main()
