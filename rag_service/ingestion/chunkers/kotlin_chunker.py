import hashlib
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple

from rag_service.domain.models import Chunk, DocumentType, ServiceMetadata


class KotlinChunker:
    """
    Code-aware structural chunker for Kotlin source files (.kt, .kts).
    - Preserves package, imports, class headers, constructor-injected collaborators, and Spring annotations.
    - Segments logical units (methods, handlers, controller endpoints, data classes).
    - Extracts Spring endpoints (@PostMapping, @GetMapping, @RequestMapping).
    - Prepends a compact Scope Header (File | Package | Class | Collaborators) and records
      collaborator dependencies for 1-hop graph expansion.
    """

    KT_BUILTINS = {
        "String", "Int", "Long", "Double", "Float", "Boolean", "Byte", "Short", "Char",
        "Any", "Unit", "Nothing", "List", "MutableList", "Map", "MutableMap", "Set", "MutableSet",
        "Array", "Pair", "Triple", "Sequence", "Flow", "Mono", "Flux", "ResponseEntity",
        "UUID", "BigDecimal", "LocalDate", "LocalDateTime", "Instant", "Logger", "Exception",
    }

    def __init__(
        self,
        service: str = "default-service",
        max_chunk_chars: int = 2800,
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
        Split a Kotlin source file into code-aware semantic chunks with Scope Headers.
        """
        lines = content.splitlines(keepends=True)
        if not lines:
            return []

        file_name = Path(file_path).name
        package_name = self._extract_package(lines)
        imports, imported_symbols = self._extract_imports(lines)
        class_info = self._extract_class_info(lines)

        # If no class found, return entire file as single chunk
        if not class_info:
            scope_header = self._build_scope_header(file_name, package_name, None, imported_symbols)
            return [
                self._create_chunk(
                    content=f"{scope_header}\n{content}",
                    file_path=file_path,
                    source=source,
                    start_line=1,
                    end_line=len(lines),
                    index=0,
                    package=package_name,
                    class_name=None,
                    method_name=None,
                    endpoint=None,
                    dependencies=imported_symbols,
                    extra_metadata=extra_metadata,
                )
            ]

        collaborators = self._extract_collaborators(lines, class_info, imported_symbols)
        scope_header = self._build_scope_header(file_name, package_name, class_info, collaborators)

        # Extract method blocks
        methods = self._extract_methods(lines, class_info)

        if not methods or len(content) <= self.max_chunk_chars:
            # Fallback or small class: chunk the whole class intact
            method_names = [m["name"] for m in methods if m.get("name")]
            endpoints = [
                self._combine_endpoints(class_info.get("base_endpoint"), m.get("endpoint"))
                for m in methods
                if m.get("endpoint") or class_info.get("base_endpoint")
            ]
            return [
                self._create_chunk(
                    content=f"{scope_header}\n{content}",
                    file_path=file_path,
                    source=source,
                    start_line=1,
                    end_line=len(lines),
                    index=0,
                    package=package_name,
                    class_name=class_info.get("class_name"),
                    method_name=method_names[0] if len(method_names) == 1 else None,
                    endpoint=endpoints[0] if endpoints else class_info.get("base_endpoint"),
                    dependencies=collaborators,
                    extra_metadata={
                        "class_annotations": class_info.get("annotations", []),
                        "collaborators": collaborators,
                        "methods_in_file": method_names,
                        "endpoints_in_file": [e for e in endpoints if e],
                        **(extra_metadata or {}),
                    },
                )
            ]

        chunks: List[Chunk] = []
        class_context_header = self._build_class_header(package_name, class_info)

        for idx, method in enumerate(methods):
            method_code = "".join(method["lines"]).strip()
            # Prepend scope & class context to give LLM full understanding of the enclosing service/component
            chunk_content = f"{scope_header}\n{class_context_header}\n    // ...\n{method_code}\n}}"

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
                dependencies=collaborators,
                extra_metadata={
                    "annotations": method.get("annotations", []),
                    "class_annotations": class_info.get("annotations", []),
                    "collaborators": collaborators,
                    **(extra_metadata or {}),
                },
            )
            chunks.append(chunk)

        return chunks

    def _extract_imports(self, lines: List[str]) -> Tuple[List[str], List[str]]:
        imports: List[str] = []
        symbols: List[str] = []
        for line in lines[:120]:
            match = re.match(r"^\s*import\s+([a-zA-Z0-9_.*]+)", line)
            if match:
                imp = match.group(1)
                imports.append(imp)
                sym = imp.split(".")[-1]
                if sym != "*" and sym[0:1].isupper() and sym not in self.KT_BUILTINS:
                    if not imp.startswith(("java.", "javax.", "jakarta.", "kotlin.", "kotlinx.", "org.springframework.", "org.slf4j.")):
                        symbols.append(sym)
        return imports, list(dict.fromkeys(symbols))[:15]

    def _extract_collaborators(
        self,
        lines: List[str],
        class_info: Dict[str, Any],
        imported_symbols: List[str],
    ) -> List[str]:
        collaborators = list(imported_symbols)
        c_line = class_info.get("line_number", 1)
        header_block = "".join(lines[max(0, c_line - 1): min(len(lines), c_line + 35)])
        for m in re.finditer(r"(?:val|var)\s+[a-zA-Z0-9_]+\s*:\s*([A-Z][A-Za-z0-9_]*)", header_block):
            t_name = m.group(1)
            if t_name not in self.KT_BUILTINS and t_name != class_info.get("class_name"):
                collaborators.append(t_name)
        return list(dict.fromkeys(collaborators))[:15]

    def _build_scope_header(
        self,
        file_name: str,
        package: Optional[str],
        class_info: Optional[Dict[str, Any]],
        collaborators: List[str],
    ) -> str:
        parts = [f"// [Scope] File: {file_name}"]
        if package:
            parts.append(f"Package: {package}")
        if class_info and class_info.get("class_name"):
            parts.append(f"Class: {class_info['class_name']}")
        if class_info and class_info.get("base_endpoint"):
            parts.append(f"BaseEndpoint: {class_info['base_endpoint']}")
        line1 = " | ".join(parts)
        if collaborators:
            return f"{line1}\n// [Collaborators] {', '.join(collaborators)}"
        return line1

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
        dependencies: Optional[List[str]] = None,
        extra_metadata: Optional[Dict[str, Any]] = None,
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
            extra={
                "dependencies": dependencies or [],
                **(extra_metadata or {}),
            },
        )

        return Chunk(
            id=chunk_id,
            content=content,
            metadata=meta,
            index=index,
        )
