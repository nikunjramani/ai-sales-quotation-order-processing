"""Durable job states and retry timing.

A job is a row in the database describing work to do later. Workers lease a job (temporary
ownership) so a crashed worker's job becomes available again when the lease expires.
"""

from collections.abc import Callable
from datetime import timedelta
from enum import StrEnum


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    DEAD = "dead"


class JobKind(StrEnum):
    PREPARE_ENQUIRY = "prepare_enquiry"


class PermanentJobError(Exception):
    """Retrying cannot help (e.g. referenced data missing). The job goes straight to dead."""


def retry_delay(
    attempt: int,
    *,
    base: timedelta = timedelta(seconds=5),
    cap: timedelta = timedelta(minutes=10),
    jitter: Callable[[], float],
) -> timedelta:
    """Exponential backoff with full jitter: random between 0 and min(cap, base * 2^(n-1)).

    Jitter spreads retries out so many failed jobs do not hit a recovering service together.
    `jitter` returns a float in [0, 1); tests pass a fixed value.
    """
    if attempt < 1:
        raise ValueError("attempt starts at 1")
    ceiling = min(cap, base * (1 << min(attempt - 1, 30)))
    return ceiling * jitter()
