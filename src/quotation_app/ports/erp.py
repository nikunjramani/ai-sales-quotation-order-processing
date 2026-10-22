"""ERP read contract. Every ERP adapter, simulated or real, must pass the shared contract suite.

Rules for implementations:
- Scope every call to context.tenant_id; never return another tenant's records.
- Omit unknown SKUs from results. Never return placeholder zero prices or stock.
- Stamp results with source and a timezone-aware fetched_at.
- Raise ErpError with a normalized code on failure; never fabricate a successful result.
"""

from collections.abc import Mapping, Sequence
from datetime import datetime
from enum import StrEnum
from typing import Protocol

from quotation_app.domain.catalogue import PriceQuote, Product, StockLevel
from quotation_app.domain.tenancy import TenantContext


class ErpErrorCode(StrEnum):
    NOT_FOUND = "not_found"
    UNSUPPORTED = "unsupported"
    UNAUTHENTICATED = "unauthenticated"
    FORBIDDEN = "forbidden"
    RATE_LIMITED = "rate_limited"
    TEMPORARY_UNAVAILABLE = "temporary_unavailable"
    INVALID_REQUEST = "invalid_request"
    CONFLICT = "conflict"
    UNKNOWN_OUTCOME = "unknown_outcome"


_RETRYABLE = frozenset({ErpErrorCode.RATE_LIMITED, ErpErrorCode.TEMPORARY_UNAVAILABLE})


class ErpError(Exception):
    def __init__(self, code: ErpErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code

    @property
    def retryable(self) -> bool:
        """Safe to retry later for reads. Writes with unknown_outcome need reconciliation."""
        return self.code in _RETRYABLE


class ErpReader(Protocol):
    def search_products(
        self, context: TenantContext, query: str, limit: int = 10
    ) -> Sequence[Product]: ...

    def get_products(self, context: TenantContext, skus: Sequence[str]) -> Mapping[str, Product]:
        """Return known products keyed by SKU; unknown SKUs are absent."""
        ...

    def get_prices(
        self,
        context: TenantContext,
        skus: Sequence[str],
        currency: str,
        effective_at: datetime,
    ) -> Mapping[str, PriceQuote]:
        """Return the price effective at effective_at in currency; absent if none exists."""
        ...

    def get_availability(
        self, context: TenantContext, skus: Sequence[str], warehouse: str | None = None
    ) -> Mapping[str, StockLevel]: ...
