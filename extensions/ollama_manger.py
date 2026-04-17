# CC-TYPE: extension
# CC-NAME: ollama_manager
# CC-DESCRIPTION: Managed Ollama models with a setup wizard.
import subprocess
import shutil
from pathlib import Path
from ui import C, Spinner
from utils import feat_data_dir

def on_startup(c):
    # Check if setup was already offered
    marker = feat_data_dir() / ".ollama_setup_done"
    if marker.exists() or not shutil.which("ollama"):
        return

    print(f"\n  {C.CYAN}Ollama Manager: Recommended models not found.{C.RESET}")
    try:
        ans = input(f"  Setup recommended models? (y/N): ").lower()
        if ans in ("y", "j", "yes"):
            _smart_pull("llama3.2:1b")
        
        # Create marker so it never asks again
        marker.touch()
    except (EOFError, KeyboardInterrupt):
        pass

def _smart_pull(model_name):
    print(f"  {C.MUTED}Fetching {model_name}...{C.RESET}")
    try:
        with Spinner(f"Pulling {model_name}"):
            subprocess.run(["ollama", "pull", model_name], capture_output=True, check=True)
        print(f"  {C.SUCCESS}✓ {model_name} ready.{C.RESET}")
    except:
        print(f"  {C.ERROR}Status: Failed to pull model.{C.RESET}")

def provides_commands():
    return {"ollama": {"handler": cmd_ollama, "description": "Manage Ollama models"}}

def cmd_ollama(args, console):
    # Manual install via command always works
    if args and args[0] == "install" and len(args) > 1:
        _smart_pull(args[1])
        return "Install triggered."
    return "Usage: ollama install <model>"