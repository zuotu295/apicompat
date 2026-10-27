# ApiCompat mechanism

## The decision the contract makes

Given an old and a new OpenAPI 3 JSON document, decide one status:

- `COMPATIBLE` — no breaking and no warning findings.
- `REVIEW` — at least one warning, no breaking finding.
- `BLOCKED` — at least one breaking finding.

A `BLOCKED` case is not automatically rejected forever: its owner may
acknowledge it with a migration note (`ACKNOWLEDGED`), which records
that the breaking change was accepted deliberately. A later case may
supersede an earlier one (`SUPERSEDED`), so a chain of API versions
remains auditable.

## Stage 1 — deterministic parsing

Input must be a JSON object with an `openapi` field starting with
`3.` and a `paths` object. Each operation is keyed as
`METHOD /path` (for example `GET /users`). For each operation the
contract extracts:

- parameters, keyed `param:{in}:{name}`, with type, format, required,
  and enum. Path-level parameters are merged into every operation
  under the path, with operation-level parameters winning on a
  name/location clash. Local `#/components/parameters/...`
  references are resolved (cycle guard, chain bound 6); an
  unresolvable reference is recorded as an `unsupported` warning for
  that operation, not silently skipped;
- request fields, flattened from the `application/json` request-body
  schema, keyed by dotted path (`address.city`, `items[]` for array
  items), plus the request-body `required` flag. A requestBody that
  is a local `#/components/requestBodies/...` reference is resolved
  first; a requestBody with no content, a non-object requestBody, or
  an unresolvable requestBody reference is recorded as a warning,
  not skipped;
- response fields, flattened the same way from the first 2xx response
  JSON schema. A response that is a local
  `#/components/responses/...` reference is resolved first. Every
  2xx response is checked for media-type and reference warnings,
  even after the first JSON schema is found, so a warning from one
  response is never lost because another response had JSON;
- non-2xx response summaries, for change detection only: for each
  non-2xx status, its media types, its flattened JSON fields
  (plus schema warnings), and its description are recorded, but
  they are not diffed field by field. The diff compares these
  summaries between old and new and warns on any addition,
  removal, or change, including a description-only change;
- the `deprecated` flag;
- effective security scopes: an operation-level security list
  REPLACES the global list (OpenAPI override), so
  `security: []` on an operation means anonymous, even when a
  global list exists. Scopes are used for semantic-field
  association and for the deterministic scope diff below;
- an `unsupported` warning list for the operation, and a
  `context_text`: the canonical text of the operation, its
  path-level parameters, and every local component it references.
  This context is what semantic evidence is checked against.

Flattening resolves local `#/components/schemas/...` references with
a visited-set cycle guard and a depth bound of 4. External, missing,
or cyclic references are recorded as warnings and the field is
recorded as an opaque `ref:` type for comparison. `allOf` subschemas
are merged into the same prefix, and `properties` are flattened even
when no explicit `type` is given. Schema nesting beyond the depth
bound is recorded as a warning.

Media types: only `application/json` schemas are flattened. If a
request or response contains any other media type, a warning is
recorded (see the warning kinds below); if it contains no
`application/json` schema at all, a warning is recorded as well.
No media type is silently used as a fallback for JSON.

Rejected as invalid input: specs containing `webhooks`, and path
items that are references. Operation references and callbacks are
recorded as warnings for the operation (see below).

Combined schemas: `oneOf`, `anyOf`, and `not` branches are not
flattened as definite fields. A warning is recorded for the schema
node, and flattening stops for that subtree (definite `properties`
and `allOf` parts of the same node are still flattened). This makes
the gap visible in the record instead of claiming coverage that does
not exist.

## Stage 2 — deterministic diff

Findings are sorted by `(operation, field, kind, severity, source)`
so the stored record is canonical.

