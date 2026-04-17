# CC-TYPE: extension
# CC-NAME: ollama_manager
# CC-DESCRIPTION: Automates Ollama model installation and management.

import subprocess
import shutil
from ui import C, Spinner


def on_startup(c):
    """
    Check for Ollama installation and prompt for model setup.
    'c' is the CreativeConsal instance passed during startup.
    """
    if not shutil.which("ollama"):
        return

    print(f"\n  {C.CYAN}🦙 Ollama Manager Active{C.RESET}")
    try:
        # Prompt user for recommended model batch
        ans = input(f"  Setup recommended models? (GPU: Qwen2.5:32B / CPU: Llama3.2:1B) (y/N): ").lower()
        if ans in ("y", "j", "yes"):
            _smart_pull("qwen2.5:32b")
            _smart_pull("llama3.2:1b")
    except (EOFError, KeyboardInterrupt):
        return


def _smart_pull(model_name):
    """Internal helper to pull models using the engine's built-in Spinner."""
    print(f"  {C.MUTED}Preparing to fetch {model_name}...{C.RESET}")
    try:
        with Spinner(f"Pulling {model_name}"):
            # Execute native ollama command
            subprocess.run(["ollama", "pull", model_name], capture_output=True, check=True)
        print(f"  {C.SUCCESS}✓ {model_name} is ready.{C.RESET}")
    except Exception as e:
        print(f"  {C.ERROR}✗ Failed to pull {model_name}: {e}{C.RESET}")


def provides_commands():
    """Expose management commands to the CreativeConsal instance."""
    return {
        "ollama": {
            "handler": cmd_ollama_list,
            "description": "List models or install new ones (usage: ollama install <name>)"
        }
    }


def cmd_ollama_list(args, console_inst):
    """Handle command execution logic."""
    if args and args[0] == "install":
        if len(args) < 2:
            return "Usage: ollama install <model_name>"
        _smart_pull(args[1])
        return f"Completed installation of {args[1]}"

    try:
        # Get list of local models
        res = subprocess.run(["ollama", "list"], capture_output=True, text=True)
        return f"\n{C.HEADING}── OLLAMA MODELS ──{C.RESET}\n{res.stdout}"
    except:
        return "Error: Ollama service unavailable."