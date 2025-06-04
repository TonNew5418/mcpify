"""
Detection module for MCPify.

This module provides various detectors for analyzing projects and extracting
API information to generate MCP configurations.
"""

from .ast import AstDetector
from .base import BaseDetector
from .camel import CamelDetector
from .factory import create_detector
from .openai import OpenaiDetector
from .types import ProjectInfo, ToolSpec

__all__ = [
    # Core detector classes
    "BaseDetector",
    "AstDetector",
    "CamelDetector",
    "OpenaiDetector",
    # Type definitions
    "ProjectInfo",
    "ToolSpec",
    # Factory function
    "create_detector",
]
