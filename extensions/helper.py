# CC-TYPE: extension
# CC-NAME: typo_fixer
# CC-DESCRIPTION: Automatically corrects command typos using Fuzzy Matching.

def on_input(line):
    """
    Hooks into the input stream to catch and fix typos before execution.
    Note: 'console' is injected globally by the ExtensionHost at runtime.
    """
    if not line or not line.strip():
        return line

    parts = line.split()
    cmd_raw = parts[0].lower()
    args = parts[1:] if len(parts) > 1 else []

    # Use the ansi_strip utility from the engine to clean input
    from utils import ansi_strip
    clean_cmd = ansi_strip(cmd_raw)

    # Standard built-in commands defined in main.py
    built_ins = [
        "help", "exit", "quit", "config", "reset", "agent-mode",
        "pull", "register-api-key", "command-list", "feature-list", "feature-status"
    ]

    # Access the actual command registries from the injected console object
    # global console is used here because the engine injects it into the module dict
    try:
        all_valid = built_ins + list(console.commands.keys()) + list(console.ext_cmds.keys())
    except NameError:
        # Fallback if extension is tested outside of the engine
        return line

    if clean_cmd in all_valid:
        return line

    # Fuzzy matching: Find the closest command within a distance of 2 characters
    best_match = None
    min_distance = 3

    for valid in all_valid:
        dist = _levenshtein(clean_cmd, valid)
        if dist < min_distance:
            min_distance = dist
            best_match = valid

    # If a close match is found, replace the command and notify the user
    if best_match:
        from ui import C
        new_line = " ".join([best_match] + args)
        # We print directly to avoid double-processing the output hook
        print(f"  {C.MUTED}ℹ Did you mean '{C.CYAN}{best_match}{C.MUTED}'? Correcting...{C.RESET}")
        return new_line

    return line


def _levenshtein(s1, s2):
    """Calculates the Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return _levenshtein(s2, s1)
    if not s2:
        return len(s1)
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]