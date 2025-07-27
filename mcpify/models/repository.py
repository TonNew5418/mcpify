from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class Repository:
    """Represents a Git repository being analyzed."""

    url: str
    local_path: Path
    name: str
    language: str = "python"
    dependencies: List[str] = None
    dependency_files: List[Path] = None
    python_files: List[Path] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.dependency_files is None:
            self.dependency_files = []
        if self.python_files is None:
            self.python_files = []
        if self.metadata is None:
            self.metadata = {}

    @property
    def has_pyproject_toml(self) -> bool:
        return (self.local_path / "pyproject.toml").exists()

    @property
    def has_requirements_txt(self) -> bool:
        return (self.local_path / "requirements.txt").exists()

    @property
    def has_setup_py(self) -> bool:
        return (self.local_path / "setup.py").exists()
