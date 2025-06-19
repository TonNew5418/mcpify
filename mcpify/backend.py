#!/usr/bin/env python3
"""
Backend adapter module - supports multiple backend program types
"""

import asyncio
import subprocess
import time
from abc import ABC, abstractmethod
from typing import Any

import aiohttp


class BackendAdapter(ABC):
    """Backend program adapter base class"""

    @abstractmethod
    async def execute_tool(self, tool_config: dict[str, Any], parameters: Any) -> str:
        """Execute tool call"""
        pass

    @abstractmethod
    async def start(self) -> None:
        """Start backend program"""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop backend program"""
        pass


class CommandLineAdapter(BackendAdapter):
    """Command line program adapter"""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.command = config["command"]
        self.base_args = config.get("args", [])
        self.cwd = config.get("cwd", ".")

    async def start(self) -> None:
        """Command line programs don't need startup"""
        pass

    async def stop(self) -> None:
        """Command line programs don't need shutdown"""
        pass

    async def execute_tool(self, tool_config: dict[str, Any], parameters: Any) -> str:
        """Execute command line tool"""
        cmd_args = []
        args_template = tool_config.get("args", [])

        for arg in args_template:
            if arg.startswith("{") and arg.endswith("}"):
                param_name = arg.strip("{}")
                value = parameters.get(param_name, "")
                cmd_args.append(str(value))
            else:
                cmd_args.append(arg)

        full_command = [self.command] + self.base_args + cmd_args

        result = subprocess.run(
            full_command, capture_output=True, text=True, cwd=self.cwd
        )

        if result.returncode != 0:
            return f"Error: {result.stderr.strip()}"
        return result.stdout.strip()


class ServerAdapter(BackendAdapter):
    """Server program adapter"""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.command = config["command"]
        self.args = config.get("args", [])
        self.cwd = config.get("cwd", ".")
        self.startup_timeout = config.get("startup_timeout", 5)
        self.ready_signal = config.get("ready_signal", "")
        self.process: subprocess.Popen | None = None
        self.ready = False
        self.lock = asyncio.Lock()

    async def start(self) -> None:
        """Start server program"""
        if self.process is not None:
            return

        print(f"🚀 Starting server: {self.command} {' '.join(self.args)}")

        self.process = subprocess.Popen(
            [self.command] + self.args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=self.cwd,
            bufsize=0,
        )

        # Wait for server to be ready
        if self.ready_signal:
            await self._wait_for_ready()
        else:
            await asyncio.sleep(1)  # Default wait 1 second

        print("✅ Server startup complete")

    async def _wait_for_ready(self) -> None:
        """Wait for server ready signal"""
        if self.process is None:
            raise RuntimeError("Server process is not started")

        start_time = time.time()

        while time.time() - start_time < self.startup_timeout:
            if self.process.poll() is not None:
                if self.process.stderr is not None:
                    stderr = self.process.stderr.read()
                else:
                    raise RuntimeError("Process stderr is not available")
                raise RuntimeError(f"Server startup failed: {stderr}")

            # Non-blocking read output
            try:
                if self.process.stdout is not None:
                    line = self.process.stdout.readline()
                    if line and self.ready_signal in line:
                        self.ready = True
                        return
                else:
                    raise RuntimeError("Process stdout is not available")
            except Exception:
                pass

            await asyncio.sleep(0.1)

        raise TimeoutError(f"Server startup timeout ({self.startup_timeout}s)")

    async def stop(self) -> None:
        """Stop server program"""
        if self.process is None:
            return

        print("🛑 Stopping server...")

        try:
            if self.process.stdin is not None:
                # Send quit command
                self.process.stdin.write("quit\n")
                self.process.stdin.flush()

                # Wait for process to end
                try:
                    self.process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.process.terminate()
                    self.process.wait(timeout=3)
            else:
                raise RuntimeError(
                    "Process stdin is not available for sending quit command"
                )
        except Exception:
            if self.process.poll() is None:
                self.process.kill()

        self.process = None
        self.ready = False
        print("✅ Server stopped")

    async def execute_tool(self, tool_config: dict[str, Any], parameters: Any) -> str:
        """Execute server tool"""
        if not self.ready or self.process is None:
            await self.start()

        async with self.lock:
            command_template = tool_config.get("command", "")

            # Replace parameters
            command = command_template
            for param_name, value in parameters.items():
                command = command.replace(f"{{{param_name}}}", str(value))

            try:
                if self.process is None:
                    raise RuntimeError("Server process is not running")

                if self.process.stdin is not None:
                    # Send command
                    self.process.stdin.write(f"{command}\n")
                    self.process.stdin.flush()
                else:
                    raise RuntimeError(
                        "Process stdin is not available for sending commands"
                    )

                if self.process.stdout is not None:
                    # Read response
                    response: str = self.process.stdout.readline().strip()
                    return response
                else:
                    raise RuntimeError(
                        "Process stdout is not available for reading response"
                    )

            except Exception as e:
                return f"Error communicating with server: {str(e)}"


class HttpAdapter(BackendAdapter):
    """HTTP API adapter"""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.base_url = config["base_url"]
        self.timeout = config.get("timeout", 10)
        self.headers = config.get("headers", {})
        self.session: aiohttp.ClientSession | None = None

    async def start(self) -> None:
        """Start HTTP session"""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(timeout=timeout, headers=self.headers)
            print(f"🌐 HTTP session started: {self.base_url}")

    async def stop(self) -> None:
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None
            print("🌐 HTTP session closed")

    async def execute_tool(self, tool_config: dict[str, Any], parameters: Any) -> str:
        """Execute HTTP API call"""
        if self.session is None:
            await self.start()

        endpoint = tool_config.get("endpoint", "/")
        method = tool_config.get("method", "GET").upper()

        url = f"{self.base_url}{endpoint}"

        try:
            result: str
            if self.session is None:
                raise RuntimeError("HTTP session is not started")

            if method == "GET":
                # GET request uses parameters as query parameters
                async with self.session.get(url, params=parameters) as response:
                    result = await response.text()
                    if response.status >= 400:
                        return f"HTTP Error {response.status}: {result}"
                    return result

            elif method == "POST":
                # POST request uses parameters as JSON body
                async with self.session.post(url, json=parameters) as response:
                    result = await response.text()
                    if response.status >= 400:
                        return f"HTTP Error {response.status}: {result}"
                    return result

            elif method == "PUT":
                async with self.session.put(url, json=parameters) as response:
                    result = await response.text()
                    if response.status >= 400:
                        return f"HTTP Error {response.status}: {result}"
                    return result

            elif method == "DELETE":
                async with self.session.delete(url, params=parameters) as response:
                    result = await response.text()
                    if response.status >= 400:
                        return f"HTTP Error {response.status}: {result}"
                    return result

            else:
                return f"Unsupported HTTP method: {method}"

        except Exception as e:
            return f"HTTP request failed: {str(e)}"


def create_adapter(backend_config: dict[str, Any]) -> BackendAdapter:
    """Create adapter based on configuration"""
    backend_type = backend_config["type"]
    config = backend_config["config"]

    if backend_type == "commandline":
        return CommandLineAdapter(config)
    elif backend_type == "server":
        return ServerAdapter(config)
    elif backend_type == "http":
        return HttpAdapter(config)
    else:
        raise ValueError(f"Unsupported backend type: {backend_type}")
