"""
GitIngest integration service for MCPify.

This module provides functionality to process repositories using gitingest
and prepare them for MCP analysis.
"""

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    from gitingest import ingest

    GITINGEST_AVAILABLE = True
except ImportError:
    GITINGEST_AVAILABLE = False

    # Fallback when gitingest is not available
    def ingest(
        source: str,
        max_file_size: int = 50000,
        exclude_patterns: list[str] | None = None,
    ):
        """Fallback ingest function when gitingest is not available."""
        raise GitIngestError(
            "GitIngest library is not installed. Install it with: pip install gitingest"
        )


logger = logging.getLogger(__name__)


class GitIngestError(Exception):
    """Exception raised when GitIngest processing fails."""

    pass


class GitIngestService:
    """Service for processing repositories with GitIngest."""

    def __init__(self):
        self.temp_dirs: list[Path] = []

    def __enter__(self) -> "GitIngestService":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.cleanup()

    def cleanup(self) -> None:
        """Clean up any temporary directories created during processing."""
        for temp_dir in self.temp_dirs:
            try:
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)
            except Exception as e:
                logger.warning(f"Failed to clean up temp directory {temp_dir}: {e}")
        self.temp_dirs.clear()

    def is_github_url(self, source: str) -> bool:
        """Check if the source is a GitHub URL."""
        try:
            parsed = urlparse(source.lower())
            return parsed.netloc in ["github.com", "www.github.com"]
        except Exception:
            return False

    def is_git_url(self, source: str) -> bool:
        """Check if the source is any git URL."""
        try:
            parsed = urlparse(source.lower())
            return (
                parsed.scheme in ["http", "https", "git"]
                or source.endswith(".git")
                or "github.com" in source
                or "gitlab.com" in source
                or "bitbucket.org" in source
            )
        except Exception:
            return False

    def clone_repository(self, git_url: str) -> Path:
        """Clone a git repository to a temporary directory."""
        temp_dir = Path(tempfile.mkdtemp(prefix="mcpify_repo_"))
        self.temp_dirs.append(temp_dir)

        try:
            logger.info(f"Cloning repository {git_url} to {temp_dir}")
            subprocess.run(
                ["git", "clone", "--depth", "1", git_url, str(temp_dir)],
                check=True,
                capture_output=True,
                text=True,
            )
            return temp_dir
        except subprocess.CalledProcessError as e:
            raise GitIngestError(
                f"Failed to clone repository {git_url}: {e.stderr}"
            ) from e
        except FileNotFoundError as e:
            raise GitIngestError("Git is not installed or not found in PATH") from e

    def process_repository(
        self,
        source: str,
        source_type: str,
        exclude_patterns: list[str] | None = None,
        max_file_size: int = 50000,
    ) -> dict[str, Any]:
        """
        Process a repository using GitIngest.

        Args:
            source: Repository URL or local path
            source_type: 'url' or 'local'
            exclude_patterns: List of patterns to exclude
            max_file_size: Maximum file size to include (in bytes)

        Returns:
            Dict containing code digest and metadata
        """
        if exclude_patterns is None:
            exclude_patterns = [
                "*.md",
                "__pycache__/",
                "*.pyc",
                ".git/",
                "node_modules/",
            ]

        try:
            # Determine the source path
            if source_type == "url":
                if self.is_git_url(source):
                    repo_path = self.clone_repository(source)
                else:
                    raise GitIngestError(f"Unsupported URL format: {source}")
            else:
                repo_path = Path(source)
                if not repo_path.exists():
                    raise GitIngestError(f"Local path does not exist: {source}")
                if not repo_path.is_dir():
                    raise GitIngestError(f"Source is not a directory: {source}")

            logger.info(f"Processing repository at {repo_path}")

            if not GITINGEST_AVAILABLE:
                raise GitIngestError(
                    "GitIngest library is not installed. Install it with: pip install gitingest"
                )

            # Use gitingest to process the repository (sync version)
            # gitingest.ingest returns (summary, tree, content)
            # Convert exclude_patterns to set if it's a list
            exclude_set = set(exclude_patterns) if exclude_patterns else None

            summary, tree, content = ingest(
                source=str(repo_path),
                max_file_size=max_file_size,
                exclude_patterns=exclude_set,
            )

            # Extract repository info
            repo_info = self._extract_repository_info(repo_path, source)

            # Count files from tree output
            file_count = len(
                [
                    line
                    for line in tree.split("\n")
                    if line.strip()
                    and not line.strip().startswith("├")
                    and not line.strip().startswith("└")
                ]
            )

            return {
                "repository_info": repo_info,
                "code_digest": content,
                "file_tree": tree,
                "summary": summary,
                "metadata": {
                    "total_files": file_count,
                    "total_size": len(content),
                    "processed_files": file_count,
                    "skipped_files": 0,
                },
            }

        except Exception as e:
            logger.error(f"Error processing repository {source}: {e}")
            raise GitIngestError(f"Failed to process repository: {str(e)}") from e

    def _extract_repository_info(
        self, repo_path: Path, original_source: str
    ) -> dict[str, Any]:
        """Extract basic information about the repository."""
        info = {
            "name": repo_path.name,
            "path": str(repo_path),
            "original_source": original_source,
            "description": "",
            "language": "",
            "framework": "",
        }

        # Try to detect main language
        language_files = {
            "python": [".py"],
            "javascript": [".js", ".ts"],
            "java": [".java"],
            "go": [".go"],
            "rust": [".rs"],
            "c++": [".cpp", ".cc", ".cxx"],
            "c": [".c"],
            "php": [".php"],
            "ruby": [".rb"],
            "swift": [".swift"],
            "kotlin": [".kt"],
        }

        file_counts = {}
        for language, extensions in language_files.items():
            count = 0
            for ext in extensions:
                count += len(list(repo_path.rglob(f"*{ext}")))
            if count > 0:
                file_counts[language] = count

        if file_counts:
            info["language"] = max(file_counts.items(), key=lambda x: x[1])[0]

        # Try to detect framework
        framework_indicators = {
            "fastapi": ["main.py", "app.py"],
            "flask": ["app.py", "application.py"],
            "django": ["manage.py", "settings.py"],
            "express": ["package.json"],
            "react": ["package.json"],
            "vue": ["package.json"],
            "angular": ["angular.json"],
            "spring": ["pom.xml", "build.gradle"],
        }

        for framework, indicators in framework_indicators.items():
            if any((repo_path / indicator).exists() for indicator in indicators):
                info["framework"] = framework
                break

        # Try to read description from README
        readme_files = ["README.md", "README.rst", "README.txt", "README"]
        for readme_file in readme_files:
            readme_path = repo_path / readme_file
            if readme_path.exists():
                try:
                    content = readme_path.read_text(encoding="utf-8")
                    # Extract first line as description (skip title)
                    lines = [
                        line.strip() for line in content.split("\n") if line.strip()
                    ]
                    if len(lines) > 1:
                        info["description"] = lines[1][:200]  # First 200 chars
                    break
                except Exception:
                    pass

        return info
