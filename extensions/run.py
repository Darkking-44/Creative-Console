# CC-TYPE: extension
# CC-NAME: run
# CC-DESCRIPTION: Universal runner and auto-installer for Python, C/C++, Java, Rust, CUDA, and Arduino.

import os
import subprocess
import shutil
import platform
import re
from pathlib import Path
from ui import C, Spinner


# ---------------------------------------------------------------------------
# Command registration
# ---------------------------------------------------------------------------

def provides_commands():
    """Register the 'run' command with the extension host."""
    return {
        "run": {
            "handler": handle_run,
            "description": (
                "Compile and execute source files by extension. "
                "Missing toolchains are installed automatically."
            )
        }
    }


# ---------------------------------------------------------------------------
# Main dispatcher
# ---------------------------------------------------------------------------

def handle_run(args, console):
    """
    Resolve the file path, ensure the required toolchain is present, then
    compile and/or execute the file.

    Supported extensions: .py  .c  .cpp  .java  .rs  .cu  .ino

    Args:
        args (list[str]): Command arguments; the first element is the file path.
        console: The active console instance (unused, required by interface).

    Returns:
        str: Execution result or error message.
    """
    if not args:
        return f"{C.ERROR}Usage: run <filepath>{C.RESET}"

    # Reconstruct and sanitise the path (handles spaces and surrounding quotes).
    raw_path = " ".join(args).strip().strip('"').strip("'")
    file_path = Path(raw_path)

    if not file_path.exists():
        return f"{C.ERROR}File not found: {file_path.absolute()}{C.RESET}"

    ext = file_path.suffix.lower()

    # Ensure the required toolchain is available before attempting to compile.
    _ensure_toolchain(ext)

    dispatch = {
        ".py":   _run_py,
        ".c":    _run_cpp,
        ".cpp":  _run_cpp,
        ".java": _run_java,
        ".rs":   _run_rust,
        ".cu":   _run_cuda,
        ".ino":  _run_arduino,
    }

    handler = dispatch.get(ext)
    if handler is None:
        return f"{C.ERROR}Unsupported extension: '{ext}'.{C.RESET}"

    return handler(file_path)


# ---------------------------------------------------------------------------
# Toolchain management
# ---------------------------------------------------------------------------

def _ensure_toolchain(ext):
    """
    Check whether the toolchain required for *ext* is available and, if not,
    trigger OS-appropriate installation.

    Args:
        ext (str): File extension including the leading dot (e.g. '.cpp').
    """
    checks = {
        ".c":    ("g++",         "g++"),
        ".cpp":  ("g++",         "g++"),
        ".java": ("javac",       "java"),
        ".rs":   ("rustc",       "rust"),
        ".cu":   ("nvcc",        "cuda"),
        ".ino":  ("arduino-cli", "arduino"),
    }

    entry = checks.get(ext)
    if entry is None:
        return  # No external toolchain required (e.g. Python).

    binary, tool_key = entry

    if shutil.which(binary):
        return  # Already installed.

    if tool_key == "cuda" and not _has_nvidia_gpu():
        return  # Let _run_cuda handle the missing-GPU error.

    _install_tool(tool_key)


def _install_tool(tool):
    """
    Launch an OS-specific installer or open the relevant download page.

    On Windows, 'start' is a shell built-in and must be invoked via shell=True
    as a single command string — NOT as a list.

    Args:
        tool (str): Tool identifier: 'java', 'g++', 'rust', 'cuda', or 'arduino'.
    """
    print(f"  {C.WARN}'{tool}' not found — launching installer…{C.RESET}")
    is_windows = platform.system() == "Windows"

    # Each entry is (command_string, use_shell).
    # Windows URLs use 'start <url>' which requires shell=True.
    # Linux commands are passed as strings to shell=True as well for simplicity.
    installers = {
        "java": {
            True:  ("start https://aws.amazon.com/corretto/",                                True),
            False: ("sudo apt install -y default-jdk",                                        True),
        },
        "g++": {
            True:  ("start https://www.msys2.org/",                                          True),
            False: ("sudo apt install -y build-essential",                                    True),
        },
        "rust": {
            True:  ("start https://rustup.rs",                                               True),
            False: ("curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh",        True),
        },
        "cuda": {
            True:  ("start https://developer.nvidia.com/cuda-downloads",                     True),
            False: ("xdg-open https://developer.nvidia.com/cuda-downloads",                  True),
        },
        "arduino": {
            True:  ("start https://arduino.github.io/arduino-cli/latest/installation/",      True),
            False: (
                "curl -fsSL "
                "https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh",
                True,
            ),
        },
    }

    entry = installers.get(tool, {}).get(is_windows)
    if entry:
        cmd, use_shell = entry
        subprocess.run(cmd, shell=use_shell)

    print(f"  {C.SUCCESS}Follow the installer instructions, then restart the console.{C.RESET}")


