# CC-TYPE:        extension
# CC-NAME:        clone
# CC-VERSION:     E0.1
# CC-DESCRIPTION: Repository cloning utility — clones Git repos and auto-pulls 'run' if needed.
# CC-REQUIREMENTS: requests

import subprocess
import shutil
import os
from pathlib import Path
from ui import C, Spinner

VERSION = "E0.1"


# ---------------------------------------------------------------------------
# Command registration
# ---------------------------------------------------------------------------

def provides_commands():
    """Register the 'clone' command with the extension host."""
    return {
        "clone": {
            "handler": handle_clone,
            "description": "Clone a git repository and optionally run its entry point."
        }
    }


# ---------------------------------------------------------------------------
# Command handler
# ---------------------------------------------------------------------------

def handle_clone(args, console):
    """
    Clones a repository and attempts to execute it via the 'run' extension.

    Usage:
        clone <url>             Clones the repo into the current directory.
        clone <url> <file>      Clones and immediately executes <file> using 'run'.

    Args:
        args (list[str]): Command arguments (URL and optional file to run).
        console: The active console instance.
    """
    if not args:
        return f"{C.ERROR}Usage: clone <repo_url> [file_to_run]{C.RESET}"

    if not shutil.which("git"):
        return f"{C.ERROR}Git is not installed or not in PATH.{C.RESET}"

    repo_url = args[0]
    # Extract folder name from URL (e.g., https://github.com/user/repo -> repo)
    repo_name = repo_url.split("/")[-1].replace(".git", "")
    target_dir = Path.cwd() / repo_name

    # Step 1: Clone the repository
    print(f"  {C.MUTED}Cloning {repo_url}...{C.RESET}")
    try:
        with Spinner(f"Cloning {repo_name}"):
            subprocess.run(["git", "clone", repo_url], capture_output=True, check=True)
        print(f"  {C.SUCCESS}Done: {repo_name} cloned successfully.{C.RESET}")
    except subprocess.CalledProcessError as e:
        return f"{C.ERROR}Clone failed: {e.stderr.decode().strip()}{C.RESET}"

    # Step 2: Check if execution is requested
    if len(args) > 1:
        file_to_run = args[1]
        full_path = target_dir / file_to_run

        if not full_path.exists():
            return f"{C.WARN}Repo cloned, but file '{file_to_run}' not found in {repo_name}.{C.RESET}"

        # Step 3: Ensure 'run' extension is available
        _ensure_run_extension(console)

        # Step 4: Execute the file using the 'run' command handler
        print(f"  {C.MUTED}Executing {file_to_run} via 'run' extension...{C.RESET}")

        # Navigate into the repo for execution
        old_cwd = os.getcwd()
        os.chdir(str(target_dir))

        try:
            # We call the 'run' command directly from console.ext_cmds
            if "run" in console.ext_cmds:
                handler = console.ext_cmds["run"]["fn"]
                # Pass the relative file name to the handler
                handler([file_to_run], console)
            else:
                return f"{C.ERROR}The 'run' extension failed to load or is unavailable.{C.RESET}"
        finally:
            os.chdir(old_cwd)

    return ""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ensure_run_extension(console):
    """
    Checks if the 'run' command is registered. If not, pulls it from remote.
    """
    if "run" in console.ext_cmds:
        return

    print(f"  {C.WARN}Required extension 'run' is missing. Pulling now...{C.RESET}")

    # Import the pull logic from main console structure
    from pull import cmd_pull
    cmd_pull(console, "run")

    # The pull logic installs the file to the extensions directory.
    # We must manually trigger a reload or check if it was loaded.
    if "run" not in console.ext_cmds:
        print(f"  {C.ERROR}Failed to auto-install 'run'. Please install manually: pull run{C.RESET}")


# ---------------------------------------------------------------------------
# Lifecycle hooks
# ---------------------------------------------------------------------------

def on_startup(console):
    """Print confirmation message when extension is loaded."""
    print(f"  {C.SUCCESS}✓{C.RESET} Clone Extension v{VERSION} active.")