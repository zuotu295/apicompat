# Evidence — Stable Studionet, 2026-10-27 (Beijing time)

Machine-readable evidence: `studionet_deployment_2026-10-27.json` in
this directory. This file is a human-readable summary of the same
runs; it adds no address, hash, or result beyond what the test
output printed.

## Network

- Stable Studionet, Chain ID 61999
- RPC: `https://studio.genlayer.com/api`
- Explorer: `https://explorer-studio.genlayer.com`
- Tooling: genlayer-test 0.29.2, genlayer-py 0.16.3,
  genvm-linter 0.11.0, Python 3.12.3 (see `requirements.lock.txt`)
- Test command: `.venv-repro/bin/gltest --network studionet tests_integration -v -s`
- Validators: the live Studionet validator set. No mocked LLM was
  used in these runs.

## Deployments and calls (all FINALIZED)

Each integration test deploys its own contract instance, so three
ApiCompat contracts were deployed in this round.

### 1. Bundled example — BLOCKED (canonical instance)

- Contract: `0xe7c40BeF9673A4ba0e00Bc63b5D9f542Cf27ae7b`
- Deploy tx: `0x708d5d2ed07c5a2dbf4b46bd5532bdfd849628d9d2cd8ff579ccb015140519bc`
- Analyze tx: `0x88fc2e8d6da34968126e46388767542cd5be6e0f91bd97048575044f4dfd67b3`
- Case: `studionet-example`, users-api 1.0.0 → 2.0.0
- Stored record: BLOCKED, breaking 3, deterministic 4, info 1,
  semantic 0, warnings 0
- Deterministic breaking kinds: `operation_removed`,
  `request_required_field_added`, `response_field_removed`
- Owner (gltest auto-generated test account, not a personal wallet):
  `0xB44746c14460b9ce7E814283336898de80d073B3`
- Duration: 283.87s, 1 passed

### 2. Identical specs — COMPATIBLE (first run)

- Contract: `0xB5699F56cB22778e5ccdde316c3a6e7335664cba`
- Deploy tx: `0xe76ba8532f7edc4b623435d62363e9c89ba8212b437adb6040e6c021f77509e2`
- Analyze tx: **not captured** — the first run of this test printed
  only the deploy receipt and the stored record. It is not
  reconstructed here.
- Stored record: COMPATIBLE, deterministic 0, semantic 0, breaking 0
- Owner: `0xCbA655650a46f9ba4dc89E08C7CDe1e45f92eb23`
- Duration: 93.04s, 1 passed

### 3. Identical specs — COMPATIBLE (rerun, complete receipts)

This rerun was made only to capture the analyze receipt that the
first run omitted.

- Contract: `0xb3b6199Cd484f480AD97795C6b9dC1F36814ba98`
- Deploy tx: `0x070d742fb10a3b9f9528f6d252575ae2f19a4c809d9b13edf076c5f5e6ec2657`
- Analyze tx: `0x34230b774159c115621de9065266155939a1416b4ce2ab0cb0fae268dc5a8e0d`
- Stored record: COMPATIBLE, deterministic 0, semantic 0, breaking 0
- Owner: `0xfC94700D061e13892Ba16024b437E3725D934Fcd`
- Duration: 86.83s, 1 passed

## What this does and does not prove

- Proves: the contract deploys on Stable Studionet, `analyze_case`
  executes through live consensus to FINALIZED, and the stored
  record read back from the chain matches the deterministic
  expectations for both the blocked example and identical specs.
- Does not prove: real-model semantic behaviour (semantic_count
  was 0 in all three runs, so no live semantic finding was
  exercised here), Studio-UI deployment (these deployments went
  through gltest, not the Studio web UI), validator
  agreement/disagreement via `run_validator()`, or full
  repository deduplication. Those remain open, see `DEPLOY.md`.
- No Appeal was invoked in any run. No personal wallet, private
  key, mnemonic, or credential was used.
