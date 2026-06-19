from locust import HttpUser, between, task


class MedVoicePilotUser(HttpUser):
    wait_time = between(1, 5)

    @task(4)
    def health(self):
        self.client.get("/api/v1/health")

    @task(3)
    def admin_overview(self):
        self.client.get("/api/v1/admin/overview")

    @task(2)
    def admin_calls(self):
        self.client.get("/api/v1/admin/calls")

    @task(1)
    def admin_quality(self):
        self.client.get("/api/v1/admin/quality")
