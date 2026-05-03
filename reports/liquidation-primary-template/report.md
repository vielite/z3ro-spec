# z3ro-spec Report

## Candidate Prioritization

- Total input candidates: `10`
- Excluded due to missing invalid zero or low value: `0`
- Remaining after value filter: `10`
- Excluded by deterministic filters: `0`
- Excluded by llm triage: `0`
- Not evaluated after top candidates selected: `0`
- Selected for formal verification: `10`
- Top candidates requested: `10`
- Min value: `0.0`
- Llm triage skipped: `1`

### Selected Candidates

- Rank `1`: `0x4e264618dc015219cd83dbc53b31251d73c2db1a` (Market), value `2285980.895498516`, confidence `high`, reason: LLM triage skipped; deterministic filters passed
- Rank `2`: `0xd68d3a44d46dd50bfeba8cca544717b76e7c4b29` (Market), value `2114714.90508023`, confidence `high`, reason: LLM triage skipped; deterministic filters passed
- Rank `3`: `0x63df5e23db45a2066508318f172ba45b9cd37035` (Market), value `1955142.740541187`, confidence `high`, reason: LLM triage skipped; deterministic filters passed
- Rank `4`: `0x48ba574edf0bc4e2e40b529863aaa6a67c264e7c` (Market), value `1786388.3553120447`, confidence `high`, reason: LLM triage skipped; deterministic filters passed
- Rank `5`: `0x3fd3dabb9f9480621c8a111603d3ba70f17550bc` (Market), value `1337554.0350286516`, confidence `high`, reason: LLM triage skipped; deterministic filters passed
- Rank `6`: `0xe4d47ef77ac2c3fa4019cd169ac1dd9e27cb12e4` (Market), value `674314.8004320001`, confidence `high`, reason: LLM triage skipped; deterministic filters passed
- Rank `7`: `0xdc2265cbd15bed67b5f2c0b82e23fce4a07ddf6b` (Market), value `414000.2793634608`, confidence `high`, reason: LLM triage skipped; deterministic filters passed
- Rank `8`: `0xb427fc22561f3963b04202f9bb5bcebd76c14a99` (Market), value `7204.600379733712`, confidence `high`, reason: LLM triage skipped; deterministic filters passed
- Rank `9`: `0xb8bc1e9c0a2d445bc39d2a745f47619e954dd565` (Market), value `5877.834750506076`, confidence `high`, reason: LLM triage skipped; deterministic filters passed
- Rank `10`: `0xb516247596ca36bf32876199fbdcad6b3322330b` (Market), value `4035.8135384549373`, confidence `high`, reason: LLM triage skipped; deterministic filters passed

### Excluded Candidates

- None

## 1. Market

- Contract address: `0x4e264618dc015219cd83dbc53b31251d73c2db1a`
- Function source lines: `(653, 680)`
- Value/TVL: `2285980.895498516`
- Vulnerability: Partial liquidation must not create bad debt: collateralFactorBps *
  (10000 + liquidationIncentiveBps + liquidationFeeBps) must be < 10000^2 for any
  partial repay where debt_before > creditLimit_before, repaidDebt > 0, repaidDebt <
  debt_before, and liquidation must reduce the debt-creditLimit gap rather than exhaust
  collateral while debt remains.

### Triage

- Keep: `True`
- Confidence: `high`
- Reason: LLM triage skipped; deterministic filters passed
- FP categories: `[]`
- Relevance: Candidate selected for formal verification without LLM triage.

### Formal Spec

- Summary: A partial liquidation can leave a borrower with less collateral relative to their remaining debt than before the liquidation, creating bad debt. This happens when the collateral removed (liquidator reward + fee) exceeds the proportional collateral freed by the debt repaid. The invariant collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps) < 10000^2 must hold to prevent this.
- Missing context: `[]`
- Unsupported features: `[]`
- Safety properties: `['collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps) < 100000000', 'gap_after < gap_before', 'implies(debt_after > 0, collateral_after > 0)']`
- Violation conditions: `['collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps) >= 100000000']`

### On-Chain Parameters

