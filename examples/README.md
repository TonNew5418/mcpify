# MCPify Configuration Examples

This directory contains example configuration files for different types of backends and use cases.

## Available Examples

### 1. FastAPI Backend (`fastapi-example.json`)
Example configuration for a FastAPI web application backend.
- **Backend Type**: `fastapi`
- **Use Case**: REST API servers, web applications
- **Features**: HTTP endpoints, automatic parameter validation

### 2. Python Module Backend (`python-module-example.json`)
Example configuration for a Python module/script backend.
- **Backend Type**: `python`
- **Use Case**: Python functions, data processing scripts
- **Features**: Direct function calls, Python-native integration

### 3. Command Line Tool Backend (`commandline-example.json`)
Example configuration for command-line tools and external programs.
- **Backend Type**: `commandline`
- **Use Case**: CLI tools, shell scripts, external executables
- **Features**: Process execution, argument templating

## Usage

To test any of these examples:

```bash
# View the configuration
mcpify view examples/fastapi-example.json

# Validate the configuration
mcpify validate examples/fastapi-example.json

# Start the server (make sure the backend is running first)
mcpify serve examples/fastapi-example.json

# Or use the standalone server
mcp-serve examples/fastapi-example.json
```

## Customization

These examples serve as templates. You can:

1. Copy an example that matches your backend type
2. Modify the backend configuration (URLs, paths, commands)
3. Update the tools section to match your API
4. Add or remove parameters as needed

## Backend Requirements

- **FastAPI**: Requires a running FastAPI server
- **Python**: Requires the Python module to be available
- **Command Line**: Requires the command/executable to be installed

For more detailed usage instructions, see `docs/usage.md`.
