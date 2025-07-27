# MCPify

Transform any Git repository into intelligent MCP tools automatically.

MCPify analyzes code repositories and generates Model Context Protocol (MCP) servers that expose repository functionality as callable tools. Simply provide a GitHub URL, describe what APIs you need, and MCPify will create a ready-to-use MCP server.

## Quick Start

```bash
# Install MCPify
pip install mcpify

# Transform a repository into MCP tools
mcpify https://github.com/sqlite/sqlite --api "database creation and query operations"

# The generated MCP server is now ready to use with any MCP client
```

## What MCPify Does

**Input**: GitHub/Git repository URL + API requirements description
**Output**: Running MCP server with callable tools

### Process Flow

1. **Repository Analysis**: Clone and analyze the target repository
2. **Project Understanding**: Extract dependencies, entry points, documentation
3. **API Design**: Use AI to understand your requirements and map them to code
4. **MCP Generation**: Create tools with proper schemas and implementations
5. **Server Launch**: Start the MCP server ready for integration

## Architecture

```
Git Repository -> Static Analysis -> Semantic Layer -> Code Generator -> MCP Server Runtime -> UX Layer
```

Components:
- **Ingestion**: Repository cloning and metadata extraction
- **Analysis**: AST parsing, symbol graphs, documentation extraction
- **Semantic**: LLM-powered code understanding and API design
- **Generation**: MCP server scaffolding and tool creation
- **Runtime**: Tool execution, subprocess management, security sandbox
- **Interface**: CLI, web UI, VSCode extension

## Features

### Current (MVP)
- **Multi-language support**: Python, JavaScript/TypeScript, Go, Rust
- **Intelligent analysis**: AST parsing + LLM-powered code understanding
- **Automatic tool generation**: Function signatures to MCP tool schemas
- **MCP SDK integration**: Official MCP SDK for guaranteed protocol compliance
- **Production ready**: Enterprise-grade servers with comprehensive error handling
- **Safe execution**: Sandboxed subprocess management with timeouts
- **Hot reload**: Dynamic tool updates without server restart

### Planned
- Interactive UI: Web interface and VSCode extension
- Advanced security: Fine-grained permissions and resource limits
- Caching: Incremental analysis and vector indexing
- Multi-repo: Composite tools across multiple repositories
- Monitoring: Execution metrics and error tracking

## Installation

### Prerequisites
- Python 3.8+
- Git
- Language-specific tools for target repositories (pip, npm, go, cargo, etc.)

### Install from PyPI
```bash
pip install mcpify
```

### Development Installation
```bash
git clone https://github.com/yourorg/mcpify
cd mcpify
pip install -e ".[dev]"
```

## Usage

### Basic Usage
```bash
# Transform a Python repository
mcpify analyze https://github.com/sqlite/sqlite --api "database operations"

# Transform with specific language hint
mcpify analyze https://github.com/expressjs/express --api "web server utilities"

# Custom output directory
mcpify analyze https://github.com/redis/redis --output ./my-redis-tools --api "key-value operations"
```

### Advanced Configuration
```bash
# Use Anthropic Claude instead of OpenAI
mcpify analyze ./repo --api "data processing" --llm anthropic

# Generate only, don't start server
mcpify analyze ./repo --api "file operations" --no-start --verbose

# Custom model and output
mcpify analyze ./repo --api "utilities" --model gpt-4 --output ./my-tools
```

### Generated MCP Server

MCPify generates production-ready MCP servers using the official MCP SDK, providing:

- **Full MCP protocol compliance**: Guaranteed compatibility with all MCP clients
- **Official SDK maintenance**: Automatic updates and new feature support
- **Rich error handling**: Comprehensive error reporting and type safety
- **Future-proof**: Support for upcoming MCP features (resources, prompts)

All generated servers use the latest MCP SDK for maximum reliability and compatibility.

### API Configuration Example
```yaml
# api-config.yaml
apis:
  - name: create_database
    description: "Create a SQLite database and return the path"
    impl:
      type: "python_function"
      module: "src/db/utils.py"
      function: "create_db"
    input_schema:
      type: object
      properties:
        path: {type: string}
      required: [path]

  - name: execute_query
    description: "Execute SQL query on database"
    impl:
      type: "python_function"
      module: "src/db/utils.py"
      function: "execute_sql"
    input_schema:
      type: object
      properties:
        db_path: {type: string}
        query: {type: string}
      required: [db_path, query]
```

## Development

### Project Structure
```
mcpify/
├── core/
│   ├── ingestion/       # Repository cloning and metadata
│   ├── analysis/        # Static analysis and AST parsing
│   ├── semantic/        # LLM-powered understanding
│   └── generation/      # MCP server generation
├── runners/             # Language-specific execution
├── security/           # Sandboxing and permissions
├── ui/                 # CLI and web interfaces
└── tests/              # Test suites
```

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=mcpify

# Run integration tests
pytest tests/integration/
```

### Development Roadmap

#### Phase 0: Technical Spike (Complete)
- Python repository support
- Basic AST parsing with tree-sitter
- Simple LLM-based API generation
- MVP MCP server generation

#### Phase 1: Multi-language Support (In Progress)
- JavaScript/TypeScript support
- Go and Rust support
- Robust build/run detection
- Universal subprocess runner

#### Phase 2: API Design & Security (Planned)
- DSL for API configuration
- Static analysis + runtime validation
- Sandboxing (nsjail, Docker, WASM)
- Permission management

#### Phase 3: Product Polish (Future)
- Web UI and VSCode extension
- Multi-repository caching
- Vector indexing for large codebases
- Monitoring and analytics

## Security

MCPify runs code analysis and execution with several security measures:

- **Sandboxed Execution**: All code runs in isolated environments
- **Resource Limits**: CPU, memory, and time constraints
- **Permission Controls**: Explicit user consent for potentially risky operations
- **Code Review**: Generated tools include source code references for inspection

### Supported Sandboxing
- Python: Virtual environments (venv/uv)
- Node.js: npm/pnpm isolation
- Docker: Container-based execution
- System: nsjail/firejail integration

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Quick Development Setup
```bash
git clone https://github.com/yourorg/mcpify
cd mcpify
pip install -e ".[dev]"
pre-commit install
pytest
```

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Model Context Protocol](https://github.com/modelcontextprotocol) for the MCP specification
- [tree-sitter](https://github.com/tree-sitter/tree-sitter) for language parsing
- [GitHub Linguist](https://github.com/github/linguist) for language detection

## Support

- Issue Tracker: https://github.com/camel-ai/mcpify/issues
- Discussions: https://github.com/camel-ai/mcpify/discussions
- Email: xiaotian.jin@eigent.ai
