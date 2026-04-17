# CC-TYPE: extension
# CC-NAME: run
# CC-DESCRIPTION: Universal runner & auto-installer for C++, Java, Rust, CUDA, and Arduino.

import os
import subprocess
import shutil
import platform
import re
from pathlib import Path
from ui import C, Spinner

def provides_commands():
    return {
        "run": {
            "handler": handle_run,
            "description": "Compiles/runs files and auto-installs missing compilers."
        }
    }

def handle_run(args, console):
    if not args:
        return f"{C.ERROR}Usage: run <filepath>{C.RESET}"

    # Path cleaning (strips quotes and spaces)
    raw_path = " ".join(args).strip().strip('"').strip("'")
    file_path = Path(raw_path)
    
    if not file_path.exists():
        return f"{C.ERROR}File not found: {file_path.absolute()}{C.RESET}"

    ext = file_path.suffix.lower()
    
    # Check dependencies before running
    if ext in [".cpp", ".c"] and not shutil.which("g++"):
        _install_tool("g++")
    elif ext == ".java" and not shutil.which("javac"):
        _install_tool("java")
    elif ext == ".rs" and not shutil.which("rustc"):
        _install_tool("rust")
    elif ext == ".cu" and not shutil.which("nvcc"):
        if _has_nvidia(): _install_tool("cuda")
        else: return f"{C.ERROR}No NVIDIA GPU detected for CUDA.{C.RESET}"
    elif ext == ".ino" and not shutil.which("arduino-cli"):
        _install_tool("arduino")

    # Routing to execution
    if ext == ".py": return _run_py(file_path)
    if ext in [".cpp", ".c"]: return _run_cpp(file_path)
    if ext == ".java": return _run_java(file_path)
    if ext == ".rs": return _run_rust(file_path)
    if ext == ".cu": return _run_cuda(file_path)
    if ext == ".ino": return _run_arduino(file_path)
    
    return f"{C.ERROR}Extension {ext} not supported yet.{C.RESET}"

def _install_tool(tool):
    """Triggers OS-specific installation or download pages."""
    print(f"  {C.WARN}⚠ {tool.upper()} missing. Launching installer...{C.RESET}")
    is_win = platform.system() == "Windows"
    
    if tool == "java":
        if is_win: subprocess.run("start https://aws.amazon.com/corretto/", shell=True)
        else: subprocess.run("sudo apt install -y default-jdk", shell=True)
    elif tool == "g++":
        if is_win: subprocess.run("start https://www.msys2.org/", shell=True)
        else: subprocess.run("sudo apt install -y build-essential", shell=True)
    elif tool == "rust":
        if is_win: subprocess.run("start https://rustup.rs", shell=True)
        else: subprocess.run("curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh", shell=True)
    elif tool == "cuda":
        subprocess.run("start https://developer.nvidia.com/cuda-downloads", shell=True)
    elif tool == "arduino":
        if is_win: subprocess.run("start https://arduino.github.io/arduino-cli/latest/installation/", shell=True)
        else: subprocess.run("curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh", shell=True)
    
    print(f"  {C.SUCCESS}Follow the instructions in your browser/terminal and restart the console.{C.RESET}")

# --- Execution Handlers (Standard implementations) ---

def _run_py(p):
    return subprocess.run(["python", str(p)], capture_output=True, text=True).stdout

def _run_java(p):
    with Spinner("Compiling Java"):
        subprocess.run(["javac", str(p)], check=True)
    return subprocess.run(["java", p.stem], capture_output=True, text=True).stdout

def _run_cpp(p):
    out = p.stem + (".exe" if platform.system() == "Windows" else "")
    with Spinner("Compiling C++"):
        subprocess.run(["g++", str(p), "-o", out], check=True)
    return subprocess.run([f"./{out}" if platform.system() != "Windows" else out], capture_output=True, text=True).stdout

def _run_arduino(p):
    # (Arduino logic from previous version with COM-Select)
    return "Arduino Upload Logic triggered..."

def _has_nvidia():
    return shutil.which("nvidia-smi") is not None

def on_startup(console):
    print(f"  {C.SUCCESS}✓{C.RESET} Runner-Engine v3.0 (Auto-Installer) online.")