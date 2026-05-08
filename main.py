import os
from typing import Any

import httpx
import uvicorn
from fastapi import Body, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

from services.nlq_to_overpass_service import (
    BboxValidationError,
    NaturalLanguageQueryError,
    PointValidationError,
    RadiusValidationError,
    generate_overpass_query_from_point_nlq,
    generate_overpass_query_from_nlq,
)


OVERPASS_API_URL = os.getenv(
    "OVERPASS_API_URL",
    "https://overpass-api.de/api/interpreter",
)
OVERPASS_TIMEOUT_SECONDS = float(os.getenv("OVERPASS_TIMEOUT_SECONDS", "90"))
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "9000"))
RAW_QUERY_EXAMPLE = (
    '[out:json][timeout:25];area["name"="north jeddah"]->.a;'
    '(node["amenity"="restaurant"](area.a);'
    'way["amenity"="restaurant"](area.a);'
    'relation["amenity"="restaurant"](area.a););'
    'out;>;out skel qt;'
)


app = FastAPI(
    title="Overpass Query Executor API",
    description="Execute dynamic Overpass QL queries and return raw JSON results.",
    version="1.0.0",
)


class OverpassQueryRequest(BaseModel):
    query: str = Field(
        ...,
        description="Any valid Overpass QL query. Include [out:json] to receive JSON.",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "query": """[out:json][timeout:30];
(
  node["amenity"="cafe"](21.390443,39.014236,21.710443,39.334236);
);
out body;"""
                }
            ]
        }
    }


class PlainTextOverpassQueryRequest(BaseModel):
    query: str | None = Field(
        None,
        description="Escaped Overpass QL string to convert to plain text.",
    )
    overpassQL: str | None = Field(
        None,
        description="Escaped Overpass QL string returned by a generator endpoint.",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "overpassQL": '[out:json][timeout:30];\\n(\\n  node["amenity"~"restaurant|fast_food"]["cuisine"~"pizza", i](around:2000,21.4949786879731,39.2392006251267);\\n);\\n\\nout center tags;'
                }
            ]
        }
    }


class GenerateQueryBboxRequest(BaseModel):
    south: Any | None = Field(
        None,
        description="Southern latitude of the bounding box.",
        examples=[21.390443],
    )
    west: Any | None = Field(
        None,
        description="Western longitude of the bounding box.",
        examples=[39.014236],
    )
    north: Any | None = Field(
        None,
        description="Northern latitude of the bounding box.",
        examples=[21.710443],
    )
    east: Any | None = Field(
        None,
        description="Eastern longitude of the bounding box.",
        examples=[39.334236],
    )


class GenerateOverpassQueryRequest(BaseModel):
    query: Any | None = Field(
        None,
        description="Natural language search phrase in Arabic or English.",
        examples=["ابحث عن مطاعم بيتزا ولكن بشرط أن يكون جنبها مسجد"],
    )
    bbox: GenerateQueryBboxRequest | None = Field(
        None,
        description="Bounding box for anchor objects in south, west, north, east order.",
    )
    radiusMeters: Any | None = Field(
        500,
        description="Search radius around detected anchor objects. Defaults to 500 and is capped at 5000.",
        examples=[500],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "query": "ابحث عن مطاعم بيتزا ولكن بشرط أن يكون جنبها مسجد",
                    "bbox": {
                        "south": 21.390443,
                        "west": 39.014236,
                        "north": 21.710443,
                        "east": 39.334236,
                    },
                    "radiusMeters": 500,
                }
            ]
        }
    }


class DetectedIntentResponse(BaseModel):
    target: str
    nearbyCondition: str | None
    radiusMeters: int
    bbox: str


class GenerateOverpassQueryResponse(BaseModel):
    naturalLanguageQuery: str
    overpassQL: str
    explanation: str
    detectedIntent: DetectedIntentResponse

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "naturalLanguageQuery": (
                        "ابحث عن مطاعم بيتزا ولكن بشرط أن يكون جنبها مسجد"
                    ),
                    "overpassQL": """[out:json][timeout:30];
(
  node["amenity"="place_of_worship"]["religion"="muslim"](21.390443,39.014236,21.710443,39.334236);
  way["amenity"="place_of_worship"]["religion"="muslim"](21.390443,39.014236,21.710443,39.334236);
  relation["amenity"="place_of_worship"]["religion"="muslim"](21.390443,39.014236,21.710443,39.334236);
)->.anchors;

(
  node["amenity"~"restaurant|fast_food"]["cuisine"~"pizza", i](around.anchors:500);
  way["amenity"~"restaurant|fast_food"]["cuisine"~"pizza", i](around.anchors:500);
  relation["amenity"~"restaurant|fast_food"]["cuisine"~"pizza", i](around.anchors:500);
);

out center tags;""",
                    "explanation": (
                        "Generated a nearby Overpass query that first selects "
                        "mosques inside the bounding box, then selects pizza "
                        "restaurants within 500 meters of those anchors."
                    ),
                    "detectedIntent": {
                        "target": "pizza restaurants",
                        "nearbyCondition": "mosques",
                        "radiusMeters": 500,
                        "bbox": "(21.390443,39.014236,21.710443,39.334236)",
                    },
                }
            ]
        }
    }


