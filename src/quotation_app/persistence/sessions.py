"""Portal session storage (API role). RLS exposes only the row whose token hash is presented."""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from uuid import UUID

from sqlalchemy import Connection, Engine, func, insert, select, text, update

from quotation_app.persistence.models import UserSession
from quotation_app.ports.identity import SessionRecord, VerifiedIdentity


class SqlSessionStore:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    @contextmanager
    def _for_token(self, token_sha256: str) -> Iterator[Connection]:
        with self._engine.begin() as connection:
            connection.execute(
                text("SELECT set_config('app.session_token_sha256', :value, true)"),
                {"value": token_sha256},
            )
            yield connection

    def create(
        self,
        session_id: UUID,
        token_sha256: str,
        identity: VerifiedIdentity,
        expires_at: datetime,
    ) -> None:
        with self._engine.begin() as connection:
            connection.execute(
                insert(UserSession).values(
                    id=session_id,
                    token_sha256=token_sha256,
                    subject=identity.subject,
                    provider=identity.provider,
                    expires_at=expires_at,
                )
            )

    def find(self, token_sha256: str) -> SessionRecord | None:
        with self._for_token(token_sha256) as connection:
            row = connection.execute(
                select(
                    UserSession.id,
                    UserSession.subject,
                    UserSession.provider,
                    UserSession.expires_at,
                    UserSession.revoked_at,
                ).where(UserSession.token_sha256 == token_sha256)
            ).one_or_none()
        if row is None:
            return None
        return SessionRecord(
            session_id=row.id,
            subject=row.subject,
            provider=row.provider,
            expires_at=row.expires_at,
            revoked=row.revoked_at is not None,
        )

    def revoke(self, token_sha256: str) -> None:
        with self._for_token(token_sha256) as connection:
            connection.execute(
                update(UserSession)
                .where(UserSession.token_sha256 == token_sha256, UserSession.revoked_at.is_(None))
                .values(revoked_at=func.now())
            )
