"""
Factory functions for creating detectors.

This module provides factory functions to create detector instances
with proper configuration and fallback strategies.
"""

from typing import Any

from .base import BaseDetector
from .camel import CamelDetector
from .openai import OpenaiDetector


def create_detector(detector_type: str = "auto", **kwargs: Any) -> BaseDetector:
    """
    Create a detector instance based on the specified type.

    Args:
        detector_type: Type of detector to create
            - "openai": OpenAI-based detector
            - "camel": Camel-AI based detector
            - "auto": Automatically select best available detector
        **kwargs: Additional arguments passed to detector constructor

    Returns:
        Configured detector instance
    """
    detectors = {
        "openai": lambda: OpenaiDetector(**kwargs),
        "camel": lambda: CamelDetector(**kwargs),
    }

    if detector_type == "auto":
        return _create_auto_detector(**kwargs)

    if detector_type not in detectors:
        raise ValueError(f"Unknown detector type: {detector_type}")

    return detectors[detector_type]()


def _create_auto_detector(**kwargs: Any) -> BaseDetector:
    """
    Automatically select the best available detector.

    This function tries to create detectors in order of preference
    and returns the first one that can be successfully initialized.
    """
    # Try Camel-AI detector first (most advanced)
    try:
        return CamelDetector(**kwargs)
    except Exception:
        pass  # Fall back to OpenAI detector

    # Fall back to OpenAI detector
    return OpenaiDetector(**kwargs)


def create_local_only_detector() -> BaseDetector:
    """Create a detector that works without external APIs."""
    raise RuntimeError(
        "No local-only detector available. AST detector has been removed."
    )
