"""Ingest PDF, DOCX, Markdown and text from the operator-controlled volume."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

import httpx

from app.core.database import SessionFactory
from app.services.rag_service import RAGService


def extract_text(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        from pypdf import PdfReader

        return "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)
    if path.suffix.lower() == ".docx":
        from docx import Document

        return "\n".join(paragraph.text for paragraph in Document(str(path)).paragraphs)
    return path.read_text(encoding="utf-8")


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path, nargs="?", default=Path("/app/data_docs"))
    args = parser.parse_args()
    async with SessionFactory() as db, httpx.AsyncClient(timeout=60) as http:
        for path in sorted(args.path.rglob("*")):
            if (
                not path.is_file()
                or path.suffix.lower() not in {".pdf", ".docx", ".txt", ".md"}
                or path.name == "leer_primero.txt"
            ):
                continue
            relative = str(path.relative_to(args.path))
            text = extract_text(path)
            type_ = "law" if "ley" in path.stem.lower() else "manual"
            chunks = await RAGService(db, http).ingest_text(
                text, type_, relative, path.name
            )
            print(f"{relative}: {len(chunks)} fragmentos")
        await db.commit()


if __name__ == "__main__":
    asyncio.run(main())
