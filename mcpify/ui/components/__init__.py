"""
UI Components package for MCPify.

This package contains all the reusable UI components for the Streamlit interface.
"""


from mcpify.ui.components.chat_interface import ChatInterface, DetectionResultsInterface
from mcpify.ui.components.sidebar import NavigationManager, SidebarManager

__all__ = [
    "ChatInterface",
    "DetectionResultsInterface",
    "SidebarManager",
    "NavigationManager",
]
