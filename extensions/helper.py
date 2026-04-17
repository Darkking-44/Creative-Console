# CC-TYPE: extension
# CC-NAME: helper
# CC-DESCRIPTION: Fuzzy matching hook with explicit global access.

import utils
from ui import C


def on_input(line):
    """
    Hooks into the raw input and fixes typos.
    """
    if not line or not line.strip():
        return line

    parts = line.split()
    raw_cmd = parts[0]
    args = parts[1:] if len(parts) > 1 else []

    # Strip colors/formatting from input
    clean_cmd = utils.ansi_strip(raw_cmd).lower()

    # Access the registries. Since 'console' is injected into the global
    # namespace of this module by the ExtensionHost:
    try:
        # Built-in routes from main.py
        built_ins = [
            "help", "exit", "quit", "config", "reset", "agent-mode",
            "pull", "register-api-key", "command-list", "feature-list",
            "command-build", "command-see", "command-open", "command-rework"
        ]

        # Combine everything the console knows
        all_valid = built_ins + list(console.commands.keys()) + list(console.ext_cmds.keys())
    except NameError:
        # If console is not found, we can't do anything
        return line

    # If the command is already perfect, leave it alone
    if clean_cmd in all_valid:
        return line

    # Fuzzy matching (Levenshtein)
    best_match = None
    min_dist = 3

    for valid in all_valid:
        dist = _levenshtein(clean_cmd, valid)
        if dist < min_dist:
            min_dist = dist
            best_match = valid

    if best_match:
        # Inform the user and replace the command
        print(f"  {C.MUTED}ℹ Auto-correcting: {C.RED}{clean_cmd}{C.MUTED} -> {C.CYAN}{best_match}{C.RESET}")
        return " ".join([best_match] + args)

    return line


def _levenshtein(s1, s2):
    if len(s1) < len(s2): return _levenshtein(s2, s1)
    if not s2: return len(s1)
    prev = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        curr = [i + 1]
        for j, c2 in enumerate(s2):
            curr.append(min(prev[j + 1] + 1, curr[j] + 1, prev[j] + (c1 != c2)))
        prev = curr
    return prev[-1]