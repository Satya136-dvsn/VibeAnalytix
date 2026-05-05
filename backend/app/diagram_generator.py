"""
Diagram Generator — pure heuristic Mermaid diagram builder.

Converts AnalysisResult and ParsedFile data into Mermaid diagram strings.
No LLM or external API needed.

Generates:
 1. dependency  — flowchart of file import dependencies
 2. module      — module/directory hierarchy graph
 3. class       — class & method diagram from AST
 4. flow        — sequence diagram from entry points & cross-file relations
 5. data_models — ER diagram of extracted classes and their inheritances
"""

import re
from pathlib import Path


# ─── helpers ──────────────────────────────────────────────────────────────────

def _safe_id(text: str) -> str:
    """Convert arbitrary string to a safe Mermaid node ID."""
    return re.sub(r"[^A-Za-z0-9_]", "_", text)[:60]


def _short_label(path: str) -> str:
    """Return a short, display-friendly label for a path."""
    parts = path.replace("\\", "/").split("/")
    # Keep last two meaningful segments
    meaningful = [p for p in parts if p and p not in (".", "..")]
    return "/".join(meaningful[-2:]) if len(meaningful) >= 2 else (meaningful[-1] if meaningful else path)


# ─── 1. Dependency Flowchart ─────────────────────────────────────────────────

def generate_dependency_diagram(analysis) -> str:
    """
    Build a flowchart TD showing file-level import dependencies.

    Args:
        analysis: AnalysisResult with dependency_graph dict

    Returns:
        Mermaid flowchart string (truncated to ≤40 nodes for readability)
    """
    dep_graph: dict = getattr(analysis, "dependency_graph", {}) or {}
    if not dep_graph:
        return "flowchart TD\n    A[No dependency data available]"

    lines = ["flowchart TD"]
    node_ids: dict[str, str] = {}
    edges_written: set[tuple[str, str]] = set()

    def get_id(path: str) -> str:
        if path not in node_ids:
            nid = f"N{len(node_ids)}_{_safe_id(_short_label(path))}"
            node_ids[path] = nid
        return node_ids[path]

    # Limit to MAX_NODES to keep diagram readable
    MAX_NODES = 40
    all_files = list(dep_graph.keys())[:MAX_NODES]

    for src in all_files:
        deps = dep_graph.get(src, []) or []
        src_id = get_id(src)
        src_label = _short_label(src)
        lines.append(f'    {src_id}["{src_label}"]')

        for dep in deps[:8]:  # max 8 edges per node
            dep_id = get_id(dep)
            dep_label = _short_label(dep)
            edge = (src_id, dep_id)
            if edge not in edges_written:
                if dep not in node_ids:
                    lines.append(f'    {dep_id}["{dep_label}"]')
                lines.append(f"    {src_id} --> {dep_id}")
                edges_written.add(edge)

    # Mark entry points with a distinct style
    entry_points = getattr(analysis, "entry_points", []) or []
    for ep in entry_points:
        if ep in node_ids:
            lines.append(f"    style {node_ids[ep]} fill:#7c3aed,color:#fff,stroke:#5b21b6")

    if len(lines) == 1:
        lines.append("    A[No inter-file dependencies detected]")

    return "\n".join(lines)


# ─── 2. Module Structure Graph ────────────────────────────────────────────────

