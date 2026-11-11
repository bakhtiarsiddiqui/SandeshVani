import uuid

from pydantic import BaseModel, EmailStr

from app.schemas.organization import OrganizationResponse, RoleResponse
from app.schemas.user import UserResponse


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str


class RegisterResponse(BaseModel):
    message: str
    user_id: uuid.UUID


class AuthMessageResponse(BaseModel):
    message: str


class VerifyEmailRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    csrf_token: str


class LoginResponse(TokenResponse):
    user: UserResponse
    active_organization: OrganizationResponse | None = None
    roles: list[RoleResponse] = []
    permissions: list[str] = []


class SelectOrgRequest(BaseModel):
    organization_id: uuid.UUID


class PasswordRecoveryRequest(BaseModel):
    email: EmailStr


class PasswordResetRequest(BaseModel):
    token: str
    new_password: str


class AuthMeResponse(BaseModel):
    user: UserResponse
    active_organization: OrganizationResponse | None = None
    organizations: list[OrganizationResponse] = []
    roles: list[RoleResponse] = []
    permissions: list[str] = []
