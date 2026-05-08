from dataclasses import dataclass
from typing import Any

from utils.osm_tag_mapper import (
    OsmTagFilter,
    POIDefinition,
    find_cuisine_definition,
    find_first_connector,
    find_poi_definition,
    normalize_query_text,
)


DEFAULT_RADIUS_METERS = 500
MAX_RADIUS_METERS = 5000
SUPPORTED_ELEMENT_TYPES = ("node", "way", "relation")


class NaturalLanguageQueryError(ValueError):
    pass


class BboxValidationError(ValueError):
    pass


class RadiusValidationError(ValueError):
    pass


class PointValidationError(ValueError):
    pass


@dataclass(frozen=True)
class Bbox:
    south: float
    west: float
    north: float
    east: float

    def to_overpass(self) -> str:
        return ",".join(
            _format_coordinate(value)
            for value in (self.south, self.west, self.north, self.east)
        )

    def to_display(self) -> str:
        return f"({self.to_overpass()})"


@dataclass(frozen=True)
class Point:
    lat: float
    lng: float

    def to_overpass(self) -> str:
        return f"{_format_coordinate(self.lat)},{_format_coordinate(self.lng)}"


@dataclass(frozen=True)
class ParsedIntent:
    target: str
    target_filters: tuple[OsmTagFilter, ...]
    nearby_condition: str | None
    anchor_filters: tuple[OsmTagFilter, ...]
    radius_meters: int
    bbox: Bbox


@dataclass(frozen=True)
class ParsedPointIntent:
    target: str
    target_filters: tuple[OsmTagFilter, ...]
    nearby_condition: str | None
    anchor_filters: tuple[OsmTagFilter, ...]
    radius_meters: int
    nearby_radius_meters: int | None
    point: Point


def validate_bbox(raw_bbox: Any) -> Bbox:
    if not isinstance(raw_bbox, dict):
        raise BboxValidationError(
            "bbox is required and must include south, west, north, and east."
        )

    missing_keys = [
        key for key in ("south", "west", "north", "east") if key not in raw_bbox
    ]
    if missing_keys:
        joined_keys = ", ".join(missing_keys)
        raise BboxValidationError(f"bbox is missing required field(s): {joined_keys}.")

    try:
        south = float(raw_bbox["south"])
        west = float(raw_bbox["west"])
        north = float(raw_bbox["north"])
        east = float(raw_bbox["east"])
    except (TypeError, ValueError) as exc:
        raise BboxValidationError(
            "bbox values must be valid numbers for south, west, north, and east."
        ) from exc

    if not -90 <= south <= 90 or not -90 <= north <= 90:
        raise BboxValidationError("bbox south and north must be between -90 and 90.")
    if not -180 <= west <= 180 or not -180 <= east <= 180:
        raise BboxValidationError("bbox west and east must be between -180 and 180.")
    if south >= north:
        raise BboxValidationError("bbox south must be less than north.")
    if west >= east:
        raise BboxValidationError("bbox west must be less than east.")

    return Bbox(south=south, west=west, north=north, east=east)


def validate_point(raw_lat: Any, raw_lng: Any) -> Point:
    if raw_lat is None:
        raise PointValidationError("lat is required.")
    if raw_lng is None:
        raise PointValidationError("lng is required.")

    try:
        lat = float(raw_lat)
        lng = float(raw_lng)
    except (TypeError, ValueError) as exc:
        raise PointValidationError("lat and lng must be valid numbers.") from exc

    if not -90 <= lat <= 90:
        raise PointValidationError("lat must be between -90 and 90.")
    if not -180 <= lng <= 180:
        raise PointValidationError("lng must be between -180 and 180.")

    return Point(lat=lat, lng=lng)


def normalize_radius(raw_radius: Any) -> int:
    if raw_radius is None:
        return DEFAULT_RADIUS_METERS

    try:
        radius = int(raw_radius)
    except (TypeError, ValueError) as exc:
        raise RadiusValidationError("radiusMeters must be a valid integer.") from exc

    if radius <= 0:
        raise RadiusValidationError("radiusMeters must be greater than zero.")

    return min(radius, MAX_RADIUS_METERS)


