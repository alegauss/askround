"""AR39: askround runs on a Python 3.11+ interpreter and nothing else.

Every provider is one HTTPS call through the standard library, so `pip install askround`
installs nothing beside it and the plugin runs with only Python present. A third-party
import anywhere in the package would break both, and an SDK pulled in for one provider
would be a requirement for every user; these tests fail on either.
"""

from __future__ import annotations

import ast
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).parent.parent
PACKAGE = ROOT / "plugin" / "src" / "askround"


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.add(node.module.split(".")[0])
    return found


def test_the_package_imports_only_the_standard_library_and_itself():
    allowed = set(sys.stdlib_module_names) | {"askround", "__future__"}
    foreign = {path.name: sorted(_imports(path) - allowed) for path in sorted(PACKAGE.glob("*.py"))}
    assert not {name: mods for name, mods in foreign.items() if mods}


def test_the_distribution_declares_no_runtime_dependency():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert project["dependencies"] == []
    assert project["requires-python"] == ">=3.11"
    # extras are for development only; a provider SDK would have to be optional, never this
    assert set(project.get("optional-dependencies", {})) <= {"dev"}
