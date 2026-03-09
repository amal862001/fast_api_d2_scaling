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

# 10 agency staff accounts
users = [
    {"full_name": "James Carter",   "email": "james@nypd.nyc.gov",   "agency_code": "NYPD",  "role": "staff"},
    {"full_name": "Maria Lopez",    "email": "maria@dot.nyc.gov",    "agency_code": "DOT",   "role": "staff"},
    {"full_name": "David Kim",      "email": "david@dsny.nyc.gov",   "agency_code": "DSNY",  "role": "staff"},
    {"full_name": "Sarah Johnson",  "email": "sarah@dep.nyc.gov",    "agency_code": "DEP",   "role": "staff"},
    {"full_name": "Michael Brown",  "email": "michael@hpd.nyc.gov",  "agency_code": "HPD",   "role": "staff"},
    {"full_name": "Emily Davis",    "email": "emily@fdny.nyc.gov",   "agency_code": "FDNY",  "role": "staff"},
    {"full_name": "Robert Wilson",  "email": "robert@dob.nyc.gov",   "agency_code": "DOB",   "role": "staff"},
    {"full_name": "Lisa Martinez",  "email": "lisa@dhs.nyc.gov",     "agency_code": "DHS",   "role": "staff"},
    {"full_name": "Kevin Thompson", "email": "kevin@dpr.nyc.gov",    "agency_code": "DPR",   "role": "staff"},
    {"full_name": "Admin User",     "email": "admin@doitt.nyc.gov",  "agency_code": "DOITT", "role": "admin"},
]

for u in users:
    user = PlatformUser(
        full_name       = u["full_name"],
        email           = u["email"],
        hashed_password = pwd_context.hash("Password"),
        agency_code     = u["agency_code"],
        role            = u["role"]
    )
    session.add(user)

session.commit()
session.close()
print("10 agency users seeded ✅")