# Deployment — Studionet integration done 2026-10-27, Studio-UI deployment still open

Studionet integration deployments were done on 2026-10-27 via
gltest (see `evidence/EVIDENCE.md` and
`evidence/studionet_deployment_2026-10-27.json` for the full
addresses, hashes, and records). The canonical example instance is
`0xe7c40BeF9673A4ba0e00Bc63b5D9f542Cf27ae7b` (deploy
`0x708d5d2ed07c5a2dbf4b46bd5532bdfd849628d9d2cd8ff579ccb015140519bc`,
analyze
`0x88fc2e8d6da34968126e46388767542cd5be6e0f91bd97048575044f4dfd67b3`,
both FINALIZED, stored record BLOCKED with 3 breaking findings).
No personal wallet, private key, mnemonic, or credential was used;
callers were gltest auto-generated Studionet test accounts, and no
Appeal was invoked. Deployment through the Studio web UI itself
has not been done; the gltest route below is what was actually run.

## Target

Stable Studionet only:

- Studio: `https://studio.genlayer.com`
- RPC: `https://studio.genlayer.com/api`
- Chain ID: `61999`
- Currency: `GEN`
- Explorer: `https://explorer-studio.genlayer.com`

Verify the chain ID in the Studio account selector before deploying.
Do not reuse the stable `studionet` preset for Studio-dev
(chain ID `61997`).

## Pre-deployment checklist

1. **Lint the contract.** Run the official linter on the current
   file and record its actual output in the deployment note; do not
   reuse a previous run as evidence for a changed file.
   ```bash
   genvm-lint check contracts/api_compat.py
   ```
   Recorded result for the current contract (see the delivery
   report for the exact run): lint passed with 3 checks, validation
   passed, 6 methods (3 view, 3 write). The linter notes a newer
   `py-genlayer` runner is available; the pinned runner in the
   contract header is the one used in the official documentation
   examples for Stable Studionet, and the deployer should confirm
   it is still the correct runner for the Studio version in use at
   deployment time. The local script
   `scripts/check_compatibility.py` is only a preliminary AST check
   and does not replace this step.
2. **Direct-mode tests with the official harness — PARTLY DONE.**
   The reproducible environment (`.venv-repro`, genlayer-test
   0.29.2, genlayer-py 0.16.3, see `requirements.lock.txt`) runs
   `tests_direct/test_direct_smoke.py` with real GenVM in-process:
   2 passed, covering deploy, empty views, and the bundled
   example with a mocked LLM (BLOCKED, 3 breaking). This is not
   a reproduction of the full 74-test stand-in suite under the
   real harness, and it does not cover validator-agreement /
   validator-disagreement cases with `run_validator()`; those
   remain to be added. The `gltest.config.yaml` in this project
   was fixed in this round: it previously used keys rejected by
   genlayer-test 0.29.2, which made pytest collection fail once
   the real plugin was installed. The config now uses valid
   `url` / `id` keys, defaults to localnet, and contains no
   account or key.
3. **Integration test on Studionet — DONE 2026-10-27 via gltest.**
   `.venv-repro/bin/gltest --network studionet tests_integration -v -s`
   deployed three ApiCompat instances and ran the bundled example
   (BLOCKED, 3 breaking) and identical specs (COMPATIBLE,
   deterministic 0) through live Studionet validators to
   FINALIZED; see `evidence/EVIDENCE.md`. A transaction was
   treated as successful only when `wait_for_transaction_receipt`
   reached FINALIZED, `tx_execution_succeeded` passed, and the
   stored record read back from the chain matched expectations;
   the receipt `result` field alone was not used as proof, because
   the evidence printer did not capture `result_name`. One gap
   remains in the first identical-specs run: its analyze tx hash
   was not printed, so it is marked not captured in the evidence
   file and was not reconstructed; a rerun with the analyze
   receipt captured supplies the complete pair for that case.
4. **Real-model semantic checks.** Run several representative pairs
   (pagination change, auth-scope tightening, error-code change,
   rename with changed meaning) against the live validator set and
   confirm that semantic findings appear, that paraphrased evidence
   is still dropped, and that a spec containing injected
   instructions does not change the deterministic outcome.
5. **Fee check.** If the deployment charges fees, generate a fee
   profile from representative branches and use the SDK estimate
   (distribution + fee value) unchanged; do not hand-build fee
   arithmetic. Studio deployments may be gasless — detect that from
   the estimate result, not from the network name.
6. **Finalisation and appeal window.** Wait for finalisation before
   presenting a case as settled, and note that an appeal can still
   overturn a decision inside its window.

## Pre-submission deduplication (required, not done here)

This candidate was developed without connecting to GitHub or any
other repository. Before submitting this candidate anywhere, run a
full search over the relevant GenLayer builder repositories and
submission lists for:

- OpenAPI / API compatibility, interface breaking-change, and
  schema-diff contracts;
- any project with the same decision-set equivalence pattern applied
  to API specifications;
- the named projects from the brief (BallotSeal, CoreRelay,
  RecallScope, PatchDebt, GrantWeave, StepSpan, TermFence,
  ErrataScope) and any contemporaneous projects, to confirm the domain and
  mechanism differences stated in `README.md` still hold.

Record the search date, sources, and queries in a review note; do not
claim deduplication until that note exists.

## Studio deployment sketch (for the future deployer)

1. Open `https://studio.genlayer.com`, confirm chain ID `61999`.
2. Create a new contract, paste the full contents of
   `contracts/api_compat.py` (including the first-line dependency
   comment), and deploy with no constructor arguments.
3. Call `analyze_case` with the bundled example specs from
   `examples/old_spec.json` and `examples/new_spec.json`.
   Expected result with a well-behaved validator set and no semantic
   findings: `BLOCKED`, 3 breaking, 1 info (see `README.md`).
   A live validator set may add legitimate semantic findings, so
   the live breaking/info counts may be higher — that is expected
   and must be recorded as the live result, not edited to match the
   local mock result.
4. Call `get_case("example-users")` and confirm the stored record
   matches the returned record.
5. Record the contract address and deployment transaction in a
   deployment note (a new file, not by editing the contract).

## What is intentionally out of scope

- No frontend. A reviewer can drive the contract from Studio, the
  CLI, or `genlayer-js` using `examples/call_examples.py`.
- No token, payment, or staking logic. This is an adjudication
  primitive, not a marketplace.
- No private key, seed phrase, or API key is stored, requested, or
  needed anywhere in this repository.
