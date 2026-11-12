"""Prepare the pinned official llama.cpp binary without changing host packages."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    metadata = json.loads((ROOT / "ops/llama-runtime.json").read_text())
    folder = ROOT / metadata["runtime_directory"]
    folder.mkdir(parents=True, exist_ok=True)
    archive = folder / f'llama-{metadata["version"]}-vulkan.tar.gz'
    partial = archive.with_name(archive.name + ".partial")
    if not archive.exists():
        subprocess.run(
            [
                "curl",
                "--fail",
                "--location",
                "--silent",
                "--show-error",
                "--continue-at",
                "-",
                "--retry",
                "3",
                "--output",
                str(partial),
                metadata["source"],
            ],
            check=True,
        )
        if hashlib.sha256(partial.read_bytes()).hexdigest() != metadata["sha256"]:
            raise SystemExit(
                "SHA-256 del binario oficial no coincide; se conserva el parcial."
            )
        partial.replace(archive)
    elif hashlib.sha256(archive.read_bytes()).hexdigest() != metadata["sha256"]:
        raise SystemExit("El archivo local no coincide con el binario oficial.")
    servers = list(folder.rglob("llama-server"))
    if not servers:
        with tarfile.open(archive) as source:
            source.extractall(folder, filter="data")
        servers = list(folder.rglob("llama-server"))
    if len(servers) != 1:
        raise SystemExit(
            "No se encontró un único ejecutable llama-server en el paquete oficial."
        )
    print(f"Binario oficial verificado: {servers[0].relative_to(ROOT)}")


if __name__ == "__main__":
    main()
