"""
Generate all architecture diagrams.

Run from docs/architecture/:  python diagrams/generate_all.py

Requires:
  - diagrams package  (pip install -e ".[docs]" from project root)
  - Graphviz binary   (brew install graphviz  /  apt-get install graphviz)
"""

import os
import runpy
import sys

SCRIPTS = [
    "system_context.py",
    "service_overview.py",
    "event_flow.py",
    "deployment.py",
]

# Resolve paths relative to this file so the script works from any CWD.
here = os.path.dirname(os.path.abspath(__file__))
arch_root = os.path.dirname(here)

os.chdir(arch_root)
os.makedirs("generated", exist_ok=True)

for name in SCRIPTS:
    path = os.path.join(here, name)
    print(f"  generating {name} …")
    try:
        runpy.run_path(path)
    except Exception as exc:
        print(f"  ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

print(f"\nDone — PNGs written to {os.path.join(arch_root, 'generated')}/")
