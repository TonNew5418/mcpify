"""
Unit tests for the MCPify validation module.
"""

import json
import tempfile
from pathlib import Path

from mcpify.validate import (
    MCPConfigValidator,
    ValidationError,
    ValidationResult,
    validate_config_dict,
    validate_config_file,
)


class TestValidationError:
    """Test ValidationError dataclass."""

    def test_validation_error_creation(self):
        """Test creating a ValidationError."""
        error = ValidationError("field", "message", "error", "path")
        assert error.field == "field"
        assert error.message == "message"
        assert error.severity == "error"
        assert error.path == "path"

    def test_validation_error_defaults(self):
        """Test ValidationError with default values."""
        error = ValidationError("field", "message")
        assert error.field == "field"
        assert error.message == "message"
        assert error.severity == "error"
        assert error.path == ""


class TestValidationResult:
    """Test ValidationResult dataclass."""

    def test_validation_result_creation(self):
        """Test creating a ValidationResult."""
        result = ValidationResult(True, [], [])
        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []

    def test_add_error(self):
        """Test adding an error to ValidationResult."""
        result = ValidationResult(True, [], [])
        result.add_error("field", "message", "path")

        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.errors[0].field == "field"
        assert result.errors[0].message == "message"
        assert result.errors[0].path == "path"

    def test_add_warning(self):
        """Test adding a warning to ValidationResult."""
        result = ValidationResult(True, [], [])
        result.add_warning("field", "message", "path")

        assert result.is_valid is True  # Warnings don't affect validity
        assert len(result.warnings) == 1
        assert result.warnings[0].field == "field"
        assert result.warnings[0].message == "message"
        assert result.warnings[0].path == "path"

    def test_get_summary_valid(self):
        """Test get_summary for valid config."""
        result = ValidationResult(True, [], [])
        assert result.get_summary() == "✅ Configuration is valid"

    def test_get_summary_errors_and_warnings(self):
        """Test get_summary with errors and warnings."""
        result = ValidationResult(False, [], [])
        result.add_error("field1", "error message")
        result.add_warning("field2", "warning message")

        summary = result.get_summary()
        assert "❌ 1 error(s)" in summary
        assert "⚠️  1 warning(s)" in summary


