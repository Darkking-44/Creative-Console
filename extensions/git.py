# CC-TYPE: extension
# CC-NAME: git
# CC-DESCRIPTION: Native Git integration — exposes Git commands directly in the console.
# CC-REQUIREMENTS: none

import subprocess
import shutil


def provides_commands():
    """Register the 'git' command with the extension host."""
    return {
        "git": {
            "handler": run_git,
            "description": "Run Git commands directly (e.g. git status, git pull)."
        }
    }


def run_git(args_list, console):
    """
    Execute a Git command with the given arguments.

    Args:
        args_list (list[str]): Arguments to pass to the git binary.
        console: The active console instance (unused here, required by the interface).

    Returns:
        str: Combined stdout/stderr output, or an error message.
    """
    if not shutil.which("git"):
        return "❌ Git is not installed or not available in PATH."

    if not args_list:
        return "⚠️  Please provide a Git command (e.g. git status)."

    try:
        result = subprocess.run(
            ["git"] + args_list,
            capture_output=True,
            text=True,
            encoding="utf-8"
        )

        output_parts = []
        if result.stdout:
            output_parts.append(result.stdout)
        if result.stderr:
            # Git frequently writes informational messages to stderr — include them.
            output_parts.append(result.stderr)

        combined = "\n".join(output_parts).strip()
        return combined if combined else "✔️  Git command executed successfully."

    except Exception as exc:
        return f"❌ Failed to execute Git: {exc}"


def on_startup(console):
    """Print a confirmation message when this extension is loaded."""
    from ui import C
    print(f"  {C.SUCCESS}✓{C.RESET} Git extension active.")
