"""
Sidebar Components for MCPify UI.

This module provides the sidebar with project history, settings, and navigation.
"""

from datetime import datetime
from typing import Optional

import streamlit as st

from mcpify.ui.session_manager import SessionManager


class SidebarManager:
    """Manages the sidebar interface with history and settings."""

    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager

    def render_sidebar(self) -> Optional[str]:
        """Render the complete sidebar and return any navigation actions."""
        with st.sidebar:
            # Header
            st.markdown("# 🚀 MCPify")
            st.markdown("*Smart Repository Analyzer*")
            st.divider()

            # Current session info
            action = self.render_current_session_info()
            if action:
                return action

            # Project history
            action = self.render_project_history()
            if action:
                return action

            # Settings and utilities
            self.render_settings()

            # Footer
            st.divider()
            st.caption("💡 Tip: Use the chat interface to specify your exact needs!")

        return None

    def render_current_session_info(self) -> Optional[str]:
        """Render information about the current session."""
        current_session = self.session_manager.get_current_session()

        if current_session:
            st.markdown("### 🎯 Current Project")

            with st.container():
                # Project name and source
                st.markdown(f"**{current_session.repository_info.name}**")
                st.caption(f"📂 {current_session.repository_source}")

                # Project stats
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Files", current_session.repository_info.total_files)
                with col2:
                    st.metric(
                        "Language",
                        current_session.repository_info.language or "Unknown",
                    )

                # Framework info
                if current_session.repository_info.framework:
                    st.info(
                        f"🔧 Framework: {current_session.repository_info.framework}"
                    )

                # Session actions
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🔄 New Analysis", use_container_width=True):
                        return "new_analysis"
                with col2:
                    if st.button("💾 Save Session", use_container_width=True):
                        self.session_manager.save_session(current_session)
                        st.success("Session saved!")

            st.divider()
        else:
            st.info("👆 Start by analyzing a repository above!")

        return None

    def render_project_history(self) -> Optional[str]:
        """Render the project history section."""
        st.markdown("### 📚 Project History")

        sessions = self.session_manager.get_session_history()

        if not sessions:
            st.caption("No previous projects analyzed")
            return None

        # Display recent sessions
        for session in sessions[:10]:  # Show last 10 sessions
            with st.container():
                # Session header
                col1, col2 = st.columns([3, 1])

                with col1:
                    # Clickable session name
                    if st.button(
                        f"📁 {session.repository_info.name}",
                        key=f"load_{session.session_id}",
                        use_container_width=True,
                        help=f"Load session: {session.repository_source}",
                    ):
                        # Load this session
                        st.session_state.current_session = session
                        st.rerun()

                with col2:
                    # Delete button
                    if st.button(
                        "🗑️", key=f"delete_{session.session_id}", help="Delete session"
                    ):
                        self.session_manager.delete_session(session.session_id)
                        st.rerun()

                # Session info
                st.caption(f"🕒 {self.format_relative_time(session.updated_at)}")
                st.caption(f"💬 {len(session.chat_messages)} messages")

                # Show a preview of requirements if available
                if session.user_requirements:
                    with st.expander("Requirements Preview", expanded=False):
                        st.caption(
                            session.user_requirements[:100] + "..."
                            if len(session.user_requirements) > 100
                            else session.user_requirements
                        )

        # Clear history button
        if sessions:
            st.divider()
            if st.button("🧹 Clear All History", use_container_width=True):
                if st.session_state.get("confirm_clear_history", False):
                    # Actually clear
                    for session in sessions:
                        self.session_manager.delete_session(session.session_id)
                    st.session_state.confirm_clear_history = False
                    st.rerun()
                else:
                    # Ask for confirmation
                    st.session_state.confirm_clear_history = True
                    st.warning("Click again to confirm deletion")

        return None

    def render_settings(self) -> None:
        """Render settings and configuration options."""
        with st.expander("⚙️ Settings", expanded=False):
            st.markdown("#### Detection Settings")

            # Default detection strategy
            default_strategy = st.selectbox(
                "Default Detection Strategy",
                options=["auto", "openai", "camel", "ast"],
                index=0,
                help="Choose the default strategy for API detection",
            )

            # File size limit
            max_file_size = st.slider(
                "Max File Size (KB)",
                min_value=10,
                max_value=1000,
                value=50,
                help="Maximum file size to include in analysis",
            )

            # Auto-save sessions
            auto_save = st.checkbox(
                "Auto-save sessions",
                value=True,
                help="Automatically save analysis sessions",
            )

            st.markdown("#### UI Settings")

            # Theme preference (placeholder)
            theme = st.selectbox("Theme", options=["auto", "light", "dark"], index=0)

            # Chat history length
            max_chat_history = st.slider(
                "Max Chat Messages",
                min_value=10,
                max_value=100,
                value=50,
                help="Maximum number of chat messages to keep",
            )

            # Save settings to session state
            if st.button("💾 Save Settings"):
                st.session_state.user_settings = {
                    "default_strategy": default_strategy,
                    "max_file_size": max_file_size * 1024,  # Convert to bytes
                    "auto_save": auto_save,
                    "theme": theme,
                    "max_chat_history": max_chat_history,
                }
                st.success("Settings saved!")

        # About section
        with st.expander("ℹ️ About MCPify", expanded=False):
            st.markdown(
                """
            **MCPify v2.0** - Smart Repository Analyzer

            Transform any code repository into Model Context Protocol servers with AI-powered analysis.

            **Features:**
            - 🤖 AI-powered API detection
            - 💬 Interactive requirement gathering
            - 📚 Session history and management
            - 🎯 Smart suggestions and optimization
            - 🔧 Multiple backend support

            **Supported Project Types:**
            - FastAPI & Flask web applications
            - CLI tools (argparse, click, typer)
            - Python libraries and modules
            - General automation scripts
            """
            )

            if st.button("📖 View Documentation"):
                st.balloons()
                st.info("Documentation will open in a new tab (feature coming soon!)")

    def format_relative_time(self, timestamp: datetime) -> str:
        """Format a timestamp as relative time (e.g., '2 hours ago')."""
        now = datetime.now()
        diff = now - timestamp

        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        else:
            return "Just now"


