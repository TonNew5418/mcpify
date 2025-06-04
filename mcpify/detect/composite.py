"""
Composite project detector.

This module contains the CompositeDetector class that combines multiple
detection strategies to provide comprehensive tool detection.
"""

from pathlib import Path

from .base import BaseDetector
from .types import ProjectInfo, ToolSpec


class CompositeDetector(BaseDetector):
    """A detector that combines multiple detection strategies."""

    def __init__(self, detectors: list[BaseDetector] | None = None, **kwargs):
        """Initialize the composite detector."""
        super().__init__(**kwargs)
        self.detectors = detectors or []

    def add_detector(self, detector: BaseDetector):
        """Add a detector to the composite."""
        self.detectors.append(detector)

    def _detect_tools(
        self, project_path: Path, project_info: ProjectInfo
    ) -> list[ToolSpec]:
        """Detect tools using multiple strategies and merge results."""
        all_tools = []
        tool_names = set()

        for detector in self.detectors:
            try:
                detector_tools = detector._detect_tools(project_path, project_info)
                # Avoid duplicates
                for tool in detector_tools:
                    if tool.name not in tool_names:
                        all_tools.append(tool)
                        tool_names.add(tool.name)
            except Exception as e:
                print(f"Warning: Detector {type(detector).__name__} failed: {e}")

        return all_tools
