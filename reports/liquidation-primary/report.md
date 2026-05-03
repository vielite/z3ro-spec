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

- Summary: The liquidate function can create bad debt if the collateral factor, liquidation incentive, and liquidation fee parameters do not satisfy the invariant collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps) < 10000^2. If this invariant is violated, a partial liquidation removes more collateral (reward + fee) than the proportional debt repaid, worsening the user's health factor and potentially exhausting collateral while debt remains.
- Missing context: `['Exact implementation of oracle.getPrice and how it applies collateralFactorBps to the raw price', 'Whether escrow.pay can fail silently or revert if insufficient balance', 'Exact behavior of dbr.onRepay and whether it can affect the liquidation outcome', 'Whether there are any other state changes during the transaction that could affect the health check']`
- Unsupported features: `[]`
- Safety properties: `['collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps) < 100000000', 'implies(debt_after > 0, collateral_after > 0)', 'implies(debt_after > 0, gap_after < gap_before)', 'implies(debt_after > 0, debt_after <= creditLimit_after)']`
- Violation conditions: `['collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps) >= 100000000', 'debt_after > 0 and collateral_after == 0', 'debt_after > 0 and gap_after >= gap_before', 'debt_after > 0 and debt_after > creditLimit_after']`

### Z3 Result

- Status: `possible_bug`
- Solver status: `sat`
- Counterexample: `{'debt_before': 10000, 'debt_after': 9999, 'collateral_before': 0, 'collateral_after': 0, 'repaidDebt': 1, 'collateralFactorBps': 0, 'liquidationIncentiveBps': 1, 'liquidationFeeBps': 0, 'liquidationFactorBps': 1, 'price': 0, 'liquidatorReward': 0, 'liquidationFee': 0, 'totalCollateralRemoved': 0, 'creditLimit_before': 0, 'creditLimit_after': 0, 'gap_before': 0, 'gap_after': 0}`
- Explanation: Z3 found a satisfying assignment for at least one violation condition.
- Warnings: `['Exact implementation of oracle.getPrice and how it applies collateralFactorBps to the raw price', 'Whether escrow.pay can fail silently or revert if insufficient balance', 'Exact behavior of dbr.onRepay and whether it can affect the liquidation outcome', 'Whether there are any other state changes during the transaction that could affect the health check']`

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

- Summary: The liquidate function allows partial liquidation of underwater debt, transferring collateral to the liquidator and a fee to governance. If the combined liquidation incentive and fee parameters are too high relative to the collateral factor, a partial liquidation can leave the remaining position more underwater than before (gap_after >= gap_before), or even exhaust the collateral while debt remains, creating bad debt.
- Missing context: `['Exact implementation of oracle.getPrice and how it updates internal state', "Exact implementation of escrow.pay and whether it can fail on insufficient balance (the code implies it doesn't revert but pays what's available for the fee portion)", 'Whether liquidatorReward payment reverts if escrow.balance is insufficient (the code does not show a balance check before escrow.pay(msg.sender, liquidatorReward))']`
- Unsupported features: `['External call to oracle.getPrice modifies pessimistic price state internally, which is abstracted as a constant price assumption', "dbr.onRepay external call effects on DBR deficit are not modeled as they don't directly affect the collateral/debt ratio bad debt condition", 'borrowController.onRepay external call is not modeled']`
- Safety properties: `['(debt_after * 10000) - (collateral_after * price * collateralFactorBps / 1000000000000000000) < (debt_before * 10000) - (collateral_before * price * collateralFactorBps / 1000000000000000000)', 'implies(debt_after > 0, collateral_after > 0)', 'collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps) < 100000000']`
- Violation conditions: `['(debt_after * 10000) - (collateral_after * price * collateralFactorBps / 1000000000000000000) >= (debt_before * 10000) - (collateral_before * price * collateralFactorBps / 1000000000000000000)', 'and(debt_after > 0, collateral_after == 0)', 'collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps) >= 100000000']`

### Z3 Result

- Status: `unsupported`
- Solver status: `not_run`
- Counterexample: `None`
- Explanation: Spec contains unsupported features.
- Warnings: `['External call to oracle.getPrice modifies pessimistic price state internally, which is abstracted as a constant price assumption', "dbr.onRepay external call effects on DBR deficit are not modeled as they don't directly affect the collateral/debt ratio bad debt condition", 'borrowController.onRepay external call is not modeled']`

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

- Summary: The liquidate function can remove more collateral value (via liquidatorReward and liquidationFee) than the debt it repays, leaving the user in a worse health state (gap_after >= gap_before) or creating bad debt (collateral exhausted while debt remains). This happens when collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps) >= 10000^2.
- Missing context: `['Exact implementation of escrow.pay and whether it can fail if insufficient balance', 'Whether oracle.getPrice can return manipulated values', 'Exact behavior when escrow.balance < liquidationFee (partial fee payment)', 'DBR deficit interactions and how they affect the health calculation', 'Whether totalDebt underflow is possible']`
- Unsupported features: `[]`
- Safety properties: `['collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps) < 100000000', 'implies(debt_after > 0, collateral_after > 0)', 'implies(debt_after > 0, gap_after < gap_before)', 'implies(debt_after > 0, collateral_after * price * collateralFactorBps > debt_after * 10000 * 1000000000000000000)']`
- Violation conditions: `['collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps) >= 100000000', 'and(debt_after > 0, collateral_after == 0)', 'and(debt_after > 0, gap_after >= gap_before)', 'and(debt_after > 0, collateral_after * price * collateralFactorBps <= debt_after * 10000 * 1000000000000000000)']`

