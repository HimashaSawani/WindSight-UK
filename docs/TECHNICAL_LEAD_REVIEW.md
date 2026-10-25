# Technical Lead Review

## Architecture

WindSight is a small two-tier application. A React/TypeScript single-page
application uses a typed Axios client and TanStack Query to call the FastAPI
service. In development, Vite proxies `/api` to the backend; in the configured
container topology, Nginx serves static assets and forwards `/api/` to the
backend service. No database or third-party data provider is used.

Backend concerns are separated into API routers, core settings, the Elexon
client, Pydantic schemas, and reusable ingestion, normalization,
point-in-time-selection, and metric services.

## Backend services

- **API:** `/api/health`, `/overview`, `/forecasts`, `/actuals`, `/comparison`,
  `/accuracy`, `/history`, and `/data-quality`. Analysis routes validate the
  January 2026 decision-date range and expose typed response models. Elexon
  errors are translated to explicit HTTP 502 responses; invalid query/range
  inputs receive HTTP 422.
- **Ingestion:** fetches actuals for the delivery date window and forecast
  publications for a configurable lookback through the final decision cutoff.
- **Normalization:** parses timezone-aware source timestamps, validates finite
  numeric generation, filters actuals to WIND, normalizes to UTC, and retains
  original source fields as metadata. Malformed rows are counted and logged.
- **Selection:** creates expected local delivery-day intervals, selects one
  point-in-time forecast per target, explicitly marks missing values, and
  carries forecast age and duplicate conflict indicators.
- **Metrics:** computes aggregate and daily error metrics exclusively from
  matched forecast/actual observations; it reports forecast and actual
  availability separately.

## Elexon API integration

The asynchronous HTTPX client calls the documented FUELHH and WINDFOR stream
endpoints at `https://data.elexon.co.uk/bmrs/api/v1`. FUELHH requests include
inclusive settlement-date parameters and `fuelType=WIND`; date ranges are
fetched one day at a time. WINDFOR uses publication-time filters and splits
the requested publication window at UTC day boundaries. Requests are bounded
by a semaphore, have configurable timeouts and retry limits, honor numeric and
HTTP-date `Retry-After` values, and retry timeouts, transport failures, HTTP
429, and HTTP 5xx responses. Other HTTP errors are reported rather than
converted to successful empty results.

Raw source records are not substituted with mock values. Disk cache entries
are keyed by request URL/parameters; cache TTL and forced refresh are settings.
Source record metadata and the original publication timestamp are retained.
The endpoint documentation inspected does not document a pagination contract
or a maximum date span; the implementation uses day-sized requests and
configurable lookback bounds.

## Data models and provenance

`ActualRecord` and `ForecastRecord` use timezone-aware `start_time` normalized
to UTC and finite `generation_mw`; forecasts also retain `publish_time`.
Original fields reside in `source_metadata`. A comparison observation records
the decision date, following delivery date, cutoff timestamp, target timestamp,
selected publication timestamp/value, actual value, forecast age, availability,
error, duplicate conflict flags, and available source metadata. The interval
and metric schemas are explicitly typed.

## Forecast revision selection and point-in-time correctness

For each target, only records with `publishTime <= cutoff` are eligible. The
selected revision has the greatest eligible publication timestamp. Forecast
groups are organized by normalized target time; target comparison uses exact
UTC equality. A later-published forecast cannot be selected for an earlier
decision. Equal latest timestamps with different numeric values are
deterministically resolved and flagged as a conflict; actual duplicate
conflicts are likewise flagged. No forecast is inferred for targets without an
eligible row.

The decision dates are January 1–31, 2026, inclusive. Delivery is the next
Europe/London calendar day, so January 31 maps to February 1. This distinction
is carried in every comparison response.

## Timezone handling

Source timestamps must carry timezone information; normalization converts them
to UTC. A configured clock time is combined with each decision date in
`Europe/London` and converted to UTC before comparison with `publishTime`.
Expected half-hour intervals derive from consecutive London midnights, so days
with daylight-saving transitions correctly contain 46 or 50 intervals rather
than assuming every civil day has 48. The UI formats relevant timestamps for
Europe/London display.

## Accuracy formulas and semantics

For matched rows only, `error = forecast - actual`. MAE is the mean absolute
error; RMSE is the square root of the mean squared error; mean bias is the
arithmetic mean of signed errors (positive means overforecast); WAPE is the sum
of absolute errors divided by the sum of absolute matched actual values, times
100. WAPE is null for a zero denominator. Maximum absolute error and matched
observation count are also returned. Missing forecast and actual counts are
independent, and coverage is based on expected target intervals. No MAPE is
computed, no missing observation is treated as zero, and no arbitrary accuracy
percentage is used.

FUELHH documentation describes average MW over half-hour intervals. The
WINDFOR endpoint docs inspected do not establish equivalent generation units
and averaging semantics; observed forecast starts are hourly. Exact timestamp
comparison without interpolation avoids inventing values, but metrics remain
indicative pending data-definition confirmation.

## Caching and operational behavior

The Elexon client uses an optional configurable local disk response cache
(default TTL 900 seconds). Forced refresh bypasses cache reads. Analysis
responses are deduplicated for concurrent identical requests and cached in
process for 30 seconds. A semaphore limits concurrent source requests to four.
`/api/data-quality` reports process-local request, cache-hit, normalized, and
invalid-record counts; these diagnostics do not persist across process restarts.

## Testing

Backend pytest coverage includes mocked HTTP success/error/retry/cache cases,
normalization, cutoff/revision selection, future-publication exclusion,
duplicates, missing actual/forecast states, metrics, zero denominator, empty
data, timezone conversion, DST, and month boundary behavior. Frontend checks
are TypeScript project checking, ESLint, and a production Vite build. The
documented QA report records live HTTP/browser checks and explicitly identifies
items not verified.

## Docker

The backend image uses `python:3.12-slim`, installs the Python package, exposes
port 8000, and has an HTTP health check. The frontend Dockerfile builds assets
using Node 22 and serves them with Nginx. Compose waits for a healthy backend
before starting the frontend and maps ports 8080 and 8000. Nginx proxies the
same-origin `/api/` path to the backend. Docker CLI was unavailable during
handover QA, so no image build or container execution is claimed.

## Deployment

There is no configured public hosting environment or verified public URL.
Local development URLs and the proposed Docker ports are documented in the
README. A future frontend deployment must use an API base URL that points to
the deployed backend and set backend CORS origins to the actual frontend
origin. Public availability, CORS, health, and full analytics must be tested
before handover claims production deployment.

## Review disposition

The modular design and transparent point-in-time selection are appropriate for
the decision-support MVP. The release should remain explicitly indicative until
forecast/actual data semantics are confirmed. Docker verification, public
deployment, and the production JavaScript chunk-size advisory remain follow-up
items rather than completed acceptance evidence.
