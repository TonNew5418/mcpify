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


@dataclass
class DetectionResult:
    """Result of project detection and analysis."""

    project_info: ProjectInfo
    tools: list[ToolSpec]
    backend_config: dict[str, Any]
    confidence_score: float = 0.8

    def __post_init__(self):
        """Validate detection result after initialization."""
        if not (0.0 <= self.confidence_score <= 1.0):
            raise ValueError("Confidence score must be between 0.0 and 1.0")
