"""Package boundaries (ADR-0021): only `source` knows the World Bank.

`storage` imports nothing from the project; `warehouse` imports only `storage`; `source` imports
only `storage` (to land runs), never the top-level `config` or `cli`. Any package may read the
package version from `worldbank` itself.
"""

import ast
from pathlib import Path

import pytest

PACKAGE = Path(__file__).parents[1] / "src" / "worldbank"

ALLOWED = {
    "source": {"worldbank.source", "worldbank.storage"},
    "storage": {"worldbank.storage"},
    "warehouse": {"worldbank.storage", "worldbank.warehouse"},
}
PACKAGE_ROOT = "worldbank"  # `from worldbank import __version__` is allowed everywhere


def project_imports(module: Path) -> set[str]:
    found = set()
    for node in ast.walk(ast.parse(module.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.add(node.module)
    return {name for name in found if name == "worldbank" or name.startswith("worldbank.")}


@pytest.mark.parametrize("package", sorted(ALLOWED))
def test_packages_only_import_what_they_may(package: str) -> None:
    modules = sorted((PACKAGE / package).glob("*.py"))
    assert modules, f"no modules found in {package}"
    violations = {
        f"{module.name}: {name}"
        for module in modules
        for name in project_imports(module)
        if name != PACKAGE_ROOT
        and not any(
            name == allowed or name.startswith(allowed + ".") for allowed in ALLOWED[package]
        )
    }
    assert not violations, f"{package} imports outside its boundary: {sorted(violations)}"
