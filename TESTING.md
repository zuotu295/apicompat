# Testing

## Layers

1. **Stand-in suite — `tests/` (89 passed).** Loads
   `contracts/api_compat.py` itself behind a small GenLayer
   stand-in (`tests/conftest.py`), so it exercises the deployable
   file, not a copy of its logic. Covers the deterministic diff,
   the semantic filter, validator agreement and disagreement,
   malformed LLM output, prompt-injection resistance of the
   deterministic layer, prompt-boundary sanitisation, requestBody
   and response references, per-response media warnings,
   parsed-field association, input validation, and the full
   state machine. The final-round additions cover: operation
   security overriding global security including `security: []`,
   deterministic scope add/remove severities, supersede cycle
   and cross-API rejection, semantic evidence-field-kind
   association including auth-scope field rules, float enum
   shrink detection and int/float distinction, non-2xx
   description-only change detection, and validator agreement
   with different evidence wording plus rejection when the
   validator finds no semantic finding, plus three tests for the
   revised semantic equivalence rule (same change split across
   fields agrees; disjoint fields disagree; different severity
   disagrees). The split-agreement test fails against the
   pre-equivalence contract; the other new tests fail against
   their respective pre-fix contracts. Run:
   `.venv-repro/bin/python -m pytest tests -q`.
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
   `evidence/EVIDENCE.md`,
   `evidence/studionet_deployment_2026-10-27.json`, and
   `evidence/studionet_semantic_2026-10-27.json`. Do not run
   this directory against another network without reviewing it
   first, and never use it for Appeal.
   - `test_studionet.py`: bundled example BLOCKED, identical
     specs COMPATIBLE (twice), all FINALIZED, semantic_count 0
     in all three runs.
   - `test_studionet_semantic.py`: 1 passed in 220.60s.
     Pagination and auth-scope cases each stored one live
     semantic breaking finding (deterministic 0, BLOCKED);
     the error-semantics case stored REVIEW via the
     deterministic non-2xx warning with semantic_count 0.
     An earlier same-day run finalised as MAJORITY_DISAGREE
     and stored nothing, which motivated the revised semantic
     equivalence rule (change-type groups with a shared field).

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

- Live `error_semantics_change` finding: not stored in the
  2026-10-27 semantic run (see above); whether the leader
  produced none or validators disagreed is not visible from
  the stored record.
- Deployment through the Studio web UI (Studionet deployments
  so far went through gltest, not Studio UI).
- Full repository deduplication before any submission
  (public-repo check only, see README.md).
