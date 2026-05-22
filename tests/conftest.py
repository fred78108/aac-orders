"""
Shared session-scoped fixtures for the aac-orders test suite.

All diagram source and documentation files are read once per
pytest session and cached, so repeated fixture use across
modules costs no extra I/O.
"""

import pathlib

import pytest


_ROOT = pathlib.Path(__file__).parent.parent
_DOCS = _ROOT / "docs" / "architecture"
_ADR = _DOCS / "decisions"
_DIAGRAMS = _DOCS / "diagrams"
_GENERATED = _DOCS / "generated"


@pytest.fixture(scope="session")
def project_root() -> pathlib.Path:
    """Return the absolute path to the project root directory."""
    return _ROOT


@pytest.fixture(scope="session")
def docs_architecture() -> pathlib.Path:
    """Return the path to docs/architecture/."""
    return _DOCS


@pytest.fixture(scope="session")
def adr_dir() -> pathlib.Path:
    """Return the path to docs/architecture/decisions/."""
    return _ADR


@pytest.fixture(scope="session")
def diagrams_dir() -> pathlib.Path:
    """Return the path to docs/architecture/diagrams/."""
    return _DIAGRAMS


@pytest.fixture(scope="session")
def generated_dir() -> pathlib.Path:
    """Return the path to docs/architecture/generated/."""
    return _GENERATED


@pytest.fixture(scope="session")
def event_flow_src(diagrams_dir: pathlib.Path) -> str:
    """Return the source text of event_flow.py."""
    return (diagrams_dir / "event_flow.py").read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def deployment_src(diagrams_dir: pathlib.Path) -> str:
    """Return the source text of deployment.py."""
    return (diagrams_dir / "deployment.py").read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def service_overview_src(diagrams_dir: pathlib.Path) -> str:
    """Return the source text of service_overview.py."""
    return (diagrams_dir / "service_overview.py").read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def arch_readme(docs_architecture: pathlib.Path) -> str:
    """Return the text of docs/architecture/README.md."""
    return (docs_architecture / "README.md").read_text(encoding="utf-8")