def generate_module_structure_diagram(analysis, knowledge) -> str:
    """
    Build a left-to-right hierarchy graph of module/directory structure.

    Args:
        analysis:  AnalysisResult
        knowledge: KnowledgeGraph with module_summaries list

    Returns:
        Mermaid graph LR string
    """
    module_summaries = getattr(knowledge, "module_summaries", []) or []
    file_tree = getattr(analysis, "file_tree", None)

    lines = ["graph LR"]

    if module_summaries:
        # Build from knowledge module summaries
        root_id = "ROOT"
        lines.append(f'    {root_id}(["🗂 Project Root"])')

        seen_mods: set[str] = set()
        for ms in module_summaries[:30]:
            mod_path = getattr(ms, "module_path", "") or ""
            if not mod_path or mod_path in seen_mods:
                continue
            seen_mods.add(mod_path)
            parts = mod_path.replace("\\", "/").split("/")
            label = parts[-1] if parts else mod_path
            mod_id = _safe_id(mod_path)

            parent_parts = parts[:-1]
            if parent_parts:
                parent_id = _safe_id("/".join(parent_parts))
                lines.append(f'    {mod_id}["{label}"]')
                lines.append(f"    {parent_id} --> {mod_id}")
            else:
                lines.append(f'    {mod_id}["{label}"]')
                lines.append(f"    {root_id} --> {mod_id}")

    elif file_tree:
        # Fallback: walk file_tree dataclass recursively
        def _walk(node, parent_id: str, depth: int):
            if depth > 4:
                return
            name = getattr(node, "name", "?")
            is_dir = getattr(node, "is_dir", False)
            node_id = _safe_id(f"d{depth}_{name}")
            icon = "📁" if is_dir else "📄"
            lines.append(f'    {node_id}["{icon} {name}"]')
            if parent_id:
                lines.append(f"    {parent_id} --> {node_id}")
            if is_dir:
                children = getattr(node, "children", []) or []
                for child in children[:12]:
                    _walk(child, node_id, depth + 1)

        _walk(file_tree, "", 0)
    else:
        lines.append('    ROOT["No structure data"]')

    return "\n".join(lines)


# ─── 3. Class Diagram ─────────────────────────────────────────────────────────

def generate_class_diagram(parsed_files) -> str:
    """
    Build a Mermaid classDiagram from AST-extracted class/method data.

    Args:
        parsed_files: list[ParsedFile] from parser

    Returns:
        Mermaid classDiagram string
    """
    lines = ["classDiagram"]
    classes_added = 0

    for pf in parsed_files:
        if classes_added >= 25:
            break
        classes = getattr(pf, "classes", []) or []
        for cls in classes:
            if classes_added >= 25:
                break
            cls_name = getattr(cls, "name", "Unknown")
            safe_name = _safe_id(cls_name)
            lines.append(f"    class {safe_name} {{")

            # Methods from class
            methods = getattr(cls, "methods", []) or []
            for method in methods[:8]:
                m_name = getattr(method, "name", "")
                params = getattr(method, "parameters", []) or []
                param_str = ", ".join(params[:4])
                if m_name:
                    lines.append(f"        +{m_name}({param_str})")
            lines.append("    }")
            classes_added += 1

        # Also add standalone functions as a «module» classifier
        functions = getattr(pf, "functions", []) or []
        if functions and not classes and classes_added < 25:
            file_name = Path(getattr(pf, "path", "file")).stem
            safe_fn = _safe_id(file_name)
            lines.append(f"    class {safe_fn} {{")
            lines.append(f"        <<module>>")
            for fn in functions[:6]:
                fn_name = getattr(fn, "name", "")
                if fn_name and not fn_name.startswith("_"):
                    params = getattr(fn, "parameters", []) or []
                    param_str = ", ".join(params[:3])
                    lines.append(f"        +{fn_name}({param_str})")
            lines.append("    }")
            classes_added += 1

    if classes_added == 0:
        lines.append("    class NoClasses {")
        lines.append("        <<No class definitions found>>")
        lines.append("    }")

    return "\n".join(lines)


# ─── 4. Execution Flow Sequence Diagram ───────────────────────────────────────

