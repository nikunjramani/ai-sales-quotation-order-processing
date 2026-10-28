"""Evaluate an enquiry interpreter on the synthetic dataset (evals/enquiry_extraction.jsonl).

Examples:
  uv run python scripts/evaluate_extraction.py                       # free rules interpreter
  uv run python scripts/evaluate_extraction.py --model google_genai:gemini-3.5-flash-lite
      (any "<provider>:<model>"; the key is QUOTATION_MODEL_API_KEY from .env)
  uv run python scripts/evaluate_extraction.py --source local
      (our own product list, holding the same synthetic data, instead of the simulated ERP)
Live model runs are opt-in and use only synthetic data. Exit code 1 if any case fails.
"""

import argparse
from statistics import mean

from quotation_app.adapters.catalogue.local import LocalCatalogue
from quotation_app.adapters.catalogue.memory import InMemoryCatalogueStore
from quotation_app.adapters.erp.simulated import SimulatedErp, demo_catalogues
from quotation_app.adapters.interpreters.factory import build_interpreter
from quotation_app.config import Settings
from quotation_app.evaluation import evaluate, load_cases
from quotation_app.persistence.seed import INDUSTRIAL_TENANT, OFFICE_TENANT
from quotation_app.ports.erp import ErpReader


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", help='"<provider>:<model>"; omit for the rules interpreter')
    parser.add_argument(
        "--source",
        choices=("simulated", "local"),
        default="simulated",
        help="product source: the simulated ERP or our own catalogue (in memory)",
    )
    arguments = parser.parse_args()

    settings = Settings()
    key = settings.model_api_key.get_secret_value() if settings.model_api_key else None
    interpreter = build_interpreter(arguments.model, key, settings.model_options)
    catalogues = demo_catalogues(INDUSTRIAL_TENANT, OFFICE_TENANT)
    erp: ErpReader = (
        SimulatedErp(catalogues)
        if arguments.source == "simulated"
        else LocalCatalogue(InMemoryCatalogueStore.from_simulated(catalogues))
    )
    tenants = {"industrial": INDUSTRIAL_TENANT, "office": OFFICE_TENANT}
    results = evaluate(interpreter, erp, tenants, load_cases())

    for result in results:
        mark = "PASS" if result.passed else "FAIL"
        detail = result.error or result.outcome
        print(f"{mark}  {result.case.name:<32} {detail:<22} {result.seconds:6.2f}s")
        if not result.passed and result.error is None:
            print(
                f"      expected {result.case.expected_outcome.value} "
                f"{list(result.case.expected_lines)}; got {list(result.lines)}"
            )
    passed = sum(result.passed for result in results)
    print(
        f"\nInterpreter: {arguments.model or 'rules (no AI)'}\n"
        f"Product source: {arguments.source}\n"
        f"Cases passed: {passed}/{len(results)}\n"
        f"Invented facts flagged: {sum(result.invented_facts for result in results)}\n"
        f"Errors: {sum(result.error is not None for result in results)}\n"
        f"Mean seconds per case: {mean(result.seconds for result in results):.2f}"
    )
    raise SystemExit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
