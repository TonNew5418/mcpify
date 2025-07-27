import re
from pathlib import Path
from typing import List, Optional

import tree_sitter_python as tspython
from tree_sitter import Language, Node, Parser

from ...models.function import FunctionInfo, Parameter


class PythonParser:
    """Parse Python files using tree-sitter to extract function information."""

    def __init__(self):
        self.language = Language(tspython.language())
        self.parser = Parser(self.language)

    def parse_file(self, file_path: Path) -> List[FunctionInfo]:
        """Parse a Python file and extract all function definitions."""
        try:
            with open(file_path, encoding="utf-8") as f:
                source_code = f.read()

            tree = self.parser.parse(bytes(source_code, "utf8"))
            functions = []

            # Find all function definitions
            for node in self._find_nodes_by_type(tree.root_node, "function_definition"):
                func_info = self._extract_function_info(node, file_path, source_code)
                if func_info:
                    functions.append(func_info)

            # Find methods in classes
            for class_node in self._find_nodes_by_type(
                tree.root_node, "class_definition"
            ):
                class_name = self._get_node_text(
                    class_node.child_by_field_name("name"), source_code
                )
                for method_node in self._find_nodes_by_type(
                    class_node, "function_definition"
                ):
                    func_info = self._extract_function_info(
                        method_node,
                        file_path,
                        source_code,
                        class_name=class_name,
                        is_method=True,
                    )
                    if func_info:
                        functions.append(func_info)

            return functions

        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return []

    def _find_nodes_by_type(self, node: Node, node_type: str) -> List[Node]:
        """Recursively find all nodes of a specific type."""
        nodes = []
        if node.type == node_type:
            nodes.append(node)

        for child in node.children:
            nodes.extend(self._find_nodes_by_type(child, node_type))

        return nodes

    def _extract_function_info(
        self,
        node: Node,
        file_path: Path,
        source_code: str,
        class_name: Optional[str] = None,
        is_method: bool = False,
    ) -> Optional[FunctionInfo]:
        """Extract function information from a function definition node."""
        try:
            # Get function name
            name_node = node.child_by_field_name("name")
            if not name_node:
                return None

            function_name = self._get_node_text(name_node, source_code)

            # Skip private methods/functions for now (can be configured later)
            if function_name.startswith("_") and not function_name.startswith("__"):
                return None

            # Get line number
            line_number = node.start_point[0] + 1

            # Extract parameters
            parameters = self._extract_parameters(node, source_code)

            # Extract return type annotation
            return_type = self._extract_return_type(node, source_code)

            # Extract docstring
            docstring = self._extract_docstring(node, source_code)

            # Check if async
            is_async = any(child.type == "async" for child in node.children)

            # Extract decorators
            decorators = self._extract_decorators(node, source_code)

            return FunctionInfo(
                name=function_name,
                file_path=file_path,
                line_number=line_number,
                parameters=parameters,
                return_type=return_type,
                docstring=docstring,
                is_async=is_async,
                is_method=is_method,
                class_name=class_name,
                decorators=decorators,
            )

        except Exception as e:
            print(f"Error extracting function info: {e}")
            return None

    def _extract_parameters(self, func_node: Node, source_code: str) -> List[Parameter]:
        """Extract function parameters."""
        parameters = []

        params_node = func_node.child_by_field_name("parameters")
        if not params_node:
            return parameters

        for child in params_node.children:
            if child.type == "identifier":
                # Simple parameter
                param_name = self._get_node_text(child, source_code)
                parameters.append(Parameter(name=param_name))

            elif child.type == "typed_parameter":
                # Parameter with type annotation
                param_name = self._get_node_text(child.children[0], source_code)
                type_annotation = (
                    self._get_node_text(child.children[2], source_code)
                    if len(child.children) > 2
                    else None
                )
                parameters.append(
                    Parameter(name=param_name, type_annotation=type_annotation)
                )

            elif child.type == "default_parameter":
                # Parameter with default value
                param_name = self._get_node_text(child.children[0], source_code)
                default_value = (
                    self._get_node_text(child.children[2], source_code)
                    if len(child.children) > 2
                    else None
                )
                parameters.append(
                    Parameter(
                        name=param_name, default_value=default_value, is_required=False
                    )
                )

            elif child.type == "typed_default_parameter":
                # Parameter with type annotation and default value
                param_name = self._get_node_text(child.children[0], source_code)
                type_annotation = (
                    self._get_node_text(child.children[2], source_code)
                    if len(child.children) > 2
                    else None
                )
                default_value = (
                    self._get_node_text(child.children[4], source_code)
                    if len(child.children) > 4
                    else None
                )
                parameters.append(
                    Parameter(
                        name=param_name,
                        type_annotation=type_annotation,
                        default_value=default_value,
                        is_required=False,
                    )
                )

        # Filter out 'self' and 'cls' parameters
        parameters = [p for p in parameters if p.name not in ("self", "cls")]

        return parameters

    def _extract_return_type(self, func_node: Node, source_code: str) -> Optional[str]:
        """Extract return type annotation."""
        return_type_node = func_node.child_by_field_name("return_type")
        if return_type_node:
            return self._get_node_text(return_type_node, source_code).lstrip("->")
        return None

    def _extract_docstring(self, func_node: Node, source_code: str) -> Optional[str]:
        """Extract function docstring."""
        body_node = func_node.child_by_field_name("body")
        if not body_node:
            return None

        # Look for string literal as first statement
        for child in body_node.children:
            if child.type == "expression_statement":
                expr = child.children[0] if child.children else None
                if expr and expr.type == "string":
                    docstring = self._get_node_text(expr, source_code)
                    # Clean up the docstring (remove quotes and extra whitespace)
                    docstring = re.sub(r'^["\']|["\']$', "", docstring.strip())
                    docstring = re.sub(
                        r'^["\']|["\']$', "", docstring.strip()
                    )  # Handle triple quotes
                    return docstring.strip()

        return None

    def _extract_decorators(self, func_node: Node, source_code: str) -> List[str]:
        """Extract function decorators."""
        decorators = []

        # Look for decorator nodes before the function
        for child in func_node.children:
            if child.type == "decorator":
                decorator_text = self._get_node_text(child, source_code)
                decorators.append(decorator_text.lstrip("@"))

        return decorators

    def _get_node_text(self, node: Node, source_code: str) -> str:
        """Get the text content of a node."""
        if not node:
            return ""
        return source_code[node.start_byte : node.end_byte]