def generate_execution_flow_diagram(analysis) -> str:
    """
    Build a sequenceDiagram from entry points and cross-file relations.

    Args:
        analysis: AnalysisResult

    Returns:
        Mermaid sequenceDiagram string
    """
    entry_points = getattr(analysis, "entry_points", []) or []
    relations = getattr(analysis, "cross_file_relations", []) or []

    lines = ["sequenceDiagram"]
    lines.append("    autonumber")

    if not entry_points and not relations:
        lines.append("    participant System")
        lines.append("    Note over System: No entry points detected")
        return "\n".join(lines)

    # Collect unique participants from entry points + relations
    participants: list[str] = []
    seen: set[str] = set()

    for ep in entry_points[:5]:
        label = _short_label(ep)
        if label not in seen:
            participants.append(label)
            seen.add(label)

    for rel in relations[:20]:
        from_file = _short_label(getattr(rel, "from_file", "") or "")
        to_file = _short_label(getattr(rel, "to_file", "") or "")
        for f in (from_file, to_file):
            if f and f not in seen and len(participants) < 8:
                participants.append(f)
                seen.add(f)

    # Declare participants
    for p in participants:
        pid = _safe_id(p)
        lines.append(f"    participant {pid} as {p}")

    # Draw entry call from "User" to first entry point
    if participants:
        first_ep = _safe_id(participants[0])
        lines.append(f"    User->>+{first_ep}: invoke()")

    # Draw cross-file relations as messages
    written = 0
    for rel in relations[:15]:
        from_file = _short_label(getattr(rel, "from_file", "") or "")
        to_file = _short_label(getattr(rel, "to_file", "") or "")
        from_entity = getattr(rel, "from_entity", "") or ""
        to_entity = getattr(rel, "to_entity", "") or ""
        rel_type = getattr(rel, "relation_type", "calls") or "calls"

        if from_file in seen and to_file in seen and from_file != to_file:
            fid = _safe_id(from_file)
            tid = _safe_id(to_file)
            msg = f"{from_entity}.{rel_type}()" if from_entity else f"{rel_type}()"
            lines.append(f"    {fid}->>{tid}: {msg[:40]}")
            written += 1

    if written == 0 and participants:
        lines.append(f"    Note over {_safe_id(participants[0])}: Single-module project")

    return "\n".join(lines)


# ─── 5. Data Models ER Diagram ────────────────────────────────────────────────

def generate_data_models_diagram(parsed_files) -> str:
    """
    Build a Mermaid erDiagram from AST-extracted class data.
    Shows inheritance relationships based on parent_class.

    Args:
        parsed_files: list[ParsedFile] from parser

    Returns:
        Mermaid erDiagram string
    """
    lines = ["erDiagram"]
    classes_added = 0
    relationships = []

    for pf in parsed_files:
        if classes_added >= 40:
            break
        classes = getattr(pf, "classes", []) or []
        for cls in classes:
            if classes_added >= 40:
                break
            cls_name = getattr(cls, "name", "Unknown")
            safe_name = _safe_id(cls_name)
            
            lines.append(f"    {safe_name} {{")
            lines.append("    }")
            
            parent = getattr(cls, "parent_class", None)
            if parent:
                safe_parent = _safe_id(parent)
                relationships.append(f"    {safe_parent} ||--o{{ {safe_name} : inherits")
                
            classes_added += 1

    if classes_added == 0:
        lines.append("    NoDataModels {")
        lines.append("    }")

    if relationships:
        lines.extend(relationships)

    return "\n".join(lines)


# ─── 6. Master generator ──────────────────────────────────────────────────────

def generate_all_diagrams(parsed_files, analysis, knowledge) -> dict[str, str]:
    """
    Generate all five Mermaid diagrams from analysis data.

    Args:
        parsed_files: list[ParsedFile]
        analysis:     AnalysisResult
        knowledge:    KnowledgeGraph

    Returns:
        dict with keys: dependency, module, class_diagram, flow, data_models
    """
    diagrams: dict[str, str] = {}

    try:
        diagrams["dependency"] = generate_dependency_diagram(analysis)
    except Exception as e:
        diagrams["dependency"] = f"flowchart TD\n    ERR[\"Error: {str(e)[:80]}\"]"

    try:
        diagrams["module"] = generate_module_structure_diagram(analysis, knowledge)
    except Exception as e:
        diagrams["module"] = f"graph LR\n    ERR[\"Error: {str(e)[:80]}\"]"

    try:
        diagrams["class_diagram"] = generate_class_diagram(parsed_files)
    except Exception as e:
        diagrams["class_diagram"] = f"classDiagram\n    class Error\n    Error : +{str(e)[:60]}"

    try:
        diagrams["flow"] = generate_execution_flow_diagram(analysis)
    except Exception as e:
        diagrams["flow"] = f"sequenceDiagram\n    Note over System: Error: {str(e)[:60]}"

    try:
        diagrams["data_models"] = generate_data_models_diagram(parsed_files)
    except Exception as e:
        diagrams["data_models"] = f'erDiagram\n    Error {{\n        string message "{str(e)[:60]}"\n    }}'

    return diagrams
