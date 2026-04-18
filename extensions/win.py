# CC-TYPE: extension
# CC-NAME: win
# CC-DESCRIPTION: Windows PowerShell bridge — execute native PowerShell commands from the console.
# CC-REQUIREMENTS: none

import subprocess
import os


def provides_commands():
    """Register the 'win' command with the extension host."""
    return {
        "win": {
            "handler": run_powershell,
            "description": "Execute a PowerShell command (e.g. win Get-Process)."
        }
    }


def run_powershell(args_list, console):
    """
    Join the provided arguments into a single PowerShell command and execute it.

    Args:
        args_list (list[str]): Tokens that form the PowerShell command.
        console: The active console instance (unused, required by interface).

    Returns:
        str: Combined stdout/stderr output, or an error message.
    """
    if os.name != "nt":
        return "❌ This command is only available on Windows."

    if not args_list:
        return "⚠️  Please provide a PowerShell command (e.g. win Get-Process)."

    command = " ".join(args_list)

    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
            capture_output=True,
            text=True,
            encoding="cp850"  # Standard Windows console encoding.
        )

        output_parts = []
        if result.stdout:
            output_parts.append(result.stdout)
        if result.stderr:
            output_parts.append(f"[PowerShell Error]:\n{result.stderr}")

        combined = "\n".join(output_parts).strip()
        return combined if combined else "✔️  Command executed with no output."

    except Exception as exc:
        return f"❌ Failed to execute PowerShell command: {exc}"


def on_startup(console):
    """Print a confirmation message when this extension is loaded."""
    from ui import C
    print(f"  {C.SUCCESS}✓{C.RESET} Windows PowerShell bridge ready.")
