import requests
from datetime import datetime, timezone
from db_code.app.config import new_spec_token

import ssl
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

class LegacyTLSAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ctx = create_urllib3_context(ciphers="DEFAULT:@SECLEVEL=1")
        ctx.options |= ssl.OP_LEGACY_SERVER_CONNECT
        kwargs["ssl_context"] = ctx
        return super().init_poolmanager(*args, **kwargs)

class NewSpecAPI:
    def __init__(self):
        self.base_url = "https://herodot.spac.dk/api/records"
        self.token = new_spec_token
        self.header = {"Authorization": f"Bearer {self.token}"}
        self.session = requests.Session()
        self.session.mount("https://", LegacyTLSAdapter())

    def pull_from(self, limit: int = 5000, from_time: str = "2026-03-09T00:00:00Z"):
        parameters = {
            "limit": limit,  # max number of records to fetch
            "from": from_time  # start timestamp
        }
        pull_time = datetime.now(timezone.utc)
        pull_time = pull_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        resp = requests.get(self.base_url, headers=self.header, params=parameters)

        resp.raise_for_status()
        data = resp.json()
        records = data.get("records", [])
        return pull_time, records