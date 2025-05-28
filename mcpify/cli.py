"""Command line interface for MCPify."""

import argparse
import json
import os
import sys
from pathlib import Path

from .wrapper import MCPWrapper


def detect_command(directory: str) -> None:
    """Detect API from project directory and extract to JSON."""
    dir_path = Path(directory)
    if not dir_path.exists():
        print(f"Error: Directory '{directory}' does not exist.")
        sys.exit(1)
    
    output_file = f"{dir_path.name}.json"
    
    # TODO: Implement actual API detection logic
    # For now, create a sample config
    sample_config = {
        "name": dir_path.name,
        "description": f"API for {dir_path.name}",
        "tools": [
            {
                "name": "sample_tool",
                "description": "A sample tool",
                "args": ["arg1", "{param1}"],
                "parameters": [
                    {
                        "name": "param1",
                        "type": "string",
                        "description": "Sample parameter"
                    }
                ]
            }
        ]
    }
    
    with open(output_file, 'w') as f:
        json.dump(sample_config, f, indent=2)
    
    print(f"API specification extracted to {output_file}")


def view_command(config_path: str) -> None:
    """Visually display the API specification."""
    if not os.path.exists(config_path):
        print(f"Error: Config file '{config_path}' does not exist.")
        sys.exit(1)
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        print(f"API Specification: {config.get('name', 'Unknown')}")
        print(f"Description: {config.get('description', 'No description')}")
        print("\nTools:")
        
        for tool in config.get('tools', []):
            print(f"  - {tool.get('name', 'Unknown')}")
            desc = tool.get('description', 'No description')
            print(f"    Description: {desc}")
            print(f"    Args: {tool.get('args', [])}")
            if tool.get('parameters'):
                print("    Parameters:")
                for param in tool['parameters']:
                    name = param.get('name', 'Unknown')
                    ptype = param.get('type', 'unknown')
                    desc = param.get('description', 'No description')
                    print(f"      - {name} ({ptype}): {desc}")
            print()
    
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in config file: {e}")
        sys.exit(1)


def start_command(config_path: str) -> None:
    """Start the MCP server with the given config."""
    if not os.path.exists(config_path):
        print(f"Error: Config file '{config_path}' does not exist.")
        sys.exit(1)
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        print(f"Starting MCP server for {config.get('name', 'Unknown')}...")
        MCPWrapper(config_path).run()
    
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in config file: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nServer stopped.")
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="MCPify - Turn existing projects into MCP servers"
    )
    
    subparsers = parser.add_subparsers(
        dest='command', 
        help='Available commands'
    )
    
    # detect command
    detect_parser = subparsers.add_parser(
        'detect', 
        help='Detect project directory and extract API into JSON'
    )
    detect_parser.add_argument(
        'directory', 
        help='Project directory to analyze'
    )
    
    # view command
    view_parser = subparsers.add_parser(
        'view', 
        help='Visually display the API specification'
    )
    view_parser.add_argument(
        'config', 
        help='Path to the config JSON file'
    )
    
    # start command
    start_parser = subparsers.add_parser(
        'start', 
        help='Start the MCP server with the given config'
    )
    start_parser.add_argument(
        'config', 
        help='Path to the config JSON file'
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == 'detect':
        detect_command(args.directory)
    elif args.command == 'view':
        view_command(args.config)
    elif args.command == 'start':
        start_command(args.config)


if __name__ == "__main__":
    main() 