class GeneratePointOverpassQueryRequest(BaseModel):
    query: Any | None = Field(
        None,
        description="Natural language search phrase in Arabic or English.",
        examples=["pizza restaurants near mosque"],
    )
    lat: Any | None = Field(
        None,
        description="Center latitude for the circular search area.",
        examples=[21.4935],
    )
    lng: Any | None = Field(
        None,
        description="Center longitude for the circular search area.",
        examples=[39.2503],
    )
    radiusMeters: Any | None = Field(
        500,
        description="Search radius around the center point. Defaults to 500 and is capped at 5000.",
        examples=[2000],
    )
    nearbyRadiusMeters: Any | None = Field(
        None,
        description="Optional distance from anchor objects when the query includes a nearby relationship. Defaults to 500 and is capped at 5000.",
        examples=[500],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "query": "pizza restaurants near mosque",
                    "lat": 21.4935,
                    "lng": 39.2503,
                    "radiusMeters": 2000,
                    "nearbyRadiusMeters": 500,
                },
                {
                    "query": "cafes",
                    "lat": 21.4935,
                    "lng": 39.2503,
                    "radiusMeters": 2000,
                },
            ]
        }
    }


class PointCenterResponse(BaseModel):
    lat: float
    lng: float


class DetectedPointIntentResponse(BaseModel):
    target: str
    nearbyCondition: str | None
    radiusMeters: int
    nearbyRadiusMeters: int | None
    center: PointCenterResponse


class GeneratePointOverpassQueryResponse(BaseModel):
    naturalLanguageQuery: str
    overpassQL: str
    explanation: str
    detectedIntent: DetectedPointIntentResponse

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "naturalLanguageQuery": "pizza restaurants near mosque",
                    "overpassQL": """[out:json][timeout:30];
(
  node["amenity"="place_of_worship"]["religion"="muslim"](around:2000,21.4935,39.2503);
  way["amenity"="place_of_worship"]["religion"="muslim"](around:2000,21.4935,39.2503);
  relation["amenity"="place_of_worship"]["religion"="muslim"](around:2000,21.4935,39.2503);
)->.anchors;

(
  node["amenity"~"restaurant|fast_food"]["cuisine"~"pizza", i](around.anchors:500);
  way["amenity"~"restaurant|fast_food"]["cuisine"~"pizza", i](around.anchors:500);
  relation["amenity"~"restaurant|fast_food"]["cuisine"~"pizza", i](around.anchors:500);
);

out center tags;""",
                    "explanation": (
                        "Generated a point-radius Overpass query that first "
                        "selects mosques within 2000 meters of the center point, "
                        "then selects pizza restaurants within 500 meters of "
                        "those anchors."
                    ),
                    "detectedIntent": {
                        "target": "pizza restaurants",
                        "nearbyCondition": "mosques",
                        "radiusMeters": 2000,
                        "nearbyRadiusMeters": 500,
                        "center": {
                            "lat": 21.4935,
                            "lng": 39.2503,
                        },
                    },
                }
            ]
        }
    }


def _short_response_text(text: str, limit: int = 1000) -> str:
    """Keep upstream error details useful without returning a huge response."""
    cleaned = text.strip()
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[:limit]}..."


def _plain_overpass_query_from_payload(
    payload: PlainTextOverpassQueryRequest | str | None,
) -> str:
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request body is required.",
        )

    if isinstance(payload, str):
        query = payload
    else:
        query = payload.query if payload.query is not None else payload.overpassQL

    if not isinstance(query, str) or not query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="query or overpassQL is required and must be a non-empty string.",
        )

    return _decode_common_json_escapes(query.strip())


def _decode_common_json_escapes(query: str) -> str:
    return (
        query.replace("\\r\\n", "\n")
        .replace("\\n", "\n")
        .replace("\\r", "\n")
        .replace("\\t", "\t")
        .replace('\\"', '"')
    )


