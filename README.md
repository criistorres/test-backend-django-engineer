# Fuel Route Optimizer API

A Django REST API that, given two US locations, returns the driving route, the cost-optimal fuel stops along the way, and the total fuel cost — assuming a vehicle with a 500-mile range at 10 MPG.

Built for the **Remote Backend Django Engineer — AI & Algorithmic Systems** assessment.

---

## Highlights

- **Single endpoint.** `GET /api/route/?start=&finish=`
- **One external call per request.** OSRM public for routing; the rest is local.
- **Hybrid geocoding.** Local US-cities dataset first; Photon (OSM) only as fallback for full addresses or small towns.
- **Vectorized math.** NumPy-vectorized haversine + projection finds candidate stations across thousands of records in tens of milliseconds.
- **Two map URLs in the response.** Google Maps Directions (with each fuel stop as a waypoint, miles by default) and the OSRM public viewer.
- **Greedy H2 optimizer.** Prefers stations in the 60–100% tank window; falls back to the full range if needed.
- **Tested.** 21 tests across geometry, geocoding, optimization, and the view.

Typical end-to-end latency: **~0.8 s** for a 1,850-mile coast-to-coast route with 4–5 stops, dominated by the OSRM network call.

---

## Quick Start

```bash
# 1. Clone & enter the project
git clone <repo-url>
cd "Test Backend Django Engineer"

# 2. Create the virtualenv and install deps
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Initialize the database and load fuel-price data
python manage.py migrate
python manage.py import_fuel_prices

# 4. Run the dev server
python manage.py runserver

# 5. Try it
curl "http://localhost:8000/api/route/?start=Houston,%20TX&finish=Boston,%20MA"
```

Tested with **Python 3.13** and **Django 6.0.5**.

---

## API

### Endpoint

```
GET /api/route/?start=<origin>&finish=<destination>
```

`start` and `finish` accept any of:

| Format | Example |
|---|---|
| `City, ST` | `Houston, TX` |
| `lat,lng` | `29.76,-95.36` |
| Full US address / POI | `1600 Pennsylvania Ave NW, Washington, DC` |

### Success response (HTTP 200)

```json
{
  "start":  {"address": "Houston, TX", "lat": 29.76, "lng": -95.36},
  "finish": {"address": "Boston, MA",  "lat": 42.36, "lng": -71.05},
  "total_distance_miles": 1845.3,
  "total_gallons": 184.53,
  "total_cost_usd": 587.42,
  "route_polyline": "<encoded polyline>",
  "view_url": "https://www.google.com/maps/dir/?api=1&origin=...&destination=...&waypoints=...&travelmode=driving",
  "view_url_osrm": "https://map.project-osrm.org/?z=4&center=...&loc=...&loc=...&srv=0",
  "fuel_stops": [
    {
      "name": "PILOT TRAVEL CENTER #1243",
      "address": "I-8, EXIT 119 & SR-85",
      "city": "Gila Bend",
      "state": "AZ",
      "lat": 32.95,
      "lng": -112.72,
      "price_per_gallon": 3.899,
      "gallons": 48.5,
      "cost": 189.10,
      "miles_from_start": 485.0
    }
  ]
}
```

### Error responses

| HTTP | Internal code | When |
|---|---|---|
| 400 | `invalid_input` | `start`/`finish` missing or impossible to geocode |
| 422 | `route_infeasible_with_range` | Some leg has no station within the 500-mile range |
| 502 | `routing_provider_error` | OSRM unavailable or returned an error |
| 504 | `routing_provider_timeout` | OSRM did not respond within 5 s |

---

## How it works

```
GET /api/route/?start=...&finish=...
 -> Geocode start & finish (local dataset -> Photon as fallback)
 -> OSRM public: one call returns polyline + distance
 -> Query candidate stations within the route bounding box (+ 5-mi padding)
 -> Filter stations to a 5-mi perpendicular buffer around the polyline
 -> Greedy H2 optimizer: pick the cheapest station in the 60–100% tank window
 -> Final leg priced at the last stop's rate
 -> Return JSON with polyline, both map URLs, and the fuel stops
```

### Greedy algorithm (H2 + H1 fallback)

```text
tank        = 500 mi
mpg         = 10
buffer      = 5 mi (perpendicular distance to the polyline)
position    = 0
stops       = []

while position + tank < total_distance:
    # H2: prefer stations in the 60–100% tank window (avoids stopping too early)
    window = stations where position + 0.6*tank <= pos_cum <= position + tank
    if window is empty:
        # H1 fallback: any station within the remaining range
        window = stations where position < pos_cum <= position + tank
        if window is empty:
            raise 422 route_infeasible_with_range
    pick the cheapest station in window
    add (gallons=(pos-position)/mpg, cost=gallons*price)
    position = chosen station position

final_gallons = (total_distance - position) / mpg
total_cost    = sum(stop.cost) + final_gallons * last_stop_price
```

Why H2: a pure "cheapest in remaining range" heuristic stops too early — refueling at mile 100 when you could comfortably reach mile 480 wastes potentially cheaper opportunities downstream. See `docs/DECISIONS.md` D11.

