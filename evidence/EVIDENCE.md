# Evidence — Stable Studionet

Runs recorded 2026-10-27 (Beijing time). Machine-readable
evidence: `studionet_deployment_2026-10-27.json`,
`studionet_semantic_2026-10-27.json`, and
`studionet_enum_2026-10-27.json` in this directory. This file is
a human-readable summary of the same runs; it adds no address,
hash, or result beyond what the test output printed.

## Source versions

Instances in sections 1–4 were deployed from the contract
version current when those runs were made. The instance in
section 5 was deployed from the current contract
(SHA-256 `5a2d094ca25c85b78ed9a9d25bdee2ed71072eea5203173ee76632740eacb25b`).
The specs used in sections 1–4 contain no enums, so the enum
handling in the current contract does not change any verdict
stored there. Instances keep running the code they were deployed
with for any later case; a verdict is evidence for the contract
version of its own instance, not for any other instance.

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

Each integration test deploys its own contract instance.

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

- Contract: `0xb3b6199Cd484f480AD97795C6b9dC1F36814ba98`
- Deploy tx: `0x070d742fb10a3b9f9528f6d252575ae2f19a4c809d9b13edf076c5f5e6ec2657`
- Analyze tx: `0x34230b774159c115621de9065266155939a1416b4ce2ab0cb0fae268dc5a8e0d`
- Stored record: COMPATIBLE, deterministic 0, semantic 0, breaking 0
- Owner: `0xfC94700D061e13892Ba16024b437E3725D934Fcd`
- Duration: 86.83s, 1 passed

## 4. Semantic consensus — two live semantic findings stored

Machine-readable: `studionet_semantic_2026-10-27.json`.
Test: `tests_integration/test_studionet_semantic.py`, 1 passed in
220.60s. One contract instance, three cases, owner (gltest
auto-generated test account, not a personal wallet)
`0x932298E26267d6F4d85bbAbA775e98ce2A984C82`, case count 3 after
the run. All three records were read back independently from the
contract after the test and match the values below.

- Contract: `0x67bd8990BBE8f90134E6Ec271F4f170310C2Bfe8`
- Deploy tx: `0x995b0d01485a4b9e900e30300abe288464dc394b66c661ede2dd456cc88a8336`
  (FINALIZED)
- Case `semantic-pagination`: analyze tx
  `0x20f7b0ab8a5eab28bb5b547e56287ad6e1f844fb2b81c378bdb63c348ab70c79`
  (FINALIZED, execution succeeded) → **BLOCKED, deterministic 0,
  semantic 1, breaking 1**. Finding: `pagination_change`, breaking,
  field `param:query:cursor`, evidence verbatim from the new
  description ("List users with cursor pagination…"). The
  deterministic layer alone would have said COMPATIBLE (identical
  schemas and parameters), so this verdict comes only from the
  semantic layer, agreed by the live validator set.
- Case `semantic-auth`: analyze tx
  `0x823f9162c4e5fd087feba686608c54bc298e9bae8d1777e7a9ffc8fb46cc17d4`
  (FINALIZED, execution succeeded) → **BLOCKED, deterministic 0,
  semantic 1, breaking 1**. Finding: `auth_scope_tightened`,
  breaking, field `read:users`, evidence verbatim from the new
  description ("Get a user. Both read:users scope and admin:users
  scope are now required…"). The deterministic scope-set diff alone
  would have said COMPATIBLE (same scope set; only the prose
  changed from either-scope-sufficient to both-required).
- Case `semantic-error`: analyze tx
  `0x824f5be4303fed9df9797cf7a12bc968fcf0aede0a6685604ab1a503aed35a05`
  (FINALIZED, execution succeeded) → **REVIEW, deterministic 1,
  semantic 0, warning 1**. The deterministic non-2xx description
  warning (`unsupported_non_2xx_response`, field `response`)
  forced REVIEW, but no agreed `error_semantics_change` finding
  was stored in this run. Whether the leader produced none or
  validators disagreed cannot be told from the stored record
  alone; this is recorded as a limitation, not retried endlessly.

### Disagreement behaviour — MAJORITY_DISAGREE run (nothing stored)

- Contract: `0x037f745BDae79c85E283eb177ef5DCEFC2E323D6`
- Deploy tx: `0x6406846146b3f833f801077fdd1e54b2d9f3c97a79f66ebdfbd98b69444a811e`
  (FINALIZED)
- Pagination analyze tx:
  `0xc5ed4807be315775cf9f5c40008f0e87072648b8ee6e267ccd6b173564df0a4c`
  — later queried and confirmed FINALIZED as MAJORITY_DISAGREE
  (validators 3 disagree / 2 agree, rotations exhausted). Leader
  result: 3 breaking `pagination_change` findings, one per
  parameter (cursor, limit, page), deterministic 0, BLOCKED.
  Nothing was stored (case NOT_FOUND, case count 0, verified by a
  later read), which is the designed disagreement behaviour:
  exact field-list equality treated a legitimate per-field split
  of one change as a different verdict. The equivalence rule in
  `MECHANISM.md` is the change-type-group rule (operation, kind,
  severity, with at least one shared field per group), and the
  prompt instructs one finding per distinct change. That rule
  still rejects a validator that finds no change, a different
  kind, a different severity, or a disjoint field set.

## 5. Enum verification — disjoint replacement BLOCKED

Machine-readable: `studionet_enum_2026-10-27.json`.
Test: `tests_integration/test_studionet_enum.py`, 1 passed in
88.00s. One contract instance, one case, owner (gltest
auto-generated test account, not a personal wallet)
`0x3f2F05dB388dCA2c9FeBbF531F1B6f06a2623E6e`, case count 1.
The record was read back independently from the contract after
the test and matches the values below.

- Contract: `0x3DEEE3252fc812D533F8Ad1d41579794A90f24fC`
- Deploy tx: `0xff74c6a50a6f748359e2d0f43c2d07cb69d69072a9c953f5cfcc5a7e1fc9f97a`
  (FINALIZED)
- Case `studionet-enum-disjoint`: analyze tx
  `0x0252796ce26c5a471e0013250ef3f4eff458265e4b16372aeb2219b7e21543b3`
  (FINALIZED, execution succeeded) → **BLOCKED, deterministic 2,
  semantic 0, breaking 1, info 1**. Findings: response field
  `state`, `response_field_enum_shrunk` (breaking, values
  removed) and `response_field_enum_expanded` (info, values
  added), for the replacement `["open", "closed"]` →
  `["active", "archived"]` with no surviving value.
- Version note: see "Source versions" above. This instance, not
  an earlier address, is the evidence for the enum handling in
  the current contract.

## What this does and does not prove

- Proves: the contract deploys on Stable Studionet, `analyze_case`
  executes through live consensus to FINALIZED, and the stored
  record read back from the chain matches the deterministic
  expectations for both the blocked example and identical specs;
  live validators agreed on two semantic findings (pagination
  and auth scope) whose verdicts the deterministic layer alone
  would not have produced, while a disagreement in another run
  wrote nothing, as designed.
- Does not prove: a live `error_semantics_change` finding (see
  case `semantic-error` above), or Studio-UI deployment (these
  deployments went through gltest, not the Studio web UI).
  See `DEPLOY.md`.
- No Appeal was invoked in any run. No personal wallet, private
  key, mnemonic, or credential was used.
