"""
OpenAI-based project detector.

This module contains the OpenaiDetector class that uses OpenAI's API
for intelligent project analysis and tool detection.
"""

import json
import os
from pathlib import Path
from typing import Any

import openai

from .base import BaseDetector
from .types import ProjectInfo, ToolSpec


class OpenaiDetector(BaseDetector):
    """OpenAI-based project detector that uses LLM for intelligent analysis."""

    def __init__(self, openai_api_key: str | None = None, **kwargs):
        """Initialize the detector with OpenAI API key."""
        super().__init__(**kwargs)
        self.openai_client = None
        if openai_api_key:
            openai.api_key = openai_api_key
            self.openai_client = openai
        elif os.getenv("OPENAI_API_KEY"):
            self.openai_client = openai
        else:
            raise ValueError(
                "OpenAI API key is required for OpenaiDetector. "
                "Provide it via openai_api_key parameter or OPENAI_API_KEY environment variable."
            )

    def _detect_tools(
        self, project_path: Path, project_info: ProjectInfo
    ) -> list[ToolSpec]:
        """Use OpenAI to intelligently detect tools/APIs in the project."""
        if not self.openai_client:
            raise ValueError("OpenAI client not initialized")

        # Gather project context
        context = self._gather_project_context(project_path, project_info)

        # Use LLM to analyze and detect tools
        tools_data = self._llm_detect_tools(context, project_info)

        # Convert to ToolSpec objects
        tools = []
        for tool_data in tools_data:
            tools.append(
                ToolSpec(
                    name=tool_data["name"],
                    description=tool_data["description"],
                    args=tool_data.get("args", []),
                    parameters=tool_data.get("parameters", []),
                )
            )

        return tools

    def _gather_project_context(
        self, project_path: Path, project_info: ProjectInfo
    ) -> str:
        """Gather comprehensive project context for LLM analysis."""
        context_parts = []

        # Basic project info
        context_parts.append(f"Project Name: {project_info.name}")
        context_parts.append(f"Project Type: {project_info.project_type}")
        context_parts.append(f"Description: {project_info.description}")

        # Dependencies
        if project_info.dependencies:
            context_parts.append(
                f"Dependencies: {', '.join(project_info.dependencies)}"
            )

        # README content (truncated)
        if project_info.readme_content:
            readme_excerpt = project_info.readme_content[:2000]
            context_parts.append(f"README:\n{readme_excerpt}")

        # Code samples from main files
        context_parts.append("\nCode samples:")
        for main_file in project_info.main_files[:3]:  # Limit to first 3 files
            file_path = project_path / main_file
            try:
                with open(file_path, encoding="utf-8") as f:
                    content = f.read()[:3000]  # First 3000 chars
                    context_parts.append(f"\n=== {main_file} ===\n{content}")
            except Exception as e:
                context_parts.append(f"\n=== {main_file} ===\nError reading file: {e}")

        return "\n".join(context_parts)

    def _llm_detect_tools(
        self, context: str, project_info: ProjectInfo
    ) -> list[dict[str, Any]]:
        """Use LLM to analyze project and detect tools."""

        system_prompt = """You are an expert software engineer specializing in API analysis and tool detection.
        Your task is to analyze a project and identify all the tools/APIs/commands that can be exposed as MCP (Model Context Protocol) tools.

        For each tool you identify, provide:
        1. name: A clear, descriptive name (snake_case)
        2. description: What the tool does
        3. args: List of command-line arguments or API call structure
        4. parameters: List of parameters with name, type, and description

        Focus on:
        - CLI commands with arguments
        - Web API endpoints
        - Interactive commands
        - Public functions that could be called
        - Any functionality that could be useful as a tool

        Return your analysis as a JSON array of tool specifications."""

        user_prompt = f"""Analyze this project and identify all possible tools/APIs:

        {context}

        Based on the project type ({project_info.project_type}) and the code, identify all tools that could be exposed.
        Consider:
        - Command-line arguments and subcommands
        - API endpoints and routes
        - Interactive command patterns
        - Public functions
        - Any other callable functionality

        Return a JSON array with tool specifications in this exact format:
        [
          {{
            "name": "tool_name",
            "description": "Clear description of what this tool does",
            "args": ["command", "--flag", "{{parameter}}"],
            "parameters": [
              {{
                "name": "parameter",
                "type": "string|integer|number|boolean|array",
                "description": "Parameter description",
                "required": true
              }}
            ]
          }}
        ]"""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
                max_tokens=4000,
            )

            content = response.choices[0].message.content.strip()

            # Extract JSON from response (in case there's extra text)
            start_idx = content.find("[")
            end_idx = content.rfind("]") + 1
            if start_idx != -1 and end_idx != 0:
                json_content = content[start_idx:end_idx]
            else:
                json_content = content

            tools_data = json.loads(json_content)

            # Validate the structure
            if not isinstance(tools_data, list):
                print("Warning: LLM returned non-list response, wrapping in list")
                tools_data = [tools_data] if tools_data else []

            # Validate each tool has required fields
            validated_tools = []
            for tool in tools_data:
                if isinstance(tool, dict) and "name" in tool and "description" in tool:
                    # Set defaults for missing fields
                    if "args" not in tool:
                        tool["args"] = []
                    if "parameters" not in tool:
                        tool["parameters"] = []
                    validated_tools.append(tool)
                else:
                    print(f"Warning: Skipping invalid tool specification: {tool}")

            return validated_tools

        except json.JSONDecodeError as e:
            print(f"Error: Failed to parse LLM response as JSON: {e}")
            print(f"Raw response: {response.choices[0].message.content}")
            return []
        except Exception as e:
            print(f"Error: LLM tool detection failed: {e}")
            return []

    def _enhance_tool_description(self, tool: ToolSpec, context: str) -> ToolSpec:
        """Use LLM to enhance a single tool's description and parameters."""
        try:
            prompt = f"""
            Enhance this tool specification with better descriptions and parameter details:

            Tool: {tool.name}
            Current Description: {tool.description}
            Args: {tool.args}
            Parameters: {tool.parameters}

            Project Context:
            {context[:1000]}

            Provide an enhanced version with:
            1. A clear, helpful description
            2. Better parameter descriptions
            3. Proper parameter types

            Return as JSON in this format:
            {{
              "name": "{tool.name}",
              "description": "Enhanced description",
              "args": {tool.args},
              "parameters": [
                {{
                  "name": "param_name",
                  "type": "string|integer|number|boolean|array",
                  "description": "Clear parameter description",
                  "required": true
                }}
              ]
            }}
            """

            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at writing clear API documentation.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=1000,
            )

            enhanced_data = json.loads(response.choices[0].message.content)
            return ToolSpec(
                name=enhanced_data["name"],
                description=enhanced_data["description"],
                args=enhanced_data.get("args", tool.args),
                parameters=enhanced_data.get("parameters", tool.parameters),
            )

        except Exception as e:
            print(f"Warning: Failed to enhance tool {tool.name}: {e}")
            return tool
