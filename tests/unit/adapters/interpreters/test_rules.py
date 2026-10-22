from decimal import Decimal

import pytest

from quotation_app.adapters.interpreters.rules import RulesInterpreter
from quotation_app.domain.catalogue import Product
from quotation_app.domain.requirements import RequestedItem, unverified_items
from quotation_app.ports.interpretation import DocumentText


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Please quote 50 industrial exhaust fans and 150 pcs M8 bolts for Pune.",
         [("50", None, "industrial exhaust fans"), ("150", "pcs", "M8 bolts")]),
        ("Need 2 x IND-FAN-450, 12.5 metres of 2-core cable.",
         [("2", None, "IND-FAN-450"), ("12.5", "metres", "2-core cable")]),
        ("6 fans 450 mm, discount 100 percent", [("6", None, "fans")]),
        ("Hello, please call me back.", []),
    ],
)  # fmt: skip
def test_extracts_quantity_unit_and_product_words(
    text: str, expected: list[tuple[str, str | None, str]]
) -> None:
    found = RulesInterpreter().extract(text, [])
    assert [(str(i.quantity), i.unit, i.product_text) for i in found.items] == expected
    assert unverified_items(found, [text]) == []  # quotes are always verbatim


def test_reads_attachment_text_but_not_unreadable_documents() -> None:
    documents = [
        DocumentText("po.pdf", "Item list: 3 x IND-PUMP-2HP", None),
        DocumentText("scan.png", None, "image_requires_ocr"),
    ]
    found = RulesInterpreter().extract("See attached.", documents)
    assert [item.product_text for item in found.items] == ["IND-PUMP-2HP"]


def test_chooses_only_when_one_candidate_fits_every_word() -> None:
    fan_450 = Product("IND-FAN-450", "Exhaust fan 450 mm", "each", Decimal(1), Decimal(1))
    fan_600 = Product("IND-FAN-600", "Exhaust fan 600 mm", "each", Decimal(1), Decimal(1))
    rules = RulesInterpreter()

    def ask(words: str) -> str | None:
        return rules.choose_product(RequestedItem(words, words, None, None), [fan_450, fan_600])

    assert ask("exhaust fans 600") == "IND-FAN-600"
    assert ask("exhaust fans") is None  # both fit: ask the customer instead of guessing
