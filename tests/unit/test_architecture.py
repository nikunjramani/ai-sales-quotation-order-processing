"""Import-boundary checks so business rules stay independent of frameworks and providers."""

import ast
import sys
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parents[2] / "src" / "quotation_app"

# Layer -> internal layers it may import. Third-party imports are forbidden in these layers.
ALLOWED = {
    "domain": {"domain"},
    "ports": {"domain", "ports"},
    "application": {"domain", "ports", "application"},
    "adapters": {"domain", "ports", "adapters"},
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
                allowed = parts[0] in sys.stdlib_module_names
            if not allowed:
                violations.append(f"{path.relative_to(PACKAGE)} imports {name}")
    assert violations == []
