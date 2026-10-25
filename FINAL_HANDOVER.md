# WindSight UK — Final Handover

## Delivery summary

WindSight UK is implemented as a React/TypeScript frontend and FastAPI backend
for decision-support analysis of day-ahead wind forecasts. The application uses
Elexon BMRS FUELHH actuals filtered to WIND and WINDFOR forecast records only.
It does not execute trades or estimate commercial savings.

## Completed features

- Modular backend/client/services/schemas/tests and React pages/components/hooks.
- Async Elexon ingestion with normalization, validation, retries, rate-limit
  handling, configurable disk cache, and retrieval diagnostics.
- Point-in-time selection for January 1–31, 2026 decisions, with next-day
  delivery dates, including February 1 for January 31 decisions.
- UTC timestamp handling, Europe/London cutoff and presentation, missing-data
  representation, conflict flags, provenance, and forecast age.
- Backend MAE, RMSE, mean bias, WAPE, maximum absolute error, matched/missing
  counts, and separate coverage.
- Connected responsive dashboard pages: Overview, Forecast Explorer, Accuracy
  Analysis, Historical Analysis, and Methodology/Data Quality.
- Dockerfiles, Compose topology, backend health check, and Nginx API proxy
  configuration.
- Root README, this handover, technical review, and executed test report.

## Audit confirmations

| Audit item | Status | Evidence / qualification |
|---|---|---|
| No fake production generation data | Confirmed by source review and live data use | Test fixtures are explicitly test-only; production pages query backend APIs. |
| No hardcoded credentials detected | First-party source/template scan | No credential-like values were found in application source or environment templates. A dedicated secret scanner was not run. |
| No look-ahead selection | Confirmed by service/test review | Forecast eligibility requires publication timestamp at or before the UTC-converted cutoff; tests include a future-published forecast. |
| January decision scope | Confirmed | Analysis endpoints validate January 1–31, 2026 inclusive; each decision maps to next-day delivery. |
| Real Elexon integration | Verified | Live BMRS-backed analytics and record counts were observed in local dashboard/API checks; integration tests also mock HTTP responses. |
| Frontend works | Verified locally | Vite frontend returned HTTP 200; all five dashboard routes rendered, the date filter updated, and a 390 px viewport smoke test had no horizontal overflow. |
| Backend works | Verified locally | `/api/health` returned `{"status":"healthy","service":"windsight-uk-api"}`; analysis routes returned HTTP 200 with live source data. |
| Docker configuration exists | Confirmed by file review | Backend/frontend Dockerfiles, Compose, ignore files, and Nginx proxy are present. Actual image/container execution was not verified. |
| README complete | Confirmed by review | Setup, data definitions, methodology, metrics, environment variables, API, tests, deployment guidance, limitations, future work, and AI disclosure are included. |
| AI disclosure exists | Confirmed | Required disclosure appears in README. |

## Audit scope

The workspace is not recognized as a Git repository (`git status` reports that
no repository exists), so a branch/diff/history review was not possible. The
audit reviewed first-party application, test, Docker, environment-template, and
documentation files; generated dependency and build directories were not
treated as source files.

## Verified tests and checks

The latest recorded automated validation:

- `python -m pytest`: **24 passed**.
- `python -m compileall -q app tests`: passed.
- `npm run typecheck`: passed.
- `npm run lint`: passed without errors or warnings.
- `npm run build`: passed; Vite emitted a non-fatal large-chunk advisory for a
  roughly 751 kB minified JavaScript bundle.

Live/manual verification recorded in [docs/TEST-REPORT.md](./docs/TEST-REPORT.md):

- Backend health and frontend HTTP responses: 200.
- Vite `/api/health` proxy and backend CORS header: verified.
- Full January overview, accuracy, and comparison requests: 200.
- Observed results: 1,488 expected half-hour intervals, 1,488 WIND actuals,
  744 selected forecasts, 744 matched observations, 50% forecast coverage, and
  100% actual coverage. The hourly versus half-hourly cadence explains absent
  forecast matches; no interpolation was performed.
- Five page routes, selected-date behavior (2 January decision to 3 January
  delivery), and narrow viewport: verified.

## Deployment status

- **Public deployment:** not performed; no public URL is configured or verified.
- **Docker:** configuration exists, but Docker is not installed in the audit
  environment. Image build, health checks, and container network routing remain
  unverified.
- **Verified local URLs:** frontend <http://localhost:5173/overview>, backend
  health <http://localhost:8000/api/health>, and API docs
  <http://localhost:8000/docs>.
- **Configured, unverified Docker URLs:** frontend <http://localhost:8080> and
  backend health <http://localhost:8000/api/health>.

## Known limitations

- WINDFOR generation unit/averaging semantics have not been shown by the
  inspected endpoint documentation to be equivalent to FUELHH. Accuracy values
  must remain indicative until this is confirmed.
- WINDFOR observations are hourly in the inspected responses, while FUELHH is
  half-hourly. Comparison uses exact UTC matches only; there is no interpolation
  or forward fill.
- Forecast collection uses a configurable 31-day default publication lookback,
  not a source retention guarantee; older forecast revisions might be outside
  the requested window.
- The default noon cutoff is a configurable assumption, not an asserted market
  gate closure.
- Diagnostics and the 30-second analytics cache are process-local; cache and
  source-request behavior do not use a persistent database.
- The production bundle exceeds Vite's advisory chunk threshold.
- Docker startup, public deployment, tablet-specific layout, and browser
  behavior during deliberate live Elexon outage were not verified.

## Exact run instructions

### Local development

Backend terminal (PowerShell):

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m uvicorn app.main:app --reload
```

Frontend terminal:

```powershell
cd frontend
npm ci
Copy-Item .env.example .env.local
npm run dev
```

Open <http://localhost:5173/overview>. API health is at
<http://localhost:8000/api/health>.

### Docker (requires Docker Engine/Desktop and Compose v2)

From repository root:

```powershell
docker compose up --build
```

Open <http://localhost:8080>; check the backend at
<http://localhost:8000/api/health>. Stop with:

```powershell
docker compose down
```

These Docker instructions have not yet been executed in this environment.

## Remaining work

1. Confirm WINDFOR/FUELHH unit and aggregation comparability with Elexon metadata
   or the data owner; revisit the interpretation of metrics afterward.
2. Obtain and document the business-approved decision cutoff, if it differs
   from the configurable noon default.
3. Run `docker compose up --build`, check both services and Nginx API routing,
   then `docker compose down` in a Docker-enabled environment.
4. Deploy only after selecting approved frontend/backend hosts; configure
   `VITE_API_BASE_URL` and `WINDSIGHT_FRONTEND_ORIGINS`, then verify the public
   URLs before marking deployment complete.
5. Consider bundle chunking and CI/deployment automation as follow-on work.

## Review references

- [Project README](./README.md)
- [Technical Lead Review](./docs/TECHNICAL_LEAD_REVIEW.md)
- [QA Test Report](./docs/TEST-REPORT.md)
