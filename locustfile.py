import random
from locust import HttpUser, task, between


# real complaint IDs from your dataset — grab 5 from your DB
# SELECT unique_key FROM nyc_311_service_requests LIMIT 5;
COMPLAINT_IDS = [40287734, 40935119, 40962915, 41499422, 41680133]

BOROUGHS = ["MANHATTAN", "BROOKLYN", "QUEENS", "BRONX", "STATEN ISLAND"]

COMPLAINT_TYPES = [
    "Noise - Residential",
    "Illegal Parking",
    "HEAT/HOT WATER",
    "Blocked Driveway",
    "Street Light Condition"
]


class AgencyStaffUser(HttpUser):
    # wait 1-3 seconds between requests (realistic user behavior)
    wait_time = between(1, 3)

    # Login on startup
    def on_start(self):
        response = self.client.post("/auth/login", data={
            "username": "kevin@dpr.nyc.gov",
            "password": "Password"
        })
        token = response.json().get("access_token")
        self.headers = {"Authorization": f"Bearer {token}"}

    # 60% — GET /complaints with filters
    @task(6)
    def get_complaints(self):
        borough        = random.choice(BOROUGHS)
        complaint_type = random.choice(COMPLAINT_TYPES)

        self.client.get(
            f"/complaints/?borough={borough}&complaint_type={complaint_type}&page=1&limit=50",
            headers = self.headers,
            name    = "GET /complaints"   # groups results in Locust UI
        )

    # 30% — GET /boroughs/stats
    @task(3)
    def get_borough_stats(self):
        self.client.get(
            "/boroughs/stats",
            headers = self.headers,
            name    = "GET /boroughs/stats"
        )

    # 10% — POST /complaints
    @task(1)
    def create_complaint(self):
        self.client.post(
            "/complaints/",
            json = {
                "complaint_type" : random.choice(COMPLAINT_TYPES),
                "borough"        : random.choice(BOROUGHS),
                "descriptor"     : "Load test complaint",
                "incident_zip"   : "10001",
                "city"           : "New York"
            },
            headers = self.headers,
            name    = "POST /complaints"
        )