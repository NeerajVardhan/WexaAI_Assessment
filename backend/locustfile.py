from locust import HttpUser, between, task


class IngestionUser(HttpUser):
    wait_time = between(0.2, 1.2)

    def on_start(self) -> None:
        self.api_key = "replace-with-wx-live-key"

    @task(5)
    def ingest_single_event(self) -> None:
        self.client.post(
            "/api/v1/ingest/event",
            headers={"X-API-Key": self.api_key},
            json={
                "event_type": "load_test_event",
                "user_external_id": "locust",
                "properties": {"source": "locust", "value": 1},
            },
        )

    @task(1)
    def read_health(self) -> None:
        self.client.get("/api/v1/health")