### Z3 Result

- Status: `unsupported`
- Solver status: `not_run`
- Counterexample: `None`
- Explanation: Unknown symbol: user
- Warnings: `['Exact implementation of escrow.pay and whether it can fail if insufficient balance', 'Whether oracle.getPrice can return manipulated values', 'Exact behavior when escrow.balance < liquidationFee (partial fee payment)', 'DBR deficit interactions and how they affect the health calculation', 'Whether totalDebt underflow is possible']`

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

- Summary: The liquidate function allows partial liquidations that can leave a borrower with less collateral backing per unit of debt than before, eventually creating bad debt where the remaining collateral is insufficient to cover the remaining debt plus liquidation incentives. This happens if collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps) >= 10000^2.
- Missing context: `['Exact implementation of escrow.pay and whether it can fail partially', 'Oracle price bounds and manipulation resistance', 'Whether escrow.balance() can be manipulated between liquidatorReward and fee payment', 'DBR deficit accumulation mechanics and their effect on liquidation']`
- Unsupported features: `['Oracle price manipulation or flash loan attacks on price', 'Reentrancy through escrow.pay callback', 'DBR deficit interactions that could affect liquidation eligibility', 'BorrowController callback side effects']`
- Safety properties: `['implies(debt_after > 0, gap_after < gap_before)', 'collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps) < 100000000', 'implies(debt_after > 0, collateral_after > 0)', 'implies(debt_before > creditLimit_before, debt_after - creditLimit_after < debt_before - creditLimit_before)']`
- Violation conditions: `['and(debt_after > 0, gap_after >= gap_before)', 'collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps) >= 100000000', 'and(debt_after > 0, collateral_after == 0)', 'and(debt_before - debt_after > 0, creditLimit_before - creditLimit_after > debt_before - debt_after)']`

### Z3 Result

- Status: `unsupported`
- Solver status: `not_run`
- Counterexample: `None`
- Explanation: Spec contains unsupported features.
- Warnings: `['Oracle price manipulation or flash loan attacks on price', 'Reentrancy through escrow.pay callback', 'DBR deficit interactions that could affect liquidation eligibility', 'BorrowController callback side effects']`

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

- Summary: The liquidation function can create bad debt if the protocol parameters do not strictly satisfy collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps) < 10000^2. If this invariant breaks, a liquidation can remove more collateral value (via reward + fee) than the debt repaid relative to the user's credit limit, leaving the user's remaining debt undercollateralized (gap_after >= gap_before). Furthermore, the escrow can be entirely drained of collateral while the user still holds debt.
- Missing context: `['Exact implementation of escrow.pay and its balance tracking', 'Oracle price update mechanics between getCreditLimitInternal and getPrice calls within liquidate', 'DBR deficit accumulation and its effect on debt during liquidation']`
- Unsupported features: `['External calls to oracle and escrow are abstracted; assumes they behave according to interface specifications without side-effects on Market state.', 'Reentrancy via escrow.pay or borrowController.onRepay is not modeled, assuming standard CEI pattern or non-reentrant callees.']`
- Safety properties: `['collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps) < 100000000', '(debt_after - creditLimit_after) < (debt_before - creditLimit_before)', 'implies(debt_after > 0, collateral_after > 0)', 'implies(debt_before > creditLimit_before, debt_after <= creditLimit_after)']`
- Violation conditions: `['collateralFactorBps * (10000 + liquidationIncentiveBps + liquidationFeeBps) >= 100000000', '(debt_after - creditLimit_after) >= (debt_before - creditLimit_before)', 'and(debt_after > 0, collateral_after == 0)', 'and(debt_before > creditLimit_before, debt_after > creditLimit_after)']`

### Z3 Result

- Status: `unsupported`
- Solver status: `not_run`
- Counterexample: `None`
- Explanation: Spec contains unsupported features.
- Warnings: `['External calls to oracle and escrow are abstracted; assumes they behave according to interface specifications without side-effects on Market state.', 'Reentrancy via escrow.pay or borrowController.onRepay is not modeled, assuming standard CEI pattern or non-reentrant callees.']`

### Limitations

- Z3 checks only the encoded formal model, not full Solidity or EVM semantics.
- sat means possible_bug, never verified_bug.
- Heuristic source slicing may miss relevant context until Slither integration is added.

### Recommended Manual Review Steps

- Review missing_context and unsupported_features before trusting solver output.
- Compare each formula against Solidity source and protocol documentation.
- Manually validate any counterexample against real units, rounding, and access control.
