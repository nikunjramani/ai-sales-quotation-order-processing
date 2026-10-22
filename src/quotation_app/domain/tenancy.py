"""Tenant context, roles and permissions.

A TenantContext says who is acting, for which business, with which roles. Only a trusted
resolver that has checked stored membership may create one; request fields never grant access.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from uuid import UUID

from quotation_app.domain.validation import require_text


class Role(StrEnum):
    ADMINISTRATOR = "administrator"
    SALES_OPERATOR = "sales_operator"
    APPROVER = "approver"
    VIEWER = "viewer"


class Permission(StrEnum):
    VIEW_QUOTATIONS = "quotations:view"
    DRAFT_QUOTATIONS = "quotations:draft"
    APPROVE_QUOTATIONS = "quotations:approve"
    MANAGE_TENANT = "tenant:manage"


# Administrators do not approve by default: approval is a separate, explicitly granted role.
ROLE_PERMISSIONS: Mapping[Role, frozenset[Permission]] = MappingProxyType(
    {
        Role.ADMINISTRATOR: frozenset(
            {Permission.VIEW_QUOTATIONS, Permission.DRAFT_QUOTATIONS, Permission.MANAGE_TENANT}
        ),
        Role.SALES_OPERATOR: frozenset({Permission.VIEW_QUOTATIONS, Permission.DRAFT_QUOTATIONS}),
        Role.APPROVER: frozenset({Permission.VIEW_QUOTATIONS, Permission.APPROVE_QUOTATIONS}),
        Role.VIEWER: frozenset({Permission.VIEW_QUOTATIONS}),
    }
)


class AuthorizationError(Exception):
    """Base for access failures. Messages never reveal whether another tenant exists."""


class AccessDenied(AuthorizationError):
    """The subject is not a member of the requested tenant."""


class PermissionDenied(AuthorizationError):
    """The subject is a member but lacks the permission for this action."""


@dataclass(frozen=True)
class TenantContext:
    tenant_id: UUID
    subject: str
    roles: frozenset[Role]

    def __post_init__(self) -> None:
        require_text(self.subject, "subject")
        if not self.roles:
            raise ValueError("A tenant context needs at least one role")

    @property
    def permissions(self) -> frozenset[Permission]:
        return frozenset().union(*(ROLE_PERMISSIONS[role] for role in self.roles))

    def require(self, permission: Permission) -> None:
        if permission not in self.permissions:
            raise PermissionDenied(f"Permission {permission} is required")
