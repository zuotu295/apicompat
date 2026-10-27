# ApiCompat — OpenAPI Compatibility Adjudicator

A standalone GenLayer Intelligent Contract that decides, as shared
on-chain state, whether a new version of an API is compatible with the
old one, needs review, or is blocked by a breaking change.

## What it is

An API producer submits two OpenAPI 3 JSON documents. The contract
returns and stores a canonical record:

- `status`: `COMPATIBLE`, `REVIEW`, `BLOCKED`, `ACKNOWLEDGED`, or `SUPERSEDED`
- `findings`: a sorted list of deterministic and LLM semantic findings,
  each with `operation`, `field`, `kind`, `severity`, `source`,
  `detail`, and `evidence` (the validated verbatim excerpt for
  semantic findings; an explicit empty string for deterministic
  findings, so consumers never have to guess whether evidence was
  dropped)
- `breaking_count`, `warning_count`, `info_count`,
  `deterministic_count`, `semantic_count`
- `old_fingerprint` / `new_fingerprint`: deterministic FNV-1a checksums
  of the submitted specs (a reviewer aid, not a cryptographic hash)
- `owner`, `migration_note`, `successor_case_id`

One deployed instance serves many APIs: each analysis is namespaced by
`case_id`, and ownership is per case (the address that analysed it).

## Why this needs GenLayer

A syntactic diff alone misses semantic breaks: a field renamed with a
changed meaning, pagination switching from offset to cursor, an error
code changing meaning, a default changing, or an auth scope tightening.
A plain backend LLM call is not shared, auditable state. ApiCompat
puts the decision on chain, but bounds the LLM:

1. **Deterministic diff first, and authoritative.** Operations,
   parameters, and flattened request/response fields are diffed with a
   fixed type-compatibility matrix. A deterministic `breaking` finding
   can never be downgraded by the LLM.
2. **Closed semantic vocabulary, operation-anchored evidence.** The
   LLM may only add findings from ten kinds (see `MECHANISM.md`).
   Each finding must name an operation that exists in a spec, a field
   that resolves to a parsed parameter, request field, response
   field, security scope, or referenced component for that same
   operation, and a verbatim excerpt (at least 5 characters) from
   that same operation's text, including any component it
   references. Evidence must also be about the claimed field: if
   it mentions only a different parsed field, the finding is
   dropped, even when the field itself is parsed and the evidence
   is verbatim text from the same operation. Generic evidence that
   mentions no parsed field at all (for example a pagination
   description) is still accepted. Validated evidence is stored in
   the record for audit. Spec text is treated as data, never as
   instructions; prompt-boundary markers inside a spec are removed
   before the spec is embedded in the prompt, so a forged closing
   tag cannot end a data section early. The removal handles
   internal spaces, tabs, newlines, JSON-escaped whitespace, case
   variants, and forged segment markers, and it never expands the
   spec text, so a spec at the size limit is not truncated.
3. **Independent validator re-execution.** A validator re-runs the
   leader function and must match the deterministic decision set
   exactly and the semantic change-type set (operation, kind,
   severity, with at least one shared field per change type), plus
   the derived status. Evidence wording and semantic finding
   multiplicity are not required to be equal, because models phrase
   the same decision differently and may split one change across
   different fields, but the validator also checks that every
   semantic finding stored by the leader has operation-anchored
   evidence; a finding that fails that check is rejected even if its
   change type matches. A validator that finds no change, a different
   kind, a different severity, or a disjoint field set still
   disagrees. Malformed LLM output is rejected (not agreed
   on), so a broken leader forces rotation instead of storing a broken
   result.
4. **State only after consensus.** Storage writes happen in
   deterministic code after `gl.vm.run_nondet_unsafe` returns. A
   rejected consensus writes nothing.

## State machine

```
analyze_case
  -> COMPATIBLE
  -> REVIEW
  -> BLOCKED --acknowledge_breaking (owner, migration note)--> ACKNOWLEDGED
COMPATIBLE / REVIEW / ACKNOWLEDGED --mark_superseded (owner, existing successor, same api_name, no successor cycle)--> SUPERSEDED
```

