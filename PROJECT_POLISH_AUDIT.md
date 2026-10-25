# WindSight UK — Project Polish Audit

## Scope and evidence

This audit began with inspection of the current frontend, backend, tests,
container configuration, environment templates, README, and existing
technical review and QA report. Follow-up implementation and verification are
recorded below; repository evidence, fresh checks, and older QA evidence are
kept distinct.

The application is an existing React/TypeScript/Vite frontend and FastAPI
backend. It must remain an indicative, point-in-time wind forecast analysis
tool until Elexon confirms that WINDFOR and FUELHH generation semantics are
equivalent.

## Existing functionality

- **Dashboard and navigation:** overview, forecast explorer, accuracy analysis,
  historical analysis, backtesting lab, and methodology/data-quality pages.
- **Forecast selection:** timestamp normalization to UTC, Europe/London
  cutoffs, latest eligible forecast selection, duplicate conflict indication,
  exact-target actual matching, and explicit missing states.
- **Charts and tables:** forecast/actual comparison, error and historical
  accuracy charts, interval tables, and a forecast publication revision
  timeline.
- **Backtesting:** two-cutoff historical comparison on common matched
  intervals, persistence baseline, and explicitly hypothetical residual
  scenarios.
- **Elexon access:** asynchronous HTTPX client for FUELHH and WINDFOR, bounded
  concurrency, request cache, timeout handling, retry/backoff for retryable
  errors, and request counters.
- **Automated ingestion:** optional in-process scheduler, file-backed JSON
  store, forecast publication overlap/checkpoint, raw source retention,
  idempotent exact-record merge, rejected-record capture, and token-protected
  manual synchronization.
- **Operational data:** data-quality and API performance endpoints, including
  process-local response-time statistics.
- **Tests:** pytest backend suite, Vitest unit tests, and a Playwright browser
  test; TypeScript checking, ESLint, and Vite production build.
- **Deployment:** Dockerfiles, Docker Compose, Nginx reverse proxy, backend
  health check, and CI image-build jobs are present. Docker Engine is not
  available in this environment.

## Confirmed working behavior

- Existing backend unit tests cover cutoff boundaries, post-cutoff exclusion,
  conflict handling, UTC/London conversion, DST day lengths, January 31 to
  February 1 delivery, metrics, and mocked Elexon errors/retries/cache.
- The latest local verification passes all 38 backend tests, Ruff, three
  frontend unit tests, one Playwright workflow test, ESLint, TypeScript
  checking, and the production build.
- The latest repository QA report records a live January 2026 result of 1,488
  expected intervals, 1,488 actual records, 744 selected forecasts, and 744
  matched intervals. This is exactly 50% forecast availability and is
  consistent with the report's observed hourly WINDFOR target timestamps
  versus half-hourly FUELHH intervals. A fresh bounded UTC publication-day
  request returned HTTP 200 with 584 records, 8 publication timestamps, and
  73 hourly target timestamps. It had no `Link` or `Content-Range` header;
  this does not prove the endpoint's general pagination or truncation contract.
- The existing QA report's full-period analytics and responsive checks remain
  historical evidence. Current browser verification covers one mocked
  backtesting workflow at 390 px with no horizontal page overflow; broader
  responsive behavior was not measured.
- The earlier technical review records January 31 next-day delivery and DST
  interval generation as tested behavior.

## Findings

### Critical

- **None confirmed in the inspected source.** This is not a certification that
  the application is production-ready; data semantics and deployment still
  have important limitations below.

### High

1. **Resolved: persistence is not the analytics source of truth.** Scheduled/manual
   ingestion writes records to the JSON store, but the existing overview,
   comparison, accuracy, revision, and backtesting request paths still fetch
   directly from Elexon. The API now declares `analytics_data_source` and the
   diagnostics UI/README explicitly state that persisted ingestion history is
   independent. No claim is made that the charts are persisted snapshots.

2. **The JSON source store grows without a retention or indexing policy.**
   Each merge reads the entire file, builds full-record identity sets, and
   rewrites the whole document. `/api/data-quality` also reads the full store
   to return counts. Cost and memory usage grow with retained history; this is
   appropriate only for small, single-process portfolio workloads and needs a
   measured bound or a durable indexed store before expanding history or
   replicas.

3. **The approximately 50% forecast coverage is consistent with, but not
   conclusively explained by, source cadence.**
   Recorded live evidence is consistent with hourly forecast targets matched
   exactly against a half-hour expected grid. No interpolation should be
   introduced. The checked client chunks requests by UTC day but contains no
   pagination traversal. The inspected evidence does not establish whether
   the WINDFOR endpoint paginates or truncates responses, so the source
   frequency explanation is not a verified exclusive cause. A bounded live
   request returned 584 records without pagination headers, but authoritative
   endpoint completeness still needs confirmation.

4. **Deployment and multi-worker behavior remain unverified.** Docker is
   configured but has not been built/run in the recorded environment. The
   ingestion lock and API performance counters are process-local, and the JSON
   store is single-process. Running multiple workers/replicas can duplicate
   scheduled requests and invalidate assumptions about locking or metrics.

### Medium

1. **Implemented, not yet exercised by GitHub-hosted CI.** GitHub Actions now
   runs Ruff/pytest, frontend lint/typecheck/unit/browser/build checks, and
   backend/frontend Docker image builds. The workflow parses locally, but no
   hosted run can be claimed from this environment.
2. **Forecast/actual comparability is limited.** Existing documentation says
   FUELHH represents half-hour averages while WINDFOR target values appear
   hourly and equivalent semantics are unconfirmed. Current exact timestamp
   metrics are explicitly indicative, not a validated like-for-like accuracy
   claim.
