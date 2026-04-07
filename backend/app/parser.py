"""
Parser module for language detection and AST extraction using tree-sitter.

Supports: Python, JavaScript, TypeScript, Java, Go, C, C++

Uses tree-sitter >= 0.23.0 new API (Language objects from language packages directly).
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import tree_sitter
from tree_sitter import Language, Node, Parser


# Language extension mapping
LANGUAGE_EXTENSIONS = {
    "python": {".py", ".pyw"},
    "javascript": {".js", ".jsx", ".mjs"},
    "typescript": {".ts", ".tsx"},
    "java": {".java"},
    "go": {".go"},
    "c": {".c", ".h"},
    "cpp": {".cc", ".cpp", ".cxx", ".c++", ".hpp", ".hxx"},
}


@dataclass
class FunctionDef:
    """Function definition from AST."""

    name: str
    line_start: int
    line_end: int
    parameters: list[str] = field(default_factory=list)
    docstring: Optional[str] = None


@dataclass
class ClassDef:
    """Class definition from AST."""

    name: str
    line_start: int
    line_end: int
    methods: list[FunctionDef] = field(default_factory=list)
    parent_class: Optional[str] = None
    interfaces: list[str] = field(default_factory=list)


@dataclass
class ImportDef:
    """Import statement from AST."""

    module: str
    names: list[str] = field(default_factory=list)
    is_external: bool = True


@dataclass
class VarDef:
    """Top-level variable definition from AST."""

    name: str
    line_start: int
    line_end: int


@dataclass
class ParsedFile:
    """Result of parsing a single source file."""

    path: str
    language: Optional[str] = None
    ast: Optional[Node] = None
    functions: list[FunctionDef] = field(default_factory=list)
    classes: list[ClassDef] = field(default_factory=list)
    imports: list[ImportDef] = field(default_factory=list)
    top_level_vars: list[VarDef] = field(default_factory=list)
    parse_error: Optional[str] = None
    source: Optional[str] = None  # store raw source for fallback analysis


@dataclass
class FileTreeNode:
    """Hierarchical file tree node."""

    name: str
    path: str
    is_dir: bool
    children: list["FileTreeNode"] = field(default_factory=list)


class LanguageDetector:
    """Detects programming language from file extension."""

    @staticmethod
    def detect_language(file_path: Path) -> Optional[str]:
        extension = file_path.suffix.lower()
        for lang, exts in LANGUAGE_EXTENSIONS.items():
            if extension in exts:
                return lang
        return None


def _load_language(lang_name: str) -> Optional[Language]:
    """
    Load a tree-sitter Language using the new >= 0.23 API.
    Each language package exposes its Language object directly.
    """
    try:
        if lang_name == "python":
            import tree_sitter_python as tsp
            return Language(tsp.language())
        elif lang_name == "javascript":
            import tree_sitter_javascript as tsjs
            return Language(tsjs.language())
        elif lang_name == "typescript":
            import tree_sitter_typescript as tsts
            # typescript package provides .language_typescript() and .language_tsx()
            return Language(tsts.language_typescript())
        elif lang_name == "java":
            import tree_sitter_java as tsjava
            return Language(tsjava.language())
        elif lang_name == "go":
            import tree_sitter_go as tsgo
            return Language(tsgo.language())
        elif lang_name == "c":
            import tree_sitter_c as tsc
            return Language(tsc.language())
        elif lang_name == "cpp":
            import tree_sitter_cpp as tscpp
            return Language(tscpp.language())
    except Exception as e:
        print(f"Warning: Could not load tree-sitter grammar for {lang_name}: {e}")
    return None


class TreeSitterParser:
    """AST parser using tree-sitter >= 0.23."""

    def __init__(self):
        self.parsers: dict[str, Parser] = {}
        self.languages: dict[str, Language] = {}
        self._load_all_languages()

    def _load_all_languages(self) -> None:
        """Load all supported language grammars."""
        for lang in LANGUAGE_EXTENSIONS.keys():
            language = _load_language(lang)
            if language:
                try:
                    parser = Parser(language)
                    self.languages[lang] = language
                    self.parsers[lang] = parser
                    print(f"[parser] Loaded grammar: {lang}")
                except Exception as e:
                    print(f"Warning: Failed to create parser for {lang}: {e}")

    def parse_source(self, source_code: bytes, language: str) -> Optional[Node]:
        """Parse source bytes to AST root node."""
        if language not in self.parsers:
            return None
        try:
            tree = self.parsers[language].parse(source_code)
            return tree.root_node
        except Exception as e:
            print(f"Warning: Parse error for {language}: {e}")
            return None

    def parse_file(self, file_path: Path) -> tuple[Optional[Node], Optional[str], Optional[str]]:
        """
        Parse a source file.
        Returns (ast_node, language, source_code_str)
        """
        try:
            with open(file_path, "rb") as f:
                source_bytes = f.read()

            language = LanguageDetector.detect_language(file_path)
            if not language:
                return None, None, None

            source_str = source_bytes.decode("utf-8", errors="replace")

            if language not in self.parsers:
                # Return file without AST but with source for text-based analysis
                return None, language, source_str

            tree = self.parsers[language].parse(source_bytes)
            return tree.root_node, language, source_str

        except Exception as e:
            print(f"Warning: Failed to parse {file_path}: {e}")
            return None, None, None

    def extract_functions(self, ast: Node, language: str) -> list[FunctionDef]:
        """Extract function definitions from AST."""
        functions = []

        if isinstance(ast, tuple):
            ast = ast[0] if ast else None
        if not ast:
            return functions

        FUNC_NODE_TYPES = {
            "python": ("function_definition", "async_function_definition"),
            "javascript": ("function_declaration", "function_expression", "arrow_function", "method_definition"),
            "typescript": ("function_declaration", "function_expression", "arrow_function", "method_definition"),
            "java": ("method_declaration", "constructor_declaration"),
            "go": ("function_declaration", "method_declaration"),
            "c": ("function_definition",),
            "cpp": ("function_definition",),
        }

        func_types = FUNC_NODE_TYPES.get(language, ())

        def traverse(node: Node):
            if not node or not hasattr(node, "type"):
                return
            children = getattr(node, "children", []) or []

            if node.type in func_types:
                # Find identifier/name node
                name = None
                for child in children:
                    if child.type in ("identifier", "property_identifier", "field_identifier"):
                        try:
                            name = child.text.decode("utf-8")
                        except Exception:
                            name = str(child.text)
                        break

                if name:
                    functions.append(FunctionDef(
                        name=name,
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                    ))

            for child in children:
                traverse(child)

        traverse(ast)
        return functions

    def extract_classes(self, ast: Node, language: str) -> list[ClassDef]:
        """Extract class definitions from AST."""
        classes = []

        if isinstance(ast, tuple):
            ast = ast[0] if ast else None
        if not ast:
            return classes

        CLASS_NODE_TYPES = {
            "python": ("class_definition",),
            "javascript": ("class_declaration", "class_expression"),
            "typescript": ("class_declaration", "class_expression"),
            "java": ("class_declaration", "interface_declaration"),
            "go": ("type_declaration",),
            "c": ("struct_specifier", "union_specifier"),
            "cpp": ("class_specifier", "struct_specifier"),
        }

        class_types = CLASS_NODE_TYPES.get(language, ())

        def traverse(node: Node):
            if not node or not hasattr(node, "type"):
                return
            children = getattr(node, "children", []) or []

            if node.type in class_types:
                name = None
                for child in children:
                    if child.type in ("identifier", "type_identifier"):
                        try:
                            name = child.text.decode("utf-8")
                        except Exception:
                            name = str(child.text)
                        break

                if name:
                    classes.append(ClassDef(
                        name=name,
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                    ))

            for child in children:
                traverse(child)

        traverse(ast)
        return classes

    def extract_imports(self, ast: Node, language: str) -> list[ImportDef]:
        """Extract import statements from AST."""
        imports = []

        if isinstance(ast, tuple):
            ast = ast[0] if ast else None
        if not ast:
            return imports

        def traverse(node: Node):
            if not node or not hasattr(node, "type"):
                return
            children = getattr(node, "children", []) or []

            if language == "python":
                if node.type in ("import_statement", "import_from_statement"):
                    module = ""
                    for child in children:
                        if child.type in ("dotted_name", "relative_import"):
                            try:
                                module = child.text.decode("utf-8")
                            except Exception:
                                module = str(child.text)
                            break
                    if module:
                        imports.append(ImportDef(module=module))

            elif language in ("javascript", "typescript"):
                if node.type == "import_statement":
                    for child in children:
                        if child.type == "string":
                            try:
                                val = child.text.decode("utf-8").strip("'\"")
                            except Exception:
                                val = str(child.text).strip("'\"")
                            imports.append(ImportDef(module=val))
                            break

            elif language == "java":
                if node.type == "import_declaration":
                    for child in children:
                        if child.type == "scoped_identifier":
                            try:
                                imports.append(ImportDef(module=child.text.decode("utf-8")))
                            except Exception:
                                pass
                            break

            elif language == "go":
                if node.type == "import_spec":
                    for child in children:
                        if child.type == "interpreted_string_literal":
                            try:
                                val = child.text.decode("utf-8").strip('"')
                            except Exception:
                                val = str(child.text).strip('"')
                            imports.append(ImportDef(module=val))
                            break

            for child in children:
                traverse(child)

        traverse(ast)
        return imports


def build_file_tree(root_dir: Path) -> FileTreeNode:
    """Build hierarchical file tree from directory structure."""

    def traverse(path: Path, relative_path: str = ".") -> FileTreeNode:
        node = FileTreeNode(
            name=path.name or root_dir.name,
            path=str(relative_path),
            is_dir=path.is_dir(),
        )

        if path.is_dir():
            try:
                for item in sorted(path.iterdir()):
                    if item.name.startswith("."):
                        continue
                    child_relative = f"{relative_path}/{item.name}"
                    node.children.append(traverse(item, child_relative))
            except PermissionError:
                pass

        return node

    return traverse(root_dir)


# Files/dirs to skip during parsing
SKIP_DIRS = {
    "node_modules", "__pycache__", ".git", ".svn", ".hg",
    "vendor", "dist", "build", ".next", "target", "out",
    ".venv", "venv", "env", ".env", "coverage", ".coverage",
    "htmlcov", ".tox", ".mypy_cache", ".pytest_cache",
}

SKIP_EXTENSIONS = {
    ".min.js", ".min.css", ".map", ".lock", ".sum",
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
    ".woff", ".woff2", ".ttf", ".eot",
    ".pdf", ".zip", ".tar", ".gz",
}


async def parse_repository(temp_dir: Path) -> list[ParsedFile]:
    """
    Parse all source files in a repository.

    Args:
        temp_dir: Temporary directory containing extracted/cloned repository

    Returns:
        List of ParsedFile objects for all source files found.
        Files that can't be AST-parsed are still included with source_code
        so the analysis engine can do text-based processing.
    """
    parser = TreeSitterParser()
    detector = LanguageDetector()
    parsed_files: list[ParsedFile] = []

    for source_file in temp_dir.rglob("*"):
        if not source_file.is_file():
            continue

        # Skip hidden files
        if source_file.name.startswith("."):
            continue

        # Skip unwanted directories
        parts = source_file.relative_to(temp_dir).parts
        if any(part in SKIP_DIRS for part in parts):
            continue

        # Skip unwanted file types
        suffix = source_file.suffix.lower()
        if suffix in SKIP_EXTENSIONS:
            continue
        if source_file.name.endswith((".min.js", ".min.css")):
            continue

        # Only parse files with known language extensions
        language = detector.detect_language(source_file)
        if not language:
            continue

        try:
            # Skip very large files (> 1MB) for performance
            if source_file.stat().st_size > 1_000_000:
                print(f"[parser] Skipping large file: {source_file.name}")
                continue

            ast, detected_lang, source_str = parser.parse_file(source_file)
            relative_path = str(source_file.relative_to(temp_dir))

            if ast and detected_lang:
                parsed_files.append(ParsedFile(
                    path=relative_path,
                    language=detected_lang,
                    ast=ast,
                    source=source_str,
                    functions=parser.extract_functions(ast, detected_lang),
                    classes=parser.extract_classes(ast, detected_lang),
                    imports=parser.extract_imports(ast, detected_lang),
                ))
            elif source_str and detected_lang:
                # Grammar not loaded but still include file for text-based analysis
                parsed_files.append(ParsedFile(
                    path=relative_path,
                    language=detected_lang,
                    ast=None,
                    source=source_str,
                ))

        except Exception as e:
            relative_path = str(source_file.relative_to(temp_dir))
            parsed_files.append(ParsedFile(
                path=relative_path,
                language=language,
                parse_error=str(e),
            ))

    print(f"[parser] Found {len(parsed_files)} source files in {temp_dir}")
    return parsed_files


def pretty_print(ast: Node, language: str) -> str:
    """Serialize AST back to normalized source code."""
    if isinstance(ast, tuple):
        ast = ast[0] if ast else None

    def reconstruct_ast(node: Node, indent: int = 0) -> str:
        if not node:
            return ""
        children = getattr(node, "children", []) or []
        if not children:
            text = node.text
            if isinstance(text, bytes):
                text = text.decode("utf-8")
            return text
        parts = [reconstruct_ast(child) for child in children if child]
        result = "".join(parts)
        lines = [line.rstrip() for line in result.split("\n")]
        return "\n".join(lines).strip()

    reconstructed = reconstruct_ast(ast)
    import re
    return re.sub(r"\n\n\n+", "\n\n", reconstructed)