- `collateralFactorBps`: `9200`
- `liquidationFactorBps`: `10000`
- `liquidationFeeBps`: `0`
- `liquidationIncentiveBps`: `400`

### Z3 Result

- Status: `not_proven`
- Solver status: `unsat`
- Counterexample: `None`
- Explanation: Z3 could not satisfy the violation condition under the encoded model.
- Warnings: `[]`

### Limitations

- Z3 checks only the encoded formal model, not full Solidity or EVM semantics.
- sat means possible_bug, never verified_bug.
- Heuristic source slicing may miss relevant context until Slither integration is added.

### Recommended Manual Review Steps

- Review missing_context and unsupported_features before trusting solver output.
- Compare each formula against Solidity source and protocol documentation.
- Manually validate any counterexample against real units, rounding, and access control.

## 2. Market

- Contract address: `0xd68d3a44d46dd50bfeba8cca544717b76e7c4b29`
- Function source lines: `(653, 680)`
- Value/TVL: `2114714.90508023`
- Vulnerability: Partial liquidation must not create bad debt: collateralFactorBps *
  (10000 + liquidationIncentiveBps + liquidationFeeBps) must be < 10000^2 for any
  partial repay where debt_before > creditLimit_before, repaidDebt > 0, repaidDebt <
  debt_before, and liquidation must reduce the debt-creditLimit gap rather than exhaust
  collateral while debt remains.

### Triage

- Keep: `True`
- Confidence: `high`
- Reason: LLM triage skipped; deterministic filters passed
- FP categories: `[]`
- Relevance: Candidate selected for formal verification without LLM triage.

### Formal Spec

- Summary: A partial liquidation can create bad debt if the collateral removed (liquidator reward + fee) exceeds the proportional reduction in the debt-credit gap. This happens when collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps) >= 10000^2, allowing a user to remain underwater after liquidation with less collateral, eventually exhausting collateral while debt remains.
- Missing context: `[]`
- Unsupported features: `[]`
- Safety properties: `['collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps) < 100000000', 'gap_after < gap_before', 'implies(debt_after > 0, collateral_after > 0)']`
- Violation conditions: `['collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps) >= 100000000']`

### On-Chain Parameters

- `collateralFactorBps`: `9000`
- `liquidationFactorBps`: `10000`
- `liquidationFeeBps`: `0`
- `liquidationIncentiveBps`: `500`

### Z3 Result

- Status: `unsupported`
- Solver status: `not_run`
- Counterexample: `None`
- Explanation: Unknown symbol: user
- Warnings: `[]`

### Limitations

- Z3 checks only the encoded formal model, not full Solidity or EVM semantics.
- sat means possible_bug, never verified_bug.
- Heuristic source slicing may miss relevant context until Slither integration is added.

### Recommended Manual Review Steps

- Review missing_context and unsupported_features before trusting solver output.
- Compare each formula against Solidity source and protocol documentation.
- Manually validate any counterexample against real units, rounding, and access control.

## 3. Market

- Contract address: `0x63df5e23db45a2066508318f172ba45b9cd37035`
- Function source lines: `(608, 632)`
- Value/TVL: `1955142.740541187`
- Vulnerability: Partial liquidation must not create bad debt: collateralFactorBps *
  (10000 + liquidationIncentiveBps + liquidationFeeBps) must be < 10000^2 for any
  partial repay where debt_before > creditLimit_before, repaidDebt > 0, repaidDebt <
  debt_before, and liquidation must reduce the debt-creditLimit gap rather than exhaust
  collateral while debt remains.

### Triage

- Keep: `True`
- Confidence: `high`
- Reason: LLM triage skipped; deterministic filters passed
- FP categories: `[]`
- Relevance: Candidate selected for formal verification without LLM triage.

### Formal Spec

- Summary: A partial liquidation can create bad debt if the collateral removed (liquidator reward + fee) exceeds the proportional reduction in the debt-to-credit-limit gap. This occurs when collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps) >= 10000^2, meaning the user's position becomes more underwater after the liquidation than before it.
- Missing context: `[]`
- Unsupported features: `[]`
- Safety properties: `['collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps) < 100000000', 'gap_after < gap_before', 'implies(debt_after > 0, collateral_after > 0)']`
- Violation conditions: `['collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps) >= 100000000']`

