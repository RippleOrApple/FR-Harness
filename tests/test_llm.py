import json

import httpx
import pytest

from fr_harness.llm import MockLLM, OpenAICompatibleLLM
from fr_harness.models import Action, ActionKind


def test_mock_llm_returns_actions_in_order() -> None:
    first = Action(kind=ActionKind.READ_FILE, path="app.py")
    second = Action(kind=ActionKind.COMPLETE, reason="tests pass")
    client = MockLLM([first, second])

    assert client.next_action([]) == first
    assert client.next_action([]) == second


def test_mock_llm_raises_when_action_queue_is_empty() -> None:
    with pytest.raises(RuntimeError, match="mock action queue exhausted"):
        MockLLM([]).next_action([])


def test_openai_compatible_client_parses_action_without_network() -> None:
    payload = {"choices": [{"message": {"content": json.dumps({"kind": "complete", "reason": "done"})}}]}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer test-key"
        return httpx.Response(200, json=payload)

    client = OpenAICompatibleLLM(
        base_url="https://llm.example/v1",
        model="test-model",
        api_key="test-key",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert client.next_action([]) == Action(kind=ActionKind.COMPLETE, reason="done")
