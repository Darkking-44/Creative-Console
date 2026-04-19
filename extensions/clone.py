# CC-TYPE:        extension
# CC-NAME:        clone
# CC-VERSION:     E0.2
# CC-DESCRIPTION: Klont Repos und führt automatisch die launch.bat aus.
# CC-REQUIREMENTS: 

import subprocess
import shutil
import os
from pathlib import Path
from ui import C, Spinner

VERSION = "E0.2"

def provides_commands():
    return {
        "clone": {
            "handler": handle_clone,
            "description": "Klont ein Repo und startet die launch.bat"
        }
    }

def handle_clone(args, console):
    if not args:
        return f"{C.ERROR}Usage: clone <repo_url>{C.RESET}"

    if not shutil.which("git"):
        return f"{C.ERROR}Git ist nicht installiert.{C.RESET}"

    repo_url = args[0]
    repo_name = repo_url.split("/")[-1].replace(".git", "")
    target_dir = Path.cwd() / repo_name

    # 1. Repository klonen
    print(f"  {C.MUTED}Klone {repo_url}...{C.RESET}")
    try:
        with Spinner(f"Cloning {repo_name}"):
            subprocess.run(["git", "clone", repo_url], capture_output=True, check=True)
        print(f"  {C.SUCCESS}Done: {repo_name} geklont.{C.RESET}")
    except subprocess.CalledProcessError as e:
        return f"{C.ERROR}Fehler beim Klonen: {e.stderr.decode().strip()}{C.RESET}"

    # 2. Prüfen ob launch.bat existiert und ausführen
    batch_file = target_dir / "launch.bat"
    
    if batch_file.exists():
        print(f"  {C.SUCCESS}Starte {batch_file.name}...{C.RESET}")
        # Wechselt in den Ordner und startet die .bat in einem neuen Fenster
        os.chdir(str(target_dir))
        os.system(f"start launch.bat")
    else:
        print(f"  {C.WARN}Keine launch.bat in {repo_name} gefunden.{C.RESET}")

    return ""

def on_startup(console):
    print(f"  {C.SUCCESS}✓{C.RESET} Clone & Launch Extension aktiv.")