### On-Chain Parameters

- `collateralFactorBps`: `8500`
- `liquidationFactorBps`: `7500`
- `liquidationFeeBps`: `0`
- `liquidationIncentiveBps`: `1000`

### Z3 Result

- Status: `not_proven`
- Solver status: `unsat`
- Counterexample: `None`
- Explanation: Z3 could not satisfy the violation condition under the encoded model.
- Warnings: `[]`

### Limitations

- Z3 checks only the encoded formal model, not full Solidity or EVM semantics.
- sat means possible_bug, never verified_bug.
- Heuristic source slicing may miss relevant context until Slither integration is added.

### Recommended Manual Review Steps

- Review missing_context and unsupported_features before trusting solver output.
- Compare each formula against Solidity source and protocol documentation.
- Manually validate any counterexample against real units, rounding, and access control.

## 4. Market

- Contract address: `0x48ba574edf0bc4e2e40b529863aaa6a67c264e7c`
- Function source lines: `(671, 698)`
- Value/TVL: `1786388.3553120447`
- Vulnerability: Partial liquidation must not create bad debt: collateralFactorBps *
  (10000 + liquidationIncentiveBps + liquidationFeeBps) must be < 10000^2 for any
  partial repay where debt_before > creditLimit_before, repaidDebt > 0, repaidDebt <
  debt_before, and liquidation must reduce the debt-creditLimit gap rather than exhaust
  collateral while debt remains.

### Triage

- Keep: `True`
- Confidence: `high`
- Reason: LLM triage skipped; deterministic filters passed
- FP categories: `[]`
- Relevance: Candidate selected for formal verification without LLM triage.

### Formal Spec

- Summary: A partial liquidation can create bad debt if the collateral removed from the user's escrow (to pay the liquidator reward and fee) is disproportionately larger than the debt repaid. This happens when collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps) >= 10000^2, meaning the user's debt-to-credit-limit gap increases after liquidation instead of decreasing, eventually exhausting collateral while debt remains.
- Missing context: `[]`
- Unsupported features: `[]`
- Safety properties: `['collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps) < 100000000', 'gap_after < gap_before', 'implies(debt_after > 0, collateral_after > 0)']`
- Violation conditions: `['collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps) >= 100000000']`

### On-Chain Parameters

- `collateralFactorBps`: `8500`
- `liquidationFactorBps`: `7500`
- `liquidationFeeBps`: `0`
- `liquidationIncentiveBps`: `1000`

### Z3 Result

- Status: `not_proven`
- Solver status: `unsat`
- Counterexample: `None`
- Explanation: Z3 could not satisfy the violation condition under the encoded model.
- Warnings: `[]`

### Limitations

- Z3 checks only the encoded formal model, not full Solidity or EVM semantics.
- sat means possible_bug, never verified_bug.
- Heuristic source slicing may miss relevant context until Slither integration is added.

### Recommended Manual Review Steps

- Review missing_context and unsupported_features before trusting solver output.
- Compare each formula against Solidity source and protocol documentation.
- Manually validate any counterexample against real units, rounding, and access control.

## 5. Market

- Contract address: `0x3fd3dabb9f9480621c8a111603d3ba70f17550bc`
- Function source lines: `(671, 698)`
- Value/TVL: `1337554.0350286516`
- Vulnerability: Partial liquidation must not create bad debt: collateralFactorBps *
  (10000 + liquidationIncentiveBps + liquidationFeeBps) must be < 10000^2 for any
  partial repay where debt_before > creditLimit_before, repaidDebt > 0, repaidDebt <
  debt_before, and liquidation must reduce the debt-creditLimit gap rather than exhaust
  collateral while debt remains.

### Triage

- Keep: `True`
- Confidence: `high`
- Reason: LLM triage skipped; deterministic filters passed
- FP categories: `[]`
- Relevance: Candidate selected for formal verification without LLM triage.

### Formal Spec

