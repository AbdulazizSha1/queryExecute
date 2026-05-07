import os
from typing import Any

import httpx
import uvicorn
from fastapi import Body, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


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


def _short_response_text(text: str, limit: int = 1000) -> str:
    """Keep upstream error details useful without returning a huge response."""
    cleaned = text.strip()
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[:limit]}..."


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
