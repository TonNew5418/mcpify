from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class Parameter:
    """Represents a function parameter."""

    name: str
    type_annotation: Optional[str] = None
    default_value: Optional[str] = None
    is_required: bool = True


@dataclass
class FunctionInfo:
    """Represents a Python function extracted from source code."""

    name: str
    file_path: Path
    line_number: int
    parameters: List[Parameter]
    return_type: Optional[str] = None
    docstring: Optional[str] = None
    is_async: bool = False
    is_method: bool = False
    class_name: Optional[str] = None
    decorators: List[str] = None

    def __post_init__(self):
        if self.decorators is None:
            self.decorators = []

    @property
    def signature(self) -> str:
        """Generate function signature string."""
        params = []
        for param in self.parameters:
            param_str = param.name
            if param.type_annotation:
                param_str += f": {param.type_annotation}"
            if param.default_value:
                param_str += f" = {param.default_value}"
            params.append(param_str)

        params_str = ", ".join(params)
        return_annotation = f" -> {self.return_type}" if self.return_type else ""
        async_prefix = "async " if self.is_async else ""

        return f"{async_prefix}def {self.name}({params_str}){return_annotation}"

    @property
    def qualified_name(self) -> str:
        """Get fully qualified name including class if applicable."""
        if self.class_name:
            return f"{self.class_name}.{self.name}"
        return self.name

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "qualified_name": self.qualified_name,
            "file_path": str(self.file_path),
            "line_number": self.line_number,
            "signature": self.signature,
            "docstring": self.docstring,
            "is_async": self.is_async,
            "is_method": self.is_method,
            "class_name": self.class_name,
            "parameters": [
                {
                    "name": p.name,
                    "type": p.type_annotation,
                    "default": p.default_value,
                    "required": p.is_required,
                }
                for p in self.parameters
            ],
            "return_type": self.return_type,
            "decorators": self.decorators,
        }
