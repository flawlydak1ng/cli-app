"""Тесты разбора файла .nuspec."""

import unittest

from depgraph.errors import RepositoryError
from depgraph.nuspec import parse_dependencies

GROUPED = b"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd">
  <metadata>
    <id>Demo</id>
    <version>1.0.0</version>
    <dependencies>
      <group targetFramework="net6.0">
        <dependency id="Alpha" version="1.0.0" exclude="Build" />
        <dependency id="Beta" version="[2.0, 3.0)" />
      </group>
      <group targetFramework=".NETStandard2.0">
        <dependency id="alpha" version="1.0.0" />
        <dependency id="Gamma" version="4.5.0" />
      </group>
      <group targetFramework="net8.0" />
    </dependencies>
  </metadata>
</package>
"""

FLAT = b"""<?xml version="1.0"?>
<package xmlns="http://schemas.microsoft.com/packaging/2010/07/nuspec.xsd">
  <metadata>
    <id>Old</id>
    <dependencies>
      <dependency id="Legacy" version="1.0" />
    </dependencies>
  </metadata>
</package>
"""

NO_DEPENDENCIES = b"""<?xml version="1.0"?>
<package><metadata><id>Leaf</id></metadata></package>
"""


class ParseDependenciesTest(unittest.TestCase):
    """Извлечение зависимостей из разных форм .nuspec."""

    def test_groups_are_merged_by_name(self):
        """Зависимости разных платформ объединяются без повторов."""
        deps = parse_dependencies(GROUPED)
        self.assertEqual([d.name for d in deps], ["Alpha", "Beta", "Gamma"])
        alpha = deps[0]
        self.assertEqual(alpha.version_range, "1.0.0")
        self.assertEqual(alpha.frameworks, ("net6.0", ".NETStandard2.0"))
        self.assertEqual(deps[1].version_range, "[2.0, 3.0)")

    def test_flat_dependencies_without_groups(self):
        """Зависимости без групп относятся к любой платформе."""
        deps = parse_dependencies(FLAT)
        self.assertEqual(len(deps), 1)
        self.assertEqual(deps[0].name, "Legacy")
        self.assertEqual(deps[0].frameworks, ("any",))

    def test_no_dependencies(self):
        """У пакета может не быть зависимостей."""
        self.assertEqual(parse_dependencies(NO_DEPENDENCIES), [])

    def test_broken_xml(self):
        """Некорректный XML приводит к RepositoryError."""
        with self.assertRaises(RepositoryError):
            parse_dependencies(b"<package><metadata>")


if __name__ == "__main__":
    unittest.main()
