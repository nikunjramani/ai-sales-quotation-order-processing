"""Import-boundary checks so business rules stay independent of frameworks and providers."""

import ast
import sys
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parents[2] / "src" / "quotation_app"

# Layer -> internal layers it may import.
ALLOWED = {
    "domain": {"domain"},
    "ports": {"domain", "ports"},
    "application": {"domain", "ports", "application"},
    "adapters": {"domain", "ports", "adapters"},
    "workflows": {"domain", "ports", "application", "workflows"},
}
# Layer -> third-party packages it may import. Domain, ports and application use only stdlib,
# so business rules never depend on a framework, database or AI provider.
THIRD_PARTY = {
    "adapters": {
        "pypdf",
        "reportlab",
        "langchain_core",
        "langchain_ollama",
        "langchain_google_genai",
        "pydantic",
    },
    "workflows": {"langgraph", "langchain_core"},
}


def _imports(path: Path) -> list[str]:
    names: list[str] = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.append(node.module)
    return names


@pytest.mark.parametrize("layer", sorted(ALLOWED))
def test_layer_imports_respect_boundaries(layer: str) -> None:
    files = sorted((PACKAGE / layer).rglob("*.py"))
    assert files, f"no source files found for {layer}"
    violations = []
    for path in files:
        for name in _imports(path):
            parts = name.split(".")
            if parts[0] == "quotation_app":
                allowed = len(parts) > 1 and parts[1] in ALLOWED[layer]
            else:
                allowed = parts[0] in sys.stdlib_module_names or parts[0] in THIRD_PARTY.get(
                    layer, set()
                )
            if not allowed:
                violations.append(f"{path.relative_to(PACKAGE)} imports {name}")
    assert violations == []
