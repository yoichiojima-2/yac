import sys


class Display:
    def __init__(self):
        self.use_colors = sys.stdout.isatty()
    
    def _color(self, text: str, code: str) -> str:
        if not self.use_colors:
            return text
        return f"\033[{code}m{text}\033[0m"
    
    def print(self, text: str = ""):
        print(text)
    
    def error(self, text: str):
        print(self._color(f"Error: {text}", "91"))
    
    def welcome(self):
        print(self._color("Yet Claude Code", "1"))
        print("Type /help for commands, /exit to quit")
        print()
    
    def goodbye(self):
        print(self._color("Goodbye!", "1"))
    
    def get_prompt(self) -> str:
        return self._color("You: ", "94")
    
    def print_response(self, content: str):
        print(self._color("Assistant: ", "92") + content)
        print()
    
    def show_help(self):
        print("""Available commands:
  /help   - Show this help
  /exit   - Exit the application  
  /clear  - Clear conversation history""")