`BLOCKED` cannot jump straight to `SUPERSEDED`; it must be
acknowledged first. Acknowledgement is one-way, and superseding is
one-way. Missing cases read as `get_case() == ""` and
`get_status() == "NOT_FOUND"` by design, so clients can check
existence without handling a view revert.

## Contract API

| Method | Kind | Arguments | Returns |
|---|---|---|---|
| `analyze_case` | write | `case_id, api_name, old_version, new_version, old_spec, new_spec` (all `str`) | canonical JSON record (`str`) |
| `acknowledge_breaking` | write | `case_id, migration_note` | updated record (`str`) |
| `mark_superseded` | write | `case_id, successor_case_id` | updated record (`str`) |
| `get_case` | view | `case_id` | record (`str`), or `""` |
| `get_status` | view | `case_id` | status (`str`), or `NOT_FOUND` |
| `get_case_count` | view | — | `u32` |

Errors are `gl.vm.UserError` values such as `CASE_EXISTS`,
`NOT_OWNER`, `INVALID_STATUS`, `NOT_FOUND`, and `INVALID_SPEC`.

## Local tests

```bash
python3 -m venv .venv
.venv/bin/pip install pytest
.venv/bin/python -m pytest tests -v
```

The tests load `contracts/api_compat.py` itself behind a small
GenLayer stand-in (see `tests/conftest.py`), so they exercise the
deployable file, not a copy of its logic. They cover the deterministic
diff, the semantic filter, validator agreement and disagreement,
malformed LLM output, prompt-injection resistance of the deterministic
layer, prompt-boundary sanitisation, requestBody and response
references, per-response media warnings, parsed-field association,
input validation, and the full state machine.

Local test result: **89 passed** in the stand-in suite, plus 2
direct-mode smoke tests (see below). The test count is reported
as a result, not as a proof of correctness. Studionet integration
is now done (2026-10-27, live validators, FINALIZED; see
`evidence/EVIDENCE.md` and `TESTING.md`): the bundled example is
BLOCKED on-chain, identical specs are COMPATIBLE on-chain, and
the final round stored two live semantic findings (pagination
and auth-scope tightening) through real validator consensus,
while an earlier same-day run finalised as MAJORITY_DISAGREE and
stored nothing, as designed. Still open (see `DEPLOY.md`):
Studio-UI deployment, a live `error_semantics_change` finding,
and full repository deduplication.

### Reproducible environment

The original minimal environment (`.venv`, pytest + genvm-linter
only) is preserved untouched. The reproducible environment is a
separate virtual environment, built from the official install
commands (`pip install genlayer-test` / `genvm-linter`, Python
3.12+; the docs give no fixed version, so the versions below are
the ones pip actually resolved):

```bash
python3 -m venv .venv-repro
.venv-repro/bin/pip install pytest genvm-linter genlayer-test
# genlayer-test 0.29.2, genlayer-py 0.16.3, genvm-linter 0.11.0,
# pytest 9.1.1, Python 3.12.3
.venv-repro/bin/python -m pytest tests -q
# 96 passed
.venv-repro/bin/genvm-lint check contracts/api_compat.py
# Lint passed (3 checks), Validation passed, 6 methods
```

The full pinned list is in `requirements.lock.txt`. It was
verified by installing it into a clean virtual environment
(`.venv-clean2`) and re-running the suite there: 98 passed
(96 stand-in + 2 direct-mode), lint passed. Neither
`.venv-repro` nor `.venv-clean2` is shipped in the
zip. (At first delivery the same check reported 74 passed;
that was the then-current suite size, not a different result.)

### Direct-mode smoke tests (real GenVM, in-process)

