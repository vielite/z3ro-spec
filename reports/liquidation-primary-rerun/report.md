# z3ro-spec Report

## Candidate Prioritization

- Total input candidates: `10`
- Excluded due to missing invalid zero or low value: `0`
- Remaining after value filter: `10`
- Excluded by deterministic filters: `0`
- Excluded by llm triage: `0`
- Not evaluated after top candidates selected: `5`
- Selected for formal verification: `5`
- Top candidates requested: `5`
- Min value: `0.0`
- Llm triage skipped: `1`

### Selected Candidates

- Rank `1`: `0x4e264618dc015219cd83dbc53b31251d73c2db1a` (Market), value `2285980.895498516`, confidence `high`, reason: LLM triage skipped; deterministic filters passed
- Rank `2`: `0xd68d3a44d46dd50bfeba8cca544717b76e7c4b29` (Market), value `2114714.90508023`, confidence `high`, reason: LLM triage skipped; deterministic filters passed
- Rank `3`: `0x63df5e23db45a2066508318f172ba45b9cd37035` (Market), value `1955142.740541187`, confidence `high`, reason: LLM triage skipped; deterministic filters passed
- Rank `4`: `0x48ba574edf0bc4e2e40b529863aaa6a67c264e7c` (Market), value `1786388.3553120447`, confidence `high`, reason: LLM triage skipped; deterministic filters passed
- Rank `5`: `0x3fd3dabb9f9480621c8a111603d3ba70f17550bc` (Market), value `1337554.0350286516`, confidence `high`, reason: LLM triage skipped; deterministic filters passed

### Excluded Candidates

- `0xe4d47ef77ac2c3fa4019cd169ac1dd9e27cb12e4` (Market), value `674314.8004320001`, reason: not_evaluated_after_top_candidates_selected
- `0xdc2265cbd15bed67b5f2c0b82e23fce4a07ddf6b` (Market), value `414000.2793634608`, reason: not_evaluated_after_top_candidates_selected
- `0xb427fc22561f3963b04202f9bb5bcebd76c14a99` (Market), value `7204.600379733712`, reason: not_evaluated_after_top_candidates_selected
- `0xb8bc1e9c0a2d445bc39d2a745f47619e954dd565` (Market), value `5877.834750506076`, reason: not_evaluated_after_top_candidates_selected
- `0xb516247596ca36bf32876199fbdcad6b3322330b` (Market), value `4035.8135384549373`, reason: not_evaluated_after_top_candidates_selected

## 1. Market

- Contract address: `0x4e264618dc015219cd83dbc53b31251d73c2db1a`
- Function source lines: `(653, 680)`
- Value/TVL: `2285980.895498516`
- Vulnerability: Partial liquidation must not create bad debt: collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps)
  must be < 10000^2, gap_after must be < gap_before, and liquidation must not exhaust collateral while debt remains.

### Triage

- Keep: `True`
- Confidence: `high`
- Reason: LLM triage skipped; deterministic filters passed
- FP categories: `[]`
- Relevance: Candidate selected for formal verification without LLM triage.

### Formal Spec

- Summary: Fallback spec created because formal-verifier LLM output could not be validated.
- Missing context: `['formal verifier LLM output', 'formal verifier LLM failed: LLM request failed for model z-ai/glm-5.1 after 3 attempt(s): The read operation timed out']`
- Unsupported features: `[]`
- Safety properties: `[]`
- Violation conditions: `[]`

### On-Chain Parameters

- `collateralFactorBps`: `9200`
- `liquidationFactorBps`: `10000`
- `liquidationFeeBps`: `0`
- `liquidationIncentiveBps`: `400`

### Z3 Result

- Status: `model_incomplete`
- Solver status: `not_run`
- Counterexample: `None`
- Explanation: Spec has no violation conditions to assert.
- Warnings: `['missing violation_conditions']`

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
- Vulnerability: Partial liquidation must not create bad debt: collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps)
  must be < 10000^2, gap_after must be < gap_before, and liquidation must not exhaust collateral while debt remains.

