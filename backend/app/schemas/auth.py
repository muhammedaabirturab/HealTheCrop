from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole


class RegisterRequest(BaseModel):
    # Deliberately no `role` field: the public registration endpoint must never let
    # a caller self-assign a role. Every account created this way is a farmer;
    # admin accounts exist only via the startup seed (see app/core/admin_seed.py).
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    phone: str | None = None
    location: str | None = None
    preferred_language: str = "en"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    user: "UserResponse"


class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: UserRole
    location: str | None = None
    preferred_language: str

    model_config = {"from_attributes": True}


TokenResponse.model_rebuild()
