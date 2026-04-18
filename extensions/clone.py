# CC-TYPE:        extension
# CC-NAME:        clone
# CC-VERSION:     E0.1
# CC-DESCRIPTION: Console cloner — spawns a new instance of Creative Consol.
# CC-REQUIREMENTS: none

import sys
import subprocess
import os
from ui import C

VERSION = "E0.1"

# ---------------------------------------------------------------------------
# Command registration
# ---------------------------------------------------------------------------

def provides_commands():
    """Register the 'clone' command with the extension host."""
    return {
        "clone": {
            "handler": handle_clone,
            "description": "Spawn a new console instance."
        }
    }

# ---------------------------------------------------------------------------
# Command handler
# ---------------------------------------------------------------------------

def handle_clone(args, console):
    """
    Executes a new process of the current python script.
    
    This uses sys.executable and the path of the main script to ensure
    the new window opens with the same environment.
    """
    
    # Save current history to disk before cloning so the new instance 
    # can load the full progress.
    try:
        import readline
        from utils import data_dir
        hf = data_dir() / "history"
        readline.write_history_file(str(hf))
    except (ImportError, AttributeError):
        pass

    print(f"  {C.MUTED}Cloning console instance...{C.RESET}")

    # Identify the entry point (main.py)
    main_script = sys.argv[0]
    
    # Platform specific terminal spawning
    try:
        if os.name == "nt":
            # Windows: Spawn in a new cmd window
            subprocess.Popen(["start", "cmd", "/K", sys.executable, main_script], shell=True)
        else:
            # Unix/Mac: Attempt to open a new terminal tab/window
            # Note: This depends on the installed terminal emulator.
            # Using a generic approach via python itself if no GUI terminal is found.
            subprocess.Popen([sys.executable, main_script], start_new_session=True)
            
        return "New instance launched."
    except Exception as e:
        return f"Failed to clone: {str(e)}"

# ---------------------------------------------------------------------------
# Lifecycle hooks
# ---------------------------------------------------------------------------

def on_startup(console):
    """Print confirmation message when extension is loaded."""
    print(f"  {C.SUCCESS}✓{C.RESET} Clone Extension v{VERSION} active.")