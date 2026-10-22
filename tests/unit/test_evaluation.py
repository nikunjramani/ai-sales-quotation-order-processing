"""The synthetic evaluation dataset run against the free rules interpreter (regression gate)."""

from uuid import UUID

import pytest

from quotation_app.adapters.erp.simulated import SimulatedErp
from quotation_app.adapters.interpreters.rules import RulesInterpreter
from quotation_app.evaluation import CaseResult, evaluate, load_cases


@pytest.fixture(scope="module")
def cases_loaded() -> int:
    return len(load_cases())


def run(simulated_erp: SimulatedErp, industrial: UUID, office: UUID) -> list[CaseResult]:
    tenants = {"industrial": industrial, "office": office}
    return evaluate(RulesInterpreter(), simulated_erp, tenants, load_cases())


def test_rules_interpreter_passes_every_case_and_invents_nothing(
    simulated_erp: SimulatedErp, industrial_tenant: UUID, office_tenant: UUID, cases_loaded: int
) -> None:
    results = run(simulated_erp, industrial_tenant, office_tenant)
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
