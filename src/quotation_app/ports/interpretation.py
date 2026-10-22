"""Contracts for reading documents and interpreting enquiries.

Swapping AI providers means writing one class that satisfies EnquiryInterpreter; the workflow,
checks and tests do not change. See adapters/interpreters/factory.py.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from quotation_app.domain.catalogue import Product
from quotation_app.domain.requirements import ExtractedRequirements, RequestedItem


@dataclass(frozen=True)
class DocumentText:
    """Text read from an attachment, or the reason it could not be read."""

    name: str
    text: str | None
    unsupported_reason: str | None


class InterpretationRejected(Exception):
    """The model answered, but not in the required shape. Retrying the same input won't help."""


class DocumentReader(Protocol):
    def read(self, name: str, content_type: str, data: bytes) -> DocumentText: ...


class EnquiryInterpreter(Protocol):
    def extract(self, text: str, documents: Sequence[DocumentText]) -> ExtractedRequirements:
        """Read untrusted customer content. Raise InterpretationRejected for invalid output;
        any other exception is treated as temporary (e.g. model unavailable) and retried."""
        ...

    def choose_product(self, item: RequestedItem, candidates: Sequence[Product]) -> str | None:
        """Pick one candidate SKU, or None if unsure. Answers outside candidates are ignored."""
        ...
