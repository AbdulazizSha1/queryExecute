import re
from dataclasses import dataclass
from typing import Literal


TagOperator = Literal["=", "~"]


@dataclass(frozen=True)
class OsmTagFilter:
    key: str
    value: str
    operator: TagOperator = "="
    case_insensitive: bool = False


@dataclass(frozen=True)
class POIDefinition:
    id: str
    display_name: str
    filters: tuple[OsmTagFilter, ...]
    terms: tuple[str, ...]


@dataclass(frozen=True)
class CuisineDefinition:
    id: str
    display_name: str
    filter: OsmTagFilter
    terms: tuple[str, ...]


ARABIC_DIACRITICS_RE = re.compile(r"[\u0617-\u061A\u064B-\u0652]")
WORD_CHAR_CLASS = "0-9A-Za-z_\u0600-\u06FF"


POI_DEFINITIONS: tuple[POIDefinition, ...] = (
    POIDefinition(
        id="fast_food",
        display_name="fast food restaurants",
        filters=(OsmTagFilter("amenity", "fast_food"),),
        terms=(
            "fast food",
            "fast-food",
            "fastfood",
            "fast food restaurants",
            "مطاعم سريعة",
            "مطعم سريع",
            "وجبات سريعة",
        ),
    ),
    POIDefinition(
        id="restaurant",
        display_name="restaurants",
        filters=(OsmTagFilter("amenity", "restaurant"),),
        terms=(
            "restaurant",
            "restaurants",
            "eatery",
            "eateries",
            "مطعم",
            "مطاعم",
        ),
    ),
    POIDefinition(
        id="cafe",
        display_name="cafes",
        filters=(OsmTagFilter("amenity", "cafe"),),
        terms=(
            "cafe",
            "cafes",
            "café",
            "coffee shop",
            "coffee shops",
            "كافيه",
            "كافيهات",
            "مقهى",
            "مقاهي",
        ),
    ),
    POIDefinition(
        id="pharmacy",
        display_name="pharmacies",
        filters=(OsmTagFilter("amenity", "pharmacy"),),
        terms=(
            "pharmacy",
            "pharmacies",
            "drugstore",
            "drugstores",
            "chemist",
            "صيدلية",
            "صيدليات",
        ),
    ),
    POIDefinition(
        id="hospital",
        display_name="hospitals",
        filters=(OsmTagFilter("amenity", "hospital"),),
        terms=(
            "hospital",
            "hospitals",
            "مستشفى",
            "مستشفيات",
        ),
    ),
    POIDefinition(
        id="school",
        display_name="schools",
        filters=(OsmTagFilter("amenity", "school"),),
        terms=(
            "school",
            "schools",
            "مدرسة",
            "مدارس",
        ),
    ),
    POIDefinition(
        id="university",
        display_name="universities",
        filters=(OsmTagFilter("amenity", "university"),),
        terms=(
            "university",
            "universities",
            "college",
            "colleges",
            "جامعة",
            "جامعات",
        ),
    ),
    POIDefinition(
        id="park",
        display_name="parks",
        filters=(OsmTagFilter("leisure", "park"),),
        terms=(
            "park",
            "parks",
            "garden",
            "gardens",
            "حديقة",
            "حدائق",
        ),
    ),
    POIDefinition(
        id="mosque",
        display_name="mosques",
        filters=(
            OsmTagFilter("amenity", "place_of_worship"),
            OsmTagFilter("religion", "muslim"),
        ),
        terms=(
            "mosque",
            "mosques",
            "masjid",
            "masjids",
            "مسجد",
            "مساجد",
        ),
    ),
)


CUISINE_DEFINITIONS: tuple[CuisineDefinition, ...] = (
    CuisineDefinition(
        id="pizza",
        display_name="pizza",
        filter=OsmTagFilter("cuisine", "pizza", "~", case_insensitive=True),
        terms=(
            "pizza",
            "pizzeria",
            "pizzerias",
            "بيتزا",
        ),
    ),
)


NEARBY_CONNECTORS: tuple[str, ...] = (
    "adjacent to",
    "close to",
    "next to",
    "nearby",
    "near",
    "beside",
    "around",
    "within",
    "by",
    "بالقرب من",
    "قريبة من",
    "قريب من",
    "بجانب",
    "بجوار",
    "جوار",
    "جنبها",
    "جنب",
    "قرب",
    "حول",
    "حوله",
    "قريبة",
    "قريب",
)


def normalize_query_text(text: str) -> str:
    lowered = text.lower().replace("\u0640", "")
    without_diacritics = ARABIC_DIACRITICS_RE.sub("", lowered)
    normalized_arabic = (
        without_diacritics.replace("أ", "ا")
        .replace("إ", "ا")
        .replace("آ", "ا")
        .replace("ى", "ي")
        .replace("ة", "ه")
        .replace("ؤ", "و")
        .replace("ئ", "ي")
    )
    cleaned = re.sub(rf"[^{WORD_CHAR_CLASS}]+", " ", normalized_arabic)
    return re.sub(r"\s+", " ", cleaned).strip()


def find_first_connector(normalized_text: str) -> tuple[str, int, int] | None:
    matches: list[tuple[str, int, int]] = []

    for connector in NEARBY_CONNECTORS:
        normalized_connector = normalize_query_text(connector)
        match = _find_phrase(normalized_text, normalized_connector)
        if match:
            start, end = match
            matches.append((normalized_connector, start, end))

    if not matches:
        return None

    return min(matches, key=lambda item: (item[1], -(item[2] - item[1])))


def find_poi_definition(text: str) -> POIDefinition | None:
    matches: list[tuple[POIDefinition, int, int]] = []

    for definition in POI_DEFINITIONS:
        for term in definition.terms:
            for normalized_term in _term_variants(term):
                match = _find_phrase(text, normalized_term)
                if match:
                    start, end = match
                    matches.append((definition, start, end))

    if not matches:
        return None

    definition, _, _ = max(matches, key=lambda item: (item[2] - item[1], -item[1]))
    return definition


def find_cuisine_definition(text: str) -> CuisineDefinition | None:
    matches: list[tuple[CuisineDefinition, int, int]] = []

    for definition in CUISINE_DEFINITIONS:
        for term in definition.terms:
            for normalized_term in _term_variants(term):
                match = _find_phrase(text, normalized_term)
                if match:
                    start, end = match
                    matches.append((definition, start, end))

    if not matches:
        return None

    definition, _, _ = max(matches, key=lambda item: (item[2] - item[1], -item[1]))
    return definition


def _find_phrase(text: str, normalized_phrase: str) -> tuple[int, int] | None:
    if not text or not normalized_phrase:
        return None

    escaped = re.escape(normalized_phrase).replace(r"\ ", r"\s+")
    pattern = rf"(?<![{WORD_CHAR_CLASS}]){escaped}(?![{WORD_CHAR_CLASS}])"
    match = re.search(pattern, text)
    if not match:
        return None

    return match.start(), match.end()


def _term_variants(term: str) -> tuple[str, ...]:
    normalized_term = normalize_query_text(term)
    variants = [normalized_term]

    if _contains_arabic(normalized_term):
        words = normalized_term.split()
        if words and not words[0].startswith("ال"):
            variants.append(" ".join((f"ال{words[0]}", *words[1:])))

    return tuple(dict.fromkeys(variant for variant in variants if variant))


def _contains_arabic(text: str) -> bool:
    return any("\u0600" <= char <= "\u06FF" for char in text)