### Triage

- Keep: `True`
- Confidence: `high`
- Reason: LLM triage skipped; deterministic filters passed
- FP categories: `[]`
- Relevance: Candidate selected for formal verification without LLM triage.

### Formal Spec

- Summary: The liquidation function can create bad debt if the combination of collateralFactorBps, liquidationIncentiveBps, and liquidationFeeBps is too high, allowing a partial liquidation to remove more collateral value than the debt repaid, worsening the user's health factor. With on-chain parameters collateralFactorBps=9000, liquidationIncentiveBps>0, and liquidationFeeBps=0, the invariant collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps) < 10000^2 is violated, meaning partial liquidations increase the debt-to-collateral ratio.
- Missing context: `['Exact on-chain value of liquidationIncentiveBps is not provided in the resolved parameters, only that it is > 0', 'Implementation of escrow.pay and whether it reverts on insufficient balance', 'Oracle price feed implementation and potential manipulation vectors']`
- Unsupported features: `['External calls to oracle, escrow, dbr, borrowController, and dola are abstracted; their side effects are assumed to follow the summaries', 'Reentrancy via external calls is not modeled', 'DBR deficit mechanics and their effect on debt accrual are not modeled']`
- Safety properties: `['collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps) < 10000 * 10000', 'gap_after < gap_before', 'not (debt_after > 0 and collateralBalance_after == 0)', 'creditLimit_after >= debt_after']`
- Violation conditions: `['collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps) >= 10000 * 10000', 'gap_after >= gap_before', 'debt_after > 0 and collateralBalance_after == 0', 'debt_after > creditLimit_after']`

### On-Chain Parameters

- `collateralFactorBps`: `9000`
- `liquidationFactorBps`: `10000`
- `liquidationFeeBps`: `0`

### Z3 Result

- Status: `possible_bug`
- Solver status: `sat`
- Counterexample: `{'debt_before': 2, 'debt_after': 1, 'collateralBalance_before': 1000100000000000000, 'collateralBalance_after': 0, 'repaidDebt': 1, 'price': 1, 'collateralFactorBps': 9000, 'liquidationIncentiveBps': 1, 'liquidationFeeBps': 0, 'liquidationFactorBps': 10000, 'liquidatorReward': 1000100000000000000, 'liquidationFee': 0, 'creditLimit_before': 0, 'creditLimit_after': 0, 'gap_before': 2, 'gap_after': 1, 'collateralBalance_after_liquidator': 0}`
- Explanation: Z3 found a satisfying assignment for at least one violation condition.
- Warnings: `['External calls to oracle, escrow, dbr, borrowController, and dola are abstracted; their side effects are assumed to follow the summaries', 'Reentrancy via external calls is not modeled', 'DBR deficit mechanics and their effect on debt accrual are not modeled', 'Exact on-chain value of liquidationIncentiveBps is not provided in the resolved parameters, only that it is > 0', 'Implementation of escrow.pay and whether it reverts on insufficient balance', 'Oracle price feed implementation and potential manipulation vectors']`

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
- Vulnerability: Partial liquidation must not create bad debt: collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps)
  must be < 10000^2, gap_after must be < gap_before, and liquidation must not exhaust collateral while debt remains.

### Triage

- Keep: `True`
- Confidence: `high`
- Reason: LLM triage skipped; deterministic filters passed
- FP categories: `[]`
- Relevance: Candidate selected for formal verification without LLM triage.

### Formal Spec

- Summary: Fallback spec created because formal-verifier LLM output could not be validated.
- Missing context: `['formal verifier LLM output', 'formal verifier LLM failed: LLM request failed for model z-ai/glm-5.1 after 3 attempt(s): The read operation timed out']`
- Unsupported features: `[]`
- Safety properties: `[]`
- Violation conditions: `[]`

### On-Chain Parameters

