"""
Data models for the AI Chat UI functionality.

This module contains all the data classes and type definitions used
throughout the AI chat interface for mcpify.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Literal, Optional

# Import ToolSpec from detect types
from mcpify.detect.types import ToolSpec

# Chat-related models


@dataclass
class Message:
    """Represents a single message in the chat conversation."""

    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate message after initialization."""
        if not self.content or not self.content.strip():
            raise ValueError("Message content cannot be empty")
        if self.role not in ["user", "assistant", "system"]:
            raise ValueError(f"Invalid role: {self.role}")


class ActionType(Enum):
    """Enum for different action types in chat responses."""

    CHAT = "chat"
    API_SEARCH = "api_search"
    CONFIG_GENERATE = "config_generate"


@dataclass
class ChatResponse:
    """Response from the chat service containing message and action information."""

    message: str
    action_type: ActionType
    data: dict[str, Any] = field(default_factory=dict)
    suggestions: list[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate chat response after initialization."""
        if not self.message or not self.message.strip():
            raise ValueError("Chat response message cannot be empty")


@dataclass
class APIRequirements:
    """Represents extracted API requirements from user conversation."""

    description: str
    functionality: list[str]
    preferred_type: Literal["rest", "graphql", "websocket"] = "rest"
    authentication: Literal["none", "api_key", "oauth"] = "none"
    language: str = "zh"

    def __post_init__(self):
        """Validate API requirements after initialization."""
        if not self.description or not self.description.strip():
            raise ValueError("API requirements description cannot be empty")
        if not self.functionality:
            raise ValueError("At least one functionality must be specified")
        if self.preferred_type not in ["rest", "graphql", "websocket"]:
            raise ValueError(f"Invalid preferred_type: {self.preferred_type}")
        if self.authentication not in ["none", "api_key", "oauth"]:
            raise ValueError(f"Invalid authentication: {self.authentication}")


# API Search-related models


@dataclass
class APIEndpoint:
    """Represents a single API endpoint."""

    path: str
    method: str
    description: str
    parameters: list[dict[str, Any]] = field(default_factory=list)
    response_schema: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate API endpoint after initialization."""
        if not self.path or not self.path.strip():
            raise ValueError("API endpoint path cannot be empty")
        if not self.method or not self.method.strip():
            raise ValueError("API endpoint method cannot be empty")
        if self.method.upper() not in [
            "GET",
            "POST",
            "PUT",
            "DELETE",
            "PATCH",
            "HEAD",
            "OPTIONS",
        ]:
            raise ValueError(f"Invalid HTTP method: {self.method}")


@dataclass
class APICandidate:
    """Represents a candidate API found during search."""

    name: str
    description: str
    base_url: str
    endpoints: list[APIEndpoint] = field(default_factory=list)
    authentication_type: str = "none"
    documentation_url: str = ""
    confidence_score: float = 0.0

    def __post_init__(self):
        """Validate API candidate after initialization."""
        if not self.name or not self.name.strip():
            raise ValueError("API candidate name cannot be empty")
        if not self.description or not self.description.strip():
            raise ValueError("API candidate description cannot be empty")
        if not self.base_url or not self.base_url.strip():
            raise ValueError("API candidate base_url cannot be empty")
        if not (0.0 <= self.confidence_score <= 1.0):
            raise ValueError("Confidence score must be between 0.0 and 1.0")


@dataclass
class ValidationResult:
    """Result of configuration validation."""

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate validation result after initialization."""
        if not self.is_valid and not self.errors:
            raise ValueError("Invalid configuration must have at least one error")


@dataclass
class MCPConfig:
    """Extended MCP configuration model for the UI."""

    name: str
    description: str
    backend: dict[str, Any]
    tools: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate MCP config after initialization."""
        if not self.name or not self.name.strip():
            raise ValueError("MCP config name cannot be empty")
        if not self.description or not self.description.strip():
            raise ValueError("MCP config description cannot be empty")
        if not self.backend:
            raise ValueError("MCP config backend cannot be empty")


# Repository Analysis models


@dataclass
class RepositoryInput:
    """Input data for repository analysis."""

    source: str
    source_type: Literal["url", "local"]
    exclude_patterns: list[str] = field(
        default_factory=lambda: [
            "*.md",
            "__pycache__/",
            "*.pyc",
            ".git/",
            "node_modules/",
        ]
    )
    max_file_size: int = 50000  # 50kB
    include_private: bool = False
    detection_strategy: Literal["auto", "openai", "camel"] = "auto"

    def __post_init__(self):
        """Validate repository input after initialization."""
        if not self.source or not self.source.strip():
            raise ValueError("Repository source cannot be empty")
        if self.source_type not in ["url", "local"]:
            raise ValueError(f"Invalid source_type: {self.source_type}")
        if self.max_file_size <= 0:
            raise ValueError("Max file size must be positive")


@dataclass
class AnalysisProgress:
    """Progress information for repository analysis."""

    current_step: str
    progress_percentage: int
    step_details: str = ""
    total_steps: int = 4  # gitingest -> detect -> validate -> complete

    def __post_init__(self):
        """Validate analysis progress after initialization."""
        if not (0 <= self.progress_percentage <= 100):
            raise ValueError("Progress percentage must be between 0 and 100")
        if self.total_steps <= 0:
            raise ValueError("Total steps must be positive")


@dataclass
class RepositoryInfo:
    """Information about the analyzed repository."""

    name: str
    description: str = ""
    language: str = ""
    framework: str = ""
    total_files: int = 0
    analyzed_files: int = 0
    file_size_bytes: int = 0

    def __post_init__(self):
        """Validate repository info after initialization."""
        if not self.name or not self.name.strip():
            raise ValueError("Repository name cannot be empty")


@dataclass
class AnalysisResult:
    """Complete result of repository analysis."""

    repository_info: RepositoryInfo
    code_digest: str
    mcp_config: Optional[MCPConfig]
    detection_summary: str
    validation_result: ValidationResult
    processing_time_seconds: float = 0.0

    def __post_init__(self):
        """Validate analysis result after initialization."""
        if not self.code_digest or not self.code_digest.strip():
            raise ValueError("Code digest cannot be empty")
        if not self.detection_summary or not self.detection_summary.strip():
            raise ValueError("Detection summary cannot be empty")
        if self.processing_time_seconds < 0:
            raise ValueError("Processing time cannot be negative")


# Chat and History models


@dataclass
class ChatMessage:
    """Represents a single message in the chat interface."""

    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate message after initialization."""
        if not self.content or not self.content.strip():
            raise ValueError("Message content cannot be empty")
        if self.role not in ["user", "assistant", "system"]:
            raise ValueError(f"Invalid role: {self.role}")


@dataclass
class ProjectSession:
    """Represents a complete analysis session for a project."""

    session_id: str
    repository_source: str
    repository_info: RepositoryInfo
    analysis_result: Optional[AnalysisResult]
    chat_messages: list[ChatMessage] = field(default_factory=list)
    user_requirements: str = ""
    final_config: Optional[MCPConfig] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Validate project session after initialization."""
        if not self.session_id or not self.session_id.strip():
            raise ValueError("Session ID cannot be empty")
        if not self.repository_source or not self.repository_source.strip():
            raise ValueError("Repository source cannot be empty")


@dataclass
class UserRequirement:
    """Parsed user requirements for specific functionality."""

    functionality_type: Literal["api", "cli", "library", "automation", "other"]
    specific_needs: list[str]
    preferred_interface: Literal["rest", "graphql", "cli", "function"]
    description: str
    priority: Literal["high", "medium", "low"] = "medium"

    def __post_init__(self):
        """Validate user requirement after initialization."""
        if not self.description or not self.description.strip():
            raise ValueError("Requirement description cannot be empty")
        if not self.specific_needs:
            raise ValueError("At least one specific need must be provided")


@dataclass
class SmartSuggestion:
    """AI-generated suggestion based on repository analysis."""

    suggestion_type: Literal["functionality", "configuration", "optimization"]
    title: str
    description: str
    confidence: float
    implementation_hint: str = ""

    def __post_init__(self):
        """Validate suggestion after initialization."""
        if not self.title or not self.title.strip():
            raise ValueError("Suggestion title cannot be empty")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("Confidence must be between 0.0 and 1.0")


@dataclass
class DetectionConfirmation:
    """User confirmation of detected APIs and tools."""

    detected_tools: list[ToolSpec]
    user_confirmed: list[str]  # Tool names confirmed by user
    user_rejected: list[str]  # Tool names rejected by user
    user_additions: list[dict[str, Any]]  # Additional tools requested by user
    notes: str = ""

    def __post_init__(self):
        """Validate detection confirmation after initialization."""
        if not self.detected_tools:
            raise ValueError("At least one detected tool must be provided")


# Error handling models


@dataclass
class ErrorResponse:
    """Standardized error response for the UI."""

    message: str
    error_type: str
    suggestions: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate error response after initialization."""
        if not self.message or not self.message.strip():
            raise ValueError("Error response message cannot be empty")
        if not self.error_type or not self.error_type.strip():
            raise ValueError("Error response type cannot be empty")
