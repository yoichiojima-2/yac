"""Configuration validators for YAC (Yet Another Claude)."""

import os
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """Represents a configuration validation issue."""

    severity: ValidationSeverity
    message: str
    field: Optional[str] = None
    suggestion: Optional[str] = None


class ConfigValidator:
    """Validates configuration settings for YAC."""

    # Known valid models for each provider
    VALID_MODELS = {
        "openai": [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-4-turbo-preview",
            "gpt-4",
            "gpt-3.5-turbo",
            "o1-preview",
            "o1-mini",
            "o3-mini",
        ],
        "anthropic": [
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
        ],
        "google": [
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "gemini-1.0-pro",
            "gemini-pro",
            "gemini-pro-vision",
        ],
    }

    # Required environment variables for each provider
    REQUIRED_ENV_VARS = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "google": "GOOGLE_API_KEY",
    }

    def __init__(self):
        self.issues: List[ValidationIssue] = []

    def validate_provider_config(
        self, provider: str, model: str, api_key: Optional[str] = None
    ) -> List[ValidationIssue]:
        """Validate AI provider configuration."""
        self.issues = []

        # Validate provider
        if provider not in self.VALID_MODELS:
            self.issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message=f"Unknown provider '{provider}'",
                    field="provider",
                    suggestion=f"Valid providers: {', '.join(self.VALID_MODELS.keys())}",
                )
            )
            return self.issues

        # Validate model for provider
        valid_models = self.VALID_MODELS[provider]
        if model not in valid_models:
            self.issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    message=f"Model '{model}' not in known models for {provider}",
                    field="model",
                    suggestion=f"Common models for {provider}: {', '.join(valid_models[:3])}",
                )
            )

        # Validate API key
        env_var = self.REQUIRED_ENV_VARS[provider]
        actual_api_key = api_key or os.getenv(env_var)

        if not actual_api_key:
            self.issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message=f"Missing API key for {provider}",
                    field="api_key",
                    suggestion=f"Set {env_var} environment variable",
                )
            )
        elif len(actual_api_key) < 10:
            self.issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    message=f"API key for {provider} seems too short",
                    field="api_key",
                    suggestion="Verify the API key is complete",
                )
            )

        return self.issues

    def validate_mcp_server_config(
        self, server_config: Dict[str, Any]
    ) -> List[ValidationIssue]:
        """Validate MCP server configuration."""
        self.issues = []

        # Required fields
        required_fields = ["name", "transport", "command"]
        for field in required_fields:
            if field not in server_config:
                self.issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        message=f"Missing required field '{field}' in MCP server config",
                        field=field,
                    )
                )

        # Validate transport
        valid_transports = ["stdio", "sse", "http"]
        transport = server_config.get("transport", "").lower()
        if transport not in valid_transports:
            self.issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message=f"Invalid transport '{transport}'",
                    field="transport",
                    suggestion=f"Valid transports: {', '.join(valid_transports)}",
                )
            )

        # Validate command for stdio transport
        if transport == "stdio":
            command = server_config.get("command", [])
            if not command or not isinstance(command, list) or len(command) == 0:
                self.issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        message="STDIO transport requires a valid command array",
                        field="command",
                    )
                )
            elif command[0] in ["npx", "npm"]:
                # Check if Node.js is available
                if not self._check_command_available("node"):
                    self.issues.append(
                        ValidationIssue(
                            severity=ValidationSeverity.WARNING,
                            message="Node.js not found but required for npx/npm commands",
                            suggestion="Install Node.js to use this MCP server",
                        )
                    )

        # Validate URL for HTTP/SSE transports
        if transport in ["http", "sse"]:
            url = server_config.get("url")
            if not url:
                self.issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        message=f"{transport.upper()} transport requires a URL",
                        field="url",
                    )
                )
            elif not self._is_valid_url(url):
                self.issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        message=f"URL '{url}' may not be valid",
                        field="url",
                    )
                )

        return self.issues

    def validate_environment(self) -> List[ValidationIssue]:
        """Validate the runtime environment."""
        self.issues = []

        # Check Python version
        import sys

        python_version = sys.version_info
        if python_version < (3, 8):
            self.issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message=f"Python {python_version.major}.{python_version.minor} is too old",
                    suggestion="Python 3.8+ is required",
                )
            )

        # Check for essential commands
        essential_commands = ["git"]
        for cmd in essential_commands:
            if not self._check_command_available(cmd):
                self.issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        message=f"Command '{cmd}' not found in PATH",
                        suggestion=f"Install {cmd} for full functionality",
                    )
                )

        # Check disk space (basic check)
        try:
            import shutil

            free_space = shutil.disk_usage(".").free / (1024**3)  # GB
            if free_space < 1.0:
                self.issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        message=f"Low disk space: {free_space:.1f}GB available",
                        suggestion="Consider freeing up disk space",
                    )
                )
        except Exception:
            pass  # Skip if can't check disk space

        return self.issues

    def validate_workspace(self, workspace_path: str) -> List[ValidationIssue]:
        """Validate workspace directory."""
        self.issues = []

        if not os.path.exists(workspace_path):
            self.issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message=f"Workspace path does not exist: {workspace_path}",
                    field="workspace_path",
                    suggestion="Create the directory or use a valid path",
                )
            )
            return self.issues

        if not os.path.isdir(workspace_path):
            self.issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message=f"Workspace path is not a directory: {workspace_path}",
                    field="workspace_path",
                )
            )
            return self.issues

        # Check permissions
        if not os.access(workspace_path, os.R_OK):
            self.issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message=f"No read permission for workspace: {workspace_path}",
                    field="workspace_path",
                )
            )

        if not os.access(workspace_path, os.W_OK):
            self.issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    message=f"No write permission for workspace: {workspace_path}",
                    field="workspace_path",
                    suggestion="Some operations may fail without write access",
                )
            )

        # Check if it's a git repository
        git_dir = os.path.join(workspace_path, ".git")
        if os.path.exists(git_dir):
            self.issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    message="Workspace is a Git repository - Git tools will be available",
                )
            )

        return self.issues

    def _check_command_available(self, command: str) -> bool:
        """Check if a command is available in PATH."""
        import shutil

        return shutil.which(command) is not None

    def _is_valid_url(self, url: str) -> bool:
        """Basic URL validation."""
        url_pattern = re.compile(
            r"^https?://"  # http:// or https://
            r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain...
            r"localhost|"  # localhost...
            r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
            r"(?::\d+)?"  # optional port
            r"(?:/?|[/?]\S+)$",
            re.IGNORECASE,
        )
        return url_pattern.match(url) is not None


