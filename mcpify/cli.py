"""Command line interface for MCPify."""

import argparse
import json
import os
import sys
from pathlib import Path

from .detect import detect_project_api
from .validate import print_validation_results, validate_config_file
from .wrapper import MCPWrapper


def detect_command(args):
    """Handle the detect command."""
    project_path = Path(args.project_path)

    if not project_path.exists():
        print(f"❌ Error: Project path does not exist: {project_path}")
        sys.exit(1)

    print(f"Analyzing project: {project_path}")

    try:
        # Detect the API
        config = detect_project_api(str(project_path), args.openai_key)

        # Determine output file
        if args.output:
            output_file = Path(args.output)
        else:
            output_file = Path(f"{project_path.name}.json")

        # Write configuration to file
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

        print(f"✅ API specification extracted to {output_file}")
        print(f"📊 Detected {len(config.get('tools', []))} tools")
        print(f"🔧 Project type: {config.get('backend', {}).get('type', 'unknown')}")

        # Validate the generated configuration
        from .validate import validate_config_dict

        result = validate_config_dict(config)

        if result.is_valid and not result.warnings:
            print("✅ Generated configuration is valid")
        else:
            print(f"\n📋 Validation: {result.get_summary()}")
            if result.warnings:
                print("\n⚠️  Warnings:")
                for warning in result.warnings:
                    print(f"  • {warning.field}: {warning.message}")

    except Exception as e:
        print(f"❌ Error during detection: {e}")
        sys.exit(1)


def view_command(config_path: str) -> None:
    """Visually display the API specification."""
    if not os.path.exists(config_path):
        print(f"Error: Config file '{config_path}' does not exist.")
        sys.exit(1)

    try:
        with open(config_path) as f:
            config = json.load(f)

        print(f"API Specification: {config.get('name', 'Unknown')}")
        print(f"Description: {config.get('description', 'No description')}")
        print("\nTools:")

        for tool in config.get("tools", []):
            print(f"  - {tool.get('name', 'Unknown')}")
            desc = tool.get("description", "No description")
            print(f"    Description: {desc}")
            print(f"    Args: {tool.get('args', [])}")
            if tool.get("parameters"):
                print("    Parameters:")
                for param in tool["parameters"]:
                    name = param.get("name", "Unknown")
                    ptype = param.get("type", "unknown")
                    desc = param.get("description", "No description")
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
        with open(config_path) as f:
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


def validate_command(args):
    """Handle the validate command."""
    config_file = Path(args.config_file)

    if not config_file.exists():
        print(f"❌ Error: Configuration file does not exist: {config_file}")
        sys.exit(1)

    print(f"Validating configuration: {config_file}")

    try:
        # Validate the configuration
        result = validate_config_file(config_file)

        # Print results
        print_validation_results(result, verbose=args.verbose)

        # Exit with appropriate code
        if not result.is_valid:
            sys.exit(1)

    except Exception as e:
        print(f"❌ Error during validation: {e}")
        sys.exit(1)


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="MCPify - Automatically detect APIs and generate MCP server configurations"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Detect command
    detect_parser = subparsers.add_parser("detect", help="Detect API from project")
    detect_parser.add_argument("project_path", help="Path to the project directory")
    detect_parser.add_argument(
        "--output", "-o", help="Output file path (default: <project-name>.json)"
    )
    detect_parser.add_argument(
        "--openai-key", help="OpenAI API key for enhanced analysis"
    )

    # Validate command
    validate_parser = subparsers.add_parser(
        "validate", help="Validate MCP configuration file"
    )
    validate_parser.add_argument(
        "config_file", help="Path to the configuration file to validate"
    )
    validate_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show detailed validation results"
    )

    args = parser.parse_args()

    if args.command == "detect":
        detect_command(args)
    elif args.command == "view":
        view_command(args.config)
    elif args.command == "start":
        start_command(args.config)
    elif args.command == "validate":
        validate_command(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
