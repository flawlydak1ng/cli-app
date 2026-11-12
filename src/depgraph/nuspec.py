"""Разбор манифеста пакета .nuspec: прямые зависимости.

Зависимости в манифесте разбиты на группы по целевым платформам (TFM).
NuGet выбирает для проекта одну группу, подходящую его платформе. Платформа
не входит в параметры инструмента, поэтому выбирается группа самой новой
платформы пакета: .NET 5+ новее .NET Core, затем идут .NET Standard и
.NET Framework; платформы с суффиксом (net8.0-android) и неизвестные
платформы уступают обычным.
"""

import re
from dataclasses import dataclass
from xml.etree import ElementTree

from depgraph.errors import RepositoryError

NO_FRAMEWORK = "any"
TAG_GROUP = "group"
TAG_DEPENDENCY = "dependency"
TAG_METADATA = "metadata"
TAG_DEPENDENCIES = "dependencies"

SHORT_NET = "net"
FRAMEWORK_RE = re.compile(
    r"^\.?(?P<name>[A-Za-z]+)(?P<version>\d[\d.]*)?(?P<platform>-.*)?$"
)
FAMILY_RANKS = {"netframework": 1, "netstandard": 2, "netcoreapp": 3}
FRAMEWORK_FAMILY = 1
MODERN_FAMILY = 4
UNKNOWN_FRAMEWORK_RANK = (False, 0, ())
ANY_FRAMEWORK_RANK = (False, -1, ())
DOT = "."


@dataclass(frozen=True)
class Dependency:
    """Зависимость пакета: имя, диапазон версий и платформа группы."""

    name: str
    version_range: str
    framework: str


def local_name(tag):
    """Имя XML-элемента без пространства имён."""
    return tag.rsplit("}", 1)[-1]


def framework_rank(framework):
    """Ключ «новизны» целевой платформы: чем больше, тем новее."""
    if framework == NO_FRAMEWORK:
        return ANY_FRAMEWORK_RANK
    match = FRAMEWORK_RE.match(framework.strip())
    if not match:
        return UNKNOWN_FRAMEWORK_RANK
    name = match["name"].lower()
    version = match["version"] or ""
    family = FAMILY_RANKS.get(name, 0)
    if name == SHORT_NET:
        family = MODERN_FAMILY if DOT in version else FRAMEWORK_FAMILY
    parts = version.split(DOT) if DOT in version else list(version)
    numbers = tuple(int(part) for part in parts)
    return (not match["platform"], family, numbers)


def read_groups(section):
    """Прочитать группы зависимостей: список пар (платформа, элементы).

    Зависимости, записанные без группы, относятся к любой платформе.
    """
    groups = []
    loose = []
    for child in section:
        if local_name(child.tag) == TAG_GROUP:
            framework = child.get("targetFramework") or NO_FRAMEWORK
            groups.append((framework, list(child)))
        else:
            loose.append(child)
    if loose:
        groups.append((NO_FRAMEWORK, loose))
    return groups


def newest_group(groups):
    """Выбрать группу самой новой платформы (при равенстве - первую)."""
    best = None
    for group in groups:
        if best is None or framework_rank(group[0]) > framework_rank(best[0]):
            best = group
    return best


def to_dependencies(framework, items):
    """Преобразовать элементы dependency в объекты без повторов по имени."""
    found = {}
    for item in items:
        name = item.get("id")
        if local_name(item.tag) != TAG_DEPENDENCY or not name:
            continue
        found.setdefault(
            name.lower(),
            Dependency(name, item.get("version") or "", framework),
        )
    return list(found.values())


def find_dependencies_section(root):
    """Найти элемент metadata/dependencies или вернуть None."""
    for metadata in root:
        if local_name(metadata.tag) != TAG_METADATA:
            continue
        for section in metadata:
            if local_name(section.tag) == TAG_DEPENDENCIES:
                return section
    return None


def parse_dependencies(xml_bytes):
    """Извлечь прямые зависимости из содержимого файла .nuspec."""
    try:
        root = ElementTree.fromstring(xml_bytes)
    except ElementTree.ParseError as error:
        raise RepositoryError(f"некорректный файл .nuspec: {error}") from None
    section = find_dependencies_section(root)
    best = newest_group(read_groups(section)) if section is not None else None
    if best is None:
        return []
    return to_dependencies(*best)
