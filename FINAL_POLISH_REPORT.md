# WindSight UK — Final Polish Report

## Outcome

The production-polish audit was followed by a focused set of improvements to
data-source transparency, automated validation, route loading, and project
documentation. Temporal forecast selection and existing analytics behavior
were preserved. The project is better tested and clearer about its operational
boundaries, but it is not certified as a production energy platform or as a
like-for-like forecast-accuracy service.

## Changes delivered

- Declared `analytics_data_source: "live_elexon"` in the data-quality API.
  The methodology page and README now distinguish live analysis requests from
  the separate persisted ingestion archive.
- Added GitHub Actions jobs for Ruff and pytest, frontend ESLint/typechecking,
  Vitest, Playwright, production builds, and backend/frontend Docker image
  builds.
- Added focused frontend tests for date-range boundaries and London daylight-
  saving formatting, plus a browser test for backtesting route rendering,
  surfaced API errors, duplicate-cutoff validation, navigation semantics, and
  a 390 px viewport overflow check.
- Lazy-loaded page routes. The previous 771.54 kB JavaScript entry was split
  into a 355.87 kB entry and a 376.43 kB chart chunk; neither exceeds Vite's
  500 kB warning threshold.
- Added a Mermaid architecture diagram and refreshed the audit and QA reports.
  The README already contained an AI-assistance disclosure.

## Verification

| Check | Result |
|---|---|
| `python -m pytest` | 38 passed |
| `ruff check app tests` | Passed |
| `npm test` | 3 passed |
| `npm run e2e` | 1 Playwright test passed, including a 390 px viewport check |
| `npm run lint` | Passed |
| `npm run build` | TypeScript check and production build passed |
| CI workflow YAML parse | Passed; backend, frontend, and Docker jobs detected |
| Bounded live WINDFOR request | HTTP 200; 584 records, 8 publication times, 73 hourly target times |

The live WINDFOR response for one UTC publication day included no `Link` or
`Content-Range` headers. This is evidence about that bounded response only; it
does not establish the endpoint's complete pagination or truncation behavior.
The prior full-January QA run recorded 1,488 expected intervals, 1,488 actuals,
744 selected forecasts, and 744 matched observations. That 50% forecast
coverage is consistent with hourly forecast targets matched against a
half-hour grid, but response completeness and source measurement equivalence
remain unconfirmed. No interpolation was introduced.

## Remaining production gaps

- The file-backed ingestion store has no retention or indexing policy and is
  intended for a small, single-process portfolio deployment. A retention policy
  was not imposed because it could discard revisions needed for historical
  analysis.
- WINDFOR pagination/record limits and WINDFOR/FUELHH measurement semantics
  still need authoritative confirmation.
- Docker is unavailable locally. The configured Docker image-build workflow
  and GitHub-hosted CI have not run in this environment.
- Browser coverage is intentionally narrow. No tablet-layout,
  accessibility-tool, assistive-technology, or full-route browser audit was
  performed.
- The protected manual-ingestion endpoint still depends on deployment-level
  HTTPS and secret management.

## Recommendation

Present WindSight UK as a well-tested portfolio analytics application with
indicative metrics. Before expanding data history, replicas, or public
deployment, confirm source completeness, choose an explicit storage-retention
strategy, run the CI workflow, and verify Docker Compose in a Docker-enabled
environment.

See [the project audit](./PROJECT_POLISH_AUDIT.md) and
[the refreshed QA report](./docs/TEST-REPORT.md) for supporting detail.
