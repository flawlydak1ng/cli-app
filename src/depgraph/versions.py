"""Версии и диапазоны версий NuGet (SemVer 2.0 с четвёртой компонентой)."""

import re
from dataclasses import dataclass
from functools import total_ordering
from typing import Optional

VERSION_PARTS = 4
OPEN_BRACKETS = "[("
CLOSE_BRACKETS = "])"
INCLUSIVE_OPEN = "["
INCLUSIVE_CLOSE = "]"
BOUND_SEPARATOR = ","

VERSION_RE = re.compile(
    r"^(?P<numbers>\d+(?:\.\d+){0,3})"
    r"(?:-(?P<pre>[0-9A-Za-z.\-]+))?"
    r"(?:\+(?P<meta>[0-9A-Za-z.\-]+))?$"
)


def identifier_key(identifier):
    """Ключ сравнения идентификатора пререлиза: числа меньше строк."""
    if identifier.isdigit():
        return (0, int(identifier), "")
    return (1, 0, identifier.lower())


@total_ordering
@dataclass(frozen=True, eq=False)
class NuGetVersion:
    """Версия пакета NuGet: до четырёх чисел, пререлиз и метаданные."""

    numbers: tuple
    prerelease: tuple = ()
    metadata: str = ""

    @property
    def sort_key(self):
        """Ключ сравнения: числа, затем релиз старше пререлиза."""
        release_flag = 0 if self.prerelease else 1
        pre_key = tuple(identifier_key(item) for item in self.prerelease)
        return (self.numbers, release_flag, pre_key)

    def __eq__(self, other):
        """Версии равны, если равны ключи сравнения."""
        if not isinstance(other, NuGetVersion):
            return NotImplemented
        return self.sort_key == other.sort_key

    def __lt__(self, other):
        """Сравнение версий по правилам NuGet."""
        if not isinstance(other, NuGetVersion):
            return NotImplemented
        return self.sort_key < other.sort_key

    def __hash__(self):
        """Хэш согласован со сравнением."""
        return hash(self.sort_key)

    def __str__(self):
        """Нормализованная запись версии (как в плоском контейнере NuGet)."""
        major, minor, patch, revision = self.numbers
        parts = [major, minor, patch]
        if revision:
            parts.append(revision)
        text = ".".join(str(part) for part in parts)
        if self.prerelease:
            text += "-" + ".".join(self.prerelease)
        return text


def parse_version(text):
    """Разобрать строку версии, при ошибке выбросить ValueError."""
    match = VERSION_RE.match(text.strip())
    if not match:
        raise ValueError(f"некорректная версия '{text}'")
    numbers = [int(part) for part in match["numbers"].split(".")]
    numbers += [0] * (VERSION_PARTS - len(numbers))
    prerelease = tuple(match["pre"].split(".")) if match["pre"] else ()
    return NuGetVersion(tuple(numbers), prerelease, match["meta"] or "")


@dataclass(frozen=True)
class VersionRange:
    """Диапазон версий NuGet; границы None означают отсутствие границы."""

    minimum: Optional[NuGetVersion] = None
    min_inclusive: bool = True
    maximum: Optional[NuGetVersion] = None
    max_inclusive: bool = False

    def below_minimum(self, version):
        """Версия ниже нижней границы диапазона."""
        if self.minimum is None:
            return False
        if version == self.minimum:
            return not self.min_inclusive
        return version < self.minimum

    def above_maximum(self, version):
        """Версия выше верхней границы диапазона."""
        if self.maximum is None:
            return False
        if version == self.maximum:
            return not self.max_inclusive
        return version > self.maximum

    def contains(self, version):
        """Проверить, что версия входит в диапазон."""
        return not (self.below_minimum(version) or self.above_maximum(version))


def parse_bound(text):
    """Разобрать границу диапазона; пустая строка даёт None."""
    text = text.strip()
    return parse_version(text) if text else None


def parse_range(text):
    """Разобрать диапазон версий NuGet, при ошибке выбросить ValueError.

    Поддерживаются запись «1.0» (то есть «не ниже 1.0») и интервальная
    запись: «[1.0]», «[1.0,)», «(,2.0]», «(1.0,2.0)» и т. д.
    """
    text = text.strip()
    if not text:
        return VersionRange()
    if text[0] not in OPEN_BRACKETS:
        return VersionRange(minimum=parse_version(text))
    if text[-1] not in CLOSE_BRACKETS:
        raise ValueError(f"некорректный диапазон версий '{text}'")
    lower_inclusive = text[0] == INCLUSIVE_OPEN
    upper_inclusive = text[-1] == INCLUSIVE_CLOSE
    lower, comma, upper = text[1:-1].partition(BOUND_SEPARATOR)
    if not comma:
        if not (lower_inclusive and upper_inclusive):
            raise ValueError(f"некорректный диапазон версий '{text}'")
        exact = parse_version(lower)
        return VersionRange(exact, True, exact, True)
    if BOUND_SEPARATOR in upper:
        raise ValueError(f"некорректный диапазон версий '{text}'")
    return VersionRange(
        parse_bound(lower),
        lower_inclusive,
        parse_bound(upper),
        upper_inclusive,
    )


def allows_prerelease(version_range):
    """Нижняя граница диапазона сама является пререлизом."""
    minimum = version_range.minimum
    return minimum is not None and bool(minimum.prerelease)


def lowest_match(version_range, versions):
    """Выбрать наименьшую версию из списка, входящую в диапазон.

    Так NuGet разрешает зависимость. Пререлизы рассматриваются, только если
    нижняя граница сама является пререлизом или стабильных версий нет.
    """
    candidates = sorted(v for v in versions if version_range.contains(v))
    if not allows_prerelease(version_range):
        candidates = [v for v in candidates if not v.prerelease] or candidates
    return candidates[0] if candidates else None
