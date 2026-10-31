import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from rag_service.domain.models import Chunk

logger = logging.getLogger("rag_service.ingestion.repo_map")

_REPO_MAP_FILENAME = "_repo_map.json"
_MEMORY_REPO_MAPS: Dict[str, Dict[str, Any]] = {}


def _get_default_storage_root() -> Path:
    return Path(__file__).resolve().parents[2] / "backend_service" / "data" / "storage" / "services"


class RepoMapBuilder:
    """
    Constructs and persists a lightweight structural Repository Map (RepoMap)
    and symbol dependency graph for each ingested microservice.

    Enables:
    1. Holistic architectural awareness via a compact Markdown blueprint injected at query time.
    2. 1-Hop Dependency Expansion by resolving collaborator symbols to their defining classes/files.
    """

    @classmethod
    def build_and_save(
        cls,
        directory_path: Path | str,
        service: str,
        chunks: List[Chunk],
    ) -> Dict[str, Any]:
        dir_path = Path(directory_path)
        files_map: Dict[str, Dict[str, Any]] = {}
        symbol_to_files: Dict[str, Set[str]] = {}

        for chunk in chunks:
            meta = chunk.metadata
            raw_path = meta.file_path or "unknown"
            try:
                rel_path = str(Path(raw_path).relative_to(dir_path))
            except ValueError:
                rel_path = Path(raw_path).name

            entry = files_map.setdefault(
                rel_path,
                {
                    "file": rel_path,
                    "language": meta.language or "markdown",
                    "package": meta.package,
                    "classes": [],
                    "methods": [],
                    "endpoints": [],
                    "dependencies": [],
                    "sections": [],
                },
            )

            if meta.package and not entry["package"]:
                entry["package"] = meta.package

            if meta.class_name and meta.class_name not in entry["classes"]:
                entry["classes"].append(meta.class_name)
                symbol_to_files.setdefault(meta.class_name, set()).add(rel_path)

            if meta.method_name and meta.method_name not in entry["methods"]:
                entry["methods"].append(meta.method_name)

            if meta.endpoint and meta.endpoint not in entry["endpoints"]:
                entry["endpoints"].append(meta.endpoint)

            extra = meta.extra or {}
            for m_name in extra.get("methods_in_file", []):
                if m_name and m_name not in entry["methods"]:
                    entry["methods"].append(m_name)

            for ep in extra.get("endpoints_in_file", []):
                if ep and ep not in entry["endpoints"]:
                    entry["endpoints"].append(ep)

            for dep in extra.get("dependencies", []):
                if dep and dep not in entry["dependencies"] and dep != meta.class_name:
                    entry["dependencies"].append(dep)

            section_title = extra.get("section_title")
            if section_title and section_title not in entry["sections"]:
                entry["sections"].append(section_title)

        # Build compact Markdown blueprint
        blueprint_lines: List[str] = [
            f"### Microservice Repository Blueprint (`{service}`)",
            f"Total Indexed Files: {len(files_map)}",
        ]

        for rel_path in sorted(files_map.keys()):
            info = files_map[rel_path]
            lang = info["language"]
            parts = [f"- `{rel_path}` [{lang}]"]
            if info["package"]:
                parts.append(f"Package/Module: `{info['package']}`")
            if info["classes"]:
                parts.append(f"Classes: {', '.join(f'`{c}`' for c in info['classes'][:8])}")
            if info["endpoints"]:
                parts.append(f"Endpoints: {', '.join(f'`{e}`' for e in info['endpoints'][:8])}")
            if info["methods"]:
                parts.append(f"Methods/Functions: {', '.join(f'`{m}`' for m in info['methods'][:10])}")
            if info["sections"] and lang in ("markdown", "pdf"):
                parts.append(f"Sections: {', '.join(f'`{s}`' for s in info['sections'][:8])}")
            if info["dependencies"]:
                parts.append(f"Collaborators: {', '.join(f'`{d}`' for d in info['dependencies'][:10])}")

            blueprint_lines.append(" | ".join(parts))

        markdown_blueprint = "\n".join(blueprint_lines)

        repo_map_data: Dict[str, Any] = {
            "service": service,
            "total_files": len(files_map),
            "files": files_map,
            "symbol_to_files": {k: sorted(list(v)) for k, v in symbol_to_files.items()},
            "markdown_blueprint": markdown_blueprint,
        }

        _MEMORY_REPO_MAPS[service] = repo_map_data

        try:
            target_file = dir_path / _REPO_MAP_FILENAME
            target_file.write_text(json.dumps(repo_map_data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning("Could not write _repo_map.json to %s: %s", dir_path, e)

        return repo_map_data

    @classmethod
    def load(cls, service: str, storage_root: Optional[Path] = None) -> Optional[Dict[str, Any]]:
        if service in _MEMORY_REPO_MAPS:
            return _MEMORY_REPO_MAPS[service]

        root = storage_root or _get_default_storage_root()
        map_file = root / service / _REPO_MAP_FILENAME
        if map_file.is_file():
            try:
                data = json.loads(map_file.read_text(encoding="utf-8"))
                _MEMORY_REPO_MAPS[service] = data
                return data
            except Exception as e:
                logger.warning("Failed to load _repo_map.json for service '%s': %s", service, e)
        return None

    @classmethod
    def load_markdown(
        cls,
        service: str,
        storage_root: Optional[Path] = None,
        focus_files: Optional[List[str]] = None,
        query_text: Optional[str] = None,
        max_chars: int = 3600,
    ) -> Optional[str]:
        data = cls.load(service, storage_root=storage_root)
        if not data:
            return None

        files_map: Dict[str, Dict[str, Any]] = data.get("files") or {}
        if not files_map:
            bp = data.get("markdown_blueprint", "")
            return bp[:max_chars] if bp else None

        full_bp = data.get("markdown_blueprint", "")
        if len(full_bp) <= max_chars and not focus_files and not query_text:
            return full_bp

        # Rank files so retrieved files, collaborators, and query-matched files appear first within the token budget
        import re
        q_tokens = set(re.findall(r"[a-zA-Z0-9_]{3,}", (query_text or "").lower()))
        focus_names = {Path(f).name for f in (focus_files or [])}

        def _score_file(rel_path: str, info: Dict[str, Any]) -> tuple:
            fname = Path(rel_path).name
            is_focused = 1 if (rel_path in (focus_files or []) or fname in focus_names) else 0
            text_repr = " ".join(
                [rel_path]
                + (info.get("classes") or [])
                + (info.get("endpoints") or [])
                + (info.get("methods") or [])
                + (info.get("dependencies") or [])
            ).lower()
            token_hits = sum(1 for t in q_tokens if t in text_repr)
            has_endpoints = 1 if info.get("endpoints") else 0
            return (is_focused, token_hits, has_endpoints, -len(rel_path))

        sorted_paths = sorted(
            files_map.keys(),
            key=lambda p: _score_file(p, files_map[p]),
            reverse=True,
        )

        lines = [
            f"### Microservice Repository Blueprint (`{service}` — {len(files_map)} total files)",
        ]
        current_len = len(lines[0])
        included = 0

        for rel_path in sorted_paths:
            info = files_map[rel_path]
            lang = info.get("language", "code")
            parts = [f"- `{rel_path}` [{lang}]"]
            if info.get("package"):
                parts.append(f"Pkg: `{info['package']}`")
            if info.get("classes"):
                parts.append(f"Classes: {', '.join(f'`{c}`' for c in info['classes'][:5])}")
            if info.get("endpoints"):
                parts.append(f"Endpoints: {', '.join(f'`{e}`' for e in info['endpoints'][:5])}")
            if info.get("methods"):
                parts.append(f"Methods: {', '.join(f'`{m}`' for m in info['methods'][:6])}")
            if info.get("dependencies"):
                parts.append(f"Collaborators: {', '.join(f'`{d}`' for d in info['dependencies'][:6])}")

            line_str = " | ".join(parts)
            if current_len + len(line_str) + 2 > max_chars:
                remaining = len(files_map) - included
                if remaining > 0:
                    lines.append(f"- *(...and {remaining} additional files in `{service}`)*")
                break
            lines.append(line_str)
            current_len += len(line_str) + 1
            included += 1

        return "\n".join(lines)
