"""
Analysis Engine implementing 3-pass analysis pipeline.

Pass 1: Structural Mapping - build file/directory tree and identify entry points
Pass 2: Dependency Detection - build dependency graph and detect cycles
Pass 3: Context Refinement - resolve cross-file semantic relationships
"""

from dataclasses import dataclass, field
from pathlib import Path

from app.parser import ClassDef, FileTreeNode, FunctionDef, ParsedFile


@dataclass
class CrossFileRelation:
    """Cross-file relationship between functions/classes."""

    from_file: str
    from_entity: str
    to_file: str
    to_entity: str
    relation_type: str  # "calls", "imports", "extends"


@dataclass
class AnalysisResult:
    """Result of 3-pass analysis."""

    file_tree: FileTreeNode
    entry_points: list[str] = field(default_factory=list)
    dependency_graph: dict[str, list[str]] = field(default_factory=dict)
    circular_deps: list[list[str]] = field(default_factory=list)
    external_deps: list[str] = field(default_factory=list)
    cross_file_relations: list[CrossFileRelation] = field(default_factory=list)


class AnalysisEngine:
    """3-pass analysis engine for repository understanding."""

    # Entry point filenames by language
    ENTRY_POINTS_BY_LANGUAGE = {
        "python": ["main.py", "__main__.py", "app.py", "server.py", "run.py"],
        "javascript": [
            "index.js",
            "main.js",
            "app.js",
            "server.js",
            "index.jsx",
        ],
        "typescript": [
            "index.ts",
            "main.ts",
            "app.ts",
            "server.ts",
            "index.tsx",
        ],
        "java": ["Main.java", "Application.java"],
        "go": ["main.go"],
        "c": ["main.c"],
        "cpp": ["main.cpp", "main.cc"],
    }

    def __init__(self):
        """Initialize analysis engine."""
        self.parsed_files: list[ParsedFile] = []
        self.file_map: dict[str, ParsedFile] = {}
        self.dependency_graph: dict[str, set[str]] = {}
        self.circular_deps: list[list[str]] = []
        self.external_deps: set[str] = set()

    def _pass_1_structural_mapping(
        self, parsed_files: list[ParsedFile], temp_dir: Path
    ) -> tuple[FileTreeNode, list[str]]:
        """
        Pass 1: Structural Mapping

        - Build hierarchical file/directory tree
        - Identify entry point files by language convention
        """
        from app.parser import build_file_tree

        # Build file tree
        file_tree = build_file_tree(temp_dir)

        # Identify entry points
        entry_points = []
        for parsed_file in parsed_files:
            file_name = Path(parsed_file.path).name
            if parsed_file.language:
                candidates = self.ENTRY_POINTS_BY_LANGUAGE.get(parsed_file.language, [])
                if file_name in candidates:
                    entry_points.append(parsed_file.path)

        return file_tree, entry_points

    def _pass_2_dependency_detection(
        self, parsed_files: list[ParsedFile]
    ) -> tuple[dict[str, list[str]], list[list[str]], list[str]]:
        """
        Pass 2: Dependency Detection

        - Build directed dependency graph from import/require statements
        - Detect circular dependencies using DFS
        - Catalog external library dependencies
        """

        # Initialize dependency graph
        dep_graph: dict[str, set[str]] = {pf.path: set() for pf in parsed_files}
        external_deps: set[str] = set()

        # Extract dependencies from imports
        for parsed_file in parsed_files:
            for import_def in parsed_file.imports:
                module = import_def.module

                # Check if it's an internal module
                is_internal = False
                for other_file in parsed_files:
                    # Simple heuristic: if module name matches file path
                    if module in other_file.path or module.replace(".", "/") in other_file.path:
                        if parsed_file.path != other_file.path:
                            dep_graph[parsed_file.path].add(other_file.path)
                        is_internal = True
                        break

                # If not internal, it's external
                if not is_internal and import_def.is_external:
                    external_deps.add(module)

        # Convert sets to lists for the result
        dep_graph_lists = {k: list(v) for k, v in dep_graph.items()}

        # Detect circular dependencies using DFS
        circular_cycles = self._detect_circular_dependencies(dep_graph_lists)

        return dep_graph_lists, circular_cycles, sorted(list(external_deps))

    def _detect_circular_dependencies(
        self, dep_graph: dict[str, list[str]]
    ) -> list[list[str]]:
        """
        Detect circular dependencies using DFS.

        Args:
            dep_graph: Dependency graph

        Returns:
            List of cycles (each cycle is a list of file paths)
        """
        cycles = []
        visited = set()
        rec_stack = set()
        path_stack = []

        def dfs(node: str):
            visited.add(node)
            rec_stack.add(node)
            path_stack.append(node)

            for neighbor in dep_graph.get(node, []):
                if neighbor not in visited:
                    dfs(neighbor)
                elif neighbor in rec_stack:
                    # Found a cycle
                    cycle_start = path_stack.index(neighbor)
                    cycle = path_stack[cycle_start:] + [neighbor]
                    cycles.append(cycle)

            path_stack.pop()
            rec_stack.remove(node)

        for node in dep_graph:
            if node not in visited:
                dfs(node)

        return cycles

    def _pass_3_context_refinement(
        self, parsed_files: list[ParsedFile], dep_graph: dict[str, list[str]]
    ) -> list[CrossFileRelation]:
        """
        Pass 3: Context Refinement

        - Resolve cross-file semantic relationships
        - Annotate functions with their callers/callees across files
        - Enrich dependency graph with semantic edges (imports, calls, inheritance)
        
        Returns:
            List of CrossFileRelation objects describing all semantic links
        """
        relations = []

        # Build a map of function names to files (for caller/callee resolution)
        function_map: dict[str, list[tuple[str, "FunctionDef"]]] = {}
        for parsed_file in parsed_files:
            for func in parsed_file.functions:
                if func.name not in function_map:
                    function_map[func.name] = []
                function_map[func.name].append((parsed_file.path, func))

        # Build a map of class names to files (for inheritance resolution)
        class_map: dict[str, list[tuple[str, "ClassDef"]]] = {}
        for parsed_file in parsed_files:
            for cls in parsed_file.classes:
                if cls.name not in class_map:
                    class_map[cls.name] = []
                class_map[cls.name].append((parsed_file.path, cls))

        # 1. Process imports - direct file dependencies
        for parsed_file in parsed_files:
            for import_def in parsed_file.imports:
                # Find matching files in dependency graph
                for dep_file_path in dep_graph:
                    # Check if this import references this file
                    if import_def.module in dep_file_path or dep_file_path.endswith(import_def.module.replace(".", "/")):
                        relations.append(
                            CrossFileRelation(
                                from_file=parsed_file.path,
                                from_entity=import_def.module,
                                to_file=dep_file_path,
                                to_entity=import_def.module,
                                relation_type="imports",
                            )
                        )

        # 2. Process function calls across files (caller/callee relationships)
        # This requires analyzing the AST for function calls
        for parsed_file in parsed_files:
            # Extract all function calls from this file by analyzing AST
            if parsed_file.ast:
                try:
                    called_functions = self._extract_function_calls(parsed_file.ast, parsed_file.language)
                    
                    # For each called function, find where it's defined
                    for called_func_name in called_functions:
                        # Check if this function is defined in another file
                        if called_func_name in function_map:
                            for target_file_path, target_func in function_map[called_func_name]:
                                if target_file_path != parsed_file.path:  # Cross-file call
                                    relations.append(
                                        CrossFileRelation(
                                            from_file=parsed_file.path,
                                            from_entity=called_func_name,
                                            to_file=target_file_path,
                                            to_entity=called_func_name,
                                            relation_type="calls",
                                        )
                                    )
                except Exception:
                    # Silently continue if AST analysis fails
                    pass

        # 3. Process class inheritance across files
        for parsed_file in parsed_files:
            for cls in parsed_file.classes:
                if cls.parent_class:
                    # Find where parent class is defined
                    if cls.parent_class in class_map:
                        for parent_file_path, parent_cls in class_map[cls.parent_class]:
                            if parent_file_path != parsed_file.path:  # Cross-file inheritance
                                relations.append(
                                    CrossFileRelation(
                                        from_file=parsed_file.path,
                                        from_entity=cls.name,
                                        to_file=parent_file_path,
                                        to_entity=cls.parent_class,
                                        relation_type="inherits",
                                    )
                                )

        return relations
    
    def _extract_function_calls(self, ast_node, language: str) -> set[str]:
        """
        Extract all function calls from an AST node.
        
        Args:
            ast_node: Tree-sitter AST node
            language: Programming language
            
        Returns:
            Set of called function names
        """
        called_functions = set()
        
        def extract_calls_recursive(node):
            """Recursively extract function calls."""
            # Language-specific node types for function calls
            call_node_types = {
                "python": ["call"],
                "javascript": ["call_expression"],
                "typescript": ["call_expression"],
                "java": ["method_invocation"],
                "go": ["call_expression"],
                "c": ["call_expression"],
                "cpp": ["call_expression"],
            }
            
            node_type = node.type
            
            # Check if this is a call node
            if node_type in call_node_types.get(language, []):
                # Extract function name (typically the first child or special handling)
                try:
                    if language == "python":
                        # In Python, call node has 'function' child
                        for child in node.children:
                            if child.type == "identifier" or child.type == "attribute":
                                func_name = child.text
                                if isinstance(func_name, bytes):
                                    func_name = func_name.decode("utf-8")
                                called_functions.add(func_name)
                    elif language in ["javascript", "typescript"]:
                        # JS/TS: first child is usually the function expression
                        if node.children:
                            func_expr = node.children[0]
                            func_name = func_expr.text
                            if isinstance(func_name, bytes):
                                func_name = func_name.decode("utf-8")
                            # Clean up method calls (e.g., "obj.method" -> extract "method")
                            if "." in func_name:
                                func_name = func_name.split(".")[-1]
                            called_functions.add(func_name)
                    elif language == "java":
                        # Java: method_invocation has specific structure
                        for child in node.children:
                            if child.type == "identifier":
                                func_name = child.text
                                if isinstance(func_name, bytes):
                                    func_name = func_name.decode("utf-8")
                                called_functions.add(func_name)
                except Exception:
                    pass
            
            # Recursively process children
            for child in node.children:
                extract_calls_recursive(child)
        
        extract_calls_recursive(ast_node)
        return called_functions

    def run(self, parsed_files: list[ParsedFile], temp_dir: Path) -> AnalysisResult:
        """
        Run complete 3-pass analysis.

        Args:
            parsed_files: List of parsed files from parser
            temp_dir: Temporary directory path

        Returns:
            Complete AnalysisResult with all analysis data
        """
        self.parsed_files = parsed_files
        self.file_map = {pf.path: pf for pf in parsed_files}

        # Pass 1: Structural Mapping
        file_tree, entry_points = self._pass_1_structural_mapping(parsed_files, temp_dir)

        # Pass 2: Dependency Detection
        dep_graph, circular_deps, external_deps = self._pass_2_dependency_detection(parsed_files)

        # Pass 3: Context Refinement
        cross_file_relations = self._pass_3_context_refinement(parsed_files, dep_graph)

        return AnalysisResult(
            file_tree=file_tree,
            entry_points=entry_points,
            dependency_graph=dep_graph,
            circular_deps=circular_deps,
            external_deps=external_deps,
            cross_file_relations=cross_file_relations,
        )


async def run_analysis(
    parsed_files: list[ParsedFile], temp_dir: Path
) -> AnalysisResult:
    """
    Run complete 3-pass analysis on parsed files.

    Args:
        parsed_files: List of parsed files
        temp_dir: Temporary directory path

    Returns:
        Complete analysis result
    """
    engine = AnalysisEngine()
    return engine.run(parsed_files, temp_dir)
