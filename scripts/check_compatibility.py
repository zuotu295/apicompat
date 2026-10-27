"""Static compatibility check for ApiCompat (no network, no keys, no chain).

This is a local AST + configuration check. It is NOT a substitute for
``genvm-lint check`` or for a real Studio / gltest run, both of which
are listed as pending in DEPLOY.md. It verifies the things that can be
verified offline:

* the GenVM dependency header is present and exact;
* imports are limited to the GenLayer SDK and ``json``;
* storage uses TreeMap / u32 (no plain dict / list storage);
* every public method has a decorator and a return annotation;
* non-deterministic calls go through the equivalence path and no
  storage write occurs inside a leader/validator function;
* the pinned network configuration is Stable Studionet (61999);
* the example specs are valid OpenAPI 3 JSON.

Usage:  python3 scripts/check_compatibility.py
Exit code 0 means all local checks passed.
"""

import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTRACT = ROOT / "contracts" / "api_compat.py"
NETWORK = ROOT / "network.json"
EXAMPLES = ROOT / "examples"

EXPECTED_HEADER = '# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }'
FORBIDDEN_IMPORTS = {
    "os", "sys", "subprocess", "random", "time", "socket", "urllib",
    "requests", "hashlib", "pathlib", "typing",
}
EXPECTED_METHODS = {
    "analyze_case": ("write", "str"),
    "acknowledge_breaking": ("write", "str"),
    "mark_superseded": ("write", "str"),
    "get_case": ("view", "str"),
    "get_status": ("view", "str"),
    "get_case_count": ("view", "u32"),
}

failures = []


def check(name, ok, detail=""):
    print(("PASS" if ok else "FAIL") + "  " + name + (("  " + detail) if detail else ""))
    if not ok:
        failures.append(name)


def main():
    source = CONTRACT.read_text()
    first_line = source.splitlines()[0] if source else ""
    check("genvm-dependency-header", first_line.strip() == EXPECTED_HEADER, first_line.strip())
    tree = ast.parse(source)

    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split(".")[0])
    check("imports-are-minimal", imports <= {"genlayer", "json"}, "imports=" + ",".join(sorted(imports)))
    check("no-forbidden-imports", not (imports & FORBIDDEN_IMPORTS))

    contract_class = None
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "ApiCompat":
            contract_class = node
    check("contract-class-exists", contract_class is not None)
    if contract_class is None:
        print("FAILED: cannot continue without ApiCompat")
        return 1

    annotations = {}
    for node in contract_class.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            annotations[node.target.id] = ast.unparse(node.annotation)
    check("storage-cases-is-treemap", annotations.get("cases") == "TreeMap[str, str]", annotations.get("cases", ""))
    check("storage-count-is-u32", annotations.get("case_count") == "u32", annotations.get("case_count", ""))

    methods = {}
    for node in contract_class.body:
        if isinstance(node, ast.FunctionDef):
            decorators = []
            for deco in node.decorator_list:
                decorators.append(ast.unparse(deco))
            ret = ast.unparse(node.returns) if node.returns is not None else ""
            methods[node.name] = (decorators, ret)
    for name, (kind, ret) in EXPECTED_METHODS.items():
        present = name in methods
        deco_ok = present and any("gl.public." + kind in d for d in methods[name][0])
        ret_ok = present and methods[name][1] == ret
        check("method-" + name, present and deco_ok and ret_ok,
              "decorators=" + str(methods[name][0]) + " return=" + methods[name][1] if present else "missing")

    # Non-determinism must be contained: exec_prompt and
    # run_nondet_unsafe must be present, and no `self.` assignment
    # may occur inside a function named leader_fn / validator_fn.
    text = source
    check("uses-exec-prompt", "gl.nondet.exec_prompt" in text)
    check("uses-run-nondet-unsafe", "gl.vm.run_nondet_unsafe" in text)
    # Invariants: the spec limit must equal the prompt limit (no
    # silent prompt truncation), semantic evidence must be stored,
    # and unsupported structures must be warned about instead of
    # silently skipped.
    check("spec-limit-equals-prompt-limit",
          "MAX_SPEC_CHARS = 12000" in text and "MAX_PROMPT_SPEC_CHARS = 12000" in text)
    check("semantic-evidence-is-stored", '"evidence": item["evidence"]' in text)
    check("validator-checks-leader-evidence",
          "_is_valid_semantic_finding(finding, operation_data)" in text)
    check("semantic-field-association-uses-parsed-fields",
          "_field_is_associated" in text and "_build_operation_data" in text)
    check("field-level-evidence-check-exists", "_evidence_matches_field" in text)
    check("non-2xx-warning-exists", '"unsupported_non_2xx_response"' in text)
    check("sanitiser-placeholder-does-not-expand",
          '"[removed]"' in text and '"[boundary marker removed]"' not in text)
    check("prompt-boundary-sanitisation-exists", "_sanitize_prompt_text" in text)
    check("media-type-warning-exists", '"unsupported_media_type"' in text)
    check("schema-combination-warning-exists", '"unsupported_schema_combination"' in text)
    check("parameter-ref-warning-exists", '"unsupported_parameter_ref"' in text)
    check("request-body-ref-warning-exists", '"unsupported_request_body_ref"' in text)
    check("response-ref-warning-exists", '"unsupported_response_ref"' in text)
    check("multiple-responses-warning-exists", '"unsupported_multiple_responses"' in text)
    check("schema-ref-warning-exists", '"unsupported_schema_ref"' in text)
    check("schema-depth-warning-exists", '"unsupported_schema_depth"' in text)
    check("no-silent-media-fallback",
          "for key in sorted(content.keys()):" not in text)
    check("does-not-use-strict-eq-for-llm", "gl.eq_principle.strict_eq" not in text)
    storage_write_in_nondet = False
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in ("leader_fn", "validator_fn"):
            for sub in ast.walk(node):
                if isinstance(sub, ast.Assign):
                    for target in sub.targets:
                        if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == "self":
                            storage_write_in_nondet = True
                if isinstance(sub, ast.AnnAssign) and isinstance(sub.target, ast.Attribute):
                    storage_write_in_nondet = True
    check("no-storage-write-inside-nondet", not storage_write_in_nondet)

    network = json.loads(NETWORK.read_text())
    check("network-is-stable-studionet", network.get("chainId") == 61999, "chainId=" + str(network.get("chainId")))
    check("network-rpc", network.get("rpcUrl") == "https://studio.genlayer.com/api", network.get("rpcUrl", ""))
    check("network-explorer", network.get("explorer") == "https://explorer-studio.genlayer.com")
    gltest_text = (ROOT / "gltest.config.yaml").read_text()
    check("gltest-config-uses-valid-keys",
          "rpc_url" not in gltest_text and "chain_id" not in gltest_text
          and 'url: "https://studio.genlayer.com/api"' in gltest_text
          and "id: 61999" in gltest_text and "default: localnet" in gltest_text)

    for example in ("old_spec.json", "new_spec.json"):
        doc = json.loads((EXAMPLES / example).read_text())
        ok = isinstance(doc, dict) and str(doc.get("openapi", "")).startswith("3.") and isinstance(doc.get("paths"), dict)
        check("example-" + example + "-is-openapi3-json", ok)

    print()
    if failures:
        print("FAILED checks: " + ", ".join(failures))
        return 1
    print("All local compatibility checks passed.")
    print("Not covered here: genvm-lint, gltest direct/integration, Studio deployment.")
    print("Run genvm-lint separately on the current contract and record its actual output;")
    print("this script does not claim a linter result.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
