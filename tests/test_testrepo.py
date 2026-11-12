"""Тесты тестового репозитория (файл описания графа)."""

import os
import tempfile
import unittest

from depgraph.errors import PackageNotFoundError, RepositoryError
from depgraph.model import Package
from depgraph.testrepo import FileRepository, parse_repository

DATA = os.path.join(os.path.dirname(__file__), "data")


class ParseRepositoryTest(unittest.TestCase):
    """Разбор текста описания репозитория."""

    def test_parse_basic(self):
        """Строки, комментарии и пустые строки."""
        graph = parse_repository(
            "# комментарий\n\nA: B C  # хвост\nB: C\nC:\n"
        )
        self.assertEqual(graph, {"A": ["B", "C"], "B": ["C"], "C": []})

    def test_separators_and_duplicates(self):
        """Запятые допустимы, повторы зависимостей схлопываются."""
        self.assertEqual(
            parse_repository("A: B, C B\n")["A"], ["B", "C"]
        )

    def test_undefined_dependency_becomes_leaf(self):
        """Пакет, упомянутый только как зависимость, не имеет зависимостей."""
        self.assertEqual(parse_repository("A: B\n")["B"], [])

    def test_missing_colon(self):
        """Строка без двоеточия."""
        with self.assertRaises(RepositoryError) as context:
            parse_repository("A B\n")
        self.assertIn("строка 1", str(context.exception))

    def test_bad_name(self):
        """Имя пакета не из заглавных латинских букв."""
        with self.assertRaises(RepositoryError):
            parse_repository("A: b\n")
        with self.assertRaises(RepositoryError):
            parse_repository("A1: B\n")

    def test_duplicate_definition(self):
        """Пакет описан дважды."""
        with self.assertRaises(RepositoryError) as context:
            parse_repository("A: B\nA: C\n")
        self.assertIn("строка 2", str(context.exception))


class FileRepositoryTest(unittest.TestCase):
    """Чтение репозитория из файла."""

    def test_from_file(self):
        """Чтение готового файла из tests/data."""
        repo = FileRepository.from_file(os.path.join(DATA, "simple.txt"))
        self.assertEqual(repo.package_names(), list("ABCDE"))
        self.assertEqual(
            repo.dependencies(Package("C")), [Package("D"), Package("E")]
        )

    def test_unknown_package(self):
        """Запрос зависимостей неизвестного пакета."""
        repo = FileRepository({"A": []})
        with self.assertRaises(PackageNotFoundError):
            repo.dependencies(Package("Z"))

    def test_unreadable_file(self):
        """Несуществующий файл."""
        with self.assertRaises(RepositoryError):
            FileRepository.from_file(os.path.join(DATA, "missing.txt"))

    def test_not_utf8(self):
        """Файл не в кодировке UTF-8."""
        with tempfile.NamedTemporaryFile(delete=False) as bad_file:
            bad_file.write(b"A: \xff\xfe\n")
        try:
            with self.assertRaises(RepositoryError):
                FileRepository.from_file(bad_file.name)
        finally:
            os.unlink(bad_file.name)


if __name__ == "__main__":
    unittest.main()
