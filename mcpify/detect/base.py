"""
Base detector class for project analysis.

This module contains the abstract BaseDetector class that defines the interface
and common functionality for all detector implementations.
"""

import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from .types import ProjectInfo, ToolSpec


class BaseDetector(ABC):
    """Base class for project detection and analysis."""

    @abstractmethod
    def __init__(self, **kwargs):
        """Initialize the detector with configuration options."""
        pass

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

        # Detect tools/APIs (abstract method)
        tools = self._detect_tools(project_path, project_info)

        # Generate backend configuration
        backend_config = self._generate_backend_config(
            project_path,
            project_info,
        )

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
        # Get project name from directory or pyproject.toml/setup.py
        name = self._get_project_name(project_path)
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

        # Check for CLI patterns first (higher priority)
        if self._has_cli_patterns(python_files):
            project_type = "cli"
        # Only check for web patterns if not already identified as CLI
        elif self._has_web_patterns(project_path):
            project_type = "web"
        else:
            project_type = "library"

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

    def _get_project_name(self, project_path: Path) -> str:
        """Extract project name from various sources."""
        # Try pyproject.toml first
        pyproject_file = project_path / "pyproject.toml"
        if pyproject_file.exists():
            try:
                with open(pyproject_file, encoding="utf-8") as f:
                    content = f.read()
                    # Look for project name in [project] section
                    name_match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
                    if name_match:
                        return name_match.group(1)
            except Exception:
                pass

        # Try setup.py next
        setup_file = project_path / "setup.py"
        if setup_file.exists():
            try:
                with open(setup_file, encoding="utf-8") as f:
                    content = f.read()
                    # Look for name parameter in setup()
                    name_match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
                    if name_match:
                        return name_match.group(1)
            except Exception:
                pass

        # Fall back to directory name
        name = project_path.resolve().name
        return name if name != "." else project_path.resolve().parent.name

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

    @abstractmethod
    def _detect_tools(
        self, project_path: Path, project_info: ProjectInfo
    ) -> list[ToolSpec]:
        """
        Detect tools/APIs in the project.

        This is the core method that subclasses must implement.
        Different detectors can use different strategies here.

        Args:
            project_path: Path to the project directory
            project_info: Extracted project information

        Returns:
            List of detected tools
        """
        pass

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
