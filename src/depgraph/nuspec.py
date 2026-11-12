"""Разбор манифеста пакета .nuspec: прямые зависимости."""

from dataclasses import dataclass
from xml.etree import ElementTree

from depgraph.errors import RepositoryError

NO_FRAMEWORK = "any"
TAG_GROUP = "group"
TAG_DEPENDENCY = "dependency"
TAG_METADATA = "metadata"
TAG_DEPENDENCIES = "dependencies"


@dataclass(frozen=True)
class Dependency:
    """Зависимость пакета: имя, диапазон версий и целевые платформы."""

    name: str
    version_range: str
    frameworks: tuple


def local_name(tag):
    """Имя XML-элемента без пространства имён."""
    return tag.rsplit("}", 1)[-1]


def read_group(element):
    """Вернуть пары (платформа, зависимость) из группы или из корня."""
    if local_name(element.tag) == TAG_GROUP:
        framework = element.get("targetFramework") or NO_FRAMEWORK
        items = list(element)
    else:
        framework = NO_FRAMEWORK
        items = [element]
    return [
        (framework, item)
        for item in items
        if local_name(item.tag) == TAG_DEPENDENCY and item.get("id")
    ]


def merge_dependencies(pairs):
    """Объединить зависимости разных платформ по имени пакета.

    Имена в NuGet не зависят от регистра. Для повторяющегося пакета
    сохраняется диапазон из первой встреченной группы.
    """
    merged = {}
    for framework, item in pairs:
        key = item.get("id").lower()
        if key not in merged:
            merged[key] = [item.get("id"), item.get("version") or "", []]
        if framework not in merged[key][2]:
            merged[key][2].append(framework)
    return [
        Dependency(name, version_range, tuple(frameworks))
        for name, version_range, frameworks in merged.values()
    ]


def parse_dependencies(xml_bytes):
    """Извлечь прямые зависимости из содержимого файла .nuspec."""
    try:
        root = ElementTree.fromstring(xml_bytes)
    except ElementTree.ParseError as error:
        raise RepositoryError(f"некорректный файл .nuspec: {error}") from None
    pairs = []
    for metadata in root:
        if local_name(metadata.tag) != TAG_METADATA:
            continue
        for section in metadata:
            if local_name(section.tag) != TAG_DEPENDENCIES:
                continue
            for child in section:
                pairs.extend(read_group(child))
    return merge_dependencies(pairs)
