"""
Chat Interface Components for MCPify UI.

This module provides the interactive chat interface for requirement gathering
and smart suggestions.
"""

from typing import Any, Optional

import streamlit as st

from mcpify.ui.models import (
    ChatMessage,
    DetectionConfirmation,
    ProjectSession,
    SmartSuggestion,
    ToolSpec,
    UserRequirement,
)
from mcpify.ui.session_manager import RequirementAnalyzer, SessionManager


class ChatInterface:
    """Interactive chat interface for user requirement gathering."""

    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager
        self.requirement_analyzer = RequirementAnalyzer()

    def render_chat_container(self) -> Optional[str]:
        """Render the main chat interface and return user input if any."""
        st.markdown("### 💬 Smart Assistant")

        current_session = self.session_manager.get_current_session()
        if not current_session:
            st.info("Please analyze a repository first to start the conversation.")
            return None

        # Display chat history
        self.render_chat_history(current_session.chat_messages)

        # Show smart suggestions if available
        self.render_smart_suggestions(current_session)

        # User input
        with st.container():
            st.markdown(
                "**What specific functionality do you need from this repository?**"
            )

            col1, col2 = st.columns([4, 1])

            with col1:
                user_input = st.text_input(
                    "Your requirements",
                    placeholder="e.g., I need REST API endpoints for user management",
                    label_visibility="collapsed",
                    key="chat_input",
                )

            with col2:
                send_button = st.button(
                    "💬 Send", type="primary", use_container_width=True
                )

        # Process user input
        if send_button and user_input:
            self.process_user_input(user_input)
            st.rerun()

        return user_input if send_button and user_input else None

    def render_chat_history(self, messages: list[ChatMessage]) -> None:
        """Render the chat message history."""
        if not messages:
            # Initial greeting
            with st.chat_message("assistant"):
                st.write(
                    "👋 Hi! I've analyzed your repository. What specific functionality would you like to extract as MCP tools?"
                )
            return

        for message in messages:
            with st.chat_message(message.role):
                st.write(message.content)

                # Show metadata if available
                if message.metadata:
                    if "suggestions" in message.metadata:
                        with st.expander("💡 Suggestions"):
                            for suggestion in message.metadata["suggestions"]:
                                st.info(
                                    f"**{suggestion['title']}**: {suggestion['description']}"
                                )

    def render_smart_suggestions(self, session: ProjectSession) -> None:
        """Render AI-generated smart suggestions."""
        if not session.analysis_result:
            return

        # Generate suggestions based on repository
        suggestions = self.requirement_analyzer.generate_suggestions(
            session.repository_info,
            UserRequirement(
                functionality_type="other",
                specific_needs=["general"],
                preferred_interface="rest",
                description="General functionality",
            ),
        )

        if suggestions:
            with st.expander("🤖 Smart Suggestions", expanded=False):
                st.markdown("Based on your repository, here are some recommendations:")

                for suggestion in suggestions:
                    with st.container():
                        col1, col2 = st.columns([3, 1])

                        with col1:
                            st.markdown(f"**{suggestion.title}**")
                            st.caption(suggestion.description)
                            if suggestion.implementation_hint:
                                st.caption(f"💡 *{suggestion.implementation_hint}*")

                        with col2:
                            confidence_color = (
                                "green"
                                if suggestion.confidence > 0.8
                                else "orange"
                                if suggestion.confidence > 0.6
                                else "red"
                            )
                            st.markdown(
                                f"<span style='color: {confidence_color}'>🎯 {suggestion.confidence:.0%}</span>",
                                unsafe_allow_html=True,
                            )

                            if st.button(
                                "Use This",
                                key=f"suggest_{suggestion.title.replace(' ', '_')}",
                            ):
                                self.apply_suggestion(suggestion)
                                st.rerun()

    def process_user_input(self, user_input: str) -> None:
        """Process user input and generate response."""
        current_session = self.session_manager.get_current_session()
        if not current_session:
            return

        # Add user message to chat
        self.session_manager.add_chat_message("user", user_input)

        # Analyze user requirements
        user_requirement = self.requirement_analyzer.analyze_user_input(
            user_input, current_session.repository_info
        )

        # Update session with requirements
        self.session_manager.update_current_session(user_requirements=user_input)

        # Generate assistant response
        response = self.generate_assistant_response(user_requirement, current_session)

        # Add assistant message
        self.session_manager.add_chat_message(
            "assistant", response["content"], response.get("metadata")
        )

    def generate_assistant_response(
        self, requirement: UserRequirement, session: ProjectSession
    ) -> dict[str, Any]:
        """Generate intelligent assistant response."""
        responses = {
            "api": "Great! I'll focus on detecting REST API endpoints and HTTP services. Let me analyze the code for route definitions and API patterns.",
            "cli": "Perfect! I'll look for command-line interfaces, argument parsers, and CLI tools in your repository.",
            "library": "Excellent! I'll identify reusable functions and classes that can be exposed as callable tools.",
            "automation": "Wonderful! I'll search for automation scripts, batch processes, and scheduled tasks.",
            "other": "Understood! Let me perform a comprehensive analysis to identify all available functionality.",
        }

        base_response = responses.get(
            requirement.functionality_type, responses["other"]
        )

        # Add specific details based on repository info
        details = []
        if session.repository_info.framework:
            if session.repository_info.framework in ["fastapi", "flask"]:
                details.append(
                    f"I detected a {session.repository_info.framework} application - I'll extract HTTP endpoints and route handlers."
                )
            elif session.repository_info.framework in ["click", "argparse"]:
                details.append(
                    f"I found {session.repository_info.framework} command patterns - I'll map CLI commands to MCP tools."
                )

        if session.repository_info.language == "python":
            details.append(
                "Since this is a Python project, I can also create direct function call interfaces."
            )

        full_response = base_response
        if details:
            full_response += "\n\n" + " ".join(details)

        # Generate suggestions
        suggestions = self.requirement_analyzer.generate_suggestions(
            session.repository_info, requirement
        )
        suggestion_data = [
            {"title": s.title, "description": s.description, "confidence": s.confidence}
            for s in suggestions
        ]

        return {
            "content": full_response,
            "metadata": {
                "requirement_type": requirement.functionality_type,
                "suggestions": suggestion_data,
            },
        }

    def apply_suggestion(self, suggestion: SmartSuggestion) -> None:
        """Apply a smart suggestion to the current analysis."""
        current_session = self.session_manager.get_current_session()
        if not current_session:
            return

        # Add message about applying suggestion
        message = f"✅ Applying suggestion: **{suggestion.title}**\n\n{suggestion.description}"
        if suggestion.implementation_hint:
            message += f"\n\n💡 Implementation: {suggestion.implementation_hint}"

        self.session_manager.add_chat_message("assistant", message)

        # Update session requirements based on suggestion
        suggestion_text = f"Using {suggestion.title}: {suggestion.description}"
        current_requirements = current_session.user_requirements
        updated_requirements = (
            f"{current_requirements}\n{suggestion_text}"
            if current_requirements
            else suggestion_text
        )

        self.session_manager.update_current_session(
            user_requirements=updated_requirements
        )


