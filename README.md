# Overpass Query Executor API

Small FastAPI backend for preparing and executing dynamic Overpass QL queries.

## Install

```bash
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

Or run it with Uvicorn directly:

```bash
uvicorn main:app --reload
```

Open Swagger UI:

```text
http://127.0.0.1:8000/docs
```

## Workflow

Use two endpoints:

```text
POST /overpass/to-json
POST /overpass/execute
```

## 1. Convert Raw Query To JSON

Endpoint:

```text
POST /overpass/to-json
```

In Swagger UI, set the request body content type to `text/plain`, then paste the Overpass QL exactly as written:

```text
[out:json][timeout:25];
nwr["amenity"="restaurant"](21.45,39.18,21.55,39.28);
out center;
```

Response example:

```json
{
  "query": "[out:json][timeout:25];\nnwr[\"amenity\"=\"restaurant\"](21.45,39.18,21.55,39.28);\nout center;"
}
```

## 2. Execute The Query

Endpoint:

```text
POST /overpass/execute
```

Paste the JSON returned from `/overpass/to-json`, or send a JSON body directly:

```json
{
  "query": "[out:json][timeout:25];\n\nnwr[\"amenity\"=\"restaurant\"](21.45,39.18,21.55,39.28);\n\nout center;"
}
```

The response is the raw JSON returned by Overpass. A successful response should include an `elements` array with matching map objects.

## Working Overpass QL Examples

The bounding box order is:

```text
(south,west,north,east)
```

Restaurants in Jeddah:

```overpassql
[out:json][timeout:25];

nwr["amenity"="restaurant"](21.45,39.18,21.55,39.28);

out center;
```

Cafes in Jeddah:

```overpassql
[out:json][timeout:25];

nwr["amenity"="cafe"](21.45,39.18,21.55,39.28);

out center;
```

Hotels in central Jeddah:

```overpassql
[out:json][timeout:25];

nwr["tourism"="hotel"](21.48,39.15,21.62,39.25);

out center;
```

Fuel stations in Makkah:

```overpassql
[out:json][timeout:25];

nwr["amenity"="fuel"](21.36,39.79,21.46,39.90);

out center;
```

Pharmacies in north Jeddah:

```overpassql
[out:json][timeout:25];

nwr["amenity"="pharmacy"](21.55,39.12,21.70,39.25);

out center;
```