class TestMCPConfigValidator:
    """Test MCPConfigValidator class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = MCPConfigValidator()

    def test_valid_commandline_config(self):
        """Test validation of a valid commandline configuration."""
        config = {
            "name": "test-api",
            "description": "A test API configuration for validation testing",
            "backend": {
                "type": "commandline",
                "config": {"command": "python3", "args": ["server.py"], "cwd": "."},
            },
            "tools": [
                {
                    "name": "hello",
                    "description": "Say hello",
                    "args": ["hello"],
                    "parameters": [],
                },
                {
                    "name": "echo",
                    "description": "Echo a message",
                    "args": ["echo", "{message}"],
                    "parameters": [
                        {
                            "name": "message",
                            "type": "string",
                            "description": "Message to echo",
                        }
                    ],
                },
            ],
        }

        result = self.validator.validate_config(config)
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 0

    def test_valid_http_config(self):
        """Test validation of a valid HTTP configuration."""
        config = {
            "name": "http-api",
            "description": "An HTTP API configuration for testing",
            "backend": {
                "type": "http",
                "config": {"base_url": "http://localhost:8000", "timeout": 30},
            },
            "tools": [
                {
                    "name": "get_data",
                    "description": "Get data from API",
                    "args": ["/api/data"],
                    "parameters": [],
                }
            ],
        }

        result = self.validator.validate_config(config)
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 0

    def test_valid_websocket_config(self):
        """Test validation of a valid WebSocket configuration."""
        config = {
            "name": "websocket-api",
            "description": "A WebSocket API configuration for testing",
            "backend": {
                "type": "websocket",
                "config": {"url": "ws://localhost:8080/ws"},
            },
            "tools": [
                {
                    "name": "send_message",
                    "description": "Send a message via WebSocket",
                    "args": ["send", "{message}"],
                    "parameters": [
                        {
                            "name": "message",
                            "type": "string",
                            "description": "Message to send",
                        }
                    ],
                }
            ],
        }

        result = self.validator.validate_config(config)
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 0

    def test_missing_required_fields(self):
        """Test validation with missing required fields."""
        config = {
            "name": "test-api"
            # Missing description, backend, tools
        }

        result = self.validator.validate_config(config)
        assert result.is_valid is False
        assert len(result.errors) == 3  # Missing description, backend, tools

        error_fields = [error.field for error in result.errors]
        assert "description" in error_fields
        assert "backend" in error_fields
        assert "tools" in error_fields

    def test_invalid_name(self):
        """Test validation with invalid name."""
        config = {
            "name": "",  # Empty name
            "description": "Test description",
            "backend": {"type": "commandline", "config": {"command": "python3"}},
            "tools": [],
        }

        result = self.validator.validate_config(config)
        assert result.is_valid is False
        assert any(error.field == "name" for error in result.errors)

    def test_invalid_backend_type(self):
        """Test validation with invalid backend type."""
        config = {
            "name": "test-api",
            "description": "Test description",
            "backend": {"type": "invalid-type", "config": {"command": "python3"}},
            "tools": [],
        }

        result = self.validator.validate_config(config)
        assert result.is_valid is False
        assert any(error.field == "backend.type" for error in result.errors)

    def test_missing_backend_config(self):
        """Test validation with missing backend config."""
        config = {
            "name": "test-api",
            "description": "Test description",
            "backend": {
                "type": "commandline"
                # Missing config
            },
            "tools": [],
        }

        result = self.validator.validate_config(config)
        assert result.is_valid is False
        assert any(error.field == "backend.config" for error in result.errors)

    def test_invalid_commandline_backend(self):
        """Test validation with invalid commandline backend."""
        config = {
            "name": "test-api",
            "description": "Test description",
            "backend": {
                "type": "commandline",
                "config": {
                    "command": "",  # Empty command
                    "args": [123],  # Non-string arg
                    "cwd": 456,  # Non-string cwd
                },
            },
            "tools": [],
        }

        result = self.validator.validate_config(config)
        assert result.is_valid is False

        # Should have errors for empty command, invalid args, invalid cwd
        error_fields = [error.field for error in result.errors]
        assert "backend.config.command" in error_fields
        assert any("backend.config.args" in field for field in error_fields)
        assert "backend.config.cwd" in error_fields

    def test_invalid_http_backend(self):
        """Test validation with invalid HTTP backend."""
        config = {
            "name": "test-api",
            "description": "Test description",
            "backend": {
                "type": "http",
                "config": {
                    "base_url": "invalid-url",  # Invalid URL
                    "timeout": -5,  # Negative timeout
                },
            },
            "tools": [],
        }

        result = self.validator.validate_config(config)
        assert result.is_valid is False

        error_fields = [error.field for error in result.errors]
        assert "backend.config.base_url" in error_fields
        assert "backend.config.timeout" in error_fields

    def test_invalid_websocket_backend(self):
        """Test validation with invalid WebSocket backend."""
        config = {
            "name": "test-api",
            "description": "Test description",
            "backend": {
                "type": "websocket",
                "config": {
                    "url": "http://localhost:8080"  # Should start with ws://
                },
            },
            "tools": [],
        }

        result = self.validator.validate_config(config)
        assert result.is_valid is False
        assert any(error.field == "backend.config.url" for error in result.errors)

    def test_duplicate_tool_names(self):
        """Test validation with duplicate tool names."""
        config = {
            "name": "test-api",
            "description": "Test description",
            "backend": {"type": "commandline", "config": {"command": "python3"}},
            "tools": [
                {"name": "duplicate", "description": "First tool", "args": ["cmd1"]},
                {
                    "name": "duplicate",  # Duplicate name
                    "description": "Second tool",
                    "args": ["cmd2"],
                },
            ],
        }

        result = self.validator.validate_config(config)
        assert result.is_valid is False
        assert any("Duplicate tool name" in error.message for error in result.errors)

    def test_invalid_tool_structure(self):
        """Test validation with invalid tool structure."""
        config = {
            "name": "test-api",
            "description": "Test description",
            "backend": {"type": "commandline", "config": {"command": "python3"}},
            "tools": [
                {
                    "name": "",  # Empty name
                    "description": "",  # Empty description
                    "args": [123],  # Non-string arg
                    "parameters": [
                        {
                            "name": "param1",
                            "type": "invalid-type",  # Invalid type
                            "description": "",  # Empty description
                        }
                    ],
                }
            ],
        }

        result = self.validator.validate_config(config)
        assert result.is_valid is False
        assert len(result.errors) > 0
        assert len(result.warnings) > 0

    def test_parameter_consistency(self):
        """Test validation of parameter consistency."""
        config = {
            "name": "test-api",
            "description": "Test description",
            "backend": {"type": "commandline", "config": {"command": "python3"}},
            "tools": [
                {
                    "name": "test_tool",
                    "description": "Test tool",
                    "args": ["cmd", "{missing_param}"],  # References undefined
                    "parameters": [
                        {
                            "name": "unused_param",  # Defined but not used
                            "type": "string",
                            "description": "Unused parameter",
                        }
                    ],
                }
            ],
        }

        result = self.validator.validate_config(config)
        assert result.is_valid is False

        # Should have error for missing parameter
        assert any("missing_param" in error.message for error in result.errors)

        # Should have warning for unused parameter
        assert any("unused_param" in warning.message for warning in result.warnings)

    def test_warnings_only(self):
        """Test configuration that's valid but has warnings."""
        config = {
            "name": "test-api",
            "description": "Short",  # Too short (warning)
            "backend": {"type": "commandline", "config": {"command": "python3"}},
            "tools": [
                {
                    "name": "test-tool",  # Invalid identifier (warning)
                    "description": "Test tool",
                    "args": ["cmd"],
                }
            ],
        }

        result = self.validator.validate_config(config)
        assert result.is_valid is True  # No errors, just warnings
        assert len(result.warnings) > 0


