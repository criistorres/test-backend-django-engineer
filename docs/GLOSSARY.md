# Glossary

Dictionary of technical terms used in `README.md`, `DIAGRAM.md`, `DECISIONS.md` and `PRESENTATION.md`. Plain-language explanations, with examples when they help.

---

## A

### API (Application Programming Interface)
Interface that lets one program talk to another. In this project, "the API" is the HTTP endpoint that accepts `start` and `finish` and returns the route.

### External API / Free routing API
Service from another company/project that receives an internet request and replies. "Free" means it does not charge to use (up to certain limits). In our case it is the public OSRM.

### Greedy algorithm
Algorithm strategy that, at each step, picks what looks best at that moment, without backtracking. Fast and simple. Not always mathematically optimal, but usually very close.

> In the optimizer: "at each stop, pick the cheapest station within the range I still have" — without reconsidering earlier stops.

---

## B

### Backend
The part of the system running on the server (not in the user's browser). Handles business logic, database, integrations. Django is a backend framework.

### Batch
Processing many items at once, instead of one at a time. E.g., `bulk_create` inserts 1,000 rows with one command, instead of 1,000 commands.

### Bounding box
Geographic rectangle defined by 4 coordinates (min latitude, max latitude, min longitude, max longitude). Used to filter stations quickly before more expensive calculations: "first pick all stations inside the route's rectangle; then do the fine math only on those."

### Buffer / Perpendicular buffer
Side strip around the route. A 5-mile buffer = a station within 5 perpendicular miles of the route line is considered "on the route". Helps capture truckstops at highway exits without including stations from distant cities.

### `bulk_create`
Django ORM method that inserts many rows with a single SQL query. Much faster than saving them one by one.

---

## C

### Cache
Temporary memory storing recent results so they don't need to be recomputed. E.g., if someone asked "Houston -> Boston" a minute ago, we can return the stored answer instead of calling OSRM again.

### CSV (Comma-Separated Values)
Text file where each line is a table row and fields are separated by commas. The `fuel-prices-for-be-assessment.csv` file is in this format.

---

## D

### Dataset
Structured collection of data. E.g., the "US cities dataset" is a table with `city, state, lat, lng` covering ~30k US cities.

### Django
Python web framework. Handles URL routing, ORM (database), templates, authentication etc. We use version 6.0.5.

### Django REST Framework (DRF)
Library on top of Django focused on building JSON APIs. Provides ready tools to validate input, serialize output, paginate etc.

### DRF (Django REST Framework)
Acronym, see above.

---

## E

### Endpoint
Specific API URL that does one specific thing. E.g., `GET /api/route/` is the endpoint that returns the route.

### End-to-end
Test that exercises the entire system, from HTTP request through to response, going through all real components (or with targeted mocks).

---

## F

### Free tier
Free quota of a paid API. E.g., OpenRouteService gives 2,000 free requests per day; beyond that, it charges.

---

## G

### Geocoding
Turning an address/text into coordinates (latitude, longitude). E.g., "Houston, TX" -> `(29.76, -95.36)`.

> **Approximate geocoding by city+state:** instead of geocoding each truckstop's full address, we use the coordinates of the city center where the truckstop is. Faster and free, with a typical 5-15 mile error.

### Greedy
See "Greedy algorithm".

---

## H

### Haversine
Mathematical formula to compute the straight-line distance between two points on Earth's surface (which is curved). Much simpler than the full spherical formula and accurate enough for our use.

### Heuristic
Practical rule for making a decision when the optimal problem would be too expensive to solve. Does not guarantee the best result, but usually gets close.

> "H1 baseline heuristic" means: "the basic rule I'll use first". H1 = cheapest in the whole remaining range. Alternative H2 = cheapest only in the 60-100% window. We start with H1 for simplicity; if time allows, we benchmark against H2.

### HTTP / HTTPS
Web protocol. All client-API communication goes over HTTP. Codes like 200 (ok), 400 (invalid input), 422 (business rule violated), 502 (external service failed), 504 (timeout).

---

## I

### Index (database)
Structure the database keeps to find rows quickly by a column. Without an index, the database reads every row; with an index, it goes straight to the right one. We create indexes on `lat`, `lng` and `state` of the `FuelStation` table.

---

## J

### JSON (JavaScript Object Notation)
Text format for exchanging structured data. Readable by humans and programs. Our API response is a JSON with `route_polyline`, `fuel_stops`, etc.

### Join
Operation that combines two datasets by a common key. E.g., join the truckstop CSV with the cities dataset by `(city, state)` to get lat/lng.

---

## L

### Latitude / Longitude (lat, lng)
Geographic coordinates. Latitude ranges from -90 (south) to +90 (north). Longitude from -180 (west) to +180 (east). Houston ~ (29.76, -95.36).

### Latest stable
The newest version of a piece of software marked as "stable" (not alpha/beta/rc). For Django as of May/2026: **6.0.5**.

### LTS (Long-Term Support)
Version with extended support. Receives only security/bug fixes, no new features. Recommended for systems that don't want frequent upgrades. Django 5.2 LTS = supported through Apr/2028.

---

## M

### Management command
Django CLI script, executed via `python manage.py <command>`. We use `python manage.py import_fuel_prices` to load the CSV.

### Migration
Versioned Django ORM script that alters the database schema (creates table, adds column, etc.). Generated by `makemigrations` and applied with `migrate`.

### Mock
Fake object used in tests to simulate a real service. E.g., in tests we "mock" OSRM so we don't hit the internet — we pass a previously recorded response.

### MPG (Miles Per Gallon)
Vehicle efficiency. Constant = 10 in the challenge (10 miles per gallon consumed).

---

## N

### NumPy
Python library for fast numeric computation with arrays. We use it to compute distances in bulk (haversine over thousands of stations) much faster than a plain Python loop.

### Nominatim
Free geocoding service based on OpenStreetMap. Limited to 1 request per second on the public server, which makes geocoding 8,000+ addresses in reasonable time impossible.

---

## P (extra)

### Photon
Free geocoding service maintained by komoot, built on OpenStreetMap + Elasticsearch. Unlike public Nominatim, **it has no publicized hard rate limit**. We use it as a fallback when the offline dataset doesn't resolve the input (full addresses, POIs, small towns). We restrict results to `countrycode == "US"`.

---

## O

### ORM (Object-Relational Mapping)
Layer that maps database tables to Python classes. In Django, `FuelStation.objects.filter(...)` generates SQL automatically.

### OSRM (Open Source Routing Machine)
Free, open-source routing engine, written in C++, that computes the shortest path between two points using OpenStreetMap data. Free public servers exist (no install needed) and you can self-host it as well.

### Public OSRM
Public OSRM server available at `router.project-osrm.org`. Free, no API key, with a **1 request per second** limit and no uptime guarantee. We use this in the project to avoid signup/credentials.

### OpenRouteService (ORS)
Alternative to OSRM, also free up to certain limits, but requires signup and an API key. Free tier of 2,000 requests/day.

### OpenStreetMap (OSM)
Collaborative project (like Wikipedia) that maps the entire world. Data is free and used by OSRM, Nominatim, ORS etc.

---

## P

### P95 / 95th percentile
Performance metric. "P95 < 800ms" means 95% of requests finish in less than 800ms (only 5% are slower). More useful than the average because it captures the experience in bad cases.

### Pipeline
Sequence of steps that process data. E.g., load pipeline = read CSV -> join with cities -> bulk_create into the database.

### Polyline (Google Polyline)
Compact way to encode a sequence of lat/lng points into a string. Instead of sending 5,000 `[lat, lng]` pairs, we send a string like `"u{~vFvyys@fS]b@..."`. Most map libraries (Leaflet, Mapbox) know how to decode it.

### Encoded polyline
The encoded string. "Encoded" because it went through the Google Polyline Algorithm Format which compresses the numbers.

### Postman
Graphical tool for testing APIs. You build the request, fire it, see the response. We create a "Postman collection" with ready-to-run requests for the reviewer to test.

### Postman collection
JSON file with multiple pre-configured requests to import into Postman.

### Postgres / PostgreSQL
Robust open-source relational database. Alternative to SQLite for production. Not used in the challenge for simplicity.

### Python
Programming language used by Django. Version 3.12+ for Django 6.0.

---

## R

### Rate limit
Limit on how many requests you can make per unit of time. Public OSRM = 1 req/s. Exceeding it returns HTTP 429.

### REST
API style that uses HTTP methods (GET, POST, PUT, DELETE) and URLs to represent resources. Our API is RESTful.

### Routing
Computing the shortest (or fastest) path between two points on a road map. The "routing engine" (e.g., OSRM) does this.

---

## S

### Self-hosted
When you install and run the service on your own server, instead of using someone else's public service. More control, more work.

### Serializer (DRF)
Django REST Framework class that defines how to transform Python objects into JSON (and vice versa). Ensures stable response format.

### SLA (Service Level Agreement)
Formal commitment to service quality (uptime, latency). Public OSRM has no SLA — it can go down at any time without notice.

### SQLite
File-based database (a single `.db` file). Zero setup, ideal for small projects. Bundled with Python; nothing to install.

### Snap-to-route / Snap-to-segment
Technique to project a point (station) onto the closest point of the route line. More accurate than just perpendicular distance, but also more expensive. Listed as a future refinement.

### Stack
Set of technologies in the project. "Stack: Django + DRF + SQLite + OSRM".

### Stable (version)
Final software version, recommended for production. Not alpha (initial tests), beta (final tests) or rc (release candidate).

---

## T

### Timeout
Maximum time we wait for an operation to finish. E.g., "5s timeout on OSRM" = if it does not respond in 5s, we abort and return 504.

### Truckstop
Highway gas station, focused on trucks (but serves any vehicle). The challenge CSV lists ~8k truckstops in the US.

### TTL (Time To Live)
Lifetime of an item in cache. E.g., "cache with 1-minute TTL" = after 1 minute, the item is discarded and the next request recomputes.

---

## U

### URL
Web address. E.g., `http://localhost:8000/api/route/?start=Houston,TX&finish=Boston,MA`.

---

## V

### Venv (virtual environment)
Isolated folder where you install Python packages for a single project without affecting the rest of the system. Command: `python -m venv .venv` creates it; `source .venv/bin/activate` activates it.

---

## W

### Warm cache
Cache that has already been populated with frequent data. Follow-up requests are faster. Opposite: "cold cache" (empty cache, first request).

---

## Terms That Surfaced During Implementation

### Vectorization / NumPy vectorized
Numeric-computing technique where you operate on whole arrays at once (in C under the hood) instead of looping item-by-item in Python. Result: 50 to 200x faster. This is what brought the optimizer from 86s down to 0.8s.

### overview=simplified / overview=full (OSRM)
Parameters controlling how many points the returned polyline contains.
- `full` = every point, faithful geometry (but more segments = more compute).
- `simplified` = polyline simplified by Douglas-Peucker, sufficient for our 5-mi buffer.

### Bulk create (Django ORM)
`Model.objects.bulk_create([...])` inserts many objects in a single SQL query. Used in `import_fuel_prices` to load ~7,500 stations in ~0.5s.

### `@dataclass(frozen=True)` decorator
Immutable Python class with typed fields, no need to write `__init__`. Used for `Route`, `Stop`, `OptimizationResult` in the project.

### `lru_cache`
Python decorator that memoizes the result of a function. Used in `geocoder.py` to load `us_cities.csv` only on the first call and reuse it on every other.

### `searchsorted` (NumPy)
Binary search in a sorted array. Used in the optimizer to find the range of stations within range in O(log n) instead of O(n).

### `bulk_create`
See "Bulk create".

### Greedy H1 (heuristic 1)
Baseline heuristic: at each stop, pick the **cheapest** station within the remaining range (from `position` to `position + 500 mi`). Simple and fast, but tends to stop too early.

### Greedy H2 (heuristic 2 — in use)
Active heuristic: only considers stations in the **60-100% window** of the range (from `position + 300 mi` to `position + 500 mi`). Stretches the tank, reduces the number of stops, improves cost. Falls back to H1 when the preferred window is empty. Decision recorded in `DECISIONS.md` D11.

### view_url
JSON-response field with a Google Maps Directions URL (`google.com/maps/dir/`) using lat/lng of origin, destination and every stop as a waypoint. Shows **miles** by default in the US locale. Decision recorded in D12.

### view_url_osrm
Alternative URL for `map.project-osrm.org` with origin, destination and stops as `&loc=` points. Useful for visually validating that the route used by the backend (OSRM) matches what the user sees. Shows distances in km by default (toggle via the gear icon in the bottom-left).

### Bounding box query
SQL query that filters stations with `lat BETWEEN min AND max AND lng BETWEEN min AND max`. Reduces thousands of rows to a few hundred before the more expensive geometric computation.

### `transaction.atomic()`
Django block that guarantees "all or nothing" in the database: either every row inserted, or none. Used in `import_fuel_prices` to avoid a partial load on error.
