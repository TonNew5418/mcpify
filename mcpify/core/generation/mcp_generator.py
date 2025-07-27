import json
from pathlib import Path
from typing import Any, Dict, List

import jinja2

from ...models.repository import Repository
from ...models.tool import MCPTool


class MCPGenerator:
    """Generate MCP server code from tool specifications using official MCP SDK."""

    def __init__(self):
        """Initialize generator."""
        # Setup Jinja2 environment
        template_dir = Path(__file__).parent.parent.parent / "templates"
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_dir),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Add custom filters
        self.jinja_env.filters["topython"] = self._to_python_literal

    def _to_python_literal(self, obj) -> str:
        """Convert object to Python literal representation."""

        def convert_nulls(obj):
            """Recursively convert null values to None."""
            if obj is None:
                return None
            elif isinstance(obj, dict):
                return {k: convert_nulls(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_nulls(item) for item in obj]
            else:
                return obj

        # Convert and format
        converted = convert_nulls(obj)
        return repr(converted)

    def generate_server(
        self,
        tools: List[MCPTool],
        repository: Repository,
        output_dir: Path,
        transport: str = "stdio",
    ) -> Path:
        """Generate MCP server code and configuration."""

        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        # Prepare template context
        context = self._prepare_template_context(tools, repository, transport)

        # Generate server code
        server_path = self._generate_server_code(context, output_dir, transport)

        # Generate configuration files
        self._generate_config_files(tools, repository, output_dir)

        return server_path

    def _prepare_template_context(
        self, tools: List[MCPTool], repository: Repository, transport: str
    ) -> Dict[str, Any]:
        """Prepare context data for template rendering."""

        # Convert tools to configuration format
        tools_config = []
        for tool in tools:
            tool_config = {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.to_mcp_schema()["inputSchema"],
                "implementation": tool.to_implementation_config(),
            }
            tools_config.append(tool_config)

        return {
            "repository_name": repository.name,
            "repository_url": repository.url,
            "repository_path": str(repository.local_path),
            "tools_config": tools_config,
            "tool_count": len(tools),
            "dependencies": repository.dependencies,
            "transport": transport,
        }

    def _generate_server_code(
        self, context: Dict[str, Any], output_dir: Path, transport: str
    ) -> Path:
        """Generate the main server Python file using MCP SDK."""

        # Select template based on transport
        if transport == "stdio":
            template_name = "mcp_server_stdio.py.jinja2"
        elif transport == "http":
            template_name = "mcp_server_http.py.jinja2"
        else:
            raise ValueError(f"Unsupported transport: {transport}")

        template = self.jinja_env.get_template(template_name)
        server_code = template.render(**context)

        server_path = output_dir / "mcp_server.py"
        with open(server_path, "w", encoding="utf-8") as f:
            f.write(server_code)

        # Make it executable
        server_path.chmod(0o755)

        return server_path

    def _generate_config_files(
        self, tools: List[MCPTool], repository: Repository, output_dir: Path
    ):
        """Generate additional configuration files."""

        # Generate tools manifest
        tools_manifest = {
            "repository": {
                "name": repository.name,
                "url": repository.url,
                "path": str(repository.local_path),
                "language": repository.language,
            },
            "tools": [tool.to_mcp_schema() for tool in tools],
            "metadata": {
                "generated_by": "MCPify",
                "tool_count": len(tools),
                "dependencies": repository.dependencies,
            },
        }

        manifest_path = output_dir / "tools_manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(tools_manifest, f, indent=2)

        # Generate README for the generated server
        readme_content = self._generate_server_readme(tools, repository)
        readme_path = output_dir / "README.md"
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(readme_content)

        # Generate requirements.txt if needed
        if repository.dependencies:
            requirements_path = output_dir / "requirements.txt"
            with open(requirements_path, "w", encoding="utf-8") as f:
                for dep in repository.dependencies:
                    f.write(f"{dep}\n")

    def _generate_server_readme(
        self, tools: List[MCPTool], repository: Repository
    ) -> str:
        """Generate README for the MCP server."""

        tools_list = "\n".join(
            [f"- **{tool.name}**: {tool.description}" for tool in tools]
        )

        return f"""# MCP Server for {repository.name}

Generated by MCPify from: {repository.url}

## Available Tools

{tools_list}

## Usage

### Start the MCP Server

```bash
python mcp_server.py
```

### Using with Claude Desktop

Add this to your Claude Desktop config:

```json
{{
  "mcpServers": {{
    "{repository.name.lower()}": {{
      "command": "python",
      "args": ["{Path.cwd().absolute() / 'mcp_server.py'}"]
    }}
  }}
}}
```

### Using with Other MCP Clients

The server implements the standard MCP protocol over stdio. Connect using:

```python
import subprocess
import json

# Start the server
process = subprocess.Popen(
    ["python", "mcp_server.py"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

# List available tools
request = {{"method": "tools/list", "id": 1}}
process.stdin.write(json.dumps(request) + "\\n")
process.stdin.flush()

response = json.loads(process.stdout.readline())
print("Available tools:", response)
```

## Dependencies

{"Install dependencies: `pip install " + " ".join(repository.dependencies) + "`" if repository.dependencies else "No additional dependencies required."}

## Source Functions

{chr(10).join([f"- `{tool.function_info.qualified_name}` in {tool.function_info.file_path}:{tool.function_info.line_number}" for tool in tools])}

## Generated by MCPify

This MCP server was automatically generated by MCPify.
Visit https://github.com/yourorg/mcpify for more information.
"""
