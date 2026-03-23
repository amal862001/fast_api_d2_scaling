from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext
from models.user import Base, PlatformUser
from config import settings

# database connection
engine = create_engine(f"postgresql+psycopg2://{settings.DB_USER}:{settings.DB_PASSWORD}@db:{settings.DB_PORT}/{settings.DB_NAME}")
Session = sessionmaker(bind=engine)
session = Session()

# password hasher
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Agency definitions
AGENCIES = [
    "NYPD", "DOT", "DSNY", "DEP", "HPD",
    "FDNY", "DOB", "DHS", "DPR", "DOITT",
    "DEP",  "DOF", "DOH", "DCP", "DCAS",
    "DFTA", "DYCD", "ACS", "SBS",  "TLC"
]

FIRST_NAMES = [
    "James", "Maria", "David", "Sarah", "Michael",
    "Emily", "Robert", "Lisa",  "Kevin", "Admin",
    "John",  "Anna",  "Chris", "Laura", "Daniel",
    "Emma",  "Mark",  "Sofia", "Peter", "Grace",
    "Tyler", "Nadia", "Brian", "Chloe", "Victor",
    "Maya",  "Aaron", "Zoe",   "Eric",  "Isla",
    "Noah",  "Lily",  "Ryan",  "Ava",   "Sean",
    "Mia",   "Luke",  "Ella",  "Owen",  "Nora",
    "Jake",  "Ruby",  "Adam",  "Leah",  "Cole",
    "Aria",  "Dean",  "Nina",  "Joel",  "Vera",
]

LAST_NAMES = [
    "Carter",   "Lopez",    "Kim",      "Johnson",  "Brown",
    "Davis",    "Wilson",   "Martinez", "Thompson", "User",
    "Smith",    "Jones",    "Taylor",   "Anderson", "Thomas",
    "Jackson",  "White",    "Harris",   "Martin",   "Garcia",
    "Miller",   "Robinson", "Clark",    "Lewis",    "Lee",
    "Walker",   "Hall",     "Allen",    "Young",    "King",
    "Wright",   "Scott",    "Green",    "Baker",    "Adams",
    "Nelson",   "Hill",     "Rivera",   "Campbell", "Mitchell",
    "Roberts",  "Turner",   "Phillips", "Parker",   "Evans",
    "Edwards",  "Collins",  "Stewart",  "Morris",   "Rogers",
]

# Original 10 seeded users
original_users = [
    {"full_name": "James Carter",   "email": "james@nypd.nyc.gov",   "agency_code": "NYPD",  "role": "staff"},
    {"full_name": "Maria Lopez",    "email": "maria@dot.nyc.gov",    "agency_code": "DOT",   "role": "staff"},
    {"full_name": "David Kim",      "email": "david@dsny.nyc.gov",   "agency_code": "DSNY",  "role": "staff"},
    {"full_name": "Sarah Johnson",  "email": "sarah@dep.nyc.gov",    "agency_code": "DEP",   "role": "staff"},
    {"full_name": "Michael Brown",  "email": "michael@hpd.nyc.gov",  "agency_code": "HPD",   "role": "staff"},
    {"full_name": "Emily Davis",    "email": "emily@fdny.nyc.gov",   "agency_code": "FDNY",  "role": "staff"},
    {"full_name": "Robert Wilson",  "email": "robert@dob.nyc.gov",   "agency_code": "DOB",   "role": "staff"},
    {"full_name": "Lisa Martinez",  "email": "lisa@dhs.nyc.gov",     "agency_code": "DHS",   "role": "staff"},
    {"full_name": "Kevin Thompson", "email": "kevin@dpr.nyc.gov",    "agency_code": "DPR",   "role": "analyst"},
    {"full_name": "Admin User",     "email": "admin@doitt.nyc.gov",  "agency_code": "DOITT", "role": "admin"},
]

# Generate 90 additional users
generated_users = []
used_emails     = {u["email"] for u in original_users}

for i in range(90):
    first     = FIRST_NAMES[i % len(FIRST_NAMES)]
    last      = LAST_NAMES[i % len(LAST_NAMES)]
    agency    = AGENCIES[i % len(AGENCIES)]
    role      = "admin" if i % 20 == 0 else "staff"

    # unique email — append number if collision
    base_email = f"{first.lower()}.{last.lower()}@{agency.lower()}.nyc.gov"
    email      = base_email
    counter    = 1
    while email in used_emails:
        email = f"{first.lower()}.{last.lower()}{counter}@{agency.lower()}.nyc.gov"
        counter += 1

    used_emails.add(email)
    generated_users.append({
        "full_name"  : f"{first} {last}",
        "email"      : email,
        "agency_code": agency,
        "role"       : role
    })

all_users = original_users + generated_users

# Seed all 100 users 
seeded = 0
for u in all_users:
    # skip if email already exists in DB
    existing = session.query(PlatformUser).filter_by(email=u["email"]).first()
    if existing:
        continue

    user = PlatformUser(
        full_name       = u["full_name"],
        email           = u["email"],
        hashed_password = pwd_context.hash("Password"),
        agency_code     = u["agency_code"],
        role            = u["role"]
    )
    session.add(user)
    seeded += 1

session.commit()
session.close()
print(f"{seeded} users seeded  ({len(all_users)} total attempted)")