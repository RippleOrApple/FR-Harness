from typing import Protocol

import httpx

from fr_harness.models import Action


class LLMClient(Protocol):
    def next_action(self, context: list[dict[str, str]]) -> Action:
        """Return the next structured agent action for the supplied context."""


class MockLLM:
    def __init__(self, actions: list[Action]) -> None:
        self._actions = list(actions)

    def next_action(self, context: list[dict[str, str]]) -> Action:
        del context
        if not self._actions:
            raise RuntimeError("mock action queue exhausted")
        return self._actions.pop(0)


class OpenAICompatibleLLM:
    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._api_key = api_key
        self._http_client = http_client or httpx.Client(timeout=30.0)

    def next_action(self, context: list[dict[str, str]]) -> Action:
        response = self._http_client.post(
            f"{self._base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={"model": self._model, "messages": context},
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return Action.model_validate_json(content)
