"""Public Desktop OAuth app registration, never user credentials."""

import json
from pathlib import Path


class OAuthConfigurationError(Exception):
    pass


def load_client_config(path: Path | None = None) -> dict:
    # PyInstaller preserves this package-relative location in its extraction directory.
    path = path or Path(__file__).resolve().parents[1] / "resources" / "oauth_client.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as error:
        raise OAuthConfigurationError(
            "Google 로그인 설정이 포함되지 않은 앱입니다. 배포자에게 로그인 설정이 포함된 실행 파일을 요청하세요."
        ) from error
    allowed = {
        "client_id",
        "project_id",
        "auth_uri",
        "token_uri",
        "auth_provider_x509_cert_url",
        "client_secret",
        "redirect_uris",
        "universe_domain",
    }
    installed = data.get("installed") if isinstance(data, dict) else None
    if (
        not isinstance(installed, dict)
        or set(data) != {"installed"}
        or not set(installed).issubset(allowed)
        or not isinstance(installed.get("client_id"), str)
        or not installed["client_id"].endswith(".apps.googleusercontent.com")
        or not isinstance(installed.get("client_secret"), str)
        or not installed["client_secret"]
        or installed.get("auth_uri")
        not in (
            "https://accounts.google.com/o/oauth2/auth",
            "https://accounts.google.com/o/oauth2/v2/auth",
        )
        or installed.get("token_uri") != "https://oauth2.googleapis.com/token"
    ):
        raise OAuthConfigurationError(
            "배포용 Google 로그인 설정이 올바르지 않습니다. Google Cloud의 데스크톱 앱 OAuth JSON이 필요합니다."
        )
    return data
