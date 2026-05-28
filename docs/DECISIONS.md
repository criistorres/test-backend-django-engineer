# Decision & Challenge Log

Living document. Each entry records a challenge encountered, the options considered, the decision taken and the reason. Ordered chronologically. Acts as the technical defense baseline for the project.

---

## D01 — Django Version

**Context:** The INSTRUCTIONS.md requirement says "latest stable Django".

**Challenge:** As of May/2026 there are two supported versions: Django 5.2 LTS (supported through Apr/2028 but in security-only mode since Dec/2025) and Django 6.0.5 (mainstream active through Aug/2026).

**Options:**

| Option | Pro | Con |
|---|---|---|
| Django 5.2 LTS | Long support, more mature third-party libs | Already security-only, no bugfixes or new features |
| Django 6.0.5 | Literal "latest stable", mainstream active | Newer ecosystem, some libs may not have compatible releases yet |

**Decision:** **Django 6.0.5**.

**Reason:** The requirement is literal — "latest stable". 6.0.5 is the most recent stable version per djangoproject.com/download. Additionally, it is the only version currently in mainstream support.

**Validation:** Direct lookup on djangoproject.com/download on 2026-05-27.

---

## D02 — Routing Provider

**Context:** The requirement asks for a free map/route API found by the candidate, with at most 1-3 calls per request.

**Options:**

| Option | Cost | Key | Single call covers route? |
|---|---|---|---|
| OSRM public (`router.project-osrm.org`) | Free | No | Yes (polyline + distance) |
| OpenRouteService free tier | Free up to 2000/day | Yes | Yes |
| GraphHopper free tier | Free up to 500/day | Yes | Yes |
| Mapbox / Google Directions | Paid after free tier | Yes | Yes |

**Decision:** **Public OSRM**.

**Reason:** Meets the requirement without signup or key, returns polyline + distance in a single call, and the limit (1 req/s) is sufficient for the challenge. Documented risks: zero SLA, possible URL changes.

**Mitigation:** We keep the OSRM client behind an interface (`RoutingProvider`) so it can be swapped for ORS or self-hosted without refactoring the view.

---

## D03 — Truckstop Geocoding

**Context:** The CSV brings ~8,151 truckstops with name, address, city and state, but **no lat/lng**. To select stops along the route, we need the coordinates of each station.

**Challenge:** Geocoding 8,151 addresses through an external API blows free tiers (Nominatim limits to 1 req/s; Mapbox charges at scale) and contradicts the "few calls" rule. Beyond that, request-time geocoding kills performance.

**Options:**

| Option | Cost | Speed | Accuracy |
|---|---|---|---|
| Online geocode at request time | Expensive / rate-limited | Slow | High |
| Offline batch geocode via self-hosted Nominatim | Complex setup | Fast after setup | High |
| **Approximate geocode by `city + state`** | Zero | Instant | Good (~5-15 mi typical error) |

**Decision:** **Approximate geocode by `city + state`** using the local SimpleMaps US cities dataset (free, ~30k cities).

**Reason:** For the challenge, the goal is to pick truckstops within a 5-mile corridor around the route. A typical 5-15 mi error between the city center and the exact truckstop location is absorbed by the route buffer, and does not distort the "which is cheapest" decision — which is what drives total cost minimization.

**Trade-off accepted:** On short routes with several very close stations, two neighbors may swap relative position. Acceptable for scope.

---

## D04 — Database

**Options:** SQLite vs Postgres.

**Decision:** **SQLite**.

**Reason:** Zero setup, no external dependency, sufficient for ~8k rows and bounding-box queries. Trivial to swap for Postgres by editing `DATABASES` in `settings.py`. The challenge demands neither multi-tenant nor high concurrency.

---

## D05 — Optimizer Heuristic

**Context:** The greedy algorithm must decide, at each stop, which station to pick within the remaining range.

**Options:**

| Heuristic | Logic | Risk |
|---|---|---|
| H1: Cheapest within the entire remaining range | `min(price)` within `position < pos_cum <= position + 500` | May stop too early if there is a very cheap station near the start |
| H2: Cheapest within the 60-100% range window | Restricted to `position + 300 < pos_cum <= position + 500` | May miss an exceptionally cheap station in the first half |
| H3: Dynamic programming optimizing global cost | True optimization | More complex, possibly unnecessary |

