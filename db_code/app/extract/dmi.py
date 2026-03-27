import requests
from datetime import datetime, timezone

class DMIAPI:
    def __init__(self):
        self.base_url = "https://opendataapi.dmi.dk/v2/metObs/collections/observation/items"

    def pull_datetime(self, station_id, parameter_id, limit: int = 5000, offset: int = 0,  start_time: str = "2026-03-09T00:00:00Z", end_time: str ="2030-01-01T00:00:00Z"):
        """The default end time is set far in the future to artificially create a "no end time" query."""
        parameters = {
            "limit": limit,
            "parameterId": parameter_id,
            "stationId": station_id,
            "datetime": start_time,
            "offset": offset
                      }
        if end_time is not None:
            parameters["datetime"] += f"/{end_time}"

        pull_time = datetime.now(timezone.utc)
        pull_time = pull_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        resp = requests.get(self.base_url, params=parameters)

        resp.raise_for_status()
        records = resp.json()
        return pull_time, records["features"]
