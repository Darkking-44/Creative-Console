# CC-TYPE: extension
# CC-NAME: typo_fixer
# CC-DESCRIPTION: Fuzzy logic hook to fix typos before command dispatch.

import utils
from ui import C

def on_input(line):
    """
    Standard Hook: Intercepts the raw input string.
    If the command is unknown, it attempts to find the nearest match.
    """
    if not line or not line.strip():
        return line

    parts = line.split()
    raw_cmd = parts[0].lower()
    args = parts[1:] if len(parts) > 1 else []

    # Clean the command name from any ANSI residue
    clean_cmd = utils.ansi_strip(raw_cmd)

    # Accessing the global console object injected by ExtensionHost
    # We define built-ins and fetch registered commands
    built_ins = [
        "help", "exit", "quit", "config", "reset", "agent-mode", 
        "pull", "register-api-key", "command-list", "feature-list"
    ]
    
    # Combined list of every valid trigger in the engine
    all_valid = built_ins + list(console.commands.keys()) + list(console.ext_cmds.keys())

    # Do nothing if the command is already recognized
    if clean_cmd in all_valid:
        return line

    # Fuzzy matching search
    best_match = None
    min_dist = 3  # Tolerance threshold

    for valid in all_valid:
        dist = _levenshtein(clean_cmd, valid)
        if dist < min_dist:
            min_dist = dist
            best_match = valid

    # Auto-correction if a match is close enough
    if best_match:
        # Inform the user through the UI
        print(f"  {C.MUTED}ℹ Did you mean '{C.CYAN}{best_match}{C.MUTED}'? Correcting...{C.RESET}")
        return " ".join([best_match] + args)

    return line

def _levenshtein(s1, s2):
    """Calculates Levenshtein distance to find the closest string match."""
    if len(s1) < len(s2): return _levenshtein(s2, s1)
    if not s2: return len(s1)
    prev_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            sub = prev_row[j] + (c1 != c2)
            curr_row.append(min(prev_row[j+1]+1, curr_row[j]+1, sub))
        prev_row = curr_row
    return prev_row[-1]

def provides_commands():
    """Returns empty dict as this extension only provides a background hook."""
    return {}