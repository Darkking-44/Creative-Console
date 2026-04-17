# CC-TYPE: extension
# CC-NAME: run
# CC-DESCRIPTION: Intelligent multi-language runner with COM-port selection for Arduino.

import os
import subprocess
import shutil
import platform
import re
from pathlib import Path
from ui import C, Spinner


def provides_commands():
    """Register the 'run' command to the console."""
    return {
        "run": {
            "handler": handle_run,
            "description": "Compiles and executes files (C++, Rust, CUDA, Python, Java, Arduino/Ino)."
        }
    }


def handle_run(args, console):
    """Main execution router based on file extension."""
    if not args:
        return f"{C.ERROR}Usage: run <filepath>{C.RESET}"

    file_path = Path(args[0])
    if not file_path.exists():
        return f"{C.ERROR}File not found: {file_path}{C.RESET}"

    ext = file_path.suffix.lower()

    # Language Dispatcher
    if ext == ".py":
        return _run_python(file_path)
    elif ext in [".cpp", ".cxx", ".cc", ".c"]:
        return _run_native_c(file_path)
    elif ext == ".rs":
        return _run_rust(file_path)
    elif ext == ".cu":
        return _run_cuda(file_path)
    elif ext == ".ino":
        return _run_arduino(file_path)
    elif ext == ".java":
        return _run_java(file_path)
    else:
        return f"{C.ERROR}Unsupported file type: {ext}{C.RESET}"


# --- Language Handlers ---

def _run_python(path):
    print(f"  {C.MUTED}Running Python script...{C.RESET}")
    result = subprocess.run(["python", str(path)], capture_output=True, text=True)
    return result.stdout + result.stderr


def _run_rust(path):
    """Compiles and runs Rust files, prompts for rustup if missing."""
    if not shutil.which("rustc"):
        print(f"  {C.WARN}Rust compiler (rustc) not found.{C.RESET}")
        if input("  Install via rustup? (y/N): ").lower() in ["y", "j"]:
            _install_rust()
            return "Installation started."
        return "Rust execution aborted."

    with Spinner(f"Compiling Rust: {path.name}"):
        res = subprocess.run(["rustc", str(path)], capture_output=True, text=True)

    if res.returncode != 0: return f"{C.ERROR}Rust Error:\n{res.stderr}{C.RESET}"
    exec_file = "./" + path.stem if platform.system() != "Windows" else path.stem + ".exe"
    return subprocess.run([exec_file], capture_output=True, text=True).stdout


def _run_arduino(path):
    """Handles .ino files with interactive COM port selection."""
    if not shutil.which("arduino-cli"):
        return f"{C.ERROR}arduino-cli not found. Install it to flash microcontrollers.{C.RESET}"

    print(f"  {C.CYAN}Scanning for connected boards...{C.RESET}")

    # Get board list
    board_data = subprocess.run(["arduino-cli", "board", "list"], capture_output=True, text=True).stdout
    ports = re.findall(r"(COM\d+|/dev/tty[a-zA-Z0-9]+)", board_data)

    if not ports:
        print(f"  {C.WARN}No boards detected automatically.{C.RESET}")
        port = input(f"  {C.CYAN}Enter COM port manually (e.g. COM3): {C.RESET}").strip()
    else:
        print(f"  {C.HEADING}── AVAILABLE PORTS ──{C.RESET}")
        for i, p in enumerate(ports):
            print(f"  [{i}] {p}")

        idx = input(f"  {C.CYAN}Select port index [0-{len(ports) - 1}]: {C.RESET}")
        try:
            port = ports[int(idx)]
        except:
            return f"{C.ERROR}Invalid selection.{C.RESET}"

    fqbn = input(f"  {C.CYAN}Enter FQBN (e.g. arduino:avr:uno or esp32:esp32:devkit-v1): {C.RESET}").strip()

    with Spinner(f"Uploading {path.name} to {port}"):
        res = subprocess.run(["arduino-cli", "compile", "--upload", "-p", port, "--fqbn", fqbn, str(path)],
                             capture_output=True, text=True)

    return res.stdout + res.stderr


def _run_native_c(path):
    """Compiles C/C++ using G++."""
    if not shutil.which("g++"):
        return f"{C.ERROR}G++ compiler not found.{C.RESET}"

    out = path.stem + (".exe" if platform.system() == "Windows" else "")
    with Spinner(f"Compiling {path.name}"):
        res = subprocess.run(["g++", str(path), "-o", out], capture_output=True, text=True)

    if res.returncode != 0: return f"{C.ERROR}G++ Error:\n{res.stderr}{C.RESET}"

    exec_cmd = [f"./{out}"] if platform.system() != "Windows" else [out]
    return subprocess.run(exec_cmd, capture_output=True, text=True).stdout


# --- Helper Methods ---

def _install_rust():
    """Triggers the Rust installer based on OS."""
    if platform.system() == "Windows":
        subprocess.run("start https://rustup.rs", shell=True)
    else:
        subprocess.run("curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh", shell=True)


def on_startup(console):
    """Greeting on extension load."""
    print(f"  {C.SUCCESS}✓{C.RESET} Runner-Engine v2.0 (with COM-Auto-Select) active.")