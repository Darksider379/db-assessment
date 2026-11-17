# Code review

Reviewed on 2026-11-17. Scope: application code, tests, project configuration,
CI workflow, documentation, and available Git history. Fixes are local and uncommitted.

## Findings and fixes

### High: concurrent requests could accept a stale trade version

**Location:** `app/service.py`, `save_trade()`.

The latest-version query and subsequent write were not serialized. A request
could read while another transaction was inserting a higher version, then save
its lower version after that transaction committed. This violated the version rule.

**Fix:** On SQLite, acquire the writer reservation with `BEGIN IMMEDIATE` before
reading the latest version when no database transaction is already active.
Competing submissions then validate against the committed writer's version.

**Regression test:** `tests/test_concurrency.py::test_version_check_waits_for_pending_writer`
holds an uncommitted version 2 while submitting version 1 from a separate session.
The original implementation accepted version 1; the fixed implementation rejects it.

**Remaining limitation:** The locking strategy covers SQLite. PostgreSQL and MySQL
need an equivalent concurrency strategy before use. The test covers independent
sessions against a file-backed SQLite database; it does not establish concurrency
safety for shared in-memory connections or caller-managed existing transactions.

### Medium: renewing an expired trade retained its expired flag

**Location:** `app/service.py`, same-version update in `save_trade()`.

Updating an expired record to a valid present or future maturity date changed its
trade fields but left `expired="Y"`. The response therefore still marked the renewed
trade as expired.

**Fix:** Reset `expired` to `N` on an accepted same-version update while preserving
the original `created_date`.

**Regression test:**
`tests/test_version_rule.py::test_renewing_expired_trade_clears_expiry`.
The original implementation fails this test; the fixed implementation passes.

### Medium: CI vulnerability policy did not match its implementation

**Location:** `.github/workflows/ci.yml`, vulnerability-scan job.

The workflow claimed to fail only on high or critical findings, but `pip-audit`
already returns a failure for known vulnerabilities. In addition, the subsequent
filter assumed a severity field that is not reliably available in its JSON output.
The severity filter could not enforce the advertised policy.

**Fix:** Remove the misleading filter and explicitly fail on any known vulnerability
using `pip-audit`'s exit status. Update the workflow label and README accordingly.

**Validation limit:** The workflow was inspected locally; GitHub Actions and a live
vulnerability audit were not run during this review.

## Claude attribution

The local `.claude/settings.json` enables an Anthropic plugin, which establishes
that Claude tooling was configured. No explicit attribution identifying specific
Claude-generated application code was found in the inspected files or available
commit messages. Code style alone is insufficient to determine authorship.
The fixes above address demonstrated defects regardless of who wrote the code.

## Validation

- Baseline: 14 tests passed.
- After fixes: 16 tests passed, with 90.58% application coverage.
- `.venv/bin/ruff check .` passed.
- `git diff --check` passed.
- Both new regression tests were run against the original service implementation
  and failed on the expected behavior, then the fixed implementation was restored.
- The test run emitted an existing Starlette warning about its HTTPX integration.

## Repository note

The local README was updated, but the repository's current `.gitignore` excludes
`README.md`, so those documentation changes do not appear in the ordinary Git diff.
This review file records the relevant concurrency limitation and revised audit policy.
