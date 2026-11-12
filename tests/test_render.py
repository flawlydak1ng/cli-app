"""Тесты вывода: PlantUML и ASCII-дерево."""

import os
import unittest

from depgraph.graph import build_graph
from depgraph.model import Package
from depgraph.render import format_ascii_tree, format_plantuml
from depgraph.testrepo import FileRepository

DATA = os.path.join(os.path.dirname(__file__), "data")


def graph_of(filename, name="A", max_depth=10, substring=""):
    """Построить граф для пакета тестового репозитория."""
    repo = FileRepository.from_file(os.path.join(DATA, filename))
    return build_graph(repo.dependencies, Package(name), max_depth, substring)


class PlantUmlTest(unittest.TestCase):
    """Описание графа на языке PlantUML."""

    def test_document_structure(self):
        """Документ начинается с @startuml и заканчивается @enduml."""
        lines = format_plantuml(graph_of("simple.txt"))
        self.assertEqual(lines[0], "@startuml")
        self.assertEqual(lines[-1], "@enduml")
        self.assertIn("title Граф зависимостей пакета A", lines)

    def test_nodes_and_edges(self):
        """Каждая вершина объявлена один раз, каждое ребро - стрелка."""
        lines = format_plantuml(graph_of("simple.txt"))
        nodes = [line for line in lines if line.startswith("rectangle")]
        edges = [line for line in lines if " --> " in line]
        self.assertEqual(len(nodes), 5)
        self.assertEqual(len(edges), 5)
        self.assertIn('rectangle "A" as n0 #LightBlue', lines)
        self.assertIn("n0 --> n1", lines)

    def test_cycle_edge_is_marked(self):
        """Ребро, замыкающее цикл, рисуется красной пунктирной стрелкой."""
        lines = format_plantuml(graph_of("cycle.txt"))
        self.assertIn("n2 -[#red,dashed]-> n0 : цикл", lines)
        self.assertNotIn("n2 --> n0", lines)

    def test_frontier_node_is_highlighted(self):
        """Нераскрытая из-за глубины вершина закрашивается."""
        lines = format_plantuml(graph_of("chain.txt", max_depth=1))
        self.assertTrue(
            any(line.startswith('rectangle "B"') and "#" in line
                for line in lines)
        )

    def test_quotes_in_label_are_replaced(self):
        """Кавычки в подписи заменяются, чтобы не сломать PlantUML."""
        graph = graph_of("simple.txt")
        graph.nodes["a"] = Package('A"1', "")
        lines = format_plantuml(graph)
        self.assertIn('rectangle "A\'1" as n0 #LightBlue', lines)


class AsciiTreeTest(unittest.TestCase):
    """ASCII-дерево зависимостей."""

    def test_diamond(self):
        """Повторная вершина помечается и не раскрывается второй раз."""
        self.assertEqual(
            format_ascii_tree(graph_of("simple.txt")),
            [
                "A",
                "|-- B",
                "|   `-- D",
                "`-- C",
                "    |-- D (см. выше)",
                "    `-- E",
            ],
        )

    def test_cycle(self):
        """Возврат к вершине текущего пути помечается как цикл."""
        self.assertEqual(
            format_ascii_tree(graph_of("cycle.txt")),
            [
                "A",
                "`-- B",
                "    `-- C",
                "        |-- A (цикл)",
                "        `-- D",
            ],
        )

    def test_depth_limit_marker(self):
        """Нераскрытые из-за глубины вершины помечаются многоточием."""
        self.assertEqual(
            format_ascii_tree(graph_of("chain.txt", max_depth=2)),
            ["A", "`-- B", "    `-- C ..."],
        )

    def test_only_root(self):
        """Дерево из одного корня."""
        self.assertEqual(
            format_ascii_tree(graph_of("simple.txt", max_depth=0)), ["A ..."]
        )

    def test_output_is_ascii_art(self):
        """Ветви рисуются только символами ASCII."""
        for line in format_ascii_tree(graph_of("complex.txt")):
            branch = line.split(" ")[0]
            self.assertTrue(branch.isascii(), line)


if __name__ == "__main__":
    unittest.main()