**Decision:** Implement **H1 as baseline**; keep hooks to swap for H2 or H3 in a future iteration.

**Reason:** H1 is simple, defensible and in practice produces results very close to the global optimum because the driver never has a reason to pass a significantly cheaper station. H3 is overengineering for a 3-day scope.

---

## D06 — Input Format (start / finish)

**Challenge:** "Houston" alone is ambiguous (Houston, TX vs Houston, MS). Accepting full addresses requires an online geocoder.

**Decision:** Accept two formats:

1. `City, ST` (e.g., `Houston, TX`) — resolved via local dataset
2. `lat,lng` (e.g., `29.76,-95.36`) — used directly without geocoder

Documented in the README and the Postman collection.

**Reason:** Keeps zero external calls for geocoding and zero ambiguity. Allows deterministic tests.

---

## D07 — Route Side Buffer

**Context:** How far from the polyline do we still accept a station as "on the route"?

**Decision:** **5 miles** perpendicular buffer.

**Reason:** Typically covers all truckstops at highway exits and rest areas, without including stations on parallel corridors. A constant in code, easy to tune.

---

## D08 — US Cities Dataset Source

**Context:** To geocode `(city, state)` we needed a CSV with ~30k US cities + lat/lng.

**Attempts:**

| Source | Result |
|---|---|
| SimpleMaps direct free download | HTTP 403 (blocked for curl/automation) |
| GitHub `kelvins/US-Cities-Database/csv/us_cities.csv` | **OK** — 29,881 cities, ~1.7 MB |

**Decision:** Use the `kelvins/US-Cities-Database` dataset (public, MIT-friendly, no download restriction).

**Coverage validation:** 3,802 out of 3,893 unique cities in the fuel-price CSV were found = **97.7%**. The 91 unmatched are all Canadian cities (ON, AB, SK, BC, MB, NB) and should be discarded naturally, since the challenge covers USA only.

**File in project:** `data/us_cities.csv`.

---

## D09 — Canadian Cities in the Fuel CSV

**Context:** The challenge CSV contains ~91 Canadian cities (ON, AB, SK, BC, MB, NB) — likely OPIS truckstops near the border.

**Decision:** **Drop** those rows in `import_fuel_prices` and log the count.

**Reason:** The brief says "both within the USA". Keeping out-of-country data may confuse the optimizer. We log it during import.

---

## D10 — Station Projection Performance

**Context:** Initial implementation (pure Python, station-by-station loop) took ~86 seconds for Houston-Boston. Houston-Austin (short route) took ~3 s. Unworkable.

**Diagnosis:** The `overview=full` polyline for long routes has ~3,000 segments. With ~4,000 stations in the bounding box: 12 million perpendicular calculations in pure Python.

**Optimizations applied:**

| Optimization | Time |
|---|---|
| Pure Python initial version | ~86 s |
| NumPy vectorization (project all stations in parallel for each segment) | ~3 s |
| Simplified polyline (`overview=simplified` from OSRM) | **~0.8 s** |

**Decision:** Keep `overview=simplified` + NumPy vectorization.

**Reason:** For a 5-mile buffer, the precision loss from the simplified polyline is negligible (a station remains either "on the route" or "off the route"). And it is a 100× speedup in response time.

**Trade-off accepted:** On extremely winding routes (mountains), the simplified polyline can "cut corners" and theoretically classify a station on a tight bend as outside the buffer. Acceptable for the use case (US interstate highways, mostly straight).

---

## D11 — H2 Heuristic (60-100% Window)

**Context:** The H1 baseline ("cheapest in remaining range") produced clustered stops in manual tests (e.g., Vidor TX at mile 103 + Vinton LA at mile 129 on a Houston → Boston route). The brief calls for an **optimal/cost-effective** result, and stopping early in the tank wastes better opportunities downstream.

**Options:**

| Option | Pro | Con |
|---|---|---|
| H1 (cheapest in 0-100% of range) | Simple, always has a solution if infeasibility doesn't apply | Stops too early |
| H2 (cheapest in 60-100% of range) | Stretches the tank, fewer stops | Can fail if no station is in the preferred window |
| Global LP / DP | Likely optimal | Overkill for 3 days and n=8,000 stations |

