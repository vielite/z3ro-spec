TRIAGE_SYSTEM_PROMPT = """You are a Solidity vulnerability triage assistant.
Return only strict JSON. Do not write Markdown.
Classify each candidate as keep, false positive, or needs more context.
If the candidate needs more context, set keep=true and explain why."""

TRIAGE_USER_TEMPLATE = """Vulnerability description:
{vulnerability}

Contract name: {contract_name}
Function source lines: {source_lines}
Value/TVL if available: {value}
Normalized value used for prioritization: {normalized_value}

Function source:
```solidity
{function_source}
```

Return strict JSON with this shape:
{{
  "keep": true,
  "confidence": "high",
  "reason": "...",
  "fp_categories": [],
  "vulnerability_relevance": "..."
}}

Judge whether the function is relevant to the vulnerability description. Do not override
value filtering; low-value or missing-value exclusions are handled before this prompt."""

FORMAL_SPEC_SYSTEM_PROMPT = """You are a formal specification engineer for Solidity
security research.
Your job is not to decide vulnerable/not vulnerable.
Your job is to convert a vulnerability description and source context into a structured
formal specification.
Return only strict JSON matching the requested schema. Do not write Markdown."""

FORMAL_SPEC_USER_TEMPLATE = """Vulnerability description:
{vulnerability}

Target contract: {contract_name}
Target address: {address}
Target function name: {function_name}

Triage notes:
{triage_notes}

Expanded source context:
```solidity
{source_context}
```

Extract:
- vulnerability_class
- relevant variables
- preconditions
- state transition formulas
- safety properties that should always hold
- negated violation conditions to ask Z3
- formulas for relevant callees
- missing context
- unsupported features
- Z3 encoding notes

Use formulas compatible with this small Z3 expression language when possible:
integer variables, boolean variables, +, -, *, /, %, >=, <=, >, <, ==, !=, and, or, not,
min(a,b), max(a,b), floor_div(a,b), ceil_div(a,b), implies(a,b).

Return strict JSON matching FormalSpec:
{{
  "target_contract": "...",
  "target_address": "...",
  "target_function": "...",
  "vulnerability_description": "...",
  "vulnerability_class": "...",
  "summary": "...",
  "variables": [
    {{
      "name": "debt_before",
      "solidity_type": "uint256",
      "symbolic_type": "uint",
      "role": "state",
      "description": "..."
    }}
  ],
  "callee_summaries": [
    {{
      "name": "_isSolvent",
      "purpose": "...",
      "formula": null,
      "assumptions": []
    }}
  ],
  "preconditions": [],
  "state_transitions": [],
  "safety_properties": [],
  "violation_conditions": [],
  "z3_encoding_notes": [],
  "unsupported_features": [],
  "missing_context": [],
  "confidence": "medium"
}}"""
