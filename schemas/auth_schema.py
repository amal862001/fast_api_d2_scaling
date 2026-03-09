from pydantic import BaseModel, EmailStr

# Request Schemas

# The data user sends when registering a new account. The role defaults to "staff" if not provided.
class RegisterRequest(BaseModel):
    full_name   : str
    email       : EmailStr
    password    : str
    agency_code : str
    role        : str = "staff"

# The data user sends when logging in. Only email and password are required.
class LoginRequest(BaseModel):
    email    : EmailStr
    password : str


# Response Schemas

# The data user receives when logging in. Contains the access token and token type.
class TokenResponse(BaseModel):
    access_token : str
    token_type   : str = "bearer"


# The data user receives when accessing their own user information.
class UserResponse(BaseModel):
    id          : int
    full_name   : str
    email       : str
    agency_code : str
    role        : str

    class Config:
        from_attributes = True