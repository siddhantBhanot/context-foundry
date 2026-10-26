import hashlib
import re
from typing import Any, Dict, List, Optional, Tuple

from rag_service.domain.models import Chunk, DocumentType, ServiceMetadata


class KotlinChunker:
    """
    Code-aware semantic chunker for Spring Boot Kotlin source files.
    - Preserves package, class headers, and Spring annotations.
    - Segments logical units (methods, handlers, controller endpoints, data classes).
    - Extracts Spring endpoints (@PostMapping, @GetMapping, @RequestMapping).
    - Attaches class-level context to method chunks for complete grounding.
    """

    def __init__(
        self,
        service: str = "income-assessment-service",
        max_chunk_chars: int = 2500,
    ) -> None:
        self.service = service
        self.max_chunk_chars = max_chunk_chars

    def chunk(
        self,
        content: str,
        file_path: str,
        source: str = "repository",
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Chunk]:
        """
        Split a Kotlin source file into code-aware semantic chunks.
        """
        lines = content.splitlines(keepends=True)
        if not lines:
            return []

        package_name = self._extract_package(lines)
        class_info = self._extract_class_info(lines)

        # If no class found, return entire file as single chunk
        if not class_info:
            return [
                self._create_chunk(
                    content=content,
                    file_path=file_path,
                    source=source,
                    start_line=1,
                    end_line=len(lines),
                    index=0,
                    package=package_name,
                    class_name=None,
                    method_name=None,
                    endpoint=None,
                    extra_metadata=extra_metadata,
                )
            ]

        # Extract method blocks
        methods = self._extract_methods(lines, class_info)

        if not methods:
            # Fallback: chunk the whole class
            return [
                self._create_chunk(
                    content=content,
                    file_path=file_path,
                    source=source,
                    start_line=1,
                    end_line=len(lines),
                    index=0,
                    package=package_name,
                    class_name=class_info.get("class_name"),
                    method_name=None,
                    endpoint=class_info.get("base_endpoint"),
                    extra_metadata=extra_metadata,
                )
            ]

        chunks: List[Chunk] = []
        class_context_header = self._build_class_header(package_name, class_info)

        for idx, method in enumerate(methods):
            method_code = "".join(method["lines"]).strip()
            # Prepend class context to give LLM full understanding of the enclosing service/component
            chunk_content = f"{class_context_header}\n    // ...\n{method_code}\n}}"

            full_endpoint = self._combine_endpoints(
                class_info.get("base_endpoint"), method.get("endpoint")
            )

            chunk = self._create_chunk(
                content=chunk_content,
                file_path=file_path,
                source=source,
                start_line=method["start_line"],
                end_line=method["end_line"],
                index=idx,
                package=package_name,
                class_name=class_info.get("class_name"),
                method_name=method.get("name"),
                endpoint=full_endpoint,
                extra_metadata={
                    "annotations": method.get("annotations", []),
                    "class_annotations": class_info.get("annotations", []),
                    **(extra_metadata or {}),
                },
            )
            chunks.append(chunk)

        return chunks

    def _extract_package(self, lines: List[str]) -> Optional[str]:
        for line in lines[:30]:
            match = re.match(r"^\s*package\s+([a-zA-Z0-9_.]+)", line)
            if match:
                return match.group(1)
        return None

    def _extract_class_info(self, lines: List[str]) -> Optional[Dict[str, Any]]:
        annotations: List[str] = []
        base_endpoint: Optional[str] = None

        for idx, line in enumerate(lines):
            stripped = line.strip()
            # Accumulate annotations before class
            if stripped.startswith("@"):
                annotations.append(stripped)
                # Check for @RequestMapping("/api/...")
                rm_match = re.search(r'@(?:RequestMapping|Path)\s*\(\s*["\']([^"\']+)["\']', stripped)
                if rm_match:
                    base_endpoint = rm_match.group(1)
                continue

            # Class or interface declaration
            class_match = re.search(
                r"^\s*(?:(?:public|internal|open|abstract|final|data|sealed)\s+)*(?:class|interface|object)\s+([a-zA-Z0-9_]+)",
                line,
            )
            if class_match:
                return {
                    "class_name": class_match.group(1),
                    "header_line": stripped,
                    "annotations": annotations,
                    "base_endpoint": base_endpoint,
                    "line_number": idx + 1,
                }

        return None

    def _build_class_header(self, package: Optional[str], class_info: Dict[str, Any]) -> str:
        parts = []
        if package:
            parts.append(f"package {package}")
            parts.append("")
        for ann in class_info.get("annotations", []):
            parts.append(ann)
        parts.append(f"{class_info.get('header_line', 'class ' + class_info.get('class_name', ''))} {{")
        return "\n".join(parts)

    def _extract_methods(self, lines: List[str], class_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        methods: List[Dict[str, Any]] = []
        current_annotations: List[str] = []
        current_endpoint: Optional[str] = None
        in_method = False
        method_lines: List[str] = []
        method_start = 1
        method_name = ""
        brace_count = 0

        for line_num, line in enumerate(lines, start=1):
            # Skip lines before class declaration
            if line_num <= class_info.get("line_number", 0):
                continue

            stripped = line.strip()

            if not in_method:
                if stripped.startswith("@"):
                    current_annotations.append(stripped)
                    # Check for Spring endpoint mapping annotations
                    ep_match = re.search(
                        r'@(?:GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping|RequestMapping)\s*\(\s*(?:value\s*=\s*)?["\']([^"\']+)["\']',
                        stripped,
                    )
                    if ep_match:
                        current_endpoint = ep_match.group(1)
                    continue

                # Method declaration: override fun ... or fun ...
                fun_match = re.search(
                    r"^\s*(?:(?:public|private|protected|internal|override|suspend|open|final)\s+)*fun\s+(?:<[^>]+>\s+)?([a-zA-Z0-9_]+)\s*\(",
                    line,
                )
                if fun_match:
                    in_method = True
                    method_name = fun_match.group(1)
                    method_start = line_num - len(current_annotations)
                    method_lines = [f"    {ann}\n" for ann in current_annotations] + [line]
                    brace_count = line.count("{") - line.count("}")
                    # If single-expression function without braces (e.g. fun x() = ...), finish immediately
                    if "=" in line and "{" not in line and brace_count == 0:
                        in_method = False
                        methods.append({
                            "name": method_name,
                            "lines": method_lines,
                            "start_line": method_start,
                            "end_line": line_num,
                            "annotations": current_annotations,
                            "endpoint": current_endpoint,
                        })
                        current_annotations = []
                        current_endpoint = None
                    continue
                else:
                    current_annotations = []
                    current_endpoint = None
            else:
                method_lines.append(line)
                brace_count += line.count("{") - line.count("}")
                if brace_count <= 0:
                    in_method = False
                    methods.append({
                        "name": method_name,
                        "lines": method_lines,
                        "start_line": method_start,
                        "end_line": line_num,
                        "annotations": current_annotations,
                        "endpoint": current_endpoint,
                    })
                    current_annotations = []
                    current_endpoint = None

        return methods

    def _combine_endpoints(self, base: Optional[str], path: Optional[str]) -> Optional[str]:
        if not base and not path:
            return None
        if base and not path:
            return base
        if not base and path:
            return path
        b = base.rstrip("/") if base else ""
        p = path.lstrip("/") if path else ""
        return f"{b}/{p}"

    def _create_chunk(
        self,
        content: str,
        file_path: str,
        source: str,
        start_line: int,
        end_line: int,
        index: int,
        package: Optional[str],
        class_name: Optional[str],
        method_name: Optional[str],
        endpoint: Optional[str],
        extra_metadata: Optional[Dict[str, Any]],
    ) -> Chunk:
        chunk_id_raw = f"{file_path}#{class_name or ''}#{method_name or ''}#{index}#{start_line}-{end_line}"
        chunk_id = hashlib.sha256(chunk_id_raw.encode("utf-8")).hexdigest()[:16]

        meta = ServiceMetadata(
            service=self.service,
            document_type=DocumentType.SOURCE_CODE,
            source=source,
            file_path=file_path,
            language="kotlin",
            package=package,
            class_name=class_name,
            method_name=method_name,
            endpoint=endpoint,
            start_line=start_line,
            end_line=end_line,
            extra=extra_metadata or {},
        )

        return Chunk(
            id=chunk_id,
            content=content,
            metadata=meta,
            index=index,
        )
