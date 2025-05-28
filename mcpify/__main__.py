#!/usr/bin/env python3
"""
MCPify main module entry point

This allows running mcpify as a module:
    python -m mcpify detect /path/to/project
    python -m mcpify serve config.json
"""

from .cli import main

if __name__ == "__main__":
    main()
