"""Delivery for enquiries that arrived through the intake API (a pull channel).

API clients are other systems; we do not push files to them. "Delivering" means making the
approved document available: from then on the client can fetch it with
GET /api/v1/enquiries/{id}/quotation(.pdf) using its API key, and the first download is
recorded. Nothing can fail here, so it never raises.
"""

from quotation_app.domain.intake import Channel
from quotation_app.ports.documents import DeliveryReceipt, DeliveryRequest, ReceiptKind


class ApiPullDelivery:
    channel = Channel.API.value

    def deliver(self, request: DeliveryRequest, document: bytes) -> DeliveryReceipt:
        return DeliveryReceipt(ReceiptKind.AVAILABLE)
