"""Studionet semantic consensus tests for ApiCompat (real chain, real validators).

Run ONLY with the reproducible environment, from the project root:
    .venv-repro/bin/gltest --network studionet tests_integration/test_studionet_semantic.py -v -s

These tests are NOT part of the default suite. Each case is designed
so the deterministic layer alone does NOT produce the verdict that
the semantic layer is expected to produce:

- pagination: old and new specs have identical schemas and
  parameters; only the pagination prose changes (offset -> cursor,
  ordering changes). Deterministic: COMPATIBLE. A semantic
  pagination_change finding, if produced and agreed, moves the
  stored status to REVIEW or BLOCKED.
- auth scope: old and new specs have the SAME security scope set
  (read:users and admin:users, either is sufficient in the old
  prose); the new prose requires BOTH scopes. Deterministic
  scope-set diff: none. A semantic auth_scope_tightened finding,
  if produced and agreed, moves the stored status.
- error semantics: the 400 response schema is identical; only its
  description changes meaning (validation failure -> payment
  failure). Deterministic: a non-2xx REVIEW warning only. A
  semantic error_semantics_change breaking finding, if produced
  and agreed, moves the stored status to BLOCKED.

The test asserts semantic_count > 0 for at least one case, and
records every case's deterministic counts, semantic findings,
status, contract address, and transaction hashes, so a partial
result is still evidence, not a hidden failure. It does NOT
assert all three cases produce semantic findings: live models
vary, and asserting all three would turn model variance into a
contract failure. If no case produces a semantic finding, the
test fails honestly and the printed records show why (for
example deterministic counts, or semantic findings that were
dropped by validation, which cannot be seen from the stored
record alone and must then be investigated from the prompt).

No mocked LLM is used. No Appeal is invoked. Each test deploys
its own contract instance.
"""

import json

from gltest import get_contract_factory
from gltest.assertions import tx_execution_succeeded
from gltest.types import TransactionStatus
from gltest.utils import extract_contract_address


def _spec(operation):
    return json.dumps({"openapi": "3.0.3", "paths": {"/users": {"get": operation}}})


def _list_operation(description):
    return {
        "description": description,
        "parameters": [
            {"name": "page", "in": "query", "required": False,
             "schema": {"type": "integer"}},
            {"name": "limit", "in": "query", "required": False,
             "schema": {"type": "integer"}},
            {"name": "cursor", "in": "query", "required": False,
             "schema": {"type": "string"}},
        ],
        "responses": {"200": {"description": "ok", "content": {
            "application/json": {"schema": {
                "type": "object",
                "properties": {
                    "items": {"type": "array", "items": {"type": "object", "properties": {
                        "id": {"type": "integer"}}}},
                    "total": {"type": "integer"},
                }}}}}},
    }


def _auth_operation(description):
    return {
        "description": description,
        "security": [{"oauth": ["read:users", "admin:users"]}],
        "responses": {"200": {"description": "ok", "content": {
            "application/json": {"schema": {
                "type": "object",
                "properties": {"id": {"type": "integer"}}}}}}},
    }


def _error_operation(description):
    return {
        "description": "Get a user.",
        "responses": {
            "200": {"description": "ok", "content": {
                "application/json": {"schema": {
                    "type": "object",
                    "properties": {"id": {"type": "integer"}}}}}},
            "400": {"description": description, "content": {
                "application/json": {"schema": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string"},
                        "message": {"type": "string"},
                    }}}}}},
    }


CASES = [
    ("semantic-pagination",
     _spec(_list_operation(
         "List users with offset pagination. Use page and limit parameters. "
         "Results are ordered by id ascending. The cursor parameter is ignored.")),
     _spec(_list_operation(
         "List users with cursor pagination. Use cursor parameter to get the next page. "
         "Results are ordered by created_at descending. The page and limit parameters are ignored.")),
     "pagination_change"),
    ("semantic-auth",
     _spec(_auth_operation(
         "Get a user. Either read:users scope or admin:users scope is sufficient. "
         "Any authenticated user with one of these scopes may call this operation.")),
     _spec(_auth_operation(
         "Get a user. Both read:users scope and admin:users scope are now required. "
         "A user with only read:users scope is no longer sufficient and will be denied.")),
     "auth_scope_tightened"),
    ("semantic-error",
     _spec(_error_operation(
         "Invalid input. The code field means the request failed validation.")),
     _spec(_error_operation(
         "Invalid input. The code field now means the payment failed, not that the request failed validation. "
         "Clients that treat this code as a validation error will behave incorrectly.")),
     "error_semantics_change"),
]


def test_studionet_semantic_cases():
    factory = get_contract_factory(contract_file_path="api_compat.py")
    deploy_receipt = factory.deploy_contract_tx(
        wait_transaction_status=TransactionStatus.FINALIZED,
    )
    assert tx_execution_succeeded(deploy_receipt), deploy_receipt
    address = extract_contract_address(deploy_receipt)
    contract = factory.build_contract(contract_address=address)
    print("\nEVIDENCE_SEMANTIC_DEPLOY " + json.dumps({
        "contract_address": str(address),
        "deploy_tx_hash": str(deploy_receipt.get("hash")),
        "deploy_status": str(deploy_receipt.get("status")),
    }, sort_keys=True))

    results = []
    for case_id, old, new, expected_kind in CASES:
        # Consensus with rotations can take longer than the default
        # 50 x 3s wait (the first run was still UNDETERMINED at 150s
        # and only later finalised as MAJORITY_DISAGREE), so wait up
        # to 600s here instead of treating a slow consensus as a
        # failure.
        call_receipt = contract.analyze_case(
            args=[case_id, "users-api", "1.0.0", "2.0.0", old, new]
        ).transact(wait_transaction_status=TransactionStatus.FINALIZED,
                   wait_retries=200)
        # Do not abort the remaining cases on one disagreement: a
        # MAJORITY_DISAGREE finalisation writes nothing, which is
        # itself evidence, and the other cases may still agree.
        raw = contract.get_case(args=[case_id]).call()
        record = json.loads(raw) if raw else None
        semantic = ([f for f in record["findings"] if f["source"] == "llm"]
                    if record else [])
        entry = {
            "case_id": case_id,
            "expected_kind": expected_kind,
            "analyze_tx_hash": str(call_receipt.get("hash")),
            "analyze_status": str(call_receipt.get("status")),
            "tx_execution_succeeded": bool(tx_execution_succeeded(call_receipt)),
            "status": record["status"] if record else "NOT_STORED",
            "deterministic_count": record["deterministic_count"] if record else 0,
            "semantic_count": record["semantic_count"] if record else 0,
            "semantic_findings": semantic,
            "breaking_count": record["breaking_count"] if record else 0,
        }
        results.append(entry)
        print("EVIDENCE_SEMANTIC_CASE " + json.dumps(entry, sort_keys=True))

    # At least one live semantic finding must survive validation
    # and consensus; otherwise the semantic layer has not been
    # shown to work on the live validator set in this run.
    assert any(r["semantic_count"] > 0 for r in results), results
    # Every stored semantic finding must carry the evidence,
    # field, kind, and severity that the contract requires, and
    # its kind must be one of the expected kinds for its case.
    for entry in results:
        for finding in entry["semantic_findings"]:
            assert finding["evidence"] and len(finding["evidence"]) >= 5
            assert finding["field"] and finding["kind"] and finding["severity"]
        if entry["semantic_count"] > 0:
            assert entry["tx_execution_succeeded"], entry
            assert any(f["kind"] == entry["expected_kind"]
                       for f in entry["semantic_findings"]), entry
