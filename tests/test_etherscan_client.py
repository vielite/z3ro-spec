from __future__ import annotations

import json

import httpx

from specscan.etherscan.client import EtherscanClient


def test_etherscan_client_uses_v2_endpoint_and_chainid(tmp_path):
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["path"] = request.url.path
        captured["chainid"] = request.url.params.get("chainid")
        captured["action"] = request.url.params.get("action")
        payload = {
            "status": "1",
            "message": "OK",
            "result": [
                {
                    "SourceCode": "contract Test { }",
                    "ABI": json.dumps([]),
                    "ContractName": "Test",
                    "CompilerVersion": "v0.8.0",
                    "Proxy": "0",
                    "Implementation": "",
                }
            ],
        }
        return httpx.Response(200, json=payload)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    etherscan = EtherscanClient(
        api_key="test-key",
        chain_id="1",
        cache_dir=tmp_path,
        client=client,
    )

    bundle = etherscan.fetch_source_bundle("0x123")

    assert captured["path"] == "/v2/api"
    assert captured["chainid"] == "1"
    assert captured["action"] == "getsourcecode"
    assert bundle.contract_name == "Test"


def test_etherscan_eth_call_uses_v2_proxy_action():
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["chainid"] = request.url.params.get("chainid")
        captured["module"] = request.url.params.get("module")
        captured["action"] = request.url.params.get("action")
        captured["to"] = request.url.params.get("to")
        captured["data"] = request.url.params.get("data")
        captured["tag"] = request.url.params.get("tag")
        return httpx.Response(
            200,
            json={"jsonrpc": "2.0", "id": 1, "result": "0x" + "2a".zfill(64)},
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    etherscan = EtherscanClient(
        api_key="test-key",
        chain_id="1",
        client=client,
    )

    result = etherscan.eth_call("0xABC", "0x12345678")

    assert result == "0x" + "2a".zfill(64)
    assert captured == {
        "path": "/v2/api",
        "chainid": "1",
        "module": "proxy",
        "action": "eth_call",
        "to": "0xabc",
        "data": "0x12345678",
        "tag": "latest",
    }
