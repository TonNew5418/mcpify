"""
OpenAI-based project detector.

This module contains the OpenaiDetector class that uses OpenAI's API
for intelligent project analysis and tool detection.
"""

import ast
import json
import os
import re
from pathlib import Path
from typing import Any

import openai

from .base import BaseDetector
from .types import ProjectInfo, ToolSpec


class OpenaiDetector(BaseDetector):
    """OpenAI-based project detector implementation."""

    def __init__(self, openai_api_key: str | None = None, **kwargs):
        """Initialize the detector with OpenAI API key."""
        super().__init__(**kwargs)
        self.openai_client = None
        if openai_api_key:
            openai.api_key = openai_api_key
            self.openai_client = openai
        elif os.getenv("OPENAI_API_KEY"):
            self.openai_client = openai
        else:
            print(
                "Warning: No OpenAI API key provided. "
                "Using basic heuristic detection."
            )

    def _detect_tools(
        self, project_path: Path, project_info: ProjectInfo
    ) -> list[ToolSpec]:
        """Detect tools/APIs in the project."""
        tools = []

        if project_info.project_type == "cli":
            tools.extend(self._detect_cli_tools(project_path, project_info))
        elif project_info.project_type == "web":
            tools.extend(self._detect_web_tools(project_path, project_info))
        else:
            # Try to detect any callable functions
            tools.extend(self._detect_generic_tools(project_path, project_info))

        # Also check for interactive command patterns
        tools.extend(self._detect_interactive_commands(project_path, project_info))

        # Use LLM to enhance detection if available
        if self.openai_client and tools:
            tools = self._enhance_tools_with_llm(project_path, project_info, tools)

        return tools

    def _detect_cli_tools(
        self, project_path: Path, project_info: ProjectInfo
    ) -> list[ToolSpec]:
        """Detect CLI tools using AST analysis."""
        tools = []

        for main_file in project_info.main_files:
            file_path = project_path / main_file
            if not file_path.suffix == ".py":
                continue

            try:
                with open(file_path, encoding="utf-8") as f:
                    content = f.read()

                # Parse AST to find argparse patterns
                tree = ast.parse(content)
                tools.extend(self._extract_argparse_tools(tree, main_file))

            except Exception as e:
                print(f"Warning: Could not parse {main_file}: {e}")

        return tools

    def _extract_argparse_tools(self, tree: ast.AST, filename: str) -> list[ToolSpec]:
        """Extract tools from argparse usage in AST."""
        tools = []

        class ArgparseVisitor(ast.NodeVisitor):
            def __init__(self):
                self.arguments = []
                self.in_parser = False

            def visit_Call(self, node):
                # Look for add_argument calls
                if (
                    isinstance(node.func, ast.Attribute)
                    and node.func.attr == "add_argument"
                ):
                    if node.args and isinstance(node.args[0], ast.Constant):
                        arg_name = node.args[0].value

                        # Extract argument details
                        arg_info = {"name": arg_name}

                        # Look for help text
                        for keyword in node.keywords:
                            if keyword.arg == "help" and isinstance(
                                keyword.value, ast.Constant
                            ):
                                arg_info["help"] = keyword.value.value
                            elif keyword.arg == "type":
                                if isinstance(keyword.value, ast.Name):
                                    arg_info["type"] = keyword.value.id
                            elif keyword.arg == "action" and isinstance(
                                keyword.value, ast.Constant
                            ):
                                arg_info["action"] = keyword.value.value
                            elif keyword.arg == "nargs":
                                if isinstance(keyword.value, ast.Constant):
                                    arg_info["nargs"] = keyword.value.value

                        self.arguments.append(arg_info)

                self.generic_visit(node)

        visitor = ArgparseVisitor()
        visitor.visit(tree)

        # Convert argparse arguments to tools
        for arg in visitor.arguments:
            arg_name = arg["name"]
            if arg_name.startswith("--"):
                tool_name = arg_name[2:].replace("-", "_")
                description = arg.get("help", f"Execute {tool_name}")

                # Determine parameters
                parameters = []
                args = [arg_name]

                if arg.get("action") != "store_true":
                    # This argument takes a value
                    param_type = self._map_python_type_to_json(arg.get("type", "str"))
                    param_name = tool_name

                    if arg.get("nargs") == 2:
                        # Two parameters
                        parameters = [
                            {
                                "name": f"{param_name}1",
                                "type": param_type,
                                "description": f"First {param_name} value",
                            },
                            {
                                "name": f"{param_name}2",
                                "type": param_type,
                                "description": f"Second {param_name} value",
                            },
                        ]
                        args.extend([f"{{{param_name}1}}", f"{{{param_name}2}}"])
                    else:
                        parameters = [
                            {
                                "name": param_name,
                                "type": param_type,
                                "description": f"The {param_name} value",
                            }
                        ]
                        args.append(f"{{{param_name}}}")

                tools.append(
                    ToolSpec(
                        name=tool_name,
                        description=description,
                        args=args,
                        parameters=parameters,
                    )
                )

        return tools

    def _detect_web_tools(
        self, project_path: Path, project_info: ProjectInfo
    ) -> list[ToolSpec]:
        """Detect web API endpoints."""
        tools = []

        # This is a simplified implementation
        # In a real scenario, you'd parse Flask/Django/FastAPI routes
        for main_file in project_info.main_files:
            file_path = project_path / main_file
            try:
                with open(file_path, encoding="utf-8") as f:
                    content = f.read()

                # Look for Flask route decorators with more detail
                routes = re.findall(
                    r'@app\.route\(["\']([^"\']+)["\'].*?\)\s*def\s+(\w+)', content
                )

                # Also look for FastAPI route decorators
                fastapi_routes = []
                # Match patterns like @app.get("/path"), @app.post("/path")
                fastapi_patterns = [
                    r'@app\.(get|post|put|delete|patch)\(["\']([^"\']+)'
                    r'["\'].*?\)\s*(?:async\s+)?def\s+(\w+)',
                ]

                for pattern in fastapi_patterns:
                    matches = re.findall(pattern, content)
                    for method, route, func_name in matches:
                        fastapi_routes.append((route, func_name, method.upper()))

                # Process Flask routes
                for route, func_name in routes:
                    tools.append(self._process_route(route, func_name, content, "GET"))

                # Process FastAPI routes
                for route, func_name, method in fastapi_routes:
                    tools.append(self._process_route(route, func_name, content, method))

            except Exception as e:
                print(f"Warning: Could not analyze {main_file}: {e}")

        return tools

    def _process_route(
        self, route: str, func_name: str, content: str, method: str
    ) -> ToolSpec:
        """Process a single route and extract parameters."""
        # Extract route parameters
        parameters = []
        processed_route = route

        # Find route parameters like <category>, <int:id>, etc.
        route_params = re.findall(r"<(?:(\w+):)?(\w+)>", route)
        for param_type, param_name in route_params:
            param_type = param_type or "string"
            # Map Flask types to JSON schema types
            json_type = {
                "int": "integer",
                "float": "number",
                "string": "string",
                "path": "string",
                "uuid": "string",
            }.get(param_type, "string")

            parameters.append(
                {
                    "name": param_name,
                    "type": json_type,
                    "description": f"The {param_name} parameter",
                }
            )

            # Replace route parameter with placeholder
            processed_route = processed_route.replace(
                (f"<{param_type}:{param_name}>" if param_type else f"<{param_name}>"),
                f"{{{param_name}}}",
            )

        # Find FastAPI path parameters like {todo_id}
        fastapi_params = re.findall(r"\{(\w+)\}", route)
        for param_name in fastapi_params:
            if not any(p["name"] == param_name for p in parameters):
                parameters.append(
                    {
                        "name": param_name,
                        # Default to integer for FastAPI path params
                        "type": "integer",
                        "description": f"The {param_name} parameter",
                    }
                )

        # Check for query parameters in the function
        func_pattern = (
            rf"def\s+{re.escape(func_name)}\s*\([^)]*\):(.*?)"
            r"(?=(?:async\s+)?def\s+\w+|@app\.|$)"
        )
        func_match = re.search(func_pattern, content, re.DOTALL)

        if func_match:
            func_body = func_match.group(1)
            # Look for request.args.get patterns (Flask)
            query_params = re.findall(r'request\.args\.get\(["\'](\w+)["\']', func_body)

            # Look for FastAPI Query parameters
            fastapi_query_params = re.findall(
                r"(\w+):\s*Optional\[\w+\]\s*=\s*Query\([^)]*\)", func_body
            )
            query_params.extend(fastapi_query_params)

            for param in query_params:
                if not any(p["name"] == param for p in parameters):
                    parameters.append(
                        {
                            "name": param,
                            "type": "string",
                            "description": f"Query parameter {param}",
                            "required": False,
                        }
                    )

        # Build args list
        args = [processed_route]

        # Add required route parameters
        for param in parameters:
            if param.get("required", True) and "Query parameter" not in param.get(
                "description", ""
            ):
                args.append(f"{{{param['name']}}}")

        # For query parameters, add them as optional args with query syntax
        query_parts = []
        for param in parameters:
            if "Query parameter" in param.get("description", ""):
                query_parts.append(f"{param['name']}={{{param['name']}}}")
        if query_parts:
            args[0] = f"{processed_route}?{'&'.join(query_parts)}"

        return ToolSpec(
            name=func_name,
            description=f"{method} {route} endpoint",
            args=args,
            parameters=parameters,
        )

    def _detect_generic_tools(
        self, project_path: Path, project_info: ProjectInfo
    ) -> list[ToolSpec]:
        """Detect generic callable functions."""
        tools = []

        for main_file in project_info.main_files:
            file_path = project_path / main_file
            if not file_path.suffix == ".py":
                continue

            try:
                with open(file_path, encoding="utf-8") as f:
                    content = f.read()

                tree = ast.parse(content)

                # Find public functions
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) and not node.name.startswith(
                        "_"
                    ):
                        # Extract function signature
                        parameters = []
                        for arg in node.args.args:
                            if arg.arg != "self":
                                parameters.append(
                                    {
                                        "name": arg.arg,
                                        "type": "string",
                                        "description": f"Parameter {arg.arg}",
                                    }
                                )

                        tools.append(
                            ToolSpec(
                                name=node.name,
                                description=f"Call function {node.name}",
                                args=[node.name]
                                + [f"{{{p['name']}}}" for p in parameters],
                                parameters=parameters,
                            )
                        )

            except Exception as e:
                print(f"Warning: Could not parse {main_file}: {e}")

        return tools

    def _detect_interactive_commands(
        self, project_path: Path, project_info: ProjectInfo
    ) -> list[ToolSpec]:
        """Detect interactive command-based APIs."""
        tools = []

        for main_file in project_info.main_files:
            file_path = project_path / main_file
            if not file_path.suffix == ".py":
                continue

            try:
                with open(file_path, encoding="utf-8") as f:
                    content = f.read()

                # Look for command patterns in if/elif chains
                commands = self._extract_command_patterns(content)
                for cmd_name, cmd_info in commands.items():
                    tools.append(
                        ToolSpec(
                            name=cmd_name,
                            description=cmd_info["description"],
                            args=[cmd_name] + cmd_info.get("args", []),
                            parameters=cmd_info.get("parameters", []),
                        )
                    )

            except Exception as e:
                print(f"Warning: Could not analyze {main_file}: {e}")

        return tools

    def _extract_command_patterns(self, content: str) -> dict[str, Any]:
        """Extract command patterns from if/elif chains."""
        commands = {}

        # Pattern for simple commands like: if line.lower() == 'hello':
        simple_pattern = r"(?:if|elif)\s+.*?\.lower\(\)\s*==\s*['\"](\w+)['\"]"
        matches = re.findall(simple_pattern, content)
        for match in matches:
            if match not in ["quit", "exit"]:  # Skip termination commands
                commands[match] = {
                    "description": f"Execute {match} command",
                    "args": [],
                    "parameters": [],
                }

        # Pattern for commands with parameters like:
        # elif line.lower().startswith('echo '):
        param_pattern = r"(?:if|elif)\s+.*?\.lower\(\)\.startswith\(['\"](\w+)\s"
        matches = re.findall(param_pattern, content)
        for match in matches:
            commands[match] = {
                "description": f"Execute {match} command with message",
                "args": ["{message}"],
                "parameters": [
                    {
                        "name": "message",
                        "type": "string",
                        "description": f"Message for {match} command",
                    }
                ],
            }

        return commands

    def _enhance_tools_with_llm(
        self, project_path: Path, project_info: ProjectInfo, tools: list[ToolSpec]
    ) -> list[ToolSpec]:
        """Use LLM to enhance tool descriptions and parameters."""
        if not self.openai_client:
            return tools

        try:
            # Prepare context for LLM
            context = self._prepare_llm_context(project_path, project_info, tools)

            prompt = f"""
Analyze this project and improve the API tool specifications:

{context}

Please provide improved descriptions and parameter details for each tool.
Return a JSON array with the enhanced tool specifications in this format:
[
  {{
    "name": "tool_name",
    "description": "Clear, helpful description",
    "args": ["--flag", "{{param}}"],
    "parameters": [
      {{
        "name": "param",
        "type": "string|number|boolean",
        "description": "Clear parameter description"
      }}
    ]
  }}
]
"""

            response = self.openai_client.chat.completions.create(
                model="gpt-4.1",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert at analyzing code and APIs. "
                            "Provide clear, accurate tool specifications."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
            )

            # Parse LLM response
            enhanced_tools_data = json.loads(response.choices[0].message.content)
            enhanced_tools = []

            for tool_data in enhanced_tools_data:
                enhanced_tools.append(
                    ToolSpec(
                        name=tool_data["name"],
                        description=tool_data["description"],
                        args=tool_data["args"],
                        parameters=tool_data["parameters"],
                    )
                )

            return enhanced_tools

        except Exception as e:
            print(f"Warning: LLM enhancement failed: {e}")
            return tools

    def _prepare_llm_context(
        self, project_path: Path, project_info: ProjectInfo, tools: list[ToolSpec]
    ) -> str:
        """Prepare context information for LLM analysis."""
        context_parts = []

        # Project info
        context_parts.append(f"Project: {project_info.name}")
        context_parts.append(f"Type: {project_info.project_type}")
        context_parts.append(f"Description: {project_info.description}")

        # README excerpt
        if project_info.readme_content:
            readme_excerpt = project_info.readme_content[:1000]
            context_parts.append(f"README excerpt:\n{readme_excerpt}")

        # Current tools
        context_parts.append("Current detected tools:")
        for tool in tools:
            context_parts.append(f"- {tool.name}: {tool.description}")
            context_parts.append(f"  Args: {tool.args}")
            if tool.parameters:
                context_parts.append(
                    f"  Parameters: {[p['name'] for p in tool.parameters]}"
                )

        # Code samples
        for main_file in project_info.main_files[:2]:  # Limit to first 2 files
            file_path = project_path / main_file
            try:
                with open(file_path, encoding="utf-8") as f:
                    content = f.read()[:2000]  # First 2000 chars
                    context_parts.append(f"\nCode from {main_file}:\n{content}")
            except Exception:
                continue

        return "\n".join(context_parts)
