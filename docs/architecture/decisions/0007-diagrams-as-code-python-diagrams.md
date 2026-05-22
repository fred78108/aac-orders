# ADR-0007: Diagrams-as-code with Python diagrams library

| Field    | Value      |
|----------|------------|
| Status   | Accepted   |
| Date     | 2026-05-22 |
| Deciders | Fred       |

## Context

Architecture diagrams must stay in sync with the system as it evolves.
Manual drawing tools (Draw.io, Lucidchart) diverge from the codebase because
they live outside version control and require human discipline to update.
The project's central theme is "architecture as code" — diagrams should be
generated from code, reviewed in pull requests, and regenerated automatically
when the architecture changes.

Four diagram levels are needed following the C4 model:
System Context, Service Overview (Container), Event Flow, and Deployment.

## Considered Options

- **Python `diagrams` library** (Mingrammer) — Graphviz-backed; Python DSL;
  outputs PNG; native to the repo's language.
- **PlantUML** — text-based UML; mature; requires Java runtime; not Python-native.
- **Mermaid** — Markdown-embeddable; renders in GitHub; limited layout control
  for complex multi-service topologies.
- **Structurizr DSL** — purpose-built C4 tooling; full C4 compliance; introduces
  a new DSL and a separate server or CLI.
- **Draw.io / Lucidchart** — WYSIWYG; XML source can be version-controlled but
  diffs are unreadable; violates architecture-as-code principle.

## Decision Outcome

Chose **Python `diagrams` library**.

Python is already the project language, so diagram scripts are first-class repo
citizens — linted, type-checked, and importable. `generate_all.py` regenerates
all four PNGs in one command and can be wired into CI. The library's built-in
icon set covers all infrastructure components used in this project (Nginx, Postgres,
RabbitMQ, Redis, Python services).

Mermaid was considered for its zero-dependency GitHub rendering but its automatic
layout struggles with the multi-service event flow diagram. Structurizr DSL is
more architecturally correct for C4 but adds a new language and toolchain.

## Consequences

**Positive**
- Diagrams live in `docs/architecture/diagrams/` alongside the narrative;
  `git diff` on a diagram script is meaningful.
- `generate_all.py` can be a pre-commit hook or CI step to catch stale PNGs.
- Adding a new service means editing a Python file — the same mental model as
  editing application code.

**Negative / watch-outs**
- Graphviz must be installed separately (`brew install graphviz` / `apt-get install graphviz`);
  documented in `docs/architecture/README.md`.
- The `diagrams` library's layout engine (Graphviz `dot`) gives limited control
  over node placement; highly complex diagrams may need manual attribute tuning.
- Generated PNGs are binary blobs in git; keep them in `generated/` (gitignored
  or explicitly tracked) rather than in the diagram source directory.

## Related decisions

- [ADR-0006](0006-docker-compose-local-runtime.md) — deployment diagram reflects
  Docker Compose topology
