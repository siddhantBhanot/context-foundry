import json
import logging
from enum import Enum
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from pydantic import BaseModel, Field

logger = logging.getLogger("rag_service.ingestion.symbol_graph")

_SYMBOL_GRAPH_FILENAME = "_symbol_graph.json"
_MEMORY_SYMBOL_GRAPHS: Dict[str, "SymbolGraphIndex"] = {}


def _get_default_storage_root() -> Path:
    return Path(__file__).resolve().parents[2] / "backend_service" / "data" / "storage" / "services"


# ---------------------------------------------------------------------------
# Domain Models: Nodes & Edges
# ---------------------------------------------------------------------------


class NodeType(str, Enum):
    FILE = "file"
    CLASS = "class"
    INTERFACE = "interface"
    METHOD = "method"
    ENDPOINT = "endpoint"
    CONFIGURATION = "configuration"


class EdgeType(str, Enum):
    DEFINES = "defines"
    IMPORTS = "imports"
    EXTENDS = "extends"
    IMPLEMENTS = "implements"
    DEPENDS_ON = "depends_on"
    CALLS = "calls"
    CALLED_BY = "called_by"
    EXPOSES = "exposes"
    INVOKES = "invokes"
    CONFIGURES = "configures"
    REFERENCES = "references"


class SymbolNode(BaseModel):
    id: str = Field(..., description="Unique node identifier, e.g. 'io.spring.api.ArticlesApi#createArticle'")
    name: str = Field(..., description="Display name, e.g. 'createArticle' or 'ArticlesApi.createArticle'")
    node_type: NodeType
    file_path: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    package: Optional[str] = None
    parent_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SymbolEdge(BaseModel):
    source_id: str
    target_id: str
    edge_type: EdgeType
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SymbolGraph(BaseModel):
    service: str
    total_nodes: int = 0
    total_edges: int = 0
    nodes: Dict[str, SymbolNode] = Field(default_factory=dict)
    edges: List[SymbolEdge] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# In-Memory Graph Index for Sub-Millisecond Multi-Hop Traversal
# ---------------------------------------------------------------------------


