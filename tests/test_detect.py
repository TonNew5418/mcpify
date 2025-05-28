"""
Unit tests for the MCPify detection module.
"""

import tempfile
from pathlib import Path

import pytest

from mcpify.detect import ProjectDetector, ProjectInfo, ToolSpec, detect_project_api
from mcpify.validate import validate_config_dict


class TestProjectInfo:
    """Test ProjectInfo dataclass."""

    def test_project_info_creation(self):
        """Test creating a ProjectInfo object."""
        info = ProjectInfo(
            name="test-project",
            description="Test description",
            main_files=["main.py"],
            readme_content="# Test Project",
            project_type="cli",
            dependencies=["requests"],
        )

        assert info.name == "test-project"
        assert info.description == "Test description"
        assert info.main_files == ["main.py"]
        assert info.readme_content == "# Test Project"
        assert info.project_type == "cli"
        assert info.dependencies == ["requests"]


class TestToolSpec:
    """Test ToolSpec dataclass."""

    def test_tool_spec_creation(self):
        """Test creating a ToolSpec object."""
        tool = ToolSpec(
            name="test_tool",
            description="Test tool description",
            args=["--flag", "{param}"],
            parameters=[
                {"name": "param", "type": "string", "description": "Test parameter"}
            ],
        )

        assert tool.name == "test_tool"
        assert tool.description == "Test tool description"
        assert tool.args == ["--flag", "{param}"]
        assert len(tool.parameters) == 1
        assert tool.parameters[0]["name"] == "param"


class TestProjectDetector:
    """Test ProjectDetector class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.detector = ProjectDetector()

    def test_detector_initialization(self):
        """Test ProjectDetector initialization."""
        # Test without API key
        detector = ProjectDetector()
        assert detector.openai_client is None

        # Test with API key
        # Note: We can't test the actual OpenAI client without a real key

    def test_extract_description_from_readme(self):
        """Test README description extraction."""
        readme_content = """
# Test Project

This is a test project for demonstration purposes.
It shows how to extract descriptions from README files.

## Installation

pip install test-project
"""

        description = self.detector._extract_description_from_readme(readme_content)
        assert "test project" in description.lower()
        assert "demonstration" in description.lower()

    def test_extract_description_empty_readme(self):
        """Test README description extraction with empty content."""
        description = self.detector._extract_description_from_readme("")
        assert description == "A project"

    def test_has_cli_patterns(self):
        """Test CLI pattern detection."""
        # Create temporary Python file with CLI patterns
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', help='Input file')
    args = parser.parse_args()

if __name__ == "__main__":
    main()
"""
            )
            temp_path = Path(f.name)

        try:
            result = self.detector._has_cli_patterns([temp_path])
            assert result is True
        finally:
            temp_path.unlink()

    def test_has_cli_patterns_no_cli(self):
        """Test CLI pattern detection with non-CLI file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """
def hello():
    return "Hello, World!"

def add(a, b):
    return a + b
"""
            )
            temp_path = Path(f.name)

        try:
            result = self.detector._has_cli_patterns([temp_path])
            assert result is False
        finally:
            temp_path.unlink()

    def test_extract_dependencies_requirements_txt(self):
        """Test dependency extraction from requirements.txt."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            req_file = temp_path / "requirements.txt"

            req_file.write_text(
                """
requests>=2.25.0
flask==2.0.1
# This is a comment
numpy
"""
            )

            dependencies = self.detector._extract_dependencies(temp_path)
            assert "requests" in dependencies
            assert "flask" in dependencies
            assert "numpy" in dependencies

    def test_extract_dependencies_pyproject_toml(self):
        """Test dependency extraction from pyproject.toml."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            pyproject_file = temp_path / "pyproject.toml"

            pyproject_file.write_text(
                """
[project]
dependencies = [
    "requests>=2.25.0",
    "flask==2.0.1",
    "numpy"
]
"""
            )

            dependencies = self.detector._extract_dependencies(temp_path)
            assert "requests" in dependencies
            assert "flask" in dependencies
            assert "numpy" in dependencies

    def test_map_python_type_to_json(self):
        """Test Python type to JSON type mapping."""
        assert self.detector._map_python_type_to_json("str") == "string"
        assert self.detector._map_python_type_to_json("int") == "integer"
        assert self.detector._map_python_type_to_json("float") == "number"
        assert self.detector._map_python_type_to_json("bool") == "boolean"
        assert self.detector._map_python_type_to_json("list") == "array"
        assert self.detector._map_python_type_to_json("unknown") == "string"

    def test_tool_spec_to_dict(self):
        """Test ToolSpec to dictionary conversion."""
        tool = ToolSpec(
            name="test_tool",
            description="Test tool",
            args=["cmd", "{param}"],
            parameters=[
                {"name": "param", "type": "string", "description": "Test parameter"}
            ],
        )

        tool_dict = self.detector._tool_spec_to_dict(tool)
        assert tool_dict["name"] == "test_tool"
        assert tool_dict["description"] == "Test tool"
        assert tool_dict["args"] == ["cmd", "{param}"]
        assert len(tool_dict["parameters"]) == 1


class TestInteractiveCommandDetection:
    """Test interactive command detection functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.detector = ProjectDetector()

    def test_extract_command_patterns(self):
        """Test extraction of command patterns from code."""
        code_content = """
def main():
    while True:
        line = input()
        if line.lower() == 'hello':
            print("Hello there!")
        elif line.lower() == 'time':
            print("Current time")
        elif line.lower().startswith('echo '):
            message = line[5:]
            print(f"Echo: {message}")
        elif line.lower() == 'quit':
            break
"""

        commands = self.detector._extract_command_patterns(code_content)

        # Should detect hello and time as simple commands
        assert "hello" in commands
        assert "time" in commands
        assert commands["hello"]["description"] == "Execute hello command"
        assert commands["hello"]["args"] == []

        # Should detect echo as parameterized command
        assert "echo" in commands
        assert commands["echo"]["description"] == "Execute echo command with message"
        assert commands["echo"]["args"] == ["{message}"]
        assert len(commands["echo"]["parameters"]) == 1

        # Should not detect quit (termination command)
        assert "quit" not in commands

    def test_detect_interactive_commands(self):
        """Test detection of interactive commands in a project."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create a server.py file with interactive commands
            server_file = temp_path / "server.py"
            server_file.write_text(
                """
