"""
Factory functions for creating detectors.

This module provides factory functions to create detector instances
with proper configuration and fallback strategies.
"""


from .ast import AstDetector
from .base import BaseDetector
from .composite import CompositeDetector
from .openai import OpenaiDetector


def create_detector(detector_type: str = "auto", **kwargs) -> BaseDetector:
    """
    Create a detector instance based on the specified type.

    Args:
        detector_type: Type of detector to create
            - "openai": OpenAI-based detector
            - "ast": AST-based detector
            - "composite": Composite detector with multiple strategies
            - "auto": Automatically select best available detector
        **kwargs: Additional arguments passed to detector constructor

    Returns:
        Configured detector instance
    """
    detectors = {
        "openai": lambda: OpenaiDetector(**kwargs),
        "ast": lambda: AstDetector(**kwargs),
        "composite": lambda: _create_composite_detector(**kwargs),
    }

    if detector_type == "auto":
        return _create_auto_detector(**kwargs)

    if detector_type not in detectors:
        raise ValueError(f"Unknown detector type: {detector_type}")

    return detectors[detector_type]()


def _create_composite_detector(**kwargs) -> CompositeDetector:
    """Create a composite detector with multiple strategies."""
    composite = CompositeDetector()

    # Add detectors in order of preference
    try:
        composite.add_detector(OpenaiDetector(**kwargs))
    except Exception:
        pass  # OpenAI detector might fail if no API key

    composite.add_detector(AstDetector(**kwargs))

    return composite


def _create_auto_detector(**kwargs) -> BaseDetector:
    """
    Automatically select the best available detector.

    This function tries to create detectors in order of preference
    and returns the first one that can be successfully initialized.
    """
    # Try OpenAI detector first if API key is available
    try:
        return OpenaiDetector(**kwargs)
    except Exception:
        pass  # Fall back to AST detector

    # Fall back to AST detector
    return AstDetector(**kwargs)


def create_local_only_detector() -> BaseDetector:
    """Create a detector that works without external APIs."""
    return AstDetector()
