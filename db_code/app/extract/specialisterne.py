import requests
from datetime import datetime, timezone
from db_code.app.config import spec_token

class SpecAPI:
    def __init__(self):
        self.base_url = "https://climate.spac.dk/api/records"
        self.token = spec_token
        self.header = {"Authorization": f"Bearer {self.token}"}

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
