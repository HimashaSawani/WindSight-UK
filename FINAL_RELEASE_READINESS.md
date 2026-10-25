# WindSight UK — Final Release Readiness

## 1. Executive summary

WindSight UK is ready for a **portfolio GitHub publication as a well-tested,
indicative wind-generation analytics project**. Local automated checks pass,
the README and QA record are current, and no unresolved critical implementation
defect was identified.

This is not a certification of an operational energy product. WINDFOR response
completeness and forecast/actual measurement equivalence are not established
by the available Elexon documentation. Docker runtime, GitHub-hosted CI, and
public deployment could not be verified in this environment and are reported
as blocked rather than passed.

## 2. Issues resolved

- Hardened the Methodology page against absent optional ingestion-run fields in
  diagnostics responses.
- Exposed the persisted archive's current byte size through `/api/data-quality`.
- Added a file-backed scheduler lease to prevent multiple ingestion-enabled
  processes sharing the same lock-capable store from starting concurrent
  scheduled ingestion.
- Kept archive history and forecast revisions; no automatic deletion or
  interpolation was added.
- Restricted Compose backend access to the internal network and bound the
  local frontend port to loopback.
- Added accessible chart summaries and visible navigation focus styling, and
  corrected a panel sizing issue that caused responsive chart overflow.
- Corrected the CI frontend Docker build context to repository root, matching
  the Dockerfile's `COPY frontend/...` and `COPY deploy/...` paths.
- Corrected a Playwright route matcher that did not intercept comparison URLs
  containing query strings; loading and empty states now test deterministically.
- Updated vulnerable Python dependency constraints after `pip-audit` identified
  affected `filelock` and `pytest` versions. The compatible
  `pytest-asyncio` constraint was updated as part of that change.

## 3. Files modified

Final-pass edits:

- `.github/workflows/ci.yml`
- `backend/pyproject.toml`
- `frontend/e2e/backtesting.spec.ts`
- `frontend/src/components/DashboardPrimitives.tsx`
- `README.md`
- `PROJECT_POLISH_AUDIT.md`
- `FINAL_POLISH_REPORT.md`
- `FINAL_HANDOVER.md`
- `docs/TEST-REPORT.md`
- `FINAL_RELEASE_READINESS.md`

The completion work also includes the related implementation and test changes
in `backend/app/services/ingestion_store.py`, `backend/app/main.py`,
`backend/app/api/data.py`, `backend/tests/test_automated_ingestion.py`,
`docker-compose.yml`, `frontend/src/types/api.ts`,
`frontend/src/pages/SectionPage.tsx`,
`frontend/src/components/AnalyticsCharts.tsx`,
`frontend/src/components/AppLayout.tsx`, and the frontend package manifest and
lockfile.

## 4. Data correctness findings

### WINDFOR API shape and retrieval limits

The official [WINDFOR stream documentation](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream)
describes a wind-generation forecast endpoint. Its documented response example
contains `dataset`, `publishTime`, `startTime`, and `generation`. The
documented query parameters are `publishDateTimeFrom` and
`publishDateTimeTo`; no page, offset, or maximum-record parameter is
documented. The page does not state a maximum response size, a completeness
guarantee, or a general pagination/truncation contract.

A bounded live publication-day response recorded for this project returned
HTTP 200 with 584 records, 8 publication timestamps, and 73 distinct hourly
target timestamps. No `Link` or `Content-Range` headers appeared. The observed
584 rows equal 8 publication groups across 73 targets for that response, but
this is not proof of completeness for other windows. The client has no
pagination traversal, so broader-window completeness remains an external
source question.

The documentation example and observed response establish a `startTime`
target field; hourly target spacing was observed in live records, but the
documentation does not guarantee hourly cadence for all dates or responses.

### FUELHH definition and comparability

The official [FUELHH stream documentation](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream)
describes half-hourly generation outturn by fuel type and average MW over each
30-minute interval. The documentation's example response says
`dataset: "FUELINST"` despite appearing on the FUELHH page; the bounded live
FUELHH response observed for this project used `dataset: "FUELHH"`. This
inconsistency is treated as a documentation-example defect, not evidence of
source equivalence.

The available WINDFOR documentation does not establish the forecast's unit,
averaging/aggregation interval, or scope equivalence with FUELHH. The
application presents the generation values in MW-based metric fields, but
that application convention does not establish the source unit. The datasets
cannot be certified as like-for-like from this evidence. Accuracy and
benchmark metrics therefore remain **indicative**.

### Timestamp alignment, coverage, and missing records

Historical QA for January 2026 previously recorded:

- 1,488 expected half-hour delivery intervals
- 1,488 FUELHH WIND actual observations
- 744 selected WINDFOR forecast observations
- 744 exact-target forecast/actual matches
- 50% forecast coverage and 100% actual coverage