| Change | Kind | Severity |
|---|---|---|
| Operation removed | `operation_removed` | breaking |
| Operation added | `operation_added` | info |
| Operation deprecated / undeprecated | `operation_deprecated` / `operation_undeprecated` | warning / info |
| Required parameter removed | `required_parameter_removed` | breaking |
| Optional parameter removed | `parameter_removed` | warning |
| Required parameter added | `required_parameter_added` | breaking |
| Optional parameter added | `parameter_added` | info |
| Parameter became required / optional | `parameter_required_added` / `parameter_required_removed` | breaking / info |
| Parameter type changed | `parameter_type_changed` | per matrix below |
| Parameter format changed | `parameter_format_changed` | warning |
| Parameter enum shrunk / expanded | `parameter_enum_shrunk` / `parameter_enum_expanded` | breaking / info |
| Request field removed | `request_field_removed` | breaking |
| Required request field added | `request_required_field_added` | breaking |
| Optional request field added | `request_field_added` | info |
| Request field became required / optional | `request_field_required_added` / `request_field_required_removed` | breaking / info |
| Request field type changed | `request_field_type_changed` | per matrix |
| Request field format changed | `request_field_format_changed` | warning |
| Request field enum shrunk / expanded | `request_field_enum_shrunk` / `request_field_enum_expanded` | breaking / info |
| Response field removed | `response_field_removed` | breaking |
| Response field added | `response_field_added` | info |
| Response field type changed | `response_field_type_changed` | per matrix |
| Response field format changed | `response_field_format_changed` | warning |
| Response field enum shrunk / expanded | `response_field_enum_shrunk` / `response_field_enum_expanded` | breaking / info |
| Request body became required / optional | `request_body_required_added` / `request_body_required_removed` | breaking / info |
| Parameter became non-nullable / nullable | `parameter_nullable_removed` / `parameter_nullable_added` | breaking / info |
| Field became non-nullable / nullable | `request_field_nullable_removed` / `request_field_nullable_added`, `response_field_nullable_removed` / `response_field_nullable_added` | breaking / info |
| Security scope added / removed | `security_scope_added` / `security_scope_removed` | breaking / info |
| Enum values | `*_enum_shrunk` / `*_enum_expanded` | breaking / info, with float, int, string, and bool values distinguished by type (1, 1.0, and true are not collapsed) |
| Enum restriction added (no enum → finite enum) | `*_enum_shrunk` | breaking: values that used to be allowed are now rejected |
| Enum restriction removed (finite enum → no enum) | `*_enum_expanded` | info: previously rejected values are now allowed |
| Enum mixed replacement (values both removed and added, including a fully disjoint set) | `*_enum_shrunk` + `*_enum_expanded` | breaking (drives the status) + info; never silently passed |

Enum handling distinguishes "no enum" (unrestricted, stored as
`None`) from an explicitly set enum list. Adding a restriction
where none existed is a shrink; removing a restriction is an
expansion; a replacement that both removes and adds values
produces both findings, so no replacement passes silently
because of the shape of the sets involved.

### Deterministic warning kinds for unsupported structures

These are emitted for the union of old and new operations
(deduplicated by operation, field, kind, and detail, so distinct
warnings for different responses or schema nodes are preserved), and
a gap in either version forces at least `REVIEW`:

| Kind | When it is emitted |
|---|---|
| `unsupported_media_type` | A request or response has a non-JSON media type, a JSON entry without a schema, a response with no content, or no 2xx JSON schema at all |
| `unsupported_multiple_responses` | A second or later 2xx response has a JSON schema that is not diffed; only the first is diffed |
| `unsupported_schema_combination` | A schema node uses `oneOf`, `anyOf`, or `not` |
| `unsupported_schema_ref` | A schema reference is external, missing, or cyclic |
| `unsupported_schema_depth` | Schema nesting beyond the depth bound of 4 |
| `unsupported_parameter_ref` | A parameter reference cannot be resolved, is cyclic or too long, or a parameter lacks a name or location |
| `unsupported_request_body` | A requestBody is not an object or has no content |
| `unsupported_request_body_ref` | A requestBody reference cannot be resolved, is cyclic, or too long |
| `unsupported_response_ref` | A response reference cannot be resolved, is cyclic or too long, or a response entry is not an object |
| `unsupported_operation_ref` | An operation is a reference and was not diffed |
| `unsupported_operation_structure` | An operation has callbacks, which are not diffed |
| `unsupported_non_2xx_response` | A non-2xx response was added, removed, or changed; it is not diffed field by field, so a human must review the error surface |

