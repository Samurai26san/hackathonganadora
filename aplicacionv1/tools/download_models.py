"""Download immutable model files by resumable ranges, then verify SHA-256."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import fcntl
import hashlib
import json
import os
from pathlib import Path
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
BLOCK = 8 * 1024 * 1024


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(8 * 1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def download(url: str, target: Path, size: int, workers: int) -> None:
    partial = target.with_name(target.name + ".partial")
    journal = target.with_name(target.name + ".ranges.json")
    count = (size + BLOCK - 1) // BLOCK
    if journal.exists():
        state = json.loads(journal.read_text())
        if state["url"] != url or state["size"] != size or state["block"] % BLOCK:
            raise SystemExit(f"Checkpoint incompatible: {journal}")
        if not partial.exists():
            raise SystemExit(f"Falta el parcial del checkpoint: {partial}")
        completed = {
            block
            for old in state["completed"]
            for block in range(
                old * state["block"] // BLOCK,
                (min((old + 1) * state["block"], size) + BLOCK - 1) // BLOCK,
            )
        }
    else:
        # Preserve the prefix from the original sequential curl downloader.
        completed = (
            set(range(min(partial.stat().st_size // BLOCK, count)))
            if partial.exists()
            else set()
        )
    state = {"url": url, "size": size, "block": BLOCK, "completed": sorted(completed)}
    journal.parent.mkdir(parents=True, exist_ok=True)

    def save_checkpoint() -> None:
        checkpoint = journal.with_suffix(".tmp")
        with checkpoint.open("w") as output:
            json.dump(state, output)
            output.flush()
            os.fsync(output.fileno())
        checkpoint.replace(journal)

    save_checkpoint()
    fd = os.open(partial, os.O_RDWR | os.O_CREAT, 0o600)

    def block(index: int) -> int:
        start, end = index * BLOCK, min((index + 1) * BLOCK, size) - 1
        for attempt in range(5):
            try:
                request = urllib.request.Request(
                    url, headers={"Range": f"bytes={start}-{end}"}
                )
                with urllib.request.urlopen(request, timeout=60) as response:
                    expected = f"bytes {start}-{end}/{size}"
                    full_file = (
                        start == 0 and end == size - 1 and response.status == 200
                    )
                    if not full_file and (
                        response.status != 206
                        or response.headers.get("Content-Range") != expected
                    ):
                        raise ValueError("El servidor no respetó el rango solicitado")
                    offset = start
                    while chunk := response.read(1024 * 1024):
                        if offset + len(chunk) > end + 1:
                            raise ValueError("El bloque excede su rango")
                        written = 0
                        while written < len(chunk):
                            written += os.pwrite(fd, chunk[written:], offset + written)
                        offset += len(chunk)
                    if offset != end + 1:
                        raise ValueError("Bloque incompleto")
                return index
            except Exception:
                if attempt == 4:
                    raise
                time.sleep(2 * (attempt + 1))
        raise RuntimeError("Descarga incompleta")

    try:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(block, i) for i in range(count) if i not in completed
            ]
            for future in as_completed(futures):
                completed.add(future.result())
                os.fsync(fd)
                state["completed"] = sorted(completed)
                save_checkpoint()
                print(
                    f"{target.name}: {len(completed)}/{count} bloques completos",
                    flush=True,
                )
    finally:
        os.close(fd)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "ops/models.json")
    parser.add_argument("--folder", type=Path, default=ROOT / "llama.cpp/models")
    parser.add_argument("--workers", type=int, choices=range(1, 17), default=8)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    args.folder.mkdir(parents=True, exist_ok=True)
    # Keep the descriptor open: OS releases the lock even after interruption.
    lock = (args.folder / ".download.lock").open("a")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit("Ya hay una descarga activa en esta carpeta.") from None
    for item in manifest["files"]:
        target = args.folder / item["name"]
        target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.with_name(target.name + ".partial")
        if not target.exists():
            url = f"https://huggingface.co/{manifest['repository']}/resolve/{manifest['revision']}/{item['name']}"
            print(
                f'Descargando/reanudando {target.name} ({item["size"]} bytes)...',
                flush=True,
            )
            download(url, target, item["size"], args.workers)
            if (
                partial.stat().st_size != item["size"]
                or digest(partial) != item["sha256"]
            ):
                raise SystemExit(f"Hash inválido, se conserva el parcial: {partial}")
            partial.replace(target)
            target.with_name(target.name + ".ranges.json").unlink()
        elif target.stat().st_size != item["size"] or digest(target) != item["sha256"]:
            raise SystemExit(
                f"El archivo existente no coincide con el hash oficial: {target.name}"
            )
        print(f"{target.name}: SHA-256 válido.", flush=True)


if __name__ == "__main__":
    main()