class ValidationReporter:
    """Formats and reports validation results."""

    def __init__(self):
        self.severity_colors = {
            ValidationSeverity.ERROR: "🔴",
            ValidationSeverity.WARNING: "🟡",
            ValidationSeverity.INFO: "🔵",
        }

    def format_issues(self, issues: List[ValidationIssue]) -> str:
        """Format validation issues for display."""
        if not issues:
            return "✅ No issues found"

        lines = []
        for issue in issues:
            icon = self.severity_colors[issue.severity]
            field_info = f" ({issue.field})" if issue.field else ""
            line = f"{icon} {issue.severity.value.upper()}{field_info}: {issue.message}"

            if issue.suggestion:
                line += f"\n   💡 Suggestion: {issue.suggestion}"

            lines.append(line)

        return "\n".join(lines)

    def get_summary(self, issues: List[ValidationIssue]) -> str:
        """Get a summary of validation results."""
        if not issues:
            return "✅ Configuration validation passed"

        error_count = sum(1 for i in issues if i.severity == ValidationSeverity.ERROR)
        warning_count = sum(
            1 for i in issues if i.severity == ValidationSeverity.WARNING
        )
        info_count = sum(1 for i in issues if i.severity == ValidationSeverity.INFO)

        parts = []
        if error_count:
            parts.append(f"{error_count} error(s)")
        if warning_count:
            parts.append(f"{warning_count} warning(s)")
        if info_count:
            parts.append(f"{info_count} info")

        return f"🔍 Validation complete: {', '.join(parts)}"

    def has_errors(self, issues: List[ValidationIssue]) -> bool:
        """Check if there are any error-level issues."""
        return any(issue.severity == ValidationSeverity.ERROR for issue in issues)