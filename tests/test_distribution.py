import json
from unittest.mock import Mock, patch

import pytest

from desktop_calendar.services.google_auth_service import GoogleAuthService
from desktop_calendar.services.oauth_config import OAuthConfigurationError, load_client_config


def client():
    return {
        "installed": {
            "client_id": "test.apps.googleusercontent.com",
            "client_secret": "test-only",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }


def test_load_bundled_desktop_config(tmp_path):
    path = tmp_path / "oauth_client.json"
    path.write_text(json.dumps(client()), encoding="utf-8")
    assert load_client_config(path) == client()


def test_missing_config_explains_build_issue(tmp_path):
    with pytest.raises(OAuthConfigurationError, match="배포"):
        load_client_config(tmp_path / "absent.json")


@pytest.mark.parametrize(
    "data",
    [
        {"web": client()["installed"]},
        {"installed": {**client()["installed"], "token_uri": "https://example.com/token"}},
        {"installed": {**client()["installed"], "refresh_token": "must-not-bundle"}},
        {"type": "service_account"},
    ],
)
def test_reject_unsupported_or_sensitive_config(tmp_path, data):
    path = tmp_path / "oauth_client.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(OAuthConfigurationError):
        load_client_config(path)


def test_login_uses_embedded_config_without_user_path():
    store = Mock()
    with (
        patch(
            "desktop_calendar.services.google_auth_service.load_client_config",
            return_value=client(),
        ),
        patch("desktop_calendar.services.google_auth_service.InstalledAppFlow") as flow_type,
    ):
        flow = flow_type.from_client_config.return_value
        flow.run_local_server.return_value.to_json.return_value = '{"token":"test-token"}'
        GoogleAuthService(store).login()
        flow_type.from_client_config.assert_called_once_with(
            client(),
            ["https://www.googleapis.com/auth/calendar.readonly"],
            autogenerate_code_verifier=True,
        )
        store.save.assert_called_once_with({"token": "test-token"})
