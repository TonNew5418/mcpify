from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .function import FunctionInfo


@dataclass
class MCPToolParameter:
    """Represents an MCP tool parameter."""

    name: str
    type: str
    description: str
    required: bool = True
    default: Optional[Any] = None


@dataclass
class MCPTool:
    """Represents an MCP tool generated from a function."""

    name: str
    description: str
    function_info: FunctionInfo
    parameters: List[MCPToolParameter]
    implementation_type: str = "python_function"  # or "subprocess", "api_call"

    def to_mcp_schema(self) -> Dict[str, Any]:
        """Convert to MCP tool schema format."""
        properties = {}
        required = []

        for param in self.parameters:
            properties[param.name] = {
                "type": param.type,
                "description": param.description,
            }
            if param.default is not None:
                properties[param.name]["default"] = param.default
            if param.required:
                required.append(param.name)

        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }

    def to_implementation_config(self) -> Dict[str, Any]:
        """Generate implementation configuration for the MCP server."""
        return {
            "type": self.implementation_type,
            "module": str(
                self.function_info.file_path.with_suffix("").as_posix()
            ).replace("/", "."),
            "function": self.function_info.name,
            "class": self.function_info.class_name,
            "file_path": str(self.function_info.file_path),
            "line_number": self.function_info.line_number,
        }
