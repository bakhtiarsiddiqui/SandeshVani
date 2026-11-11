import uuid
from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

T = TypeVar("T", bound=Base)


class TenantRepository(Generic[T]):  # noqa: UP046
    """Base repository for tenant-owned entities.

    Enforces defense-in-depth:
    1. Refuses execution if organization_id is missing.
    2. Explicitly scopes all select/update/delete operations to organization_id.
    3. Works alongside PostgreSQL RLS.
    """

    def __init__(
        self, model: type[T], session: AsyncSession, organization_id: uuid.UUID
    ):
        if not organization_id:
            raise ValueError("TenantRepository requires a valid organization_id")
        self.model = model
        self.session = session
        self.organization_id = organization_id

    def tenant_query(self):
        """Construct a base query filtered by the verified tenant context."""
        return select(self.model).where(
            self.model.organization_id == self.organization_id
        )
