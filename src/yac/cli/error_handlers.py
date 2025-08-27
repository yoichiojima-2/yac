"""Error handling strategies for different types of failures."""

import asyncio
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any


class ErrorHandler(ABC):
    """Abstract base class for error handling strategies."""

    @abstractmethod
    async def can_handle(self, error: Exception, context: Dict[str, Any]) -> bool:
        """Check if this handler can handle the given error."""
        pass

    @abstractmethod
    async def handle(self, error: Exception, context: Dict[str, Any]) -> Optional[str]:
        """Handle the error and return recovery information or None."""
        pass


class FileNotFoundHandler(ErrorHandler):
    """Handle file not found errors with intelligent suggestions."""

    async def can_handle(self, error: Exception, context: Dict[str, Any]) -> bool:
        error_str = str(error).lower()
        return any(
            phrase in error_str
            for phrase in [
                "file not found",
                "no such file",
                "does not exist",
                "cannot find",
            ]
        )

    async def handle(self, error: Exception, context: Dict[str, Any]) -> Optional[str]:
        args = context.get("args", {})
        tools = context.get("tools", [])

        # Extract filename from args
        filename = self._extract_filename(args)
        if not filename:
            return None

        # Build contextual error message with investigation suggestions
        error_context = f"File '{filename}' not found. "

        # Suggest available investigation tools
        available_tools = [t.name for t in tools]
        investigation_tools = [
            tool
            for tool in available_tools
            if tool
            in ["search_files", "list_directory", "directory_tree", "execute_command"]
        ]

        if investigation_tools:
            error_context += (
                f"Available tools to investigate: {', '.join(investigation_tools)}. "
            )
            error_context += self._get_investigation_suggestions(filename)

        return error_context

    def _extract_filename(self, args: Any) -> Optional[str]:
        """Extract filename from various argument formats."""
        if isinstance(args, dict):
            return args.get("path") or args.get("file_path") or args.get("filename")
        elif isinstance(args, str):
            return args
        return None

    def _get_investigation_suggestions(self, filename: str) -> str:
        """Get specific investigation suggestions based on filename."""
        import os

        basename = os.path.basename(filename)
        extension = os.path.splitext(basename)[1]

        suggestions = [
            f"search_files to look for '{basename}' or similar files",
            "list_directory to see what's available in the current or parent directories",
        ]

        if extension:
            suggestions.append(f"search for other {extension} files")

        suggestions.append("execute_command with 'find' to search the filesystem")

        return f"Consider using: {'; '.join(suggestions)}."


class PermissionErrorHandler(ErrorHandler):
    """Handle permission denied errors."""

    async def can_handle(self, error: Exception, context: Dict[str, Any]) -> bool:
        error_str = str(error).lower()
        return any(
            phrase in error_str
            for phrase in [
                "permission denied",
                "access denied",
                "not permitted",
                "insufficient privileges",
            ]
        )

    async def handle(self, error: Exception, context: Dict[str, Any]) -> Optional[str]:
        tool_name = context.get("tool_name", "")

        suggestions = [
            "Check file/directory permissions",
            "Verify you have the necessary access rights",
            "Consider using sudo if appropriate",
            "Check if the file is locked by another process",
        ]

        if "write" in tool_name.lower() or "edit" in tool_name.lower():
            suggestions.append("Ensure the target location is writable")

        return f"Permission denied. Suggestions: {'; '.join(suggestions)}."


class NetworkErrorHandler(ErrorHandler):
    """Handle network-related errors with retry logic."""

    def __init__(self, max_retries: int = 2, retry_delay: float = 1.0):
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    async def can_handle(self, error: Exception, context: Dict[str, Any]) -> bool:
        error_str = str(error).lower()
        return any(
            phrase in error_str
            for phrase in [
                "connection",
                "timeout",
                "network",
                "unreachable",
                "dns",
                "socket",
            ]
        )

    async def handle(self, error: Exception, context: Dict[str, Any]) -> Optional[str]:
        tool_name = context.get("tool_name", "")
        args = context.get("args", {})
        tools = context.get("tools", [])

        # Attempt retry for network operations
        for attempt in range(self.max_retries):
            try:
                await asyncio.sleep(self.retry_delay * (attempt + 1))

                # Find and retry the original tool
                original_tool = next((t for t in tools if t.name == tool_name), None)
                if original_tool:
                    retry_result = await original_tool.ainvoke(args)
                    return f"Network retry successful after {attempt + 1} attempts: {retry_result}"

            except Exception as retry_error:
                if attempt == self.max_retries - 1:
                    return f"Network error persisted after {self.max_retries} retries. Last error: {retry_error}"

        return "Network error occurred. Please check your connection and try again."


