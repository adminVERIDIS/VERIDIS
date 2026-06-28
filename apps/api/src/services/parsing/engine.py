from __future__ import annotations

import csv
import logging
import re
import zipfile
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from uuid import uuid4
from xml.etree import ElementTree

from services.schemas import DocumentChunk, DocumentMetadata, ParsedDocument

logger = logging.getLogger(__name__)

SUPPORTED_FILE_TYPES = {"pdf", "docx", "xlsx", "csv"}
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024


class ParsingError(Exception):
    """Raised when a document cannot be parsed safely."""


class UnsupportedFileTypeError(ParsingError):
    """Raised when the input extension is not supported."""


class FileTooLargeError(ParsingError):
    """Raised when the uploaded document is above the MVP safety limit."""


class UnstructuredClient:
    """
    Minimal adapter for unstructured.io.

    The MVP keeps parsing deterministic and dependency-light. If an API key is
    provided later, this class is the single integration seam.
    """

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)


class BaseFileParser(ABC):
    @abstractmethod
    async def parse(self, file_path: Path) -> tuple[list[DocumentChunk], int | None]:
        raise NotImplementedError

    def _chunk_text(
        self,
        text: str,
        *,
        page_number: int | None = None,
        max_chars: int = 1800,
    ) -> list[DocumentChunk]:
        cleaned = normalize_whitespace(text)
        if not cleaned:
            return []

        chunks: list[DocumentChunk] = []
        current_section: str | None = None

        for block in split_blocks(cleaned, max_chars=max_chars):
            chunk_type: Literal["text", "table", "heading", "footer"] = "text"
            if looks_like_heading(block):
                chunk_type = "heading"
                current_section = block[:140]
            elif looks_like_table(block):
                chunk_type = "table"

            chunks.append(
                DocumentChunk(
                    id=uuid4(),
                    content=block,
                    page_number=page_number,
                    section_title=current_section,
                    chunk_type=chunk_type,
                    confidence=0.72 if chunk_type == "table" else 0.82,
                )
            )

        return chunks


class PDFParser(BaseFileParser):
    def __init__(self, client: UnstructuredClient):
        self.client = client

    async def parse(self, file_path: Path) -> tuple[list[DocumentChunk], int | None]:
        # Dependency-light fallback: extract readable text fragments from bytes.
        # This is not a replacement for unstructured.io, but it fails gracefully
        # and keeps unit tests deterministic.
        try:
            raw = file_path.read_bytes()
        except OSError as exc:
            raise ParsingError(f"Cannot read PDF file: {file_path}") from exc

        text = raw.decode("utf-8", errors="ignore")
        if len(text.strip()) < 50:
            text = raw.decode("latin-1", errors="ignore")

        page_markers = re.split(r"\f|/Page\b", text)
        chunks: list[DocumentChunk] = []
        for page_index, page_text in enumerate(page_markers, start=1):
            chunks.extend(self._chunk_text(page_text, page_number=page_index))

        return chunks, max(len(page_markers), 1)


class DocxParser(BaseFileParser):
    async def parse(self, file_path: Path) -> tuple[list[DocumentChunk], int | None]:
        try:
            with zipfile.ZipFile(file_path) as archive:
                xml = archive.read("word/document.xml")
        except (KeyError, zipfile.BadZipFile, OSError) as exc:
            raise ParsingError(f"Cannot parse DOCX file: {file_path}") from exc

        root = ElementTree.fromstring(xml)
        namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        paragraphs: list[str] = []
        for paragraph in root.findall(".//w:p", namespace):
            texts = [node.text or "" for node in paragraph.findall(".//w:t", namespace)]
            paragraph_text = normalize_whitespace(" ".join(texts))
            if paragraph_text:
                paragraphs.append(paragraph_text)

        return self._chunk_text("\n\n".join(paragraphs)), None


class ExcelParser(BaseFileParser):
    async def parse(self, file_path: Path) -> tuple[list[DocumentChunk], int | None]:
        try:
            with zipfile.ZipFile(file_path) as archive:
                shared_strings = self._read_shared_strings(archive)
                sheet_names = [name for name in archive.namelist() if name.startswith("xl/worksheets/")]
                rows: list[str] = []
                for sheet_name in sheet_names:
                    rows.extend(self._read_sheet_rows(archive, sheet_name, shared_strings))
        except zipfile.BadZipFile as exc:
            raise ParsingError(f"Cannot parse XLSX file: {file_path}") from exc

        chunks = [
            DocumentChunk(
                content=row,
                page_number=None,
                chunk_type="table",
                confidence=0.78,
            )
            for row in rows
            if row.strip()
        ]
        return chunks, None

    def _read_shared_strings(self, archive: zipfile.ZipFile) -> list[str]:
        try:
            xml = archive.read("xl/sharedStrings.xml")
        except KeyError:
            return []

        root = ElementTree.fromstring(xml)
        return [" ".join(text.itertext()) for text in root]

    def _read_sheet_rows(
        self,
        archive: zipfile.ZipFile,
        sheet_name: str,
        shared_strings: list[str],
    ) -> list[str]:
        xml = archive.read(sheet_name)
        root = ElementTree.fromstring(xml)
        rows: list[str] = []
        for row in root.iter():
            if not row.tag.endswith("row"):
                continue
            values: list[str] = []
            for cell in row:
                if not cell.tag.endswith("c"):
                    continue
                cell_type = cell.attrib.get("t")
                value_node = next((child for child in cell if child.tag.endswith("v")), None)
                if value_node is None or value_node.text is None:
                    continue
                value = value_node.text
                if cell_type == "s" and value.isdigit():
                    index = int(value)
                    value = shared_strings[index] if index < len(shared_strings) else value
                values.append(value)
            if values:
                rows.append(" | ".join(values))
        return rows


