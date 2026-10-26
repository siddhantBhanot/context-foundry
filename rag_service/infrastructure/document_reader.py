import os
from pathlib import Path
import re
from typing import Optional, Set

from rag_service.domain.models import DocumentContent


ALLOWED_DOC_EXTENSIONS: Set[str] = {".md", ".markdown", ".txt", ".rst", ".pdf", ".kt", ".kts"}
SERVICE_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_\-]+$")


class DocumentReader:
    """
    Secure document reader for microservice documentation.
    Enforces strict path traversal security, whitelist directory boundaries,
    and safe file extension restrictions.
    """

    def __init__(self, data_dir: Optional[Path | str] = None) -> None:
        if data_dir:
            self.data_dir = Path(data_dir).resolve()
        else:
            env_data_dir = os.getenv("DATA_DIR")
            if env_data_dir:
                self.data_dir = Path(env_data_dir).resolve()
            else:
                self.data_dir = (Path(__file__).resolve().parent.parent / "sample_data").resolve()

    def get_service_base_dir(self, service: str) -> Path:
        """
        Validate and return the base documentation directory for a service.
        Prioritizes DATA_DIR / {service} / docs /; falls back to DATA_DIR / {service} /.
        """
        if not service or not SERVICE_NAME_PATTERN.match(service):
            raise ValueError(f"Invalid service identifier: '{service}'")

        service_root = (self.data_dir / service).resolve()
        if not service_root.is_relative_to(self.data_dir):
            raise PermissionError(f"Access denied: Service directory outside data root: {service}")

        docs_subdir = (service_root / "docs").resolve()
        if docs_subdir.is_dir() and docs_subdir.is_relative_to(self.data_dir):
            return docs_subdir

        return service_root

    def read_document(self, service: str, file_path: str) -> DocumentContent:
        """
        Securely read a documentation file for a given service.

        Raises:
            ValueError: If service or file name has invalid characters.
            PermissionError: If path traversal or unauthorized file extension is detected.
            FileNotFoundError: If the document does not exist.
        """
        if not file_path:
            raise ValueError("File path cannot be empty.")
        if not service or not SERVICE_NAME_PATTERN.match(service):
            raise ValueError(f"Invalid service identifier: '{service}'")

        service_root = (self.data_dir / service).resolve()
        if not service_root.is_relative_to(self.data_dir):
            raise PermissionError(f"Access denied: Service directory outside data root: {service}")

        raw_path = Path(file_path.strip())
        parts = list(raw_path.parts)

        # If the service identifier appears in parts, extract relative subpath within service
        if service in parts:
            idx = parts.index(service)
            subparts = parts[idx + 1:]
            # If 'docs' is the immediate subfolder, extract after it
            if subparts and subparts[0] == "docs":
                subparts = subparts[1:]
            clean_name = str(Path(*subparts)) if subparts else raw_path.name
        else:
            clean_name = file_path.strip().lstrip("/\\")
            if clean_name.startswith("docs/") or clean_name.startswith("docs\\"):
                clean_name = clean_name[5:]

        # Upfront Extension Whitelist: deny code files immediately
        ext = Path(clean_name).suffix.lower()
        if ext not in ALLOWED_DOC_EXTENSIONS:
            raise PermissionError(
                f"Access denied: File extension '{ext}' is not permitted for document viewing. "
                f"Allowed formats: {', '.join(sorted(ALLOWED_DOC_EXTENSIONS))}. "
                "Source code and binary files cannot be viewed."
            )

        # Candidate directories to search (docs/, pending/, uploads/ subfolders or service root)
        docs_dir = (service_root / "docs").resolve()
        pending_dir = (service_root / "pending").resolve()
        uploads_dir = (service_root / "uploads").resolve()
        candidates = []
        if docs_dir.is_dir() and docs_dir.is_relative_to(self.data_dir):
            candidates.append((docs_dir / clean_name).resolve())
        if pending_dir.is_dir() and pending_dir.is_relative_to(self.data_dir):
            candidates.append((pending_dir / clean_name).resolve())
        if uploads_dir.is_dir() and uploads_dir.is_relative_to(self.data_dir):
            candidates.append((uploads_dir / clean_name).resolve())
        candidates.append((service_root / clean_name).resolve())

        # 1. Path traversal guard: all candidate locations must be inside service_root
        target_path: Optional[Path] = None
        for cand in candidates:
            if not cand.is_relative_to(service_root):
                raise PermissionError(
                    f"Access denied: Path traversal detected for path '{file_path}'"
                )
            if cand.is_file():
                target_path = cand
                break

        # If not found, verify traversal on primary candidate before raising 404
        if not target_path:
            raise FileNotFoundError(
                f"Document '{clean_name}' not found for microservice '{service}'."
            )

        # 3. Content reading & metadata
        suffix = target_path.suffix.lower()
        if suffix == ".pdf":
            try:
                import pypdf

                reader = pypdf.PdfReader(str(target_path))
                pages_text = []
                for i, page in enumerate(reader.pages):
                    page_content = page.extract_text() or ""
                    pages_text.append(f"## Page {i + 1}\n\n{page_content.strip()}")
                content = "\n\n".join(pages_text) if pages_text else "*(Empty PDF document)*"
                content_type = "text/markdown"
            except Exception as e:
                content = f"Error extracting text from PDF: {e}"
                content_type = "text/plain"
        else:
            content = target_path.read_text(encoding="utf-8", errors="replace")
            if suffix in [".kt", ".kts"]:
                content_type = "text/x-kotlin"
            elif suffix in [".md", ".markdown"]:
                content_type = "text/markdown"
            else:
                content_type = "text/plain"

        total_lines = len(content.splitlines())
        size_bytes = target_path.stat().st_size

        return DocumentContent(
            file=target_path.name,
            service=service,
            content=content,
            content_type=content_type,
            total_lines=total_lines,
            size_bytes=size_bytes,
        )
