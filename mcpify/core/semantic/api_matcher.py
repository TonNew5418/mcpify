from typing import Any, Dict, List, Optional

from ...models.function import FunctionInfo
from ...models.tool import MCPTool, MCPToolParameter
from .embeddings import create_embedding_provider
from .llm_client import LLMClient


class APIMatcher:
    """Match user requirements to repository functions and generate MCP tools."""

    def __init__(
        self,
        llm_provider: str = "openai",
        llm_model: str = None,
        embedding_provider: str = "sentence_transformers",
        embedding_model: str = None,
    ):
        self.llm_client = LLMClient(provider=llm_provider, model=llm_model)

        # Initialize embedding provider
        embedding_kwargs = {}
        if embedding_model:
            if embedding_provider == "sentence_transformers":
                embedding_kwargs["model_name"] = embedding_model
            elif embedding_provider == "openai":
                embedding_kwargs["model_name"] = embedding_model

        try:
            self.embedding_provider = create_embedding_provider(
                embedding_provider, **embedding_kwargs
            )
            self.use_embeddings = True
        except Exception as e:
            print(
                f"Warning: Failed to initialize embedding provider '{embedding_provider}': {e}"
            )
            print("Falling back to keyword-based matching")
            self.embedding_provider = None
            self.use_embeddings = False

    def generate_tools(
        self, user_request: str, functions: List[FunctionInfo]
    ) -> List[MCPTool]:
        """Generate MCP tools based on user request and available functions."""
        if not functions:
            print("No functions available for analysis")
            return []

        print(f"Analyzing {len(functions)} functions for request: '{user_request}'")

        # Get LLM analysis
        tool_specs = self.llm_client.analyze_user_request(user_request, functions)

        if not tool_specs:
            print("No relevant functions found for the user request")
            return []

        print(f"LLM identified {len(tool_specs)} relevant tools")

        # Convert specifications to MCPTool objects
        mcp_tools = []
        function_lookup = {f.qualified_name: f for f in functions}

        for spec in tool_specs:
            tool = self._create_mcp_tool(spec, function_lookup)
            if tool:
                mcp_tools.append(tool)

        return mcp_tools

    def _create_mcp_tool(
        self, spec: Dict[str, Any], function_lookup: Dict[str, FunctionInfo]
    ) -> Optional[MCPTool]:
        """Create an MCP tool from a specification."""
        try:
            function_name = spec["function_name"]

            # Find the corresponding function
            function_info = function_lookup.get(function_name)
            if not function_info:
                # Try to find by simple name if qualified name doesn't match
                for func in function_lookup.values():
                    if func.name == function_name or func.qualified_name.endswith(
                        f".{function_name}"
                    ):
                        function_info = func
                        break

            if not function_info:
                print(f"Function '{function_name}' not found in available functions")
                return None

            # Create MCP tool parameters
            mcp_parameters = []
            for param_spec in spec["parameters"]:
                mcp_param = MCPToolParameter(
                    name=param_spec["name"],
                    type=param_spec["type"],
                    description=param_spec["description"],
                    required=param_spec["required"],
                )
                mcp_parameters.append(mcp_param)

            # Create the MCP tool
            mcp_tool = MCPTool(
                name=spec["tool_name"],
                description=spec["description"],
                function_info=function_info,
                parameters=mcp_parameters,
                implementation_type="python_function",
            )

            return mcp_tool

        except Exception as e:
            print(f"Error creating MCP tool from spec {spec}: {e}")
            return None

    def filter_functions(
        self, functions: List[FunctionInfo], filters: Dict[str, Any] = None
    ) -> List[FunctionInfo]:
        """Filter functions based on various criteria."""
        if not filters:
            filters = {}

        filtered = functions.copy()

        # Filter out private functions by default
        if filters.get("include_private", False) is False:
            filtered = [
                f
                for f in filtered
                if not f.name.startswith("_") or f.name.startswith("__")
            ]

        # Filter by minimum docstring length
        min_doc_length = filters.get("min_docstring_length", 10)
        if min_doc_length > 0:
            filtered = [
                f
                for f in filtered
                if f.docstring and len(f.docstring) >= min_doc_length
            ]

        # Filter by maximum parameter count
        max_params = filters.get("max_parameters", 10)
        filtered = [f for f in filtered if len(f.parameters) <= max_params]

        # Filter by file patterns
        include_patterns = filters.get("include_files", [])
        if include_patterns:
            filtered = [
                f
                for f in filtered
                if any(pattern in str(f.file_path) for pattern in include_patterns)
            ]

        exclude_patterns = filters.get("exclude_files", ["test", "__pycache__", ".git"])
        filtered = [
            f
            for f in filtered
            if not any(pattern in str(f.file_path) for pattern in exclude_patterns)
        ]

        return filtered

    def rank_functions_by_relevance(
        self, functions: List[FunctionInfo], user_request: str
    ) -> List[FunctionInfo]:
        """Rank functions by relevance to user request using embeddings or keyword matching."""
        if self.use_embeddings and self.embedding_provider:
            return self._rank_with_embeddings(functions, user_request)
        else:
            return self._rank_with_keywords(functions, user_request)

    def _rank_with_embeddings(
        self, functions: List[FunctionInfo], user_request: str
    ) -> List[FunctionInfo]:
        """Rank functions using semantic embeddings."""
        if not functions:
            return []

        # Create comprehensive text representation for each function
        function_texts = []
        for func in functions:
            # Combine function name, docstring, class context, and file context
            parts = []

            # Function name (replace underscores for better semantic understanding)
            parts.append(func.name.replace("_", " "))

            # Class context
            if func.class_name:
                parts.append(f"class {func.class_name.replace('_', ' ')}")

            # Function signature (simplified)
            if func.signature:
                # Extract parameter names for context
                param_names = [
                    p.name for p in func.parameters if not p.name.startswith("self")
                ]
                if param_names:
                    parts.append(f"parameters: {' '.join(param_names)}")

            # Docstring (most important)
            if func.docstring:
                # Take first few lines of docstring for relevance
                doc_lines = func.docstring.strip().split("\n")[:3]
                clean_doc = " ".join(line.strip() for line in doc_lines if line.strip())
                parts.append(clean_doc)

            # File context (extract meaningful names from path)
            file_stem = func.file_path.stem
            if file_stem not in ["main", "__init__", "utils"]:
                parts.append(file_stem.replace("_", " "))

            function_texts.append(" ".join(parts))

        try:
            # Encode all function texts and user request
            all_texts = function_texts + [user_request]
            embeddings = self.embedding_provider.encode(all_texts)

            # Split embeddings
            func_embeddings = embeddings[:-1]  # All but last
            query_embedding = embeddings[-1]  # Last one

            # Compute similarities
            similarities = self.embedding_provider.compute_similarity(
                query_embedding, func_embeddings
            )

            # Create scored functions list
            scored_functions = list(zip(functions, similarities))

            # Sort by similarity (descending)
            scored_functions.sort(key=lambda x: x[1], reverse=True)

            # Filter by minimum similarity threshold (very lenient to catch edge cases)
            min_similarity = -0.1  # Allow functions with very low similarity (embeddings can be negative)
            filtered_functions = [
                func for func, sim in scored_functions if sim >= min_similarity
            ]

            print("Embedding similarity scores:")
            for func, sim in scored_functions[:5]:  # Show top 5
                print(f"  {func.name}: {sim:.3f}")

            return filtered_functions

        except Exception as e:
            print(f"Error in embedding-based ranking: {e}")
            print("Falling back to keyword-based matching")
            return self._rank_with_keywords(functions, user_request)

    def _rank_with_keywords(
        self, functions: List[FunctionInfo], user_request: str
    ) -> List[FunctionInfo]:
        """Rank functions using keyword-based heuristics (fallback method)."""

        def calculate_relevance_score(func: FunctionInfo) -> float:
            score = 0.0
            user_words = set(user_request.lower().split())

            # Check function name
            func_name_words = set(func.name.lower().replace("_", " ").split())
            score += len(user_words.intersection(func_name_words)) * 3

            # Check docstring
            if func.docstring:
                doc_words = set(func.docstring.lower().split())
                score += len(user_words.intersection(doc_words)) * 2

            # Check class name if it's a method
            if func.class_name:
                class_words = set(func.class_name.lower().replace("_", " ").split())
                score += len(user_words.intersection(class_words)) * 1.5

            # Check file path
            file_words = set(
                str(func.file_path).lower().replace("/", " ").replace("_", " ").split()
            )
            score += len(user_words.intersection(file_words)) * 1

            # Bonus for functions with good documentation
            if func.docstring and len(func.docstring) > 50:
                score += 1

            # Bonus for functions with reasonable parameter counts
            if 1 <= len(func.parameters) <= 5:
                score += 0.5

            return score

        # Calculate scores and sort
        scored_functions = [
            (func, calculate_relevance_score(func)) for func in functions
        ]
        scored_functions.sort(key=lambda x: x[1], reverse=True)

        # Fixed: Use >= 0 instead of > 0 to include functions with small positive scores
        return [func for func, score in scored_functions if score >= 0]

    def get_function_summary(self, functions: List[FunctionInfo]) -> Dict[str, Any]:
        """Get a summary of available functions."""
        summary = {
            "total_functions": len(functions),
            "by_file": {},
            "by_class": {},
            "with_docstring": 0,
            "async_functions": 0,
            "methods": 0,
            "parameter_stats": {"min": float("inf"), "max": 0, "avg": 0},
        }

        param_counts = []

        for func in functions:
            # Count by file
            file_key = str(func.file_path)
            summary["by_file"][file_key] = summary["by_file"].get(file_key, 0) + 1

            # Count by class
            class_key = func.class_name or "module_level"
            summary["by_class"][class_key] = summary["by_class"].get(class_key, 0) + 1

            # Other stats
            if func.docstring:
                summary["with_docstring"] += 1

            if func.is_async:
                summary["async_functions"] += 1

            if func.is_method:
                summary["methods"] += 1

            param_count = len(func.parameters)
            param_counts.append(param_count)
            summary["parameter_stats"]["min"] = min(
                summary["parameter_stats"]["min"], param_count
            )
            summary["parameter_stats"]["max"] = max(
                summary["parameter_stats"]["max"], param_count
            )

        if param_counts:
            summary["parameter_stats"]["avg"] = sum(param_counts) / len(param_counts)
            if summary["parameter_stats"]["min"] == float("inf"):
                summary["parameter_stats"]["min"] = 0

        return summary
