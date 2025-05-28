# MCPify

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**MCPify** is a powerful tool that automatically detects APIs in existing projects and transforms them into [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) servers. This enables seamless integration of your existing command-line tools, scripts, and applications with AI assistants and other MCP-compatible clients.

## 🚀 Features

- **Automatic API Detection**: Analyze existing projects and extract their API structure
- **MCP Server Generation**: Convert any project into a fully functional MCP server
- **Multiple Backend Support**: Works with command-line tools, Python scripts, and more
- **Visual API Inspection**: Preview and validate your API specifications before deployment
- **Zero Code Changes**: Transform existing projects without modifying their source code
- **Flexible Configuration**: Fine-tune tool definitions and parameters through JSON configuration

## 📦 Installation

### Using pip (recommended)

```bash
pip install mcpify
```

### From source

```bash
git clone https://github.com/your-username/mcpify.git
cd mcpify
pip install -e .
```

## 🛠️ Quick Start

### 1. Detect APIs in your project

```bash
mcpify detect /path/to/your/project
```

This will analyze your project and generate a `project-name.json` configuration file containing the detected API structure.

### 2. Preview the API specification

```bash
mcpify view project-name.json
```

This displays a human-readable overview of the detected tools and their parameters.

### 3. Start the MCP server

```bash
mcpify start project-name.json
```

Your project is now running as an MCP server, ready to be used by AI assistants and other MCP clients!

## 📋 Usage Examples

### Command-Line Tool Integration

Suppose you have a Python CLI tool with the following interface:

```bash
python my-tool.py --hello
python my-tool.py --echo "Hello World"
python my-tool.py --add 5.5 3.2
```

MCPify can automatically detect this structure and create an MCP server that exposes these commands as tools:

```json
{
  "backend": {
    "type": "commandline",
    "config": {
      "command": "python3",
      "args": ["/path/to/my-tool.py"],
      "cwd": "."
    }
  },
  "tools": [
    {
      "name": "say_hello",
      "description": "Prints a greeting message",
      "args": ["--hello"],
      "parameters": []
    },
    {
      "name": "echo_message",
      "description": "Echo the input message",
      "args": ["--echo", "{message}"],
      "parameters": [
        {
          "name": "message",
          "type": "string",
          "description": "The message to echo"
        }
      ]
    },
    {
      "name": "add_numbers",
      "description": "Add two numbers together",
      "args": ["--add", "{num1}", "{num2}"],
      "parameters": [
        {
          "name": "num1",
          "type": "float",
          "description": "The first number to add"
        },
        {
          "name": "num2",
          "type": "float",
          "description": "The second number to add"
        }
      ]
    }
  ]
}
```

### Testing Your MCP Server

You can test your MCPify server using the MCP client libraries:

```python
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_mcpify():
    server_params = StdioServerParameters(
        command="mcpify",
        args=["start", "my-project.json"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # List available tools
            tools = await session.list_tools()
            print("Available tools:", [tool.name for tool in tools.tools])
            
            # Call a tool
            result = await session.call_tool("echo_message", {
                "message": "Hello from MCP!"
            })
            print("Result:", result.content)

asyncio.run(test_mcpify())
```

## 🔧 Configuration

MCPify uses JSON configuration files to define how your project should be exposed as an MCP server. The configuration includes:

### Backend Configuration

- **type**: The type of backend (`commandline`, `http`, etc.)
- **config**: Backend-specific configuration (command, arguments, working directory, etc.)

### Tool Definitions

- **name**: Unique identifier for the tool
- **description**: Human-readable description of what the tool does
- **args**: Command-line arguments template with parameter placeholders
- **parameters**: List of input parameters with types and descriptions

### Parameter Types

MCPify supports various parameter types:

- `string`: Text input
- `float`/`number`: Numeric input
- `integer`: Whole number input
- `boolean`: True/false values
- `array`: List of values

## 🏗️ Architecture

MCPify consists of several key components:

- **CLI Interface**: Command-line tool for detection, viewing, and server management
- **Backend Abstraction**: Pluggable backend system supporting different execution environments
- **MCP Wrapper**: Translates MCP protocol calls to backend-specific operations
- **Configuration Engine**: Manages API specifications and tool definitions

## 🧪 Development

### Running Tests

```bash
# Run all tests
python run_tests.py --all

# Run specific test types
python run_tests.py --unittest
python run_tests.py --pytest
python run_tests.py --coverage
python run_tests.py --lint
```

### Project Structure

```
mcpify/
├── mcpify/           # Main package
│   ├── cli.py        # Command-line interface
│   ├── backend.py    # Backend abstraction layer
│   ├── wrapper.py    # MCP protocol wrapper
│   └── __init__.py
├── tests/            # Test suite
├── example-projects/ # Example configurations
├── README.md
└── pyproject.toml
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details on:

- Setting up the development environment
- Running tests and linting
- Submitting pull requests
- Reporting issues

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Related Projects

- [Model Context Protocol](https://modelcontextprotocol.io/) - The protocol specification
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) - Official Python implementation

## 📞 Support

- **Documentation**: [Full documentation](https://mcpify.readthedocs.io/)
- **Issues**: [GitHub Issues](https://github.com/your-username/mcpify/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-username/mcpify/discussions)

---

Made with ❤️ by the MCPify team


