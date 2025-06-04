"""
MCPify detect module.

This module provides various detector implementations for analyzing projects
and generating MCP server configurations.
"""

from .base import BaseDetector
from .claude import ClaudeDetector
from .composite import CompositeDetector
from .factory import (
    create_detector,
    create_local_only_detector,
    create_multi_strategy_detector,
)
from .heuristic import HeuristicDetector
from .local_llm import LocalLLMDetector
from .openai import OpenaiDetector
from .types import ProjectInfo, ToolSpec

# Backward compatibility alias
ProjectDetector = OpenaiDetector


def detect_project_api(
    project_path: str, openai_api_key: str | None = None
) -> dict[str, any]:
    """
    Main function to detect project API and generate MCP configuration.

    Args:
        project_path: Path to the project directory
        openai_api_key: Optional OpenAI API key for enhanced analysis

    Returns:
        Dictionary containing the MCP configuration
    """
    detector = OpenaiDetector(openai_api_key)
    return detector.detect_project(project_path)


__all__ = [
    # Base classes and types
    "BaseDetector",
    "ProjectInfo",
    "ToolSpec",
    # Detector implementations
    "OpenaiDetector",
    "HeuristicDetector",
    "ClaudeDetector",
    "LocalLLMDetector",
    "CompositeDetector",
    # Backward compatibility
    "ProjectDetector",
    # Factory functions
    "create_detector",
    "create_multi_strategy_detector",
    "create_local_only_detector",
    # Main function
    "detect_project_api",
]
