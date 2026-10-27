from collections.abc import Callable
from uuid import UUID

import pytest

from quotation_app.domain.tenancy import (
    PEOPLE_ROLES,
    Permission,
    PermissionDenied,
    Role,
    TenantContext,
    TenantStatus,
    accepts_intake,
    allows_api_pull,
    allows_changes,
    may_contact_customers,
)

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


def test_only_administrators_manage_integrations(
    make_context: ContextFactory, industrial_tenant: UUID
) -> None:
    holders = {
        role
        for role in Role
        if Permission.MANAGE_INTEGRATIONS in make_context(industrial_tenant, role).permissions
    }
    assert holders == {Role.ADMINISTRATOR}


def test_only_administrators_manage_members(
    make_context: ContextFactory, industrial_tenant: UUID
) -> None:
    holders = {
        role
        for role in Role
        if Permission.MANAGE_MEMBERS in make_context(industrial_tenant, role).permissions
    }
    assert holders == {Role.ADMINISTRATOR}
    assert Role.INTAKE_SERVICE not in PEOPLE_ROLES


@pytest.mark.parametrize(
    ("status", "intake", "customers", "pull", "changes"),
    [
        (TenantStatus.SETTING_UP, True, False, True, True),
        (TenantStatus.ACTIVE, True, True, True, True),
        (TenantStatus.SUSPENDED, False, False, False, False),
    ],
)
def test_status_gates(
    status: TenantStatus, intake: bool, customers: bool, pull: bool, changes: bool
) -> None:
    assert accepts_intake(status) is intake
    assert may_contact_customers(status) is customers
    assert allows_api_pull(status) is pull
    assert allows_changes(status) is changes
