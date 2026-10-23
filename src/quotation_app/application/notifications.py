"""Job handler: send a pending approval task's review packet to bound manager accounts.

Delivery is at least once. A reference is stored before sending and marked sent afterwards; if
sending fails, the retry replaces the unsent token so only the delivered token can act. Each
token is single use, expires, and only works for the account it was sent to.
"""

import logging
import secrets
from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from uuid import UUID

from quotation_app.application.api_keys import hash_secret
from quotation_app.domain.jobs import PermanentJobError
from quotation_app.ports.channels import ApprovalNotifier, NotificationStore
from quotation_app.ports.jobs import ClaimedJob

REFERENCE_LIFETIME = timedelta(hours=24)

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(UTC)


def new_action_token() -> str:
    return secrets.token_urlsafe(24)


class ApprovalNotificationHandler:
    def __init__(
        self,
        store: NotificationStore,
        notifiers: Mapping[str, ApprovalNotifier],
        clock: Callable[[], datetime] = utc_now,
        token_factory: Callable[[], str] = new_action_token,
    ) -> None:
        self._store = store
        self._notifiers = dict(notifiers)
        self._clock = clock
        self._token_factory = token_factory

    def __call__(self, job: ClaimedJob) -> None:
        try:
            task_id = UUID(job.payload["task_id"])
        except (KeyError, ValueError):
            raise PermanentJobError("Job payload has no valid task_id") from None
        packet = self._store.review_packet(job.tenant_id, task_id)
        if packet is None:
            return  # decided or gone: nothing to announce
        for binding in self._store.approver_bindings(job.tenant_id):
            notifier = self._notifiers.get(binding.channel)
            if notifier is None:
                logger.warning("No notifier configured for channel %s", binding.channel)
                continue
            token = self._token_factory()
            expires_at = self._clock() + REFERENCE_LIFETIME
            reference_id = self._store.prepare_reference(
                job.tenant_id, task_id, binding.binding_id, hash_secret(token), expires_at
            )
            if reference_id is None:
                continue  # already delivered on an earlier attempt
            notifier.send_review(binding, packet, token, expires_at)
            self._store.mark_sent(job.tenant_id, reference_id)
