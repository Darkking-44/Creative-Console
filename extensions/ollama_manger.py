# CC-TYPE: extension
# CC-NAME: ollama_manager
# CC-DESCRIPTION: Automatisches Modell-Setup & Management für Ollama.
# CC-REQUIREMENTS: requests

import subprocess
import shutil
import requests
from ui import C, Spinner


def on_startup(console):
    if not shutil.which("ollama"):
        ans = input(f"  {C.WARN}Ollama nicht gefunden. Installieren? (y/N): {C.RESET}").lower()
        if ans in ("y", "j"):
            print("  Bitte installiere Ollama von https://ollama.com und starte die Konsole neu.")
        return

    # Automatischer Setup-Vibe
    ans = input(f"\n  {C.CYAN}Ollama Setup:{C.RESET} GPU-Modell (Qwen2.5:32B) & CPU-Modell laden? (y/N): ").lower()
    if ans in ("y", "j"):
        _pull_model("qwen2.5:32b", console)
        _pull_model("llama3.2:1b", console)
    else:
        ans_other = input(f"  {C.CYAN}❯{C.RESET} Ein anderes Modell auswählen? (y/N): ").lower()
        if ans_other in ("y", "j"):
            m = input(f"  {C.CYAN}❯{C.RESET} Modellname: ").strip()
            if m: _pull_model(m, console)


def _pull_model(name, console):
    print(f"  {C.MUTED}Lade {name}...{C.RESET}")
    # Nutzt den Spinner aus deiner ui.py
    with Spinner(f"Pulling {name}"):
        subprocess.run(["ollama", "pull", name], capture_output=True)
    print(f"  {C.SUCCESS}✓ {name} bereit.{C.RESET}")


def provides_commands():
    return {
        "ollama": {
            "handler": list_ollama,
            "description": "Zeigt installierte Modelle und erlaubt Installationen."
        }
    }


def list_ollama(args, console):
    if args and args[0] == "install":
        _pull_model(args[1], console)
        return f"Modell {args[1]} installiert."

    res = subprocess.run(["ollama", "list"], capture_output=True, text=True)
    return f"\n{C.HEADING}── INSTALLIERTE MODELLE ──{C.RESET}\n{res.stdout}"