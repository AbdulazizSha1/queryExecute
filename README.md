# Overpass Query Executor API

A FastAPI service for working with OpenStreetMap Overpass QL.

The API can:

1. Wrap raw Overpass QL text inside a JSON request body.
2. Convert escaped Overpass QL JSON back into plain text for Overpass Turbo.
3. Generate Overpass QL from natural language using either a bounding box or a center point.
4. Execute raw Overpass QL against the Overpass API and return JSON results.

## Quick Start

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the app:

```bash
python main.py
```

Or run with Uvicorn:

```bash
uvicorn main:app --reload 
```

Open Swagger UI:

```text
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/docs
```

## Endpoints

| Method | Endpoint | Purpose | Executes Overpass? |
| --- | --- | --- | --- |
| `GET` | `/health` | Check API health | No |
| `POST` | `/overpass/to-json` | Convert plain Overpass QL text to JSON | No |
| `POST` | `/api/overpass/to-plain-text` | Convert escaped Overpass QL JSON to plain text | No |
| `POST` | `/api/overpass/generate-query` | Generate Overpass QL from natural language with a `bbox` | No |
| `POST` | `/api/overpass/generate-query-by-point` | Generate Overpass QL from natural language around `lat/lng` | No |
| `POST` | `/overpass/execute` | Execute Overpass QL against the Overpass API | Yes |

## Jeddah Coordinates Used In Examples

Approximate points:

| Place | Latitude | Longitude |
| --- | --- | --- |
| King Abdulaziz University | `21.4935` | `39.2503` |
| Al-Balad | `21.4858` | `39.1925` |
| Jeddah Corniche | `21.6117` | `39.1089` |

Useful Jeddah bounding boxes:

```json
{
  "south": 21.390443,
  "west": 39.014236,
  "north": 21.710443,
  "east": 39.334236
}
```

```json
{
  "south": 21.45,
  "west": 39.15,
  "north": 21.55,
  "east": 39.28
}
```

```json
{
  "south": 21.55,
  "west": 39.10,
  "north": 21.70,
  "east": 39.25
}



```

## 1. Convert Plain Overpass QL To JSON

```text
POST /overpass/to-json
```

Use this endpoint when you have raw Overpass QL text and want to wrap it in a JSON body for `/overpass/execute`.

Request content type:

```text
text/plain
```

### Example 1: Restaurants in central Jeddah

Request body:

```overpassql

[out:json][timeout:30];
(
  node["amenity"="restaurant"](21.45,39.15,21.55,39.28);
  way["amenity"="restaurant"](21.45,39.15,21.55,39.28);
  relation["amenity"="restaurant"](21.45,39.15,21.55,39.28);
);

out center tags;

```

Response:

```json
{
  "query": "[out:json][timeout:30];\n(\n  node[\"amenity\"=\"restaurant\"](21.45,39.15,21.55,39.28);\n  way[\"amenity\"=\"restaurant\"](21.45,39.15,21.55,39.28);\n  relation[\"amenity\"=\"restaurant\"](21.45,39.15,21.55,39.28);\n);\n\nout center tags;"
}
```

### Example 2: Cafes in north Jeddah

Request body:

```overpassql
[out:json][timeout:30];
(
  node["amenity"="cafe"](21.55,39.10,21.70,39.25);
  way["amenity"="cafe"](21.55,39.10,21.70,39.25);
  relation["amenity"="cafe"](21.55,39.10,21.70,39.25);
);

out center tags;
```

### Example 3: Pharmacies near Al-Balad

Request body:

```overpassql

[out:json][timeout:30];
(
  node["amenity"="pharmacy"](21.47,39.18,21.50,39.21);
  way["amenity"="pharmacy"](21.47,39.18,21.50,39.21);
  relation["amenity"="pharmacy"](21.47,39.18,21.50,39.21);
);

out center tags;

```

## 2. Convert Escaped Overpass QL JSON To Plain Text

```text
POST /api/overpass/to-plain-text
```

Use this endpoint when an Overpass QL string is inside JSON and contains escaped characters such as `\n` and `\"`.

Accepted body keys:

- `query`
- `overpassQL`

Response content type:

```text
text/plain
```

### Example 1: Pizza restaurants around King Abdulaziz University

Request body:

```json
{
  "overpassQL": "[out:json][timeout:30];\\n(\\n  node[\\\"amenity\\\"~\\\"restaurant|fast_food\\\"][\\\"cuisine\\\"~\\\"pizza\\\", i](around:2000,21.4935,39.2503);\\n  way[\\\"amenity\\\"~\\\"restaurant|fast_food\\\"][\\\"cuisine\\\"~\\\"pizza\\\", i](around:2000,21.4935,39.2503);\\n  relation[\\\"amenity\\\"~\\\"restaurant|fast_food\\\"][\\\"cuisine\\\"~\\\"pizza\\\", i](around:2000,21.4935,39.2503);\\n);\\n\\nout center tags;"
}
```

