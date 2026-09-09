import pytest

from src.api.routes.settings import CloudConfigRequest
from src.infra.openai_client import OpenAICompatibleClient
from src.services.cost_service import get_pricing


class _Response:
    status_code = 200

    def raise_for_status(self):
        return None

    def json(self):
        return {
            "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
            "usage": {},
        }


class _HttpClient:
    def __init__(self):
        self.payload = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    async def post(self, _url, *, json, headers):
        self.payload = json
        return _Response()


def test_cloud_config_legacy_request_defaults_to_thinking_enabled():
    req = CloudConfigRequest(
        provider="deepseek",
        base_url="https://api.deepseek.com",
        model="deepseek-v4-flash",
        api_key="",
    )
    assert req.thinking_mode == "enabled"


def test_deepseek_v4_thinking_enabled_removes_temperature():
    client = OpenAICompatibleClient(
        "https://api.deepseek.com", "test", "deepseek-v4-pro",
        thinking_mode="enabled",
    )
    payload = {"temperature": 0.1}
    client._apply_deepseek_thinking(payload)
    assert payload == {"thinking": {"type": "enabled"}}


def test_deepseek_v4_thinking_disabled_keeps_temperature():
    client = OpenAICompatibleClient(
        "https://api.deepseek.com", "test", "deepseek-v4-flash",
        thinking_mode="disabled",
    )
    payload = {"temperature": 0.1}
    client._apply_deepseek_thinking(payload)
    assert payload == {
        "temperature": 0.1,
        "thinking": {"type": "disabled"},
    }


def test_deepseek_controls_do_not_leak_to_other_providers():
    client = OpenAICompatibleClient(
        "https://api.example.com/v1", "test", "deepseek-v4-pro",
        thinking_mode="enabled",
    )
    payload = {"temperature": 0.1}
    client._apply_deepseek_thinking(payload)
    assert payload == {"temperature": 0.1}


def test_deepseek_v4_pricing_uses_conservative_peak_rate():
    assert get_pricing("deepseek-v4-flash") == (0.44, 1.32)
    assert get_pricing("deepseek-v4-pro") == (1.32, 3.96)


@pytest.mark.asyncio
async def test_deepseek_v4_generate_does_not_apply_legacy_8192_cap():
    client = OpenAICompatibleClient(
        "https://api.deepseek.com", "test", "deepseek-v4-pro",
        thinking_mode="disabled",
    )
    http = _HttpClient()
    client._make_client = lambda _timeout: http

    await client.generate("system", "prompt", max_tokens=65536)

    assert http.payload["max_tokens"] == 65536
    assert http.payload["thinking"] == {"type": "disabled"}
