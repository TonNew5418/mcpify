"""
MCPify UI Module

This module provides a Streamlit-based interactive UI for mcpify,
allowing users to chat with AI to describe their needs and automatically
generate MCP server configurations.
"""

from .main import start_ui

__all__ = ["start_ui"]
