"""Login and session contracts, independent of the identity provider.

An identity provider (the dev login now, OIDC later) only proves who someone is and returns a
VerifiedIdentity. Sessions, tenant membership and permissions are the same for every provider.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from quotation_app.domain.validation import require_text


class IdentityRejected(Exception):
    """The provider could not verify the person. One message for every reason."""


@dataclass(frozen=True)
class VerifiedIdentity:
    subject: str  # stable user ID from the provider (OIDC "sub"; the dev login uses an email)
    provider: str

    def __post_init__(self) -> None:
        require_text(self.subject, "subject")
        require_text(self.provider, "provider", 32)


@dataclass(frozen=True)
class SessionRecord:
    session_id: UUID
    subject: str
    provider: str
    expires_at: datetime
    revoked: bool


class SessionStore(Protocol):
    """Only a SHA-256 hash of the session token is stored."""

    def create(
        self,
        session_id: UUID,
        token_sha256: str,
        identity: VerifiedIdentity,
        expires_at: datetime,
    ) -> None: ...

    def find(self, token_sha256: str) -> SessionRecord | None: ...

    def revoke(self, token_sha256: str) -> None: ...
