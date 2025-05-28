"""
Repository analysis and API detection module for MCPify.

This module analyzes existing projects to automatically detect their API structure
and generate MCP server configurations. It uses LLM analysis to understand code
patterns, documentation, and project structure.
"""

import ast
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import openai


@dataclass
class ProjectInfo:
    """Information extracted from a project."""

    name: str
    description: str
    main_files: list[str]
    readme_content: str
    project_type: str  # 'cli', 'web', 'library', etc.
    dependencies: list[str]


@dataclass
class ToolSpec:
    """Specification for a detected tool/API endpoint."""

    name: str
    description: str
    args: list[str]
    parameters: list[dict[str, Any]]


class ProjectDetector:
    """Detects and analyzes project structure to generate MCP configurations."""

    def __init__(self, openai_api_key: str | None = None):
        """Initialize the detector with OpenAI API key."""
        self.openai_client = None
        if openai_api_key:
            openai.api_key = openai_api_key
            self.openai_client = openai
        elif os.getenv("OPENAI_API_KEY"):
            self.openai_client = openai
        else:
            print(
                "Warning: No OpenAI API key provided. Using basic heuristic detection."
            )

    def detect_project(self, project_path: str) -> dict[str, Any]:
        """
        Analyze a project directory and generate MCP configuration.

        Args:
            project_path: Path to the project directory

        Returns:
            Dictionary containing the MCP configuration
        """
        project_path = Path(project_path)
        if not project_path.exists():
            raise ValueError(f"Project path does not exist: {project_path}")

        # Extract project information
        project_info = self._extract_project_info(project_path)

        # Detect tools/APIs
        tools = self._detect_tools(project_path, project_info)

        # Generate backend configuration
        backend_config = self._generate_backend_config(project_path, project_info)

        # Construct final configuration
        config = {
            "name": project_info.name,
            "description": project_info.description,
            "backend": backend_config,
            "tools": [self._tool_spec_to_dict(tool) for tool in tools],
        }

        return config

    def _extract_project_info(self, project_path: Path) -> ProjectInfo:
        """Extract basic information about the project."""
        name = project_path.name
        description = f"API for {name}"
        main_files = []
        readme_content = ""
        project_type = "unknown"
        dependencies = []

        # Find README files
        readme_files = list(project_path.glob("README*")) + list(
            project_path.glob("readme*")
        )
        if readme_files:
            try:
                with open(readme_files[0], encoding="utf-8") as f:
                    readme_content = f.read()
                    # Extract description from README
                    description = self._extract_description_from_readme(readme_content)
            except Exception as e:
                print(f"Warning: Could not read README: {e}")

        # Find main Python files
        python_files = list(project_path.glob("*.py"))
        if python_files:
            main_files.extend([str(f.relative_to(project_path)) for f in python_files])
            project_type = "cli" if self._has_cli_patterns(python_files) else "library"

        # Check for web frameworks
        if self._has_web_patterns(project_path):
            project_type = "web"

        # Extract dependencies
        dependencies = self._extract_dependencies(project_path)

        return ProjectInfo(
            name=name,
            description=description,
            main_files=main_files,
            readme_content=readme_content,
            project_type=project_type,
            dependencies=dependencies,
        )

    def _extract_description_from_readme(self, readme_content: str) -> str:
        """Extract a meaningful description from README content."""
        lines = readme_content.split("\n")

        # Look for the first substantial paragraph after the title
        description_lines = []
        found_title = False

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Skip title lines (starting with #)
            if line.startswith("#"):
                found_title = True
                continue

            # Skip badges and links
            if "[![" in line or line.startswith("http"):
                continue

            # If we found a title and this is a substantial line, use it
            if found_title and len(line) > 20:
                description_lines.append(line)
                if len(" ".join(description_lines)) > 100:
                    break

        description = " ".join(description_lines)
        return description if description else "A project"

    def _has_cli_patterns(self, python_files: list[Path]) -> bool:
        """Check if the project has CLI patterns."""
        for file_path in python_files:
            try:
                with open(file_path, encoding="utf-8") as f:
                    content = f.read()
                    if any(
                        pattern in content
                        for pattern in [
                            "argparse",
                            "click",
                            "typer",
                            'if __name__ == "__main__"',
                            "ArgumentParser",
                            "add_argument",
                        ]
                    ):
                        return True
            except Exception:
                continue
        return False

    def _has_web_patterns(self, project_path: Path) -> bool:
        """Check if the project has web framework patterns."""
        # Check for common web framework files/patterns
        web_indicators = [
            "app.py",
            "main.py",
            "server.py",
            "wsgi.py",
            "asgi.py",
            "requirements.txt",
            "Pipfile",
            "pyproject.toml",
        ]

        for indicator in web_indicators:
            if (project_path / indicator).exists():
                try:
                    with open(project_path / indicator, encoding="utf-8") as f:
                        content = f.read()
                        if any(
                            framework in content.lower()
                            for framework in [
                                "flask",
                                "django",
                                "fastapi",
                                "tornado",
                                "bottle",
                                "aiohttp",
                                "sanic",
                                "quart",
                            ]
                        ):
                            return True
                except Exception:
                    continue
        return False

    def _extract_dependencies(self, project_path: Path) -> list[str]:
        """Extract project dependencies from various files."""
        dependencies = []

        # Check requirements.txt
        req_file = project_path / "requirements.txt"
        if req_file.exists():
            try:
                with open(req_file, encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            # Extract package name (before version specifiers)
                            pkg_name = re.split(r"[>=<!=]", line)[0].strip()
                            dependencies.append(pkg_name)
            except Exception:
                pass

        # Check pyproject.toml
        pyproject_file = project_path / "pyproject.toml"
        if pyproject_file.exists():
            try:
                with open(pyproject_file, encoding="utf-8") as f:
                    content = f.read()
                    # Simple regex to extract dependencies
                    deps_match = re.search(
                        r"dependencies\s*=\s*\[(.*?)\]", content, re.DOTALL
                    )
                    if deps_match:
                        deps_str = deps_match.group(1)
                        for line in deps_str.split("\n"):
                            line = line.strip().strip('"').strip("'").strip(",")
                            if line and not line.startswith("#"):
                                pkg_name = re.split(r"[>=<!=]", line)[0].strip()
                                dependencies.append(pkg_name)
            except Exception:
                pass

        return dependencies

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
                # Match patterns like @app.get("/path"), @app.post("/path"), etc.
                fastapi_patterns = [
                    r'@app\.(get|post|put|delete|patch)\(["\']([^"\']+)["\'].*?\)\s*(?:async\s+)?def\s+(\w+)',
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
                f"<{param_type}:{param_name}>" if param_type else f"<{param_name}>",
                f"{{{param_name}}}",
            )

        # Find FastAPI path parameters like {todo_id}
        fastapi_params = re.findall(r"\{(\w+)\}", route)
        for param_name in fastapi_params:
            if not any(p["name"] == param_name for p in parameters):
                parameters.append(
                    {
                        "name": param_name,
                        "type": "integer",  # Default to integer for FastAPI path params
                        "description": f"The {param_name} parameter",
                    }
                )

        # Check for query parameters in the function
        func_pattern = rf"def\s+{re.escape(func_name)}\s*\([^)]*\):(.*?)(?=(?:async\s+)?def\s+\w+|@app\.|$)"
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
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at analyzing code and APIs. Provide clear, accurate tool specifications.",
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

    def _generate_backend_config(
        self, project_path: Path, project_info: ProjectInfo
    ) -> dict[str, Any]:
        """Generate backend configuration based on project type."""
        if project_info.project_type == "cli":
            # Find the main executable file
            main_file = None
            for file_name in project_info.main_files:
                if file_name.endswith(".py") and (
                    "main" in file_name or "cli" in file_name or "__main__" in file_name
                ):
                    main_file = file_name
                    break

            if not main_file and project_info.main_files:
                main_file = project_info.main_files[0]

            return {
                "type": "commandline",
                "config": {
                    "command": "python3",
                    "args": [
                        str(project_path / main_file)
                        if main_file
                        else str(project_path)
                    ],
                    "cwd": ".",
                },
            }

        elif project_info.project_type == "web":
            return {
                "type": "http",
                "config": {"base_url": "http://localhost:8000", "timeout": 30},
            }

        else:
            # Default to commandline
            return {
                "type": "commandline",
                "config": {
                    "command": "python3",
                    "args": [str(project_path)],
                    "cwd": ".",
                },
            }

    def _map_python_type_to_json(self, python_type: str) -> str:
        """Map Python types to JSON schema types."""
        type_mapping = {
            "str": "string",
            "int": "integer",
            "float": "number",
            "bool": "boolean",
            "list": "array",
        }
        return type_mapping.get(python_type, "string")

    def _tool_spec_to_dict(self, tool: ToolSpec) -> dict[str, Any]:
        """Convert ToolSpec to dictionary format."""
        return {
            "name": tool.name,
            "description": tool.description,
            "args": tool.args,
            "parameters": tool.parameters,
        }


def detect_project_api(
    project_path: str, openai_api_key: str | None = None
) -> dict[str, Any]:
    """
    Main function to detect project API and generate MCP configuration.

    Args:
        project_path: Path to the project directory
        openai_api_key: Optional OpenAI API key for enhanced analysis

    Returns:
        Dictionary containing the MCP configuration
    """
    detector = ProjectDetector(openai_api_key)
    return detector.detect_project(project_path)
