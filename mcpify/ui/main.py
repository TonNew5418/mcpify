"""
Main entry point for the MCPify Streamlit UI application.

This module provides the main Streamlit application for repository analysis
and MCP server configuration generation.
"""

import sys


def start_ui() -> None:
    """
    Start the Streamlit UI application.

    This function imports and runs the main UI application.
    """
    try:
        # Import the UI app
        from mcpify.ui.app import main

        print("🚀 Starting MCPify Repository Analyzer UI...")
        print("🌐 Navigate to: http://localhost:8501")
        print("Press Ctrl+C to stop")

        # Run the main UI function
        main()

    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Install UI dependencies with: pip install 'mcpify[ui]'")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 MCPify UI stopped by user")
        sys.exit(0)


if __name__ == "__main__":
    start_ui()
