"""Tests for configuration validation functionality."""

import os
import tempfile
import pytest

from yet_claude_code.cli.validators import (
    ConfigValidator,
    ValidationReporter,
    ValidationSeverity,
    ValidationIssue,
)
from yet_claude_code.cli.config import Config


class TestConfigValidator:
    """Test configuration validation logic."""

    def test_valid_provider_config(self):
        """Test validation of valid provider configuration."""
        validator = ConfigValidator()

        # Test with valid OpenAI config
        issues = validator.validate_provider_config(
            "openai", "o3-mini", "sk-test123456789"
        )

        # Should have no errors, maybe warnings about unknown model
        errors = [
            issue for issue in issues if issue.severity == ValidationSeverity.ERROR
        ]
        assert len(errors) == 0

    def test_invalid_provider(self):
        """Test validation with invalid provider."""
        validator = ConfigValidator()

        issues = validator.validate_provider_config(
            "invalid_provider", "some-model", "api-key"
        )

        errors = [
            issue for issue in issues if issue.severity == ValidationSeverity.ERROR
        ]
        assert len(errors) >= 1
        assert any("Unknown provider" in issue.message for issue in errors)

    def test_missing_api_key(self):
        """Test validation with missing API key."""
        validator = ConfigValidator()

        # Clear any existing OpenAI API key for this test
        original_key = os.environ.get("OPENAI_API_KEY")
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]

        try:
            issues = validator.validate_provider_config("openai", "gpt-4", None)

            errors = [
                issue for issue in issues if issue.severity == ValidationSeverity.ERROR
            ]
            assert len(errors) >= 1
            assert any("Missing API key" in issue.message for issue in errors)
        finally:
            # Restore original key if it existed
            if original_key:
                os.environ["OPENAI_API_KEY"] = original_key

    def test_invalid_mcp_server_config(self):
        """Test validation of invalid MCP server configuration."""
        validator = ConfigValidator()

        # Missing required fields
        invalid_config = {"name": "test"}
        issues = validator.validate_mcp_server_config(invalid_config)

        errors = [
            issue for issue in issues if issue.severity == ValidationSeverity.ERROR
        ]
        assert len(errors) >= 2  # Missing transport and command

    def test_valid_mcp_server_config(self):
        """Test validation of valid MCP server configuration."""
        validator = ConfigValidator()

        valid_config = {
            "name": "test_server",
            "transport": "stdio",
            "command": ["echo", "test"],
        }
        issues = validator.validate_mcp_server_config(valid_config)

        # Should have no errors
        errors = [
            issue for issue in issues if issue.severity == ValidationSeverity.ERROR
        ]
        assert len(errors) == 0

    def test_workspace_validation(self):
        """Test workspace directory validation."""
        validator = ConfigValidator()

        # Test with temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            issues = validator.validate_workspace(temp_dir)

            # Should have no errors for valid temp directory
            errors = [
                issue for issue in issues if issue.severity == ValidationSeverity.ERROR
            ]
            assert len(errors) == 0

    def test_nonexistent_workspace(self):
        """Test validation with nonexistent workspace."""
        validator = ConfigValidator()

        nonexistent_path = "/path/that/does/not/exist/12345"
        issues = validator.validate_workspace(nonexistent_path)

        errors = [
            issue for issue in issues if issue.severity == ValidationSeverity.ERROR
        ]
        assert len(errors) >= 1
        assert any("does not exist" in issue.message for issue in errors)

    def test_environment_validation(self):
        """Test environment validation."""
        validator = ConfigValidator()

        issues = validator.validate_environment()

        # Should not have Python version errors on current system
        python_errors = [
            issue
            for issue in issues
            if issue.severity == ValidationSeverity.ERROR and "Python" in issue.message
        ]
        assert len(python_errors) == 0


class TestValidationReporter:
    """Test validation reporting functionality."""

    def test_format_issues(self):
        """Test formatting of validation issues."""
        reporter = ValidationReporter()

        issues = [
            ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message="Test error",
                field="test_field",
                suggestion="Fix the test",
            ),
            ValidationIssue(
                severity=ValidationSeverity.WARNING, message="Test warning"
            ),
        ]

        formatted = reporter.format_issues(issues)

        assert "ERROR" in formatted
        assert "WARNING" in formatted
        assert "Test error" in formatted
        assert "Test warning" in formatted
        assert "Fix the test" in formatted

    def test_empty_issues(self):
        """Test formatting with no issues."""
        reporter = ValidationReporter()

        formatted = reporter.format_issues([])
        assert "No issues found" in formatted

    def test_summary_generation(self):
        """Test summary generation."""
        reporter = ValidationReporter()

        issues = [
            ValidationIssue(ValidationSeverity.ERROR, "Error 1"),
            ValidationIssue(ValidationSeverity.ERROR, "Error 2"),
            ValidationIssue(ValidationSeverity.WARNING, "Warning 1"),
            ValidationIssue(ValidationSeverity.INFO, "Info 1"),
        ]

        summary = reporter.get_summary(issues)

        assert "2 error(s)" in summary
        assert "1 warning(s)" in summary
        assert "1 info" in summary

    def test_has_errors(self):
        """Test error detection."""
        reporter = ValidationReporter()

        # With errors
        issues_with_errors = [
            ValidationIssue(ValidationSeverity.ERROR, "Test error"),
            ValidationIssue(ValidationSeverity.WARNING, "Test warning"),
        ]
        assert reporter.has_errors(issues_with_errors)

        # Without errors
        issues_without_errors = [
            ValidationIssue(ValidationSeverity.WARNING, "Test warning"),
            ValidationIssue(ValidationSeverity.INFO, "Test info"),
        ]
        assert not reporter.has_errors(issues_without_errors)


class TestConfigIntegration:
    """Test integration of validation with Config class."""

    def test_config_validation_method(self):
        """Test Config.validate_configuration method."""
        config = Config()

        # Should not raise exceptions
        report = config.validate_configuration()
        assert isinstance(report, str)
        assert len(report) > 0

    def test_config_error_checking(self):
        """Test Config.has_validation_errors method."""
        config = Config()

        # Should not raise exceptions
        has_errors = config.has_validation_errors()
        assert isinstance(has_errors, bool)

    def test_validation_with_workspace(self):
        """Test validation with workspace path."""
        config = Config()

        with tempfile.TemporaryDirectory() as temp_dir:
            report = config.validate_configuration(temp_dir)
            assert isinstance(report, str)

            has_errors = config.has_validation_errors(temp_dir)
            assert isinstance(has_errors, bool)

    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"), reason="No OpenAI API key available"
    )
    def test_validation_with_real_api_key(self):
        """Test validation with real API key (if available)."""
        config = Config()

        # This should pass validation if OPENAI_API_KEY is set
        report = config.validate_configuration()

        # Should not have API key errors
        assert "Missing API key" not in report


if __name__ == "__main__":
    pytest.main([__file__])