- `collateralFactorBps`: `8500`
- `liquidationFactorBps`: `7500`
- `liquidationFeeBps`: `0`

### Z3 Result

- Status: `model_incomplete`
- Solver status: `not_run`
- Counterexample: `None`
- Explanation: Spec has no violation conditions to assert.
- Warnings: `['missing violation_conditions']`

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
- Vulnerability: Partial liquidation must not create bad debt: collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps)
  must be < 10000^2, gap_after must be < gap_before, and liquidation must not exhaust collateral while debt remains.

### Triage

- Keep: `True`
- Confidence: `high`
- Reason: LLM triage skipped; deterministic filters passed
- FP categories: `[]`
- Relevance: Candidate selected for formal verification without LLM triage.

### Formal Spec

- Summary: A partial liquidation can increase the gap between a user's debt and their credit limit (i.e., make their position more underwater), or even fully exhaust their collateral while debt remains, creating bad debt. This happens if the collateral removed (liquidator reward + fee) exceeds the proportional collateral value of the debt repaid, which occurs when collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps) >= 10000^2.
- Missing context: `['Exact implementation of oracle.getPrice and whether it can return different values on consecutive calls within the same transaction.', 'Implementation of escrow.pay to confirm it reverts on insufficient balance vs silently transferring less.', 'Whether borrowController.onRepay can revert and under what conditions.']`
- Unsupported features: `['External calls to oracle, dbr, borrowController, and dola are abstracted; their internal logic and potential reverts are not modeled.', 'Potential oracle price manipulation between the credit limit check and the reward calculation is not modeled (assumes consistent price).', 'DBR deficit mechanics and their effect on debt accrual during liquidation are not modeled.']`
- Safety properties: `['(debt_after - creditLimit_after) < (debt_before - creditLimit_before)', 'implies(debt_after > 0, collateral_after > 0)', 'collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps) < 10000 * 10000']`
- Violation conditions: `['(debt_after - creditLimit_after) >= (debt_before - creditLimit_before)', 'and(debt_after > 0, collateral_after == 0)', 'collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps) >= 10000 * 10000']`

### On-Chain Parameters

- `collateralFactorBps`: `8500`
- `liquidationFactorBps`: `7500`
- `liquidationFeeBps`: `0`
- `liquidationIncentiveBps`: `1000`

### Z3 Result

- Status: `possible_bug`
- Solver status: `sat`
- Counterexample: `{'debt_before': 2, 'debt_after': 1, 'collateral_before': 1, 'collateral_after': 1, 'repaidDebt': 1, 'collateralFactorBps': 8500, 'liquidationIncentiveBps': 1000, 'liquidationFeeBps': 0, 'liquidationFactorBps': 7500, 'price': 1, 'liquidatorReward': 0, 'liquidationFee': 0, 'creditLimit_before': 1, 'creditLimit_after': 0, 'actualFeePaid': 0}`
- Explanation: Z3 found a satisfying assignment for at least one violation condition.
- Warnings: `['External calls to oracle, dbr, borrowController, and dola are abstracted; their internal logic and potential reverts are not modeled.', 'Potential oracle price manipulation between the credit limit check and the reward calculation is not modeled (assumes consistent price).', 'DBR deficit mechanics and their effect on debt accrual during liquidation are not modeled.', 'Exact implementation of oracle.getPrice and whether it can return different values on consecutive calls within the same transaction.', 'Implementation of escrow.pay to confirm it reverts on insufficient balance vs silently transferring less.', 'Whether borrowController.onRepay can revert and under what conditions.', 'Skipped unsupported state transition `liquidatorReward = repaidDebt * 1 ether / price * (10000 + liquidationIncentiveBps) / 10000`: Could not parse expression: repaidDebt * 1 ether / price * (10000 + liquidationIncentiveBps) / 10000', 'Skipped unsupported state transition `liquidationFee = repaidDebt * 1 ether / price * liquidationFeeBps / 10000`: Could not parse expression: repaidDebt * 1 ether / price * liquidationFeeBps / 10000', 'Skipped unsupported state transition `creditLimit_before = collateral_before * price / 1 ether * collateralFactorBps / 10000`: Could not parse expression: collateral_before * price / 1 ether * collateralFactorBps / 10000', 'Skipped unsupported state transition `creditLimit_after = collateral_after * price / 1 ether * collateralFactorBps / 10000`: Could not parse expression: collateral_after * price / 1 ether * collateralFactorBps / 10000']`

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
- Vulnerability: Partial liquidation must not create bad debt: collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps)
  must be < 10000^2, gap_after must be < gap_before, and liquidation must not exhaust collateral while debt remains.

