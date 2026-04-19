import subprocess
import shutil
import os
from pathlib import Path
from ui import C, Spinner

VERSION = "E0.2.1"

def provides_commands():
    return {
        "clone": {
            "handler": handle_clone,
            "description": "Klont ein Repo und startet die launch.bat im Parent-Ordner"
        }
    }

def handle_clone(args, console):
    if not args:
        return f"{C.ERROR}Usage: clone <repo_url>{C.RESET}"

    if not shutil.which("git"):
        return f"{C.ERROR}Git ist nicht installiert.{C.RESET}"

    repo_url = args[0]
    repo_name = repo_url.split("/")[-1].replace(".git", "")
    
    # 1. Repository klonen
    print(f"  {C.MUTED}Klone {repo_url}...{C.RESET}")
    try:
        with Spinner(f"Cloning {repo_name}"):
            # Wir klonen ganz normal in den aktuellen Ordner
            subprocess.run(["git", "clone", repo_url], capture_output=True, check=True)
        print(f"  {C.SUCCESS}Done: {repo_name} geklont.{C.RESET}")
    except subprocess.CalledProcessError as e:
        return f"{C.ERROR}Fehler beim Klonen: {e.stderr.decode().strip()}{C.RESET}"

    # 2. Pfad zur launch.bat im ÜBERGEORDNETEN Verzeichnis festlegen
    # Path.cwd().parent entspricht "../"
    parent_launch_bat = Path.cwd().parent / "launch.bat"

    if parent_launch_bat.exists():
        print(f"  {C.SUCCESS}Starte {parent_launch_bat}...{C.RESET}")
        # Startet die Batch-Datei im Kontext des übergeordneten Ordners
        os.system(f'start "" "{parent_launch_bat}"')
    else:
        print(f"  {C.WARN}Keine launch.bat in {parent_launch_bat.parent} gefunden.{C.RESET}")

    return ""

def on_startup(console):
    print(f"  {C.SUCCESS}✓{C.RESET} Clone & Parent-Launch Extension aktiv.")