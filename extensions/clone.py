import os
from pathlib import Path
from ui import C

VERSION = "E0.3"

def provides_commands():
    return {
        "clone": {
            "handler": handle_instance_clone,
            "description": "Clones the instance by running launch.bat from the parent directory"
        }
    }

def handle_instance_clone(args, console):
    # Locate launch.bat in the directory above
    parent_launch_bat = Path.cwd().parent / "launch.bat"

    if parent_launch_bat.exists():
        print(f"  {C.SUCCESS}Cloning instance...{C.RESET}")
        
        # 'start' launches the file in a NEW window.
        # This ensures the current console stays exactly where it is.
        os.system(f'start "" "{parent_launch_bat}"')
        return ""
    else:
        return f"{C.ERROR}Error: launch.bat not found at {parent_launch_bat}{C.RESET}"

def on_startup(console):
    print(f"  {C.SUCCESS}✓{C.RESET} Instance-Clone Extension active. Type 'clone' to spawn a new window.")