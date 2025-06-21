import sys
from ..models import Message, Role


class Display:
    def __init__(self):
        self.colors = {
            "user": "\033[94m",
            "assistant": "\033[92m",
            "system": "\033[93m",
            "error": "\033[91m",
            "reset": "\033[0m",
            "dim": "\033[90m",
            "bold": "\033[1m",
        }
        self.use_colors = sys.stdout.isatty()
    
    def color(self, text: str, color: str) -> str:
        if not self.use_colors:
            return text
        return f"{self.colors.get(color, '')}{text}{self.colors['reset']}"
    
    def print(self, text: str = "", end: str = "\n"):
        print(text, end=end, flush=True)
    
    def error(self, text: str):
        self.print(self.color(f"Error: {text}", "error"))
    
    def welcome(self):
        self.print(self.color("Yet Claude Code - Multi-model AI Assistant", "bold"))
        self.print(self.color("Type /help for commands, /exit to quit", "dim"))
        self.print()
    
    def goodbye(self):
        self.print()
        self.print(self.color("Goodbye!", "bold"))
    
    def get_prompt(self) -> str:
        return self.color("You: ", "user")
    
    def thinking(self):
        self.print(self.color("Assistant: ", "assistant"), end="")
    
    def stream_chunk(self, chunk: str):
        print(chunk, end="", flush=True)
    
    def stream_end(self):
        print("\n")
    
    def print_message(self, message: Message):
        role_color = {
            Role.USER: "user",
            Role.ASSISTANT: "assistant",
            Role.SYSTEM: "system",
        }.get(message.role, "reset")
        
        prefix = f"{message.role.value.capitalize()}: "
        self.print(self.color(prefix, role_color) + message.content)
        self.print()
    
    def show_help(self):
        help_text = """
Available commands:
  /help     - Show this help message
  /exit     - Exit the application
  /clear    - Clear conversation history
  /model    - Show or set the current model
  /tokens   - Show token count for current conversation
"""
        self.print(help_text)