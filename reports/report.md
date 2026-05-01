# z3ro-spec Report

## Candidate Prioritization

- Total input candidates: `25`
- Excluded due to missing invalid zero or low value: `11`
- Remaining after value filter: `14`
- Excluded by deterministic filters: `0`
- Excluded by llm triage: `0`
- Not evaluated after top candidates selected: `12`
- Selected for formal verification: `2`
- Top candidates requested: `2`
- Min value: `0.0`

### Selected Candidates

- Rank `1`: `0x80ac24aa929eaf5013f6436cda2a7ba190f5cc0b` (MaplePool), value `216026506.55839744`, confidence `medium`, reason: The deposit function is directly relevant as it implements the deposit-mint pattern described in the vulnerability. It mints shares calculated by previewDeposit(assets_) without explicitly validating that shares_ > 0 when assets_ > 0. However, confirmation requires the previewDeposit implementation and current vault state (totalAssets, totalSupply) to determine if rounding or edge cases could produce zero shares for nonzero asset deposits.
- Rank `2`: `0x356b8d89c1e1239cbbb9de4815c39a1474d5ba7d` (MaplePool), value `20001061.331183918`, confidence `medium`, reason: The deposit function directly uses previewDeposit(assets_) to calculate shares without validating that shares_ > 0. This matches the vulnerability pattern where zero shares could be minted for non-zero asset deposits if previewDeposit rounds down. Need to examine previewDeposit implementation to confirm if it can return zero when assets_ > 0. The absence of a zero-shares check in this function is a red flag.

### Excluded Candidates

- `0x96dd07b6c99b22f3f0cb1836aff8530a98bde9e3` (StrategyProxy), value `0.0`, reason: excluded_zero_or_negative_value
- `0x358cfacf00d0b4634849821bb3d1965b472c776a` (LayerZeroTeller), value `0.0`, reason: excluded_zero_or_negative_value
- `0x359c1efd3fc7e3a9b7a043c185fd5d39dec1fc81` (StakingProxyERC20), value `0.0`, reason: excluded_zero_or_negative_value
- `0x359c1efd3fc7e3a9b7a043c185fd5d39dec1fc81` (StakingProxyERC20), value `0.0`, reason: excluded_zero_or_negative_value
- `0x96fe7b5762bd4405149a9a313473e68a8e870f6c` (PrizeVault), value `0.0`, reason: excluded_zero_or_negative_value
- `0x357ada6e0da1bb40668bddd3e3af64f472cbd9ff` (StakingPool), value `0.0`, reason: excluded_zero_or_negative_value
- `0x96c2c05c7fee9ad6953467b6fc4ce4beb8c9b08c` (MetamorphoConnector), value `0.0`, reason: excluded_zero_or_negative_value
- `0x96becced4ed2cbefa679306bf9353093b7276a16` (EigenLayerRETHVault), value `0.0`, reason: excluded_zero_or_negative_value
- `0x973c2f122dbfa2867e6f7a05d329414bff43eaea` (ChefRewardHook), value `0.0`, reason: excluded_zero_or_negative_value
- `0x353e11ab2da88bfc57fd42c2871301c1f123d4db` (ConcentratorStakeDAOLocker), value `0.0`, reason: excluded_zero_or_negative_value
- `0x975304c676eb3dc86cd336138328e107a95eaa50` (TokenizedStrategy), value `0.0`, reason: excluded_zero_or_negative_value
- `0xc39a5a616f0ad1ff45077fa2de3f79ab8eb8b8b9` (MaplePool), value `535624.1483062173`, reason: not_evaluated_after_top_candidates_selected
- `0x35a398425d9f1029021a92bc3d2557d42c8588d7` (PirexCvx), value `359558.1406365472`, reason: not_evaluated_after_top_candidates_selected
- `0x970609f90e695e4fe3a6a7ee87e4dae7da8deecc` (StashETH), value `62000.18206260953`, reason: not_evaluated_after_top_candidates_selected
- `0x000000000000040470635eb91b7ce4d132d616ed` (ZAMM), value `41462.413162619196`, reason: not_evaluated_after_top_candidates_selected
- `0x00000000000008882d72efa6cce4b6a40b24c860` (ZAMM), value `39527.24288488058`, reason: not_evaluated_after_top_candidates_selected
- `0x000000000000fea5f4b241f9e77b4d43b76798a9` (AutoSniper), value `14539.454729114117`, reason: not_evaluated_after_top_candidates_selected
- `0x017e71e96f2ae777c679740d2d8dc15ed4231981` (WrappedYFI), value `6942.928838811601`, reason: not_evaluated_after_top_candidates_selected
- `0x9669890e48f330acd88b78d63e1a6b3482652cd9` (BCNTToken), value `1603.5807668642574`, reason: not_evaluated_after_top_candidates_selected
- `0x967fb06a8d8428bc9d03436d06694704e9bf7019` (StableAMM), value `1408.242322890154`, reason: not_evaluated_after_top_candidates_selected
- `0x96f70e168a4ad963b4b81ea9cce77c56d0d4d92e` (YapStarter), value `592.4599326063639`, reason: not_evaluated_after_top_candidates_selected
- `0x974c8fbf4fd795f66b85b73ebc988a51f1a040a9` (MetaMorphoV1_1), value `0.043271028641488`, reason: not_evaluated_after_top_candidates_selected
- `0x96e61422b6a9ba0e068b6c5add4ffabc6a4aae27` (FixedEUR), value `0.0005991100537499999`, reason: not_evaluated_after_top_candidates_selected

