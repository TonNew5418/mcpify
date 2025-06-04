"""
Data structures for project detection.

This module contains the common data types used across all detector implementations.
"""

from dataclasses import dataclass
from typing import Any


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
