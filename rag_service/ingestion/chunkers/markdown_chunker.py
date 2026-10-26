import hashlib
import re
from typing import List, Optional

from rag_service.domain.models import Chunk, DocumentType, ServiceMetadata


class MarkdownChunker:
    """
    Semantic Markdown chunker for technical documentation.
    - Preserves document hierarchy (H1 > H2 > H3).
    - Prevents splitting code blocks (``` ... ```) and Markdown tables.
    - Prepends header breadcrumbs so each chunk is self-contained.
    - Generates rich service-level metadata for indexing.
    """

    def __init__(
        self,
        max_chunk_chars: int = 1500,
        min_chunk_chars: int = 100,
        service: str = "income-assessment-service",
    ) -> None:
        self.max_chunk_chars = max_chunk_chars
        self.min_chunk_chars = min_chunk_chars
        self.service = service

    def chunk(
        self,
        content: str,
        file_path: str,
        source: str = "documentation",
        extra_metadata: Optional[dict] = None,
    ) -> List[Chunk]:
        """
        Split markdown content into semantic, header-aware chunks.
        """
        lines = content.splitlines(keepends=True)
        if not lines:
            return []

        chunks: List[Chunk] = []
        current_headers: List[str] = []
        current_chunk_lines: List[str] = []
        current_start_line = 1
        in_code_block = False
        chunk_idx = 0

        for line_num, line in enumerate(lines, start=1):
            stripped = line.strip()

            # Track fenced code blocks
            if stripped.startswith("```"):
                in_code_block = not in_code_block

            # Header detection (only outside code blocks)
            header_match = re.match(r"^(#{1,6})\s+(.*)$", stripped) if not in_code_block else None

            if header_match:
                level = len(header_match.group(1))
                title = header_match.group(2).strip()

                # Adjust header hierarchy stack
                while len(current_headers) >= level:
                    current_headers.pop()
                current_headers.append(title)

                # If current chunk has enough content, flush it before starting new section
                current_text = "".join(current_chunk_lines).strip()
                if len(current_text) >= self.min_chunk_chars:
                    chunk = self._create_chunk(
                        text=current_text,
                        file_path=file_path,
                        source=source,
                        start_line=current_start_line,
                        end_line=line_num - 1,
                        index=chunk_idx,
                        headers=current_headers[:-1],
                        extra_metadata=extra_metadata,
                    )
                    chunks.append(chunk)
                    chunk_idx += 1
                    current_chunk_lines = []
                    current_start_line = line_num

            current_chunk_lines.append(line)

            # Check if current accumulated chunk exceeds max size and not inside a code block
            chunk_length = sum(len(l) for l in current_chunk_lines)
            if chunk_length >= self.max_chunk_chars and not in_code_block and stripped == "":
                current_text = "".join(current_chunk_lines).strip()
                if len(current_text) >= self.min_chunk_chars:
                    chunk = self._create_chunk(
                        text=current_text,
                        file_path=file_path,
                        source=source,
                        start_line=current_start_line,
                        end_line=line_num,
                        index=chunk_idx,
                        headers=current_headers,
                        extra_metadata=extra_metadata,
                    )
                    chunks.append(chunk)
                    chunk_idx += 1
                    current_chunk_lines = []
                    current_start_line = line_num + 1

        # Flush remaining lines
        remaining_text = "".join(current_chunk_lines).strip()
        if remaining_text:
            chunk = self._create_chunk(
                text=remaining_text,
                file_path=file_path,
                source=source,
                start_line=current_start_line,
                end_line=len(lines),
                index=chunk_idx,
                headers=current_headers,
                extra_metadata=extra_metadata,
            )
            chunks.append(chunk)

        return chunks

    def _create_chunk(
        self,
        text: str,
        file_path: str,
        source: str,
        start_line: int,
        end_line: int,
        index: int,
        headers: List[str],
        extra_metadata: Optional[dict],
    ) -> Chunk:
        # Prepend header breadcrumbs if available and not already in text
        breadcrumbs = " > ".join(headers) if headers else ""
        formatted_content = f"[{breadcrumbs}]\n{text}" if breadcrumbs and not text.startswith(f"[{breadcrumbs}]") else text

        chunk_id_raw = f"{file_path}#{index}#{start_line}-{end_line}"
        chunk_id = hashlib.sha256(chunk_id_raw.encode("utf-8")).hexdigest()[:16]

        meta = ServiceMetadata(
            service=self.service,
            document_type=DocumentType.MARKDOWN,
            source=source,
            file_path=file_path,
            language="markdown",
            start_line=start_line,
            end_line=end_line,
            extra={
                "section_hierarchy": headers,
                "breadcrumbs": breadcrumbs,
                **(extra_metadata or {}),
            },
        )

        return Chunk(
            id=chunk_id,
            content=formatted_content,
            metadata=meta,
            index=index,
        )
