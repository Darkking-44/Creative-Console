import os
from pathlib import Path
from ui import C

VERSION = "E0.3.1"

def provides_commands():
    return {
        "clone": {
            "handler": handle_instance_clone,
            "description": "Starts a new instance using relative paths"
        }
    }

def handle_instance_clone(args, console):
    # Path.cwd() is where your console is currently looking.
    # We navigate to the 'win' folder which contains launch.bat
    # This logic assumes the structure: Creative Console/win/launch.bat
    
    # We look for launch.bat one level up from the current working directory
    launch_script = Path.cwd().parent / "launch.bat"

    if launch_script.exists():
        print(f"  {C.SUCCESS}Cloning instance (Portable mode)...{C.RESET}")
        
        # We use double quotes around the path in case there are spaces in folder names
        # 'os.system' with 'start' launches it as a background process
        os.system(f'start "" "{launch_script}"')
        return ""
    else:
        # Fallback: if not found in parent, check if we are already in the 'win' folder
        launch_script = Path.cwd() / "launch.bat"
        if launch_script.exists():
            os.system(f'start "" "{launch_script}"')
            return ""
        
        return f"{C.ERROR}Error: Could not find launch.bat relative to this location.{C.RESET}"

def on_startup(console):
    print(f"  {C.SUCCESS}✓{C.RESET} Portable Clone Extension active.")