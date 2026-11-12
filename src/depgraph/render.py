"""Представление графа зависимостей в текстовом виде."""

NO_DEPENDENCIES = "нет зависимостей"
DEPTH_EXHAUSTED = "достигнута максимальная глубина"


def describe_node(graph, key):
    """Строка с вершиной и списком её зависимостей."""
    label = graph.nodes[key].label
    children = graph.children(key)
    if children:
        return f"{label} -> " + ", ".join(child.label for child in children)
    reason = DEPTH_EXHAUSTED if key in graph.frontier else NO_DEPENDENCIES
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
