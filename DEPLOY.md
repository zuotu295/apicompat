# Deployment

## Target

Stable Studionet only:

- Studio: `https://studio.genlayer.com`
- RPC: `https://studio.genlayer.com/api`
- Chain ID: `61999`
- Currency: `GEN`
- Explorer: `https://explorer-studio.genlayer.com`

Verify the chain ID in the Studio account selector before deploying.
Do not reuse the stable `studionet` preset for Studio-dev
(chain ID `61997`); that is a different network.

Deployments recorded in `evidence/EVIDENCE.md` used gltest with
auto-generated Studionet test accounts. No personal wallet, private
key, mnemonic, or credential is used or stored anywhere in this
repository, and no Appeal was invoked in any recorded run.
Deployment through the Studio web UI has not been performed.

## Pre-deployment checklist

1. **Lint the contract.** Run the official linter on the current
   file. A linter result belongs to the exact file it was run on;
   re-run it after any contract change.
   ```bash
   genvm-lint check contracts/api_compat.py
   ```
   Recorded result for the current contract: lint passed with
   3 checks, validation passed, 6 methods (3 view, 3 write).
   The linter notes a newer `py-genlayer` runner is available;
   the pinned runner in the contract header is the one used in
   the official documentation examples for Stable Studionet, and
   the deployer should confirm it is still the correct runner
   for the Studio version in use at deployment time. The local
   script `scripts/check_compatibility.py` is only a preliminary
   AST check and does not replace this step.
2. **Direct-mode tests.** With the reproducible environment
   (`requirements.lock.txt`: genlayer-test 0.29.2, genlayer-py
   0.16.3, genvm-linter 0.11.0, pytest 9.1.1, Python 3.12.3),
   run `tests_direct/test_direct_smoke.py` with real GenVM
   in-process: 2 passed, covering deploy, empty views, and the
   bundled example with a mocked LLM (BLOCKED, 3 breaking).
   This does not reproduce the full stand-in suite under the
   real harness.
3. **Integration test on Studionet.**
   ```bash
   .venv-repro/bin/gltest --network studionet tests_integration -v -s
   ```
   Each test deploys its own contract instance and calls it
   through the live validator set; no mocked LLM is used. A
   transaction counts as successful only when its receipt
   reached FINALIZED, `tx_execution_succeeded` passed, and the
   stored record read back from the chain matched expectations;
   a FINALIZED receipt alone is not treated as proof of
   execution success. One recorded gap: the first identical-specs
   run did not print its analyze transaction hash, so that hash
   is recorded as not captured in the evidence file and was not
   reconstructed; a rerun with the analyze receipt captured
   supplies the complete pair for that case.
4. **Semantic checks.** The recorded semantic run stored one
   live semantic breaking finding each for pagination and
   auth-scope tightening; the error case stored REVIEW via the
   deterministic non-2xx warning with no agreed semantic
   finding. Paraphrased-evidence dropping and injection
   resistance of the deterministic layer are covered by the
   stand-in suite, not by a live run. A live run could still
   test rename-with-changed-meaning and a live injection pair.
5. **Fee check.** If the deployment charges fees, generate a fee
   profile from representative branches and use the SDK estimate
   (distribution + fee value) unchanged; do not hand-build fee
   arithmetic. Studio deployments may be gasless — detect that
   from the estimate result, not from the network name.
6. **Finalisation and appeal window.** Wait for finalisation
   before presenting a case as settled, and note that an appeal
   can still overturn a decision inside its window.

## Deploying through Studio

1. Open `https://studio.genlayer.com`, confirm chain ID `61999`.
2. Create a new contract, paste the full contents of
   `contracts/api_compat.py` (including the first-line dependency
   comment), and deploy with no constructor arguments.
3. Call `analyze_case` with the bundled example specs from
   `examples/old_spec.json` and `examples/new_spec.json`.
   Expected result with a validator set that adds no semantic
   findings: `BLOCKED`, 3 breaking, 1 info (see `README.md`).
   A live validator set may add legitimate semantic findings, so
   the live breaking/info counts may be higher — that is
   expected and must be recorded as the live result, not edited
   to match the local mock result.
4. Call `get_case("example-users")` and confirm the stored record
   matches the returned record.
5. Record the contract address and deployment transaction in a
   deployment note (a new file, not by editing the contract).

## What is intentionally out of scope

- No frontend. The contract can be driven from Studio, the
  CLI, or `genlayer-js` using `examples/call_examples.py`.
- No token, payment, or staking logic. This is an adjudication
  primitive, not a marketplace.
- No private key, seed phrase, or API key is stored, requested, or
  needed anywhere in this repository.
