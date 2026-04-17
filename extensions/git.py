# CC-TYPE: extension
# CC-NAME: git
# CC-DESCRIPTION: Native Git-Integration
# CC-REQUIREMENTS: none

import subprocess
import shutil


def provides_commands():
    """Registriert den 'git' Befehl."""
    return {
        "git": {
            "handler": run_git,
            "description": "Führt Git-Befehle aus (z.B. git status, git pull)"
        }
    }


def run_git(args_list, console):
    """Führt den Git-Befehl aus und gibt den Output zurück."""
    if not shutil.which("git"):
        return "❌ Git ist auf diesem System nicht installiert oder nicht im PATH."

    if not args_list:
        return "⚠️ Bitte gib einen Git-Befehl an (z.B. git status)."

    try:
        # Führt git mit den übergebenen Argumenten aus
        result = subprocess.run(
            ["git"] + args_list,
            capture_output=True,
            text=True,
            encoding="utf-8"
        )

        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            # Git schreibt Warnungen oft in den stderr, auch wenn es kein Fehler ist
            output += f"\n{result.stderr}"

        return output.strip() if output else "✔️ Git-Befehl erfolgreich ausgeführt."

    except Exception as e:
        return f"❌ Fehler beim Ausführen von Git: {str(e)}"


def on_startup(console):
    """Begrüßung beim Laden."""
    from ui import C
    print(f"  {C.SUCCESS}✓{C.RESET} Git-Extension aktiv.")