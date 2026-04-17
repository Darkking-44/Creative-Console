# CC-TYPE: extension
# CC-NAME: helper
# CC-DESCRIPTION: Fügt Autovervollständigung für alle Befehle hinzu.

import readline


def on_startup(console):
    # Wir sammeln alle Befehlsnamen
    commands = list(console.commands.keys()) + list(console.ext_cmds.keys())

    def completer(text, state):
        options = [c for c in commands if c.startswith(text)]
        if state < len(options):
            return options[state]
        return None

    # Readline Konfiguration
    readline.set_completer(completer)
    if "libedit" in readline.__doc__:  # macOS Support
        readline.parse_and_bind("bind ^I rl_complete")
    else:
        readline.parse_and_bind("tab: complete")

    from ui import C
    print(f"  {C.SUCCESS}✓{C.RESET} Autocomplete für {len(commands)} Befehle aktiv (Tab nutzen).")


def on_command_run(name, args, result):
    # Neue Befehle (z.B. nach pull) könnten hier dynamisch geupdatet werden
    pass