---

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.13 | Required by Django 6.0.5 |
| Framework | **Django 6.0.5** | Latest stable on djangoproject.com/download |
| API | Django REST Framework | Serializers, browsable API, easy error responses |
| Database | SQLite | Zero setup; ~8k rows + bounding-box filter is well within its comfort zone |
| Routing | **OSRM public** (`router.project-osrm.org`) | Free, no API key, one call returns polyline + distance |
| Geocoder | Local US-cities CSV + Photon (OSM) fallback | Offline-first; Photon has no hard rate limit |
| Geometry | NumPy (vectorized haversine + projection) | ~100× faster than a pure-Python loop |

---

## Project layout

```text
.
├── manage.py
├── requirements.txt
├── pytest.ini
├── README.md
├── config/                     # Django project (settings, urls, wsgi)
├── routing/                    # The app
│   ├── models.py               # FuelStation
│   ├── views.py                # RouteView
│   ├── serializers.py
│   ├── urls.py
│   ├── services/
│   │   ├── geocoder.py         # 'lat,lng' / 'City, ST' -> Photon fallback
│   │   ├── osrm_client.py      # Single OSRM call, polyline + distance
│   │   ├── geometry.py         # Haversine, projection, bounding box
│   │   └── optimizer.py        # Greedy H2 (60–100% window) + H1 fallback
│   ├── management/commands/
│   │   └── import_fuel_prices.py
│   └── tests/                  # pytest + pytest-django
├── data/
│   ├── fuel-prices-for-be-assessment.csv
│   └── us_cities.csv           # kelvins/US-Cities-Database (MIT)
├── postman/
│   └── fuel-route-optimizer.postman_collection.json
└── docs/
    ├── INSTRUCTIONS.md         # Original assessment brief
    ├── DIAGRAM.md              # Executive diagrams (sequence + flowchart)
    ├── DECISIONS.md            # Decision log (Dxx entries)
    ├── GLOSSARY.md             # Glossary of technical terms
    └── PRESENTATION.md         # 5-min Loom script
```

---

## Running the tests

```bash
.venv/bin/python -m pytest routing/tests/ -v
```

| Suite | What it covers |
|---|---|
| `test_geometry.py` | haversine, cumulative distance, bounding box, station projection |
| `test_geocoder.py` | input parsing, Photon fallback (mocked), error cases |
| `test_optimizer.py` | short-route no-stop, single stop, cheapest selection, infeasible route |
| `test_view.py` | end-to-end with mocked OSRM: 400 / 200 / 422 paths, `view_url` shape |

21 tests total, all green.

---

## Testing with Insomnia / Postman / Bruno

Import `postman/fuel-route-optimizer.postman_collection.json` (Postman v2.1 format — Insomnia and Bruno import it natively). The collection includes 8 ready-to-run requests:

| Request | What it exercises |
|---|---|
| Short route — Houston → Austin | Happy path, zero fuel stops |
| Long route — Houston → Boston | Multiple stops, full payload |
| Coast-to-coast — LA → New York | Stress-test the optimizer over ~2,800 mi |
| Direct coordinates `(lat,lng)` | Bypasses geocoding |
| Full address (Photon fallback) | Forces the Photon path |
| 400 — missing parameters | Input validation |
| 400 — unknown city | Geocoder negative path |
| 502 — infeasible route (Honolulu → Boston) | Routing provider error |

---

## Performance budget

| Step | Typical |
|---|---|
| Geocoding (in-memory dict lookup) | < 1 ms |
| OSRM call (network, `overview=simplified`) | 200–600 ms |
| Polyline decode + bounding box | < 5 ms |
| SQLite bounding-box query | < 20 ms |
| NumPy projection + filter | < 30 ms |
| Greedy loop | < 5 ms |
| Serialization | < 5 ms |
| **End-to-end P95** | **~800 ms** |

---

## Documentation index

| File | Purpose |
|---|---|
| [`docs/INSTRUCTIONS.md`](docs/INSTRUCTIONS.md) | Original assignment brief |
| [`docs/DIAGRAM.md`](docs/DIAGRAM.md) | Executive diagrams: sequence + flowchart + data pipeline |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | Decision log (D01–D13) with context, options, trade-offs |
| [`docs/GLOSSARY.md`](docs/GLOSSARY.md) | Glossary of technical terms used in the project |
| [`docs/PRESENTATION.md`](docs/PRESENTATION.md) | 5-minute Loom walkthrough script |

---

## Deliverables checklist

- [x] Django 6.0.5 (latest stable, validated on djangoproject.com)
- [x] Single endpoint accepting US start/finish
- [x] Returns a map of the route (`route_polyline` + two `view_url`s)
- [x] Returns the optimal fuel stops along the route
- [x] Total fuel cost at 10 MPG
- [x] Uses the provided fuel-prices CSV
- [x] One external call per request (OSRM)
- [x] Postman / Insomnia / Bruno collection
- [x] 5-minute Loom demonstrating the API and giving a code overview
