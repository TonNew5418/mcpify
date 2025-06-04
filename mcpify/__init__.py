"""
MCPify - Automatically detect APIs and generate MCP server configurations.

This package provides tools to analyze existing projects and transform them into
Model Context Protocol (MCP) servers.
"""

from .detect import (
    AstDetector,
    BaseDetector,
    CompositeDetector,
    OpenaiDetector,
    create_detector,
)
from .validate import validate_config_dict, validate_config_file
from .wrapper import MCPWrapper

__version__ = "0.1.0"

__all__ = [
    # Core functionality
    "MCPWrapper",
    "validate_config_dict",
    "validate_config_file",
    # Detectors
    "BaseDetector",
    "AstDetector",
    "OpenaiDetector",
    "CompositeDetector",
    "create_detector",
    # Version
    "__version__",
]
