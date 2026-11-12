"""Представление графа зависимостей: PlantUML, ASCII-дерево, списки."""

NO_DEPENDENCIES = "нет зависимостей"
NO_DEPENDENTS = "от него никто не зависит"

ROOT_COLOR = "#LightBlue"
FRONTIER_COLOR = "#FFE9A8"
CYCLE_ARROW = "-[#red,dashed]->"

MIDDLE_BRANCH = "|-- "
LAST_BRANCH = "`-- "
VERTICAL = "|   "
BLANK = "    "
CYCLE_MARK = " (цикл)"
REPEAT_MARK = " (см. выше)"
FRONTIER_MARK = " ..."
DEPTH_EXHAUSTED = "достигнута максимальная глубина"


def describe_node(graph, key, arrow="->", empty=NO_DEPENDENCIES):
    """Строка с вершиной и списком её соседей по ребрам графа."""
    label = graph.nodes[key].label
    children = graph.children(key)
    if children:
        joined = ", ".join(child.label for child in children)
        return f"{label} {arrow} {joined}"
    reason = DEPTH_EXHAUSTED if key in graph.frontier else empty
    return f"{label} ({reason})"


def format_reverse_listing(graph, max_depth, substring):
    """Построить текстовый список обратных зависимостей.

    Запись «X <- Y» означает: пакет Y зависит от пакета X.
    """
    shown_filter = substring or "нет"
    lines = [
        f"Обратные зависимости пакета {graph.root.label} "
        f"(максимальная глубина {max_depth}, фильтр: {shown_filter})"
    ]
    dependents = [pkg.label for key, pkg in graph.nodes.items()
                  if key != graph.root.key]
    if not dependents:
        lines.append("Пакетов, зависящих от него, нет")
    else:
        lines.append(f"Зависят от него ({len(dependents)}): "
                     + ", ".join(dependents))
    lines.append("Запись «X <- Y»: пакет Y зависит от пакета X")
    lines.extend(
        describe_node(graph, key, "<-", NO_DEPENDENTS) for key in graph.nodes
    )
    for source, target in graph.cycles:
        lines.append(
            f"Цикл: {graph.nodes[source].label} <- {graph.nodes[target].label}"
        )
    return lines


def plantuml_label(package):
    """Подпись вершины для PlantUML без символов, ломающих кавычки."""
    return package.label.replace('"', "'")


def plantuml_node(package_id, graph, key):
    """Объявление вершины: корень и нераскрытые вершины выделяются."""
    label = plantuml_label(graph.nodes[key])
    line = f'rectangle "{label}" as {package_id}'
    if key == graph.root.key:
        return line + f" {ROOT_COLOR}"
    if key in graph.frontier:
        return line + f" {FRONTIER_COLOR}"
    return line


def format_plantuml(graph):
    """Описание графа зависимостей на языке диаграмм PlantUML."""
    ids = {key: f"n{index}" for index, key in enumerate(graph.nodes)}
    lines = [
        "@startuml",
        f"title Граф зависимостей пакета {plantuml_label(graph.root)}",
        "skinparam shadowing false",
    ]
    lines.extend(plantuml_node(ids[key], graph, key) for key in graph.nodes)
    for source, children in graph.edges.items():
        for target in children:
            if (source, target) in graph.cycles:
                arrow = f"{ids[source]} {CYCLE_ARROW} {ids[target]} : цикл"
            else:
                arrow = f"{ids[source]} --> {ids[target]}"
            lines.append(arrow)
    lines.append("@enduml")
    return lines


class TreePrinter:
    """Печатает граф в виде ASCII-дерева, раскрывая каждую вершину один раз."""

    def __init__(self, graph):
        """Подготовить печать дерева для графа."""
        self._graph = graph
        self._shown = set()
        self._path = []
        self.lines = []

    def print_tree(self):
        """Построить строки дерева, начиная с корня; вернуть их список."""
        root = self._graph.root
        self.lines = [root.label + self._mark(root.key)]
        self._shown = {root.key}
        self._path = [root.key]
        self._children(root.key, "")
        return self.lines

    def _mark(self, key):
        """Пометка вершины, которая не раскрыта из-за предельной глубины."""
        return FRONTIER_MARK if key in self._graph.frontier else ""

    def _children(self, key, prefix):
        """Напечатать потомков вершины key с общим префиксом prefix."""
        children = self._graph.children(key)
        for index, child in enumerate(children):
            last = index == len(children) - 1
            branch = LAST_BRANCH if last else MIDDLE_BRANCH
            note = self._note(child.key)
            self.lines.append(f"{prefix}{branch}{child.label}{note}")
            if note:
                continue
            self._shown.add(child.key)
            self._path.append(child.key)
            self._children(child.key, prefix + (BLANK if last else VERTICAL))
            self._path.pop()

    def _note(self, key):
        """Пометка для цикла, повтора или нераскрытой вершины."""
        if key in self._path:
            return CYCLE_MARK
        if key in self._shown:
            return REPEAT_MARK
        return self._mark(key)


def format_ascii_tree(graph):
    """Представить граф зависимостей в виде ASCII-дерева."""
    return TreePrinter(graph).print_tree()
