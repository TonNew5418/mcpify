#!/usr/bin/env python3
"""
Universal MCP tool wrapper - supports multiple backend program types
"""

import asyncio
import concurrent.futures
import inspect
import json
import subprocess
from collections.abc import Callable
from typing import Any

from mcp.server.fastmcp import FastMCP

from .backend import create_adapter


class MCPWrapper:
    """MCP server wrapper"""

    def __init__(self, config_path: str):
        self.config_path = config_path
        with open(config_path) as f:
            self.config = json.load(f)

        server_name = self.config.get("name", "tool-wrapper")
        self.mcp = FastMCP(server_name)

        # Check if backend configuration exists
        if "backend" in self.config:
            self.adapter = create_adapter(self.config["backend"])
        else:
            self.adapter = None

        self._register_tools()

    def get_python_type(self, type_str: str) -> type:
        """Convert string type to Python type"""
        type_mapping = {
            "string": str,
            "str": str,
            "int": int,
            "integer": int,
            "float": float,
            "number": float,
            "bool": bool,
            "boolean": bool,
        }
        return type_mapping.get(type_str.lower(), str)

    def create_tool_function(self, tool_config: dict[str, Any]) -> Callable:
        """Dynamically create tool function"""
        tool_name = tool_config["name"]
        parameters = tool_config.get("parameters", [])

        def tool_executor(**kwargs):
            """Generic function to execute tools"""
            if self.adapter:
                # Use adapter to execute tool
                def run_async_in_thread():
                    """Run async code in new thread"""
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        return loop.run_until_complete(
                            self.adapter.execute_tool(tool_config, kwargs)
                        )
                    finally:
                        loop.close()

                # Use thread pool to execute async operation
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_async_in_thread)
                    try:
                        result = future.result(timeout=30)  # 30 second timeout
                        return result
                    except concurrent.futures.TimeoutError:
                        return "Error: Tool execution timed out"
                    except Exception as e:
                        return f"Error executing tool: {str(e)}"
            else:
                # Use simple command line execution (backward compatibility)
                # This requires a command to be specified in the config
                command = self.config.get("command")
                if not command:
                    return (
                        "Error: No backend adapter configured and no command "
                        "specified"
                    )

                args_template = tool_config.get("args", [])
                cmd_args = []
                for arg in args_template:
                    if arg.startswith("{") and arg.endswith("}"):
                        param_name = arg.strip("{}")
                        value = kwargs.get(param_name, "")
                        cmd_args.append(str(value))
                    else:
                        cmd_args.append(arg)

                result = subprocess.run(
                    [command] + cmd_args, capture_output=True, text=True, cwd="."
                )

                if result.returncode != 0:
                    return f"Error: {result.stderr.strip()}"
                return result.stdout.strip()

        # Set function name
        tool_executor.__name__ = tool_name
        tool_executor.__qualname__ = tool_name

        # Dynamically create function signature
        if parameters:
            # Create parameter list
            sig_params = []
            annotations = {}

            for param in parameters:
                param_name = param["name"]
                param_type = self.get_python_type(param["type"])

                # Create parameter object
                sig_param = inspect.Parameter(
                    param_name,
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=param_type,
                )
                sig_params.append(sig_param)
                annotations[param_name] = param_type

            # Set return type annotation
            annotations["return"] = str
            tool_executor.__annotations__ = annotations

            # Create new function signature
            new_signature = inspect.Signature(sig_params)
            tool_executor.__signature__ = new_signature
        else:
            # Function with no parameters
            tool_executor.__annotations__ = {"return": str}
            tool_executor.__signature__ = inspect.Signature([])

        return tool_executor

    def _register_tools(self):
        """Register all tools to MCP server"""
        for tool in self.config.get("tools", []):
            tool_name = tool["name"]
            tool_description = tool["description"]

            # Create tool function
            tool_func = self.create_tool_function(tool)

            # Register to MCP
            self.mcp.tool(name=tool_name, description=tool_description)(tool_func)

    async def start_backend(self):
        """Start backend service"""
        if self.adapter:
            await self.adapter.start()

    async def stop_backend(self):
        """Stop backend service"""
        if self.adapter:
            await self.adapter.stop()

    def server(self):
        """Run MCP server"""
        return self.mcp

    def run(self):
        """Start MCP server"""
        # If adapter exists, start backend service first
        if self.adapter:
            asyncio.run(self.start_backend())

        try:
            self.mcp.run()
        finally:
            # Clean up resources
            if self.adapter:
                asyncio.run(self.stop_backend())