### Triage

- Keep: `True`
- Confidence: `high`
- Reason: LLM triage skipped; deterministic filters passed
- FP categories: `[]`
- Relevance: Candidate selected for formal verification without LLM triage.

### Formal Spec

- Summary: The liquidate function can create bad debt if the protocol parameters allow the collateral removed (liquidator reward + fee) to exceed the proportional collateral value of the repaid debt. Specifically, if collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps) >= 10000^2, a partial liquidation worsens the user's collateralization ratio, potentially exhausting collateral while debt remains.
- Missing context: `['Exact implementation of oracle.getPrice and its price bounds', 'Implementation of escrow.pay and whether it can fail partially', 'DBR deficit state and its effect on liquidation eligibility']`
- Unsupported features: `['External calls to oracle, dbr, borrowController, and dola are abstracted; reverts on failure are assumed', 'ERC20 transferFrom assumed to succeed and return true or revert']`
- Safety properties: `['(collateral_after * price / 1000000000000000000 * collateralFactorBps / 10000) - debt_after >= (collateral_before * price / 1000000000000000000 * collateralFactorBps / 10000) - debt_before', 'collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps) < 100000000', 'implies(debt_after > 0, collateral_after > 0)']`
- Violation conditions: `['(collateral_after * price / 1000000000000000000 * collateralFactorBps / 10000) - debt_after < (collateral_before * price / 1000000000000000000 * collateralFactorBps / 10000) - debt_before', 'collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps) >= 100000000', 'and(debt_after > 0, collateral_after == 0)']`

### On-Chain Parameters

- `collateralFactorBps`: `8500`
- `liquidationFactorBps`: `7500`
- `liquidationFeeBps`: `0`
- `liquidationIncentiveBps`: `1000`

### Z3 Result

- Status: `possible_bug`
- Solver status: `sat`
- Counterexample: `{'debt_before': 3, 'debt_after': 2, 'collateral_before': 2000000000000000001, 'collateral_after': 1450000000000000001, 'repaidDebt': 1, 'liquidatorReward': 550000000000000000, 'liquidationFee': 0, 'collateralFactorBps': 8500, 'liquidationIncentiveBps': 1000, 'liquidationFeeBps': 0, 'liquidationFactorBps': 7500, 'price': 2}`
- Explanation: Z3 found a satisfying assignment for at least one violation condition.
- Warnings: `['External calls to oracle, dbr, borrowController, and dola are abstracted; reverts on failure are assumed', 'ERC20 transferFrom assumed to succeed and return true or revert', 'Exact implementation of oracle.getPrice and its price bounds', 'Implementation of escrow.pay and whether it can fail partially', 'DBR deficit state and its effect on liquidation eligibility', 'Skipped unsupported precondition `getCreditLimitInternal(user) < debt_before`: Unknown symbol: user']`

### Limitations

- Z3 checks only the encoded formal model, not full Solidity or EVM semantics.
- sat means possible_bug, never verified_bug.
- Heuristic source slicing may miss relevant context until Slither integration is added.

### Recommended Manual Review Steps

- Review missing_context and unsupported_features before trusting solver output.
- Compare each formula against Solidity source and protocol documentation.
- Manually validate any counterexample against real units, rounding, and access control.
