# MCPify - Export all projects as MCP servers!

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**MCPify** is a powerful tool that automatically detects APIs in existing projects and transforms them into [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) servers. This enables seamless integration of your existing command-line tools, web APIs, and applications with AI assistants and other MCP-compatible clients.

## 🚀 Features

- **Automatic API Detection**: Analyze existing projects and extract their API structure
  - **CLI Tools**: Detect argparse-based command-line interfaces
  - **Web APIs**: Support for Flask and FastAPI applications with route detection
  - **Interactive Commands**: Identify command-based interactive applications
- **Flexible MCP Server**: Multiple ways to start and control MCP servers
- **Multiple Backend Support**: Works with command-line tools, HTTP APIs, Python modules, and more
- **Configuration Validation**: Built-in validation system to ensure correct configurations
- **Parameter Detection**: Automatically extract route parameters, query parameters, and CLI arguments
- **Zero Code Changes**: Transform existing projects without modifying their source code
- **Professional Architecture**: Clean separation between detection, configuration, and server execution

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

## 🏗️ Project Architecture

```
mcpify/
├── mcpify/                    # Core package
│   ├── cli.py                 # CLI interface (mcpify command)
│   ├── __main__.py            # Module entry point
│   ├── wrapper.py             # MCP protocol wrapper
│   ├── backend.py             # Backend adapters
│   ├── detect.py              # API detection engine
│   └── validate.py            # Configuration validation
├── bin/                       # Standalone executables
│   └── mcp-serve              # Independent server script
├── examples/                  # Example configurations
│   ├── fastapi-example.json
│   ├── python-module-example.json
│   └── commandline-example.json
├── docs/                      # Documentation
│   └── usage.md               # Detailed usage guide
└── tests/                     # Test suite
```

## 🛠️ Quick Start

### 1. Detect APIs in your project

```bash
mcpify detect /path/to/your/project --output config.json
```

This analyzes your project and generates a configuration file containing the detected API structure.

### 2. View and validate the configuration

```bash
mcpify view config.json
mcpify validate config.json
```

This validates the generated configuration and shows any warnings or errors.

### 3. Start the MCP server

MCPify provides multiple ways to start MCP servers:

```bash
# Method 1: Using mcpify CLI
mcpify serve config.json

# Method 2: Using standalone mcp-serve script (recommended for MCP clients)
./bin/mcp-serve config.json

# Method 3: Direct module invocation
python -m mcpify serve config.json

# HTTP mode for web integration
./bin/mcp-serve config.json --mode streamable-http --port 8080
```

## 🎯 Usage Scenarios

### For Developers (API Detection & Testing)
```bash
# Detect and test your APIs
mcpify detect my-project --output my-project.json
mcpify view my-project.json
mcpify serve my-project.json
```

### For MCP Clients (Server Integration)
```bash
# MCP clients can start servers directly
./bin/mcp-serve config.json                    # stdio mode
./bin/mcp-serve config.json --mode streamable-http  # HTTP mode
```

### For Production Deployment
```bash
# Deploy as HTTP server
./bin/mcp-serve config.json --mode streamable-http --host 0.0.0.0 --port 8080
```

## 📋 Backend Types & Examples

### FastAPI/Flask Web Applications
```json
{
  "name": "my-web-api",
  "description": "Web API server",
  "backend": {
    "type": "fastapi",
    "base_url": "http://localhost:8000"
  },
  "tools": [
    {
      "name": "get_user",
      "description": "Get user information",
      "endpoint": "/users/{user_id}",
      "method": "GET",
      "parameters": [
        {
          "name": "user_id",
          "type": "string",
          "description": "User ID"
        }
      ]
    }
  ]
}
```

### Python Modules
```json
{
  "name": "my-python-tools",
  "description": "Python module backend",
  "backend": {
    "type": "python",
    "module_path": "./my_module.py"
  },
  "tools": [
    {
      "name": "calculate",
      "description": "Perform calculation",
      "function": "calculate",
      "parameters": [
        {
          "name": "expression",
          "type": "string",
          "description": "Mathematical expression"
        }
      ]
    }
  ]
}
```

### Command-Line Tools
```json
{
  "name": "my-cli-tool",
  "description": "Command line tool backend",
  "backend": {
    "type": "commandline",
    "config": {
      "command": "python3",
      "args": ["./my_script.py"],
      "cwd": "."
    }
  },
  "tools": [
    {
      "name": "process_data",
      "description": "Process data with CLI tool",
      "args": ["--process", "{input_file}"],
      "parameters": [
        {
          "name": "input_file",
          "type": "string",
          "description": "Input file path"
        }
      ]
    }
  ]
}
```

## 🔧 Configuration

### Supported Backend Types
- **`fastapi`**: FastAPI web applications
- **`python`**: Python modules and functions
- **`commandline`**: Command-line tools and scripts
- **`external`**: External programs and services

### Server Modes
- **`stdio`**: Standard input/output (default MCP mode)
- **`streamable-http`**: HTTP Server-Sent Events mode

### Parameter Types
- `string`, `integer`, `number`, `boolean`, `array`
- Automatic type detection from source code
- Custom validation rules

## 📁 Examples

Explore the `examples/` directory for ready-to-use configurations:

```bash
# View example configurations
mcpify view examples/fastapi-example.json
mcpify view examples/python-module-example.json
mcpify view examples/commandline-example.json

# Test with examples
./bin/mcp-serve examples/fastapi-example.json
```

## 🧪 Development

### Running Tests
```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=mcpify --cov-report=html

# Run specific tests
python -m pytest tests/test_detect.py -v
```

### Development Setup
```bash
git clone https://github.com/your-username/mcpify.git
cd mcpify
pip install -e ".[dev]"
python -m pytest tests/ -v
```

### Available Commands

#### MCPify CLI Commands
```bash
mcpify detect <project_path> [--output <file>]    # Detect APIs
mcpify view <config_file>                         # View configuration
mcpify validate <config_file>                     # Validate configuration
mcpify serve <config_file> [--mode <mode>]        # Start server
```

#### MCP Server Commands
```bash
./bin/mcp-serve <config_file>                          # Start stdio server
./bin/mcp-serve <config_file> --mode streamable-http   # Start HTTP server
./bin/mcp-serve <config_file> --host <host> --port <port>  # Custom host/port
```

## 🚀 Deployment Options

### 1. Package Installation
```bash
pip install mcpify
# Use mcpify for development, copy bin/mcp-serve for production
```

### 2. Standalone Script
```bash
# Copy standalone script
cp bin/mcp-serve /usr/local/bin/
chmod +x /usr/local/bin/mcp-serve
mcp-serve config.json
```

### 3. Docker Deployment
```dockerfile
FROM python:3.10-slim
COPY . /app
WORKDIR /app
RUN pip install .
CMD ["./bin/mcp-serve", "config.json", "--mode", "streamable-http", "--host", "0.0.0.0"]
```

## 🤝 Contributing

We welcome contributions! Please see our development setup above and:

- Fork the repository
- Create a feature branch
- Add tests for new functionality
- Submit a pull request

### Code Quality
```bash
# Linting and formatting
ruff check mcpify/
ruff format mcpify/

# Type checking
mypy mcpify/
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Related Projects

- [Model Context Protocol](https://modelcontextprotocol.io/) - The protocol specification
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) - Official Python implementation

## 📞 Support

- **Documentation**: See `docs/usage.md` for detailed usage instructions
- **Examples**: Check the `examples/` directory for configuration templates
- **Issues**: [GitHub Issues](https://github.com/your-username/mcpify/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-username/mcpify/discussions)