class CSVParser(BaseFileParser):
    async def parse(self, file_path: Path) -> tuple[list[DocumentChunk], int | None]:
        try:
            with file_path.open("r", encoding="utf-8-sig", newline="") as handle:
                sample = handle.read(4096)
                handle.seek(0)
                dialect = csv.Sniffer().sniff(sample) if sample else csv.excel
                reader = csv.reader(handle, dialect)
                rows = [" | ".join(cell.strip() for cell in row) for row in reader]
        except (OSError, csv.Error, UnicodeDecodeError) as exc:
            raise ParsingError(f"Cannot parse CSV file: {file_path}") from exc

        chunks = [
            DocumentChunk(content=row, chunk_type="table", confidence=0.86)
            for row in rows
            if row.strip()
        ]
        return chunks, None


class ParsingEngine:
    """
    Parsing orchestrator. Selects the right parser and returns structured data.
    """

    def __init__(self, unstructured_api_key: str | None = None):
        self.client = UnstructuredClient(api_key=unstructured_api_key)
        self.parsers: dict[str, BaseFileParser] = {
            "pdf": PDFParser(self.client),
            "docx": DocxParser(),
            "xlsx": ExcelParser(),
            "csv": CSVParser(),
        }

    async def parse(self, file_path: Path, filename: str) -> ParsedDocument:
        file_type = self._detect_file_type(filename)
        resolved_path = file_path.resolve()

        if not resolved_path.exists():
            raise ParsingError(f"File does not exist: {resolved_path}")

        file_size = resolved_path.stat().st_size
        if file_size > MAX_FILE_SIZE_BYTES:
            raise FileTooLargeError(
                f"File {filename} is {file_size} bytes; max is {MAX_FILE_SIZE_BYTES} bytes"
            )

        parser = self.parsers[file_type]
        try:
            chunks, total_pages = await parser.parse(resolved_path)
        except ParsingError:
            logger.exception("Parsing failed for %s", filename)
            raise
        except Exception as exc:  # defensive boundary: never leak parser internals
            logger.exception("Unexpected parser failure for %s", filename)
            raise ParsingError(f"Unexpected parser failure for {filename}") from exc

        if not chunks:
            logger.warning("No chunks extracted from %s", filename)

        metadata = infer_metadata(chunks)
        return ParsedDocument(
            filename=filename,
            file_type=file_type,  # type: ignore[arg-type]
            total_pages=total_pages,
            extracted_at=datetime.now(timezone.utc),
            chunks=chunks,
            metadata=metadata,
        )

    def _detect_file_type(self, filename: str) -> str:
        extension = Path(filename).suffix.lower().lstrip(".")
        if extension not in SUPPORTED_FILE_TYPES:
            raise UnsupportedFileTypeError(
                f"Unsupported file type '{extension}'. Supported: {sorted(SUPPORTED_FILE_TYPES)}"
            )
        return extension


def normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def split_blocks(text: str, *, max_chars: int) -> list[str]:
    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n{2,}", text) if paragraph.strip()]
    if not paragraphs:
        paragraphs = [text]

    blocks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(current) + len(paragraph) + 2 <= max_chars:
            current = f"{current}\n\n{paragraph}".strip()
            continue
        if current:
            blocks.append(current)
        current = paragraph

        while len(current) > max_chars:
            blocks.append(current[:max_chars].strip())
            current = current[max_chars:].strip()

    if current:
        blocks.append(current)
    return blocks


def looks_like_heading(text: str) -> bool:
    words = text.split()
    return len(words) <= 12 and (text.isupper() or re.match(r"^\d+(\.\d+)*\s+", text) is not None)


def looks_like_table(text: str) -> bool:
    return "|" in text or text.count(";") >= 3 or text.count("\t") >= 3


def infer_metadata(chunks: list[DocumentChunk]) -> DocumentMetadata:
    combined = "\n".join(chunk.content for chunk in chunks[:20])
    word_count = sum(len(chunk.content.split()) for chunk in chunks)
    frameworks = [
        framework
        for framework in ("GRI", "SASB", "TCFD", "CSRD")
        if re.search(rf"\b{framework}\b", combined, flags=re.IGNORECASE)
    ]
    year_match = re.search(r"\b(20[12]\d)\b", combined)
    company = infer_company_name(combined)

    return DocumentMetadata(
        detected_company=company,
        detected_year=int(year_match.group(1)) if year_match else None,
        detected_frameworks=frameworks,
        language="fr" if has_french_markers(combined) else "en",
        word_count=word_count,
    )


def infer_company_name(text: str) -> str | None:
    match = re.search(r"(?:societe|entreprise|groupe)\s+([A-Z][A-Za-z0-9& .'-]{2,80})", text)
    if match:
        return normalize_whitespace(match.group(1))
    return None


def has_french_markers(text: str) -> bool:
    markers = ("rapport", "developpement durable", "emissions", "salaries", "conformite")
    lowered = text.lower()
    return any(marker in lowered for marker in markers)
