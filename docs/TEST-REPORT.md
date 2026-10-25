# WindSight UK QA Test Report

## Executed checks

| Check | Result | Evidence |
|---|---|---|
| Backend tests: `python -m pytest` | Passed | 38 tests passed, including automated-ingestion idempotency/failure cases, mocked Elexon responses, normalization, cutoff selection, duplicate handling, metric edge cases, and API validation. |
| Python lint: `ruff check app tests` | Passed | Ruff completed without findings. |
| Python compilation: `python -m compileall -q app tests` | Passed | No syntax or compilation errors. |
| Frontend TypeScript: `npm run typecheck` | Passed | `tsc -b` completed without diagnostics. |
| Frontend lint: `npm run lint` | Passed | ESLint completed with no errors or warnings. |
| Frontend unit tests: `npm test` | Passed | 3 tests passed for date-range boundaries and London daylight-saving formatting. |
| Frontend browser test: `npm run e2e` | Passed | Playwright verified backtesting page rendering, visible API errors, duplicate-cutoff rejection, navigation semantics, and no horizontal page overflow at 390 px. |
| Frontend production build: `npm run build` | Passed | Entry chunk is 355.87 kB minified / 115.00 kB gzip; chart chunk is 376.43 kB / 108.10 kB gzip. No chunk triggers Vite's 500 kB warning. The earlier unsplit entry was 771.54 kB. |
| CI workflow YAML | Passed | Local YAML parse found backend, frontend, and Docker jobs. GitHub-hosted execution was not available. |
| API health and frontend delivery | Historical pass | Previous local QA recorded `GET /api/health` and Vite root as HTTP 200. |
| Frontend API proxy and CORS | Historical pass | Previous local QA recorded a successful Vite `/api/health` proxy and matching CORS origin. |
| Live full-period analytics | Historical pass | Previous run recorded successful January 2026 overview, accuracy, and comparison requests from Elexon. |
| Other routes and responsive layout | Historical/limited | Previous QA recorded route/date-filter checks; current Playwright additionally checks the backtesting page at 390 px. Other routes and tablet layouts were not rechecked. |

## Live data evidence

The previous full January decision-period dashboard run returned 1,488 expected half-hour
intervals, 1,488 actual WIND observations, 744 selected forecast observations,
and 744 matched forecast/actual intervals. Forecast coverage was 50% and actual
coverage was 100%. This is consistent with the observed hourly WINDFOR target
times and half-hourly FUELHH actuals; unmatched intervals were left missing,
not interpolated. The data-quality panel reported successful Elexon retrieval,
35,989 normalized forecast records, and no malformed records for that run.

The metrics are indicative because the available WINDFOR endpoint documentation
does not confirm that its generation semantics are equivalent to FUELHH.

A fresh, bounded WINDFOR request for the UTC publication window
2026-01-01T00:00:00Z through 2026-01-02T00:00:00Z returned HTTP 200 and 584
records in one JSON response: 8 publication timestamps and 73 distinct hourly
target timestamps. The response did not include `Link` or `Content-Range`
headers. This confirms one bounded response was returned but does not establish
the endpoint's behavior for larger requests or prove that no truncation is
possible.

## Failed checks

All final automated checks listed above passed. During setup, Ruff found two
unused imports, and Vitest initially collected the Playwright spec; both were
corrected. The first Playwright assertion expected an HTTP status string, while
the frontend correctly surfaced the backend's structured error detail; the
assertion now verifies that visible detail.

## Unverified items and limitations

- Docker is not installed in this environment. `docker compose up --build`,
  container health checks, image builds, and container-to-container Nginx
  routing could not be executed locally. CI is configured to build both images,
  but no hosted workflow run is available as evidence. Verify locally with
  `docker compose up --build`, then visit `http://localhost:8080` and
  `http://localhost:8000/api/health`; stop with `docker compose down`.
- No public deployment was performed. A hosting target and configured deployment
  account are not available in this workspace, so no public URL is available to
  verify.
- The Playwright error case uses a mocked 503 response; no live browser session
  with Elexon deliberately unavailable was simulated.
- No tablet-specific viewport check was run.
- WINDFOR measurement-unit/averaging equivalence to FUELHH remains unconfirmed
  by the consulted endpoint documentation. Comparisons therefore remain
  exact-timestamp, MW-based, and explicitly indicative.
- No MWh conversion, forecast interpolation, missing-value substitution, or
  commercial savings estimate is performed.
