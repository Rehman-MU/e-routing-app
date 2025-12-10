# EV Routing Application - Complete Technical Documentation

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture & Technology Stack](#architecture--technology-stack)
3. [Database Schema & Models](#database-schema--models)
4. [Backend Architecture](#backend-architecture)
5. [Frontend Architecture](#frontend-architecture)
6. [Complete Workflow](#complete-workflow)
7. [Technical Concepts & Algorithms](#technical-concepts--algorithms)
8. [API Endpoints](#api-endpoints)
9. [External Service Integrations](#external-service-integrations)
10. [Deployment & Infrastructure](#deployment--infrastructure)

---

## System Overview

This is an **Electric Vehicle (EV) Routing System** that calculates optimal routes with charging stops based on:
- Vehicle battery specifications
- Current battery State of Charge (SOC)
- Desired arrival SOC
- Real-time charging station availability

The system provides two optimization strategies:
- **Fastest Route**: Minimizes total travel time (driving + charging)
- **Cheapest Route**: Prioritizes slower, cheaper charging options

---

## Architecture & Technology Stack

### High-Level Architecture

```
┌─────────────────┐
│   Frontend      │  Streamlit Web UI (Port 8501)
│   (Streamlit)   │
└────────┬────────┘
         │ HTTP REST API
         ▼
┌─────────────────┐
│   Backend       │  FastAPI Server (Port 8000)
│   (FastAPI)     │
└─────┬───────────┘
      │
      ├──► PostgreSQL Database (Port 5432)
      ├──► Redis Cache (Port 6379) [Configured but not actively used]
      │
      ├──► OSRM Routing Service (External)
      ├──► Photon Geocoding Service (External)
      └──► OpenChargeMap API (External)
```

### Technology Stack Details

#### Backend
- **FastAPI** (0.115.4): Modern, fast Python web framework for building APIs
- **SQLAlchemy** (2.0.36): ORM for database operations
- **PostgreSQL** (16): Relational database for persistent storage
- **Redis** (7): Caching layer (configured but not actively implemented)
- **Uvicorn**: ASGI server for running FastAPI
- **Pydantic**: Data validation and settings management
- **httpx**: Async HTTP client for external API calls
- **Shapely**: Geometric operations (point-in-polygon, distance calculations)
- **Polyline**: Encoding/decoding Google Maps polyline format
- **Geopy**: Geocoding utilities

#### Frontend
- **Streamlit** (1.39.0): Python-based web framework for rapid UI development
- **PyDeck** (0.9.1): WebGL-powered visualization library for maps
- **Requests**: HTTP client for backend communication

#### Infrastructure
- **Docker & Docker Compose**: Containerization and orchestration
- **PostgreSQL 16**: Database container
- **Redis 7**: Cache container

---

## Database Schema & Models

### Database Connection (`backend/db.py`)

```python
# Connection Pool Configuration
- Uses SQLAlchemy's create_engine with connection pooling
- SessionLocal: Factory for database sessions
- get_db(): Dependency injection function for FastAPI routes
- Base: Declarative base for ORM models
```

### Data Models (`backend/models.py`)

#### 1. **Vehicle Model**
Stores EV specifications:

```python
- id: Primary key (auto-increment)
- name: Vehicle identifier (e.g., "EV-1")
- battery_kwh: Total battery capacity in kilowatt-hours
- consumption_km_per_soc: Kilometers per 1% State of Charge
  (Example: 5.0 means 5 km per 1% SOC)
- charge_rate_soc_per_min: Percentage SOC gained per minute of charging
  (Example: 2.0 means 2% SOC per minute)
```

**Concept**: These parameters define the vehicle's energy efficiency and charging characteristics.

#### 2. **Query Model**
Stores user route planning requests:

```python
- id: Primary key
- created_at: Timestamp of query
- start_lon, start_lat: Starting coordinates
- end_lon, end_lat: Destination coordinates
- start_soc: Initial battery percentage
- arrival_soc: Desired battery percentage at destination
- vehicle_id: Foreign key to Vehicle
```

**Purpose**: Audit trail and potential analytics on route queries.

#### 3. **Plan Model**
Stores calculated route plans:

```python
- id: Primary key
- query_id: Foreign key to Query
- plan_type: "fastest" or "cheapest"
- total_time_min: Total travel time (driving + charging)
- total_cost_eur: Cost (currently NULL, placeholder for future)
- route_geojson: GeoJSON LineString of the route
- steps: Complete plan details (JSON)
```

**Purpose**: Persist route plans for historical analysis or caching.

#### 4. **StationCache Model**
Caches charging station data:

```python
- ocm_id: Primary key (OpenChargeMap station ID)
- name: Station name
- lon, lat: Coordinates
- power_kw: Charging power in kilowatts
- last_seen_at: Last update timestamp
- raw: Full JSON response from OCM API
```

**Purpose**: Reduce API calls to OpenChargeMap and improve response times.

---

## Backend Architecture

### Application Entry Point (`backend/app.py`)

```python
FastAPI Application Structure:
├── CORS Middleware: Allows cross-origin requests from frontend
├── Router: /api/v1/autocomplete (location search)
├── Router: /api/v1/route (basic routing)
├── Router: /api/v1/charging-stations (station lookup)
├── Router: /api/v1/ev-plan (main EV route planning)
└── Health Check: /health endpoint
```

### Configuration (`backend/core/config.py`)

Uses **Pydantic Settings** for environment-based configuration:

```python
Settings:
- DATABASE_URL: PostgreSQL connection string
- OSRM_BASE_URL: Routing service endpoint
- PHOTON_BASE_URL: Geocoding service endpoint
- OCM_BASE_URL: Charging station API endpoint
- OCM_API_KEY: Optional API key for OCM
- REDIS_URL: Redis connection (optional)
- APP_SECRET_KEY: Application secret
```

**Configuration Source**: `.env` file (loaded via `pydantic-settings`)

---

## Service Layer

### 1. Photon Service (`backend/services/photon.py`)

**Purpose**: Location autocomplete/search using Photon geocoding API.

**How It Works**:
1. Accepts a search query string (minimum 2 characters)
2. Queries Photon API: `https://photon.komoot.io/api?q={query}&limit={limit}`
3. Parses GeoJSON response
4. Extracts coordinates and formatted address labels
5. Returns list of `{label, coord: [lon, lat]}`

**Technical Details**:
- Uses `httpx.AsyncClient` for async HTTP requests
- 10-second timeout
- Handles missing fields gracefully (name, city, country)
- Returns coordinates in `[longitude, latitude]` format (GeoJSON standard)

**Concept**: Photon is an open-source geocoding service that provides fast, free location search without API keys.

---

### 2. OSRM Service (`backend/services/osrm.py`)

**Purpose**: Calculate driving routes between two points.

**How It Works**:
1. Accepts start/end coordinates and routing profile
2. Calls OSRM Route API: `{base}/route/v1/{profile}/{coords}?overview=full&geometries=polyline`
3. Decodes polyline-encoded geometry
4. Converts to GeoJSON LineString format
5. Returns distance (km), duration (minutes), and route geometry

**Technical Details**:
- **Polyline Encoding**: OSRM returns routes in Google's polyline format (compressed coordinate strings)
- **Decoding**: Uses `polyline.decode()` to convert to `(lat, lon)` tuples
- **Coordinate Conversion**: Converts to `[lon, lat]` for GeoJSON compatibility
- **Profile**: Default "driving" (can be "cycling", "walking", etc.)

**OSRM Concepts**:
- **Open Source Routing Machine**: Open-source routing engine
- **Profiles**: Different routing algorithms (driving considers roads, cycling considers bike paths)
- **Polyline**: Efficient encoding of coordinate sequences (reduces response size by ~90%)

**Example Request**:
```
GET /route/v1/driving/13.388860,52.517037;13.397634,52.529407
Response: {
  "distance": 1234.5,  // meters
  "duration": 180.2,   // seconds
  "geometry": "encoded_polyline_string"
}
```

---

### 3. OpenChargeMap Service (`backend/services/ocm.py`)

**Purpose**: Find charging stations near a route or within a bounding box.

#### Function: `stations_along_line()`

**Algorithm**:
1. **Sampling**: Selects ~12 evenly-spaced points along the route
2. **Parallel Queries**: For each sample point, queries OCM API with radius (default 7km)
3. **Deduplication**: Uses OCM station IDs to avoid duplicates
4. **Filtering**: Removes stations with invalid coordinates

**Technical Details**:
- **Sampling Strategy**: Uses `_sample_indices()` to evenly distribute query points
- **Radius**: 7km buffer around route (configurable)
- **Max Results**: 80 stations per query (OCM API limit)
- **Error Handling**: Gracefully degrades if API calls fail

**Concept**: Instead of querying the entire route polygon, samples points to reduce API calls while maintaining coverage.

#### Function: `stations_in_bbox()`

**Purpose**: Query stations within a geographic bounding box.

**Parameters**:
- `min_lon, min_lat, max_lon, max_lat`: Bounding box coordinates
- `maxresults`: Maximum stations to return

**OCM API Format**:
```
GET /v3/poi?boundingbox={min_lat},{min_lon},{max_lat},{max_lon}&maxresults=80
```

**Response Processing**:
- Extracts: `ID`, `AddressInfo` (name, coordinates), `Connections` (power rating)
- Returns "slim" format: `{ocm_id, name, lon, lat, power_kw}`

**OpenChargeMap Concepts**:
- **POI (Point of Interest)**: Charging station location
- **Connections**: Charging connectors at a station (CCS, CHAdeMO, Type 2, etc.)
- **PowerKW**: Maximum charging power in kilowatts
- **Country Code**: Currently hardcoded to "DE" (Germany)

---

## Router Layer (API Endpoints)

### 1. Autocomplete Router (`backend/routers/autocomplete.py`)

**Endpoint**: `GET /api/v1/autocomplete`

**Parameters**:
- `q`: Search query (minimum 2 characters)
- `limit`: Maximum results (default: 5)

**Flow**:
```
User types "Berlin" 
  → Frontend calls /api/v1/autocomplete?q=Berlin&limit=5
  → Router calls Photon service
  → Returns: [
      {label: "Berlin, Germany", coord: [13.4050, 52.5200]},
      {label: "Berlin, USA", coord: [-88.9444, 42.0006]},
      ...
    ]
```

---

### 2. Route Router (`backend/routers/route.py`)

**Endpoint**: `POST /api/v1/route`

**Request Body**:
```json
{
  "start": [13.388860, 52.517037],  // [lon, lat]
  "end": [13.397634, 52.529407],
  "profile": "driving"  // optional
}
```

**Response**:
```json
{
  "distance_km": 1.23,
  "duration_min": 3.0,
  "line": {
    "type": "LineString",
    "coordinates": [[lon1, lat1], [lon2, lat2], ...]
  }
}
```

**Error Handling**: Returns `{"error": "NoRoute"}` if no route found.

---

### 3. Stations Router (`backend/routers/stations.py`)

**Endpoint**: `GET /api/v1/charging-stations`

**Parameters**:
- `bbox`: Comma-separated `minLon,minLat,maxLon,maxLat`
- `maxresults`: Maximum stations (default: 80)

**Response**:
```json
{
  "count": 15,
  "items": [
    {
      "ocm_id": 12345,
      "name": "Tesla Supercharger",
      "lon": 13.4050,
      "lat": 52.5200,
      "power_kw": 150.0
    },
    ...
  ]
}
```

---

### 4. Plan Router (`backend/routers/plan.py`) - **CORE LOGIC**

**Endpoint**: `POST /api/v1/ev-plan`

**Request Body**:
```json
{
  "start": [13.388860, 52.517037],
  "end": [13.397634, 52.529407],
  "start_soc": 80.0,      // Initial battery %
  "arrival_soc": 20.0,    // Desired battery % at destination
  "vehicle_id": 1
}
```

**Response**:
```json
{
  "fastest": {
    "summary": {
      "drive_min": 180.5,
      "charge_min": 15.0,
      "total_time_min": 195.5
    },
    "route": {GeoJSON LineString},
    "stops": [charging station objects]
  },
  "cheapest": {same structure},
  "chargers": [all candidate stations]
}
```

#### Plan Algorithm (`plan_one_stop()`)

**Step-by-Step Logic**:

1. **Calculate Required SOC**:
   ```python
   need_total = route_km / vehicle.consumption_km_per_soc
   # Example: 200 km route, 5 km per 1% SOC = 40% SOC needed
   ```

2. **Check if Charging is Needed**:
   ```python
   if start_soc - need_total >= arrival_soc:
       return {"stops": [], "charge_min": 0.0}  # No charging needed
   ```

3. **Calculate SOC Deficit**:
   ```python
   delta_needed = arrival_soc + need_total - start_soc
   # Example: 20% arrival + 40% needed - 80% start = -20% (no deficit)
   # Example: 20% arrival + 60% needed - 50% start = 30% deficit
   ```

4. **One-Stop Strategy** (if `delta_needed <= 100%`):
   - Selects highest-power charger from candidates
   - Calculates charge time: `delta_needed / charge_rate_soc_per_min`
   - Returns single charging stop

5. **Two-Stop Strategy** (if `delta_needed > 100%`):
   - Selects top 2 highest-power chargers
   - Splits charge requirement equally between stops
   - Returns two charging stops

**Greedy Selection**: Currently selects highest-power chargers, not necessarily optimal for route deviation.

#### Route Planning Workflow

```
1. Validate vehicle exists in database
2. Get route from OSRM (distance, duration, geometry)
3. Save query to database (audit trail)
4. Find charging stations along route:
   - Sample points along route
   - Query OCM for each sample
   - Filter stations within 5km of route (using Shapely)
5. Calculate charging plan (plan_one_stop algorithm)
6. Calculate time estimates:
   - Fastest: drive_time + charge_time
   - Cheapest: drive_time + (charge_time * 1.3 if low-power chargers)
7. Save plans to database
8. Return results
```

**Geometric Filtering**:
```python
# Uses Shapely for spatial operations
line = LineString(route_coordinates)
for station in stations:
    point = Point(station["lon"], station["lat"])
    if line.distance(point) <= 0.05:  # ~5km in degrees
        candidates.append(station)
```

**Note**: The distance check (`0.05` degrees) is approximate. More accurate would use geodesic distance (Haversine formula).

---

## Frontend Architecture

### Streamlit Application (`frontend/streamlit_app.py`)

**UI Components**:

1. **Location Input** (`typeahead()` function):
   - Text input with autocomplete
   - Calls `/api/v1/autocomplete` on user input (≥3 characters)
   - Displays suggestions in dropdown
   - Returns selected location coordinates

2. **Vehicle Configuration Sidebar**:
   - Vehicle ID selector (1-5)
   - Start SOC slider (1-100%)
   - Arrival SOC slider (0-100%)

3. **Route Planning**:
   - "Plan Route" button triggers `/api/v1/ev-plan`
   - Displays fastest and cheapest plans side-by-side

4. **Map Visualization** (PyDeck):

   **Layers**:
   - **PathLayer**: Route polyline (blue line)
   - **IconLayer (Flags)**: Start (green) and end (red) markers
   - **ScatterplotLayer**: All candidate charging stations (gray dots)
   - **IconLayer (Charging)**: Selected charging stops (amber icons)

   **Map Configuration**:
   - Centers on route midpoint
   - Zoom level: 6 (adjustable)
   - Tooltips show station name and charge time

**PyDeck Concepts**:
- **WebGL Rendering**: Hardware-accelerated map rendering
- **Layers**: Stacked visualizations (routes, points, icons)
- **ViewState**: Camera position (lat, lon, zoom, pitch, bearing)
- **IconLayer**: Uses built-in icons (flag, charging-station)

---

## Complete Workflow

### End-to-End User Journey

```
1. USER OPENS FRONTEND
   └─> Streamlit app loads on port 8501

2. USER SEARCHES FOR START LOCATION
   └─> Types "Berlin" in departure field
   └─> Frontend: GET /api/v1/autocomplete?q=Berlin&limit=5
   └─> Backend: Calls Photon API
   └─> Returns: [{label: "Berlin, Germany", coord: [13.4050, 52.5200]}, ...]
   └─> User selects from dropdown

3. USER SEARCHES FOR END LOCATION
   └─> Same process as step 2

4. USER CONFIGURES VEHICLE
   └─> Selects Vehicle ID: 1
   └─> Sets Start SOC: 80%
   └─> Sets Arrival SOC: 20%

5. USER CLICKS "PLAN ROUTE"
   └─> Frontend: POST /api/v1/ev-plan
       {
         "start": [13.388860, 52.517037],
         "end": [13.397634, 52.529407],
         "start_soc": 80.0,
         "arrival_soc": 20.0,
         "vehicle_id": 1
       }

6. BACKEND PROCESSING
   ├─> Validates vehicle exists (Query Vehicle table)
   ├─> Gets route from OSRM
   │   └─> Returns: distance=200km, duration=180min, geometry=LineString
   ├─> Saves query to database (Query table)
   ├─> Finds charging stations:
   │   ├─> Samples 12 points along route
   │   ├─> Queries OCM for each sample (radius 7km)
   │   ├─> Deduplicates by OCM ID
   │   └─> Filters stations within 5km of route (Shapely)
   ├─> Calculates charging plan:
   │   ├─> Computes required SOC: 200km / 5km_per_% = 40%
   │   ├─> Computes deficit: 20% + 40% - 80% = -20% (no charging needed)
   │   └─> OR selects chargers if deficit > 0
   ├─> Calculates time estimates (fastest vs cheapest)
   └─> Saves plans to database (Plan table)

7. FRONTEND DISPLAYS RESULTS
   ├─> Shows summary: Drive 180min, Charge 0min, Total 180min
   ├─> Renders map with:
   │   ├─> Route polyline (blue)
   │   ├─> Start flag (green)
   │   ├─> End flag (red)
   │   ├─> Candidate stations (gray dots)
   │   └─> Selected charging stops (amber icons)
   └─> Displays both "fastest" and "cheapest" plans
```

---

## Technical Concepts & Algorithms

### 1. State of Charge (SOC) Calculation

**Formula**:
```
SOC_needed = distance_km / consumption_km_per_soc
```

**Example**:
- Vehicle: 5 km per 1% SOC
- Route: 200 km
- Required SOC: 200 / 5 = 40%

**Concept**: Linear consumption model (simplified; real-world varies with speed, elevation, temperature).

---

### 2. Charging Time Calculation

**Formula**:
```
charge_time_min = (target_soc - current_soc) / charge_rate_soc_per_min
```

**Example**:
- Need to charge from 20% to 80% (60% increase)
- Charge rate: 2% per minute
- Charge time: 60 / 2 = 30 minutes

---

### 3. Bounding Box Calculation (`bbox_around_line()`)

**Purpose**: Create a geographic bounding box around a route with buffer.

**Algorithm**:
```python
1. Find min/max longitude and latitude from route coordinates
2. Calculate buffer in degrees:
   - 1 degree latitude ≈ 111 km
   - 1 degree longitude ≈ 111 * cos(latitude) km
3. Add buffer to bounding box
```

**Example**:
- Route spans: lon [13.0, 14.0], lat [52.0, 53.0]
- Buffer: 5 km
- Buffer in degrees: ~0.045° (lat), ~0.045° / cos(52.5°) ≈ 0.074° (lon)
- Bounding box: [12.926, 51.955, 14.074, 53.045]

**Limitation**: This is an approximation. More accurate would use geodesic calculations (Haversine).

---

### 4. Spatial Filtering (Shapely)

**Purpose**: Filter charging stations within distance of route.

**Method**:
```python
line = LineString(route_coordinates)
point = Point(station_lon, station_lat)
distance_degrees = line.distance(point)
if distance_degrees <= 0.05:  # ~5km
    include_station()
```

**Concept**: Shapely uses planar geometry (Euclidean distance in degrees). For accurate kilometers, use `geopy.distance` or `shapely.ops.transform` with a projection.

---

### 5. Greedy Charger Selection

**Current Algorithm**:
1. Sort candidates by `power_kw` (descending)
2. Select top N chargers (N = 1 or 2)
3. Calculate charge time based on power

**Limitations**:
- Doesn't consider route deviation (distance to charger)
- Doesn't optimize for total travel time
- Doesn't consider charger availability/occupancy

**Better Approach** (not implemented):
- Use graph search (Dijkstra/A*) with charging stops as nodes
- Minimize: `drive_time + charge_time + deviation_time`
- Consider charger power, distance, and availability

---

### 6. Fastest vs Cheapest Strategy

**Fastest**:
- Uses highest-power chargers
- Minimizes total time: `drive_time + charge_time`

**Cheapest**:
- Assumes slower chargers are cheaper (AC vs DC)
- Applies 1.3x multiplier to charge time if all chargers ≤ 22kW
- Formula: `drive_time + (charge_time * slow_factor)`

**Note**: Cost calculation (`total_cost_eur`) is not implemented; only time estimates.

---

## API Endpoints Summary

| Endpoint | Method | Purpose | Input | Output |
|----------|--------|---------|-------|--------|
| `/health` | GET | Health check | None | `{ok: true, env: {...}}` |
| `/api/v1/autocomplete` | GET | Location search | `q`, `limit` | `[{label, coord}]` |
| `/api/v1/route` | POST | Basic routing | `{start, end, profile}` | `{distance_km, duration_min, line}` |
| `/api/v1/charging-stations` | GET | Station lookup | `bbox`, `maxresults` | `{count, items: [...]}` |
| `/api/v1/ev-plan` | POST | EV route planning | `{start, end, start_soc, arrival_soc, vehicle_id}` | `{fastest, cheapest, chargers}` |

---

## External Service Integrations

### 1. OSRM (Open Source Routing Machine)

**URL**: `https://router.project-osrm.org` (public instance)

**API**:
```
GET /route/v1/{profile}/{coordinates}?overview=full&geometries=polyline
```

**Response Format**:
```json
{
  "routes": [{
    "distance": 1234.5,  // meters
    "duration": 180.2,   // seconds
    "geometry": "encoded_polyline"
  }]
}
```

**Rate Limits**: Public instance has rate limits; production should use self-hosted OSRM.

---

### 2. Photon Geocoding

**URL**: `https://photon.komoot.io`

**API**:
```
GET /api?q={query}&limit={limit}
```

**Response Format** (GeoJSON):
```json
{
  "features": [{
    "geometry": {"coordinates": [lon, lat]},
    "properties": {
      "name": "Berlin",
      "city": "Berlin",
      "country": "Germany"
    }
  }]
}
```

**Rate Limits**: Free, no API key required, but has rate limits.

---

### 3. OpenChargeMap (OCM)

**URL**: `https://api.openchargemap.io/v3/poi`

**API**:
```
GET /v3/poi?latitude={lat}&longitude={lon}&distance={km}&maxresults={n}
GET /v3/poi?boundingbox={min_lat},{min_lon},{max_lat},{max_lon}&maxresults={n}
```

**Response Format**:
```json
[{
  "ID": 12345,
  "AddressInfo": {
    "Title": "Tesla Supercharger",
    "Latitude": 52.5200,
    "Longitude": 13.4050
  },
  "Connections": [{
    "PowerKW": 150.0
  }]
}]
```

**API Key**: Optional but recommended for higher rate limits.

**Country Filter**: Currently hardcoded to "DE" (Germany).

---

## Deployment & Infrastructure

### Docker Compose Architecture

**Services**:

1. **db** (PostgreSQL 16):
   - Container: `evr_db`
   - Port: 5432
   - Database: `evr`
   - User: `evr` / Password: `evrpass`
   - Volume: `dbdata` (persistent storage)

2. **redis** (Redis 7):
   - Container: `evr_redis`
   - Port: 6379
   - **Note**: Configured but not actively used in code

3. **backend** (FastAPI):
   - Container: `evr_backend`
   - Port: 8000
   - Build: `./backend/dockerfile`
   - Startup: `/app/start.sh`
   - Dependencies: `db`, `redis`

4. **frontend** (Streamlit):
   - Container: `evr_frontend`
   - Port: 8501
   - Build: `./frontend/Dockerfile`
   - Command: `streamlit run streamlit_app.py`

**Network**: All services on `evr-network` (bridge network)

---

### Backend Startup Script (`backend/start.sh`)

**Steps**:

1. **Wait for PostgreSQL**:
   - Polls database connection (max 30 attempts, 1s interval)
   - Uses SQLAlchemy `pool_pre_ping` to test connection

2. **Seed Database**:
   - Runs `seed.py` to create initial vehicles
   - Idempotent (won't duplicate if already seeded)

3. **Start Uvicorn**:
   - Runs FastAPI app on `0.0.0.0:8000`
   - Uses `exec` to replace shell process

**Error Handling**: Gracefully handles database connection failures and seed errors.

---

### Database Seeding (`backend/seed.py`)

**Purpose**: Create initial vehicle data.

**Process**:
1. Creates database tables (if not exist): `Base.metadata.create_all(engine)`
2. Checks if vehicles already exist
3. If empty, creates 5 sample vehicles:
   - Names: "EV-1" through "EV-5"
   - Random battery sizes: 55, 64, 70, 77, or 82 kWh
   - Random consumption: 4.0-8.0 km per 1% SOC
   - Random charge rate: 1.0-3.0% per minute

**Idempotency**: Won't create duplicates if run multiple times.

---

## Data Flow Diagrams

### Route Planning Request Flow

```
User Input
    │
    ▼
Frontend (Streamlit)
    │ POST /api/v1/ev-plan
    ▼
Backend Router (plan.py)
    │
    ├─> Validate Vehicle (DB Query)
    │
    ├─> Get Route (OSRM Service)
    │   └─> OSRM API
    │
    ├─> Save Query (DB Insert)
    │
    ├─> Find Stations (OCM Service)
    │   ├─> Sample Route Points
    │   ├─> Query OCM (multiple calls)
    │   └─> Filter by Distance (Shapely)
    │
    ├─> Calculate Plan (plan_one_stop)
    │   ├─> Calculate SOC Requirements
    │   ├─> Select Chargers (greedy)
    │   └─> Calculate Times
    │
    ├─> Save Plans (DB Insert)
    │
    └─> Return JSON Response
        │
        ▼
Frontend Display
    ├─> Summary Statistics
    └─> Map Visualization (PyDeck)
```

---

## Key Technical Decisions

### 1. **Why FastAPI?**
- Async/await support for concurrent external API calls
- Automatic OpenAPI documentation
- Type validation with Pydantic
- High performance (comparable to Node.js)

### 2. **Why Streamlit?**
- Rapid prototyping (no HTML/CSS/JS needed)
- Python-native (same language as backend)
- Built-in widgets and map support (PyDeck)

### 3. **Why PostgreSQL?**
- Relational data (vehicles, queries, plans)
- ACID compliance for data integrity
- JSON support for flexible plan storage

### 4. **Why Shapely for Geometry?**
- Simple API for point-line distance
- Fast for filtering operations
- Note: Uses planar geometry (approximation)

### 5. **Why Sample Points for Station Search?**
- OCM API doesn't support route/polyline queries
- Reduces API calls (12 vs hundreds)
- Trade-off: May miss stations between samples

---

## Limitations & Future Improvements

### Current Limitations

1. **Simplified Charging Model**:
   - Linear consumption (doesn't account for speed, elevation, weather)
   - Constant charge rate (doesn't account for charging curve)
   - No consideration of charger availability

2. **Greedy Charger Selection**:
   - Doesn't optimize for route deviation
   - Doesn't consider total travel time holistically

3. **Geographic Approximation**:
   - Uses degree-based distance (not geodesic)
   - Bounding box calculation is approximate

4. **No Cost Calculation**:
   - `total_cost_eur` is NULL
   - No pricing data integration

5. **No Real-time Data**:
   - Doesn't check charger availability
   - Doesn't consider traffic conditions

### Potential Improvements

1. **Advanced Routing**:
   - Graph-based optimization (Dijkstra/A*)
   - Consider route deviation in charger selection
   - Multi-stop optimization

2. **Better Charging Model**:
   - Non-linear consumption (speed, elevation)
   - Charging curve (fast at low SOC, slower at high SOC)
   - Temperature effects

3. **Real-time Integration**:
   - Charger availability APIs
   - Traffic data (OSRM traffic service)
   - Weather data for consumption adjustment

4. **Cost Optimization**:
   - Charging pricing APIs
   - Time-of-day pricing
   - Membership discounts

5. **Caching**:
   - Redis for route caching
   - Station data caching (StationCache model not actively used)

6. **User Features**:
   - Save favorite routes
   - Vehicle profiles
   - Route history

---

## Conclusion

This EV routing system demonstrates a complete full-stack application with:
- **Backend**: FastAPI with external service integration
- **Frontend**: Streamlit with interactive maps
- **Database**: PostgreSQL for persistence
- **Algorithms**: SOC calculation, charger selection, route optimization
- **Infrastructure**: Docker Compose for easy deployment

The system provides a solid foundation for EV route planning, with clear extension points for more sophisticated algorithms and real-time data integration.

