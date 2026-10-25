# WindSight UK — Final Handover

WindSight UK is a React/TypeScript and FastAPI portfolio project for
point-in-time day-ahead wind forecast analysis using Elexon BMRS data. The
historical January 2026 metrics are indicative because the available
documentation does not prove that WINDFOR forecast values and FUELHH actual
values have equivalent measurement semantics. Missing half-hour matches are
not interpolated.

## Current verification

- Backend: 39 tests passed; Ruff and Python compilation passed.
- Frontend: lint, TypeScript, 3 unit tests, 3 Playwright tests, and production
  build passed. Browser tests cover all six routes at 1440, 768, and 390 px and
  automated Axe WCAG 2.1 A/AA checks.
- Dependency audits: npm reported 0 vulnerabilities; pip-audit reported no
  known vulnerabilities in resolved third-party dependencies.
- Docker: configuration reviewed and YAML parsed, but Docker Engine is not
  available for builds or runtime checks.
- GitHub Actions: workflow structure checked locally; hosted status is
  unavailable (GitHub API returned 404).
- Public deployment: not configured or performed.

## Operating constraints

- The JSON ingestion archive has no automatic retention. Size is exposed via
  `/api/data-quality`; the measured benchmark was synthetic. Use a single
  ingestion-enabled replica, or a genuinely shared lock-capable store.
- Manual ingestion requires a configured `WINDSIGHT_INGESTION_ADMIN_TOKEN`.
  Protect administrative access with HTTPS and secret management before any
  public deployment.
- No Elexon API credential is required for the current read-only data sources.
- Docker Compose binds the local frontend to `127.0.0.1:8080`, keeps the
  backend port internal, and persists the archive in the `ingestion-data`
  named volume. Runtime persistence has not been exercised here.

## Run instructions

Use the verified PowerShell setup and test commands in [`README.md`](./README.md).
For full evidence, limitations, status classifications, and the release
recommendation, see [`FINAL_RELEASE_READINESS.md`](./FINAL_RELEASE_READINESS.md).
