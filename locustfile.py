import random
from locust import HttpUser, task, between

COMPLAINT_IDS = [40287734, 40935119, 40962915, 41499422, 41680133]

BOROUGHS = ["MANHATTAN", "BROOKLYN", "QUEENS", "BRONX", "STATEN ISLAND"]

COMPLAINT_TYPES = [
    "Noise - Residential",
    "Illegal Parking",
    "HEAT/HOT WATER",
    "Blocked Driveway",
    "Street Light Condition"
]

# all 10 seeded users — Locust picks one randomly per simulated user
USERS = [
    {"username": "james@nypd.nyc.gov",   "password": "Password"},
    {"username": "maria@dot.nyc.gov",    "password": "Password"},
    {"username": "david@dsny.nyc.gov",   "password": "Password"},
    {"username": "sarah@dep.nyc.gov",    "password": "Password"},
    {"username": "michael@hpd.nyc.gov",  "password": "Password"},
    {"username": "emily@fdny.nyc.gov",   "password": "Password"},
    {"username": "robert@dob.nyc.gov",   "password": "Password"},
    {"username": "lisa@dhs.nyc.gov",     "password": "Password"},
    {"username": "kevin@dpr.nyc.gov",    "password": "Password"},
    {"username": "admin@doitt.nyc.gov",  "password": "Password"},
]


class AgencyStaffUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        # each simulated user picks a random agency account
        user     = random.choice(USERS)
        response = self.client.post("/auth/login", data={
            "username": user["username"],
            "password": user["password"]
        })
        token        = response.json().get("access_token")
        self.headers = {"Authorization": f"Bearer {token}"}
        self.agency  = user["username"].split("@")[1].split(".")[0].upper()

    @task(6)
    def get_complaints(self):
        borough        = random.choice(BOROUGHS)
        complaint_type = random.choice(COMPLAINT_TYPES)
        self.client.get(
            f"/complaints/?borough={borough}&complaint_type={complaint_type}&page=1&limit=50",
            headers = self.headers,
            name    = "GET /complaints"
        )

    @task(3)
    def get_borough_stats(self):
        self.client.get(
            "/boroughs/stats",
            headers = self.headers,
            name    = "GET /boroughs/stats"
        )

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