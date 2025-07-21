"""
Session and History Management for MCPify UI.

This module handles project sessions, chat history, and persistent storage.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import streamlit as st

from mcpify.ui.models import (
    ChatMessage,
    ProjectSession,
    RepositoryInfo,
    SmartSuggestion,
    UserRequirement,
)


class SessionManager:
    """Manages project sessions, history, and chat conversations."""

    def __init__(self, storage_path: Optional[Path] = None):
        """Initialize session manager with optional custom storage path."""
        if storage_path:
            self.storage_path = storage_path
        else:
            # Default to user's home directory
            self.storage_path = Path.home() / ".mcpify" / "sessions"

        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Initialize session state if not exists
        if "current_session" not in st.session_state:
            st.session_state.current_session = None
        if "session_history" not in st.session_state:
            st.session_state.session_history = self.load_session_history()

    def create_new_session(
        self, repository_source: str, repository_info: RepositoryInfo
    ) -> ProjectSession:
        """Create a new analysis session."""
        session_id = str(uuid.uuid4())[:8]  # Short UUID

        session = ProjectSession(
            session_id=session_id,
            repository_source=repository_source,
            repository_info=repository_info,
            analysis_result=None,
        )

        # Set as current session
        st.session_state.current_session = session

        # Add to history
        if session not in st.session_state.session_history:
            st.session_state.session_history.insert(0, session)  # Add to front

        return session

    def update_current_session(self, **kwargs) -> Optional[ProjectSession]:
        """Update the current session with new data."""
        if not st.session_state.current_session:
            return None

        session = st.session_state.current_session

        # Update fields
        for key, value in kwargs.items():
            if hasattr(session, key):
                setattr(session, key, value)

        session.updated_at = datetime.now()

        # Save to persistent storage
        self.save_session(session)

        return session

    def add_chat_message(
        self, role: str, content: str, metadata: Optional[dict[str, Any]] = None
    ) -> Optional[ChatMessage]:
        """Add a message to the current session's chat."""
        if not st.session_state.current_session:
            return None

        message = ChatMessage(role=role, content=content, metadata=metadata or {})

        st.session_state.current_session.chat_messages.append(message)
        st.session_state.current_session.updated_at = datetime.now()

        return message

    def get_current_session(self) -> Optional[ProjectSession]:
        """Get the current active session."""
        return st.session_state.current_session

    def get_session_history(self) -> list[ProjectSession]:
        """Get list of all sessions."""
        return st.session_state.session_history or []

    def load_session(self, session_id: str) -> Optional[ProjectSession]:  # noqa: UP007
        """Load a specific session by ID."""
        session_file = self.storage_path / f"session_{session_id}.json"

        if not session_file.exists():
            return None

        try:
            with open(session_file, encoding="utf-8") as f:
                data = json.load(f)

            # Reconstruct session object
            # This is a simplified version - in production you'd want proper serialization
            session = self._dict_to_session(data)
            return session

        except Exception as e:
            st.error(f"Failed to load session {session_id}: {e}")
            return None

    def save_session(self, session: ProjectSession) -> bool:
        """Save session to persistent storage."""
        try:
            session_file = self.storage_path / f"session_{session.session_id}.json"

            # Convert to dictionary
            data = self._session_to_dict(session)

            with open(session_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)

            return True

        except Exception as e:
            st.error(f"Failed to save session: {e}")
            return False

    def load_session_history(self) -> list[ProjectSession]:
        """Load all sessions from storage."""
        sessions = []

        try:
            for session_file in self.storage_path.glob("session_*.json"):
                with open(session_file, encoding="utf-8") as f:
                    data = json.load(f)

                session = self._dict_to_session(data)
                sessions.append(session)

        except Exception as e:
            st.warning(f"Some sessions could not be loaded: {e}")

        # Sort by update time (most recent first)
        sessions.sort(key=lambda x: x.updated_at, reverse=True)
        return sessions

    def delete_session(self, session_id: str) -> bool:
        """Delete a session from storage and history."""
        try:
            # Remove from file
            session_file = self.storage_path / f"session_{session_id}.json"
            if session_file.exists():
                session_file.unlink()

            # Remove from session state
            st.session_state.session_history = [
                s
                for s in st.session_state.session_history
                if s.session_id != session_id
            ]

            # Clear current session if it's the deleted one
            if (
                st.session_state.current_session
                and st.session_state.current_session.session_id == session_id
            ):
                st.session_state.current_session = None

            return True

        except Exception as e:
            st.error(f"Failed to delete session: {e}")
            return False

    def _session_to_dict(self, session: ProjectSession) -> dict[str, Any]:
        """Convert session object to dictionary for JSON serialization."""
        return {
            "session_id": session.session_id,
            "repository_source": session.repository_source,
            "repository_info": {
                "name": session.repository_info.name,
                "description": session.repository_info.description,
                "language": session.repository_info.language,
                "framework": session.repository_info.framework,
                "total_files": session.repository_info.total_files,
                "analyzed_files": session.repository_info.analyzed_files,
                "file_size_bytes": session.repository_info.file_size_bytes,
            },
            "chat_messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "metadata": msg.metadata,
                }
                for msg in session.chat_messages
            ],
            "user_requirements": session.user_requirements,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
        }

    def _dict_to_session(self, data: dict[str, Any]) -> ProjectSession:
        """Convert dictionary back to session object."""
        # Create repository info
        repo_info_data = data["repository_info"]
        repository_info = RepositoryInfo(
            name=repo_info_data["name"],
            description=repo_info_data.get("description", ""),
            language=repo_info_data.get("language", ""),
            framework=repo_info_data.get("framework", ""),
            total_files=repo_info_data.get("total_files", 0),
            analyzed_files=repo_info_data.get("analyzed_files", 0),
            file_size_bytes=repo_info_data.get("file_size_bytes", 0),
        )

        # Create chat messages
        chat_messages = []
        for msg_data in data.get("chat_messages", []):
            message = ChatMessage(
                role=msg_data["role"],
                content=msg_data["content"],
                timestamp=datetime.fromisoformat(msg_data["timestamp"]),
                metadata=msg_data.get("metadata", {}),
            )
            chat_messages.append(message)

        # Create session
        session = ProjectSession(
            session_id=data["session_id"],
            repository_source=data["repository_source"],
            repository_info=repository_info,
            analysis_result=None,  # Simplified for now
            chat_messages=chat_messages,
            user_requirements=data.get("user_requirements", ""),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )

        return session


