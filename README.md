# MCPify - Export all projects as MCP servers!

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**MCPify** is a powerful tool that automatically detects APIs in existing projects and transforms them into [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) servers. This enables seamless integration of your existing command-line tools, web APIs, and applications with AI assistants and other MCP-compatible clients.

## 🚀 Features

- **Automatic API Detection**: Analyze existing projects and extract their API structure
  - **CLI Tools**: Detect argparse-based command-line interfaces
  - **Web APIs**: Support for Flask and FastAPI applications with route detection
  - **Interactive Commands**: Identify command-based interactive applications
- **MCP Server Generation**: Convert any project into a fully functional MCP server
- **Multiple Backend Support**: Works with command-line tools, HTTP APIs, and more
- **Configuration Validation**: Built-in validation system to ensure correct configurations
- **Parameter Detection**: Automatically extract route parameters, query parameters, and CLI arguments
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

### 2. View the configuration

```bash
mcpify view project-name.json
```

This validates the generated configuration and shows any warnings or errors.

### 3. Start the MCP server

```bash
mcpify start project-name.json
```

Your project is now running as an MCP server, ready to be used by AI assistants and other MCP clients!

## 📋 Usage Examples

### Command-Line Tool Integration

For CLI tools with argparse:

```python
# cli_tool.py
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--hello', action='store_true', help='Say hello')
    parser.add_argument('--echo', type=str, help='Echo a message')
    parser.add_argument('--add', nargs=2, type=float, help='Add two numbers')
    args = parser.parse_args()

    if args.hello:
        print("Hello!")
    elif args.echo:
        print(f"Echo: {args.echo}")
    elif args.add:
        print(f"Result: {args.add[0] + args.add[1]}")
```

MCPify automatically generates:
```json
{
  "backend": {
    "type": "commandline",
    "config": {
      "command": "python3",
      "args": ["cli_tool.py"],
      "cwd": "."
    }
  },
  "tools": [
    {
      "name": "hello",
      "description": "Say hello",
      "args": ["--hello"],
      "parameters": []
    },
    {
      "name": "echo",
      "description": "Echo a message",
      "args": ["--echo", "{message}"],
      "parameters": [
        {
          "name": "message",
          "type": "string",
          "description": "The message value"
        }
      ]
    }
  ]
}
```

### Interactive Command Applications

MCPify can detect interactive command-based applications:

```python
# server.py
def main():
    while True:
        line = input()
        if line.lower() == 'hello':
            print("Hello there!")
        elif line.lower().startswith('echo '):
            message = line[5:]
            print(f"Echo: {message}")
        elif line.lower() == 'quit':
            break
```

Detected commands:
- `hello` - Simple command
- `echo` - Command with message parameter

### FastAPI Application

MCPify can automatically detect FastAPI applications and their endpoints:

```python
# main.py
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/todos/{todo_id}")
async def get_todo(todo_id: int):
    return {"id": todo_id, "title": "Sample todo"}

@app.post("/todos")
async def create_todo(todo: dict):
    return {"id": 1, **todo}
```

MCPify will detect:
- Route parameters (`{todo_id}`)
- HTTP methods (GET, POST, PUT, DELETE, PATCH)
- Query parameters
- Proper parameter types

Generated configuration:
```json
{
  "name": "fastapi-app",
  "description": "FastAPI application",
  "backend": {
    "type": "http",
    "config": {
      "base_url": "http://localhost:8000",
      "timeout": 30
    }
  },
  "tools": [
    {
      "name": "root",
      "description": "GET / endpoint",
      "args": ["/"],
      "parameters": []
    },
    {
      "name": "get_todo",
      "description": "GET /todos/{todo_id} endpoint",
      "args": ["/todos/{todo_id}", "{todo_id}"],
      "parameters": [
        {
          "name": "todo_id",
          "type": "integer",
          "description": "The todo_id parameter"
        }
      ]
    }
  ]
}
```


## 🔧 Configuration

MCPify uses JSON configuration files to define how your project should be exposed as an MCP server.

### Backend Types

- **commandline**: Execute command-line tools
- **http**: Call HTTP REST APIs
- **websocket**: Connect to WebSocket endpoints

### Parameter Types

MCPify supports various parameter types:
- `string`: Text input
- `integer`: Whole number input
- `number`/`float`: Numeric input
- `boolean`: True/false values
- `array`: List of values

### Validation

The built-in validation system checks:
- Required fields presence
- Parameter type consistency
- Backend configuration validity
- Tool name uniqueness
- Parameter usage in arguments

## 📁 Example Projects

The repository includes several example projects:

### FastAPI Todo Server
```bash
cd example-projects/fastapi-todo-server
uvicorn main:app --reload
# In another terminal:
mcpify detect . --output todo-api.json
mcpify validate todo-api.json
```

Features:
- Complete CRUD API for todo management
- Path parameters (`{todo_id}`)
- Query parameters for filtering
- Automatic OpenAPI documentation

### Python Server Project
```bash
cd example-projects/python-server-project
python server.py &
mcpify detect . --output server-api.json
```

Features:
- Interactive command processing
- Simple text-based protocol
- Multiple command types

## 🧪 Development

### Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=mcpify --cov-report=html

# Run specific test files
python -m pytest tests/test_detect.py tests/test_validate.py -v
```

### Project Structure

```
mcpify/
├── mcpify/           # Main package
│   ├── cli.py        # Command-line interface
│   ├── detect.py     # API detection engine
│   ├── validate.py   # Configuration validation
│   ├── backend.py    # Backend abstraction layer
│   ├── wrapper.py    # MCP protocol wrapper
│   └── __init__.py
├── tests/            # Test suite
│   ├── test_detect.py
│   ├── test_validate.py
│   └── __init__.py
├── example-projects/ # Example configurations
│   ├── fastapi-todo-server/
│   └── python-server-project/
├── README.md
└── pyproject.toml
```

### Available Commands

```bash
# Detect APIs in a project
mcpify detect <project_path> [--output <file>] [--openai-key <key>]

# Validate a configuration file
mcpify validate <config_file> [--verbose]

# Start an MCP server (coming soon)
mcpify start <config_file>
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details on:

- Setting up the development environment
- Running tests and linting
- Submitting pull requests
- Reporting issues

### Development Setup

```bash
git clone https://github.com/your-username/mcpify.git
cd mcpify
pip install -e ".[dev]"
python -m pytest tests/ -v
```

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
