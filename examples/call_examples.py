"""Call examples for ApiCompat.

This script sends nothing, connects to nothing, and holds no key.
It only prints the exact arguments that can be pasted into GenLayer
Studio (or pass to the CLI / genlayer-js) after deploying the contract.
See DEPLOY.md for the deployment guide and evidence/EVIDENCE.md for
recorded deployments.

Example outcome (local tests, mocked LLM returning no semantic
findings): the bundled example pair is BLOCKED with 3 breaking and
1 info finding -- operation_removed, response_field_removed,
request_required_field_added, and parameter_added.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    old = (ROOT / "examples" / "old_spec.json").read_text()
    new = (ROOT / "examples" / "new_spec.json").read_text()
    print("== analyze_case (write) ==")
    print(json.dumps({
        "case_id": "example-users",
        "api_name": "users-api",
        "old_version": "1.0.0",
        "new_version": "2.0.0",
        "old_spec_chars": len(old),
        "new_spec_chars": len(new),
        "old_spec": json.loads(old),
        "new_spec": json.loads(new),
    }, indent=2, sort_keys=True))
    print()
    print("== acknowledge_breaking (write, case owner only, BLOCKED only) ==")
    print(json.dumps({
        "case_id": "example-users",
        "migration_note": "Clients must stop reading the removed email field and send tenant on creation.",
    }, indent=2))
    print()
    print("== get_case / get_status / get_case_count (views) ==")
    print('get_case("example-users")  -> canonical JSON record, or "" if missing')
    print('get_status("example-users") -> COMPATIBLE | REVIEW | BLOCKED | ACKNOWLEDGED | SUPERSEDED | NOT_FOUND')
    print("get_case_count() -> number of analysed cases")
    print()
    print("== genlayer-js sketch (after deployment, address placeholder only) ==")
    print(
        "// const tx = await client.writeContract({\n"
        "//   address: '0xYOUR_DEPLOYED_CONTRACT', // fill in after deployment\n"
        "//   functionName: 'analyze_case',\n"
        "//   args: ['example-users', 'users-api', '1.0.0', '2.0.0', oldSpecText, newSpecText],\n"
        "// });\n"
        "// const record = await client.readContract({\n"
        "//   address: '0xYOUR_DEPLOYED_CONTRACT', functionName: 'get_case',\n"
        "//   args: ['example-users'],\n"
        "// });"
    )


if __name__ == "__main__":
    main()
