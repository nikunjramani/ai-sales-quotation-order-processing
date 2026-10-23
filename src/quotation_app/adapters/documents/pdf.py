"""Quotation PDF renderer using ReportLab (BSD licence, pure Python, no system libraries).

- Deterministic: ReportLab's invariant mode removes timestamps and random IDs, so the same
  version always gives byte-identical files and a retried render overwrites nothing new.
- Faithful: amounts are printed exactly as stored in the version (already rounded by the M1
  calculator); nothing is recalculated here.
- Safe with untrusted text: customer references and descriptions are escaped before ReportLab
  reads its mini-markup, so text like "<b>" or "&" is printed, never interpreted.
- Limited fonts: the built-in Helvetica covers Windows-1252 (Western European) text only. Other
  characters raise UnrenderableContent rather than turning into boxes or question marks.
  Embedding a Unicode font is a recorded gap before real customer data.
- Customer-facing: internal evidence (price list IDs, stock checks, content hash details) stays
  in the portal; the PDF shows prices, totals and a short document reference.
"""

from decimal import Decimal
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from quotation_app.domain.documents import RENDERER_VERSION, DocumentSource, UnrenderableContent

_ENCODING = "cp1252"  # what the standard PDF fonts can show
_PREVIEW_MARK = "PREVIEW - NOT AN OFFER"


def _text(value: object, field: str) -> str:
    text = " ".join(str(value).split())
    try:
        text.encode(_ENCODING)
    except UnicodeEncodeError:
        raise UnrenderableContent(
            f"{field} contains characters the PDF fonts cannot show"
        ) from None
    return text


def _percent(rate: str) -> str:
    value = (Decimal(rate) * 100).normalize()
    return f"{value:f}%"


class ReportLabQuotationRenderer:
    renderer = RENDERER_VERSION

    def __init__(self) -> None:
        styles = getSampleStyleSheet()
        self._title = styles["Title"]
        self._body = styles["BodyText"]
        self._small = ParagraphStyle("small", parent=self._body, fontSize=8, leading=10)
        self._cell = ParagraphStyle("cell", parent=self._body, fontSize=9, leading=11)
        self._number = ParagraphStyle("number", parent=self._cell, alignment=TA_RIGHT)

    def render(self, source: DocumentSource, *, preview: bool) -> bytes:
        content = source.content
        currency = _text(content["currency"], "currency")
        lines = content["lines"]
        if not isinstance(lines, list) or not lines:
            raise UnrenderableContent("The version has no lines")
        tenant = _text(source.tenant_name, "business name")
        reference = (
            "not given"
            if source.customer_reference is None
            else _text(source.customer_reference, "customer reference")
        )

        def cell(value: object, field: str, style: ParagraphStyle | None = None) -> Paragraph:
            return Paragraph(escape(_text(value, field)), style or self._cell)

        rows: list[list[object]] = [
            [
                cell("#", "header"),
                cell("Item", "header"),
                cell("Quantity", "header", self._number),
                cell(f"Unit price ({currency})", "header", self._number),
                cell(f"Amount ({currency})", "header", self._number),
            ]
        ]
        for position, line in enumerate(lines, start=1):
            assert isinstance(line, dict)
            rows.append(
                [
                    cell(position, "position"),
                    cell(f"{line['sku']} - {line['description']}", "item"),
                    cell(f"{line['quantity']} {line['unit']}", "quantity", self._number),
                    cell(line["unit_price"], "unit price", self._number),
                    cell(line["line_total"], "amount", self._number),
                ]
            )
        policy = content["policy"]
        assert isinstance(policy, dict)
        totals = [
            ("Subtotal", content["subtotal"]),
            (f"Tax ({_percent(str(policy['tax_rate']))})", content["tax"]),
            (f"Total ({currency})", content["total"]),
        ]
        for label, amount in totals:
            bold = Paragraph(f"<b>{escape(_text(amount, 'total'))}</b>", self._number)
            rows.append(["", "", "", cell(label, "label", self._number), bold])

        table = Table(rows, colWidths=[10 * mm, 76 * mm, 26 * mm, 32 * mm, 30 * mm], repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LINEBELOW", (0, 0), (-1, 0), 0.8, colors.black),
                    ("LINEBELOW", (0, len(lines)), (-1, len(lines)), 0.5, colors.grey),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
                ]
            )
        )
        status = (
            "Preview of an unapproved version"
            if preview or source.approved_at is None
            else f"Approved on {source.approved_at.date().isoformat()}"
        )
        story = [
            Paragraph(escape(tenant), self._title),
            Paragraph(
                f"<b>Quotation {escape(source.number)}</b>, version {source.version}", self._body
            ),
            Paragraph(f"Your reference: {escape(reference)}", self._body),
            Paragraph(escape(status), self._body),
            Spacer(1, 6 * mm),
            table,
            Spacer(1, 6 * mm),
            Paragraph(
                f"All amounts are in {escape(currency)}. Availability and delivery dates are "
                "confirmed when the order is placed.",
                self._small,
            ),
            Paragraph(f"Document reference: {escape(source.content_sha256[:16])}", self._small),
        ]
        if preview:
            story.insert(0, Paragraph(f"<b>{_PREVIEW_MARK}</b>", self._body))

        def decorate(canvas: Canvas, document: SimpleDocTemplate) -> None:
            canvas.saveState()
            canvas.setFont("Helvetica", 8)
            canvas.drawRightString(
                A4[0] - 18 * mm,
                10 * mm,
                f"{source.number} v{source.version} - page {canvas.getPageNumber()}",
            )
            if preview:
                canvas.setFont("Helvetica-Bold", 40)
                canvas.setFillColor(colors.Color(0.8, 0.1, 0.1, alpha=0.25))
                canvas.translate(A4[0] / 2, A4[1] / 2)
                canvas.rotate(45)
                canvas.drawCentredString(0, 0, _PREVIEW_MARK)
            canvas.restoreState()

        buffer = BytesIO()
        document = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=18 * mm,
            rightMargin=18 * mm,
            topMargin=18 * mm,
            bottomMargin=18 * mm,
            title=f"Quotation {source.number} v{source.version}",
            author=tenant,
            invariant=1,
        )
        document.build(story, onFirstPage=decorate, onLaterPages=decorate)
        return buffer.getvalue()
