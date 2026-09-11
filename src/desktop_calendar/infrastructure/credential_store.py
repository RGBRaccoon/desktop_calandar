import json

from keyring.backends.Windows import WinVaultKeyring
from keyring.errors import PasswordDeleteError


class CredentialStore:
    """Explicit Windows backend: never fall back to a plaintext keyring."""

    SERVICE = "DesktopCalendar"
    ACCOUNT = "google_oauth_token"

    def __init__(self):
        self.backend = WinVaultKeyring()

    def load(self) -> dict | None:
        value = self.backend.get_password(self.SERVICE, self.ACCOUNT)
        if not value:
            return None
        try:
            data = json.loads(str(value))
            return data if isinstance(data, dict) else None
        except ValueError:
            return None

    def save(self, value: dict):
        self.backend.set_password(self.SERVICE, self.ACCOUNT, json.dumps(value))

    def delete(self):
        try:
            self.backend.delete_password(self.SERVICE, self.ACCOUNT)
        except PasswordDeleteError:
            pass