Response:

```overpassql

[out:json][timeout:30];
(
  node["amenity"~"restaurant|fast_food"]["cuisine"~"pizza", i](around:2000,21.4935,39.2503);
  way["amenity"~"restaurant|fast_food"]["cuisine"~"pizza", i](around:2000,21.4935,39.2503);
  relation["amenity"~"restaurant|fast_food"]["cuisine"~"pizza", i](around:2000,21.4935,39.2503);
);

out center tags;

```

### Example 2: Cafes around Jeddah Corniche

Request body:

```json
{
  "query": "[out:json][timeout:30];\\n(\\n  node[\\\"amenity\\\"=\\\"cafe\\\"](around:1500,21.6117,39.1089);\\n  way[\\\"amenity\\\"=\\\"cafe\\\"](around:1500,21.6117,39.1089);\\n  relation[\\\"amenity\\\"=\\\"cafe\\\"](around:1500,21.6117,39.1089);\\n);\\n\\nout center tags;"
}
```

### Example 3: Pharmacies around Al-Balad

Request body:

```json
{
  "overpassQL": "[out:json][timeout:30];\\n(\\n  node[\\\"amenity\\\"=\\\"pharmacy\\\"](around:1000,21.4858,39.1925);\\n  way[\\\"amenity\\\"=\\\"pharmacy\\\"](around:1000,21.4858,39.1925);\\n  relation[\\\"amenity\\\"=\\\"pharmacy\\\"](around:1000,21.4858,39.1925);\\n);\\n\\nout center tags;"
}
```

## 3. Generate Overpass QL From Natural Language With Bbox

```text
POST /api/overpass/generate-query
```

This endpoint does not execute the query. It only returns a ready-to-use Overpass QL string.

Use it when the search area is a bounding box.

### Request shape

```json
{
  "query": "pizza restaurants near mosque",
  "bbox": {
    "south": 21.390443,
    "west": 39.014236,
    "north": 21.710443,
    "east": 39.334236
  },
  "radiusMeters": 500
}
```

### Example 1: Pizza restaurants near mosques in Jeddah

```json
{
  "query": "pizza restaurants near mosque",
  "bbox": {
    "south": 21.390443,
    "west": 39.014236,
    "north": 21.710443,
    "east": 39.334236
  },
  "radiusMeters": 500
}
```

Meaning:

1. Find mosques inside the bounding box.
2. Find pizza restaurants within 500 meters of those mosques.

### Example 2: Cafes near universities in central Jeddah

```json
{
  "query": "cafes close to university",
  "bbox": {
    "south": 21.45,
    "west": 39.15,
    "north": 21.55,
    "east": 39.28
  },
  "radiusMeters": 700
}
```

### Example 3: Pharmacies beside hospitals

```json
{
  "query": "pharmacies beside hospital",
  "bbox": {
    "south": 21.45,
    "west": 39.15,
    "north": 21.55,
    "east": 39.28
  },
  "radiusMeters": 400
}
```

Response shape:

```json
{
  "naturalLanguageQuery": "pizza restaurants near mosque",
  "overpassQL": "[out:json][timeout:30];\n...\nout center tags;",
  "explanation": "Generated a nearby Overpass query...",
  "detectedIntent": {
    "target": "pizza restaurants",
    "nearbyCondition": "mosques",
    "radiusMeters": 500,
    "bbox": "(21.390443,39.014236,21.710443,39.334236)"
  }
}
```

## 5. Generate Overpass QL From Natural Language Around A Point

```text
POST /api/overpass/generate-query-by-point
```

Use this endpoint when you have a specific center point, such as King Abdulaziz University, and want to search inside a circular area around it.

### radiusMeters vs nearbyRadiusMeters

`radiusMeters` is the search radius around the given `lat/lng`.

`nearbyRadiusMeters` is used only when the natural language query contains a nearby relationship such as `near`, `beside`, `close to`, or `around`. It controls the distance between the target POI and the anchor POI.

Example:

```json
{
  "query": "pizza restaurants near mosque",
  "lat": 21.4935,
  "lng": 39.2503,
  "radiusMeters": 2000,
  "nearbyRadiusMeters": 500
}
```

Meaning:

1. Find mosques within 2000 meters of the center point.
2. Find pizza restaurants within 500 meters of those mosques.

If the query has no nearby relationship, you can omit `nearbyRadiusMeters`.

### Example 1: Pizza restaurants around King Abdulaziz University

```json
{
  "query": "pizza restaurants",
  "lat": 21.4935,
  "lng": 39.2503,
  "radiusMeters": 2000
}
```

### Example 2: Pizza restaurants near mosques around King Abdulaziz University

```json
{
  "query": "pizza restaurants near mosque",
  "lat": 21.4935,
  "lng": 39.2503,
  "radiusMeters": 2000,
  "nearbyRadiusMeters": 500
}
```

### Example 3: Cafes around Jeddah Corniche

