import os
from pathlib import Path
from ui import C

VERSION = "E0.2.1"

def provides_commands():
    return {
        "clone": {  # Ich lasse den Namen 'clone', damit dein gewohnter Befehl bleibt
            "handler": handle_launch,
            "description": "Startet die launch.bat im Parent-Ordner"
        }
    }

def handle_launch(args, console):
    # Wir ignorieren 'args' jetzt einfach, da du keine URL brauchst
    
    # Pfad zur launch.bat im ÜBERGEORDNETEN Verzeichnis
    parent_launch_bat = Path.cwd().parent / "launch.bat"

    if parent_launch_bat.exists():
        print(f"  {C.SUCCESS}Starte {parent_launch_bat.name}...{C.RESET}")
        
        # Startet die Batch-Datei
        # 'start' öffnet ein neues CMD-Fenster
        os.system(f'start "" "{parent_launch_bat}"')
        return f"{C.SUCCESS}Launch-Befehl gesendet.{C.RESET}"
    else:
        return f"{C.ERROR}Fehler: Keine launch.bat in {parent_launch_bat.parent} gefunden.{C.RESET}"

def on_startup(console):
    print(f"  {C.SUCCESS}✓{C.RESET} Quick-Launch Extension aktiv (Befehl: clone).")