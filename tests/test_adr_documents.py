"""
Tests for Architecture Decision Record (ADR) documents.

Validates that all seven ADRs exist under
docs/architecture/decisions/, follow the MADR structure
(Status, Date, Deciders, Context, Decision Outcome,
Consequences), are marked Accepted, and name the correct
technology in their decision outcome.
"""

import pathlib

import pytest


ADR_FILES = [
    "0001-choreography-saga-pattern.md",
    "0002-rabbitmq-as-message-broker.md",
    "0003-database-per-service.md",
    "0004-nginx-api-gateway.md",
    "0005-python-3-12-service-language.md",
    "0006-docker-compose-local-runtime.md",
    "0007-diagrams-as-code-python-diagrams.md",
]

_ADR_IDS = [f[:4] for f in ADR_FILES]

REQUIRED_SECTIONS = [
    "## Context",
    "## Decision Outcome",
    "## Consequences",
]

REQUIRED_FIELDS = ["Status", "Date", "Deciders"]


# ── File existence ────────────────────────────────────────────


class TestAdrFilesExist:
    """Verify every expected ADR file is present on disk."""

    @pytest.mark.parametrize("filename", ADR_FILES, ids=_ADR_IDS)
    def test_adr_file_exists(
        self, adr_dir: pathlib.Path, filename: str
    ) -> None:
        """Each ADR file must exist in the decisions/ directory."""
        assert (adr_dir / filename).is_file(), f"Missing ADR: {filename}"

    def test_adr_index_readme_exists(self, adr_dir: pathlib.Path) -> None:
        """An index README must exist alongside the ADR files."""
        assert (adr_dir / "README.md").is_file()


# ── MADR structural requirements ─────────────────────────────


class TestAdrStructure:
    """Verify MADR structure for every ADR, parametrised over
    all seven files."""

    @pytest.fixture(
        params=ADR_FILES,
        ids=_ADR_IDS,
    )
    def adr_content(
        self,
        adr_dir: pathlib.Path,
        request: pytest.FixtureRequest,
    ) -> str:
        """Return text of one ADR, cycled over all ADR files."""
        return (adr_dir / request.param).read_text(encoding="utf-8")

    def test_status_is_accepted(self, adr_content: str) -> None:
        """Every ADR must declare Status: Accepted."""
        assert "Accepted" in adr_content

    def test_date_field_present(self, adr_content: str) -> None:
        """Every ADR must carry the project inception date."""
        assert "2026-05-22" in adr_content

    def test_deciders_field_present(self, adr_content: str) -> None:
        """Every ADR must list a Deciders field."""
        assert "Deciders" in adr_content

    def test_context_section_present(self, adr_content: str) -> None:
        """Every ADR must include a ## Context section."""
        assert "## Context" in adr_content

    def test_decision_outcome_section_present(self, adr_content: str) -> None:
        """Every ADR must include a ## Decision Outcome section."""
        assert "## Decision Outcome" in adr_content

    def test_consequences_section_present(self, adr_content: str) -> None:
        """Every ADR must include a ## Consequences section."""
        assert "## Consequences" in adr_content


# ── Technology-specific content spot-checks ──────────────────


class TestAdrDecisionContent:
    """Verify each ADR names the correct chosen technology."""

    def test_saga_adr_chose_choreography(self, adr_dir: pathlib.Path) -> None:
        """ADR-0001 must confirm choreography was chosen."""
        src = (adr_dir / "0001-choreography-saga-pattern.md").read_text(
            encoding="utf-8"
        )
        assert "choreography" in src.lower()

    def test_broker_adr_chose_rabbitmq(self, adr_dir: pathlib.Path) -> None:
        """ADR-0002 must name RabbitMQ as the broker choice."""
        src = (adr_dir / "0002-rabbitmq-as-message-broker.md").read_text(
            encoding="utf-8"
        )
        assert "RabbitMQ" in src

    def test_database_adr_chose_per_service(
        self, adr_dir: pathlib.Path
    ) -> None:
        """ADR-0003 must confirm one database per service."""
        src = (adr_dir / "0003-database-per-service.md").read_text(
            encoding="utf-8"
        )
        assert "database per service" in src.lower()

    def test_gateway_adr_chose_nginx(self, adr_dir: pathlib.Path) -> None:
        """ADR-0004 must name Nginx as the API gateway."""
        src = (adr_dir / "0004-nginx-api-gateway.md").read_text(
            encoding="utf-8"
        )
        assert "Nginx" in src

    def test_language_adr_chose_python_312(
        self, adr_dir: pathlib.Path
    ) -> None:
        """ADR-0005 must confirm Python 3.12 as the language."""
        src = (adr_dir / "0005-python-3-12-service-language.md").read_text(
            encoding="utf-8"
        )
        assert "Python 3.12" in src

    def test_runtime_adr_chose_docker_compose(
        self, adr_dir: pathlib.Path
    ) -> None:
        """ADR-0006 must confirm Docker Compose as the runtime."""
        src = (adr_dir / "0006-docker-compose-local-runtime.md").read_text(
            encoding="utf-8"
        )
        assert "Docker Compose" in src

    def test_diagrams_adr_chose_python_library(
        self, adr_dir: pathlib.Path
    ) -> None:
        """ADR-0007 must name the Python diagrams library."""
        src = (adr_dir / "0007-diagrams-as-code-python-diagrams.md").read_text(
            encoding="utf-8"
        )
        assert "diagrams" in src.lower()


# ── Cross-references between ADRs ────────────────────────────


class TestAdrCrossReferences:
    """Verify inter-ADR links are present where expected."""

    def test_saga_adr_links_to_broker_adr(self, adr_dir: pathlib.Path) -> None:
        """ADR-0001 must reference ADR-0002 (broker choice)."""
        src = (adr_dir / "0001-choreography-saga-pattern.md").read_text(
            encoding="utf-8"
        )
        assert "0002" in src, "ADR-0001 should link to ADR-0002"

    def test_broker_adr_links_to_saga_adr(self, adr_dir: pathlib.Path) -> None:
        """ADR-0002 must reference ADR-0001 (saga pattern)."""
        src = (adr_dir / "0002-rabbitmq-as-message-broker.md").read_text(
            encoding="utf-8"
        )
        assert "0001" in src, "ADR-0002 should link to ADR-0001"

    def test_database_adr_links_to_saga_adr(
        self, adr_dir: pathlib.Path
    ) -> None:
        """ADR-0003 must reference ADR-0001 (saga pattern)."""
        src = (adr_dir / "0003-database-per-service.md").read_text(
            encoding="utf-8"
        )
        assert "0001" in src, "ADR-0003 should link to ADR-0001"

    def test_diagrams_adr_links_to_deployment_adr(
        self, adr_dir: pathlib.Path
    ) -> None:
        """ADR-0007 must reference ADR-0006 (deployment)."""
        src = (adr_dir / "0007-diagrams-as-code-python-diagrams.md").read_text(
            encoding="utf-8"
        )
        assert "0006" in src, "ADR-0007 should link to ADR-0006"