```json
{
  "query": "cafes",
  "lat": 21.6117,
  "lng": 39.1089,
  "radiusMeters": 1500
}
```

Response shape:

```json
{
  "naturalLanguageQuery": "pizza restaurants near mosque",
  "overpassQL": "[out:json][timeout:30];\n...\nout center tags;",
  "explanation": "Generated a point-radius Overpass query...",
  "detectedIntent": {
    "target": "pizza restaurants",
    "nearbyCondition": "mosques",
    "radiusMeters": 2000,
    "nearbyRadiusMeters": 500,
    "center": {
      "lat": 21.4935,
      "lng": 39.2503
    }
  }
}
```

## 6. Execute Overpass QL

```text
POST /overpass/execute
```

This is the only endpoint that sends a query to the real Overpass API.

Request content type:

```text
application/json
```

### Example 1: Execute restaurants around King Abdulaziz University

```json
{
  "query": "[out:json][timeout:30];\n(\n  node[\"amenity\"=\"restaurant\"](around:2000,21.4935,39.2503);\n  way[\"amenity\"=\"restaurant\"](around:2000,21.4935,39.2503);\n  relation[\"amenity\"=\"restaurant\"](around:2000,21.4935,39.2503);\n);\n\nout center tags;"
}
```

### Example 2: Execute cafes in north Jeddah

```json
{
  "query": "[out:json][timeout:30];\n(\n  node[\"amenity\"=\"cafe\"](21.55,39.10,21.70,39.25);\n  way[\"amenity\"=\"cafe\"](21.55,39.10,21.70,39.25);\n  relation[\"amenity\"=\"cafe\"](21.55,39.10,21.70,39.25);\n);\n\nout center tags;"
}
```

### Example 3: Execute pharmacies around Al-Balad

```json
{
  "query": "[out:json][timeout:30];\n(\n  node[\"amenity\"=\"pharmacy\"](around:1000,21.4858,39.1925);\n  way[\"amenity\"=\"pharmacy\"](around:1000,21.4858,39.1925);\n  relation[\"amenity\"=\"pharmacy\"](around:1000,21.4858,39.1925);\n);\n\nout center tags;"
}
```

Expected response shape:

```json
{
  "version": 0.6,
  "generator": "Overpass API",
  "elements": [
    {
      "type": "node",
      "id": 123456,
      "lat": 21.4935,
      "lon": 39.2503,
      "tags": {
        "amenity": "restaurant",
        "name": "Example Restaurant"
      }
    }
  ]
}
```

If `elements` is empty:

```json
{
  "elements": []
}
```

Possible reasons:

- The selected area has no matching OpenStreetMap data.
- The radius or bounding box is too small.
- The tag is not commonly mapped in that area.

## Supported Natural Language Terms

The parser maps common Arabic and English terms to OSM tags.

| User term | OSM tags |
| --- | --- |
| `mosque` and Arabic mosque terms | `amenity=place_of_worship`, `religion=muslim` |
| `restaurant`, `restaurants` | `amenity=restaurant` |
| `fast food` | `amenity=fast_food` |
| `cafe`, `cafes`, `coffee shop` | `amenity=cafe` |
| `pharmacy`, `pharmacies` | `amenity=pharmacy` |
| `hospital`, `hospitals` | `amenity=hospital` |
| `school`, `schools` | `amenity=school` |
| `university`, `college` | `amenity=university` |
| `park`, `garden` | `leisure=park` |
| `pizza`, `pizzeria` | `cuisine=pizza` |

Nearby relationship terms include:

```text
near, close to, beside, around, next to, nearby, within
```

Arabic nearby terms are also supported by the parser, such as equivalent words for near, beside, and around.

## Validation And Errors

### 400 Bad Request

Returned when request input is missing or invalid.

Common cases:

- `query` is missing or empty.
- `bbox` is missing or invalid.
- `lat` or `lng` is missing or invalid.
- `radiusMeters` is not a valid positive integer.

Example:

```json
{
  "detail": "query is required and must be a non-empty string."
}
```

### 422 Unprocessable Entity

Returned when the natural language query cannot be mapped to a valid OSM intent.

```json
{
  "error": "Unable to detect a valid OSM intent from the natural language query",
  "suggestion": "Try something like: restaurants near mosque, cafes near university, pharmacies near hospital"
}
```

### 502 Bad Gateway Or 504 Gateway Timeout

Returned only by `/overpass/execute` when the upstream Overpass API fails, returns non-JSON data, or times out.

## Notes

- Generator endpoints do not execute queries. They only generate Overpass QL.
- Use `/api/overpass/to-plain-text` when you want to copy generated Overpass QL into Overpass Turbo without escaped `\n` and `\"`.
- `radiusMeters` defaults to `500` and is capped at `5000`.
- `nearbyRadiusMeters` is optional and only applies to point-based nearby relationship queries.
- OpenStreetMap data changes over time, so result counts can change.