def parse_natural_language_query(
    query: str,
    bbox: Bbox,
    radius_meters: int,
) -> ParsedIntent:
    normalized_query = normalize_query_text(query)
    if not normalized_query:
        raise NaturalLanguageQueryError(
            "Unable to detect a valid OSM intent from the natural language query"
        )

    connector = find_first_connector(normalized_query)
    if connector:
        _, connector_start, connector_end = connector
        target_text = normalized_query[:connector_start].strip()
        anchor_text = normalized_query[connector_end:].strip()
    else:
        target_text = normalized_query
        anchor_text = ""

    target_poi = detect_target_poi(target_text)
    if not target_poi:
        raise NaturalLanguageQueryError(
            "Unable to detect a valid OSM intent from the natural language query"
        )

    anchor_poi = detect_anchor_poi(anchor_text) if anchor_text else None
    if connector and not anchor_poi:
        raise NaturalLanguageQueryError(
            "Unable to detect a valid OSM intent from the natural language query"
        )

    cuisine = find_cuisine_definition(target_text)
    target_filters = _build_target_filters(target_poi, cuisine is not None)
    target_name = target_poi.display_name

    if cuisine:
        target_filters = (*target_filters, cuisine.filter)
        target_name = f"{cuisine.display_name} {target_name}"

    return ParsedIntent(
        target=target_name,
        target_filters=target_filters,
        nearby_condition=anchor_poi.display_name if anchor_poi else None,
        anchor_filters=anchor_poi.filters if anchor_poi else (),
        radius_meters=radius_meters,
        bbox=bbox,
    )


def parse_natural_language_query_for_point(
    query: str,
    point: Point,
    radius_meters: int,
    nearby_radius_meters: int | None,
) -> ParsedPointIntent:
    normalized_query = normalize_query_text(query)
    if not normalized_query:
        raise NaturalLanguageQueryError(
            "Unable to detect a valid OSM intent from the natural language query"
        )

    connector = find_first_connector(normalized_query)
    if connector:
        _, connector_start, connector_end = connector
        target_text = normalized_query[:connector_start].strip()
        anchor_text = normalized_query[connector_end:].strip()
    else:
        target_text = normalized_query
        anchor_text = ""

    target_poi = detect_target_poi(target_text)
    if not target_poi:
        raise NaturalLanguageQueryError(
            "Unable to detect a valid OSM intent from the natural language query"
        )

    anchor_poi = detect_anchor_poi(anchor_text) if anchor_text else None
    if connector and not anchor_poi:
        raise NaturalLanguageQueryError(
            "Unable to detect a valid OSM intent from the natural language query"
        )

    cuisine = find_cuisine_definition(target_text)
    target_filters = _build_target_filters(target_poi, cuisine is not None)
    target_name = target_poi.display_name

    if cuisine:
        target_filters = (*target_filters, cuisine.filter)
        target_name = f"{cuisine.display_name} {target_name}"

    return ParsedPointIntent(
        target=target_name,
        target_filters=target_filters,
        nearby_condition=anchor_poi.display_name if anchor_poi else None,
        anchor_filters=anchor_poi.filters if anchor_poi else (),
        radius_meters=radius_meters,
        nearby_radius_meters=nearby_radius_meters if anchor_poi else None,
        point=point,
    )


def detect_target_poi(text: str) -> POIDefinition | None:
    poi = find_poi_definition(text)
    if poi:
        return poi

    cuisine = find_cuisine_definition(text)
    if cuisine:
        return POIDefinition(
            id="restaurant",
            display_name="restaurants",
            filters=(OsmTagFilter("amenity", "restaurant"),),
            terms=(),
        )

    return None


def detect_anchor_poi(text: str) -> POIDefinition | None:
    return find_poi_definition(text)


def build_overpass_ql(intent: ParsedIntent) -> str:
    bbox = intent.bbox.to_overpass()

    if intent.anchor_filters:
        anchor_lines = _build_element_lines(intent.anchor_filters, f"({bbox})")
        target_lines = _build_element_lines(
            intent.target_filters,
            f"(around.anchors:{intent.radius_meters})",
        )

        return "\n".join(
            [
                "[out:json][timeout:30];",
                "(",
                *anchor_lines,
                ")->.anchors;",
                "",
                "(",
                *target_lines,
                ");",
                "",
                "out center tags;",
            ]
        )

    target_lines = _build_element_lines(intent.target_filters, f"({bbox})")
    return "\n".join(
        [
            "[out:json][timeout:30];",
            "(",
            *target_lines,
            ");",
            "",
            "out center tags;",
        ]
    )