class RequirementAnalyzer:
    """Analyzes user requirements and generates smart suggestions."""

    def __init__(self):
        self.common_patterns = {
            "api": ["api", "endpoint", "rest", "graphql", "service"],
            "cli": ["command", "terminal", "script", "tool"],
            "library": ["function", "module", "package", "import"],
            "automation": ["automate", "schedule", "batch", "pipeline"],
        }

    def analyze_user_input(
        self, user_input: str, repository_info: RepositoryInfo
    ) -> UserRequirement:
        """Analyze user input to extract structured requirements."""
        user_input_lower = user_input.lower()

        # Determine functionality type
        functionality_type = "other"
        for func_type, keywords in self.common_patterns.items():
            if any(keyword in user_input_lower for keyword in keywords):
                functionality_type = func_type
                break

        # Extract specific needs (simplified)
        specific_needs = []
        if "endpoint" in user_input_lower or "api" in user_input_lower:
            specific_needs.append("HTTP endpoints")
        if "command" in user_input_lower:
            specific_needs.append("Command-line interface")
        if "function" in user_input_lower:
            specific_needs.append("Function calls")

        if not specific_needs:
            specific_needs = ["General functionality"]

        # Determine preferred interface
        preferred_interface = "rest"  # Default
        if functionality_type == "cli":
            preferred_interface = "cli"
        elif functionality_type == "library":
            preferred_interface = "function"

        return UserRequirement(
            functionality_type=functionality_type,
            specific_needs=specific_needs,
            preferred_interface=preferred_interface,
            description=user_input,
        )

    def generate_suggestions(
        self, repository_info: RepositoryInfo, user_requirement: UserRequirement
    ) -> list[SmartSuggestion]:
        """Generate smart suggestions based on repository and user requirements."""
        suggestions = []

        # Framework-specific suggestions
        if repository_info.framework == "fastapi":
            suggestions.append(
                SmartSuggestion(
                    suggestion_type="functionality",
                    title="FastAPI Endpoints",
                    description="Detect all FastAPI routes and generate REST API tools",
                    confidence=0.9,
                    implementation_hint="Use HTTP backend with automatic route discovery",
                )
            )

        elif repository_info.framework == "flask":
            suggestions.append(
                SmartSuggestion(
                    suggestion_type="functionality",
                    title="Flask Routes",
                    description="Extract Flask routes and blueprints for API access",
                    confidence=0.85,
                    implementation_hint="Map Flask routes to MCP tools with request handling",
                )
            )

        # Language-specific suggestions
        if repository_info.language == "python":
            if user_requirement.functionality_type == "cli":
                suggestions.append(
                    SmartSuggestion(
                        suggestion_type="configuration",
                        title="Python CLI Tools",
                        description="Create command-line interface wrappers for Python functions",
                        confidence=0.8,
                        implementation_hint="Use commandline backend with argument parsing",
                    )
                )

            suggestions.append(
                SmartSuggestion(
                    suggestion_type="functionality",
                    title="Function Access",
                    description="Direct access to Python functions as MCP tools",
                    confidence=0.75,
                    implementation_hint="Use python backend for direct function calls",
                )
            )

        # General suggestions
        suggestions.append(
            SmartSuggestion(
                suggestion_type="optimization",
                title="Smart Parameter Detection",
                description="Automatically detect and validate function parameters",
                confidence=0.7,
                implementation_hint="Analyze function signatures for type hints and defaults",
            )
        )

        return suggestions
