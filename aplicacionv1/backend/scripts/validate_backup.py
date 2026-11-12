"""Restore a private backup into a new scratch database; never replace the source."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
CONTAINER = "exb-budget-copilot-postgres-1"
SQL = """SELECT json_build_object(
  'budgets', (SELECT count(*) FROM budgets),
  'movements', (SELECT count(*) FROM movements),
  'budget', (SELECT sum(initial_amount)::text FROM budgets),
  'executed', (SELECT sum(amount)::text FROM movements),
  'pgvector', (SELECT count(*) FROM pg_extension WHERE extname='vector')
);"""


def command(*args: str, **kwargs):
    return subprocess.run(
        ["docker", "exec", "-i", CONTAINER, *args], check=True, **kwargs
    )


def snapshot(database: str) -> dict:
    result = command(
        "psql",
        "-U",
        "postgres",
        "-d",
        database,
        "-Atc",
        SQL,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def main() -> None:
    label = subprocess.run(
        [
            "docker",
            "inspect",
            "--format",
            '{{index .Config.Labels "com.docker.compose.project"}}',
            CONTAINER,
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if label != "exb-budget-copilot":
        raise SystemExit("El contenedor no pertenece a este proyecto.")
    scratch = "budget_ai_restore_check_" + uuid4().hex[:10]
    folder = ROOT / "ops/runtime/backups"
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"{scratch}.dump"
    created = False
    report = {"passed": False, "scratch_removed": False}
    started = time.monotonic()
    try:
        before = snapshot("budget_ai")
        # Exclusive file creation with private permissions. Never overwrite a dump.
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as output:
            command(
                "pg_dump",
                "-U",
                "postgres",
                "-Fc",
                "budget_ai",
                stdout=output,
                stderr=subprocess.PIPE,
            )
        command("createdb", "-U", "postgres", scratch, capture_output=True)
        created = True
        with target.open("rb") as source:
            command(
                "pg_restore",
                "-U",
                "postgres",
                "--exit-on-error",
                "-d",
                scratch,
                stdin=source,
                capture_output=True,
            )
        restored = snapshot(scratch)
        if before != restored:
            raise ValueError(
                "La restauración no coincide con los datos financieros del origen."
            )
        report.update(
            {
                "passed": True,
                "snapshot": restored,
                "backup_bytes": target.stat().st_size,
                "backup_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            }
        )
    except Exception as error:
        report["error_type"] = type(error).__name__
    finally:
        if created:
            try:
                command("dropdb", "-U", "postgres", scratch, capture_output=True)
                report["scratch_removed"] = True
            except Exception as error:
                report.update(
                    {"passed": False, "cleanup_error_type": type(error).__name__}
                )
        report["seconds"] = round(time.monotonic() - started, 3)
        (ROOT / "docs/validation_operations.json").write_text(
            json.dumps(report, indent=2) + "\n"
        )
    print(json.dumps(report, ensure_ascii=False))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