#!/usr/bin/env python3
import time

def main():
    while True:
        line = input()
        if line.lower() == 'hello':
            print("Hello there!")
        elif line.lower() == 'time':
            current_time = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"Current time: {current_time}")
        elif line.lower().startswith('echo '):
            message = line[5:]
            print(f"Echo: {message}")
        elif line.lower() == 'quit':
            break

if __name__ == "__main__":
    main()
"""
            )

            project_info = ProjectInfo(
                name="test-server",
                description="Test server",
                main_files=["server.py"],
                readme_content="",
                project_type="cli",
                dependencies=[],
            )

            tools = self.detector._detect_interactive_commands(temp_path, project_info)

            # Should detect hello, time, and echo commands
            tool_names = [tool.name for tool in tools]
            assert "hello" in tool_names
            assert "time" in tool_names
            assert "echo" in tool_names

            # Check echo tool has parameters
            echo_tool = next(tool for tool in tools if tool.name == "echo")
            assert len(echo_tool.parameters) == 1
            assert echo_tool.parameters[0]["name"] == "message"


class TestProjectDetection:
    """Test end-to-end project detection."""

    def test_detect_simple_server_project(self):
        """Test detection of a simple server project."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create README
            readme_file = temp_path / "README.md"
            readme_file.write_text(
                """
# Test Server Project

This is a simple command-line server written in Python that processes
input from stdin and responds with appropriate output.
"""
            )

            # Create server.py
            server_file = temp_path / "server.py"
            server_file.write_text(
                """
#!/usr/bin/env python3
import time

def main():
    while True:
        line = input()
        if line.lower() == 'hello':
            print("Hello there!")
        elif line.lower() == 'time':
            current_time = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"Current time: {current_time}")
        elif line.lower().startswith('echo '):
            message = line[5:]
            print(f"Echo: {message}")
        elif line.lower() == 'quit':
            break

if __name__ == "__main__":
    main()
"""
            )

            # Detect the project
            config = detect_project_api(str(temp_path))

            # Validate the generated configuration
            result = validate_config_dict(config)
            assert result.is_valid is True

            # Check basic structure
            assert config["name"] == temp_path.name
            assert "simple command-line server" in config["description"].lower()
            assert config["backend"]["type"] == "commandline"
            assert config["backend"]["config"]["command"] == "python3"

            # Check detected tools
            tools = config["tools"]
            tool_names = [tool["name"] for tool in tools]
            assert "hello" in tool_names
            assert "time" in tool_names
            assert "echo" in tool_names

            # Check echo tool has parameters
            echo_tool = next(tool for tool in tools if tool["name"] == "echo")
            assert len(echo_tool["parameters"]) == 1
            assert echo_tool["parameters"][0]["name"] == "message"

    def test_detect_nonexistent_project(self):
        """Test detection of non-existent project."""
        with pytest.raises(ValueError, match="Project path does not exist"):
            detect_project_api("/nonexistent/path")

    def test_detect_empty_project(self):
        """Test detection of empty project directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = detect_project_api(temp_dir)

            # Should still generate a basic configuration
            assert "name" in config
            assert "description" in config
            assert "backend" in config
            assert "tools" in config

            # Validate the configuration
            result = validate_config_dict(config)
            assert result.is_valid is True


class TestBackendGeneration:
    """Test backend configuration generation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.detector = ProjectDetector()

    def test_generate_commandline_backend(self):
        """Test generation of commandline backend configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            project_info = ProjectInfo(
                name="test-project",
                description="Test project",
                main_files=["main.py"],
                readme_content="",
                project_type="cli",
                dependencies=[],
            )

            backend_config = self.detector._generate_backend_config(
                temp_path, project_info
            )

            assert backend_config["type"] == "commandline"
            assert backend_config["config"]["command"] == "python3"
            assert len(backend_config["config"]["args"]) == 1
            assert backend_config["config"]["cwd"] == "."

    def test_generate_web_backend(self):
        """Test generation of web backend configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            project_info = ProjectInfo(
                name="test-project",
                description="Test project",
                main_files=["app.py"],
                readme_content="",
                project_type="web",
                dependencies=[],
            )

            backend_config = self.detector._generate_backend_config(
                temp_path, project_info
            )

            assert backend_config["type"] == "http"
            assert backend_config["config"]["base_url"] == "http://localhost:8000"
            assert backend_config["config"]["timeout"] == 30

    def test_generate_default_backend(self):
        """Test generation of default backend configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            project_info = ProjectInfo(
                name="test-project",
                description="Test project",
                main_files=["lib.py"],
                readme_content="",
                project_type="library",
                dependencies=[],
            )

            backend_config = self.detector._generate_backend_config(
                temp_path, project_info
            )

            assert backend_config["type"] == "commandline"
            assert backend_config["config"]["command"] == "python3"
