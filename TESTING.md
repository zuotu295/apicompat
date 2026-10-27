# Testing

## Layers

1. **Stand-in suite — `tests/` (74 passed).** Loads
   `contracts/api_compat.py` itself behind a small GenLayer
   stand-in (`tests/conftest.py`), so it exercises the deployable
   file, not a copy of its logic. Covers the deterministic diff,
   the semantic filter, validator agreement and disagreement,
   malformed LLM output, prompt-injection resistance of the
   deterministic layer, prompt-boundary sanitisation, requestBody
   and response references, per-response media warnings,
   parsed-field association, input validation, and the full
   state machine. Run: `.venv-repro/bin/python -m pytest tests -q`.
   A test count is a result, not a proof of correctness.
2. **Direct-mode smoke — `tests_direct/` (2 passed, real GenVM
   in-process, no network, no chain transaction).** Deploys the
   real contract in-process and runs the bundled example with a
   mocked LLM (empty findings), asserting BLOCKED with 3 breaking
   findings. One environment quirk: direct mode first tried to
   re-download the GenVM v0.3.0-rc7 artifact and got HTTP 404,
   even though the same artifact was already cached by
   genvm-linter; reusing that cached tarball locally let the
   tests run. A fresh machine may hit the same 404.
3. **Studionet integration — `tests_integration/` (done
   2026-10-27, live validators, FINALIZED).** Run only with:
   `.venv-repro/bin/gltest --network studionet tests_integration -v -s`
   Each test deploys its own contract instance on Stable
   Studionet (61999) and calls it through the live validator
   set; no mocked LLM is used. Results are in
   `evidence/EVIDENCE.md` and
   `evidence/studionet_deployment_2026-10-27.json`. Do not run
   this directory against another network without reviewing it
   first, and never use it for Appeal.

## Linter

`.venv-repro/bin/genvm-lint check contracts/api_compat.py`:
lint passed (3 checks), validation passed, 6 methods
(3 view, 3 write). The linter notes a newer `py-genlayer`
runner is available; the contract keeps the documented Stable
Studionet runner.

## Preliminary check (no network, no keys)

`python3 scripts/check_compatibility.py` checks the GenVM
dependency header, minimal imports, storage types, public-method
decorators and return types, containment of non-determinism,
and the pinned Studionet configuration. It does not claim a
linter result.

## Still open

- Real-model semantic behaviour: semantic_count was 0 in all
  three Studionet runs, so no live semantic finding was
  exercised there.
- Validator agreement/disagreement via `run_validator()` under
  the real harness.
- Deployment through the Studio web UI (Studionet deployments
  so far went through gltest, not Studio UI).
- Full repository deduplication before any submission.
