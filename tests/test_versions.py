"""Тесты версий и диапазонов версий NuGet."""

import unittest

from depgraph.versions import lowest_match, parse_range, parse_version


def versions(*texts):
    """Список разобранных версий."""
    return [parse_version(text) for text in texts]


class VersionTest(unittest.TestCase):
    """Разбор, нормализация и сравнение версий."""

    def test_normalized_string(self):
        """Версия приводится к нормализованной записи."""
        self.assertEqual(str(parse_version("1.0")), "1.0.0")
        self.assertEqual(str(parse_version("1.2.3.0")), "1.2.3")
        self.assertEqual(str(parse_version("1.2.3.4")), "1.2.3.4")
        self.assertEqual(
            str(parse_version("1.0.0-Beta.1+abc")), "1.0.0-Beta.1"
        )

    def test_invalid_versions(self):
        """Некорректные записи версий отвергаются."""
        for text in ("", "v1", "1..2", "1.2.3.4.5", "1.0-", "a.b"):
            with self.assertRaises(ValueError, msg=text):
                parse_version(text)

    def test_ordering(self):
        """Порядок: пререлиз младше релиза, числа сравниваются как числа."""
        ordered = versions(
            "1.0.0-alpha", "1.0.0-alpha.1", "1.0.0-alpha.beta",
            "1.0.0-beta", "1.0.0-beta.2", "1.0.0-beta.11", "1.0.0-rc.1",
            "1.0.0", "1.0.1", "1.9.0", "1.10.0",
        )
        self.assertEqual(sorted(reversed(ordered)), ordered)

    def test_equality_ignores_metadata_and_case(self):
        """Метаданные сборки и регистр пререлиза не влияют на равенство."""
        self.assertEqual(parse_version("1.0+a"), parse_version("1.0.0+b"))
        self.assertEqual(parse_version("1.0-RC"), parse_version("1.0.0-rc"))


class RangeTest(unittest.TestCase):
    """Разбор диапазонов и выбор наименьшей подходящей версии."""

    def test_simple_range_means_minimum(self):
        """Запись «1.0» означает «не ниже 1.0»."""
        version_range = parse_range("1.0")
        self.assertTrue(version_range.contains(parse_version("1.0.0")))
        self.assertTrue(version_range.contains(parse_version("9.0")))
        self.assertFalse(version_range.contains(parse_version("0.9")))

    def test_interval_notation(self):
        """Интервальная запись с включёнными и исключёнными границами."""
        version_range = parse_range("(1.0, 2.0]")
        self.assertFalse(version_range.contains(parse_version("1.0")))
        self.assertTrue(version_range.contains(parse_version("1.5")))
        self.assertTrue(version_range.contains(parse_version("2.0")))
        self.assertFalse(version_range.contains(parse_version("2.0.1")))

    def test_exact_and_open_ranges(self):
        """Точная версия и диапазоны без границы."""
        exact = parse_range("[1.2.3]")
        self.assertTrue(exact.contains(parse_version("1.2.3")))
        self.assertFalse(exact.contains(parse_version("1.2.4")))
        upper = parse_range("(,3.0)")
        self.assertTrue(upper.contains(parse_version("0.1")))
        self.assertFalse(upper.contains(parse_version("3.0")))

    def test_empty_range_accepts_everything(self):
        """Пустой диапазон допускает любую версию."""
        self.assertTrue(parse_range("").contains(parse_version("0.0.1")))

    def test_invalid_ranges(self):
        """Некорректные диапазоны отвергаются."""
        for text in ("[1.0", "(1.0)", "[1.0,2.0,3.0]", "[a,b]", "1.*"):
            with self.assertRaises(ValueError, msg=text):
                parse_range(text)

    def test_lowest_match(self):
        """Выбирается наименьшая подходящая версия."""
        available = versions("1.0.0", "1.1.0", "2.0.0", "3.0.0")
        self.assertEqual(
            str(lowest_match(parse_range("1.0.5"), available)), "1.1.0"
        )
        self.assertEqual(
            str(lowest_match(parse_range("(1.0.0,)"), available)), "1.1.0"
        )
        self.assertIsNone(lowest_match(parse_range("[4.0,)"), available))

    def test_prerelease_ignored_unless_requested(self):
        """Пререлиз выбирается, только если нижняя граница - пререлиз."""
        available = versions("1.0.1-beta", "1.0.1", "1.1.0")
        self.assertEqual(
            str(lowest_match(parse_range("1.0.0"), available)), "1.0.1"
        )
        self.assertEqual(
            str(lowest_match(parse_range("1.0.1-alpha"), available)),
            "1.0.1-beta",
        )
        only_pre = versions("2.0.0-rc")
        self.assertEqual(
            str(lowest_match(parse_range("1.0"), only_pre)), "2.0.0-rc"
        )


if __name__ == "__main__":
    unittest.main()
