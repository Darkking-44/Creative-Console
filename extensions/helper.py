# CC-TYPE: extension
# CC-NAME: helper
# CC-DESCRIPTION: Fuzzy-matching input hook that auto-corrects mistyped commands.

import utils
from ui import C


def on_input(line):
    """
    Hook into raw console input and correct minor typos via fuzzy matching.

    If the entered command is not recognised but closely resembles a known
    command (Levenshtein distance < 3), it is silently replaced and the user
    is informed of the substitution.

    Args:
        line (str): The raw input line from the user.

    Returns:
        str: The (possibly corrected) input line.
    """
    if not line or not line.strip():
        return line

    parts = line.split()
    raw_cmd = parts[0]
    args = parts[1:] if len(parts) > 1 else []

    # Strip ANSI colour codes before comparing.
    clean_cmd = utils.ansi_strip(raw_cmd).lower()

    try:
        # Built-in routes defined in main.py.
        built_ins = [
            "help", "exit", "quit", "config", "reset", "agent-mode",
            "pull", "register-api-key", "command-list", "feature-list",
            "command-build", "command-see", "command-open", "command-rework"
        ]

        # Combine built-ins with any dynamically registered commands.
        all_valid = built_ins + list(console.commands.keys()) + list(console.ext_cmds.keys())
    except NameError:
        # 'console' is injected into this module's globals by the ExtensionHost.
        # If it is absent we cannot perform any matching.
        return line

    # If the command already matches exactly, leave the line unchanged.
    if clean_cmd in all_valid:
        return line

    # Find the closest match using Levenshtein distance.
    best_match = None
    min_dist = 3  # Maximum tolerated edit distance.

    for candidate in all_valid:
        dist = _levenshtein(clean_cmd, candidate)
        if dist < min_dist:
            min_dist = dist
            best_match = candidate

    if best_match:
        print(
            f"  {C.MUTED}ℹ  Auto-correcting: "
            f"{C.RED}{clean_cmd}{C.MUTED} → {C.CYAN}{best_match}{C.RESET}"
        )
        return " ".join([best_match] + args)

    return line


def _levenshtein(s1, s2):
    """
    Compute the Levenshtein edit distance between two strings.

    Args:
        s1 (str): First string.
        s2 (str): Second string.

    Returns:
        int: The minimum number of single-character edits required to
             transform s1 into s2.
    """
    if len(s1) < len(s2):
        return _levenshtein(s2, s1)
    if not s2:
        return len(s1)

    prev = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        curr = [i + 1]
        for j, c2 in enumerate(s2):
            curr.append(min(prev[j + 1] + 1, curr[j] + 1, prev[j] + (c1 != c2)))
        prev = curr

    return prev[-1]