class DetectionResultsInterface:
    """Interface for displaying and confirming detected APIs."""

    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager

    def render_detection_results(
        self, detected_tools: list[ToolSpec], user_requirements: str
    ) -> Optional[DetectionConfirmation]:
        """Render detected tools and get user confirmation."""
        if not detected_tools:
            st.warning("No tools were detected based on your requirements.")
            return None

        st.markdown("### 🎯 Detected APIs & Tools")
        st.markdown(f"Based on your requirements: *{user_requirements}*")

        # Display detected tools in an organized way
        user_confirmed = []
        user_rejected = []
        user_additions = []

        with st.container():
            st.markdown("**Please review and confirm the detected tools:**")

            for i, tool in enumerate(detected_tools):
                with st.expander(f"🔧 {tool.name}", expanded=True):
                    col1, col2, col3 = st.columns([2, 2, 1])

                    with col1:
                        st.write(f"**Description:** {tool.description}")
                        if tool.args:
                            st.code(" ".join(tool.args), language="bash")

                    with col2:
                        if tool.parameters:
                            st.write("**Parameters:**")
                            for param in tool.parameters:
                                st.caption(
                                    f"• {param.get('name', 'unknown')}: {param.get('description', 'No description')}"
                                )
                        else:
                            st.caption("No parameters required")

                    with col3:
                        confirm_key = f"confirm_{tool.name}_{i}"

                        if st.checkbox("✅ Include", value=True, key=confirm_key):
                            if tool.name not in user_confirmed:
                                user_confirmed.append(tool.name)
                        else:
                            if tool.name not in user_rejected:
                                user_rejected.append(tool.name)

        # Additional tools section
        with st.expander("➕ Add Additional Tools", expanded=False):
            st.markdown("Need additional functionality not detected above?")

            add_tool_name = st.text_input(
                "Tool Name", placeholder="e.g., custom_function"
            )
            add_tool_desc = st.text_input(
                "Description", placeholder="e.g., Performs custom data processing"
            )
            add_tool_command = st.text_input(
                "Command", placeholder="e.g., python script.py --input"
            )

            if st.button("Add Tool"):
                if add_tool_name and add_tool_desc:
                    user_additions.append(
                        {
                            "name": add_tool_name,
                            "description": add_tool_desc,
                            "args": add_tool_command.split()
                            if add_tool_command
                            else [],
                            "parameters": [],
                        }
                    )
                    st.success(f"Added {add_tool_name} to the configuration!")

        # Notes section
        notes = st.text_area(
            "Additional Notes",
            placeholder="Any special requirements or modifications needed?",
            height=100,
        )

        # Confirmation button
        if st.button("🎯 Generate Final Configuration", type="primary"):
            confirmation = DetectionConfirmation(
                detected_tools=detected_tools,
                user_confirmed=user_confirmed,
                user_rejected=user_rejected,
                user_additions=user_additions,
                notes=notes,
            )

            return confirmation

        return None

    def render_final_configuration(
        self, confirmation: DetectionConfirmation
    ) -> Optional[dict[str, Any]]:
        """Render the final MCP configuration based on user confirmation."""
        st.markdown("### ✅ Final MCP Configuration")

        # Build final tool list
        final_tools = []

        # Add confirmed tools
        for tool in confirmation.detected_tools:
            if tool.name in confirmation.user_confirmed:
                final_tools.append(
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "args": tool.args,
                        "parameters": list(tool.parameters),
                    }
                )

        # Add user additions
        final_tools.extend(confirmation.user_additions)

        # Get current session for backend config
        current_session = self.session_manager.get_current_session()
        if not current_session or not current_session.analysis_result:
            st.error("No analysis result available")
            return None

        # Create final configuration
        # Get backend config from session state (saved during detection) or create a default one
        backend_config = st.session_state.get("backend_config")

        # Create default backend config if not available
        if not backend_config:
            # Determine backend type based on repository info
            repo_info = current_session.repository_info
            if repo_info.language == "python":
                backend_config = {
                    "type": "commandline",
                    "config": {
                        "command": "python3",
                        "args": [f"{repo_info.name}.py"],  # or main file
                        "cwd": ".",
                    },
                }
            else:
                backend_config = {
                    "type": "commandline",
                    "config": {"command": "bash", "args": ["run.sh"], "cwd": "."},
                }

        final_config = {
            "name": current_session.repository_info.name,
            "description": f"MCP server for {current_session.repository_info.name}",
            "backend": backend_config,
            "tools": final_tools,
        }

        # Display configuration
        st.json(final_config)

        # Download button
        import json

        config_json = json.dumps(final_config, indent=2)
        st.download_button(
            "📥 Download MCP Configuration",
            config_json,
            f"{current_session.repository_info.name}_mcp_config.json",
            "application/json",
            use_container_width=True,
        )

        # Update session with final config
        from mcpify.ui.models import MCPConfig

        mcp_config = MCPConfig(
            name=final_config["name"],
            description=final_config["description"],
            backend=final_config["backend"],
            tools=final_config["tools"],
        )

        self.session_manager.update_current_session(final_config=mcp_config)

        return final_config