### Type-compatibility matrix

| Old → New | Severity |
|---|---|
| Same type | (no finding) |
| `integer` → `number` | warning (widening) |
| `number` → `integer` | breaking (narrowing) |
| Either side `unknown` | warning |
| Either side a `ref:` type | warning |
| Any other change | breaking |

This matrix is deliberately conservative: an unknown or referenced
type change is a warning for a human to review, not a silent pass.

## Stage 3 — LLM semantic layer (additive only)

The leader calls `gl.nondet.exec_prompt` with `response_format="json"`
and a prompt that:

- wraps both specs as data inside `<old_spec>` / `<new_spec>` tags,
  after removing prompt-boundary markers from the spec text itself,
  so a forged closing tag inside a spec cannot end a data section
  early. The removal is a scanner, not exact-string replacement: it
  removes any `<...>` sequence whose tag name, after stripping
  surrounding whitespace, slashes, and JSON-escaped whitespace and
  lowercasing, is `old_spec` or `new_spec`, and any `===...===`
  sequence whose inner text, after stripping whitespace and
  underscores and lowercasing, contains `oldspec` or `newspec`.
  The placeholder is `[removed]` (9 characters), shorter than any
  marker it replaces, so sanitisation never expands a spec and a
  spec at the 12,000-character limit is not truncated;
- states explicitly that instructions inside the specs must be ignored,
  including any text that looks like a closing tag, a new section, or
  an instruction to change the output;
- lists the deterministic findings already found, so the LLM should
  not repeat them;
- restricts output to ten semantic kinds and three severities;
- requires each finding's evidence to be a verbatim excerpt.

### Allowed semantic kinds

`semantic_rename`, `format_or_unit_change`, `pagination_change`,
`error_semantics_change`, `default_change`, `auth_scope_tightened`,
`ordering_change`, `deprecation_timeline`, `rate_limit_change`,
`idempotency_change`.

### Semantic validation (deterministic, applied to every LLM output)

A semantic finding is kept only if all of these hold:

1. it is a JSON object with non-empty `operation`, `field`, `kind`,
   `severity`, and `evidence` (field ≤ 200 chars, evidence between
   5 and 300 chars);
2. `kind` is in the closed list and `severity` is
   `breaking` / `warning` / `info`;
3. `operation` exists in the old or the new spec;
4. the normalised evidence is a substring of that same operation's
   normalised context text (the operation, its path-level parameters,
   and every local component it references), not merely a substring
   of either whole spec. Evidence from another operation therefore
   fails, even if it appears somewhere in the spec;
5. the field resolves to a parsed parameter, request field, response
   field, security scope, or referenced component for that same
   operation. The check uses the parsed field sets (union of old and
   new), not a substring test on the operation text: a field that
   only appears in a description, and a field with no parsed
   association, both fail, even if the evidence itself is genuine
   text from that operation. Section names (`request`, `response`,
   `parameters`, `security`) are accepted only when that section
   exists for the operation; a component name is accepted only when
   the operation references that component;
