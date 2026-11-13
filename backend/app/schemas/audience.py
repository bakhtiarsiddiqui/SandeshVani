import uuid
from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)


class AudienceMemberCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(min_length=1, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(
        default=None,
        min_length=9,
        max_length=16,
        pattern=r"^\+[1-9]\d{7,14}$",
    )
    preferred_language: Literal["en", "hi"] = "en"
    district: str | None = Field(default=None, max_length=150)
    state_code: str | None = Field(default=None, min_length=2, max_length=2, pattern=r"^[A-Z]{2}$")
    city: str | None = Field(default=None, max_length=120)

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("full_name must not be blank")
        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr | None) -> str | None:
        if value is None:
            return None
        return str(value).strip().lower()

    @field_validator("phone", mode="before")
    @classmethod
    def normalize_phone(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("district")
    @classmethod
    def normalize_district(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator("state_code", mode="before")
    @classmethod
    def normalize_state_code(cls, value):
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator("city")
    @classmethod
    def normalize_city(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @model_validator(mode="after")
    def require_contact_point(self):
        if self.email is None and self.phone is None:
            raise ValueError("at least one contact point (email or phone) is required")
        return self


class AudienceMemberUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(
        default=None,
        min_length=9,
        max_length=16,
        pattern=r"^\+[1-9]\d{7,14}$",
    )
    preferred_language: Literal["en", "hi"] | None = None
    district: str | None = Field(default=None, max_length=150)
    state_code: str | None = Field(default=None, min_length=2, max_length=2, pattern=r"^[A-Z]{2}$")
    city: str | None = Field(default=None, max_length=120)
    status: Literal["active", "inactive"] | None = None

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("full_name must not be blank")
        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr | None) -> str | None:
        if value is None:
            return None
        return str(value).strip().lower()

    @field_validator("phone", mode="before")
    @classmethod
    def normalize_phone(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("district")
    @classmethod
    def normalize_district(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator("state_code", mode="before")
    @classmethod
    def normalize_state_code(cls, value):
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator("city")
    @classmethod
    def normalize_city(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @model_validator(mode="after")
    def reject_null_required_fields(self):
        for field_name in ("full_name", "preferred_language", "status"):
            if (
                field_name in self.model_fields_set
                and getattr(self, field_name) is None
            ):
                raise ValueError(f"{field_name} cannot be null")
        return self


class AudienceMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    full_name: str
    email: EmailStr | None
    phone: str | None
    preferred_language: str
    district: str | None
    state_code: str | None
    city: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class AudiencePagination(BaseModel):
    next_cursor: str | None
    has_more: bool
    limit: int


class AudienceMemberListResponse(BaseModel):
    data: list[AudienceMemberResponse]
    pagination: AudiencePagination