This is consistent with observed hourly forecast targets on a half-hour
expected grid. It does not prove that cadence alone explains the coverage or
that no API records were omitted. A repeated live source request during this
final pass timed out; the January totals above are explicitly earlier QA
evidence, not a fresh full-period execution.

Point-in-time selection remains based on `publishTime <= decision cutoff`,
with the latest eligible revision selected. Matching remains exact normalized
UTC target-time equality. Missing intervals remain missing: no interpolation,
half-hour forecast synthesis, zero substitution, or artificial coverage
increase was introduced.

## 5. WINDFOR coverage conclusion and evidence

**Status: LIMITATION.** The 50% result is compatible with the observed hourly
WINDFOR target cadence versus half-hour FUELHH delivery intervals, but the
official WINDFOR documentation does not guarantee hourly cadence and does not
specify response-size/completeness behavior. No pagination parameters or
pagination headers were observed for the documented endpoint and bounded
response. Retrieval completeness for broader windows and the exclusive cause
of the coverage level are not proven.

The project retains exact matching and labels affected metrics indicative.
No data fabrication is used to improve coverage.

## 6. Forecast/actual comparability status

**Status: LIMITATION.** FUELHH is documented as a 30-minute average-MW
outturn; WINDFOR's published schema and description do not establish equivalent
measurement or aggregation semantics. Do not describe these results as
validated like-for-like forecast accuracy until Elexon confirms comparability.

## 7. Storage capacity and coordination

- **Current archive:** no file was present at the configured default
  `WINDSIGHT_INGESTION_STORE_PATH`; current archive size and archived record
  count are therefore zero/not yet populated, not representative of a live
  deployment.
- **Synthetic benchmark:** 10,000 forecast plus 5,000 actual records produced
  a 2,184,080-byte JSON store (about 145.6 bytes/record), with 1.347 seconds
  measured write time, 0.182 seconds read time, and 8.6 MiB peak traced memory.
  These are synthetic results, not production archive measurements.
- **Growth estimate:** at the observed sample cadence of about 584 forecasts
  and 48 actuals per day and the benchmark's average bytes per record, a simple
  linear estimate is about 34 MB/year. Record shape, revisions, rejections,
  and run metadata can change actual growth.
- **Decision:** the file-backed JSON store is sufficient for a small,
  single-instance portfolio deployment; adding PostgreSQL or Redis is not
  justified by this evidence. It rewrites the retained document, has no
  automatic retention/indexing, and is not sized for unbounded history.
- **Monitoring/coordination:** `/api/data-quality` reports archive bytes.
  A file lock prevents concurrent scheduled ingestion only when processes
  share the same lock-capable store path/filesystem. Use one
  ingestion-enabled replica unless reliable shared locking is available.
  Isolated replica volumes do not coordinate. Do not delete historical
  revisions automatically.

## 8. Backend test results

**PASS:** `python -m pytest` — 39 passed with the patched dependency versions.
`python -m ruff check app tests` and `python -m compileall -q app tests` also
passed.

Backend tests cover point-in-time selection, normalization, Elexon client
behavior, metrics, API validation, automated-ingestion persistence/idempotency,
store sizing, and same-store scheduler lease exclusion/reacquisition.

## 9. Frontend test results

**PASS:**

- `npm run lint`
- `npm run typecheck`
- `npm test` — 3 tests passed
- `npm run build`

The production build produced a 355.98 kB entry chunk (115.02 kB gzip) and a
377.11 kB chart chunk (108.33 kB gzip). No chunk exceeded Vite's 500 kB
warning threshold.

## 10. Playwright and accessibility results

**PASS:** `npm run e2e` — all 3 browser tests passed. They cover:

- All six navigation routes, each loaded at 1440, 768, and 390 px; no
  horizontal document overflow was found on those fresh loads.
- Axe WCAG 2.1 A/AA scans at the desktop viewport, navigation semantics,
  visible keyboard focus, date selection, chart accessible summary and tooltip.
- Explicit loading, empty-data, API-error, and invalid-cutoff behavior.

Dynamic orientation/resize without reloading and assistive-technology testing
were not performed. Axe results are automated checks, not a full accessibility
certification.

## 11. Docker verification

**PASS — static configuration review:** backend and frontend Dockerfiles,
Compose services, health checks, Nginx `/api/` proxy, persistent named volume,
internal backend port, and loopback-only frontend binding were inspected.
Compose YAML parses, and CI build contexts were checked.

**BLOCKED — runtime verification:** Docker CLI/Engine is unavailable. Image
builds, container startup, health checks, frontend-to-backend connectivity,
container logs, and persistence through restart were not executed. Reproduce
when Docker is available:

```powershell
docker compose up --build
# Open http://localhost:8080 and verify http://localhost:8080/api/health
docker compose restart backend
# Verify retained record counts at http://localhost:8080/api/data-quality
docker compose down
```

Do not use `docker compose down -v` unless permanently deleting the named
archive volume is intended.

## 12. GitHub Actions verification

