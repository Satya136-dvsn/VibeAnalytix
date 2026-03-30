"""
Parser module for language detection and AST extraction using tree-sitter.

Supports: Python, JavaScript, TypeScript, Java, Go, C, C++
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
    "cpp": {".cc", ".cpp", ".cxx", ".c++", ".h", ".hpp", ".hxx"},
}

# Supported languages
SUPPORTED_LANGUAGES = {
    "python": "tree_sitter_python",
    "javascript": "tree_sitter_javascript",
    "typescript": "tree_sitter_typescript",
    "java": "tree_sitter_java",
    "go": "tree_sitter_go",
    "c": "tree_sitter_c",
    "cpp": "tree_sitter_cpp",
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


@dataclass
class FileTreeNode:
    """Hierarchical file tree node."""

    name: str
    path: str
    is_dir: bool
    children: list["FileTreeNode"] = field(default_factory=list)


class LanguageDetector:
    """Detects programming language from file extension and content."""

    @staticmethod
    def detect_language(file_path: Path) -> Optional[str]:
        """
        Detect programming language from file.

        Args:
            file_path: Path to source file

        Returns:
            Language name or None if unsupported
        """
        extension = file_path.suffix.lower()

        # Check by extension
        for lang, exts in LANGUAGE_EXTENSIONS.items():
            if extension in exts:
                return lang

        return None


class TreeSitterParser:
    """AST parser using tree-sitter."""

    def __init__(self):
        """Initialize tree-sitter parser with supported languages."""
        self.parsers: dict[str, Parser] = {}
        self.languages: dict[str, Language] = {}

        # Load grammars
        self._load_languages()

    def _load_languages(self) -> None:
        """Load tree-sitter language grammars."""
        try:
            # Python
            Language.build_library(
                "build/languages.so",
                ["tree-sitter-python"],
            )
        except:
            pass  # Grammars may already be loaded

        for lang in SUPPORTED_LANGUAGES.keys():
            try:
                self.languages[lang] = Language(f"build/languages.so", lang)
                parser = Parser()
                parser.set_language(self.languages[lang])
                self.parsers[lang] = parser
            except Exception as e:
                print(f"Warning: Failed to load {lang} grammar: {e}")

    def parse_file(self, file_path: Path) -> Optional[Node]:
        """
        Parse a source file to AST.

        Args:
            file_path: Path to source file

        Returns:
            Root AST node or None if parsing fails
        """
        try:
            with open(file_path, "rb") as f:
                source_code = f.read()

            language = LanguageDetector.detect_language(file_path)
            if not language or language not in self.parsers:
                return None

            parser = self.parsers[language]
            tree = parser.parse(source_code)
            return tree.root_node

        except Exception as e:
            print(f"Warning: Failed to parse {file_path}: {e}")
            return None

    def extract_functions(self, ast: Node, language: str) -> list[FunctionDef]:
        """Extract function definitions from AST."""
        functions = []

        def traverse(node: Node):
            # Language-specific function/method patterns
            if language == "python":
                if node.type == "function_definition":
                    name_node = None
                    for child in node.children:
                        if child.type == "identifier":
                            name_node = child
                            break

                    if name_node:
                        functions.append(
                            FunctionDef(
                                name=name_node.text.decode("utf-8"),
                                line_start=node.start_point[0] + 1,
                                line_end=node.end_point[0] + 1,
                            )
                        )

            elif language in ("javascript", "typescript"):
                if node.type in ("function_declaration", "arrow_function"):
                    # Find identifier
                    for child in node.children:
                        if child.type == "identifier":
                            functions.append(
                                FunctionDef(
                                    name=child.text.decode("utf-8"),
                                    line_start=node.start_point[0] + 1,
                                    line_end=node.end_point[0] + 1,
                                )
                            )
                            break

            elif language == "java":
                if node.type == "method_declaration":
                    for child in node.children:
                        if child.type == "identifier":
                            functions.append(
                                FunctionDef(
                                    name=child.text.decode("utf-8"),
                                    line_start=node.start_point[0] + 1,
                                    line_end=node.end_point[0] + 1,
                                )
                            )
                            break

            elif language == "go":
                if node.type == "function_declaration":
                    for child in node.children:
                        if child.type == "identifier":
                            functions.append(
                                FunctionDef(
                                    name=child.text.decode("utf-8"),
                                    line_start=node.start_point[0] + 1,
                                    line_end=node.end_point[0] + 1,
                                )
                            )
                            break

            # Recurse
            for child in node.children:
                traverse(child)

        traverse(ast)
        return functions

    def extract_classes(self, ast: Node, language: str) -> list[ClassDef]:
        """Extract class definitions from AST."""
        classes = []

        def traverse(node: Node):
            if language == "python":
                if node.type == "class_definition":
                    name_node = None
                    for child in node.children:
                        if child.type == "identifier":
                            name_node = child
                            break

                    if name_node:
                        classes.append(
                            ClassDef(
                                name=name_node.text.decode("utf-8"),
                                line_start=node.start_point[0] + 1,
                                line_end=node.end_point[0] + 1,
                            )
                        )

            elif language in ("javascript", "typescript"):
                if node.type == "class_declaration":
                    for child in node.children:
                        if child.type == "identifier":
                            classes.append(
                                ClassDef(
                                    name=child.text.decode("utf-8"),
                                    line_start=node.start_point[0] + 1,
                                    line_end=node.end_point[0] + 1,
                                )
                            )
                            break

            elif language == "java":
                if node.type == "class_declaration":
                    for child in node.children:
                        if child.type == "identifier":
                            classes.append(
                                ClassDef(
                                    name=child.text.decode("utf-8"),
                                    line_start=node.start_point[0] + 1,
                                    line_end=node.end_point[0] + 1,
                                )
                            )
                            break

            for child in node.children:
                traverse(child)

        traverse(ast)
        return classes

    def extract_imports(self, ast: Node, language: str) -> list[ImportDef]:
        """Extract import statements from AST."""
        imports = []

        def traverse(node: Node):
            if language == "python":
                if node.type == "import_statement":
                    name_node = None
                    for child in node.children:
                        if child.type == "dotted_name":
                            name_node = child
                            break
                    if name_node:
                        imports.append(
                            ImportDef(
                                module=name_node.text.decode("utf-8"),
                                names=[],
                            )
                        )

            elif language in ("javascript", "typescript"):
                if node.type in ("import_statement", "import_clause"):
                    # Simplified extraction
                    for child in node.children:
                        if child.type == "string":
                            imports.append(
                                ImportDef(
                                    module=child.text.decode("utf-8").strip('"\''),
                                    names=[],
                                )
                            )

            for child in node.children:
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
                        continue  # Skip hidden files
                    child_relative = f"{relative_path}/{item.name}"
                    node.children.append(traverse(item, child_relative))
            except PermissionError:
                pass

        return node

    return traverse(root_dir)


async def parse_repository(temp_dir: Path) -> list[ParsedFile]:
    """
    Parse all source files in a repository.

    Args:
        temp_dir: Temporary directory containing extracted/cloned repository

    Returns:
        List of ParsedFile objects for all source files
    """
    parser = TreeSitterParser()
    detector = LanguageDetector()
    parsed_files = []

    for source_file in temp_dir.rglob("*"):
        if not source_file.is_file() or source_file.name.startswith("."):
            continue

        language = detector.detect_language(source_file)
        if not language:
            continue

        try:
            ast = parser.parse_file(source_file)
            if ast:
                relative_path = str(source_file.relative_to(temp_dir))
                parsed_files.append(
                    ParsedFile(
                        path=relative_path,
                        language=language,
                        ast=ast,
                        functions=parser.extract_functions(ast, language),
                        classes=parser.extract_classes(ast, language),
                        imports=parser.extract_imports(ast, language),
                    )
                )
        except Exception as e:
            parsed_files.append(
                ParsedFile(
                    path=str(source_file.relative_to(temp_dir)),
                    language=language,
                    parse_error=str(e),
                )
            )

    return parsed_files


def pretty_print(ast: Node, language: str) -> str:
    """
    Serialize AST back to normalized source code.

    Args:
        ast: Tree-sitter AST node
        language: Programming language

    Returns:
        Pretty-printed source code string
    """
    # For simplicity, return the raw text
    # In production, implement language-specific pretty printing
    if hasattr(ast, "text"):
        return ast.text.decode("utf-8")
    return ""
