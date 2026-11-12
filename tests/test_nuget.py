"""Тесты клиента репозитория NuGet на поддельном сервере."""

import unittest

from depgraph.errors import PackageNotFoundError, RepositoryError
from depgraph.nuget import NuGetRepository
from tests.fake_nuget import INDEX_URL, make_fetch

PACKAGES = {
    "Alpha": {"1.0.0": [("Beta", "1.0.0"), ("Gamma", "[2.0,3.0)")]},
    "Beta": {"1.0.0": [], "1.2.0": []},
    "Gamma": {"2.1.0": [], "2.5.0": [], "3.0.0": []},
}


class NuGetRepositoryTest(unittest.TestCase):
    """Получение версий и прямых зависимостей."""

    def setUp(self):
        """Подготовить репозиторий с поддельной загрузкой."""
        self.fetch = make_fetch(PACKAGES)
        self.repo = NuGetRepository(INDEX_URL, self.fetch)

    def test_direct_dependencies(self):
        """Прямые зависимости заданной версии."""
        deps = self.repo.direct_dependencies("Alpha", "1.0.0")
        self.assertEqual([d.name for d in deps], ["Beta", "Gamma"])
        self.assertEqual(deps[1].version_range, "[2.0,3.0)")

    def test_version_is_normalized(self):
        """Версия «1.0» находит пакет с версией 1.0.0."""
        deps = self.repo.direct_dependencies("alpha", "1.0")
        self.assertEqual(len(deps), 2)

    def test_unknown_package(self):
        """Отсутствующий пакет даёт понятную ошибку."""
        with self.assertRaises(PackageNotFoundError) as context:
            self.repo.direct_dependencies("Missing", "1.0.0")
        self.assertIn("не найден", str(context.exception))

    def test_unknown_version(self):
        """Отсутствующая версия существующего пакета."""
        with self.assertRaises(PackageNotFoundError):
            self.repo.direct_dependencies("Alpha", "9.9.9")

    def test_invalid_version(self):
        """Некорректная версия отвергается до обращения к сети."""
        with self.assertRaises(RepositoryError):
            self.repo.direct_dependencies("Alpha", "x.y")
        self.assertEqual(self.fetch.calls, [])

    def test_resolve_version_picks_lowest_match(self):
        """Диапазон разрешается в наименьшую подходящую версию."""
        self.assertEqual(self.repo.resolve_version("Beta", "1.1.0"), "1.2.0")
        self.assertEqual(
            self.repo.resolve_version("Gamma", "[2.0,3.0)"), "2.1.0"
        )

    def test_resolve_version_without_candidates(self):
        """Нет версии, удовлетворяющей диапазону."""
        with self.assertRaises(PackageNotFoundError):
            self.repo.resolve_version("Beta", "[5.0,)")

    def test_resolve_version_bad_range(self):
        """Некорректный диапазон версий."""
        with self.assertRaises(RepositoryError):
            self.repo.resolve_version("Beta", "[1.0")

    def test_versions_are_cached(self):
        """Список версий скачивается один раз."""
        self.repo.versions("Beta")
        self.repo.versions("beta")
        listing = [
            url for url in self.fetch.calls if url.endswith("/beta/index.json")
        ]
        self.assertEqual(len(listing), 1)


class BrokenServiceTest(unittest.TestCase):
    """Некорректные ответы службы NuGet."""

    def test_index_without_base_address(self):
        """В индексе службы нет PackageBaseAddress."""
        repo = NuGetRepository(INDEX_URL, lambda url: b'{"resources": []}')
        with self.assertRaises(RepositoryError):
            repo.base_address()

    def test_not_json(self):
        """Служба вернула не JSON."""
        repo = NuGetRepository(INDEX_URL, lambda url: b"<html>")
        with self.assertRaises(RepositoryError):
            repo.base_address()

    def test_json_is_not_object(self):
        """Служба вернула JSON, не являющийся объектом."""
        repo = NuGetRepository(INDEX_URL, lambda url: b"[1, 2]")
        with self.assertRaises(RepositoryError):
            repo.base_address()


if __name__ == "__main__":
    unittest.main()
