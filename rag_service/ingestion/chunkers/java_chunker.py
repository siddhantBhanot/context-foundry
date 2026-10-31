import hashlib
from pathlib import Path
import re
from typing import Any, Dict, List, Optional

from rag_service.domain.models import Chunk, DocumentType, ServiceMetadata


class JavaChunker:
    """
    AST/Structure-aware chunker for Java source files (.java).
    - Extracts package, imports, class/interface/enum/record declarations, and annotations.
    - Detects field/constructor-injected collaborator types (e.g. private final FooService fooService).
    - Extracts Spring/Jakarta REST endpoints (@GetMapping, @PostMapping, @RequestMapping, @Path).
    - Prepends a rich structural Scope Header to every chunk and records collaborator dependencies
      for 1-hop graph expansion.
    """

    JAVA_BUILTINS = {
        "String", "Integer", "Long", "Double", "Float", "Boolean", "Byte", "Short", "Character",
        "Object", "Class", "Void", "List", "ArrayList", "Map", "HashMap", "Set", "HashSet",
        "Optional", "Stream", "CompletableFuture", "UUID", "BigDecimal", "LocalDate", "LocalDateTime",
        "Instant", "ZonedDateTime", "Logger", "Exception", "RuntimeException",
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
        lines = content.splitlines(keepends=True)
        if not lines:
            return []

        file_name = Path(file_path).name
        package_name = self._extract_package(lines)
        imports, imported_symbols = self._extract_imports(lines)
        class_info = self._extract_class_info(lines)

        if not class_info:
            scope_header = self._build_scope_header(file_name, package_name, imports, None, [])
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
        methods = self._extract_methods(lines, class_info)
        scope_header = self._build_scope_header(file_name, package_name, imports, class_info, collaborators)

        if not methods or len(content) <= self.max_chunk_chars:
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
        class_header = self._build_class_header(package_name, class_info, collaborators)

        for idx, method in enumerate(methods):
            method_code = "".join(method["lines"]).strip()
            chunk_content = f"{scope_header}\n{class_header}\n    // ...\n    {method_code}\n}}"
            full_endpoint = self._combine_endpoints(
                class_info.get("base_endpoint"), method.get("endpoint")
            )

            chunks.append(
                self._create_chunk(
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
            )

        return chunks

    def _extract_package(self, lines: List[str]) -> Optional[str]:
        for line in lines[:40]:
            match = re.match(r"^\s*package\s+([a-zA-Z0-9_.]+)\s*;", line)
            if match:
                return match.group(1)
        return None

    def _extract_imports(self, lines: List[str]) -> tuple[List[str], List[str]]:
        imports: List[str] = []
        symbols: List[str] = []
        for line in lines[:120]:
            match = re.match(r"^\s*import\s+(?:static\s+)?([a-zA-Z0-9_.*]+)\s*;", line)
            if match:
                imp = match.group(1)
                imports.append(imp)
                sym = imp.split(".")[-1]
                if sym != "*" and sym[0:1].isupper() and sym not in self.JAVA_BUILTINS:
                    if not imp.startswith(("java.", "javax.", "jakarta.", "org.springframework.", "lombok.")):
                        symbols.append(sym)
        return imports, list(dict.fromkeys(symbols))

    def _extract_class_info(self, lines: List[str]) -> Optional[Dict[str, Any]]:
        annotations: List[str] = []
        base_endpoint: Optional[str] = None

        for idx, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("@"):
                annotations.append(stripped)
                rm_match = re.search(
                    r'@(?:RequestMapping|Path)\s*\(\s*(?:value\s*=\s*|path\s*=\s*)?["\']([^"\']+)["\']',
                    stripped,
                )
                if rm_match:
                    base_endpoint = rm_match.group(1)
                continue

            class_match = re.search(
                r"^\s*(?:(?:public|protected|private|abstract|final|static|sealed|non-sealed)\s+)*(?:class|interface|enum|record)\s+([a-zA-Z0-9_]+)",
                line,
            )
            if class_match:
                return {
                    "class_name": class_match.group(1),
                    "header_line": stripped.rstrip("{").strip(),
                    "annotations": annotations,
                    "base_endpoint": base_endpoint,
                    "line_number": idx + 1,
                }
        return None

    def _extract_collaborators(
        self,
        lines: List[str],
        class_info: Dict[str, Any],
        imported_symbols: List[str],
    ) -> List[str]:
        collaborators = list(imported_symbols)
        header = class_info.get("header_line", "")
        for match in re.finditer(r"(?:extends|implements)\s+([A-Za-z0-9_, <>]+)", header):
            for token in re.findall(r"\b([A-Z][A-Za-z0-9_]+)\b", match.group(1)):
                if token not in self.JAVA_BUILTINS and token != class_info.get("class_name"):
                    collaborators.append(token)

        # Scan field declarations for injected collaborators
        field_pattern = re.compile(
            r"^\s*(?:private|protected|public)?\s*(?:final\s+)?([A-Z][A-Za-z0-9_<>]+)\s+[a-z][A-Za-z0-9_]*\s*;"
        )
        for line in lines[class_info.get("line_number", 1): min(len(lines), class_info.get("line_number", 1) + 80)]:
            m = field_pattern.match(line)
            if m:
                raw_type = m.group(1).split("<")[0].strip()
                if raw_type not in self.JAVA_BUILTINS and raw_type != class_info.get("class_name"):
                    collaborators.append(raw_type)

        return list(dict.fromkeys(collaborators))[:15]

    def _build_scope_header(
        self,
        file_name: str,
        package: Optional[str],
        imports: List[str],
        class_info: Optional[Dict[str, Any]],
        collaborators: List[str],
    ) -> str:
        header_parts = [f"// [Scope] File: {file_name}"]
        if package:
            header_parts.append(f"Package: {package}")
        if class_info and class_info.get("class_name"):
            header_parts.append(f"Class: {class_info['class_name']}")
        if class_info and class_info.get("base_endpoint"):
            header_parts.append(f"BaseEndpoint: {class_info['base_endpoint']}")
        line1 = " | ".join(header_parts)
        if collaborators:
            return f"{line1}\n// [Collaborators] {', '.join(collaborators)}"
        return line1

    def _build_class_header(
        self,
        package: Optional[str],
        class_info: Dict[str, Any],
        collaborators: List[str],
    ) -> str:
        parts = []
        if package:
            parts.append(f"package {package};")
        for ann in class_info.get("annotations", []):
            parts.append(ann)
        parts.append(f"{class_info.get('header_line', 'public class ' + class_info.get('class_name', ''))} {{")
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

        method_sig_re = re.compile(
            r"^\s*(?:(?:public|private|protected|static|final|synchronized|abstract|default)\s+)+"
            r"(?:<[^>]+>\s+)?(?:[A-Za-z0-9_<>.\[\],\s]+)\s+([a-zA-Z0-9_]+)\s*\([^;]*$"
        )

        for line_num, line in enumerate(lines, start=1):
            if line_num <= class_info.get("line_number", 0):
                continue

            stripped = line.strip()
            if not in_method:
                if stripped.startswith("@"):
                    current_annotations.append(stripped)
                    ep_match = re.search(
                        r'@(?:GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping|RequestMapping|Path)\s*\(\s*(?:value\s*=\s*|path\s*=\s*)?["\']([^"\']+)["\']',
                        stripped,
                    )
                    if ep_match:
                        current_endpoint = ep_match.group(1)
                    continue

                m = method_sig_re.match(line)
                if m and m.group(1) not in {"if", "for", "while", "switch", "catch", "return", "new"}:
                    in_method = True
                    method_name = m.group(1)
                    method_start = line_num - len(current_annotations)
                    method_lines = [f"    {ann}\n" for ann in current_annotations] + [line]
                    brace_count = line.count("{") - line.count("}")
                    if ";" in line and "{" not in line:
                        in_method = False
                        current_annotations = []
                        current_endpoint = None
                    elif "{" in line and brace_count <= 0:
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
                elif stripped and not stripped.startswith("//") and not stripped.startswith("/*") and not stripped.startswith("*"):
                    current_annotations = []
                    current_endpoint = None
            else:
                method_lines.append(line)
                brace_count += line.count("{") - line.count("}")
                if brace_count <= 0 and any("{" in ml for ml in method_lines):
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
        return f"{(base or '').rstrip('/')}/{(path or '').lstrip('/')}"

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
        dependencies: List[str],
        extra_metadata: Optional[Dict[str, Any]],
    ) -> Chunk:
        chunk_id_raw = f"{file_path}#{class_name or ''}#{method_name or ''}#{index}#{start_line}-{end_line}"
        chunk_id = hashlib.sha256(chunk_id_raw.encode("utf-8")).hexdigest()[:16]

        meta = ServiceMetadata(
            service=self.service,
            document_type=DocumentType.SOURCE_CODE,
            source=source,
            file_path=file_path,
            language="java",
            package=package,
            class_name=class_name,
            method_name=method_name,
            endpoint=endpoint,
            start_line=start_line,
            end_line=end_line,
            extra={
                "dependencies": dependencies,
                **(extra_metadata or {}),
            },
        )

        return Chunk(
            id=chunk_id,
            content=content,
            metadata=meta,
            index=index,
        )
