# Presentation Script — 5-min Loom

Tight script targeting **~3 min 45 s** of speaking time, leaving room for transitions and to breathe. Cut anything that isn't on this page.

---

## Setup Before Recording

- Django server running: `python manage.py runserver`.
- Insomnia/Postman open with 2 requests ready: Houston → Austin and Houston → Boston.
- VS Code open with two files pinned: `routing/views.py` and `routing/services/optimizer.py`.
- A browser tab ready to paste the `view_url` from the long-route response.
- Close everything else. Mute notifications. Loom in "desktop + camera" mode.

---

## Block 1 — Context (0:00 - 0:20)

**Show:** README briefly.

**Say:**

> Hi, quick walkthrough of my Backend Django Engineer solution. Single endpoint: takes a start and finish in the US, returns the route, the optimal fuel stops for a 500-mile tank at 10 MPG, and the total cost. Let me show it working, then walk the code.

---

## Block 2 — Demo (0:20 - 1:30)

### Request 1 — short route (0:20 - 0:40)

```
GET /api/route/?start=Houston,TX&finish=Austin,TX
```

**Say:**

> Short route, fits in one tank: zero stops, just distance and the cost of that final leg.

### Request 2 — long route + map (0:40 - 1:30)

```
GET /api/route/?start=Houston,TX&finish=Boston,MA
```

**Say:**

> Now Houston to Boston, about 1850 miles. Response has the encoded polyline, the fuel stops with gallons and cost at each, the total cost, and a `view_url`. I'll paste that into the browser — Google Maps opens directly in miles with every fuel stop pinned as a waypoint.

**Show:** paste `view_url` in browser.

---

## Block 3 — Code (1:30 - 3:20)

### 3.1 Stack + flow — `views.py` (1:30 - 2:10)

**Say:**

> Stack is Django 6.0.5 — current latest stable — DRF, and SQLite. The view orchestrates four steps: geocode start and finish, one OSRM call to get polyline and distance, run the optimizer, serialize. Geocoding tries a local US-cities dataset first and falls back to Photon, an OSM geocoder with no hard rate limit, only when the dataset can't resolve the input. So the common path makes exactly one external call per request.

### 3.2 Optimizer — `optimizer.py` (2:10 - 3:20)

**Say:**

> The core is a greedy loop. For each station inside the route's bounding box, I compute the perpendicular distance to the polyline using haversine — vectorized in NumPy — and discard anything beyond five miles. Then I get each station's cumulative position along the route. Starting with a full tank at mile zero, I pick the cheapest station in the 60-to-100 percent window of the remaining range. That window matters: a naive "cheapest in the whole remaining range" stops too early and wastes cheaper stations downstream. If the preferred window is empty, it falls back to the full range. If nothing fits, 422 with `route_infeasible_with_range`. Total cost is the sum at each stop plus the final leg priced at the last stop.

---

## Block 4 — Closing (3:20 - 3:45)

**Say:**

> Key calls — all in DECISIONS.md: Django 6.0.5 because the spec says "latest stable", public OSRM for zero-key routing, offline-first geocoding with Photon as fallback, and the 60-to-100 percent window heuristic for cost. Twenty-one tests, end-to-end response around 800 milliseconds, dominated by the OSRM network call. Code is on GitHub. Thanks.

---

## What I Cut and Why

- **Third demo request (Hawaii error case)**: error handling is covered in the README and the Postman collection. Skipping it saves ~25 s.
- **Separate "model + pipeline" block**: the data load runs once offline; it's not part of the runtime story. The README covers it for anyone curious.
- **Separate "error handling + performance" block**: folded a one-liner into the closing.
- **Glossary and phrase backup**: removed from this file. If a term is unclear in the take, redo that sentence.

---

## Take Tips

- Read the script once before recording; then close it and speak.
- Target 145 words per minute. The blocks above are sized to that pace.
- If you trip on a sentence, pause and restart that sentence — Loom trims easily.
- One take. Don't perfect it; ship it.