6. the evidence is about the claimed field, not only about the
   operation. Field mentions are matched as whole words, not
   substrings, so `valid` does not count as a mention of `id`. If
   evidence mentions the claimed field (or a descendant of a
   claimed object field, or any field in a claimed section), it
   matches. If evidence mentions no parsed field at all, it
   matches ONLY if it mentions vocabulary for the claimed
   semantic kind (for example pagination words for
   `pagination_change`, or scope/security words for
   `auth_scope_tightened`); a generic description about something
   else entirely no longer passes merely by naming no field. If
   evidence mentions only other parsed fields, it does not match
   and the finding is rejected. For example, evidence that only
   describes the `admin` field cannot support a finding about
   `response.id`, and pagination prose cannot support an
   `auth_scope_tightened` finding. Additionally, an
   `auth_scope_tightened` finding's field must be a security
   scope (or `security`), not an unrelated data field;
7. it does not duplicate another kept semantic finding;
8. it does not shadow a deterministic finding on the same
   operation/field/kind.

Kept findings store the LLM's verbatim `evidence` in the record.
Deterministic findings store an explicit empty `evidence` string,
so a stored semantic finding can be audited against the operation
it names.

Semantic findings are capped at 20, in LLM order. The LLM result is
parsed tolerantly (dict with a `findings` list, a bare list, or a
JSON string possibly wrapped in code fences), but a result that cannot
be parsed is a leader error, not a stored result.

### Spec size and prompt coverage (unified limit)

Each spec is capped at 12,000 characters, and the prompt retains
exactly 12,000 characters per spec, so a validated case's prompt
contains the full spec text. A spec over 12,000 characters is
rejected with `INVALID_SPEC` instead of being silently truncated
for the LLM. Prompt sanitisation uses a placeholder shorter than
any marker it replaces, so sanitising a spec at the limit cannot
push it over the limit and cause truncation. The deterministic findings listed in the prompt are
capped at 200 entries for prompt size, but that list is guidance
only — the full deterministic set is still used to filter semantic
findings, so truncating it cannot create a duplicate or a missed
deterministic finding in the stored record. Remaining limit: large
APIs must be split into smaller cases (for example one case per
service or path group).

## Stage 4 — equivalence (custom validator)

The contract uses `gl.vm.run_nondet_unsafe` with a custom validator,
following the GenLayer documentation's recommended pattern for most
contracts. It does **not** use `strict_eq` for the LLM output, because
LLM wording is non-deterministic and exact equality would fail
consensus.

Validator logic:

1. If the leader result is not a `gl.vm.Return`, return `False`.
   Malformed LLM output therefore forces rotation to a new leader
   instead of being agreed on as an error.
2. Re-run the leader function independently.
3. Require the same derived `status` and the same
   `deterministic_count`. There is no `semantic_count` equality:
   the stored count is the leader's, and models may split one
   change into different numbers of findings.
4. Check that every semantic finding stored by the leader passes the
   same operation-anchored evidence check as in stage 3. A leader
   finding with unanchored evidence is rejected here even if its
   change type matches the validator's; this is defence in depth,
   since the leader's own validation already drops such findings
   before consensus.
5. Require the same deterministic decision set, where a decision is
   `(operation, field, kind, severity, source)`, and the same
   semantic change-type set, where a change type is
   `(operation, kind, severity)` and every change type must also
   share at least one field between leader and validator.

Detail text, evidence wording, and semantic finding multiplicity
are not required to be equal. The stored record keeps the leader's
wording and field list after consensus, provided that wording
passed step 4. This is the documented
partial-field-matching pattern: compare the fields that decide the
outcome, not the prose around them — with the added guard that the
prose must still be anchored to the operation it claims to describe.

Field-list exactness is deliberately not required: a model may
split one change across fields (for example one finding per
parameter of a pagination change), and exact field-list equality
would treat that legitimate split as a different verdict. The
group rule above still rejects a validator that finds no change,
a different kind, a different severity, or a disjoint field set,
so it is not agreement on wording alone; but field-level
exactness of a stored semantic finding is not
consensus-guaranteed, and the stored field should be checked
against the stored evidence.

