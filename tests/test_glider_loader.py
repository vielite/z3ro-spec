from __future__ import annotations

import json

from specscan.loaders.glider_json import load_glider_json


def test_loads_plain_glider_list(tmp_path):
    path = tmp_path / "results.json"
    path.write_text(
        json.dumps(
            [
                {
                    "contract": "0xabc",
                    "contract_name": "Vault",
                    "sol_function": "function deposit(uint256 assets) external {}",
                    "sol_function_source_lines": [10, 12],
                    "value": 1.5,
                    "unknown": "kept",
                }
            ]
        )
    )

    findings = load_glider_json(path)

    assert len(findings) == 1
    assert findings[0].contract == "0xabc"
    assert findings[0].sol_function_source_lines == (10, 12)
    assert findings[0].extra["unknown"] == "kept"

