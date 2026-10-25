# QA Test Report

Last verified locally: **25 October 2026**.

These checks cover the repository's current source tree. Backend tests use
mocked Elexon responses; the Playwright suite also mocks API responses. They
verify application behavior without claiming that live source data is complete.

## Results

| Check | Result |
|---|---|
| Backend lint (`python -m ruff check app tests`) | **PASS** |
| Backend tests (`python -m pytest -q`) | **PASS** — 39 tests |
| Frontend lint (`npm run lint`) | **PASS** |
| TypeScript (`npm run typecheck`) | **PASS** |
| Frontend unit tests (`npm test`) | **PASS** — 3 tests |
| Playwright browser tests (`npm run e2e`) | **PASS** — 3 tests |
| Production build (`npm run build`) | **PASS** — Vite 8.3.5 |

The production build emitted a 355.98 kB main JavaScript bundle and a
377.11 kB chart bundle (uncompressed). The browser tests cover the six
application routes, viewport layouts, navigation, and explicit loading,
empty-data, and error states.

## Verification limits

- Docker images and Compose startup were not tested because Docker was
  unavailable in the local environment.
- GitHub-hosted Actions and public deployment were not verified.
- Automated frontend tests use mocked APIs. The screenshot in the
  [README](../README.md) is a live-data overview, but it does not verify
  completeness of Elexon responses.
- No screen-reader or other assistive-technology testing was performed.

## Data limitations

- Elexon documentation does not establish equivalent units or aggregation
  semantics between WINDFOR forecasts and FUELHH actuals; comparisons are
  indicative.
- Forecast and actual targets can have different cadences. WindSight matches
  exact timestamps and does not interpolate or fill missing intervals.
- Forecast requests use a configurable publication lookback. The inspected
  source documentation does not establish a pagination or response-completeness
  guarantee.
- The analysis date range is limited to January 2026. The optional ingestion
  archive is a single-instance JSON store without automatic retention.

See the README's [data-source details](../README.md#data-sources-and-scope) and
[known limitations](../README.md#known-limitations) for context.
