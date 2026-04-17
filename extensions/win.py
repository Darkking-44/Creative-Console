# CC-TYPE: extension
# CC-NAME: win
# CC-DESCRIPTION: Ermöglicht das Ausführen von nativen PowerShell-Befehlen unter Windows.
# CC-REQUIREMENTS: none

import subprocess
import os


def provides_commands():
    """Registriert den 'win' Befehl in der Konsole."""
    return {
        "win": {
            "handler": run_powershell,
            "description": "Führt einen PowerShell-Befehl aus (z.B. win Get-Process)"
        }
    }


def run_powershell(args_list, console):
    """
    Nimmt die Argumente entgegen und führt sie in der PowerShell aus.
    """
    if os.name != "nt":
        return "❌ Dieser Befehl funktioniert nur auf Windows-Systemen."

    if not args_list:
        return "⚠️ Bitte gib einen Befehl an. Beispiel: win ls"

    # Den Befehl aus der Liste wieder zusammenbauen
    command = " ".join(args_list)

    try:
        # PowerShell Aufruf:
        # -ExecutionPolicy Bypass verhindert Probleme mit Skript-Restriktionen
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            encoding="cp850"  # Standard Windows Terminal Encoding
        )

        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += f"\n[PowerShell Error]:\n{result.stderr}"

        return output.strip() if output else "✔️ Befehl wurde ohne Rückgabe ausgeführt."

    except Exception as e:
        return f"❌ Fehler beim Ausführen der PowerShell: {str(e)}"


def on_startup(console):
    """Wird beim Laden der Extension angezeigt."""
    # Wir nutzen die Farben aus der ui.py (C.SUCCESS ist grün)
    from ui import C
    print(f"  {C.SUCCESS}✓{C.RESET} Windows PowerShell-Bridge bereit.")