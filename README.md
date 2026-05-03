# z3ro-spec

`z3ro-spec` is a vulnerability-agnostic formal-spec assistant for smart-contract whitehat research.

It accepts a Glider result JSON file containing candidate Solidity functions and a free-form vulnerability description. Glider provides the initial candidate set; `z3ro-spec` removes obvious false positives, uses a lightweight triage LLM for relevance, expands verified source context from Etherscan, asks a stronger formal-verifier LLM to engineer a structured specification, and checks the encoded model locally with Z3.

Z3 runs through the local Python package `z3-solver`. It does not require an API key.

No output from this version is automatically a verified bug. A satisfiable Z3 result is reported as `possible_bug`, meaning the model admits a counterexample under the extracted assumptions. Human review is required.

## Install

```bash
uv sync --all-groups
```

Set environment variables:

```bash
cp .env.example .env
export ETHERSCAN_API_KEY=...
export ETHERSCAN_CHAIN_ID=1
export TRIAGE_LLM_API_KEY=...
export TRIAGE_LLM_BASE_URL=https://api.openai.com/v1
export TRIAGE_LLM_MODEL=...
export FORMAL_VERIFIER_LLM_API_KEY=...
export FORMAL_VERIFIER_LLM_BASE_URL=https://api.openai.com/v1
export FORMAL_VERIFIER_LLM_MODEL=...
export Z3RO_SPEC_LLM_TIMEOUT_SECONDS=300
export Z3RO_SPEC_ETHERSCAN_TIMEOUT_SECONDS=60
export Z3RO_SPEC_NETWORK_RETRIES=2
```

`z3ro-spec` also reads `.env` from the project directory, so exporting is optional when running
from the project root. Exported variables override `.env` values.

## Commands

Put the vulnerability description in a text file:

```bash
cat > vuln.txt <<'EOF'
borrow must not make health factor fall below MIN_HEALTH_FACTOR
EOF
```

Run the full pipeline:

```bash
uv run z3ro-spec scan results.json \
  --vulnerability vuln.txt \
  --top-candidates 5 \
  --min-value 0 \
  --out reports/
```

Skip lightweight LLM triage and send deterministic, value-positive candidates directly to formal verification:

```bash
uv run z3ro-spec scan results.json \
  --vulnerability vuln.txt \
  --verify \
  --top-candidates 5 \
  --min-value 0 \
  --out reports/
```

Run deterministic filters plus lightweight LLM triage:

```bash
uv run z3ro-spec triage results.json \
  --vulnerability vuln.txt \
  --top-candidates 5 \
  --min-value 0 \
  --out triaged.json
```

Fetch verified source and ABI from Etherscan:

```bash
uv run z3ro-spec fetch-source 0xContractAddress --out cache/
```

Generate structured formal specifications without running Z3:

```bash
uv run z3ro-spec spec results.json \
  --vulnerability vuln.txt \
  --top-candidates 5 \
  --min-value 0 \
  --out specs/
```

Run Z3 against a generated or manually edited spec:

```bash
uv run z3ro-spec verify spec.json --out reports/
```

## Pipeline

1. Load Glider JSON candidate functions.
2. Normalize each candidate's Glider `value`.
3. Exclude candidates where `value <= --min-value`.
4. Sort remaining candidates by value descending.
5. Remove obvious false positives using deterministic filters.
6. Ask a cheap triage LLM whether each value-positive candidate is relevant.
7. Select the top high-value candidates with `keep=true` and high or medium confidence.
8. Fetch verified source and ABI from Etherscan only for selected candidates.
9. Build heuristic source context around target functions, callees, declarations, modifiers, constants, and relevant helpers.
10. Ask the formal-verifier LLM to return strict JSON matching `FormalSpec`.
11. Encode supported formulas with a small expression parser and generic Z3 templates.
12. Run Z3 locally.
13. Produce `report.json` and `report.md`.

The v1 source context builder uses regex and brace matching. It includes TODO markers for replacing this with Slither later.

## TVL/value prioritization

`z3ro-spec` assumes Glider's `value` field represents TVL, protocol value, or another impact proxy.
By default, candidates with `value <= 0` are excluded before deterministic filtering and LLM triage.
Missing, null, invalid, or non-numeric values are excluded by default. Use `--allow-missing-value`
to allow missing-value candidates through triage with `normalized_value=0`; they still are not eligible
for final top-candidate selection unless they have positive value.

The tool processes only the top 5 high-value relevant candidates unless changed with
`--top-candidates`. This saves LLM cost and focuses whitehat review on impactful targets.
Use `--min-value` to raise the exclusion threshold.

```bash
uv run z3ro-spec scan output.json \
  --vulnerability vuln.txt \
  --top-candidates 5 \
  --min-value 0 \
  --out reports/
```

```bash
uv run z3ro-spec scan output.json \
  --vulnerability vuln.txt \
  --top-candidates 10 \
  --min-value 100000 \
  --out reports/high-value-vaults/
```

## On-chain parameter resolution

When verified ABI is available, `scan` and `spec` attempt to read relevant zero-argument
configuration getters through Etherscan `eth_call`. This is useful for liquidation bugs where
deployed values such as `collateralFactorBps`, `liquidationIncentiveBps`,
`liquidationFeeBps`, `liquidationFactorBps`, `closeFactor`, or `lltv` determine whether a
symbolic counterexample applies to the live market.

Resolved values are added to the formal-spec prompt, injected as concrete Z3 preconditions, and
included in reports under `onchain_parameters`.

## Limitations

The Z3 engine is intentionally small. It supports integer and boolean variables, arithmetic, comparisons, `and`, `or`, `not`, `min`, `max`, `floor_div`, `ceil_div`, and `implies`. It does not compile Solidity or model EVM semantics. Unsupported expressions are reported as `unsupported` or `model_incomplete`.
