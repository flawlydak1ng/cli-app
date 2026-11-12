"""Обратные зависимости: какие пакеты зависят от заданного."""

from depgraph.model import Package


def reverse_neighbors(repository):
    """Построить функцию соседей обращённого графа репозитория.

    Для пакета возвращаются пакеты, которые зависят от него напрямую.
    Обход графа выполняет тот же DFS, что и для прямых зависимостей.
    """
    dependents = {}
    for name in repository.package_names():
        parent = Package(name)
        for dependency in repository.dependencies(parent):
            dependents.setdefault(dependency.key, []).append(parent)

    def neighbors(package):
        """Пакеты, напрямую зависящие от package."""
        return dependents.get(package.key, [])

    return neighbors
