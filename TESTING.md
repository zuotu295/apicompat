# Testing

## Layers

1. **Stand-in suite — `tests/` (96 passed).** Loads
   `contracts/api_compat.py` itself behind a small GenLayer
   stand-in (`tests/conftest.py`), so it exercises the deployable
   file, not a copy of its logic. Covers the deterministic diff,
   the semantic filter, validator agreement and disagreement,
   malformed LLM output, prompt-injection resistance of the
   deterministic layer, prompt-boundary sanitisation, requestBody
   and response references, per-response media warnings,
   parsed-field association, input validation, and the full
   state machine. Coverage includes: operation security
   overriding global security including `security: []`,
   deterministic scope add/remove severities, supersede cycle
   and cross-API rejection, semantic evidence-field-kind
   association including auth-scope field rules, float enum
   shrink detection and int/float distinction, non-2xx
   description-only change detection, validator agreement
   with different evidence wording plus rejection when the
   validator finds no semantic finding, semantic equivalence
   by change-type groups (same change split across fields
   agrees; disjoint fields disagree; different severity
   disagrees), and enum transitions: unrestricted → finite
   (breaking), finite → unrestricted (info only), disjoint
   replacement (breaking + info), mixed add-and-remove
   (breaking + info), pure expansion (info only), parameter
   restriction (breaking), and identical/no-enum (no finding).
   Run: `.venv-repro/bin/python -m pytest tests -q`.
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
     A separate run finalised as MAJORITY_DISAGREE and stored
     nothing; see `evidence/EVIDENCE.md`.
   - `test_studionet_enum.py`: 1 passed in 88.00s. A disjoint
     enum replacement stored BLOCKED with both
     `response_field_enum_shrunk` (breaking) and
     `response_field_enum_expanded` (info). See
     `evidence/studionet_enum_2026-10-27.json`.

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

## Known limits

- Live `error_semantics_change` finding: not stored in the
  semantic run (see above); whether the leader produced none or
  validators disagreed is not visible from the stored record.
- Deployment through the Studio web UI: Studionet deployments
  so far went through gltest, not Studio UI.
