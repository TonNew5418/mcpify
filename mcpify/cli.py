"""Command line interface for MCPify."""

import argparse
import json
import sys
from pathlib import Path

from .detect import detect_project_api
from .validate import print_validation_results, validate_config_file
from .wrapper import MCPWrapper


def detect_command(args) -> None:
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
        backend_type = config.get("backend", {}).get("type", "unknown")
        print(f"🔧 Project type: {backend_type}")

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


def view_command(args) -> None:
    """Visually display the API specification."""
    config_file = Path(args.config_file)

    if not config_file.exists():
        print(f"❌ Error: Configuration file does not exist: {config_file}")
        sys.exit(1)

    print(f"Viewing configuration: {config_file}")

    try:
        with open(config_file, encoding="utf-8") as f:
            config = json.load(f)

        print(f"\n📋 API Specification: {config.get('name', 'Unknown')}")
        print(f"📝 Description: {config.get('description', 'No description')}")

        # Show backend information
        backend = config.get("backend", {})
        backend_type = backend.get("type", "unknown")
        print(f"🔧 Backend Type: {backend_type}")

        print(f"\n🛠️  Tools ({len(config.get('tools', []))}):")

        for tool in config.get("tools", []):
            print(f"  • {tool.get('name', 'Unknown')}")
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

        # Validate the configuration and show results
        from .validate import print_validation_results, validate_config_dict

        result = validate_config_dict(config)
        print("📊 Validation Results:")
        print_validation_results(result, verbose=args.verbose)

    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in config file: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error viewing configuration: {e}")
        sys.exit(1)


def serve_command(args) -> None:
    """Serve MCP server directly."""
    config_file = Path(args.config_file)

    if not config_file.exists():
        print(f"❌ Error: Configuration file does not exist: {config_file}")
        sys.exit(1)

    try:
        with open(config_file, encoding="utf-8") as f:
            config = json.load(f)

        # Direct serve mode
        print(f"🚀 Starting MCP server for {config.get('name', 'Unknown')}...")
        print(f"📡 Mode: {args.mode}")

        wrapper = MCPWrapper(str(config_file))

        if args.mode == "stdio":
            # Use existing wrapper for stdio mode
            wrapper.run()
        elif args.mode == "streamable-http":
            # Use wrapper with HTTP mode
            mcp_server = wrapper.server()

            # Start backend if needed
            if wrapper.adapter:
                import asyncio

                asyncio.run(wrapper.start_backend())

            try:
                mcp_server.run(transport="sse", host=args.host, port=args.port)
            finally:
                if wrapper.adapter:
                    import asyncio

                    asyncio.run(wrapper.stop_backend())
        else:
            print(f"❌ Error: Unsupported mode '{args.mode}'")
            sys.exit(1)

    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in config file: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n🛑 Server stopped.")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)


def validate_command(args) -> None:
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
        description=(
            "MCPify - Automatically detect APIs and generate "
            "MCP server configurations"
        )
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

    # View command
    view_parser = subparsers.add_parser(
        "view", help="View and validate MCP configuration file"
    )
    view_parser.add_argument(
        "config_file", help="Path to the configuration file to view"
    )
    view_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show detailed validation results"
    )

    # Serve command
    serve_parser = subparsers.add_parser("serve", help="Start MCP server")
    serve_parser.add_argument("config_file", help="Path to the configuration file")
    serve_parser.add_argument(
        "--mode",
        choices=["stdio", "streamable-http"],
        default="stdio",
        help="Server mode (default: stdio)",
    )
    serve_parser.add_argument(
        "--host", default="localhost", help="Host for HTTP mode (default: localhost)"
    )
    serve_parser.add_argument(
        "--port", type=int, default=8080, help="Port for HTTP mode (default: 8080)"
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
        view_command(args)
    elif args.command == "serve":
        serve_command(args)
    elif args.command == "validate":
        validate_command(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