class NavigationManager:
    """Manages navigation state and flow between different UI phases."""

    def __init__(self):
        # Initialize navigation state
        if "ui_phase" not in st.session_state:
            st.session_state.ui_phase = (
                "input"  # input -> analysis -> chat -> confirmation -> complete
            )

        if "show_examples" not in st.session_state:
            st.session_state.show_examples = True

    def get_current_phase(self) -> str:
        """Get the current UI phase."""
        return st.session_state.ui_phase

    def set_phase(self, phase: str) -> None:
        """Set the current UI phase."""
        valid_phases = ["input", "analysis", "chat", "confirmation", "complete"]
        if phase in valid_phases:
            st.session_state.ui_phase = phase

    def next_phase(self) -> None:
        """Move to the next phase in the workflow."""
        phase_flow = ["input", "analysis", "chat", "confirmation", "complete"]
        current_index = phase_flow.index(st.session_state.ui_phase)

        if current_index < len(phase_flow) - 1:
            st.session_state.ui_phase = phase_flow[current_index + 1]

    def reset_to_input(self) -> None:
        """Reset to the initial input phase."""
        st.session_state.ui_phase = "input"
        st.session_state.show_examples = True

    def render_phase_indicator(self) -> None:
        """Render a visual indicator of the current phase."""
        phases = [
            ("📁", "Input", "Repository input and configuration"),
            ("🔍", "Analysis", "GitIngest processing and code analysis"),
            ("💬", "Chat", "Requirement gathering and smart suggestions"),
            ("✅", "Confirm", "Review and confirm detected tools"),
            ("🎯", "Complete", "Final configuration ready"),
        ]

        current_phase = self.get_current_phase()
        phase_index = ["input", "analysis", "chat", "confirmation", "complete"].index(
            current_phase
        )

        # Create phase indicators
        cols = st.columns(len(phases))

        for i, (icon, title, desc) in enumerate(phases):
            with cols[i]:
                if i <= phase_index:
                    # Completed or current phase
                    if i == phase_index:
                        st.markdown(f"**{icon} {title}**")  # Current
                        st.caption(desc)
                    else:
                        st.markdown(f"{icon} ~~{title}~~")  # Completed
                else:
                    st.markdown(f"{icon} {title}")  # Future
                    st.caption(desc)