`tests_direct/test_direct_smoke.py` uses the genlayer-test direct
fixtures, not the stand-in in `tests/conftest.py`. It deploys the
real contract in-process and runs the bundled example with a
mocked LLM (empty findings), asserting BLOCKED with 3 breaking
findings. Result in this round: **2 passed in 56.90s**. Direct
mode makes no network call and no chain transaction, and its
mocked LLM is not real validator consensus.

One environment quirk is documented, not hidden: direct mode
first tried to re-download the GenVM v0.3.0-rc7 artifact and got
HTTP 404, even though the same artifact was already cached by
genvm-linter. Reusing that cached tarball locally
(`~/.cache/gltest-direct/genvm-universal-v0.3.0-rc7.tar.xz`,
copied from `~/.cache/genvm-linter/`) let the direct tests run.
A fresh machine may hit the same 404 and will need the same
workaround or a different GenVM version.

## Local compatibility check (no network, no keys)

```bash
python3 scripts/check_compatibility.py
```

This checks the GenVM dependency header, minimal imports, storage
types, public-method decorators and return types, containment of
non-determinism, and the pinned Studionet configuration. It does
not claim a linter result: run the official linter separately and
record its actual output (see `DEPLOY.md` for the current recorded
result).

```bash
genvm-lint check contracts/api_compat.py
```

The linter also notes a newer `py-genlayer` runner is available;
the contract keeps the runner pinned in the official documentation
examples for Stable Studionet, and that choice should be re-checked
at deployment time. `gltest` integration on Studionet is done
(see `evidence/EVIDENCE.md`); Studio-UI deployment remains pending.

## Call examples (no chain interaction)

```bash
python3 examples/call_examples.py
```

This only prints the arguments for `analyze_case` and friends, using
`examples/old_spec.json` and `examples/new_spec.json`. The bundled
pair is `BLOCKED` (3 breaking, 1 info): the `GET /users/{id}`
operation was removed, the `email` response field was removed, and a
required `tenant` request field was added; a new optional `search`
parameter is the additive info finding.

## Target network

Stable Studionet only, as pinned in `network.json`:

- RPC: `https://studio.genlayer.com/api`
- Chain ID: `61999`
- Currency: `GEN`
- Explorer: `https://explorer-studio.genlayer.com`
- Studio: `https://studio.genlayer.com`

Do not point the stable `studionet` preset at the Studio-dev preview
(chain ID `61997`); that is a different deployment. See the official
GenLayer documentation for the network table.

## Supported scope and known limits

Supported:

- OpenAPI 3 JSON only (YAML and Swagger 2 are rejected with
  `INVALID_SPEC`).
- Path-level parameters, merged into every operation under the path,
  with operation-level parameters winning on a name/location clash.
- Local `#/components/parameters/...`,
  `#/components/requestBodies/...`, and `#/components/responses/...`
  references, resolved with a cycle guard; an unresolvable reference
  is reported as a warning, not silently skipped.
- Local `#/components/schemas/...` references, resolved with a cycle
  guard and depth bound of 4.
- `allOf` subschemas, merged into the same field set.
- Request-body `required` changes and field/parameter `nullable`
  changes, diffed deterministically.
- `application/json` request schemas, and the first 2xx response
  JSON schema. Every 2xx response is still checked for media-type
  and reference warnings, even after the first JSON schema is found.
- Security scopes, for semantic-field association: a scope name is
  a valid semantic field only when it appears in the operation's
  effective security (an operation-level security list replaces
  the global list; `security: []` means anonymous). Security scope
  changes are also diffed deterministically: an added scope is
  `security_scope_added` (breaking), a removed scope is
  `security_scope_removed` (info).
- Non-2xx responses, for change detection only: their presence,
  media types, JSON schemas, and descriptions are recorded, but
  they are not diffed field by field. If a non-2xx response is
  added, removed, or changed, including a description-only change,
  the record gets a `unsupported_non_2xx_response`
  warning and is at least REVIEW. Unchanged non-2xx responses
  produce no warning, so a COMPATIBLE status means the error
  surface did not change in any detected way.

Explicitly not silently skipped (reported as deterministic warnings,
so the record is at least `REVIEW`, unless a breaking finding also
applies):

