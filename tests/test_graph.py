"""Тесты построения графа зависимостей обходом DFS."""

import unittest

from depgraph.errors import RootExcludedError
from depgraph.graph import build_graph
from depgraph.model import Package


def neighbors_of(table):
    """Функция соседей по словарю «имя -> список имён»."""

    def neighbors(package):
        """Зависимости пакета."""
        return [Package(name) for name in table.get(package.name, [])]

    return neighbors


def edges_of(graph):
    """Рёбра графа в виде множества пар имён."""
    return {
        (graph.nodes[parent].name, graph.nodes[child].name)
        for parent, children in graph.edges.items()
        for child in children
    }


DIAMOND = {"A": ["B", "C"], "B": ["D"], "C": ["D", "E"]}


class DepthFirstTest(unittest.TestCase):
    """Обход, глубина, фильтр и циклы."""

    def test_diamond_has_unique_nodes(self):
        """Общая зависимость D попадает в граф один раз."""
        graph = build_graph(neighbors_of(DIAMOND), Package("A"), 10)
        self.assertEqual(list(graph.nodes), ["a", "b", "d", "c", "e"])
        self.assertEqual(
            edges_of(graph),
            {("A", "B"), ("A", "C"), ("B", "D"), ("C", "D"), ("C", "E")},
        )
        self.assertEqual(graph.cycles, [])

    def test_dfs_order(self):
        """Вершины перечисляются в порядке обхода в глубину."""
        table = {"A": ["B", "C"], "B": ["D"], "D": ["E"]}
        graph = build_graph(neighbors_of(table), Package("A"), 10)
        self.assertEqual(list(graph.nodes), ["a", "b", "d", "e", "c"])

    def test_max_depth_limits_graph(self):
        """Вершины глубже предельной не раскрываются."""
        table = {"A": ["B"], "B": ["C"], "C": ["D"]}
        graph = build_graph(neighbors_of(table), Package("A"), 2)
        self.assertEqual(list(graph.nodes), ["a", "b", "c"])
        self.assertEqual(graph.frontier, {"c"})

    def test_depth_zero_is_only_root(self):
        """Глубина 0: в графе только корневой пакет."""
        graph = build_graph(neighbors_of(DIAMOND), Package("A"), 0)
        self.assertEqual(list(graph.nodes), ["a"])
        self.assertEqual(graph.edge_count(), 0)

    def test_shortcut_is_expanded_by_shortest_path(self):
        """Пакет, достижимый коротким путём, раскрывается полностью."""
        table = {"A": ["B", "C"], "B": ["C"], "C": ["D"], "D": ["E"]}
        graph = build_graph(neighbors_of(table), Package("A"), 2)
        self.assertEqual(
            edges_of(graph),
            {("A", "B"), ("A", "C"), ("B", "C"), ("C", "D")},
        )
        self.assertEqual(graph.frontier, {"d"})

    def test_filter_excludes_packages_and_their_subtrees(self):
        """Пакеты с подстрокой в имени и их зависимости не учитываются."""
        table = {"A": ["Xb", "C"], "Xb": ["D"], "C": ["E"]}
        graph = build_graph(neighbors_of(table), Package("A"), 10, "xb")
        self.assertEqual(list(graph.nodes), ["a", "c", "e"])

    def test_filter_does_not_cut_alternative_paths(self):
        """Если до пакета есть обход мимо исключённого, он остаётся."""
        table = {"A": ["Xb", "C"], "Xb": ["D"], "C": ["D"]}
        graph = build_graph(neighbors_of(table), Package("A"), 10, "Xb")
        self.assertIn("d", graph.nodes)
        self.assertEqual(edges_of(graph), {("A", "C"), ("C", "D")})

    def test_excluded_root(self):
        """Корневой пакет с подстрокой в имени - ошибка."""
        with self.assertRaises(RootExcludedError):
            build_graph(neighbors_of(DIAMOND), Package("Abc"), 3, "bc")

    def test_cycle_is_detected_and_terminates(self):
        """Цикл A -> B -> C -> A обнаруживается, обход завершается."""
        table = {"A": ["B"], "B": ["C"], "C": ["A", "D"]}
        graph = build_graph(neighbors_of(table), Package("A"), 50)
        self.assertEqual(graph.cycles, [("c", "a")])
        self.assertIn(("C", "A"), edges_of(graph))
        self.assertEqual(len(graph.nodes), 4)

    def test_self_dependency(self):
        """Зависимость пакета от самого себя - цикл длины 1."""
        table = {"A": ["A", "B"]}
        graph = build_graph(neighbors_of(table), Package("A"), 5)
        self.assertEqual(graph.cycles, [("a", "a")])
        self.assertEqual(list(graph.nodes), ["a", "b"])

    def test_names_are_case_insensitive(self):
        """Имена, различающиеся регистром, - одна вершина."""
        table = {"Core": ["util"], "Lib": ["Util"]}
        graph = build_graph(neighbors_of(table), Package("Core"), 3)
        self.assertEqual(list(graph.nodes), ["core", "util"])

    def test_graph_can_be_built_twice_with_one_walker(self):
        """Повторный вызов build не наследует состояние предыдущего."""
        graph1 = build_graph(neighbors_of(DIAMOND), Package("A"), 10)
        graph2 = build_graph(neighbors_of(DIAMOND), Package("A"), 10)
        self.assertEqual(edges_of(graph1), edges_of(graph2))


if __name__ == "__main__":
    unittest.main()
