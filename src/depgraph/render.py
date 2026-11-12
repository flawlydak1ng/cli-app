"""Представление графа зависимостей в текстовом виде."""

NO_DEPENDENCIES = "нет зависимостей"
NO_DEPENDENTS = "от него никто не зависит"
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


def format_listing(graph, max_depth, substring):
    """Построить текстовый список вершин графа и найденных циклов."""
    shown_filter = substring or "нет"
    lines = [
        f"Граф зависимостей пакета {graph.root.label}: "
        f"вершин {len(graph.nodes)}, рёбер {graph.edge_count()}, "
        f"максимальная глубина {max_depth}, фильтр: {shown_filter}"
    ]
    lines.extend(describe_node(graph, key) for key in graph.nodes)
    if not graph.cycles:
        lines.append("Циклические зависимости: нет")
        return lines
    lines.append("Циклические зависимости (ребро замыкает цикл):")
    for source, target in graph.cycles:
        lines.append(
            f"  {graph.nodes[source].label} -> {graph.nodes[target].label}"
        )
    return lines


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