async def _execute_overpass_query(query: str) -> Any:
    query = query.strip()

    if not query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query must not be empty.",
        )

    try:
        timeout = httpx.Timeout(OVERPASS_TIMEOUT_SECONDS, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                OVERPASS_API_URL,
                data={"data": query},
                headers={"User-Agent": "queryExec-fastapi/1.0"},
            )
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Overpass API request timed out.",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Network error while contacting Overpass API: {exc}",
        ) from exc

    if response.status_code == status.HTTP_400_BAD_REQUEST:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Invalid Overpass query.",
                "overpass_status_code": response.status_code,
                "overpass_response": _short_response_text(response.text),
            },
        )

    if response.status_code == status.HTTP_504_GATEWAY_TIMEOUT:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail={
                "message": "Overpass API timed out or is too busy for this query.",
                "hint": (
                    "Try a smaller area, fewer element types, fewer recursion steps, "
                    "or increase the [timeout] value inside the Overpass query."
                ),
                "overpass_status_code": response.status_code,
                "overpass_response": _short_response_text(response.text),
            },
        )

    if response.is_error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "message": "Overpass API returned an error.",
                "overpass_status_code": response.status_code,
                "overpass_response": _short_response_text(response.text),
            },
        )

    try:
        return response.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "message": "Overpass API returned a non-JSON response.",
                "overpass_status_code": response.status_code,
                "overpass_response": _short_response_text(response.text),
            },
        ) from exc


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(Exception)
async def unexpected_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Unexpected server error."},
    )


@app.post(
    "/overpass/to-json",
    tags=["Overpass"],
    status_code=status.HTTP_200_OK,
    summary="Convert raw Overpass QL to JSON body",
    response_model=OverpassQueryRequest,
    responses={
        400: {"description": "Empty query."},
        500: {"description": "Unexpected server error."},
    },
)
async def convert_overpass_query_to_json(
    query: str = Body(
        ...,
        media_type="text/plain",
        description="Paste raw Overpass QL exactly as written.",
        examples=[RAW_QUERY_EXAMPLE],
    ),
) -> OverpassQueryRequest:
    query = query.strip()

    if not query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query must not be empty.",
        )

    return OverpassQueryRequest(query=query)


@app.post(
    "/api/overpass/to-plain-text",
    tags=["Overpass"],
    status_code=status.HTTP_200_OK,
    summary="Convert escaped Overpass QL JSON to plain text",
    description=(
        "Converts an escaped Overpass QL string from a JSON body into text/plain "
        "so it can be copied directly into Overpass Turbo."
    ),
    response_class=PlainTextResponse,
    responses={
        200: {
            "description": "Plain Overpass QL text.",
            "content": {
                "text/plain": {
                    "example": """[out:json][timeout:30];
(
  node["amenity"~"restaurant|fast_food"]["cuisine"~"pizza", i](around:2000,21.4949786879731,39.2392006251267);
);

out center tags;"""
                }
            },
        },
        400: {
            "description": "Missing or empty query.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": (
                            "query or overpassQL is required and must be a "
                            "non-empty string."
                        )
                    }
                }
            },
        },
        500: {"description": "Unexpected server error."},
    },
)
async def convert_overpass_json_to_plain_text(
    payload: PlainTextOverpassQueryRequest | str | None = Body(None),
) -> PlainTextResponse:
    return PlainTextResponse(
        content=_plain_overpass_query_from_payload(payload),
        media_type="text/plain",
    )


