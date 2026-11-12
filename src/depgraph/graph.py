"""Граф зависимостей и его построение обходом в глубину (DFS)."""

from depgraph.errors import RootExcludedError


class Graph:
    """Ориентированный граф: ребро A -> B значит «A зависит от B»."""

    def __init__(self, root):
        """Создать граф с единственной вершиной - корневым пакетом."""
        self.root = root
        self.nodes = {}
        self.edges = {}
        self.cycles = []
        self.frontier = set()
        self.add_node(root)

    def add_node(self, package):
        """Добавить вершину; при повторном добавлении ничего не меняется."""
        self.nodes.setdefault(package.key, package)
        self.edges.setdefault(package.key, [])

    def add_edge(self, parent_key, child):
        """Добавить ребро от вершины parent_key к пакету child."""
        self.add_node(child)
        children = self.edges[parent_key]
        if child.key not in children:
            children.append(child.key)

    def add_cycle(self, source_key, target_key):
        """Запомнить ребро, замыкающее цикл."""
        pair = (source_key, target_key)
        if pair not in self.cycles:
            self.cycles.append(pair)

    def edge_count(self):
        """Общее число рёбер графа."""
        return sum(len(children) for children in self.edges.values())

    def children(self, key):
        """Пакеты, на которые ссылается вершина key (в порядке обхода)."""
        return [self.nodes[child] for child in self.edges[key]]


class DependencyWalker:
    """Строит граф рекурсивным обходом в глубину.

    neighbors - функция «пакет -> список соседних пакетов». Для прямых
    зависимостей это репозиторий, для обратных - обращённый граф.
    """

    def __init__(self, neighbors, max_depth, substring=""):
        """Задать функцию соседей, предельную глубину и подстроку-фильтр."""
        self._neighbors = neighbors
        self._max_depth = max_depth
        self._substring = substring.lower()
        self._graph = None
        self._depth_of = {}
        self._path = []

    def is_excluded(self, package):
        """Имя пакета содержит подстроку фильтрации."""
        return bool(self._substring) and self._substring in package.key

    def build(self, root):
        """Построить граф, начиная с корневого пакета root."""
        if self.is_excluded(root):
            raise RootExcludedError(
                f"пакет '{root.name}' исключён подстрокой фильтрации"
            )
        self._graph = Graph(root)
        self._depth_of = {}
        self._path = []
        self._visit(root, 0)
        return self._graph

    def _visit(self, package, depth):
        """Рекурсивно обойти пакет, находящийся на глубине depth.

        Вершина разворачивается повторно, если до неё дошли по более
        короткому пути: иначе из-за порядка обхода часть зависимостей,
        укладывающихся в предельную глубину, была бы потеряна.
        """
        key = package.key
        package = self._graph.nodes[key]
        known = self._depth_of.get(key)
        if known is not None and known <= depth:
            return
        self._depth_of[key] = depth
        if depth >= self._max_depth:
            self._graph.frontier.add(key)
            return
        self._graph.frontier.discard(key)
        self._path.append(key)
        for child in self._neighbors(package):
            if self.is_excluded(child):
                continue
            self._graph.add_edge(key, child)
            if child.key in self._path:
                self._graph.add_cycle(key, child.key)
            else:
                self._visit(child, depth + 1)
        self._path.pop()


def build_graph(neighbors, root, max_depth, substring=""):
    """Построить граф зависимостей пакета root обходом DFS."""
    return DependencyWalker(neighbors, max_depth, substring).build(root)
