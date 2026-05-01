from __future__ import annotations

from specscan.config import Settings


def test_settings_loads_dotenv_from_current_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("TRIAGE_LLM_API_KEY", raising=False)
    monkeypatch.delenv("TRIAGE_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("TRIAGE_LLM_MODEL", raising=False)
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                "TRIAGE_LLM_API_KEY=dotenv-key",
                "TRIAGE_LLM_BASE_URL=https://example.test/v1",
                "TRIAGE_LLM_MODEL='cheap-model'",
            ]
        )
    )

    settings = Settings.from_env()

    assert settings.triage_llm_api_key == "dotenv-key"
    assert settings.triage_llm_base_url == "https://example.test/v1"
    assert settings.triage_llm_model == "cheap-model"


def test_real_environment_overrides_dotenv(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TRIAGE_LLM_MODEL", "exported-model")
    (tmp_path / ".env").write_text("TRIAGE_LLM_MODEL=dotenv-model\n")

    settings = Settings.from_env()

    assert settings.triage_llm_model == "exported-model"


def test_z3ro_spec_env_prefix_loads_timeout_settings(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("Z3RO_SPEC_LLM_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("Z3RO_SPEC_ETHERSCAN_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("Z3RO_SPEC_NETWORK_RETRIES", raising=False)
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                "Z3RO_SPEC_LLM_TIMEOUT_SECONDS=600",
                "Z3RO_SPEC_ETHERSCAN_TIMEOUT_SECONDS=90",
                "Z3RO_SPEC_NETWORK_RETRIES=4",
            ]
        )
    )

    settings = Settings.from_env()

    assert settings.llm_timeout_seconds == 600
    assert settings.etherscan_timeout_seconds == 90
    assert settings.network_retries == 4


def test_legacy_specscan_env_prefix_still_works(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("Z3RO_SPEC_LLM_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("SPECSCAN_LLM_TIMEOUT_SECONDS", raising=False)
    (tmp_path / ".env").write_text("SPECSCAN_LLM_TIMEOUT_SECONDS=450\n")

    settings = Settings.from_env()

    assert settings.llm_timeout_seconds == 450


def test_etherscan_chain_id_loads_from_env(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("ETHERSCAN_CHAIN_ID=8453\n")

    settings = Settings.from_env()

    assert settings.etherscan_chain_id == "8453"
