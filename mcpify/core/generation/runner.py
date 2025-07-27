import subprocess
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import psutil

from ...models.repository import Repository
from ..analysis.detector import DependencyDetector


class MCPServerRunner:
    """Manage MCP server execution and lifecycle."""

    def __init__(self):
        self.dependency_detector = DependencyDetector()
        self.active_servers: Dict[str, subprocess.Popen] = {}

    def setup_and_run_server(
        self,
        repository: Repository,
        server_path: Path,
        venv_path: Optional[Path] = None,
        timeout: int = 300,
    ) -> Tuple[bool, str, Optional[subprocess.Popen]]:
        """Set up environment and run the MCP server."""

        try:
            # Create virtual environment if not provided
            if venv_path is None:
                venv_path = repository.local_path / ".mcpify_venv"

            if not venv_path.exists():
                print(f"Creating virtual environment at {venv_path}")
                success, message = self.dependency_detector.create_virtual_environment(
                    repository, venv_path
                )
                if not success:
                    return (
                        False,
                        f"Failed to create virtual environment: {message}",
                        None,
                    )
                print(f"Virtual environment created: {message}")

            # Start the server
            process = self._start_server_process(
                server_path, venv_path, repository.local_path
            )

            if process is None:
                return False, "Failed to start server process", None

            # Wait a moment and check if process is still running
            time.sleep(2)
            if process.poll() is not None:
                stderr_output = (
                    process.stderr.read() if process.stderr else "No error output"
                )
                return (
                    False,
                    f"Server process exited immediately. Error: {stderr_output}",
                    None,
                )

            # Register the server
            server_id = f"{repository.name}_{int(time.time())}"
            self.active_servers[server_id] = process

            return (
                True,
                f"MCP server started successfully (PID: {process.pid})",
                process,
            )

        except Exception as e:
            return False, f"Error setting up server: {e}", None

    def _start_server_process(
        self, server_path: Path, venv_path: Path, working_dir: Path
    ) -> Optional[subprocess.Popen]:
        """Start the MCP server process."""

        try:
            import sys

            # Use MCPify's Python environment (which has MCP SDK installed)
            # The generated server will import original project code via sys.path
            python_exe = sys.executable

            if not python_exe or not Path(python_exe).exists():
                print(f"Python executable not found at {python_exe}")
                return None

            # Start the process
            process = subprocess.Popen(
                [str(python_exe), str(server_path)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=working_dir,
                text=True,
                bufsize=1,  # Line buffered
                universal_newlines=True,
            )

            return process

        except Exception as e:
            print(f"Error starting server process: {e}")
            return None

    def test_server_communication(
        self, process: subprocess.Popen, timeout: int = 5
    ) -> Tuple[bool, str]:
        """Test if the server responds to MCP requests."""

        try:
            import json

            # Send a tools/list request
            test_request = {"method": "tools/list", "id": 1}

            # Send request
            request_json = json.dumps(test_request) + "\n"
            process.stdin.write(request_json)
            process.stdin.flush()

            # Read response with timeout
            import select

            ready, _, _ = select.select([process.stdout], [], [], timeout)

            if not ready:
                return False, "Server did not respond within timeout"

            response_line = process.stdout.readline()
            if not response_line:
                return False, "No response received from server"

            # Parse response
            response = json.loads(response_line.strip())

            if "tools" in response:
                tool_count = len(response["tools"])
                return True, f"Server responding correctly with {tool_count} tools"
            elif "error" in response:
                return False, f"Server returned error: {response['error']}"
            else:
                return False, f"Unexpected response format: {response}"

        except Exception as e:
            return False, f"Error testing server communication: {e}"

    def stop_server(
        self, server_id: str = None, process: subprocess.Popen = None
    ) -> bool:
        """Stop a running MCP server."""

        try:
            target_process = None

            if server_id and server_id in self.active_servers:
                target_process = self.active_servers[server_id]
                del self.active_servers[server_id]
            elif process:
                target_process = process
                # Remove from active servers if present
                for sid, proc in list(self.active_servers.items()):
                    if proc == process:
                        del self.active_servers[sid]
                        break

            if target_process is None:
                return False

            # Try graceful shutdown first
            if target_process.poll() is None:
                target_process.terminate()

                # Wait for graceful shutdown
                try:
                    target_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Force kill if graceful shutdown fails
                    target_process.kill()
                    target_process.wait(timeout=2)

            return True

        except Exception as e:
            print(f"Error stopping server: {e}")
            return False

    def stop_all_servers(self):
        """Stop all active servers."""
        for server_id in list(self.active_servers.keys()):
            self.stop_server(server_id)

    def get_server_status(self, process: subprocess.Popen) -> Dict[str, Any]:
        """Get status information about a server process."""

        try:
            if process.poll() is None:
                # Process is running
                try:
                    psutil_process = psutil.Process(process.pid)
                    return {
                        "status": "running",
                        "pid": process.pid,
                        "cpu_percent": psutil_process.cpu_percent(),
                        "memory_mb": psutil_process.memory_info().rss / 1024 / 1024,
                        "create_time": psutil_process.create_time(),
                    }
                except psutil.NoSuchProcess:
                    return {"status": "terminated", "pid": process.pid}
            else:
                return {
                    "status": "terminated",
                    "pid": process.pid,
                    "return_code": process.returncode,
                }

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def cleanup(self):
        """Clean up resources and stop all servers."""
        self.stop_all_servers()

    def __del__(self):
        """Cleanup when the runner is destroyed."""
        self.cleanup()