class SymbolGraphIndex:
    """
    In-memory graph index providing fast traversal (callees, callers, implementations)
    and call hierarchy trace formatting for prompt context injection.
    """

    def __init__(self, graph: SymbolGraph) -> None:
        self.graph = graph
        self.nodes = graph.nodes
        self.outgoing: Dict[str, List[SymbolEdge]] = {}
        self.incoming: Dict[str, List[SymbolEdge]] = {}
        self.method_names_map: Dict[str, List[str]] = {}
        self.class_names_map: Dict[str, List[str]] = {}
        self.endpoints_map: Dict[str, List[str]] = {}

        self._build_indexes()

    def _build_indexes(self) -> None:
        for node_id, node in self.nodes.items():
            if node.node_type == NodeType.METHOD:
                # Index by full display name, short name, and ID
                self.method_names_map.setdefault(node.name, []).append(node_id)
                short_name = node.metadata.get("short_name")
                if short_name and short_name != node.name:
                    self.method_names_map.setdefault(short_name, []).append(node_id)
                self.method_names_map.setdefault(node_id, []).append(node_id)
            elif node.node_type in (NodeType.CLASS, NodeType.INTERFACE):
                self.class_names_map.setdefault(node.name, []).append(node_id)
                fqn = node.metadata.get("fqn")
                if fqn and fqn != node.name:
                    self.class_names_map.setdefault(fqn, []).append(node_id)
                self.class_names_map.setdefault(node_id, []).append(node_id)
            elif node.node_type == NodeType.ENDPOINT:
                self.endpoints_map.setdefault(node.name, []).append(node_id)
                self.endpoints_map.setdefault(node_id, []).append(node_id)

        for edge in self.graph.edges:
            self.outgoing.setdefault(edge.source_id, []).append(edge)
            self.incoming.setdefault(edge.target_id, []).append(edge)

    def find_nodes_by_name(self, name: str) -> List[SymbolNode]:
        node_ids: List[str] = []
        if name in self.method_names_map:
            node_ids.extend(self.method_names_map[name])
        if name in self.class_names_map:
            node_ids.extend(self.class_names_map[name])
        if name in self.endpoints_map:
            node_ids.extend(self.endpoints_map[name])
        return [self.nodes[nid] for nid in dict.fromkeys(node_ids) if nid in self.nodes]

    def traverse(
        self,
        seed_id: str,
        direction: str = "outgoing",
        max_depth: int = 2,
        edge_types: Optional[Set[EdgeType]] = None,
    ) -> List[Tuple[SymbolNode, int, EdgeType]]:
        """
        Traverse graph from seed_id using BFS up to max_depth.
        Returns list of (SymbolNode, depth, EdgeType).
        """
        results: List[Tuple[SymbolNode, int, EdgeType]] = []
        visited: Set[str] = {seed_id}
        queue: List[Tuple[str, int]] = [(seed_id, 0)]

        while queue:
            curr_id, depth = queue.pop(0)
            if depth >= max_depth:
                continue

            edges_to_check: List[SymbolEdge] = []
            if direction in ("outgoing", "both"):
                edges_to_check.extend(self.outgoing.get(curr_id, []))
            if direction in ("incoming", "both"):
                edges_to_check.extend(self.incoming.get(curr_id, []))

            for edge in edges_to_check:
                if edge_types and edge.edge_type not in edge_types:
                    continue

                neighbor_id = edge.target_id if edge.source_id == curr_id else edge.source_id
                if neighbor_id not in visited and neighbor_id in self.nodes:
                    visited.add(neighbor_id)
                    neighbor_node = self.nodes[neighbor_id]
                    results.append((neighbor_node, depth + 1, edge.edge_type))
                    queue.append((neighbor_id, depth + 1))

        return results

    def get_callees(self, method_id_or_name: str, max_depth: int = 2) -> List[SymbolNode]:
        """Return all methods invoked by the target method."""
        nodes = self.find_nodes_by_name(method_id_or_name)
        if not nodes:
            return []
        seed = nodes[0]
        traversed = self.traverse(
            seed_id=seed.id,
            direction="outgoing",
            max_depth=max_depth,
            edge_types={EdgeType.CALLS},
        )
        return [n for n, _, _ in traversed if n.node_type == NodeType.METHOD]

    def get_callers(self, method_id_or_name: str, max_depth: int = 2) -> List[SymbolNode]:
        """Return all methods or endpoints invoking the target method."""
        nodes = self.find_nodes_by_name(method_id_or_name)
        if not nodes:
            return []
        seed = nodes[0]
        traversed = self.traverse(
            seed_id=seed.id,
            direction="incoming",
            max_depth=max_depth,
            edge_types={EdgeType.CALLED_BY, EdgeType.INVOKES},
        )
        return [n for n, _, _ in traversed if n.node_type in (NodeType.METHOD, NodeType.ENDPOINT)]

    def get_implementations(self, interface_id_or_name: str) -> List[SymbolNode]:
        """Find classes or methods that implement this interface or interface method."""
        impls: List[SymbolNode] = []
        target_ids = [interface_id_or_name]
        if interface_id_or_name in self.class_names_map:
            target_ids.extend(self.class_names_map[interface_id_or_name])
        if interface_id_or_name in self.method_names_map:
            target_ids.extend(self.method_names_map[interface_id_or_name])

        for tid in target_ids:
            for edge in self.incoming.get(tid, []):
                if edge.edge_type == EdgeType.IMPLEMENTS and edge.source_id in self.nodes:
                    impls.append(self.nodes[edge.source_id])
        return impls

    def build_call_hierarchy_trace(
        self,
        seed_methods: List[str],
        max_depth: int = 3,
    ) -> List[str]:
        """
        Builds a human-readable, grounded call hierarchy trace for prompt injection.
        Example:
        • [Ingress API] POST /articles (ArticlesApi.java L28)
          ↳ [Invokes] ArticlesApi.createArticle (ArticlesApi.java L29)
            ↳ [Calls] ArticleCommandService.createArticle (ArticleCommandService.java L18)
              ↳ [Calls] ArticleRepository.save (ArticleRepository.java L7)
                ↳ [Implemented by] MyBatisArticleRepository.save (MyBatisArticleRepository.java L21)
        """
        trace_lines: List[str] = []
        seen_calls: Set[Tuple[str, str]] = set()

        # Resolve seed identifiers to actual method / endpoint nodes
        resolved_nodes: List[SymbolNode] = []
        for sm in seed_methods:
            if sm in self.nodes:
                resolved_nodes.append(self.nodes[sm])
            elif sm in self.method_names_map:
                for nid in self.method_names_map[sm]:
                    if nid in self.nodes:
                        resolved_nodes.append(self.nodes[nid])

        for seed in resolved_nodes[:4]:
            # 1. Look for incoming triggers (e.g. Endpoints invoking this method)
            incoming_edges = self.incoming.get(seed.id, [])
            has_ingress = False
            for in_edge in incoming_edges:
                if in_edge.edge_type in (EdgeType.INVOKES, EdgeType.EXPOSES):
                    ep_node = self.nodes.get(in_edge.source_id)
                    if ep_node and ep_node.node_type == NodeType.ENDPOINT:
                        has_ingress = True
                        ep_file = Path(ep_node.file_path).name
                        ep_line = f" L{ep_node.line_start}" if ep_node.line_start else ""
                        trace_lines.append(f"• [Ingress API] {ep_node.name} ({ep_file}{ep_line})")
                        seed_file = Path(seed.file_path).name
                        seed_line = f" L{seed.line_start}" if seed.line_start else ""
                        trace_lines.append(f"  ↳ [Invokes] {seed.name} ({seed_file}{seed_line})")

            # If no endpoint found, print root method
            if not has_ingress:
                seed_file = Path(seed.file_path).name
                seed_line = f" L{seed.line_start}" if seed.line_start else ""
                trace_lines.append(f"• [Method] {seed.name} ({seed_file}{seed_line})")

            # 2. Forward call chain (Callees)
            curr_nodes = [(seed, 1)]
            visited_in_tree = {seed.id}

            while curr_nodes:
                c_node, depth = curr_nodes.pop(0)
                if depth > max_depth:
                    continue

                out_edges = self.outgoing.get(c_node.id, [])
                for edge in out_edges:
                    if edge.edge_type != EdgeType.CALLS:
                        continue
                    callee_id = edge.target_id
                    pair = (c_node.id, callee_id)
                    if pair in seen_calls:
                        continue
                    seen_calls.add(pair)

                    callee_node = self.nodes.get(callee_id)
                    if not callee_node:
                        continue

                    indent = "  " * depth
                    callee_file = Path(callee_node.file_path).name
                    callee_line = f" L{callee_node.line_start}" if callee_node.line_start else ""

                    poly_via = edge.metadata.get("polymorphic_via")
                    if poly_via:
                        trace_lines.append(
                            f"{indent}↳ [Implemented by via {poly_via}] {callee_node.name} ({callee_file}{callee_line})"
                        )
                    else:
                        trace_lines.append(f"{indent}↳ [Calls] {callee_node.name} ({callee_file}{callee_line})")

                    if callee_node.id not in visited_in_tree:
                        visited_in_tree.add(callee_node.id)
                        curr_nodes.append((callee_node, depth + 1))

        # Deduplicate consecutive lines
        deduped: List[str] = []
        for line in trace_lines:
            if not deduped or deduped[-1] != line:
                deduped.append(line)
        return deduped[:16]

    @classmethod
    def load(cls, service: str, storage_root: Optional[Path] = None) -> Optional["SymbolGraphIndex"]:
        if service in _MEMORY_SYMBOL_GRAPHS:
            return _MEMORY_SYMBOL_GRAPHS[service]

        root = storage_root or _get_default_storage_root()
        graph_file = root / service / _SYMBOL_GRAPH_FILENAME
        if graph_file.is_file():
            try:
                data = json.loads(graph_file.read_text(encoding="utf-8"))
                nodes = {k: SymbolNode(**v) for k, v in data.get("nodes", {}).items()}
                edges = [SymbolEdge(**e) for e in data.get("edges", [])]
                graph = SymbolGraph(
                    service=service,
                    total_nodes=len(nodes),
                    total_edges=len(edges),
                    nodes=nodes,
                    edges=edges,
                )
                idx = cls(graph)
                _MEMORY_SYMBOL_GRAPHS[service] = idx
                return idx
            except Exception as e:
                logger.warning("Failed to load _symbol_graph.json for service '%s': %s", service, e)
        return None