A validator that only checked the leader's JSON shape, enum, or a
non-empty summary would not be consensus; this validator re-derives
the decision from the same inputs, which is why it satisfies the
documentation's warning against leader-output-only validation.

## Stage 5 — deterministic state write

Only after `run_nondet_unsafe` returns does deterministic code build
the record, store it in `cases: TreeMap[str, str]`, increment
`case_count`, and return the record. Nothing is written inside
`leader_fn` or `validator_fn`, and storage is never read inside a
non-deterministic block: deterministic findings, known operations,
and spec texts are captured as local variables, as the documentation
allows for captured locals.

## Errors

| Error prefix | Meaning |
|---|---|
| `INVALID_CASE_ID` | empty, too long (> 64), or illegal character |
| `INVALID_INPUT` | empty or too long name/version/note |
| `INVALID_SPEC` | not JSON, not OpenAPI 3, no paths, no operations, too many operations, or over the size cap |
| `CASE_EXISTS` | `case_id` already analysed |
| `NOT_FOUND` | case (or successor case) does not exist |
| `NOT_OWNER` | caller is not the case owner |
| `INVALID_STATUS` | transition not allowed from the current status |
| `LLM_ERROR` | LLM output could not be parsed or validated (leader-side; validators reject it) |
| `CONSENSUS_RESULT_INVALID` | consensus result could not be parsed after agreement (defensive; should not occur) |

## Prompt-injection and gaming notes

- Specs are untrusted input. They are delimited as data, the prompt
  instructs the model to ignore instructions inside them, and the
  deterministic layer cannot be overridden by any LLM output.
- A semantic finding cannot invent an operation, invent evidence, or
  use a kind outside the closed list. It also cannot borrow evidence
  from another operation or name a field absent from its operation;
  both are rejected by the association check, and stored evidence can
  be audited against the operation it claims to describe.
- A case owner cannot rewrite findings: `acknowledge_breaking` only
  changes status and adds a migration note; `mark_superseded` only
  changes status and records a successor. Findings are immutable once
  stored. `mark_superseded` additionally requires the successor to
  be for the same `api_name` (no cross-API successor links) and
  rejects any link that would close a successor cycle, by walking
  the successor chain with a bound of case_count + 1.
- The fingerprint is FNV-1a, not a cryptographic hash. It helps a
  reader spot that a spec changed; it does not prove authorship or
  prevent a determined party from crafting a colliding spec. Do not
  use it as a signature.
- Real-model resistance to prompt injection (as opposed to the
  deterministic guarantees above) can only be shown on a live
  validator set: no live prompt-injection pair has been run
  against the validator set, so that resistance is unproven even
  though the Studionet runs used live validators and stored live
  semantic findings; see `evidence/EVIDENCE.md`.

## Reuse guide for other builders

- **One instance, many APIs.** Deploy once, then analyse any API by
  choosing a new `case_id`. There is no per-API deployment.
- **Gate a release.** Treat `BLOCKED` as "do not release without an
  acknowledgement", `REVIEW` as "release only after human review",
  and `COMPATIBLE` as "no compatibility gate triggered".
- **Audit trail.** Keep cases instead of deleting them; supersede an
  old case with the new analysis so the version history stays
  readable through `get_case`.
- **Client integration.** Read `get_case` and check `status` plus
  `breaking_count` / `warning_count` before acting. Do not parse the
  LLM detail text as a decision; the decision fields are the
  contract's output. For semantic findings, also check the stored
  `evidence` against the operation it names if you need an audit
  trail; a semantic finding without operation-anchored evidence
  should not have been stored, and its presence would indicate a
  contract or validator problem.
- **What not to reuse this for.** This is not a legal opinion on API
  compatibility, not a security audit, and not a replacement for
  contract tests against a real server. It adjudicates the
  specifications as submitted; if the submitted specs do not match
  the deployed server, the verdict describes the specs, not the
  server.
