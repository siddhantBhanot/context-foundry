import ast
import hashlib
from pathlib import Path
import re
from typing import Any, Dict, List, Optional

from rag_service.domain.models import Chunk, DocumentType, ServiceMetadata


class PythonChunker:
    """
    AST-native structural chunker for Python source files (.py).
    - Parses Python Abstract Syntax Tree (ast.parse) to preserve exact function and class boundaries.
    - Extracts imports, base classes, type-annotated dependencies, and FastAPI/Flask route decorators.
    - Prepends a compact Scope Header (# [Scope] File | Module | Class | Collaborators) to each chunk.
    - Records collaborator symbol names in metadata for 1-hop dependency graph expansion.
    """

    PY_BUILTINS = {
        "str", "int", "float", "bool", "bytes", "list", "dict", "set", "tuple", "Any",
        "Optional", "Union", "List", "Dict", "Set", "Tuple", "Callable", "Sequence",
        "Iterable", "AsyncIterator", "BaseModel", "Field", "Enum", "Protocol", "Path",
        "Exception", "ValueError", "RuntimeError", "HTTPException", "APIRouter", "FastAPI",
        "Depends", "Query", "Form", "File", "UploadFile",
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
        module_name = Path(file_path).stem

        try:
            tree = ast.parse(content)
        except SyntaxError:
            # Fallback if file has syntax errors or template markers
            return [
                self._create_chunk(
                    content=f"# [Scope] File: {file_name} | Module: {module_name}\n{content}",
                    file_path=file_path,
                    source=source,
                    start_line=1,
                    end_line=len(lines),
                    index=0,
                    module_name=module_name,
                    class_name=None,
                    method_name=None,
                    endpoint=None,
                    dependencies=[],
                    extra_metadata=extra_metadata,
                )
            ]

        imports, imported_symbols = self._extract_ast_imports(tree)
        router_prefix = self._extract_router_prefix(content)
        chunks: List[Chunk] = []
        chunk_idx = 0

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                class_chunks = self._chunk_class_node(
                    node=node,
                    lines=lines,
                    file_path=file_path,
                    file_name=file_name,
                    module_name=module_name,
                    source=source,
                    imports=imports,
                    imported_symbols=imported_symbols,
                    start_idx=chunk_idx,
                    extra_metadata=extra_metadata,
                )
                chunks.extend(class_chunks)
                chunk_idx += len(class_chunks)

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                start_line = self._get_node_start_line(node)
                end_line = getattr(node, "end_lineno", start_line) or start_line
                func_code = "".join(lines[start_line - 1: end_line]).strip()
                endpoint = self._extract_decorator_endpoint(node, router_prefix)
                func_deps = self._extract_function_dependencies(node, imported_symbols)
                scope_header = self._build_scope_header(
                    file_name=file_name,
                    module_name=module_name,
                    class_name=None,
                    endpoint=endpoint,
                    collaborators=func_deps,
                )
                chunks.append(
                    self._create_chunk(
                        content=f"{scope_header}\n{func_code}",
                        file_path=file_path,
                        source=source,
                        start_line=start_line,
                        end_line=end_line,
                        index=chunk_idx,
                        module_name=module_name,
                        class_name=None,
                        method_name=node.name,
                        endpoint=endpoint,
                        dependencies=func_deps,
                        extra_metadata=extra_metadata,
                    )
                )
                chunk_idx += 1

        if not chunks:
            scope_header = self._build_scope_header(
                file_name=file_name,
                module_name=module_name,
                class_name=None,
                endpoint=router_prefix,
                collaborators=imported_symbols,
            )
            chunks.append(
                self._create_chunk(
                    content=f"{scope_header}\n{content}",
                    file_path=file_path,
                    source=source,
                    start_line=1,
                    end_line=len(lines),
                    index=0,
                    module_name=module_name,
                    class_name=None,
                    method_name=None,
                    endpoint=router_prefix,
                    dependencies=imported_symbols,
                    extra_metadata=extra_metadata,
                )
            )

        return chunks

    def _chunk_class_node(
        self,
        node: ast.ClassDef,
        lines: List[str],
        file_path: str,
        file_name: str,
        module_name: str,
        source: str,
        imports: List[str],
        imported_symbols: List[str],
        start_idx: int,
        extra_metadata: Optional[Dict[str, Any]],
    ) -> List[Chunk]:
        c_start = self._get_node_start_line(node)
        c_end = getattr(node, "end_lineno", c_start) or c_start
        full_class_code = "".join(lines[c_start - 1: c_end]).strip()
        collaborators = self._extract_class_dependencies(node, imported_symbols)

        methods = [
            item for item in node.body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]

        scope_header = self._build_scope_header(
            file_name=file_name,
            module_name=module_name,
            class_name=node.name,
            endpoint=None,
            collaborators=collaborators,
        )

        # Keep small classes or Pydantic/dataclass models as a single cohesive chunk
        if not methods or len(full_class_code) <= self.max_chunk_chars:
            method_names = [m.name for m in methods]
            endpoints = [
                ep for ep in (self._extract_decorator_endpoint(m, None) for m in methods) if ep
            ]
            return [
                self._create_chunk(
                    content=f"{scope_header}\n{full_class_code}",
                    file_path=file_path,
                    source=source,
                    start_line=c_start,
                    end_line=c_end,
                    index=start_idx,
                    module_name=module_name,
                    class_name=node.name,
                    method_name=method_names[0] if len(method_names) == 1 else None,
                    endpoint=endpoints[0] if endpoints else None,
                    dependencies=collaborators,
                    extra_metadata={
                        "collaborators": collaborators,
                        "methods_in_file": method_names,
                        "endpoints_in_file": endpoints,
                        **(extra_metadata or {}),
                    },
                )
            ]

        # Split larger classes by method while preserving class signature & __init__ context
        first_method_start = self._get_node_start_line(methods[0])
        class_signature_header = "".join(lines[c_start - 1: first_method_start - 1]).rstrip()

        chunks: List[Chunk] = []
        for offset, m_node in enumerate(methods):
            m_start = self._get_node_start_line(m_node)
            m_end = getattr(m_node, "end_lineno", m_start) or m_start
            m_code = "".join(lines[m_start - 1: m_end]).rstrip()
            endpoint = self._extract_decorator_endpoint(m_node, None)

            chunk_text = f"{scope_header}\n{class_signature_header}\n    # ...\n{m_code}"
            chunks.append(
                self._create_chunk(
                    content=chunk_text,
                    file_path=file_path,
                    source=source,
                    start_line=m_start,
                    end_line=m_end,
                    index=start_idx + offset,
                    module_name=module_name,
                    class_name=node.name,
                    method_name=m_node.name,
                    endpoint=endpoint,
                    dependencies=collaborators,
                    extra_metadata={
                        "collaborators": collaborators,
                        **(extra_metadata or {}),
                    },
                )
            )
        return chunks

    def _get_node_start_line(self, node: ast.AST) -> int:
        lineno = getattr(node, "lineno", 1)
        decorators = getattr(node, "decorator_list", [])
        if decorators:
            first_dec = min(getattr(d, "lineno", lineno) for d in decorators)
            return min(lineno, first_dec)
        return lineno

    def _extract_ast_imports(self, tree: ast.Module) -> tuple[List[str], List[str]]:
        imports: List[str] = []
        symbols: List[str] = []
        stdlib_prefixes = {
            "os", "sys", "re", "json", "time", "uuid", "math", "typing", "pathlib",
            "datetime", "collections", "itertools", "functools", "asyncio", "logging",
            "hashlib", "enum", "abc", "dataclasses", "pydantic", "fastapi",
        }
        for node in tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                root_mod = mod.split(".")[0] if mod else ""
                for alias in node.names:
                    imports.append(f"{mod}.{alias.name}" if mod else alias.name)
                    if root_mod not in stdlib_prefixes and alias.name not in self.PY_BUILTINS:
                        if alias.name != "*":
                            symbols.append(alias.name)
        return imports, list(dict.fromkeys(symbols))[:15]

    def _extract_router_prefix(self, content: str) -> Optional[str]:
        m = re.search(r'APIRouter\s*\([^)]*prefix\s*=\s*["\']([^"\']+)["\']', content)
        return m.group(1) if m else None

    def _extract_decorator_endpoint(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        router_prefix: Optional[str],
    ) -> Optional[str]:
        http_methods = {"get", "post", "put", "delete", "patch", "route", "api_route"}
        for dec in node.decorator_list:
            if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
                method_name = dec.func.attr.lower()
                if method_name in http_methods:
                    path_val = ""
                    if dec.args and isinstance(dec.args[0], ast.Constant) and isinstance(dec.args[0].value, str):
                        path_val = dec.args[0].value
                    full_path = f"{(router_prefix or '').rstrip('/')}/{path_val.lstrip('/')}".rstrip("/") or "/"
                    return f"{method_name.upper()} {full_path}"
        return None

    def _extract_class_dependencies(
        self,
        node: ast.ClassDef,
        imported_symbols: List[str],
    ) -> List[str]:
        deps = list(imported_symbols)
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id not in self.PY_BUILTINS:
                deps.append(base.id)
        for sub in ast.walk(node):
            if isinstance(sub, ast.arg) and sub.annotation and isinstance(sub.annotation, ast.Name):
                if sub.annotation.id not in self.PY_BUILTINS and sub.annotation.id != node.name:
                    deps.append(sub.annotation.id)
        return list(dict.fromkeys(deps))[:15]

    def _extract_function_dependencies(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        imported_symbols: List[str],
    ) -> List[str]:
        deps = list(imported_symbols)
        for sub in ast.walk(node):
            if isinstance(sub, ast.arg) and sub.annotation and isinstance(sub.annotation, ast.Name):
                if sub.annotation.id not in self.PY_BUILTINS:
                    deps.append(sub.annotation.id)
        return list(dict.fromkeys(deps))[:15]

    def _build_scope_header(
        self,
        file_name: str,
        module_name: str,
        class_name: Optional[str],
        endpoint: Optional[str],
        collaborators: List[str],
    ) -> str:
        parts = [f"# [Scope] File: {file_name}", f"Module: {module_name}"]
        if class_name:
            parts.append(f"Class: {class_name}")
        if endpoint:
            parts.append(f"Endpoint: {endpoint}")
        line1 = " | ".join(parts)
        if collaborators:
            return f"{line1}\n# [Collaborators] {', '.join(collaborators)}"
        return line1

    def _create_chunk(
        self,
        content: str,
        file_path: str,
        source: str,
        start_line: int,
        end_line: int,
        index: int,
        module_name: Optional[str],
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
            language="python",
            package=module_name,
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