class TestValidationFunctions:
    """Test module-level validation functions."""

    def test_validate_config_dict(self):
        """Test validate_config_dict function."""
        config = {
            "name": "test-api",
            "description": "Test description",
            "backend": {"type": "commandline", "config": {"command": "python3"}},
            "tools": [],
        }

        result = validate_config_dict(config)
        assert isinstance(result, ValidationResult)
        assert result.is_valid is True

    def test_validate_config_file_valid(self):
        """Test validate_config_file with valid file."""
        config = {
            "name": "test-api",
            "description": "Test description",
            "backend": {"type": "commandline", "config": {"command": "python3"}},
            "tools": [],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config, f)
            temp_path = f.name

        try:
            result = validate_config_file(temp_path)
            assert isinstance(result, ValidationResult)
            assert result.is_valid is True
        finally:
            Path(temp_path).unlink()

    def test_validate_config_file_not_found(self):
        """Test validate_config_file with non-existent file."""
        result = validate_config_file("non-existent-file.json")
        assert result.is_valid is False
        assert any("not found" in error.message for error in result.errors)

    def test_validate_config_file_invalid_json(self):
        """Test validate_config_file with invalid JSON."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{ invalid json }")
            temp_path = f.name

        try:
            result = validate_config_file(temp_path)
            assert result.is_valid is False
            assert any("Invalid JSON" in error.message for error in result.errors)
        finally:
            Path(temp_path).unlink()


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = MCPConfigValidator()

    def test_non_dict_config(self):
        """Test validation with non-dictionary config."""
        result = self.validator.validate_config("not a dict")
        assert result.is_valid is False
        assert any("must be a JSON object" in error.message for error in result.errors)

    def test_empty_tools_array(self):
        """Test validation with empty tools array."""
        config = {
            "name": "test-api",
            "description": "Test description",
            "backend": {"type": "commandline", "config": {"command": "python3"}},
            "tools": [],
        }

        result = self.validator.validate_config(config)
        assert result.is_valid is True
        assert any("No tools defined" in warning.message for warning in result.warnings)

    def test_unknown_fields(self):
        """Test validation with unknown fields."""
        config = {
            "name": "test-api",
            "description": "Test description",
            "backend": {"type": "commandline", "config": {"command": "python3"}},
            "tools": [],
            "unknown_field": "value",  # Unknown field
        }

        result = self.validator.validate_config(config)
        assert result.is_valid is True
        assert any("Unknown field" in warning.message for warning in result.warnings)

    def test_very_long_name(self):
        """Test validation with very long name."""
        config = {
            "name": "a" * 150,  # Very long name
            "description": "Test description",
            "backend": {"type": "commandline", "config": {"command": "python3"}},
            "tools": [],
        }

        result = self.validator.validate_config(config)
        assert result.is_valid is True
        assert any("quite long" in warning.message for warning in result.warnings)

    def test_very_long_description(self):
        """Test validation with very long description."""
        config = {
            "name": "test-api",
            "description": "a" * 1500,  # Very long description
            "backend": {"type": "commandline", "config": {"command": "python3"}},
            "tools": [],
        }

        result = self.validator.validate_config(config)
        assert result.is_valid is True
        assert any("quite long" in warning.message for warning in result.warnings)
