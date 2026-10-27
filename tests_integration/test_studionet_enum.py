"""Studionet enum-diff verification for ApiCompat (real chain, real validators).

Run ONLY with the reproducible environment, from the project root:
    .venv-repro/bin/gltest --network studionet tests_integration/test_studionet_enum.py -v -s

One case, one deploy: a disjoint enum replacement on a response
field. Under the pre-fix contract this case passed silently (the
old _enum_diff only handled strict subset/superset and returned
early on empty sides, so a replacement with no surviving value
produced no finding). Under the fixed contract it must store
BLOCKED with both a breaking enum_shrunk finding and an info
enum_expanded finding. No mocked LLM is used; the semantic layer
is not expected to add findings here, and the test does not
require any. No Appeal is invoked.
"""

import json

from gltest import get_contract_factory
from gltest.assertions import tx_execution_succeeded
from gltest.types import TransactionStatus
from gltest.utils import extract_contract_address


def _spec(enum_values):
    return json.dumps({
        "openapi": "3.0.3",
        "paths": {"/items": {"get": {
            "responses": {"200": {"description": "ok", "content": {
                "application/json": {"schema": {
                    "type": "object",
                    "properties": {
                        "state": {"type": "string", "enum": enum_values},
                    }}}}}}}}},
    })


def test_studionet_enum_disjoint_replacement():
    factory = get_contract_factory(contract_file_path="api_compat.py")
    deploy_receipt = factory.deploy_contract_tx(
        wait_transaction_status=TransactionStatus.FINALIZED,
    )
    assert tx_execution_succeeded(deploy_receipt), deploy_receipt
    address = extract_contract_address(deploy_receipt)
    contract = factory.build_contract(contract_address=address)
    print("\nEVIDENCE_ENUM_DEPLOY " + json.dumps({
        "contract_address": str(address),
        "deploy_tx_hash": str(deploy_receipt.get("hash")),
        "deploy_status": str(deploy_receipt.get("status")),
    }, sort_keys=True))

    call_receipt = contract.analyze_case(
        args=["studionet-enum-disjoint", "items-api", "1.0.0", "2.0.0",
              _spec(["open", "closed"]), _spec(["active", "archived"])]
    ).transact(wait_transaction_status=TransactionStatus.FINALIZED,
               wait_retries=200)
    assert tx_execution_succeeded(call_receipt), call_receipt
    record = json.loads(contract.get_case(args=["studionet-enum-disjoint"]).call())
    print("EVIDENCE_ENUM_CASE " + json.dumps({
        "case_id": "studionet-enum-disjoint",
        "analyze_tx_hash": str(call_receipt.get("hash")),
        "analyze_status": str(call_receipt.get("status")),
        "status": record["status"],
        "deterministic_count": record["deterministic_count"],
        "semantic_count": record["semantic_count"],
        "breaking_count": record["breaking_count"],
        "findings": record["findings"],
    }, sort_keys=True))
    assert record["status"] == "BLOCKED"
    assert any(f["kind"] == "response_field_enum_shrunk"
               and f["severity"] == "breaking" for f in record["findings"])
    assert any(f["kind"] == "response_field_enum_expanded"
               and f["severity"] == "info" for f in record["findings"])