**PASS — static workflow review:** `.github/workflows/ci.yml` includes Ruff,
pytest, frontend ESLint, TypeScript, Vitest, Playwright, frontend production
build, and backend/frontend Docker image builds. YAML parses locally. The
frontend Docker build context was corrected from `./frontend` to `.` because
the Dockerfile uses repository-root-relative `COPY` paths.

**BLOCKED — hosted result:** GitHub Actions workflow/run lookup returned 404.
No hosted success or failure is claimed.

## 13. Security review

- **Dependency findings resolved:** the initial Python dependency audit found
  known vulnerabilities in the resolved `filelock` and `pytest` versions.
  Constraints were updated to require `filelock>=4.2.1,<5.0`,
  `pytest>=9.0.3,<10.0`, and `pytest-asyncio>=1.0,<2.0`. The installed
  versions were `filelock 4.2.4`, `pytest 9.1.1`, and
  `pytest-asyncio 1.4.0`; all backend tests pass after the upgrade.
- `pip-audit -r requirements.txt` reported no known vulnerabilities in
  resolved third-party dependencies. It skips the unpublished local project
  package because that package is not on PyPI.
- `npm audit --audit-level=high` reported 0 vulnerabilities.
- Environment files, local caches, data, and build artifacts are excluded by
  `.gitignore`; frontend environment files are excluded from the frontend
  Docker build context. Environment templates contain no configured
  administrative token. A dedicated repository secret-scanner was not run.
- Administrative sync requires `X-Admin-Token`; CORS is not authorization.
  The backend/Nginx configuration does not terminate TLS. Any public
  deployment must protect the admin token and endpoint with HTTPS and managed
  secrets. The Compose backend is not published directly to the host.
- Request timeouts, bounded retries, validated settings/API inputs, and
  explicit API error handling are present. API counters and response-time
  summaries are process-local and are not a multi-replica monitoring service.

**Overall security status: PASS with deployment limitations.** No unresolved
critical implementation issue was identified; public HTTPS and secret
management remain deployment prerequisites.

## 14. Accessibility review

**PASS for automated local checks:** Axe WCAG 2.1 A/AA, chart summaries,
navigation/form semantics, visible keyboard focus, and measured initial
layouts passed the stated Playwright checks. **LIMITATION:** no screen reader,
manual keyboard-only audit, or separate expert contrast review was performed.

## 15. README and release documentation

**PASS:** README includes project scope, verified features, architecture
diagram, data sources, point-in-time methodology, limitations, installation
and environment setup, Docker instructions, tests, deployment guidance, and
AI-assistance disclosure. Commands were checked against project scripts.
No real application screenshot was available to add; the existing image asset
is not a dashboard screenshot. The QA, polish, and handover documents now
point to this report for authoritative current status.

## 16. Deployment status and remaining limitations

**BLOCKED:** no deployment target, credentials, or authorization were
configured. No public deployment, HTTPS endpoint, environment configuration,
or public historical query was tested. No demo URL is claimed.

Remaining limitations:

1. Confirm WINDFOR response completeness/limits and measurement comparability
   with Elexon before treating the metrics as validated accuracy.
2. Populate and monitor the JSON archive before estimating its real workload;
   adopt retention or indexed storage only if measured needs justify it.
3. Verify Docker builds and runtime/persistence in a Docker-enabled environment.
4. Retrieve a successful hosted GitHub Actions run when repository access
   allows it.
5. Perform manual assistive-technology testing and verify in-place responsive
   resize behavior if broader accessibility assurance is required.

## 17. Final release recommendation

| Requirement | Status | Conclusion |
|---|---|---|
| No known critical implementation defects | **PASS** | No unresolved critical defect was identified; relevant fixes are regression-tested. |
| Existing core workflows and historical selection | **PASS** | Local backend/UI tests pass; point-in-time selection and exact matching remain unchanged. |
| Data limitations disclosed | **PASS** | Coverage, pagination uncertainty, and metric comparability are documented as indicative/limited. |
| Automated local tests and frontend build | **PASS** | Backend, frontend, browser, lint, type, build, and dependency checks passed. |
| Security-sensitive configuration | **PASS** | Audited vulnerable packages were upgraded; admin sync remains token-protected and deployment TLS requirements are explicit. |
| README accuracy and reproducibility | **PASS** | Verified setup/test commands and release limitations are documented. |
| Docker runtime and hosted CI | **BLOCKED** | Engines/hosted results were unavailable; static configuration is checked only. |
| Public deployment | **BLOCKED** | No approved target or authorization was provided. |
| External source semantics/completeness | **LIMITATION** | Official docs and bounded responses do not establish equivalence or universal completeness. |

**Recommendation: READY for portfolio GitHub publication with the stated
limitations.** This recommendation does not imply Docker runtime verification,
successful hosted CI, public deployment, certified data comparability, or
suitability as a trading platform. No unresolved **FAIL** status remains in
the local implementation checks.