# ---------------------------------------------------------------------------
# Two-Pass Deterministic Symbol Table & AST Extraction Engine
# ---------------------------------------------------------------------------


class SymbolGraphBuilder:
    """
    Constructs the Lightweight Symbol Graph (LSG) for a microservice repository.
    Pass 1: AST declaration & scope indexing (Classes, Interfaces, Methods, Endpoints, DI fields).
    Pass 2: Invocation linking & polymorphic call graph resolution.
    """

    def __init__(self, service: str) -> None:
        self.service = service
        self.nodes: Dict[str, SymbolNode] = {}
        self.edges: List[SymbolEdge] = []
        self._seen_edge_keys: Set[Tuple[str, str, str]] = set()

        # Scope tables for Pass 2 resolution
        self.class_fields: Dict[str, Dict[str, str]] = {}
        self.class_methods: Dict[str, Dict[str, str]] = {}
        self.interface_to_impls: Dict[str, List[str]] = {}
        self.class_to_interfaces: Dict[str, List[str]] = {}
        self.class_extends: Dict[str, str] = {}
        self.class_fqn_map: Dict[str, str] = {}
        self.fqn_to_class_name: Dict[str, str] = {}
        self.file_imports: Dict[str, Dict[str, str]] = {}
        self.file_package: Dict[str, str] = {}

    def _add_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: EdgeType,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        key = (source_id, target_id, edge_type.value)
        if key not in self._seen_edge_keys:
            self._seen_edge_keys.add(key)
            self.edges.append(
                SymbolEdge(
                    source_id=source_id,
                    target_id=target_id,
                    edge_type=edge_type,
                    metadata=metadata or {},
                )
            )

    @classmethod
    def build_and_save(
        cls,
        directory_path: Path | str,
        service: str,
        storage_root: Optional[Path] = None,
    ) -> SymbolGraph:
        builder = cls(service=service)
        dir_path = Path(directory_path)

        candidate_files: List[Path] = []
        allowed_suffixes = {".java", ".kt", ".kts", ".py", ".yml", ".yaml", ".properties"}
        for p in sorted(dir_path.glob("**/*")):
            if (
                p.is_file()
                and p.suffix.lower() in allowed_suffixes
                and not p.name.startswith(".")
                and "pending" not in p.parts
            ):
                candidate_files.append(p)

        # 1. PASS 1: Scope & Declarations
        pass1_ast_cache: Dict[str, Any] = {}
        for p in candidate_files:
            rel_path = str(p.relative_to(dir_path)) if dir_path in p.parents else p.name
            try:
                content_bytes = p.read_bytes()
                builder._pass1_file(p, rel_path, content_bytes, pass1_ast_cache)
            except Exception as e:
                logger.debug("Pass 1 skipped file %s: %s", rel_path, e)

        # 2. PASS 2: Invocations & Call Linking
        for p in candidate_files:
            rel_path = str(p.relative_to(dir_path)) if dir_path in p.parents else p.name
            try:
                builder._pass2_file(p, rel_path, pass1_ast_cache)
            except Exception as e:
                logger.debug("Pass 2 skipped file %s: %s", rel_path, e)

        graph = SymbolGraph(
            service=service,
            total_nodes=len(builder.nodes),
            total_edges=len(builder.edges),
            nodes=builder.nodes,
            edges=builder.edges,
        )

        try:
            target_json = dir_path / _SYMBOL_GRAPH_FILENAME
            target_json.write_text(json.dumps(graph.model_dump(), indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning("Could not write _symbol_graph.json to %s: %s", dir_path, e)

        root = storage_root or _get_default_storage_root()
        service_dir = root / service
        if service_dir.is_dir():
            try:
                (service_dir / _SYMBOL_GRAPH_FILENAME).write_text(
                    json.dumps(graph.model_dump(), indent=2), encoding="utf-8"
                )
            except Exception as e:
                logger.warning("Could not copy _symbol_graph.json to service storage: %s", e)

        _MEMORY_SYMBOL_GRAPHS[service] = SymbolGraphIndex(graph)
        logger.info(
            "Built SymbolGraph for '%s': %d nodes, %d edges across %d files.",
            service,
            len(builder.nodes),
            len(builder.edges),
            len(candidate_files),
        )
        return graph

    # -----------------------------------------------------------------------
    # PASS 1 Implementation
    # -----------------------------------------------------------------------

    def _pass1_file(
        self,
        path: Path,
        rel_path: str,
        content_bytes: bytes,
        ast_cache: Dict[str, Any],
    ) -> None:
        suffix = path.suffix.lower()

        file_node_id = f"file://{rel_path}"
        self.nodes[file_node_id] = SymbolNode(
            id=file_node_id,
            name=path.name,
            node_type=NodeType.FILE,
            file_path=rel_path,
            line_start=1,
            line_end=len(content_bytes.splitlines()),
            metadata={"size_bytes": len(content_bytes)},
        )

        if suffix == ".java":
            self._pass1_java(path, rel_path, content_bytes, file_node_id, ast_cache)
        elif suffix in (".kt", ".kts"):
            self._pass1_kotlin(path, rel_path, content_bytes, file_node_id, ast_cache)
        elif suffix == ".py":
            self._pass1_python(path, rel_path, content_bytes, file_node_id, ast_cache)
        elif suffix in (".yml", ".yaml", ".properties"):
            self._pass1_config(path, rel_path, content_bytes, file_node_id)

    def _pass1_java(
        self,
        path: Path,
        rel_path: str,
        content_bytes: bytes,
        file_node_id: str,
        ast_cache: Dict[str, Any],
    ) -> None:
        import tree_sitter_java as tsjava
        from tree_sitter import Language, Parser

        java_lang = Language(tsjava.language())
        parser = Parser(java_lang)
        tree = parser.parse(content_bytes)
        ast_cache[rel_path] = (tree, content_bytes, "java")

        root = tree.root_node
        package_name = ""
        imports: Dict[str, str] = {}

        for child in root.children:
            if child.type == "package_declaration":
                for sub in child.children:
                    if sub.type in ("scoped_identifier", "identifier"):
                        package_name = content_bytes[sub.start_byte:sub.end_byte].decode("utf-8", "ignore")
            elif child.type == "import_declaration":
                for sub in child.children:
                    if sub.type == "scoped_identifier":
                        imp_text = content_bytes[sub.start_byte:sub.end_byte].decode("utf-8", "ignore")
                        sym = imp_text.split(".")[-1]
                        imports[sym] = imp_text

        self.file_package[rel_path] = package_name
        self.file_imports[rel_path] = imports

        for child in root.children:
            if child.type in ("class_declaration", "interface_declaration", "enum_declaration", "record_declaration"):
                self._extract_java_type(child, rel_path, package_name, file_node_id, content_bytes)

    def _extract_java_type(
        self,
        node: Any,
        rel_path: str,
        package_name: str,
        file_node_id: str,
        content_bytes: bytes,
    ) -> None:
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        type_name = content_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8", "ignore")
        fqn = f"{package_name}.{type_name}" if package_name else type_name

        self.class_fqn_map[type_name] = fqn
        self.fqn_to_class_name[fqn] = type_name
        is_interface = node.type == "interface_declaration"
        node_type = NodeType.INTERFACE if is_interface else NodeType.CLASS

        class_node_id = fqn
        line_start = node.start_point[0] + 1
        line_end = node.end_point[0] + 1

        # Check modifiers node (a child with type 'modifiers')
        base_route = ""
        annotations: List[str] = []
        for c in node.children:
            if c.type == "modifiers":
                for mod in c.children:
                    if mod.type in ("annotation", "marker_annotation"):
                        ann_text = content_bytes[mod.start_byte:mod.end_byte].decode("utf-8", "ignore")
                        annotations.append(ann_text)
                        if "RequestMapping" in ann_text:
                            match = re.search(r'["\']([^"\']+)["\']', ann_text)
                            if match:
                                base_route = match.group(1)

        self.nodes[class_node_id] = SymbolNode(
            id=class_node_id,
            name=type_name,
            node_type=node_type,
            file_path=rel_path,
            line_start=line_start,
            line_end=line_end,
            package=package_name,
            parent_id=file_node_id,
            metadata={"fqn": fqn, "annotations": annotations, "is_interface": is_interface, "base_route": base_route},
        )
        self._add_edge(file_node_id, class_node_id, EdgeType.DEFINES)

        # Superclass & Interfaces
        super_node = node.child_by_field_name("superclass")
        if super_node:
            for s_child in super_node.children:
                if s_child.type == "type_identifier":
                    s_name = content_bytes[s_child.start_byte:s_child.end_byte].decode("utf-8", "ignore")
                    self.class_extends[type_name] = s_name
                    self._add_edge(class_node_id, s_name, EdgeType.EXTENDS)

        interfaces_node = node.child_by_field_name("interfaces")
        if interfaces_node:
            for i_child in interfaces_node.children:
                if i_child.type == "type_list":
                    for t_node in i_child.children:
                        if t_node.type == "type_identifier":
                            i_name = content_bytes[t_node.start_byte:t_node.end_byte].decode("utf-8", "ignore")
                            self.interface_to_impls.setdefault(i_name, []).append(type_name)
                            self.class_to_interfaces.setdefault(type_name, []).append(i_name)
                            self._add_edge(class_node_id, i_name, EdgeType.IMPLEMENTS)

        # Body declarations (fields, constructors, methods)
        body_node = node.child_by_field_name("body")
        if not body_node:
            return

        fields: Dict[str, str] = {}
        for b_child in body_node.children:
            if b_child.type == "field_declaration":
                type_sub = b_child.child_by_field_name("type")
                decl_sub = b_child.child_by_field_name("declarator")
                if type_sub and decl_sub:
                    t_str = content_bytes[type_sub.start_byte:type_sub.end_byte].decode("utf-8", "ignore")
                    m_gen = re.search(r"<([a-zA-Z0-9_]+)>", t_str)
                    raw_type = m_gen.group(1) if m_gen else t_str
                    name_sub = decl_sub.child_by_field_name("name")
                    if name_sub:
                        f_name = content_bytes[name_sub.start_byte:name_sub.end_byte].decode("utf-8", "ignore")
                        fields[f_name] = raw_type
                        self._add_edge(class_node_id, raw_type, EdgeType.DEPENDS_ON)
            elif b_child.type == "constructor_declaration":
                params = b_child.child_by_field_name("parameters")
                if params:
                    for p_node in params.children:
                        if p_node.type == "formal_parameter":
                            pt = p_node.child_by_field_name("type")
                            pn = p_node.child_by_field_name("name")
                            if pt and pn:
                                pt_str = content_bytes[pt.start_byte:pt.end_byte].decode("utf-8", "ignore")
                                pn_str = content_bytes[pn.start_byte:pn.end_byte].decode("utf-8", "ignore")
                                fields[pn_str] = pt_str
                                self._add_edge(class_node_id, pt_str, EdgeType.DEPENDS_ON)
            elif b_child.type == "method_declaration":
                self._extract_java_method(
                    b_child, class_node_id, type_name, rel_path, package_name, base_route, content_bytes
                )

        self.class_fields[type_name] = fields

    def _extract_java_method(
        self,
        node: Any,
        class_node_id: str,
        type_name: str,
        rel_path: str,
        package_name: str,
        base_route: str,
        content_bytes: bytes,
    ) -> None:
        m_name_node = node.child_by_field_name("name")
        if not m_name_node:
            return
        m_name = content_bytes[m_name_node.start_byte:m_name_node.end_byte].decode("utf-8", "ignore")
        method_id = f"{class_node_id}#{m_name}"

        line_start = node.start_point[0] + 1
        line_end = node.end_point[0] + 1

        # Check for HTTP annotations in modifiers
        endpoint_str: Optional[str] = None
        http_method: Optional[str] = None
        for c in node.children:
            if c.type == "modifiers":
                for mod in c.children:
                    if mod.type in ("annotation", "marker_annotation"):
                        ann_text = content_bytes[mod.start_byte:mod.end_byte].decode("utf-8", "ignore")
                        for verb in ("GetMapping", "PostMapping", "PutMapping", "DeleteMapping", "PatchMapping", "RequestMapping"):
                            if verb in ann_text:
                                http_method = verb.replace("Mapping", "").upper() if verb != "RequestMapping" else "REQUEST"
                                sub_path = ""
                                m_route = re.search(r'["\']([^"\']+)["\']', ann_text)
                                if m_route and verb != "RequestMapping":
                                    sub_path = m_route.group(1)
                                full_parts = [p.strip("/") for p in (base_route, sub_path) if p and p.strip("/")]
                                full_route = "/" + "/".join(full_parts) if full_parts else "/"
                                endpoint_str = f"{http_method} {full_route}"
                                break

        method_node = SymbolNode(
            id=method_id,
            name=f"{type_name}.{m_name}",
            node_type=NodeType.METHOD,
            file_path=rel_path,
            line_start=line_start,
            line_end=line_end,
            package=package_name,
            parent_id=class_node_id,
            metadata={"short_name": m_name, "class_name": type_name, "endpoint": endpoint_str},
        )
        self.nodes[method_id] = method_node
        self._add_edge(class_node_id, method_id, EdgeType.DEFINES)
        self.class_methods.setdefault(type_name, {})[m_name] = method_id

        if endpoint_str:
            ep_node_id = f"endpoint://{endpoint_str}"
            if ep_node_id not in self.nodes:
                self.nodes[ep_node_id] = SymbolNode(
                    id=ep_node_id,
                    name=endpoint_str,
                    node_type=NodeType.ENDPOINT,
                    file_path=rel_path,
                    line_start=line_start,
                    line_end=line_end,
                    metadata={"http_method": http_method, "handler": method_id},
                )
            self._add_edge(ep_node_id, method_id, EdgeType.INVOKES)
            self._add_edge(method_id, ep_node_id, EdgeType.EXPOSES)

    def _pass1_kotlin(
        self,
        path: Path,
        rel_path: str,
        content_bytes: bytes,
        file_node_id: str,
        ast_cache: Dict[str, Any],
    ) -> None:
        import tree_sitter_kotlin as tskotlin
        from tree_sitter import Language, Parser

        kt_lang = Language(tskotlin.language())
        parser = Parser(kt_lang)
        tree = parser.parse(content_bytes)
        ast_cache[rel_path] = (tree, content_bytes, "kotlin")

        root = tree.root_node
        package_name = ""
        imports: Dict[str, str] = {}

        for child in root.children:
            if child.type == "package_header":
                for sub in child.children:
                    if sub.type == "qualified_identifier":
                        package_name = content_bytes[sub.start_byte:sub.end_byte].decode("utf-8", "ignore")
            elif child.type == "import":
                for sub in child.children:
                    if sub.type == "qualified_identifier":
                        imp_text = content_bytes[sub.start_byte:sub.end_byte].decode("utf-8", "ignore")
                        sym = imp_text.split(".")[-1]
                        imports[sym] = imp_text

        self.file_package[rel_path] = package_name
        self.file_imports[rel_path] = imports

        for child in root.children:
            if child.type == "class_declaration":
                self._extract_kotlin_class(child, rel_path, package_name, file_node_id, content_bytes)

    def _extract_kotlin_class(
        self,
        node: Any,
        rel_path: str,
        package_name: str,
        file_node_id: str,
        content_bytes: bytes,
    ) -> None:
        type_name = ""
        for n in node.children:
            if n.type in ("identifier", "simple_identifier"):
                type_name = content_bytes[n.start_byte:n.end_byte].decode("utf-8", "ignore")
                break
        if not type_name:
            return

        fqn = f"{package_name}.{type_name}" if package_name else type_name
        self.class_fqn_map[type_name] = fqn
        self.fqn_to_class_name[fqn] = type_name

        class_node_id = fqn
        line_start = node.start_point[0] + 1
        line_end = node.end_point[0] + 1

        self.nodes[class_node_id] = SymbolNode(
            id=class_node_id,
            name=type_name,
            node_type=NodeType.CLASS,
            file_path=rel_path,
            line_start=line_start,
            line_end=line_end,
            package=package_name,
            parent_id=file_node_id,
            metadata={"fqn": fqn},
        )
        self._add_edge(file_node_id, class_node_id, EdgeType.DEFINES)

        fields: Dict[str, str] = {}

        for c in node.children:
            if c.type == "primary_constructor":
                for p in c.children:
                    if p.type == "class_parameters":
                        for param in p.children:
                            if param.type == "class_parameter":
                                p_name = ""
                                p_type = ""
                                for p_child in param.children:
                                    if p_child.type in ("identifier", "simple_identifier") and not p_name:
                                        p_name = content_bytes[p_child.start_byte:p_child.end_byte].decode("utf-8", "ignore")
                                    elif p_child.type in ("user_type", "type_identifier"):
                                        p_type = content_bytes[p_child.start_byte:p_child.end_byte].decode("utf-8", "ignore")
                                if p_name and p_type:
                                    fields[p_name] = p_type
                                    self._add_edge(class_node_id, p_type, EdgeType.DEPENDS_ON)
            elif c.type == "delegation_specifiers":
                for spec in c.children:
                    for s_child in spec.children:
                        if s_child.type in ("user_type", "type_identifier"):
                            i_name = content_bytes[s_child.start_byte:s_child.end_byte].decode("utf-8", "ignore")
                            self.interface_to_impls.setdefault(i_name, []).append(type_name)
                            self.class_to_interfaces.setdefault(type_name, []).append(i_name)
                            self._add_edge(class_node_id, i_name, EdgeType.IMPLEMENTS)
            elif c.type == "class_body":
                for b_child in c.children:
                    if b_child.type in ("function_declaration", "named_function"):
                        f_name = ""
                        for fn_child in b_child.children:
                            if fn_child.type in ("identifier", "simple_identifier"):
                                f_name = content_bytes[fn_child.start_byte:fn_child.end_byte].decode("utf-8", "ignore")
                                break
                        if f_name:
                            method_id = f"{class_node_id}#{f_name}"
                            self.nodes[method_id] = SymbolNode(
                                id=method_id,
                                name=f"{type_name}.{f_name}",
                                node_type=NodeType.METHOD,
                                file_path=rel_path,
                                line_start=b_child.start_point[0] + 1,
                                line_end=b_child.end_point[0] + 1,
                                package=package_name,
                                parent_id=class_node_id,
                                metadata={"short_name": f_name, "class_name": type_name},
                            )
                            self._add_edge(class_node_id, method_id, EdgeType.DEFINES)
                            self.class_methods.setdefault(type_name, {})[f_name] = method_id

        self.class_fields[type_name] = fields

    def _pass1_python(
        self,
        path: Path,
        rel_path: str,
        content_bytes: bytes,
        file_node_id: str,
        ast_cache: Dict[str, Any],
    ) -> None:
        import tree_sitter_python as tspy
        from tree_sitter import Language, Parser

        py_lang = Language(tspy.language())
        parser = Parser(py_lang)
        tree = parser.parse(content_bytes)
        ast_cache[rel_path] = (tree, content_bytes, "python")

        root = tree.root_node
        module_name = path.stem
        self.file_package[rel_path] = module_name

        for child in root.children:
            if child.type == "class_definition":
                self._extract_python_class(child, rel_path, module_name, file_node_id, content_bytes)

    def _extract_python_class(
        self,
        node: Any,
        rel_path: str,
        module_name: str,
        file_node_id: str,
        content_bytes: bytes,
    ) -> None:
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        class_name = content_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8", "ignore")
        class_node_id = f"{module_name}.{class_name}"

        self.nodes[class_node_id] = SymbolNode(
            id=class_node_id,
            name=class_name,
            node_type=NodeType.CLASS,
            file_path=rel_path,
            line_start=node.start_point[0] + 1,
            line_end=node.end_point[0] + 1,
            package=module_name,
            parent_id=file_node_id,
            metadata={"class_name": class_name},
        )
        self._add_edge(file_node_id, class_node_id, EdgeType.DEFINES)

        fields: Dict[str, str] = {}
        body = node.child_by_field_name("body")
        if body:
            for b_child in body.children:
                if b_child.type == "function_definition":
                    fn_name_node = b_child.child_by_field_name("name")
                    if not fn_name_node:
                        continue
                    fn_name = content_bytes[fn_name_node.start_byte:fn_name_node.end_byte].decode("utf-8", "ignore")
                    method_id = f"{class_node_id}#{fn_name}"

                    self.nodes[method_id] = SymbolNode(
                        id=method_id,
                        name=f"{class_name}.{fn_name}",
                        node_type=NodeType.METHOD,
                        file_path=rel_path,
                        line_start=b_child.start_point[0] + 1,
                        line_end=b_child.end_point[0] + 1,
                        package=module_name,
                        parent_id=class_node_id,
                        metadata={"short_name": fn_name, "class_name": class_name},
                    )
                    self._add_edge(class_node_id, method_id, EdgeType.DEFINES)
                    self.class_methods.setdefault(class_name, {})[fn_name] = method_id

                    if fn_name == "__init__":
                        params = b_child.child_by_field_name("parameters")
                        if params:
                            for p in params.children:
                                if p.type == "typed_parameter":
                                    p_id = p.child_by_field_name("name") or p.children[0]
                                    p_type = p.child_by_field_name("type") or p.children[-1]
                                    p_name_str = content_bytes[p_id.start_byte:p_id.end_byte].decode("utf-8", "ignore")
                                    p_type_str = content_bytes[p_type.start_byte:p_type.end_byte].decode("utf-8", "ignore")
                                    fields[p_name_str] = p_type_str
                                    self._add_edge(class_node_id, p_type_str, EdgeType.DEPENDS_ON)

        self.class_fields[class_name] = fields

    def _pass1_config(
        self,
        path: Path,
        rel_path: str,
        content_bytes: bytes,
        file_node_id: str,
    ) -> None:
        text = content_bytes.decode("utf-8", "ignore")
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line or "=" in line:
                delim = ":" if ":" in line else "="
                key = line.split(delim, 1)[0].strip()
                if key and len(key) > 3 and not key.startswith("-"):
                    cfg_id = f"config://{key}"
                    if cfg_id not in self.nodes:
                        self.nodes[cfg_id] = SymbolNode(
                            id=cfg_id,
                            name=key,
                            node_type=NodeType.CONFIGURATION,
                            file_path=rel_path,
                            metadata={"property": key},
                        )
                        self._add_edge(file_node_id, cfg_id, EdgeType.DEFINES)

    # -----------------------------------------------------------------------
    # PASS 2 Implementation: Call Linking & Type Resolution
    # -----------------------------------------------------------------------

    def _pass2_file(
        self,
        path: Path,
        rel_path: str,
        ast_cache: Dict[str, Any],
    ) -> None:
        cached = ast_cache.get(rel_path)
        if not cached:
            return

        tree, content_bytes, lang = cached
        root = tree.root_node

        if lang == "java":
            self._pass2_java(root, rel_path, content_bytes)
        elif lang == "kotlin":
            self._pass2_kotlin(root, rel_path, content_bytes)
        elif lang == "python":
            self._pass2_python(root, rel_path, content_bytes)

    def _pass2_java(self, root: Any, rel_path: str, content_bytes: bytes) -> None:
        for child in root.children:
            if child.type in ("class_declaration", "interface_declaration", "record_declaration"):
                name_node = child.child_by_field_name("name")
                if not name_node:
                    continue
                class_name = content_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8", "ignore")
                body = child.child_by_field_name("body")
                if not body:
                    continue

                for b_child in body.children:
                    if b_child.type == "method_declaration":
                        m_name_node = b_child.child_by_field_name("name")
                        if not m_name_node:
                            continue
                        m_name = content_bytes[m_name_node.start_byte:m_name_node.end_byte].decode("utf-8", "ignore")
                        caller_method_id = self.class_methods.get(class_name, {}).get(m_name)
                        if not caller_method_id:
                            continue

                        self._resolve_java_invocations(b_child, class_name, caller_method_id, content_bytes)

    def _resolve_java_invocations(
        self,
        method_node: Any,
        caller_class: str,
        caller_method_id: str,
        content_bytes: bytes,
    ) -> None:
        field_map = self.class_fields.get(caller_class, {})
        visited_calls: Set[Tuple[str, str]] = set()

        def _walk(n: Any) -> None:
            if n.type == "method_invocation":
                obj_node = n.child_by_field_name("object")
                name_node = n.child_by_field_name("name")
                if name_node:
                    called_method_name = content_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8", "ignore")
                    obj_text = ""
                    if obj_node:
                        obj_text = content_bytes[obj_node.start_byte:obj_node.end_byte].decode("utf-8", "ignore").strip()
                        if obj_text.startswith("this."):
                            obj_text = obj_text[5:]

                    pair = (obj_text, called_method_name)
                    if pair not in visited_calls:
                        visited_calls.add(pair)
                        self._link_call(caller_class, caller_method_id, obj_text, called_method_name, field_map)

            for child in n.children:
                _walk(child)

        _walk(method_node)

    def _pass2_kotlin(self, root: Any, rel_path: str, content_bytes: bytes) -> None:
        for child in root.children:
            if child.type == "class_declaration":
                class_name = ""
                for n in child.children:
                    if n.type in ("identifier", "simple_identifier"):
                        class_name = content_bytes[n.start_byte:n.end_byte].decode("utf-8", "ignore")
                        break
                if not class_name:
                    continue

                body = None
                for c in child.children:
                    if c.type == "class_body":
                        body = c
                        break
                if not body:
                    continue

                for b_child in body.children:
                    if b_child.type in ("function_declaration", "named_function"):
                        f_name = ""
                        for fn_child in b_child.children:
                            if fn_child.type in ("identifier", "simple_identifier"):
                                f_name = content_bytes[fn_child.start_byte:fn_child.end_byte].decode("utf-8", "ignore")
                                break
                        if not f_name:
                            continue
                        caller_method_id = self.class_methods.get(class_name, {}).get(f_name)
                        if not caller_method_id:
                            continue

                        self._resolve_kotlin_invocations(b_child, class_name, caller_method_id, content_bytes)

    def _resolve_kotlin_invocations(
        self,
        fn_node: Any,
        caller_class: str,
        caller_method_id: str,
        content_bytes: bytes,
    ) -> None:
        field_map = self.class_fields.get(caller_class, {})
        visited_calls: Set[Tuple[str, str]] = set()

        def _walk(n: Any) -> None:
            if n.type == "call_expression":
                first = n.children[0] if n.children else None
                if first and first.type == "navigation_expression":
                    parts = [content_bytes[c.start_byte:c.end_byte].decode("utf-8", "ignore") for c in first.children if c.is_named]
                    if len(parts) >= 2:
                        obj_text = parts[0]
                        called_name = parts[1]
                        pair = (obj_text, called_name)
                        if pair not in visited_calls:
                            visited_calls.add(pair)
                            self._link_call(caller_class, caller_method_id, obj_text, called_name, field_map)
                elif first and first.type in ("identifier", "simple_identifier"):
                    called_name = content_bytes[first.start_byte:first.end_byte].decode("utf-8", "ignore")
                    pair = ("", called_name)
                    if pair not in visited_calls:
                        visited_calls.add(pair)
                        self._link_call(caller_class, caller_method_id, "", called_name, field_map)

            for child in n.children:
                _walk(child)

        _walk(fn_node)

    def _pass2_python(self, root: Any, rel_path: str, content_bytes: bytes) -> None:
        for child in root.children:
            if child.type == "class_definition":
                name_node = child.child_by_field_name("name")
                if not name_node:
                    continue
                class_name = content_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8", "ignore")
                body = child.child_by_field_name("body")
                if not body:
                    continue

                for b_child in body.children:
                    if b_child.type == "function_definition":
                        fn_name_node = b_child.child_by_field_name("name")
                        if not fn_name_node:
                            continue
                        fn_name = content_bytes[fn_name_node.start_byte:fn_name_node.end_byte].decode("utf-8", "ignore")
                        caller_method_id = self.class_methods.get(class_name, {}).get(fn_name)
                        if not caller_method_id:
                            continue

                        self._resolve_python_invocations(b_child, class_name, caller_method_id, content_bytes)

    def _resolve_python_invocations(
        self,
        fn_node: Any,
        caller_class: str,
        caller_method_id: str,
        content_bytes: bytes,
    ) -> None:
        field_map = self.class_fields.get(caller_class, {})
        visited_calls: Set[Tuple[str, str]] = set()

        def _walk(n: Any) -> None:
            if n.type == "call":
                fn = n.child_by_field_name("function")
                if fn and fn.type == "attribute":
                    obj = fn.child_by_field_name("object")
                    attr = fn.child_by_field_name("attribute")
                    obj_text = content_bytes[obj.start_byte:obj.end_byte].decode("utf-8", "ignore").strip() if obj else ""
                    called_name = content_bytes[attr.start_byte:attr.end_byte].decode("utf-8", "ignore") if attr else ""
                    if obj_text.startswith("self."):
                        obj_text = obj_text[5:]
                    pair = (obj_text, called_name)
                    if pair not in visited_calls:
                        visited_calls.add(pair)
                        self._link_call(caller_class, caller_method_id, obj_text, called_name, field_map)
                elif fn and fn.type == "identifier":
                    called_name = content_bytes[fn.start_byte:fn.end_byte].decode("utf-8", "ignore")
                    pair = ("", called_name)
                    if pair not in visited_calls:
                        visited_calls.add(pair)
                        self._link_call(caller_class, caller_method_id, "", called_name, field_map)

            for child in n.children:
                _walk(child)

        _walk(fn_node)

    # -----------------------------------------------------------------------
    # Core Deterministic Two-Pass Linking Algorithm
    # -----------------------------------------------------------------------

    def _link_call(
        self,
        caller_class: str,
        caller_method_id: str,
        receiver_name: str,
        method_name: str,
        field_map: Dict[str, str],
    ) -> None:
        target_class: Optional[str] = None

        if not receiver_name or receiver_name in ("this", "self"):
            target_class = caller_class
        elif receiver_name in field_map:
            target_class = field_map[receiver_name]
        elif receiver_name in self.class_methods or receiver_name in self.class_fqn_map:
            target_class = receiver_name
        else:
            # Check camelCase heuristic (e.g. articleCommandService -> ArticleCommandService)
            words = re.findall(r"[a-zA-Z0-9]+", receiver_name)
            pascal = "".join(w.capitalize() for w in words)
            if pascal in self.class_methods:
                target_class = pascal

        if not target_class:
            return

        # 1. Direct Target Method Resolution
        target_method_id = self.class_methods.get(target_class, {}).get(method_name)
        if target_method_id:
            self._add_edge(caller_method_id, target_method_id, EdgeType.CALLS)
            self._add_edge(target_method_id, caller_method_id, EdgeType.CALLED_BY)

        # 2. Polymorphic Interface Resolution:
        # If target_class is an interface, resolve to all implementing classes' methods!
        implementing_classes = self.interface_to_impls.get(target_class, [])
        for impl_cls in implementing_classes:
            impl_method_id = self.class_methods.get(impl_cls, {}).get(method_name)
            if impl_method_id:
                if target_method_id:
                    self._add_edge(impl_method_id, target_method_id, EdgeType.IMPLEMENTS)
                self._add_edge(caller_method_id, impl_method_id, EdgeType.CALLS, {"polymorphic_via": target_class})
                self._add_edge(impl_method_id, caller_method_id, EdgeType.CALLED_BY, {"polymorphic_via": target_class})