- Any non-JSON media type present on a request or response
  (`unsupported_media_type`), including a response with no content
  or no 2xx JSON schema at all, and a requestBody with no content.
- Additional 2xx JSON schemas beyond the first
  (`unsupported_multiple_responses`); only the first is diffed.
- `oneOf` / `anyOf` / `not` schema branches
  (`unsupported_schema_combination`); their branches are not diffed
  field by field.
- External, missing, or cyclic schema references
  (`unsupported_schema_ref`); the field is still recorded as an
  opaque `ref:` type for comparison, but the gap is warned.
- Schema nesting beyond the depth bound
  (`unsupported_schema_depth`).
- Unresolvable parameter, requestBody, or response references
  (`unsupported_parameter_ref`, `unsupported_request_body_ref`,
  `unsupported_response_ref`).
- Operation references and callbacks
  (`unsupported_operation_ref`, `unsupported_operation_structure`).

Rejected as invalid input, rather than silently ignored:

- Specs containing `webhooks` (not analysed).
- Path items that are references (operations cannot be determined).
- Non-JSON specs, non-OpenAPI-3 specs, specs without a `paths`
  object, specs with no operations, and specs over the size limit.

Limits:

- Each spec is capped at 12,000 characters, exactly the amount the
  LLM prompt retains, so a validated case's prompt contains the full
  spec text with no truncation. Larger APIs must be split into
  smaller submissions, for example one case per service or path
  group; this is a real limit, not a hidden one. Operations are
  capped at 200, semantic findings at 20, and the deterministic
  findings listed in the prompt are capped at 200 entries for prompt
  size (the full deterministic set is still used for filtering, so
  prompt truncation of that list cannot cause a duplicate finding).
- The fingerprint is FNV-1a, not SHA-256, by design (minimal import
  surface in the Studio file). Do not use it as a cryptographic
  commitment.
- Semantic evidence must be a verbatim excerpt of at least 5
  characters from the same operation, and the field must resolve to
  a parsed parameter, request field, response field, security scope,
  or referenced component for that operation. The evidence must
  also be about the claimed field and kind: evidence mentioning
  only other parsed fields is rejected, and evidence mentioning no
  parsed field is accepted only if it contains vocabulary for the
  claimed kind; an `auth_scope_tightened` finding's field must be
  a scope or `security`. A correct semantic observation quoted as
  a paraphrase, quoted from another operation, or naming a field
  with no parsed association will be dropped;
  this is a deliberate anti-hallucination trade-off.
- Enum values are compared with their type: float, int, string,
  and bool values are distinct, so shrinking a float enum is
  detected and 1 vs 1.0 vs true are not collapsed.
- Not diffed deterministically, and documented here rather than
  claimed: non-2xx response schemas (only their presence, media
  types, flattened JSON fields, and descriptions are compared, and
  a change produces a REVIEW warning, not a field-level finding), parameter
  `style` / `explode`, schema constraints other than type, format,
  enum, and nullable (such as `minimum`, `pattern`, or length
  bounds), schema `discriminator`, and `example` / `examples`
  values. A semantic finding may still report a change in one of
  these areas, but a deterministic finding is not guaranteed for
  it. Non-JSON non-2xx schema changes within the same media type
  are not detected by the media-type comparison.
- Prompt-boundary markers inside a spec are removed before the spec
  is embedded in the prompt, with a placeholder shorter than any
  marker it replaces, so sanitisation cannot push a spec over the
  size limit. The deterministic diff and the evidence check use
  the original spec text, so sanitisation cannot hide a real
  change.
- No frontend is included, by design. This is a reusable primitive,
  not a full application.

## Files

