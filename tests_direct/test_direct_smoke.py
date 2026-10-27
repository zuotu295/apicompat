"""Direct-mode smoke tests for ApiCompat, using the real GenVM.

These tests are deliberately kept separate from tests/test_api_compat.py:
they require the genlayer-test direct fixtures, which are only
available in the reproducible environment (.venv-repro), not in the
original minimal environment (.venv). They do not use the stand-in
in tests/conftest.py, and they make no network call and no chain
transaction: direct mode runs the contract in-process.

Run only with the reproducible environment, from the project root:
    .venv-repro/bin/python -m pytest tests_direct -v
"""

import json
from pathlib import Path

ROOT = Path(__file__).parent.parent


def _specs():
    old = (ROOT / "examples" / "old_spec.json").read_text()
    new = (ROOT / "examples" / "new_spec.json").read_text()
    return old, new


def test_direct_deploy_and_empty_view(direct_deploy):
    contract = direct_deploy("contracts/api_compat.py")
    assert contract.get_case_count() == 0
    assert contract.get_status("missing") == "NOT_FOUND"
    assert contract.get_case("missing") == ""


def test_direct_analyze_blocked_example(direct_vm, direct_deploy):
    direct_vm.mock_llm(".*", '{"findings": []}')
    contract = direct_deploy("contracts/api_compat.py")
    old, new = _specs()
    result = contract.analyze_case(
        "direct-smoke", "users-api", "1.0.0", "2.0.0", old, new
    )
    record = json.loads(result)
    assert record["status"] == "BLOCKED"
    assert record["breaking_count"] == 3
    assert contract.get_case_count() == 1
    assert contract.get_status("direct-smoke") == "BLOCKED"
    stored = json.loads(contract.get_case("direct-smoke"))
    assert stored["case_id"] == "direct-smoke"
