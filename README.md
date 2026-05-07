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
[out:json][timeout:25];area["name"="north jeddah"]->.a;(node["amenity"="restaurant"](area.a);way["amenity"="restaurant"](area.a);relation["amenity"="restaurant"](area.a););out;>;out skel qt;
```

Response example:

```json
{
  "query": "[out:json][timeout:25];area[\"name\"=\"north jeddah\"]->.a;(node[\"amenity\"=\"restaurant\"](area.a);way[\"amenity\"=\"restaurant\"](area.a);relation[\"amenity\"=\"restaurant\"](area.a););out;>;out skel qt;"
}
```