## 1. MaplePool

- Contract address: `0x80ac24aa929eaf5013f6436cda2a7ba190f5cc0b`
- Function source lines: `(1002, 1004)`
- Value/TVL: `216026506.55839744`
- Vulnerability: Deposit and mint must not mint zero shares for a nonzero asset
  deposit.

### Triage

- Keep: `True`
- Confidence: `medium`
- Reason: The deposit function is directly relevant as it implements the deposit-mint pattern described in the vulnerability. It mints shares calculated by previewDeposit(assets_) without explicitly validating that shares_ > 0 when assets_ > 0. However, confirmation requires the previewDeposit implementation and current vault state (totalAssets, totalSupply) to determine if rounding or edge cases could produce zero shares for nonzero asset deposits.
- FP categories: `[]`
- Relevance: This is the core deposit function that could exhibit the described vulnerability if previewDeposit returns zero for small asset amounts due to rounding down in the share calculation. The absence of a shares > 0 check makes it relevant, but exploitability depends on the specific previewDeposit logic and vault conditions.

### Formal Spec

- Summary: Fallback spec created because formal-verifier LLM output could not be validated.
- Missing context: `['formal verifier LLM output', "formal verifier LLM failed: LLM request failed for model z-ai/glm-5.1 after 3 attempt(s): Server error '502 Bad Gateway' for url 'https://integrate.api.nvidia.com/v1/chat/completions'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/502"]`
- Unsupported features: `[]`
- Safety properties: `[]`
- Violation conditions: `[]`

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

## 2. MaplePool

- Contract address: `0x356b8d89c1e1239cbbb9de4815c39a1474d5ba7d`
- Function source lines: `(1002, 1004)`
- Value/TVL: `20001061.331183918`
- Vulnerability: Deposit and mint must not mint zero shares for a nonzero asset
  deposit.

### Triage

- Keep: `True`
- Confidence: `medium`
- Reason: The deposit function directly uses previewDeposit(assets_) to calculate shares without validating that shares_ > 0. This matches the vulnerability pattern where zero shares could be minted for non-zero asset deposits if previewDeposit rounds down. Need to examine previewDeposit implementation to confirm if it can return zero when assets_ > 0. The absence of a zero-shares check in this function is a red flag.
- FP categories: `[]`
- Relevance: This function is the exact implementation site of the described vulnerability. It executes the deposit flow that calculates shares via previewDeposit and passes them directly to _mint. If previewDeposit contains integer division that rounds down to zero for small asset amounts, this function would mint zero shares, causing loss of deposited assets.

### Formal Spec

- Summary: The deposit function calculates shares using previewDeposit(assets_) and passes the result directly to _mint without checking that shares > 0. If previewDeposit rounds down to 0 for a small nonzero asset deposit, the user loses their deposited assets while receiving zero shares.
- Missing context: `["{'description': 'The exact implementation of previewDeposit is not provided in the source context', 'detail': 'Assuming standard ERC4626 formula shares = assets * totalSupply / totalAssets, but the actual implementation may differ or include fees'}", "{'description': 'The implementation of _mint is not fully provided', 'detail': 'Assuming it mints the specified shares and transfers the specified assets, but it may contain additional logic or validation'}", "{'description': 'The value of BOOTSTRAP_MINT is not provided', 'detail': 'This constant affects the minimum totalSupply and thus the rounding behavior; it is typically a small number like 1e6 or 1e18'}"]`
- Unsupported features: `[]`
- Safety properties: `['implies(assets_ > 0, shares_ > 0)', 'implies(assets_ > 0, floor_div(assets_ * totalSupply_before, totalAssets_before) >= 1)']`
- Violation conditions: `['and(assets_ > 0, shares_ == 0)', 'and(assets_ > 0, assets_ * totalSupply_before < totalAssets_before)']`

### Z3 Result

- Status: `unsupported`
- Solver status: `not_run`
- Counterexample: `None`
- Explanation: Unsupported arithmetic operator
- Warnings: `["{'description': 'The exact implementation of previewDeposit is not provided in the source context', 'detail': 'Assuming standard ERC4626 formula shares = assets * totalSupply / totalAssets, but the actual implementation may differ or include fees'}", "{'description': 'The implementation of _mint is not fully provided', 'detail': 'Assuming it mints the specified shares and transfers the specified assets, but it may contain additional logic or validation'}", "{'description': 'The value of BOOTSTRAP_MINT is not provided', 'detail': 'This constant affects the minimum totalSupply and thus the rounding behavior; it is typically a small number like 1e6 or 1e18'}"]`

### Limitations

- Z3 checks only the encoded formal model, not full Solidity or EVM semantics.
- sat means possible_bug, never verified_bug.
- Heuristic source slicing may miss relevant context until Slither integration is added.

### Recommended Manual Review Steps

- Review missing_context and unsupported_features before trusting solver output.
- Compare each formula against Solidity source and protocol documentation.
- Manually validate any counterexample against real units, rounding, and access control.