@app.post(
    "/api/overpass/generate-query",
    tags=["Overpass"],
    status_code=status.HTTP_200_OK,
    summary="Generate Overpass QL from natural language",
    description=(
        "Converts an Arabic or English natural language POI search into a valid "
        "Overpass QL string. This endpoint only generates the query and does not "
        "execute it."
    ),
    response_model=GenerateOverpassQueryResponse,
    responses={
        400: {
            "description": "Missing or invalid query, bbox, or radiusMeters.",
            "content": {
                "application/json": {
                    "examples": {
                        "missingQuery": {
                            "summary": "Missing natural language query",
                            "value": {
                                "detail": (
                                    "query is required and must be a non-empty string."
                                )
                            },
                        },
                        "invalidBbox": {
                            "summary": "Invalid bounding box",
                            "value": {
                                "detail": (
                                    "bbox is required and must include south, west, "
                                    "north, and east."
                                )
                            },
                        },
                    }
                }
            },
        },
        422: {
            "description": "Unable to detect a valid OSM intent.",
            "content": {
                "application/json": {
                    "example": {
                        "error": (
                            "Unable to detect a valid OSM intent from the natural "
                            "language query"
                        ),
                        "suggestion": (
                            "Try something like: restaurants near mosque, cafes "
                            "near university, pharmacies near hospital"
                        ),
                    }
                }
            },
        },
        500: {"description": "Unexpected server error."},
    },
)
async def generate_overpass_query(
    payload: GenerateOverpassQueryRequest | None = Body(None),
) -> GenerateOverpassQueryResponse | JSONResponse:
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request body is required.",
        )

    if not isinstance(payload.query, str) or not payload.query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="query is required and must be a non-empty string.",
        )

    raw_bbox = payload.bbox.model_dump(exclude_none=True) if payload.bbox else None

    try:
        result = generate_overpass_query_from_nlq(
            query=payload.query.strip(),
            raw_bbox=raw_bbox,
            raw_radius_meters=payload.radiusMeters,
        )
    except (BboxValidationError, RadiusValidationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except NaturalLanguageQueryError:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": (
                    "Unable to detect a valid OSM intent from the natural language "
                    "query"
                ),
                "suggestion": (
                    "Try something like: restaurants near mosque, cafes near "
                    "university, pharmacies near hospital"
                ),
            },
        )

    return GenerateOverpassQueryResponse(**result)


@app.post(
    "/api/overpass/generate-query-by-point",
    tags=["Overpass"],
    status_code=status.HTTP_200_OK,
    summary="Generate Overpass QL from natural language around a point",
    description=(
        "Converts an Arabic or English natural language POI search into a valid "
        "Overpass QL string using a center point and radius. This endpoint only "
        "generates the query and does not execute it."
    ),
    response_model=GeneratePointOverpassQueryResponse,
    responses={
        400: {
            "description": "Missing or invalid query, lat, lng, radiusMeters, or nearbyRadiusMeters.",
            "content": {
                "application/json": {
                    "examples": {
                        "missingQuery": {
                            "summary": "Missing natural language query",
                            "value": {
                                "detail": (
                                    "query is required and must be a non-empty string."
                                )
                            },
                        },
                        "missingLat": {
                            "summary": "Missing latitude",
                            "value": {"detail": "lat is required."},
                        },
                        "invalidLng": {
                            "summary": "Invalid longitude",
                            "value": {"detail": "lng must be between -180 and 180."},
                        },
                    }
                }
            },
        },
        422: {
            "description": "Unable to detect a valid OSM intent.",
            "content": {
                "application/json": {
                    "example": {
                        "error": (
                            "Unable to detect a valid OSM intent from the natural "
                            "language query"
                        ),
                        "suggestion": (
                            "Try something like: restaurants near mosque, cafes "
                            "near university, pharmacies near hospital"
                        ),
                    }
                }
            },
        },
        500: {"description": "Unexpected server error."},
    },
)
async def generate_overpass_query_by_point(
    payload: GeneratePointOverpassQueryRequest | None = Body(None),
) -> GeneratePointOverpassQueryResponse | JSONResponse:
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request body is required.",
        )

    if not isinstance(payload.query, str) or not payload.query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="query is required and must be a non-empty string.",
        )

    try:
        result = generate_overpass_query_from_point_nlq(
            query=payload.query.strip(),
            raw_lat=payload.lat,
            raw_lng=payload.lng,
            raw_radius_meters=payload.radiusMeters,
            raw_nearby_radius_meters=payload.nearbyRadiusMeters,
        )
    except (PointValidationError, RadiusValidationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except NaturalLanguageQueryError:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": (
                    "Unable to detect a valid OSM intent from the natural language "
                    "query"
                ),
                "suggestion": (
                    "Try something like: restaurants near mosque, cafes near "
                    "university, pharmacies near hospital"
                ),
            },
        )

    return GeneratePointOverpassQueryResponse(**result)


@app.post(
    "/overpass/execute",
    tags=["Overpass"],
    status_code=status.HTTP_200_OK,
    summary="Execute an Overpass JSON request body",
    description="Paste the JSON returned from /overpass/to-json into this endpoint.",
    responses={
        400: {"description": "Empty or invalid Overpass query."},
        502: {"description": "Network, upstream, or non-JSON Overpass API error."},
        504: {"description": "Overpass API request timed out."},
        500: {"description": "Unexpected server error."},
    },
)
async def execute_overpass_query(payload: OverpassQueryRequest) -> Any:
    return await _execute_overpass_query(payload.query)


if __name__ == "__main__":
    uvicorn.run(app, host=APP_HOST, port=APP_PORT)