- Summary: The liquidation function can create bad debt during a partial liquidation if the combined liquidation incentive and fee parameters are too high relative to the collateral factor. Specifically, if collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps) >= 10000^2, the collateral removed from the user's escrow to pay the liquidator reward and fee is disproportionately large compared to the debt repaid, potentially leaving the user with debt exceeding their new credit limit (bad debt).
- Missing context: `[]`
- Unsupported features: `[]`
- Safety properties: `['collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps) < 100000000', 'gap_after < gap_before', 'implies(debt_after > 0, collateral_after > 0)']`
- Violation conditions: `['collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps) >= 100000000']`

### On-Chain Parameters

- `collateralFactorBps`: `8500`
- `liquidationFactorBps`: `7500`
- `liquidationFeeBps`: `0`
- `liquidationIncentiveBps`: `1000`

### Z3 Result

- Status: `not_proven`
- Solver status: `unsat`
- Counterexample: `None`
- Explanation: Z3 could not satisfy the violation condition under the encoded model.
- Warnings: `[]`

### Limitations

- Z3 checks only the encoded formal model, not full Solidity or EVM semantics.
- sat means possible_bug, never verified_bug.
- Heuristic source slicing may miss relevant context until Slither integration is added.

### Recommended Manual Review Steps

- Review missing_context and unsupported_features before trusting solver output.
- Compare each formula against Solidity source and protocol documentation.
- Manually validate any counterexample against real units, rounding, and access control.

## 6. Market

- Contract address: `0xe4d47ef77ac2c3fa4019cd169ac1dd9e27cb12e4`
- Function source lines: `(653, 680)`
- Value/TVL: `674314.8004320001`
- Vulnerability: Partial liquidation must not create bad debt: collateralFactorBps *
  (10000 + liquidationIncentiveBps + liquidationFeeBps) must be < 10000^2 for any
  partial repay where debt_before > creditLimit_before, repaidDebt > 0, repaidDebt <
  debt_before, and liquidation must reduce the debt-creditLimit gap rather than exhaust
  collateral while debt remains.

### Triage

- Keep: `True`
- Confidence: `high`
- Reason: LLM triage skipped; deterministic filters passed
- FP categories: `[]`
- Relevance: Candidate selected for formal verification without LLM triage.

### Formal Spec

- Summary: Partial liquidation can create bad debt if the collateral removed (including liquidator incentive and fee) exceeds the proportional reduction in debt relative to the credit limit. This occurs if collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps) >= 10000^2, meaning the user's position becomes more underwater after a partial liquidation.
- Missing context: `[]`
- Unsupported features: `[]`
- Safety properties: `['collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps) < 100000000', 'gap_after < gap_before', 'implies(debt_after > 0, collateral_after > 0)']`
- Violation conditions: `['collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps) >= 100000000']`

### On-Chain Parameters

- `collateralFactorBps`: `9000`
- `liquidationFactorBps`: `10000`
- `liquidationFeeBps`: `0`
- `liquidationIncentiveBps`: `500`

### Z3 Result

- Status: `not_proven`
- Solver status: `unsat`
- Counterexample: `None`
- Explanation: Z3 could not satisfy the violation condition under the encoded model.
- Warnings: `[]`

### Limitations

- Z3 checks only the encoded formal model, not full Solidity or EVM semantics.
- sat means possible_bug, never verified_bug.
- Heuristic source slicing may miss relevant context until Slither integration is added.

### Recommended Manual Review Steps

- Review missing_context and unsupported_features before trusting solver output.
- Compare each formula against Solidity source and protocol documentation.
- Manually validate any counterexample against real units, rounding, and access control.

## 7. Market

- Contract address: `0xdc2265cbd15bed67b5f2c0b82e23fce4a07ddf6b`
- Function source lines: `(658, 685)`
- Value/TVL: `414000.2793634608`
- Vulnerability: Partial liquidation must not create bad debt: collateralFactorBps *
  (10000 + liquidationIncentiveBps + liquidationFeeBps) must be < 10000^2 for any
  partial repay where debt_before > creditLimit_before, repaidDebt > 0, repaidDebt <
  debt_before, and liquidation must reduce the debt-creditLimit gap rather than exhaust
  collateral while debt remains.

### Triage

