# WindSight UK — Project Polish Audit

## Scope and evidence

This audit is based on inspection of the current frontend, backend, tests,
container configuration, environment templates, README, and the existing
technical review and QA report. Findings distinguish repository evidence from
historical verification recorded in those reports. No live Elexon request,
browser session, or Docker build was run as part of this audit.

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
- **Tests:** pytest backend suite; TypeScript checking, ESLint, and Vite
  production build. There is no configured frontend unit-test runner.
- **Deployment:** Dockerfiles, Docker Compose, Nginx reverse proxy and backend
  health check are present. Docker Engine is not available in the inspected
  environment.

## Confirmed working behavior

- Existing backend unit tests cover cutoff boundaries, post-cutoff exclusion,
  conflict handling, UTC/London conversion, DST day lengths, January 31 to
  February 1 delivery, metrics, and mocked Elexon errors/retries/cache.
- The latest repository QA report records a live January 2026 result of 1,488
  expected intervals, 1,488 actual records, 744 selected forecasts, and 744
  matched intervals. This is exactly 50% forecast availability and is
  consistent with the report's observed hourly WINDFOR target timestamps
  versus half-hourly FUELHH intervals. It does not prove that no Elexon
  pagination or other retrieval limitation exists.
- The existing QA report records successful frontend build/type-check/lint,
  backend tests at that report's then-current count, browser route smoke tests,
  and no horizontal overflow at 390px. These are historical results, not a
  claim that those exact checks were rerun for this audit.
- The earlier technical review records January 31 next-day delivery and DST
  interval generation as tested behavior.

## Findings

### Critical

- **None confirmed in the inspected source.** This is not a certification that
  the application is production-ready; data semantics and deployment still
  have important limitations below.

### High

1. **Persistence is not the analytics source of truth.** Scheduled/manual
   ingestion writes records to the JSON store, but the existing overview,
   comparison, accuracy, revision, and backtesting request paths still fetch
   directly from Elexon. Users can therefore see dashboards based on live
   retrieval while the data-quality page reports an independent persisted
   ingestion history. This split should be made explicit or unified before
   describing the charts as reproducible snapshots.

2. **The JSON source store grows without a retention or indexing policy.**
   Each merge reads the entire file, builds full-record identity sets, and
   rewrites the whole document. `/api/data-quality` also reads the full store
   to return counts. Cost and memory usage grow with retained history; this is
   appropriate only for small, single-process portfolio workloads and needs a
   measured bound or a durable indexed store before expanding history or
   replicas.

3. **The approximately 50% forecast coverage is only partially explained.**
   Recorded live evidence is consistent with hourly forecast targets matched
   exactly against a half-hour expected grid. No interpolation should be
   introduced. The checked client chunks requests by UTC day but contains no
   pagination traversal. The inspected evidence does not establish whether
   the WINDFOR endpoint paginates or truncates responses, so the source
   frequency explanation is not a verified exclusive cause. Recheck the
   endpoint contract and returned counts before declaring the cause settled.

4. **Deployment and multi-worker behavior remain unverified.** Docker is
   configured but has not been built/run in the recorded environment. The
   ingestion lock and API performance counters are process-local, and the JSON
   store is single-process. Running multiple workers/replicas can duplicate
   scheduled requests and invalidate assumptions about locking or metrics.

### Medium

1. **No CI workflow or frontend automated tests are configured.** `package.json`
   includes build/typecheck/lint scripts but no Vitest or browser test script;
   the repository has no inspected GitHub Actions workflow.
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
5. **Error/loading states are implemented but not comprehensively tested in a
   browser.** The existing QA report records successful route checks but says
   live API-failure simulation and tablet-specific checks were not performed.
6. **Administrative sync is bearer-token protected but transport-dependent.**
   There is no TLS termination configuration in the application itself. The
   manual endpoint should only be exposed behind HTTPS and a deployment
   boundary that protects the token; CORS alone is not authorization.
7. **Large frontend bundle advisory.** Previous successful Vite builds report
   a minified main chunk above 500 kB. No profiling evidence currently justifies
   a larger refactor; lazy-loading routes is a measurable, low-risk candidate.
8. **Analysis request limits are modest.** The current API explicitly limits
   decision dates to January 2026, but forecast-revision requests retrieve the
   full configured publication lookback for one target. Keep this bound and
   avoid claiming arbitrary historical-range support.

### Low

1. **Accessibility verification is incomplete.** Navigation and form controls
   have labels/semantics, but chart screen-reader descriptions, keyboard
   interactions, focus visibility, and contrast have not been assessed with an
   automated accessibility tool or assistive technology.
2. **Documentation is split across duplicated sections.** Ingestion settings
   are described both in the pipeline narrative and the environment table.
   README architecture uses a text diagram, not Mermaid; no real screenshots,
   AI-assistance disclosure, or final polish report exist.
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
  live evidence of 1,488 records, but this audit did not issue a fresh request.
- **WINDFOR retrieval:** code splits publication windows into UTC-day chunks
  and filters records back to those windows. No pagination traversal is
  implemented. The endpoint's pagination contract was not independently
  verified in this audit.
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
  half-hour grid in the historical QA evidence. This audit cannot rule out
  endpoint pagination/truncation or confirm source contract details, so label
  the explanation as consistent with observations rather than proven.

## Prioritized improvement checklist

- [ ] **High — Resolve dashboard/persisted-store separation:** decide whether
  analytics should remain explicitly live Elexon queries or consume persisted
  records; do not silently mix them.
- [ ] **High — Establish and document WINDFOR response completeness:** confirm
  pagination/record limits from official endpoint behavior and test bounded
  full retrieval.
- [ ] **High — Bound persisted ingestion growth:** add a retention/compaction
  policy or choose an indexed database only after measuring actual file size
  and query cost.
- [ ] **High — Verify Docker startup and persistent-volume behavior** in an
  environment with Docker Engine.
- [ ] **Medium — Add GitHub Actions** for backend tests, frontend checks/build,
  and safe Docker build validation.
- [ ] **Medium — Add focused frontend tests** for route rendering, data loading
  and failures, and date/cutoff controls; introduce a test framework only as
  part of that requirement.
- [ ] **Medium — Add high-value browser E2E coverage** after a supported browser
  test tool is available.
- [ ] **Medium — Re-run live coverage verification** and keep source cadence,
  source semantics, and retrieval completeness as distinct hypotheses.
- [ ] **Medium — Profile and consider route-level lazy loading** to address the
  verified bundle warning; record before/after output sizes.
- [ ] **Low — Refresh QA report, add Mermaid architecture and AI-assistance
  disclosure, and verify accessibility and tablet layouts.**

## Audit disposition

The project has a coherent modular MVP architecture and meaningful backend
tests for temporal correctness. It should be presented as a **well-tested
portfolio analytics application with indicative metrics**, not as a fully
production-ready or source-equivalence-certified energy platform. The first
quality work should address data-source completeness evidence, the live-versus-
persisted analytics boundary, bounded storage, CI/frontend test automation,
and Docker verification. No unrelated feature expansion is recommended.