def build_overpass_ql_for_point(intent: ParsedPointIntent) -> str:
    point = intent.point.to_overpass()

    if intent.anchor_filters and intent.nearby_radius_meters is not None:
        anchor_lines = _build_element_lines(
            intent.anchor_filters,
            f"(around:{intent.radius_meters},{point})",
        )
        target_lines = _build_element_lines(
            intent.target_filters,
            f"(around.anchors:{intent.nearby_radius_meters})",
        )

        return "\n".join(
            [
                "[out:json][timeout:30];",
                "(",
                *anchor_lines,
                ")->.anchors;",
                "",
                "(",
                *target_lines,
                ");",
                "",
                "out center tags;",
            ]
        )

    target_lines = _build_element_lines(
        intent.target_filters,
        f"(around:{intent.radius_meters},{point})",
    )
    return "\n".join(
        [
            "[out:json][timeout:30];",
            "(",
            *target_lines,
            ");",
            "",
            "out center tags;",
        ]
    )


def generate_overpass_query_from_nlq(
    query: str,
    raw_bbox: Any,
    raw_radius_meters: Any,
) -> dict[str, Any]:
    bbox = validate_bbox(raw_bbox)
    radius_meters = normalize_radius(raw_radius_meters)
    intent = parse_natural_language_query(query, bbox, radius_meters)
    overpass_ql = build_overpass_ql(intent)

    return {
        "naturalLanguageQuery": query,
        "overpassQL": overpass_ql,
        "explanation": _build_explanation(intent),
        "detectedIntent": {
            "target": intent.target,
            "nearbyCondition": intent.nearby_condition,
            "radiusMeters": intent.radius_meters,
            "bbox": intent.bbox.to_display(),
        },
    }


def generate_overpass_query_from_point_nlq(
    query: str,
    raw_lat: Any,
    raw_lng: Any,
    raw_radius_meters: Any,
    raw_nearby_radius_meters: Any = None,
) -> dict[str, Any]:
    point = validate_point(raw_lat, raw_lng)
    radius_meters = normalize_radius(raw_radius_meters)
    nearby_radius_meters = (
        normalize_radius(raw_nearby_radius_meters)
        if raw_nearby_radius_meters is not None
        else DEFAULT_RADIUS_METERS
    )
    intent = parse_natural_language_query_for_point(
        query=query,
        point=point,
        radius_meters=radius_meters,
        nearby_radius_meters=nearby_radius_meters,
    )
    overpass_ql = build_overpass_ql_for_point(intent)

    return {
        "naturalLanguageQuery": query,
        "overpassQL": overpass_ql,
        "explanation": _build_point_explanation(intent),
        "detectedIntent": {
            "target": intent.target,
            "nearbyCondition": intent.nearby_condition,
            "radiusMeters": intent.radius_meters,
            "nearbyRadiusMeters": intent.nearby_radius_meters,
            "center": {
                "lat": intent.point.lat,
                "lng": intent.point.lng,
            },
        },
    }


def _build_target_filters(
    target_poi: POIDefinition,
    has_cuisine_filter: bool,
) -> tuple[OsmTagFilter, ...]:
    if target_poi.id in {"restaurant", "fast_food"} and has_cuisine_filter:
        return (OsmTagFilter("amenity", "restaurant|fast_food", "~"),)

    return target_poi.filters


def _build_element_lines(
    filters: tuple[OsmTagFilter, ...],
    area_clause: str,
) -> list[str]:
    selector = "".join(_format_filter(filter_item) for filter_item in filters)
    return [
        f"  {element_type}{selector}{area_clause};"
        for element_type in SUPPORTED_ELEMENT_TYPES
    ]


def _format_filter(filter_item: OsmTagFilter) -> str:
    suffix = ", i" if filter_item.case_insensitive else ""
    return (
        f'["{filter_item.key}"{filter_item.operator}"{filter_item.value}"{suffix}]'
    )


def _format_coordinate(value: float) -> str:
    return f"{value:.15g}"


def _build_point_explanation(intent: ParsedPointIntent) -> str:
    if intent.nearby_condition and intent.nearby_radius_meters is not None:
        return (
            f"Generated a point-radius Overpass query that first selects "
            f"{intent.nearby_condition} within {intent.radius_meters} meters of "
            f"the center point, then selects {intent.target} within "
            f"{intent.nearby_radius_meters} meters of those anchors."
        )

    return (
        f"Generated a point-radius Overpass query that selects {intent.target} "
        f"within {intent.radius_meters} meters of the center point."
    )


def _build_explanation(intent: ParsedIntent) -> str:
    if intent.nearby_condition:
        return (
            f"Generated a nearby Overpass query that first selects "
            f"{intent.nearby_condition} inside the bounding box, then selects "
            f"{intent.target} within {intent.radius_meters} meters of those anchors."
        )

    return (
        f"Generated an Overpass query that selects {intent.target} inside the "
        "provided bounding box."
    )
