# WindSight UK — Final QA Test Report

This report records the latest local checks for the final release-readiness
pass. It distinguishes automated local results, bounded source observations,
previous full-period evidence, and checks blocked by missing external access.
The detailed status and release recommendation are in
[`FINAL_RELEASE_READINESS.md`](../FINAL_RELEASE_READINESS.md).

## Executed local checks

| Check | Result | Evidence |
|---|---|---|
| Backend tests | **PASS** | `python -m pytest`: 39 passed after upgrading the audited test/runtime dependencies. |
| Python lint | **PASS** | `python -m ruff check app tests`: no findings. |
| Python compilation | **PASS** | `python -m compileall -q app tests`: completed without errors. |
| Frontend lint | **PASS** | `npm run lint`: ESLint completed successfully. |
| Frontend unit tests | **PASS** | `npm test`: 3 tests passed. |
| TypeScript | **PASS** | `npm run typecheck`: `tsc -b` completed successfully. |
| Frontend production build | **PASS** | `npm run build` completed. Entry bundle: 355.98 kB (115.02 kB gzip); chart bundle: 377.11 kB (108.33 kB gzip). No Vite chunk exceeded 500 kB. |
| Playwright | **PASS** | `npm run e2e`: all 3 tests passed, including six routes, fresh layouts at 1440/768/390 px, keyboard/focus, date selection, chart tooltip, explicit loading/empty/error states, and accessibility scans. |
| Frontend dependency audit | **PASS** | `npm audit --audit-level=high`: 0 vulnerabilities. |
| Python dependency audit | **PASS** | `pip-audit -r requirements.txt`: no known vulnerabilities in resolved third-party dependencies. The local `windsight-uk-api` project is not published to PyPI and is skipped by the PyPI audit. |
| Compose and Actions YAML | **PASS, static only** | Both files parse; required Compose services and CI jobs are present. The frontend Docker build context was corrected to repository root and its referenced source paths were checked. |

The Playwright route-layout checks reload each route at each viewport. They do
not establish behavior during an in-place orientation/viewport resize.
Accessibility checks use Axe WCAG 2.1 A/AA rules; no automated violations
blocked the run. Assistive-technology testing was not performed.

## Data correctness and source evidence

The official Elexon [WINDFOR stream documentation](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream)
describes a wind-generation forecast endpoint and lists publication-time
filters. Its documented response example includes `dataset`, `publishTime`,
`startTime`, and `generation`; it does not state target cadence, units,
averaging semantics, a maximum response size, or a pagination contract. The
documented parameters do not include page/offset controls.

The official Elexon [FUELHH stream documentation](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream)
defines half-hourly generation outturn by fuel type and describes its
generation values as average MW over 30-minute intervals. Its example response
uses `dataset: "FUELINST"` despite being on the FUELHH page; the bounded live
FUELHH response previously observed for this project used `dataset: "FUELHH"`.
Treat that example-field discrepancy as a documentation inconsistency, not as
evidence that the datasets are interchangeable.

The recorded bounded WINDFOR publication-day response was HTTP 200 with 584
records, 8 publication timestamps, and 73 distinct hourly target timestamps.
It had no `Link` or `Content-Range` headers. This is evidence for that one
bounded response only; it cannot prove completeness or rule out a limit for
other request windows. No interpolation, half-hour value synthesis, or
coverage adjustment was introduced.

The previously recorded January 2026 full-period QA run reported 1,488
expected half-hour intervals, 1,488 WIND actual observations, 744 selected
forecasts, and 744 exact-time matches (50% forecast coverage). This is
consistent with hourly forecast targets on a half-hour expected grid, but the
source documentation does not establish that cadence as universal or prove
that retrieval was complete. A repeat raw-source query during the final pass
timed out; the full-period numbers above are identified as earlier QA evidence,
not a newly recomputed result.

WINDFOR generation and FUELHH actuals must remain **indicative** comparisons:
FUELHH documents half-hour averages, while WINDFOR documentation does not
establish comparable unit/aggregation semantics. Exact UTC target-time
matching and historical point-in-time selection remain unchanged.

## Storage, Docker, CI, and deployment

- The configured default archive file was absent during this review; therefore
  there is no real archive size or record count to report.
- The earlier synthetic 15,000-record benchmark measured a 2,184,080-byte
  JSON file, 1.347 seconds to write, 0.182 seconds to read, and 8.6 MiB peak
  traced memory. It is not a measurement of a production archive. At the
  observed sample cadence and size, growth is roughly 34 MB/year if records
  continue to arrive at about 584 forecasts and 48 actuals per day; actual
  growth depends on revisions, rejections, record shape, and run history.
- Archive byte size is exposed by `/api/data-quality`. No automatic retention
  was added, so monitor size and do not use isolated multi-replica stores.
- Docker Engine/CLI is unavailable. Dockerfiles, Compose ports, health checks,
  Nginx proxy paths, named volume, and build contexts were inspected and YAML
  parsed, but image builds, startup, logs, health, network connectivity, and
  restart persistence were **not executed**.
- The workflow statically includes Ruff, pytest, frontend lint/typecheck/unit
  tests, Playwright, production build, and both image builds. GitHub-hosted
  workflow/run lookup returned 404, so hosted CI is **unverified**.
- No deployment target or credentials were configured. Public deployment,
  HTTPS, hosted environment variables, and a real public historical query are
  **not verified**.

## Resolved issues during this pass

- Fixed a Playwright route matcher so the delayed comparison response matches
  query-string URLs; loading and empty states are now deterministically tested.
- Fixed the frontend Docker CI build context to match the Dockerfile's
  repository-root `COPY` paths.
- Dependency auditing identified vulnerable resolved versions of `filelock`
  and `pytest`. The project now requires patched versions and a compatible
  `pytest-asyncio` release. The dependency audit and all 39 backend tests pass
  with the updated versions.

## Earlier test setup failures

The first loading-state test run did not intercept the request because the
route pattern did not match a URL with a query string. The regular-expression
route now matches it and the full browser suite passes. The first attempted
dependency upgrade was blocked by the existing `pytest-asyncio` constraint
that pinned pytest below 9; the plugin range was updated to a compatible
release, then installation, audit, and backend tests passed.
