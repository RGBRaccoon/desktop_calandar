import json

import httplib2
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_httplib2 import AuthorizedHttp
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


class LoginRequired(Exception):
    pass


class GoogleAuthService:
    def __init__(self, store, credential_factory=None):
        self.store = store
        self.credential_factory = credential_factory or (
            lambda value: Credentials.from_authorized_user_info(value, SCOPES)
        )

    def credentials(self):
        data = self.store.load()
        if not data:
            raise LoginRequired("설정에서 Google 계정을 연결하세요.")
        try:
            credentials = self.credential_factory(data)
        except (ValueError, KeyError) as error:
            raise LoginRequired("Google 계정을 다시 연결하세요.") from error
        if not credentials.valid:
            if not credentials.refresh_token:
                raise LoginRequired("Google 계정을 다시 연결하세요.")
            try:
                credentials.refresh(Request())
            except RefreshError as error:
                raise LoginRequired(
                    "인증이 만료되었습니다. Google 계정을 다시 연결하세요."
                ) from error
            self.store.save(json.loads(credentials.to_json()))
        return credentials

    def login(self, client_file: str):
        flow = InstalledAppFlow.from_client_secrets_file(
            client_file, SCOPES, autogenerate_code_verifier=True
        )
        credentials = flow.run_local_server(
            host="127.0.0.1",
            port=0,
            timeout_seconds=120,
            authorization_prompt_message="",
            success_message="연결이 완료되었습니다. 이 창을 닫으세요.",
            access_type="offline",
            prompt="consent",
        )
        self.store.save(json.loads(credentials.to_json()))

    def api(self):
        http = AuthorizedHttp(self.credentials(), http=httplib2.Http(timeout=20))
        return build("calendar", "v3", http=http, cache_discovery=False)

    def logout(self):
        self.store.delete()
