# WindSight UK QA Test Report

## Executed checks

| Check | Result | Evidence |
|---|---|---|
| Backend tests: `python -m pytest` | Passed | 24 tests passed, including mocked Elexon responses, normalization, cutoff selection, duplicate handling, metric edge cases, and API validation. |
| Python compilation: `python -m compileall -q app tests` | Passed | No syntax or compilation errors. |
| Frontend TypeScript: `npm run typecheck` | Passed | `tsc -b` completed without diagnostics. |
| Frontend lint: `npm run lint` | Passed | ESLint completed with no errors or warnings. |
| Frontend production build: `npm run build` | Passed with warning | Vite produced production assets. The main JavaScript chunk is about 751 kB minified, above Vite's 500 kB advisory threshold. |
| API health and frontend delivery | Passed | `GET /api/health` and the Vite root returned HTTP 200. |
| Frontend API proxy and CORS | Passed | Vite `/api/health` proxy returned HTTP 200; a request with `Origin: http://localhost:5173` returned the matching `Access-Control-Allow-Origin` header. |
| Live full-period analytics | Passed | Overview, accuracy, and comparison requests for January 2026 returned HTTP 200 using live Elexon data. |
| Browser routes and date filter | Passed | All five dashboard pages rendered. Selecting the 2 January decision showed the 3 January delivery date and updated the displayed period. |
| Responsive layout smoke check | Passed | At a 390 px viewport, the page body had no horizontal overflow. |

## Live data evidence

The full January decision-period dashboard returned 1,488 expected half-hour
intervals, 1,488 actual WIND observations, 744 selected forecast observations,
and 744 matched forecast/actual intervals. Forecast coverage was 50% and actual
coverage was 100%. This is consistent with the observed hourly WINDFOR target
times and half-hourly FUELHH actuals; unmatched intervals were left missing,
not interpolated. The data-quality panel reported successful Elexon retrieval,
35,989 normalized forecast records, and no malformed records for that run.

The metrics are indicative because the available WINDFOR endpoint documentation
does not confirm that its generation semantics are equivalent to FUELHH.

## Failed checks

No final automated checks failed. Two early browser-smoke attempts used an
incorrect expected page heading and an ambiguous selector; the locators were
corrected, and all pages and the date-filter check then passed.

## Unverified items and limitations

- Docker is not installed in this environment. `docker compose up --build`,
  container health checks, and container-to-container Nginx routing could not
  be executed. Verify locally with `docker compose up --build`, then visit
  `http://localhost:8080` and `http://localhost:8000/api/health`; stop with
  `docker compose down`.
- No public deployment was performed. A hosting target and configured deployment
  account are not available in this workspace, so no public URL is available to
  verify.
- Browser error and empty-data states are implemented and backend/error cases
  are covered by tests, but a live browser session with Elexon deliberately
  unavailable was not simulated.
- No tablet-specific viewport check was run.
- WINDFOR measurement-unit/averaging equivalence to FUELHH remains unconfirmed
  by the consulted endpoint documentation. Comparisons therefore remain
  exact-timestamp, MW-based, and explicitly indicative.
- No MWh conversion, forecast interpolation, missing-value substitution, or
  commercial savings estimate is performed.
