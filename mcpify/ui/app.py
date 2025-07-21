"""
MCPify UI - Streamlit Application

This is the main Streamlit application that provides the complete
intelligent repository analysis workflow with GitIngest-style interface.
"""

import json
import logging
import subprocess
import time
from typing import Any

import streamlit as st

from mcpify.detect.factory import create_detector
from mcpify.gitingest_service import GitIngestError, GitIngestService
from mcpify.ui.components import (
    ChatInterface,
    DetectionResultsInterface,
    NavigationManager,
    SidebarManager,
)
from mcpify.ui.models import (
    AnalysisProgress,
    AnalysisResult,
    MCPConfig,
    RepositoryInfo,
    RepositoryInput,
    ValidationResult,
)
from mcpify.ui.session_manager import SessionManager
from mcpify.validate import MCPConfigValidator

logger = logging.getLogger(__name__)


class MCPifyApp:
    """Main MCPify Streamlit application with intelligent workflow."""

    def __init__(self):
        # Initialize managers and components
        self.session_manager = SessionManager()
        self.navigation_manager = NavigationManager()
        self.sidebar_manager = SidebarManager(self.session_manager)
        self.chat_interface = ChatInterface(self.session_manager)
        self.detection_interface = DetectionResultsInterface(self.session_manager)

        # Example repositories
        self.examples = [
            {
                "name": "FastAPI Todo Server",
                "url": "https://github.com/tiangolo/full-stack-fastapi-template",
                "description": "Modern FastAPI application with database",
            },
            {
                "name": "Flask Example",
                "url": "https://github.com/pallets/flask/tree/main/examples",
                "description": "Official Flask examples",
            },
            {
                "name": "CLI Tool Example",
                "url": "https://github.com/click-contrib/click-examples",
                "description": "Click CLI framework examples",
            },
            {
                "name": "Python API Client",
                "url": "https://github.com/psf/requests",
                "description": "Popular HTTP library for Python",
            },
        ]

    def render_header(self):
        """Render the page header with title and description."""
        st.markdown(
            """
        <div style="text-align: center; padding: 2rem 0;">
            <h1 style="font-size: 3rem; margin: 0.5rem 0;">
                <span style="color: #ff4b4b;">✨</span> MCPify
                <span style="color: #00d4aa;">✨</span>
            </h1>
            <h2 style="font-size: 1.8rem; color: #333; margin: 1rem 0;">
                Turn repositories into MCP servers
            </h2>
            <p style="font-size: 1.1rem; color: #666; max-width: 600px; margin: 0 auto;">
                Analyze any Git repository and automatically generate Model Context Protocol configurations.
                Perfect for integrating existing projects with AI assistants.
            </p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    def render_input_form(self) -> RepositoryInput | None:
        """Render the main input form and return validated input."""
        st.markdown("### 📁 Repository Input")

        # Main input container with styling similar to GitIngest
        with st.container():
            col1, col2 = st.columns([4, 1])

            with col1:
                source = st.text_input(
                    "Repository URL or Path",
                    placeholder="https://github.com/user/repo or /path/to/local/repo",
                    label_visibility="collapsed",
                    help="Enter a GitHub URL or local directory path",
                )

            with col2:
                analyze_button = st.button(
                    "🔍 Analyze", type="primary", use_container_width=True
                )

        # Advanced options in expandable section
        with st.expander("⚙️ Advanced Options", expanded=False):
            col1, col2 = st.columns(2)

            with col1:
                exclude_patterns = st.text_area(
                    "Exclude patterns",
                    value="*.md, __pycache__/, *.pyc, .git/, node_modules/",
                    help="Comma-separated patterns to exclude from analysis",
                )

                max_file_size = st.number_input(
                    "Max file size (KB)",
                    min_value=1,
                    max_value=1000,
                    value=50,
                    help="Maximum file size to include in analysis",
                )

            with col2:
                detection_strategy = st.selectbox(
                    "Detection Strategy",
                    options=["auto", "openai", "camel"],
                    index=0,
                    help="Choose the detection strategy for API analysis",
                )

                include_private = st.checkbox(
                    "Include private repositories",
                    value=False,
                    help="Allow analysis of private repositories (requires authentication)",
                )

        # Process input when analyze button is clicked
        if analyze_button and source:
            try:
                # Determine source type
                source_type = (
                    "url"
                    if source.startswith(("http://", "https://", "git://"))
                    else "local"
                )

                # Parse exclude patterns
                exclude_list = [
                    pattern.strip() for pattern in exclude_patterns.split(",")
                ]

                # Create repository input
                repo_input = RepositoryInput(
                    source=source.strip(),
                    source_type=source_type,
                    exclude_patterns=exclude_list,
                    max_file_size=max_file_size * 1024,  # Convert KB to bytes
                    include_private=include_private,
                    detection_strategy=detection_strategy,
                )

                return repo_input

            except Exception as e:
                st.error(f"Invalid input: {str(e)}")

        return None

    def render_examples(self):
        """Render example repositories section."""
        st.markdown("### 💡 Try these examples:")

        cols = st.columns(len(self.examples))
        for i, example in enumerate(self.examples):
            with cols[i]:
                if st.button(
                    example["name"],
                    help=example["description"],
                    use_container_width=True,
                    key=f"example_{i}",
                ):
                    # Set the example URL in the input field
                    st.session_state["example_url"] = example["url"]
                    st.rerun()

    def render_progress(self, progress: AnalysisProgress):
        """Render analysis progress indicator."""
        st.markdown("### 🔄 Analysis Progress")

        # Progress bar
        st.progress(progress.progress_percentage / 100)

        # Current step info
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(f"**{progress.current_step}**")
            if progress.step_details:
                st.caption(progress.step_details)
        with col2:
            st.write(f"{progress.progress_percentage}%")

        # Step indicators
        steps = ["🔍 GitIngest", "🎯 Detect APIs", "✅ Validate", "✨ Complete"]
        step_cols = st.columns(len(steps))

        current_step_index = min(progress.progress_percentage // 25, len(steps) - 1)

        for i, (col, step) in enumerate(zip(step_cols, steps, strict=True)):
            with col:
                if i <= current_step_index:
                    st.success(step)
                else:
                    st.info(step)

    def analyze_repository(self, repo_input: RepositoryInput) -> AnalysisResult:
        """Perform the complete repository analysis."""
        start_time = time.time()

        # Initialize progress
        progress_placeholder = st.empty()

        try:
            # Step 1: GitIngest processing
            progress = AnalysisProgress(
                "Processing with GitIngest", 10, "Analyzing repository structure..."
            )
            progress_placeholder.empty()
            with progress_placeholder.container():
                self.render_progress(progress)

            with GitIngestService() as gitingest:
                gitingest_result = gitingest.process_repository(
                    repo_input.source,
                    repo_input.source_type,
                    repo_input.exclude_patterns,
                    repo_input.max_file_size,
                )

            # Step 2: API Detection
            progress = AnalysisProgress(
                "Detecting APIs",
                50,
                f"Using {repo_input.detection_strategy} strategy...",
            )
            progress_placeholder.empty()
            with progress_placeholder.container():
                self.render_progress(progress)

            detector = create_detector(repo_input.detection_strategy)
            detection_result = detector._detect_from_content(
                gitingest_result["code_digest"]
            )

            # Step 3: Configuration Generation and Validation
            progress = AnalysisProgress(
                "Validating Configuration", 80, "Checking configuration validity..."
            )
            progress_placeholder.empty()
            with progress_placeholder.container():
                self.render_progress(progress)

            # Create MCP config
            mcp_config = None
            if detection_result.tools:
                mcp_config = MCPConfig(
                    name=detection_result.project_info.name,
                    description=detection_result.project_info.description,
                    backend=detection_result.backend_config,
                    tools=[tool.__dict__ for tool in detection_result.tools],
                )

            # Validate configuration
            validator = MCPConfigValidator()
            validation_result = ValidationResult(is_valid=True)
            if mcp_config:
                validation_result = validator.validate_config(
                    {
                        "name": mcp_config.name,
                        "description": mcp_config.description,
                        "backend": mcp_config.backend,
                        "tools": mcp_config.tools,
                    }
                )

            # Step 4: Complete
            progress = AnalysisProgress(
                "Complete", 100, "Analysis finished successfully!"
            )
            progress_placeholder.empty()
            with progress_placeholder.container():
                self.render_progress(progress)

            # Create repository info
            repo_info = RepositoryInfo(
                name=gitingest_result["repository_info"]["name"],
                description=gitingest_result["repository_info"]["description"],
                language=gitingest_result["repository_info"]["language"],
                framework=gitingest_result["repository_info"]["framework"],
                total_files=gitingest_result["metadata"]["total_files"],
                analyzed_files=gitingest_result["metadata"]["processed_files"],
                file_size_bytes=gitingest_result["metadata"]["total_size"],
            )

            # Create final result
            processing_time = time.time() - start_time
            result = AnalysisResult(
                repository_info=repo_info,
                code_digest=gitingest_result["code_digest"],
                mcp_config=mcp_config,
                detection_summary=f"Detected {len(detection_result.tools)} tools using {repo_input.detection_strategy} strategy.",
                validation_result=validation_result,
                processing_time_seconds=processing_time,
            )

            return result

        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            raise

    def perform_targeted_detection(
        self, code_digest: str, user_requirements: str
    ) -> tuple[list[Any], dict[str, Any]]:
        """Perform targeted API detection based on user requirements."""
        # Use the existing detector but with enhanced focus
        detector = create_detector(
            "auto"
        )  # Use auto-detection for best available strategy
        detection_result = detector._detect_from_content(code_digest)

        # Filter and enhance tools based on user requirements
        relevant_tools = []
        requirements_lower = user_requirements.lower()

        for tool in detection_result.tools:
            # Simple relevance scoring based on requirements
            relevance_score = 0

            # Check for keyword matches
            if any(
                keyword in requirements_lower for keyword in ["api", "endpoint", "rest"]
            ):
                if (
                    "endpoint" in tool.description.lower()
                    or "api" in tool.description.lower()
                ):
                    relevance_score += 2

            if any(
                keyword in requirements_lower
                for keyword in ["command", "cli", "terminal"]
            ):
                if (
                    "command" in tool.description.lower()
                    or "cli" in tool.description.lower()
                ):
                    relevance_score += 2

            if any(
                keyword in requirements_lower
                for keyword in ["function", "library", "module"]
            ):
                if "function" in tool.description.lower():
                    relevance_score += 2

            # Always include tools with some relevance
            if relevance_score > 0 or len(detection_result.tools) <= 3:
                relevant_tools.append(tool)

        final_tools = relevant_tools or detection_result.tools  # Fallback to all tools
        return final_tools, detection_result.backend_config

    def start_mcp_server(self, config: dict[str, Any], port: int):
        """Start MCP server with the given configuration."""
        import tempfile

        try:
            # Create temporary config file
            temp_config = tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False
            )
            json.dump(config, temp_config, indent=2)
            temp_config.close()

            # Build command
            cmd = [
                "python",
                "-m",
                "mcpify.cli",
                "serve",
                temp_config.name,
                "--mode",
                "streamable-http",
                "--port",
                str(port),
            ]

            # Start server process in background
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )

            # Store server info in session state
            st.session_state.mcp_server_running = True
            st.session_state.mcp_server_info = {
                "process": process,
                "config_file": temp_config.name,
                "port": port,
                "cmd": " ".join(cmd),
            }

            st.success(f"🚀 Starting MCP server on port {port}...")
            st.info(f"**Command:** `{' '.join(cmd)}`")

        except Exception as e:
            st.error(f"❌ Failed to start MCP server: {str(e)}")

    def stop_mcp_server(self):
        """Stop the running MCP server."""
        import os

        try:
            if st.session_state.get("mcp_server_running"):
                server_info = st.session_state.get("mcp_server_info", {})
                process = server_info.get("process")
                config_file = server_info.get("config_file")

                if process:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()

                # Clean up temp config file
                if config_file and os.path.exists(config_file):
                    os.unlink(config_file)

                # Clear session state
                st.session_state.mcp_server_running = False
                if "mcp_server_info" in st.session_state:
                    del st.session_state.mcp_server_info

                st.success("⏹️ MCP server stopped successfully!")

        except Exception as e:
            st.error(f"❌ Error stopping server: {str(e)}")

    def render_input_phase(self):
        """Render the initial repository input phase."""
        self.render_header()

        # Handle example URL from session state
        if "example_url" in st.session_state:
            st.session_state["repo_source"] = st.session_state["example_url"]
            del st.session_state["example_url"]

        # Main input form
        repo_input = self.render_input_form()

        # Examples section if enabled
        if st.session_state.get("show_examples", True):
            self.render_examples()

        # Process input and move to analysis
        if repo_input:
            st.session_state.repo_input = repo_input
            self.navigation_manager.set_phase("analysis")
            st.rerun()

    def render_analysis_phase(self):
        """Render the GitIngest analysis phase."""
        st.markdown("### 🔍 Analyzing Repository...")

        repo_input = st.session_state.get("repo_input")
        if not repo_input:
            st.error("No repository input found. Please go back to input phase.")
            return

        try:
            # Perform analysis
            with st.spinner("Processing repository with GitIngest..."):
                result = self.analyze_repository(repo_input)

            if result:
                # Create new session
                self.session_manager.create_new_session(
                    repo_input.source, result.repository_info
                )

                # Update session with analysis result
                self.session_manager.update_current_session(analysis_result=result)

                # Move to chat phase
                self.navigation_manager.set_phase("chat")
                st.success(
                    "✅ Repository analyzed successfully! Let's discuss what you need."
                )
                st.rerun()

        except GitIngestError as e:
            st.error(f"Repository processing failed: {str(e)}")
        except Exception as e:
            st.error(f"Analysis failed: {str(e)}")
            logger.error(f"Unexpected error during analysis: {e}", exc_info=True)

    def render_chat_phase(self):
        """Render the intelligent chat interface phase."""
        current_session = self.session_manager.get_current_session()
        if not current_session:
            st.error("No active session. Please start with repository analysis.")
            return

        # Show repository summary
        with st.expander("📊 Repository Summary", expanded=False):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Repository", current_session.repository_info.name)
            with col2:
                st.metric(
                    "Language", current_session.repository_info.language or "Unknown"
                )
            with col3:
                st.metric("Files", current_session.repository_info.total_files)

        # Render chat interface
        self.chat_interface.render_chat_container()

        # Check if user has provided requirements
        if (
            current_session.user_requirements
            and len(current_session.chat_messages) >= 2
        ):
            if st.button(
                "🎯 Start API Detection", type="primary", use_container_width=True
            ):
                self.navigation_manager.set_phase("confirmation")
                st.rerun()

    def render_confirmation_phase(self):
        """Render the API detection and confirmation phase."""
        current_session = self.session_manager.get_current_session()
        if not current_session or not current_session.user_requirements:
            st.error("Please complete the chat phase first.")
            return

        st.markdown("### 🎯 API Detection & Confirmation")

        # Perform targeted detection based on user requirements
        if "detected_tools" not in st.session_state:
            with st.spinner("Detecting APIs based on your requirements..."):
                detected_tools, backend_config = self.perform_targeted_detection(
                    current_session.analysis_result.code_digest,
                    current_session.user_requirements,
                )
                st.session_state.detected_tools = detected_tools
                st.session_state.backend_config = backend_config

        detected_tools = st.session_state.detected_tools

        # Render confirmation interface
        confirmation = self.detection_interface.render_detection_results(
            detected_tools, current_session.user_requirements
        )

        if confirmation:
            st.session_state.detection_confirmation = confirmation
            self.navigation_manager.set_phase("complete")
            st.rerun()

    def render_complete_phase(self):
        """Render the final configuration phase."""
        confirmation = st.session_state.get("detection_confirmation")
        if not confirmation:
            st.error("No detection confirmation found.")
            return

        # Generate and display final configuration
        final_config = self.detection_interface.render_final_configuration(confirmation)

        if final_config:
            st.success("🎉 MCP Configuration Ready!")

            # Session summary
            current_session = self.session_manager.get_current_session()
            if current_session:
                st.markdown("### 📋 Session Summary")
                st.write(f"**Repository:** {current_session.repository_source}")
                st.write(f"**Requirements:** {current_session.user_requirements}")
                st.write(f"**Tools Generated:** {len(final_config.get('tools', []))}")
                st.write(f"**Chat Messages:** {len(current_session.chat_messages)}")

            # Next Steps section
            st.markdown("### 📋 Next Steps to Test Your MCP Server")

            # Step 1: Save Configuration
            self.render_step_save_config(final_config, current_session)

            # Step 2: Install Dependencies
            self.render_step_install_dependencies(current_session)

            # Step 3: Start MCP Server
            self.render_step_start_server(final_config)

            # Step 4: Test with MCP Inspector
            self.render_step_test_inspector()

        # Action buttons
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🔄 Analyze Another Repository", use_container_width=True):
                self.navigation_manager.reset_to_input()
                # Clear session state
                for key in [
                    "repo_input",
                    "detected_tools",
                    "detection_confirmation",
                    "mcp_server_running",
                ]:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()

        with col2:
            if st.button("🔧 Modify Configuration", use_container_width=True):
                self.navigation_manager.set_phase("confirmation")
                st.rerun()

        with col3:
            if st.button("💾 Save & Start New", use_container_width=True):
                if current_session:
                    self.session_manager.save_session(current_session)
                self.navigation_manager.reset_to_input()
                st.rerun()

    def render(self):
        """Render the complete MCPify application."""
        # Render sidebar first
        sidebar_action = self.sidebar_manager.render_sidebar()
        if sidebar_action == "new_analysis":
            self.navigation_manager.reset_to_input()
            st.rerun()

        # Get current UI phase
        current_phase = self.navigation_manager.get_current_phase()

        # Render phase indicator
        self.navigation_manager.render_phase_indicator()
        st.divider()

        # Route to appropriate phase renderer
        if current_phase == "input":
            self.render_input_phase()
        elif current_phase == "analysis":
            self.render_analysis_phase()
        elif current_phase == "chat":
            self.render_chat_phase()
        elif current_phase == "confirmation":
            self.render_confirmation_phase()
        elif current_phase == "complete":
            self.render_complete_phase()


def main():
    """Main Streamlit application entry point."""
    # Set page configuration
    st.set_page_config(
        page_title="MCPify - Repository Analyzer",
        page_icon="✨",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    # Create and render the app
    app = MCPifyApp()
    app.render()


if __name__ == "__main__":
    main()