- Keep: `True`
- Confidence: `high`
- Reason: LLM triage skipped; deterministic filters passed
- FP categories: `[]`
- Relevance: Candidate selected for formal verification without LLM triage.

### Formal Spec

- Summary: A partial liquidation can create bad debt if the collateral removed (liquidator reward + fee) exceeds the proportional collateral backing the repaid debt. This happens when collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps) >= 10000^2, causing the post-liquidation debt to exceed the post-liquidation credit limit even though pre-liquidation debt exceeded the pre-liquidation credit limit.
- Missing context: `[]`
- Unsupported features: `[]`
- Safety properties: `['collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps) < 100000000', 'gap_after < gap_before', 'implies(debt_after > 0, collateral_after > 0)']`
- Violation conditions: `['collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps) >= 100000000']`

### On-Chain Parameters

- `collateralFactorBps`: `6500`
- `liquidationFactorBps`: `10000`
- `liquidationFeeBps`: `0`
- `liquidationIncentiveBps`: `1000`

### Z3 Result

- Status: `not_proven`
- Solver status: `unsat`
- Counterexample: `None`
- Explanation: Z3 could not satisfy the violation condition under the encoded model.
- Warnings: `[]`

### Limitations

- Z3 checks only the encoded formal model, not full Solidity or EVM semantics.
- sat means possible_bug, never verified_bug.
- Heuristic source slicing may miss relevant context until Slither integration is added.

### Recommended Manual Review Steps

- Review missing_context and unsupported_features before trusting solver output.
- Compare each formula against Solidity source and protocol documentation.
- Manually validate any counterexample against real units, rounding, and access control.

## 8. Market

- Contract address: `0xb427fc22561f3963b04202f9bb5bcebd76c14a99`
- Function source lines: `(653, 680)`
- Value/TVL: `7204.600379733712`
- Vulnerability: Partial liquidation must not create bad debt: collateralFactorBps *
  (10000 + liquidationIncentiveBps + liquidationFeeBps) must be < 10000^2 for any
  partial repay where debt_before > creditLimit_before, repaidDebt > 0, repaidDebt <
  debt_before, and liquidation must reduce the debt-creditLimit gap rather than exhaust
  collateral while debt remains.

### Triage

- Keep: `True`
- Confidence: `high`
- Reason: LLM triage skipped; deterministic filters passed
- FP categories: `[]`
- Relevance: Candidate selected for formal verification without LLM triage.

### Formal Spec

- Summary: A partial liquidation can create bad debt if the collateral removed from the user's escrow (to pay the liquidator incentive and governance fee) is disproportionately larger than the debt repaid. If collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps) >= 10000^2, the user's debt can remain above their credit limit after liquidation, and the gap between debt and credit limit can widen, eventually exhausting collateral while debt remains.
- Missing context: `[]`
- Unsupported features: `[]`
- Safety properties: `['collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps) < 100000000', 'gap_after < gap_before', 'implies(debt_after > 0, collateral_after > 0)']`
- Violation conditions: `['collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps) >= 100000000']`

### On-Chain Parameters

- `collateralFactorBps`: `9200`
- `liquidationFactorBps`: `10000`
- `liquidationFeeBps`: `0`
- `liquidationIncentiveBps`: `400`

### Z3 Result

- Status: `not_proven`
- Solver status: `unsat`
- Counterexample: `None`
- Explanation: Z3 could not satisfy the violation condition under the encoded model.
- Warnings: `[]`

### Limitations

- Z3 checks only the encoded formal model, not full Solidity or EVM semantics.
- sat means possible_bug, never verified_bug.
- Heuristic source slicing may miss relevant context until Slither integration is added.

### Recommended Manual Review Steps

- Review missing_context and unsupported_features before trusting solver output.
- Compare each formula against Solidity source and protocol documentation.
- Manually validate any counterexample against real units, rounding, and access control.

## 9. Market

