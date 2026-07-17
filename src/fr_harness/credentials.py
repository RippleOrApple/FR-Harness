import os
from collections.abc import Mapping
from typing import Protocol


SERVICE_NAME = "fr-harness"
ACCOUNT_NAME = "openai-api-key"


class KeyringBackend(Protocol):
    def get_password(self, service_name: str, username: str) -> str | None:
        raise NotImplementedError

    def set_password(
        self, service_name: str, username: str, password: str
    ) -> None:
        raise NotImplementedError

    def delete_password(self, service_name: str, username: str) -> None:
        raise NotImplementedError


class CredentialStoreError(RuntimeError):
    pass


class CredentialStore:
    def __init__(self, backend: KeyringBackend | None = None) -> None:
        if backend is None:
            import keyring

            backend = keyring
        self._backend = backend

    def get(self) -> str | None:
        try:
            return self._backend.get_password(SERVICE_NAME, ACCOUNT_NAME)
        except Exception:
            raise CredentialStoreError("system keyring operation failed") from None

    def set(self, value: str) -> None:
        if not value:
            raise ValueError("credential cannot be empty")
        try:
            self._backend.set_password(SERVICE_NAME, ACCOUNT_NAME, value)
        except Exception:
            raise CredentialStoreError("system keyring operation failed") from None

    def clear(self) -> bool:
        if self.get() is None:
            return False
        try:
            self._backend.delete_password(SERVICE_NAME, ACCOUNT_NAME)
        except Exception:
            raise CredentialStoreError("system keyring operation failed") from None
        return True


def resolve_api_key(
    store: CredentialStore,
    environ: Mapping[str, str] | None = None,
) -> tuple[str | None, str]:
    values = os.environ if environ is None else environ
    environment_value = values.get("OPENAI_API_KEY")
    if environment_value:
        return environment_value, "environment"
    keyring_value = store.get()
    if keyring_value:
        return keyring_value, "system keyring"
    return None, "not configured"
