"""The synthetic evaluation dataset run against the free rules interpreter (regression gate)."""

from dataclasses import replace
from uuid import UUID

import pytest

from quotation_app.adapters.catalogue.local import LocalCatalogue
from quotation_app.adapters.catalogue.memory import InMemoryCatalogueStore
from quotation_app.adapters.erp.simulated import SimulatedErp, demo_catalogues
from quotation_app.adapters.interpreters.rules import RulesInterpreter
from quotation_app.evaluation import CaseResult, evaluate, load_cases
from quotation_app.ports.erp import ErpReader


@pytest.fixture(scope="module")
def cases_loaded() -> int:
    return len(load_cases())


def run(erp: ErpReader, industrial: UUID, office: UUID) -> list[CaseResult]:
    tenants = {"industrial": industrial, "office": office}
    return evaluate(RulesInterpreter(), erp, tenants, load_cases())


@pytest.mark.parametrize("source", ["simulated", "local"])
def test_rules_interpreter_passes_every_case_and_invents_nothing(
    simulated_erp: SimulatedErp,
    industrial_tenant: UUID,
    office_tenant: UUID,
    cases_loaded: int,
    source: str,
) -> None:
    """Phase 3: our own catalogue holding the same data must give the same answers."""
    erp: ErpReader = simulated_erp
    if source == "local":
        catalogues = demo_catalogues(industrial_tenant, office_tenant)
        erp = LocalCatalogue(InMemoryCatalogueStore.from_simulated(catalogues))
    results = run(erp, industrial_tenant, office_tenant)
    assert cases_loaded >= 10
    failures = [(r.case.name, r.outcome, r.lines, r.error) for r in results if not r.passed]
    assert failures == []
    assert sum(result.invented_facts for result in results) == 0


def test_evaluation_detects_a_wrong_answer(
    simulated_erp: SimulatedErp, industrial_tenant: UUID, office_tenant: UUID
) -> None:
    simulated_erp.failures["search_products"] = RuntimeError("ERP outage")  # type: ignore[assignment]
    results = run(simulated_erp, industrial_tenant, office_tenant)
    assert all(result.error == "RuntimeError" for result in results if result.case.expected_lines)
    assert not all(result.passed for result in results)


def test_expected_question_text_is_checked(
    simulated_erp: SimulatedErp, industrial_tenant: UUID, office_tenant: UUID
) -> None:
    case = next(c for c in load_cases() if c.expected_question)
    wrong = replace(case, expected_question="We supply: Cars")
    tenants = {"industrial": industrial_tenant, "office": office_tenant}
    right, mismatch = evaluate(RulesInterpreter(), simulated_erp, tenants, [case, wrong])
    assert right.passed
    assert not mismatch.passed
