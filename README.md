# Overpass Query Executor API

واجهة API بسيطة مبنية بـ FastAPI عشان تساعدك تشتغل مع Overpass QL على خطوتين واضحتين:

1. ترسل استعلام Overpass QL كنص عادي.
2. تحصل عليه داخل JSON جاهز.
3. ترسل الـ JSON للتنفيذ وتستقبل نتائج Overpass.

## الفكرة بسرعة

عندك endpointين مهمين:

| Endpoint | ماذا يفعل؟ | هل ينفذ الاستعلام؟ |
| --- | --- | --- |
| `POST /overpass/to-json` | يحول نص Overpass QL الخام إلى JSON | لا |
| `POST /overpass/execute` | يرسل الاستعلام إلى Overpass API ويرجع النتائج | نعم |

يعني الترتيب الطبيعي هو:

```text
Overpass QL text
        ↓
POST /overpass/to-json
        ↓
JSON body
        ↓
POST /overpass/execute
        ↓
Overpass results
```

## التثبيت

```bash
pip install -r requirements.txt
```

## تشغيل المشروع

```bash
python main.py
```

بعد التشغيل افتح Swagger UI:

```text
http://127.0.0.1:9000/docs
```

تقدر تشغله بـ Uvicorn أيضا:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 9000
```

## Endpoint 1: تحويل Overpass QL إلى JSON

Endpoint:

```text
POST /overpass/to-json
```

هذه endpoint تستقبل الاستعلام كنص عادي `text/plain`.

مهم: هذه endpoint لا تنفذ الاستعلام ولا ترجع أماكن من الخريطة. وظيفتها فقط أنها تلف الاستعلام داخل JSON بالشكل الذي تحتاجه endpoint الثانية.

### طريقة الاستخدام في Swagger

1. افتح:

```text
http://127.0.0.1:9000/docs
```

2. افتح endpoint:

```text
POST /overpass/to-json
```

3. اضغط `Try it out`.
4. تأكد أن نوع الطلب `text/plain`.
5. الصق استعلام Overpass QL مثل هذا:

```overpassql
[out:json][timeout:25];

nwr["amenity"="restaurant"](21.45,39.18,21.55,39.28);

out center 25;
```

### مثال الرد

```json
{
  "query": "[out:json][timeout:25];\n\nnwr[\"amenity\"=\"restaurant\"](21.45,39.18,21.55,39.28);\n\nout center 25;"
}
```

انسخ هذا الرد واستخدمه في endpoint الثانية.

## Endpoint 2: تنفيذ الاستعلام على Overpass

Endpoint:

```text
POST /overpass/execute
```

هذه endpoint تستقبل JSON يحتوي على المفتاح `query`، ثم ترسل الاستعلام إلى Overpass API الحقيقي وترجع لك النتيجة الخام.

### Request body

```json
{
  "query": "[out:json][timeout:25];\n\nnwr[\"amenity\"=\"restaurant\"](21.45,39.18,21.55,39.28);\n\nout center 25;"
}
```

### شكل الرد المتوقع

الرد يرجع من Overpass نفسه، وأهم شيء تبحث عنه هو `elements`.

```json
{
  "version": 0.6,
  "generator": "Overpass API",
  "elements": [
    {
      "type": "node",
      "id": 123456,
      "lat": 21.51,
      "lon": 39.24,
      "tags": {
        "amenity": "restaurant",
        "name": "Example name"
      }
    }
  ]
}
```

إذا رجعت `elements` وفيها عناصر، معناته الاستعلام اشتغل ولقى نتائج.

إذا رجعت:

```json
{
  "elements": []
}
```

فهذا غالبا يعني أن الـ bounding box صغير، أو أن الوسم `tag` غير موجود في المنطقة المختارة.

## أمثلة Overpass QL جاهزة

هذه الأمثلة مختارة على مناطق ووسوم ترجع نتائج فعلية من Overpass. انتبه فقط أن بيانات OpenStreetMap تتغير مع الوقت، فعدد النتائج وأسماؤها ممكن تختلف.

الأمثلة التالية تستخدم `nwr` عشان تجيب:

```text
nodes + ways + relations
```

وتستخدم:

```overpassql
out center 25;
```

عشان ترجع أول 25 نتيجة فقط، ومعها نقطة مركزية للعناصر الكبيرة مثل المباني والطرق.

صيغة الـ bounding box هي:

```text
(south, west, north, east)
```

### 1. مطاعم في جدة

```overpassql
[out:json][timeout:25];

nwr["amenity"="restaurant"](21.45,39.18,21.55,39.28);

out center 25;
```

### 2. كافيهات في جدة

```overpassql
[out:json][timeout:25];

nwr["amenity"="cafe"](21.45,39.18,21.55,39.28);

out center 25;
```

### 3. فنادق في وسط جدة

```overpassql
[out:json][timeout:25];

nwr["tourism"="hotel"](21.48,39.15,21.62,39.25);

out center 25;
```

### 4. محطات وقود في مكة

```overpassql
[out:json][timeout:25];

nwr["amenity"="fuel"](21.36,39.79,21.46,39.90);

out center 25;
```

### 5. صيدليات في شمال جدة

```overpassql
[out:json][timeout:25];

nwr["amenity"="pharmacy"](21.55,39.12,21.70,39.25);

out center 25;
```

## ملاحظات مهمة

- استخدم `/overpass/to-json` عندما يكون عندك استعلام Overpass QL كنص وتبغى تحوله إلى JSON.
- استخدم `/overpass/execute` عندما تبغى تنفذ الاستعلام وترجع نتائج من Overpass.
- لو الاستعلام بطيء أو رجع timeout، صغر الـ bounding box أو قلل عدد النتائج.
- لو ما رجعت نتائج، جرب وسم مختلف مثل `amenity`, `tourism`, أو `shop`.
- وجود `[out:json]` مهم لأن التطبيق يتوقع أن Overpass يرجع JSON.