# ---------------------------------------------------------------------------
# Language runners
# ---------------------------------------------------------------------------

def _run_py(path):
    """Execute a Python script in a subprocess (inherits stdio for interactivity)."""
    print(f"  {C.MUTED}Running Python: {path.name}{C.RESET}")
    subprocess.run(["python", str(path)])
    return ""


def _run_cpp(path):
    """Compile a C/C++ file with g++ and execute the resulting binary."""
    binary = path.stem + (".exe" if platform.system() == "Windows" else "")

    with Spinner(f"Compiling {path.name}"):
        result = subprocess.run(["g++", str(path), "-o", binary], capture_output=True, text=True)

    if result.returncode != 0:
        return f"{C.ERROR}Compilation failed:\n{result.stderr}{C.RESET}"

    exec_cmd = [binary] if platform.system() == "Windows" else [f"./{binary}"]
    subprocess.run(exec_cmd)
    return f"  {C.MUTED}--- Process finished ---{C.RESET}"


def _run_java(path):
    """Compile a Java source file and run the resulting class (GUI-compatible)."""
    with Spinner(f"Compiling {path.name}"):
        result = subprocess.run(["javac", str(path)], capture_output=True, text=True)

    if result.returncode != 0:
        return f"{C.ERROR}Compilation failed:\n{result.stderr}{C.RESET}"

    print(f"  {C.PURPLE}Launching JVM…{C.RESET}")
    # Inherit stdio so that GUI windows and interactive programs work correctly.
    subprocess.run(["java", path.stem])
    return f"  {C.MUTED}--- Process finished ---{C.RESET}"


def _run_rust(path):
    """Compile a Rust source file with rustc and execute it."""
    with Spinner(f"Compiling {path.name}"):
        result = subprocess.run(["rustc", str(path)], capture_output=True, text=True)

    if result.returncode != 0:
        return f"{C.ERROR}Compilation failed:\n{result.stderr}{C.RESET}"

    binary = path.stem + (".exe" if platform.system() == "Windows" else "")
    exec_cmd = [binary] if platform.system() == "Windows" else [f"./{binary}"]
    subprocess.run(exec_cmd)
    return ""


def _run_cuda(path):
    """Compile a CUDA source file with nvcc and execute the resulting binary."""
    if not _has_nvidia_gpu():
        return f"{C.ERROR}No NVIDIA GPU detected — CUDA is unavailable.{C.RESET}"

    # Place the binary next to the source file to avoid working-directory issues.
    binary = path.parent / (path.stem + (".exe" if platform.system() == "Windows" else ""))

    with Spinner(f"Building CUDA binary from {path.name}"):
        result = subprocess.run(
            ["nvcc", str(path), "-o", str(binary)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",   # Prevent UnicodeDecodeError on Windows terminals.
        )

    # nvcc sometimes writes errors to stdout rather than stderr — include both.
    compiler_output = "\n".join(filter(None, [result.stdout.strip(), result.stderr.strip()]))

    if result.returncode != 0:
        detail = compiler_output or "(nvcc produced no output)"
        return f"{C.ERROR}CUDA compilation failed:\n{detail}{C.RESET}"

    subprocess.run([str(binary.absolute())])
    return ""


def _run_arduino(path):
    """Compile and upload an Arduino sketch after prompting for port and FQBN."""
    board_data = subprocess.run(
        ["arduino-cli", "board", "list"], capture_output=True, text=True
    ).stdout
    ports = re.findall(r"(COM\d+|/dev/tty[a-zA-Z0-9]+)", board_data)

    if not ports:
        return f"{C.ERROR}No Arduino board detected.{C.RESET}"

    print(f"  {C.HEADING}Detected ports:{C.RESET}")
    for idx, port in enumerate(ports):
        print(f"    [{idx}] {port}")

    try:
        selection = int(input(f"  {C.CYAN}Select port index: {C.RESET}"))
        selected_port = ports[selection]
    except (ValueError, IndexError):
        return f"{C.ERROR}Invalid selection.{C.RESET}"

    fqbn = input(f"  {C.CYAN}Enter FQBN (e.g. arduino:avr:uno): {C.RESET}").strip()

    with Spinner("Compiling and uploading"):
        subprocess.run([
            "arduino-cli", "compile", "--upload",
            "-p", selected_port, "--fqbn", fqbn, str(path)
        ])

    return "  Upload complete."


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _has_nvidia_gpu():
    """Return True if nvidia-smi is available, indicating an NVIDIA GPU is present."""
    return shutil.which("nvidia-smi") is not None


# ---------------------------------------------------------------------------
# Lifecycle hooks
# ---------------------------------------------------------------------------

def on_startup(console):
    """Print a confirmation message when this extension is loaded."""
    print(f"  {C.SUCCESS}✓{C.RESET} Runner Engine v3.1 online (GUI support enabled).")