```
contracts/api_compat.py      # single-file GenLayer contract (deployable)
tests/conftest.py            # GenLayer stand-in + contract loader
tests/test_api_compat.py     # 96 tests with real assertions
tests_direct/test_direct_smoke.py  # 2 direct-mode tests, real GenVM
examples/old_spec.json       # bundled v1 example
examples/new_spec.json       # bundled v2 example (BLOCKED pair)
examples/call_examples.py    # printable call arguments, no chain use
scripts/check_compatibility.py  # offline static + config check
network.json                 # pinned Stable Studionet configuration
gltest.config.yaml           # gltest config, valid keys, no keys
requirements.lock.txt        # reproducible environment lock file
MECHANISM.md                 # full mechanism, tables, and reuse guide
DEPLOY.md                    # deployment steps, all marked NOT DONE here
```

## Originality and deduplication limits

A deduplication check was run on 2026-10-27 against what is
publicly accessible: all public repositories of `zuotu295`
(apicompat, erratascope-genlayer, citation-impact-primitive) and
of `halihalibt` (19 public repositories, none about OpenAPI
compatibility), plus a web search for GenLayer OpenAPI
compatibility contracts. No core-mechanism duplicate was found:
the closest results are off-chain OpenAPI diff tools (no GenLayer
consensus) and GenLayer projects in other domains (citation
impact, clause relations, policy drift, semantic exchange). This
is **not** a full deduplication: private repositories, the
GenLayer Portal submission list, and code-level search inside
other projects were not checked. The mechanism was chosen to differ
from the known projects named in the brief — BallotSeal,
CoreRelay, RecallScope, PatchDebt, GrantWeave, StepSpan,
TermFence, and ErrataScope — in domain (OpenAPI interface
compatibility, not voting, relaying, recalls, patch debt, grants,
steps, terms, or errata), in mechanism (a deterministic OpenAPI
diff that the LLM cannot override, plus a closed-kind semantic
layer and change-type consensus equivalence), and in state
machine (analyse → acknowledge → supersede). Before any
submission, a reviewer must still run the full repository search
listed in `DEPLOY.md` under "Pre-submission deduplication" and
confirm no existing project covers this exact primitive.

### Difference from a Protocol Consumer Compatibility Attestation

This note is written from the concept as named, because no
project by that exact name was located in memory, in the public
repositories checked above, or in a web search on 2026-10-27.
It therefore does not claim to describe any particular
implementation's code; if a reviewer means a specific
implementation, that repository must be named and this comparison
re-checked against its code. The conceptual difference is still
sharp, and it is the point an originality reviewer is most likely
to confuse:

- **Different subject.** An attestation answers, for a specific
  consumer, "does this protocol (or version) meet this
  consumer's requirements?" Its subject is a consumer +
  protocol pair, and its verdict is about that consumer. ApiCompat
  answers, for a producer's API, "is version N+1 compatible with
  version N for consumers in general?" Its subject is two versions
  of one OpenAPI document, and it takes no consumer identity and
  no consumer-registered requirements as input at all.
- **Different verdict meaning.** `BLOCKED` here means "do not
  release this API version without acknowledging the break"; it
  is not a statement that a particular consumer is or is not
  compatible, and `COMPATIBLE` here is not an attestation that any
  named consumer's requirements are met. A BLOCKED or COMPATIBLE
  verdict could be *used as input* to an attestation, but it is
  not itself one.
- **Different authority.** ApiCompat's verdict is driven by a
  deterministic spec-to-spec diff that the LLM cannot override,
  plus a bounded semantic layer. An attestation's authority comes
  from evidencing a claim about a consumer's requirements, which
  ApiCompat never collects, so the two cannot be the same
  mechanism with different labels.
- **Different lifecycle.** ApiCompat's state machine is
  analyse → acknowledge (BLOCKED only, owner, migration note) →
  supersede (to an existing successor case for the same API):
  a version chain. An attestation lifecycle is about issuing,
  relying on, and expiring a claim for a consumer, which ApiCompat
  has no concept of: it stores no consumer, no attestation, and
  no expiry.

In short: ApiCompat judges a spec change; an attestation judges a
consumer's fit to a protocol. Similar words ("compatibility",
"consumer"), different question, different inputs, different
verdict, different state.
