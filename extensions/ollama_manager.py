# CC-TYPE: extension
# CC-NAME: ollama_manager
# CC-DESCRIPTION: Ollama model management — list, pull, and set up local LLM models.

import subprocess
import shutil
from ui import C, Spinner


# ---------------------------------------------------------------------------
# Lifecycle hooks
# ---------------------------------------------------------------------------

def on_startup(console):
    """Print a non-blocking hint when the extension is loaded."""
    if shutil.which("ollama"):
        print(
            f"  {C.MUTED}Ollama Manager active. "
            f"Type 'ollama setup' for first-time installation.{C.RESET}"
        )


# ---------------------------------------------------------------------------
# Command registration
# ---------------------------------------------------------------------------

def provides_commands():
    """Register the 'ollama' command with the extension host."""
    return {
        "ollama": {
            "handler": cmd_handler,
            "description": "Manage Ollama models: 'ollama list', 'ollama setup', 'ollama pull <model>'."
        }
    }


def cmd_handler(args, console):
    """
    Dispatch sub-commands for Ollama management.

    Sub-commands:
        (none)       List all locally available models.
        list         Same as above.
        setup        Interactively install the recommended model set.
        pull <name>  Pull a specific model by name.

    Args:
        args (list[str]): Sub-command and optional arguments.
        console: The active console instance (unused, required by interface).

    Returns:
        str: Result message.
    """
    if not args:
        return _list_models()

    sub_cmd = args[0].lower()

    if sub_cmd == "list":
        return _list_models()

    if sub_cmd == "setup":
        answer = input("  Install recommended models? (y/N): ").strip().lower()
        if answer in ("y", "yes"):
            _smart_pull("qwen2.5:32b")
            _smart_pull("llama3.2:1b")
        return "Setup complete."

    if sub_cmd == "pull":
        if len(args) < 2:
            return f"{C.ERROR}Usage: ollama pull <model_name>{C.RESET}"
        _smart_pull(args[1])
        return f"Pull initiated for '{args[1]}'."

    return "Usage: ollama [list | setup | pull <model>]"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _list_models():
    """Return a formatted list of locally available Ollama models."""
    result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
    return f"\n{C.HEADING}── OLLAMA MODELS ──{C.RESET}\n{result.stdout}"


def _smart_pull(model_name):
    """
    Pull an Ollama model with a progress spinner.

    Args:
        model_name (str): The model identifier to pull (e.g. 'llama3.2:1b').
    """
    print(f"  {C.MUTED}Preparing {model_name}...{C.RESET}")
    try:
        with Spinner(f"Pulling {model_name}"):
            subprocess.run(["ollama", "pull", model_name], capture_output=True, check=True)
        print(f"  {C.SUCCESS}✓ {model_name} ready.{C.RESET}")
    except Exception as exc:
        print(f"  {C.ERROR}✗ Failed to pull {model_name}: {exc}{C.RESET}")
