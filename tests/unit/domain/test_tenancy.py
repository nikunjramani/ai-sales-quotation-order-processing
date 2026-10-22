from collections.abc import Callable
from uuid import UUID

import pytest

from quotation_app.domain.tenancy import Permission, PermissionDenied, Role, TenantContext

type ContextFactory = Callable[[UUID, Role], TenantContext]


def test_role_permissions_separate_approval_from_administration(
    make_context: ContextFactory, industrial_tenant: UUID
) -> None:
    admin = make_context(industrial_tenant, Role.ADMINISTRATOR)
    approver = make_context(industrial_tenant, Role.APPROVER)
    assert Permission.APPROVE_QUOTATIONS not in admin.permissions
    assert Permission.DRAFT_QUOTATIONS not in approver.permissions
    with pytest.raises(PermissionDenied):
        make_context(industrial_tenant, Role.VIEWER).require(Permission.DRAFT_QUOTATIONS)


def test_permissions_combine_across_roles(industrial_tenant: UUID) -> None:
    both = TenantContext(
        industrial_tenant, "x@example.test", frozenset({Role.ADMINISTRATOR, Role.APPROVER})
    )
    both.require(Permission.APPROVE_QUOTATIONS)
    both.require(Permission.MANAGE_TENANT)


def test_context_requires_roles(industrial_tenant: UUID) -> None:
    with pytest.raises(ValueError, match="role"):
        TenantContext(industrial_tenant, "nobody@example.test", frozenset())
