"""Тесты разбора файла .nuspec и выбора группы платформы."""

import unittest

from depgraph.errors import RepositoryError
from depgraph.nuspec import framework_rank, parse_dependencies

NAMESPACE = "http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd"


def manifest(body):
    """Собрать .nuspec с заданным содержимым элемента dependencies."""
    return (
        f'<package xmlns="{NAMESPACE}"><metadata><id>Demo</id>'
        f"<dependencies>{body}</dependencies></metadata></package>"
    ).encode()


GROUPED = manifest(
    '<group targetFramework=".NETFramework4.6.2">'
    '<dependency id="Legacy" version="1.0.0"/></group>'
    '<group targetFramework=".NETStandard2.0">'
    '<dependency id="Alpha" version="1.0.0"/>'
    '<dependency id="Gamma" version="4.5.0"/></group>'
    '<group targetFramework="net6.0">'
    '<dependency id="Alpha" version="1.0.0" exclude="Build"/>'
    '<dependency id="alpha" version="2.0.0"/>'
    '<dependency id="Beta" version="[2.0, 3.0)"/></group>'
)

EMPTY_NEWEST = manifest(
    '<group targetFramework="net8.0"/>'
    '<group targetFramework="net6.0">'
    '<dependency id="Alpha" version="1.0.0"/></group>'
)

FLAT = (
    b'<package xmlns="http://schemas.microsoft.com/packaging/2010/07/'
    b'nuspec.xsd"><metadata><id>Old</id><dependencies>'
    b'<dependency id="Legacy" version="1.0"/></dependencies>'
    b"</metadata></package>"
)

NO_DEPENDENCIES = b"<package><metadata><id>Leaf</id></metadata></package>"


class FrameworkRankTest(unittest.TestCase):
    """Порядок «новизны» целевых платформ."""

    def test_order(self):
        """От старых платформ к новым."""
        ordered = [
            "any", "???", ".NETPortable4.5-Profile111", ".NETFramework4.5",
            ".NETFramework4.6.2", ".NETStandard1.3",
            ".NETStandard2.0", "netstandard2.1", ".NETCoreApp3.1",
            "net5.0", "net6.0", "net8.0", "net10.0",
        ]
        ranks = [framework_rank(name) for name in ordered]
        self.assertEqual(ranks, sorted(ranks))
        self.assertEqual(len(set(ranks)), len(ranks))

    def test_short_and_long_names_are_equal(self):
        """Короткая и длинная записи .NET Framework равнозначны."""
        self.assertEqual(
            framework_rank("net462"), framework_rank(".NETFramework4.6.2")
        )

    def test_platform_suffix_is_less_preferred(self):
        """Платформа с суффиксом уступает обычной."""
        self.assertLess(
            framework_rank("net8.0-android34.0"), framework_rank("net6.0")
        )

    def test_unparsable_framework(self):
        """Нераспознанное название - самая низкая оценка."""
        self.assertLess(
            framework_rank("???"), framework_rank(".NETFramework2.0")
        )


class ParseDependenciesTest(unittest.TestCase):
    """Извлечение зависимостей из разных форм .nuspec."""

    def test_newest_group_is_selected(self):
        """Берётся группа самой новой платформы, остальные игнорируются."""
        deps = parse_dependencies(GROUPED)
        self.assertEqual([d.name for d in deps], ["Alpha", "Beta"])
        self.assertEqual(deps[0].version_range, "1.0.0")
        self.assertEqual(deps[0].framework, "net6.0")
        self.assertEqual(deps[1].version_range, "[2.0, 3.0)")

    def test_empty_newest_group_means_no_dependencies(self):
        """Пустая группа новейшей платформы: зависимостей нет."""
        self.assertEqual(parse_dependencies(EMPTY_NEWEST), [])

    def test_flat_dependencies_without_groups(self):
        """Зависимости без групп относятся к любой платформе."""
        deps = parse_dependencies(FLAT)
        self.assertEqual(len(deps), 1)
        self.assertEqual(deps[0].name, "Legacy")
        self.assertEqual(deps[0].framework, "any")

    def test_no_dependencies(self):
        """У пакета может не быть зависимостей."""
        self.assertEqual(parse_dependencies(NO_DEPENDENCIES), [])

    def test_broken_xml(self):
        """Некорректный XML приводит к RepositoryError."""
        with self.assertRaises(RepositoryError):
            parse_dependencies(b"<package><metadata>")


if __name__ == "__main__":
    unittest.main()
