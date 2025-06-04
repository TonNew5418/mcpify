"""
MCPify - Automatically generate MCP server configurations from
existing projects.
"""

__version__ = "0.1.0"

# Export main detection function for backward compatibility
# Export base classes and core types
# Backward compatibility alias
# Export detector implementations
from .detect import (
    BaseDetector,
    ClaudeDetector,
    CompositeDetector,
    HeuristicDetector,
    LocalLLMDetector,
    OpenaiDetector,
    ProjectDetector,
    ProjectInfo,
    ToolSpec,
    create_detector,
    create_local_only_detector,
    create_multi_strategy_detector,
    detect_project_api,
)

__all__ = [
    # Core functions
    "detect_project_api",
    # Base classes
    "BaseDetector",
    "OpenaiDetector",
    "ProjectInfo",
    "ToolSpec",
    # Backward compatibility
    "ProjectDetector",
    # Detector implementations
    "HeuristicDetector",
    "ClaudeDetector",
    "LocalLLMDetector",
    "CompositeDetector",
    # Factory functions
    "create_detector",
    "create_multi_strategy_detector",
    "create_local_only_detector",
]
