# CC-TYPE: extension
# CC-NAME: helper
# CC-DESCRIPTION: Fuzzy Matching

def on_input(line):
    """Checks if the command has a typo and fixes it on the fly."""
    if not line.strip(): return line
    
    parts = line.split()
    cmd = parts[0].lower()
    args = parts[1:] if len(parts) > 1 else []

    # Get all available commands from the console
    from main import ansi_strip
    clean_cmd = ansi_strip(cmd)
    
    # List of all valid commands
    built_ins = ["help", "exit", "config", "reset", "agent-mode", "pull", "feature-list"]
    all_valid = built_ins + list(console.commands.keys()) + list(console.ext_cmds.keys())

    if clean_cmd in all_valid:
        return line

    # Find the best match
    best_match = None
    min_distance = 3 # Max errors allowed (1-2 characters)

    for valid in all_valid:
        dist = _levenshtein(clean_cmd, valid)
        if dist < min_distance:
            min_distance = dist
            best_match = valid

    if best_match:
        from ui import C
        new_line = " ".join([best_match] + args)
        print(f"  {C.MUTED}ℹ Meinten Sie '{C.CYAN}{best_match}{C.MUTED}'? Korrigiere...{C.RESET}")
        return new_line

    return line

def _levenshtein(s1, s2):
    """Calculates the edit distance between two strings."""
    if len(s1) < len(s2): return _levenshtein(s2, s1)
    if not s2: return len(s1)
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