import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.user import UserResponse


class OrganizationBase(BaseModel):
    name: str
    slug: str


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationResponse(OrganizationBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    created_at: datetime


class PermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    description: str


class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID | None = None
    name: str
    description: str
    is_system_role: bool
    permissions: list[PermissionResponse] = []


class MembershipRoleSummary(BaseModel):
    role_id: uuid.UUID
    name: str


class MembershipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    user_id: uuid.UUID
    status: str
    joined_at: datetime
    user: UserResponse | None = None
    roles: list[RoleResponse] = []


class MemberAddRequest(BaseModel):
    email: str
    role_ids: list[uuid.UUID] = []


class RoleAssignRequest(BaseModel):
    role_id: uuid.UUID