- Contract address: `0xb8bc1e9c0a2d445bc39d2a745f47619e954dd565`
- Function source lines: `(653, 680)`
- Value/TVL: `5877.834750506076`
- Vulnerability: Partial liquidation must not create bad debt: collateralFactorBps *
  (10000 + liquidationIncentiveBps + liquidationFeeBps) must be < 10000^2 for any
  partial repay where debt_before > creditLimit_before, repaidDebt > 0, repaidDebt <
  debt_before, and liquidation must reduce the debt-creditLimit gap rather than exhaust
  collateral while debt remains.

### Triage

- Keep: `True`
- Confidence: `high`
- Reason: LLM triage skipped; deterministic filters passed
- FP categories: `[]`
- Relevance: Candidate selected for formal verification without LLM triage.

### Formal Spec

- Summary: The liquidation function can create bad debt during a partial liquidation if the collateral removed (due to liquidator reward and fee) is disproportionately larger than the debt repaid. This occurs if collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps) >= 10000^2, meaning the user's remaining debt can exceed their remaining credit limit after a partial liquidation.
- Missing context: `[]`
- Unsupported features: `[]`
- Safety properties: `['collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps) < 100000000', 'gap_after < gap_before', 'implies(debt_after > 0, collateral_after > 0)']`
- Violation conditions: `['collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps) >= 100000000']`

### On-Chain Parameters

- `collateralFactorBps`: `8750`
- `liquidationFactorBps`: `10000`
- `liquidationFeeBps`: `0`
- `liquidationIncentiveBps`: `650`

### Z3 Result

- Status: `not_proven`
- Solver status: `unsat`
- Counterexample: `None`
- Explanation: Z3 could not satisfy the violation condition under the encoded model.
- Warnings: `[]`

### Limitations

- Z3 checks only the encoded formal model, not full Solidity or EVM semantics.
- sat means possible_bug, never verified_bug.
- Heuristic source slicing may miss relevant context until Slither integration is added.

### Recommended Manual Review Steps

- Review missing_context and unsupported_features before trusting solver output.
- Compare each formula against Solidity source and protocol documentation.
- Manually validate any counterexample against real units, rounding, and access control.

## 10. Market

- Contract address: `0xb516247596ca36bf32876199fbdcad6b3322330b`
- Function source lines: `(658, 685)`
- Value/TVL: `4035.8135384549373`
- Vulnerability: Partial liquidation must not create bad debt: collateralFactorBps *
  (10000 + liquidationIncentiveBps + liquidationFeeBps) must be < 10000^2 for any
  partial repay where debt_before > creditLimit_before, repaidDebt > 0, repaidDebt <
  debt_before, and liquidation must reduce the debt-creditLimit gap rather than exhaust
  collateral while debt remains.

### Triage

- Keep: `True`
- Confidence: `high`
- Reason: LLM triage skipped; deterministic filters passed
- FP categories: `[]`
- Relevance: Candidate selected for formal verification without LLM triage.

### Formal Spec

- Summary: The liquidation function calculates the liquidator reward and fee based on the repaid debt, which removes collateral from the escrow. If the combined liquidation incentive and fee parameters are too high relative to the collateral factor, a partial liquidation can remove more collateral value than the debt repaid, leaving the user with debt exceeding their credit limit (bad debt).
- Missing context: `[]`
- Unsupported features: `[]`
- Safety properties: `['collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps) < 100000000', 'gap_after < gap_before', 'implies(debt_after > 0, collateral_after > 0)']`
- Violation conditions: `['collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps) >= 100000000']`

### On-Chain Parameters

- `collateralFactorBps`: `3000`
- `liquidationFactorBps`: `5000`
- `liquidationFeeBps`: `0`
- `liquidationIncentiveBps`: `1000`

### Z3 Result

- Status: `not_proven`
- Solver status: `unsat`
- Counterexample: `None`
- Explanation: Z3 could not satisfy the violation condition under the encoded model.
- Warnings: `[]`

### Limitations

- Z3 checks only the encoded formal model, not full Solidity or EVM semantics.
- sat means possible_bug, never verified_bug.
- Heuristic source slicing may miss relevant context until Slither integration is added.

### Recommended Manual Review Steps

- Review missing_context and unsupported_features before trusting solver output.
- Compare each formula against Solidity source and protocol documentation.
- Manually validate any counterexample against real units, rounding, and access control.
