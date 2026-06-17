from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def run_step(label: str, command: list[str]) -> None:
    print(f"\n== {label} ==")
    print(" ".join(command))
    result = subprocess.run(command, cwd=PROJECT_ROOT, text=True)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main() -> int:
    python = sys.executable
    run_step("Run test suite", [python, "-m", "pytest"])
    run_step("Ingest sample documents", [python, "scripts/ingest_sample_docs.py"])
    run_step("Rebuild retrieval indexes", [python, "scripts/rebuild_indexes.py"])
    run_step("Run retrieval evaluation", [python, "scripts/run_retrieval_eval.py"])
    print("\nMVP-0 demo checkpoint passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

