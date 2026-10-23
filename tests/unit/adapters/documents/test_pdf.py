"""ReportLab quotation PDFs: faithful amounts, determinism, escaping and refusal to guess."""

from datetime import UTC, datetime
from io import BytesIO
from uuid import uuid4

import pytest
from pypdf import PdfReader

from quotation_app.adapters.documents.pdf import ReportLabQuotationRenderer
from quotation_app.domain.documents import DocumentSource, UnrenderableContent


def content(lines: int = 1, description: str = "Industrial fan 450 mm") -> dict[str, object]:
    return {
        "schema": 1,
        "currency": "INR",
        "policy": {"version": 1, "minor_units": 2, "rounding": "half_up", "tax_rate": "0.18"},
        "lines": [
            {
                "line_index": index,
                "sku": "IND-FAN-450",
                "description": description,
                "quantity": "2",
                "unit": "each",
                "unit_price": "4425.16",
                "line_total": "8850.32",
                "price_list_id": "PL-SECRET-INTERNAL",
                "stock_status": "in_stock",
                "stock_note": "warehouse 7 shelf B",
            }
            for index in range(lines)
        ],
        "subtotal": "8856.25",
        "tax": "1594.13",
        "total": "10450.38",
    }


def source(**changes: object) -> DocumentSource:
    values: dict[str, object] = {
        "tenant_name": "Demo Industrial",
        "quotation_id": uuid4(),
        "version": 1,
        "content": content(),
        "content_sha256": "c" * 64,
        "customer_reference": "PO-2026-17",
        "approved_at": datetime(2026, 10, 23, 9, 30, tzinfo=UTC),
    }
    values.update(changes)
    return DocumentSource(**values)  # type: ignore[arg-type]


def text_of(pdf: bytes) -> str:
    return "\n".join(page.extract_text() for page in PdfReader(BytesIO(pdf)).pages)


@pytest.fixture
def renderer() -> ReportLabQuotationRenderer:
    return ReportLabQuotationRenderer()


def test_pdf_shows_the_approved_amounts_exactly(renderer: ReportLabQuotationRenderer) -> None:
    document = source()
    pdf = renderer.render(document, preview=False)
    assert pdf.startswith(b"%PDF-")
    text = text_of(pdf)
    for expected in (
        "Demo Industrial",
        document.number,
        "version 1",
        "PO-2026-17",
        "Approved on 2026-10-23",
        "IND-FAN-450 - Industrial fan 450 mm",
        "2 each",
        "4425.16",
        "8850.32",
        "8856.25",
        "Tax (18%)",
        "1594.13",
        "Total (INR)",
        "10450.38",
        "cccccccccccccccc",
    ):
        assert expected in text, expected
    assert "PREVIEW" not in text


def test_internal_evidence_stays_out_of_the_customer_document(
    renderer: ReportLabQuotationRenderer,
) -> None:
    text = text_of(renderer.render(source(), preview=False))
    assert "PL-SECRET-INTERNAL" not in text and "warehouse 7" not in text


def test_same_version_gives_identical_bytes(renderer: ReportLabQuotationRenderer) -> None:
    document = source()
    assert renderer.render(document, preview=False) == renderer.render(document, preview=False)


def test_previews_are_marked_as_not_an_offer(renderer: ReportLabQuotationRenderer) -> None:
    text = text_of(renderer.render(source(approved_at=None), preview=True))
    assert "PREVIEW - NOT AN OFFER" in text
    assert "Preview of an unapproved version" in text
    assert "Approved on" not in text


def test_customer_text_is_printed_not_interpreted(renderer: ReportLabQuotationRenderer) -> None:
    hostile = source(
        customer_reference='<font color="red">PO & co</font>',
        content=content(description="<b>Fan</b> & <a href='x'>link</a>"),
    )
    text = text_of(renderer.render(hostile, preview=False))
    assert '<font color="red">PO & co</font>' in text
    assert "<b>Fan</b> & <a href='x'>link</a>" in text


def test_long_quotations_continue_on_more_pages(renderer: ReportLabQuotationRenderer) -> None:
    pdf = renderer.render(source(content=content(lines=60)), preview=False)
    pages = PdfReader(BytesIO(pdf)).pages
    assert len(pages) >= 2
    last = pages[-1].extract_text()
    assert "Total (INR)" in last and "10450.38" in last
    assert "page 2" in pages[1].extract_text()


@pytest.mark.parametrize(
    "changes",
    [
        {"tenant_name": "Demo 工業"},
        {"customer_reference": "PO-✓"},
        {"content": content(description="Fan ⚙")},
    ],
)
def test_unsupported_characters_are_refused_not_replaced(
    renderer: ReportLabQuotationRenderer, changes: dict[str, object]
) -> None:
    with pytest.raises(UnrenderableContent):
        renderer.render(source(**changes), preview=False)


def test_a_version_without_lines_is_refused(renderer: ReportLabQuotationRenderer) -> None:
    empty = content()
    empty["lines"] = []
    with pytest.raises(UnrenderableContent):
        renderer.render(source(content=empty), preview=False)
