"""Contracts for reading tenant membership and tenant-owned configuration."""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from quotation_app.domain.pricing import PricingPolicy
from quotation_app.domain.tenancy import Role, TenantContext


class PricingPolicyNotConfigured(Exception):
    """The tenant has no pricing policy; quotations cannot be calculated safely."""


class MembershipReader(Protocol):
    def roles_for(self, tenant_id: UUID, subject: str) -> frozenset[Role]:
        """Return the subject's roles in this tenant, or an empty set if not a member."""
        ...


class PricingPolicyReader(Protocol):
    def get(self, context: TenantContext) -> PricingPolicy: ...


@dataclass(frozen=True)
class TenantMembership:
    tenant_id: UUID
    tenant_name: str
    roles: frozenset[Role]


class MembershipDirectory(Protocol):
    def tenants_for(self, subject: str) -> list[TenantMembership]:
        """Every tenant where this subject has a membership (used for login and tenant choice)."""
        ...