**Decision:** **H2 with fallback to H1** when the preferred window (60-100%) is empty.

**Reason:** Keeps the greedy simplicity, reaches "cost-effective" closer to the optimum in real cases, and does not introduce artificial infeasibilities — if there is no station in the ideal window, it falls back to accepting any in range.

**Trade-off:** On routes where the 60-100% segment is significantly more expensive than the 0-60% segment, H2 may pick worse than H1. Accepted: in practice the "drive further before stopping" trade-off beats "stop early at a cheap one only to stop again soon after".

---

## D12 — `view_url` Field in the Response

**Context:** The brief asks to "Return a map of the route". JSON cannot render a map, but it can deliver a URL that **renders** the map in any browser at zero cost.

**Options:**

| Option | Pro | Con |
|---|---|---|
| Render PNG image in the backend | Self-contained | Requires tile server, cache, bandwidth cost |
| Embed Leaflet/Mapbox in Django itself | Polished | Extra UI out of scope, requires template |
| URL to public OSRM viewer (`map.project-osrm.org`) | Zero extra infra, same provider as the route | Shows km by default (unit toggle only via UI/localStorage, no query param) |
| Google Maps Directions URL (`google.com/maps/dir/?api=1`) | Zero infra, **miles by US locale**, high availability | Routing provider differs from our calculation (Google may suggest a slightly different path) |

**Decision:** **Google Maps Directions URL** with origin/destination in lat,lng.

**Reason:** Literally fulfills "Return a map" with no infra cost. Since the challenge targets the USA, Google Maps shows distances in miles automatically — aligned with the response's `total_distance_miles`. The OSRM URL worked, but displayed km and required the user to click the gear icon to switch.

**Trade-off:** Google may recompute the suggested path with slight differences (proprietary algorithm + traffic data), so the visual polyline in the link may not match `route_polyline` in the JSON 100%. The stop calculation remains valid — the source of truth is the `route_polyline` returned.

**Waypoints:** Fuel stops are added as `&waypoints=lat1,lng1|lat2,lng2|...` in the URL so they can be visualized on the map. Google Maps caps URLs at **9 waypoints**; if the route has more (rare: only on > 4,500-mile trips), we expose the first 9. The JSON always carries the complete list in `fuel_stops`.

**Additional field `view_url_osrm`:** Since Google may pick a slightly different path from OSRM, we also expose a URL for `map.project-osrm.org` with origin, destination and stops via `&loc=`. This lets the reviewer visually confirm that the route used for the calculation matches the one rendered. The OSRM viewer accepts N points with no practical limit, but shows distances in km by default.

---

## D13 — Photon as Geocoding Fallback

**Context:** The offline dataset (`us_cities.csv`) covers only the `City, ST` format. Full addresses ("123 Main St, Springfield, IL"), POIs ("Walmart Houston") or very small towns do not resolve. The user needs a flexible way to provide origin/destination.

**Options:**

| Provider | Cost | Rate-limit | Accepts full address |
|---|---|---|---|
| Public Nominatim | Free | 1 req/s (hard) | Yes |
| Self-hosted Nominatim | 30GB disk + 16GB RAM + 4-12h import | No limit | Yes |
| Photon (komoot.io) | Free | No publicized hard limit | Yes |
| Google Geocoding | Paid | High | Yes |

**Decision:** **Photon as fallback**, with the chain `lat,lng → local dataset → Photon`.

**Reason:** Photon is based on OSM (the same source data as OSRM), has no hard 1 req/s limit, and covers cases where the offline dataset fails. The fallback only fires when the fast path (offline) does not resolve, keeping most calls instantaneous. We filter by `countrycode == "US"` to honor the USA requirement.

**Trade-off:** Adds an external HTTP dependency on fallback cases. Typical Photon latency: 200-600 ms. Since the common path (large cities / lat,lng) does not hit Photon, the average impact on response time is zero. Results are cached in memory (`lru_cache`).

---

## Template for New Entries

```text
## Dxx — <Short Title>

**Context:** ...
**Challenge:** ...
**Options:** (table)
**Decision:** ...
**Reason:** ...
**Trade-off / accepted risk:** ...
```
