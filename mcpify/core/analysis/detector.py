import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import toml

from ...models.repository import Repository


class DependencyDetector:
    """Detect and parse Python project dependencies."""

    def __init__(self):
        self.has_uv = shutil.which("uv") is not None
        self.has_pip = shutil.which("pip") is not None

        # Common directories and patterns to ignore
        self.ignore_patterns = {
            # Hidden directories
            ".*",
            # Version control
            ".git",
            ".svn",
            ".hg",
            ".bzr",
            # Python cache and virtual environments
            "__pycache__",
            ".pytest_cache",
            ".mypy_cache",
            ".tox",
            "venv",
            ".venv",
            "env",
            ".env",
            "virtualenv",
            # Build and distribution
            "build",
            "dist",
            "*.egg-info",
            ".eggs",
            # IDE and editor files
            ".vscode",
            ".idea",
            ".sublime-project",
            ".sublime-workspace",
            # Documentation and temporary
            "docs",
            "_build",
            ".doctrees",
            "htmlcov",
            # Dependencies
            "node_modules",
            ".npm",
            "bower_components",
            # OS specific
            ".DS_Store",
            "Thumbs.db",
            "desktop.ini",
            # Test coverage
            ".coverage",
            ".nyc_output",
            "coverage",
            # Temporary files
            "*.tmp",
            "*.temp",
            "*.log",
            "*.swp",
            "*.swo",
        }

    def analyze_repository(self, repo_path: Path) -> Repository:
        """Analyze a repository and extract dependency information."""
        repo_name = repo_path.name
        python_files = self._find_python_files(repo_path)

        # Detect dependency files
        dependency_files = []
        dependencies = []

        if (repo_path / "pyproject.toml").exists():
            dependency_files.append(repo_path / "pyproject.toml")
            deps = self._parse_pyproject_toml(repo_path / "pyproject.toml")
            dependencies.extend(deps)

        if (repo_path / "requirements.txt").exists():
            dependency_files.append(repo_path / "requirements.txt")
            deps = self._parse_requirements_txt(repo_path / "requirements.txt")
            dependencies.extend(deps)

        if (repo_path / "setup.py").exists():
            dependency_files.append(repo_path / "setup.py")
            deps = self._parse_setup_py(repo_path / "setup.py")
            dependencies.extend(deps)

        # Remove duplicates
        dependencies = list(set(dependencies))

        return Repository(
            url="",  # Will be set by caller
            local_path=repo_path,
            name=repo_name,
            language="python",
            dependencies=dependencies,
            dependency_files=dependency_files,
            python_files=python_files,
            metadata=self._extract_metadata(repo_path),
        )

    def _find_python_files(self, repo_path: Path) -> List[Path]:
        """Find Python files while ignoring common patterns."""
        python_files = []

        for py_file in repo_path.rglob("*.py"):
            # Check if any part of the path should be ignored
            should_ignore = False

            for part in py_file.relative_to(repo_path).parts:
                if self._should_ignore_path_part(part):
                    should_ignore = True
                    break

            if not should_ignore:
                python_files.append(py_file)

        return python_files

    def _should_ignore_path_part(self, path_part: str) -> bool:
        """Check if a path part matches ignore patterns."""
        import fnmatch

        for pattern in self.ignore_patterns:
            if fnmatch.fnmatch(path_part, pattern):
                return True

        return False

    def _parse_pyproject_toml(self, file_path: Path) -> List[str]:
        """Parse dependencies from pyproject.toml."""
        try:
            with open(file_path, encoding="utf-8") as f:
                data = toml.load(f)

            dependencies = []

            # Standard dependencies
            project_deps = data.get("project", {}).get("dependencies", [])
            dependencies.extend(self._clean_dependency_specs(project_deps))

            # Build system requirements
            build_deps = data.get("build-system", {}).get("requires", [])
            dependencies.extend(self._clean_dependency_specs(build_deps))

            # Optional dependencies
            optional_deps = data.get("project", {}).get("optional-dependencies", {})
            for group_deps in optional_deps.values():
                dependencies.extend(self._clean_dependency_specs(group_deps))

            return dependencies

        except Exception as e:
            print(f"Error parsing pyproject.toml: {e}")
            return []

    def _parse_requirements_txt(self, file_path: Path) -> List[str]:
        """Parse dependencies from requirements.txt."""
        try:
            with open(file_path, encoding="utf-8") as f:
                lines = f.readlines()

            dependencies = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith("#") and not line.startswith("-"):
                    dep = self._clean_dependency_spec(line)
                    if dep:
                        dependencies.append(dep)

            return dependencies

        except Exception as e:
            print(f"Error parsing requirements.txt: {e}")
            return []

    def _parse_setup_py(self, file_path: Path) -> List[str]:
        """Extract dependencies from setup.py (basic regex parsing)."""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            dependencies = []

            # Look for install_requires
            install_requires_match = re.search(
                r"install_requires\s*=\s*\[(.*?)\]", content, re.DOTALL
            )
            if install_requires_match:
                deps_str = install_requires_match.group(1)
                # Extract quoted strings
                dep_matches = re.findall(r'["\']([^"\']+)["\']', deps_str)
                dependencies.extend(self._clean_dependency_specs(dep_matches))

            return dependencies

        except Exception as e:
            print(f"Error parsing setup.py: {e}")
            return []

    def _clean_dependency_specs(self, deps: List[str]) -> List[str]:
        """Clean a list of dependency specifications."""
        return [
            self._clean_dependency_spec(dep)
            for dep in deps
            if self._clean_dependency_spec(dep)
        ]

    def _clean_dependency_spec(self, dep: str) -> Optional[str]:
        """Extract package name from dependency specification."""
        if not dep or dep.startswith("#"):
            return None

        # Remove version specifiers and extras
        dep = dep.strip()
        dep = re.sub(r"\[.*?\]", "", dep)  # Remove extras like [dev]
        dep = re.sub(r"[><=!~].*", "", dep)  # Remove version specifiers
        dep = dep.strip()

        # Handle git URLs and file paths
        if dep.startswith(("git+", "http", "file:", ".")):
            return None

        return dep if dep else None

    def _extract_metadata(self, repo_path: Path) -> Dict[str, Any]:
        """Extract additional repository metadata."""
        metadata = {}

        # Check for common Python project indicators
        metadata["has_tests"] = any(
            [
                (repo_path / "tests").exists(),
                (repo_path / "test").exists(),
                list(repo_path.glob("**/test_*.py")),
                list(repo_path.glob("**/*_test.py")),
            ]
        )

        metadata["has_docs"] = any(
            [
                (repo_path / "docs").exists(),
                (repo_path / "doc").exists(),
                (repo_path / "documentation").exists(),
            ]
        )

        metadata["has_src_layout"] = (repo_path / "src").exists()

        # Estimate project size
        metadata["python_file_count"] = len(self._find_python_files(repo_path))
        metadata["total_lines"] = self._count_lines_of_code(repo_path)

        return metadata

    def _count_lines_of_code(self, repo_path: Path) -> int:
        """Count total lines of Python code."""
        total_lines = 0
        for py_file in self._find_python_files(repo_path):
            try:
                with open(py_file, encoding="utf-8") as f:
                    total_lines += len(f.readlines())
            except Exception:
                continue
        return total_lines

    def create_virtual_environment(
        self, repo: Repository, venv_path: Path
    ) -> Tuple[bool, str]:
        """Create a virtual environment and install dependencies."""
        try:
            if self.has_uv:
                return self._create_with_uv(repo, venv_path)
            elif self.has_pip:
                return self._create_with_pip(repo, venv_path)
            else:
                return False, "Neither uv nor pip found"

        except Exception as e:
            return False, f"Error creating virtual environment: {e}"

    def _create_with_uv(self, repo: Repository, venv_path: Path) -> Tuple[bool, str]:
        """Create virtual environment using uv."""
        # Create venv
        import os

        result = subprocess.run(
            ["uv", "venv", str(venv_path)],
            capture_output=True,
            text=True,
            cwd=repo.local_path,
            env=os.environ.copy(),  # 传递当前环境变量
        )

        if result.returncode != 0:
            return False, f"Failed to create venv: {result.stderr}"

        # Install dependencies
        if repo.has_pyproject_toml:
            env = os.environ.copy()
            env["VIRTUAL_ENV"] = str(venv_path)
            install_result = subprocess.run(
                ["uv", "pip", "install", "-e", "."],
                capture_output=True,
                text=True,
                cwd=repo.local_path,
                env=env,
            )
        elif repo.has_requirements_txt:
            env = os.environ.copy()
            env["VIRTUAL_ENV"] = str(venv_path)
            install_result = subprocess.run(
                ["uv", "pip", "install", "-r", "requirements.txt"],
                capture_output=True,
                text=True,
                cwd=repo.local_path,
                env=env,
            )
        else:
            # Install individual dependencies
            if repo.dependencies:
                env = os.environ.copy()
                env["VIRTUAL_ENV"] = str(venv_path)
                install_result = subprocess.run(
                    ["uv", "pip", "install"] + repo.dependencies,
                    capture_output=True,
                    text=True,
                    cwd=repo.local_path,
                    env=env,
                )
            else:
                return True, "No dependencies to install"

        if install_result.returncode != 0:
            return False, f"Failed to install dependencies: {install_result.stderr}"

        return True, "Virtual environment created successfully with uv"

    def _create_with_pip(self, repo: Repository, venv_path: Path) -> Tuple[bool, str]:
        """Create virtual environment using pip."""
        import venv

        # Create venv
        venv.create(venv_path, with_pip=True)

        # Get pip path
        if venv_path.name == "venv":
            pip_path = venv_path / "bin" / "pip"
        else:
            pip_path = (
                venv_path / "Scripts" / "pip.exe"
                if Path.cwd().drive
                else venv_path / "bin" / "pip"
            )

        # Install dependencies
        if repo.has_pyproject_toml:
            install_result = subprocess.run(
                [str(pip_path), "install", "-e", "."],
                capture_output=True,
                text=True,
                cwd=repo.local_path,
            )
        elif repo.has_requirements_txt:
            install_result = subprocess.run(
                [str(pip_path), "install", "-r", "requirements.txt"],
                capture_output=True,
                text=True,
                cwd=repo.local_path,
            )
        else:
            # Install individual dependencies
            if repo.dependencies:
                install_result = subprocess.run(
                    [str(pip_path), "install"] + repo.dependencies,
                    capture_output=True,
                    text=True,
                    cwd=repo.local_path,
                )
            else:
                return True, "No dependencies to install"

        if install_result.returncode != 0:
            return False, f"Failed to install dependencies: {install_result.stderr}"

        return True, "Virtual environment created successfully with pip"