class DirectoryNotFoundHandler(ErrorHandler):
    """Handle directory not found errors."""

    async def can_handle(self, error: Exception, context: Dict[str, Any]) -> bool:
        error_str = str(error).lower()
        return any(
            phrase in error_str
            for phrase in [
                "directory not found",
                "no such directory",
                "path does not exist",
            ]
        )

    async def handle(self, error: Exception, context: Dict[str, Any]) -> Optional[str]:
        args = context.get("args", {})

        directory = None
        if isinstance(args, dict):
            directory = args.get("path") or args.get("directory")
        elif isinstance(args, str):
            directory = args

        if directory:
            # Suggest checking parent directories
            import os

            parent_dir = os.path.dirname(directory)
            suggestions = [
                f"Check if parent directory '{parent_dir}' exists",
                "Use list_directory to explore available paths",
                "Consider creating the directory first if needed",
                "Verify the path format is correct",
            ]

            return f"Directory '{directory}' not found. {'; '.join(suggestions)}."

        return "Directory not found. Please verify the path exists."


class ProcessErrorHandler(ErrorHandler):
    """Handle process execution errors."""

    async def can_handle(self, error: Exception, context: Dict[str, Any]) -> bool:
        error_str = str(error).lower()
        return any(
            phrase in error_str
            for phrase in [
                "command not found",
                "no such command",
                "executable not found",
                "process failed",
                "exit code",
            ]
        )

    async def handle(self, error: Exception, context: Dict[str, Any]) -> Optional[str]:
        tool_name = context.get("tool_name", "")
        args = context.get("args", {})

        if "command not found" in str(error).lower():
            command = args.get("command", "") if isinstance(args, dict) else str(args)
            return (
                f"Command '{command}' not found. Check if it's installed and in PATH."
            )

        if "exit code" in str(error).lower():
            return "Command executed but failed. Check command syntax and arguments."

        return f"Process execution error in {tool_name}. Verify command and arguments."


class ErrorHandlerRegistry:
    """Registry for managing error handlers with fallback chain."""

    def __init__(self):
        self.handlers: List[ErrorHandler] = [
            FileNotFoundHandler(),
            PermissionErrorHandler(),
            NetworkErrorHandler(),
            DirectoryNotFoundHandler(),
            ProcessErrorHandler(),
        ]

    def add_handler(self, handler: ErrorHandler):
        """Add a custom error handler to the registry."""
        self.handlers.insert(0, handler)  # Custom handlers get priority

    async def handle_error(
        self, error: Exception, tool_name: str, args: Any, tools: List[Any]
    ) -> Optional[str]:
        """Find appropriate handler and process the error."""
        context = {
            "tool_name": tool_name,
            "args": args,
            "tools": tools,
            "error_type": type(error).__name__,
        }

        for handler in self.handlers:
            try:
                if await handler.can_handle(error, context):
                    result = await handler.handle(error, context)
                    if result:
                        return result
            except Exception as handler_error:
                # Don't let handler errors break the chain
                print(f"Error in handler {type(handler).__name__}: {handler_error}")
                continue

        # Fallback for unhandled errors
        return f"Unhandled error in {tool_name}: {error}. Please check your input and try again."


class GracefulErrorMixin:
    """Mixin to add graceful error handling to any class."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.error_registry = ErrorHandlerRegistry()

    async def handle_tool_error_gracefully(
        self, error: Exception, tool_name: str, args: Any, tools: List[Any]
    ) -> str:
        """Handle tool errors with the error registry."""
        return await self.error_registry.handle_error(error, tool_name, args, tools)