3. **Ingestion diagnostics can conflate a successfully fetched empty dataset
   with a healthy/current source.** Run success, source freshness, and data
   availability must remain separate concepts; the UI should report the
   returned source timestamps and missing actuals rather than interpret an
   empty response as proof of freshness.
4. **Automated actual interval checks are a partial validation.** Missing
   counts are generated for completed local delivery dates, while forecast
   off-grid checks use a half-hour rule even though WINDFOR may legitimately
   publish hourly targets. This is a warning, not proof that a forecast row is
   invalid. Expected forecast resolution must not be presented as established
   until documented by the source.
5. **Browser coverage is still narrow.** A Playwright test covers the
   backtesting route, surfaced API errors, duplicate cutoffs, and 390 px
   horizontal overflow; it is not a full-route, accessibility, or tablet test.
6. **Administrative sync is bearer-token protected but transport-dependent.**
   There is no TLS termination configuration in the application itself. The
   manual endpoint should only be exposed behind HTTPS and a deployment
   boundary that protects the token; CORS alone is not authorization.
7. **Bundle improved through route splitting.** Lazy-loaded route chunks reduce
   the entry chunk from 771.54 kB to 355.87 kB minified. The largest current
   chunk is the chart module at 376.43 kB; no chunk exceeds Vite's 500 kB
   warning threshold.
8. **Analysis request limits are modest.** The current API explicitly limits
   decision dates to January 2026, but forecast-revision requests retrieve the
   full configured publication lookback for one target. Keep this bound and
   avoid claiming arbitrary historical-range support.

### Low

1. **Accessibility verification is incomplete.** Navigation and form controls
   have labels/semantics, but chart screen-reader descriptions, keyboard
   interactions, focus visibility, and contrast have not been assessed with an
   automated accessibility tool or assistive technology.
2. **Documentation still has some repeated ingestion detail.** Mermaid
   architecture and a final polish report are now present. The README already
   had an AI-assistance disclosure; no real screenshots have been added.
3. **The QA report is stale relative to the current code.** It documents an
   earlier backend test count and predates the backtesting and automated
   ingestion additions.
4. **No tracked deployment target or verified public demo is configured.**
   Do not add a public URL or claim deployment without an approved target and
   live verification.

## Data correctness review

- **FUELHH retrieval:** code requests daily settlement dates with
  `fuelType=WIND` and filters any returned rows by fuel and date. Existing
  client tests use mocked responses. The last QA report provides historical
  live evidence of 1,488 records; no fresh FUELHH full-period request was run.
- **WINDFOR retrieval:** code splits publication windows into UTC-day chunks
  and filters records back to those windows. A bounded live request returned
  584 records in one JSON response, with no pagination headers. No pagination
  traversal is implemented, and that request alone does not establish the
  endpoint's full pagination/truncation contract.
- **Revision preservation:** selection groups revisions by UTC target;
  revision endpoint preserves normalized matching rows and deterministically
  orders equal-publication values. The ingestion store preserves distinct raw
  records, including conflicts, and deduplicates identical serialized source
  records.
- **Historical cutoff:** the point-in-time selector filters on
  `publishTime <= cutoff` and existing tests include post-cutoff exclusion.
- **Matching/missing values:** matching is exact UTC target-time equality.
  Missing values remain null; no interpolation or zero substitution is used.
- **Timezone and boundaries:** normalization requires offsets, selection uses
  `Europe/London`, expected delivery intervals account for DST, and tests cover
  January 31 to February 1.
- **Metrics:** MAE, RMSE, bias, and WAPE use matched observations; coverage is
  computed separately for forecast and actual presence. WAPE is null when the
  absolute matched actual denominator is zero.
- **Coverage conclusion:** exact 50% is consistent with hourly forecasts on a
  half-hour grid in the historical QA evidence. A new bounded request
  independently observed 73 hourly target timestamps, but cannot rule out
  endpoint pagination/truncation for larger requests or establish compatible
  source measurement semantics.

## Prioritized improvement checklist

- [x] **High — Resolve dashboard/persisted-store separation:** analytics remain
  live Elexon queries, explicitly declared in the API and UI; the store is an
  independent ingestion archive.
- [ ] **High — Establish WINDFOR response completeness:** a bounded live
  request was measured, but the endpoint pagination/record-limit contract
  still needs authoritative confirmation.
- [ ] **High — Bound persisted ingestion growth:** add a retention/compaction
  policy or choose an indexed database only after measuring actual file size
  and query cost.
- [ ] **High — Verify Docker startup and persistent-volume behavior** in an
  environment with Docker Engine.
- [x] **Medium — Add GitHub Actions** for backend tests, frontend checks/build,
  and backend/frontend Docker image builds (hosted execution remains pending).
- [x] **Medium — Add focused frontend tests** for timezone/date helpers and
  route/API-error/cutoff behavior.
- [x] **Medium — Add browser E2E coverage** using Playwright; one workflow is
  covered, so broader route coverage remains future work.
- [x] **Medium — Re-run bounded live source verification** and keep cadence,
  source semantics, and response completeness as distinct claims.
- [x] **Medium — Profile and apply route-level lazy loading:** entry chunk
  decreased from 771.54 kB to 355.87 kB; chart chunk is 376.43 kB.
- [x] **Low — Refresh QA report and add Mermaid architecture.** AI disclosure
  already existed; accessibility and tablet-layout verification remain open.

## Audit disposition

The project has a coherent modular MVP architecture and meaningful automated
tests for temporal correctness, plus CI configuration and improved route
loading. It should be presented as a **well-tested portfolio analytics
application with indicative metrics**, not as a fully production-ready or
source-equivalence-certified energy platform. Remaining high-priority work is
bounded-store design, authoritative response-completeness confirmation, and
Docker/hosted-CI execution. No unrelated feature expansion is recommended.
