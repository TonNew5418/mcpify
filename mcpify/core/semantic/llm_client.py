import json
import os
from typing import Any, Dict, List

try:
    import openai

    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    import anthropic

    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

from ...models.function import FunctionInfo


class LLMClient:
    """Client for interacting with LLM APIs."""

    def __init__(self, provider: str = "openai", model: str = None):
        self.provider = provider.lower()
        self.model = model or self._get_default_model()
        self.client = self._initialize_client()

    def _get_default_model(self) -> str:
        """Get default model for the provider."""
        if self.provider == "openai":
            return "gpt-4"
        elif self.provider == "anthropic":
            return "claude-3-sonnet-20240229"
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def _initialize_client(self):
        """Initialize the appropriate LLM client."""
        if self.provider == "openai":
            if not HAS_OPENAI:
                raise ImportError(
                    "OpenAI package not installed. Run: pip install openai"
                )
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable not set")
            return openai.OpenAI(api_key=api_key)

        elif self.provider == "anthropic":
            if not HAS_ANTHROPIC:
                raise ImportError(
                    "Anthropic package not installed. Run: pip install anthropic"
                )
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY environment variable not set")
            return anthropic.Anthropic(api_key=api_key)

        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def analyze_user_request(
        self, user_request: str, functions: List[FunctionInfo]
    ) -> List[Dict[str, Any]]:
        """Analyze user request and match it with relevant functions."""
        # Prepare function data for the prompt
        function_data = []
        for func in functions:
            func_dict = func.to_dict()
            function_data.append(
                {
                    "name": func_dict["qualified_name"],
                    "signature": func_dict["signature"],
                    "docstring": func_dict["docstring"] or "No documentation",
                    "file": func_dict["file_path"],
                    "line": func_dict["line_number"],
                }
            )

        prompt = self._create_analysis_prompt(user_request, function_data)

        try:
            response = self._make_llm_call(prompt)
            return self._parse_analysis_response(response)
        except Exception as e:
            print(f"Error analyzing user request: {e}")
            return []

    def _create_analysis_prompt(
        self, user_request: str, functions: List[Dict[str, Any]]
    ) -> str:
        """Create a prompt for analyzing user request against available functions."""
        functions_text = "\n".join(
            [
                f"- {func['name']}: {func['signature']}\n  Doc: {func['docstring']}\n  File: {func['file']}:{func['line']}"
                for func in functions[:50]  # Limit to avoid token limits
            ]
        )

        return f"""You are an expert Python code analyzer. A user wants to create MCP tools from a Python repository.

User Request: "{user_request}"

Available Functions:
{functions_text}

Your task is to identify the 1-3 most relevant functions that match the user's request and generate MCP tool specifications.

For each relevant function, provide:
1. The exact function name
2. A clear tool name (kebab-case)
3. A helpful description for the MCP tool
4. Parameter mappings (which function parameters to expose, with types and descriptions)

Respond with a JSON array of tool specifications. Each tool should have:
{{
  "function_name": "exact.function.name",
  "tool_name": "descriptive-tool-name",
  "description": "Clear description of what this tool does",
  "parameters": [
    {{
      "name": "param_name",
      "type": "string|number|boolean|array|object",
      "description": "Parameter description",
      "required": true|false
    }}
  ]
}}

Focus on functions that directly address the user's needs. If no functions are relevant, return an empty array.

JSON Response:"""

    def _make_llm_call(self, prompt: str) -> str:
        """Make a call to the LLM API."""
        if self.provider == "openai":
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that analyzes code and generates MCP tool specifications. Always respond with valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=2000,
            )
            return response.choices[0].message.content

        elif self.provider == "anthropic":
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text

        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def _parse_analysis_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse the LLM response into structured data."""
        try:
            # Extract JSON from the response
            response = response.strip()

            # Find JSON content
            start_idx = response.find("[")
            end_idx = response.rfind("]") + 1

            if start_idx == -1 or end_idx == 0:
                print("No JSON array found in response")
                return []

            json_str = response[start_idx:end_idx]
            tools = json.loads(json_str)

            # Validate the structure
            validated_tools = []
            for tool in tools:
                if self._validate_tool_spec(tool):
                    validated_tools.append(tool)
                else:
                    print(f"Invalid tool specification: {tool}")

            return validated_tools

        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON response: {e}")
            print(f"Response was: {response}")
            return []
        except Exception as e:
            print(f"Error parsing analysis response: {e}")
            return []

    def _validate_tool_spec(self, tool: Dict[str, any]) -> bool:
        """Validate a tool specification."""
        required_fields = ["function_name", "tool_name", "description", "parameters"]

        if not all(field in tool for field in required_fields):
            return False

        if not isinstance(tool["parameters"], list):
            return False

        for param in tool["parameters"]:
            param_required_fields = ["name", "type", "description", "required"]
            if not all(field in param for field in param_required_fields):
                return False

            if param["type"] not in ["string", "number", "boolean", "array", "object"]:
                return False

        return True

    def enhance_tool_description(
        self, tool_spec: Dict[str, Any], function_info: FunctionInfo
    ) -> Dict[str, Any]:
        """Enhance tool specification with additional context."""
        enhanced_spec = tool_spec.copy()

        # Add source information
        enhanced_spec["source"] = {
            "file": str(function_info.file_path),
            "line": function_info.line_number,
            "signature": function_info.signature,
        }

        # Enhance description if it's too short
        if len(enhanced_spec["description"]) < 20 and function_info.docstring:
            docstring_summary = function_info.docstring.split("\n")[0][:100]
            enhanced_spec[
                "description"
            ] = f"{enhanced_spec['description']} - {docstring_summary}"

        return enhanced_spec
