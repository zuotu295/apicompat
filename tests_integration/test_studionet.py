"""Studionet integration tests for ApiCompat (real chain, real validators).

Run ONLY with the reproducible environment, from the project root:
    .venv-repro/bin/python -m pytest tests_integration -v -s \
        --network studionet
or via the gltest CLI:
    .venv-repro/bin/gltest --network studionet tests_integration -v -s

These tests are NOT part of the default suite (tests/): they deploy
a contract to Stable Studionet (chain 61999, gasless test network)
and call it with the network's real validators. No mocked LLM is
used, so semantic findings may vary with the live validator set;
the assertions below are therefore written against the
deterministic layer, which the LLM cannot downgrade:
- the bundled example pair must be BLOCKED with exactly the 3
  deterministic breaking findings;
- an identical-spec pair must have deterministic_count == 0.

Each test deploys its own contract instance, so a full run leaves
a small number of ApiCompat contracts on Studionet. Do NOT run
this file against a network other than studionet without
reviewing it first, and do NOT use it for Appeal (the contract
has no appeal path and this suite does not invoke one).

The test prints a JSON evidence line per deployment/call so the
agent can archive the contract address, transaction hashes,
consensus status and execution result without relying on
pytest's summary alone.
"""

import json
from pathlib import Path

from gltest import get_contract_factory
from gltest.assertions import tx_execution_succeeded
from gltest.types import TransactionStatus

ROOT = Path(__file__).parent.parent


def _specs():
    old = (ROOT / "examples" / "old_spec.json").read_text()
    new = (ROOT / "examples" / "new_spec.json").read_text()
    return old, new


def _receipt_info(receipt):
    # Receipts are dict-like; be tolerant about field names so a
    # schema change surfaces as a missing field, not a crash.
    info = {}
    for key in ("hash", "transaction_hash", "tx_hash", "status",
                "consensus_status", "execution_result", "result",
                "contract_address", "address"):
        try:
            value = receipt.get(key)
        except Exception:
            value = None
        if value is not None:
            info[key] = str(value)
    info["raw_keys"] = sorted(list(receipt.keys())) if hasattr(receipt, "keys") else []
    return info


def test_studionet_deploy_and_blocked_example():
    factory = get_contract_factory(contract_file_path="api_compat.py")
    deploy_receipt = factory.deploy_contract_tx(
        wait_transaction_status=TransactionStatus.FINALIZED,
    )
    assert tx_execution_succeeded(deploy_receipt), deploy_receipt
    from gltest.utils import extract_contract_address
    address = extract_contract_address(deploy_receipt)
    contract = factory.build_contract(contract_address=address)
    print("\nEVIDENCE_DEPLOY " + json.dumps({
        "contract_address": str(address),
        "deploy_receipt": _receipt_info(deploy_receipt),
    }, sort_keys=True))

    old, new = _specs()
    call_receipt = contract.analyze_case(
        args=["studionet-example", "users-api", "1.0.0", "2.0.0", old, new]
    ).transact(wait_transaction_status=TransactionStatus.FINALIZED)
    assert tx_execution_succeeded(call_receipt), call_receipt
    print("EVIDENCE_ANALYZE " + json.dumps({
        "contract_address": str(address),
        "analyze_receipt": _receipt_info(call_receipt),
    }, sort_keys=True))

    status = contract.get_status(args=["studionet-example"]).call()
    count = contract.get_case_count().call()
    record = json.loads(contract.get_case(args=["studionet-example"]).call())
    print("EVIDENCE_RECORD " + json.dumps({
        "contract_address": str(address),
        "status": str(status),
        "case_count": str(count),
        "record": record,
    }, sort_keys=True))

    assert str(status) == "BLOCKED"
    assert int(count) == 1
    assert record["status"] == "BLOCKED"
    assert record["breaking_count"] == 3
    deterministic = [f for f in record["findings"] if f["source"] == "deterministic"]
    assert record["deterministic_count"] == len(deterministic)
    assert sorted(f["kind"] for f in deterministic if f["severity"] == "breaking") == sorted([
        "operation_removed",
        "request_required_field_added",
        "response_field_removed",
    ])


def test_studionet_identical_specs_have_no_deterministic_findings():
    factory = get_contract_factory(contract_file_path="api_compat.py")
    deploy_receipt = factory.deploy_contract_tx(
        wait_transaction_status=TransactionStatus.FINALIZED,
    )
    assert tx_execution_succeeded(deploy_receipt), deploy_receipt
    from gltest.utils import extract_contract_address
    address = extract_contract_address(deploy_receipt)
    contract = factory.build_contract(contract_address=address)
    print("\nEVIDENCE_DEPLOY " + json.dumps({
        "contract_address": str(address),
        "deploy_receipt": _receipt_info(deploy_receipt),
    }, sort_keys=True))

    old, _new = _specs()
    call_receipt = contract.analyze_case(
        args=["studionet-identical", "users-api", "1.0.0", "1.0.0", old, old]
    ).transact(wait_transaction_status=TransactionStatus.FINALIZED)
    assert tx_execution_succeeded(call_receipt), call_receipt
    print("EVIDENCE_ANALYZE " + json.dumps({
        "contract_address": str(address),
        "analyze_receipt": _receipt_info(call_receipt),
    }, sort_keys=True))
    record = json.loads(contract.get_case(args=["studionet-identical"]).call())
    print("EVIDENCE_RECORD " + json.dumps({
        "contract_address": str(address),
        "record": record,
    }, sort_keys=True))
    # Deterministic layer must find nothing for identical specs,
    # regardless of what the live LLM adds semantically.
    assert record["deterministic_count"] == 0
    assert all(f["source"] != "deterministic" or f["severity"] != "breaking"
               for f in record["findings"])
