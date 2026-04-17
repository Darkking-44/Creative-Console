# CC-TYPE: extension
# CC-NAME: run
# CC-DESCRIPTION: Universal runner and auto-installer for C++, Java, Rust, CUDA, and Arduino.

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
            "description": "Compiles and executes files based on extension. Auto-installs missing tools."
        }
    }

def handle_run(args, console):
    """Main entry point. Cleans paths and dispatches to compilers."""
    if not args:
        return f"{C.ERROR}Usage: run <filepath>{C.RESET}"

    # Clean path from quotes and whitespace
    raw_path = " ".join(args).strip().strip('"').strip("'")
    file_path = Path(raw_path)
    
    if not file_path.exists():
        return f"{C.ERROR}File not found: {file_path.absolute()}{C.RESET}"

    ext = file_path.suffix.lower()
    
    # Pre-check dependencies
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

    # Routing to execution handlers
    if ext == ".py": return _run_py(file_path)
    if ext in [".cpp", ".c"]: return _run_cpp(file_path)
    if ext == ".java": return _run_java(file_path)
    if ext == ".rs": return _run_rust(file_path)
    if ext == ".cu": return _run_cuda(file_path)
    if ext == ".ino": return _run_arduino(file_path)
    
    return f"{C.ERROR}Extension {ext} is not supported.{C.RESET}"

def _install_tool(tool):
    """Triggers OS-specific installation or opens download pages."""
    print(f"  {C.WARN}Status: {tool.upper()} missing. Launching installer...{C.RESET}")
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
    
    print(f"  {C.SUCCESS}Action: Follow instructions and restart the console.{C.RESET}")

def _run_py(p):
    """Executes Python scripts interactively."""
    print(f"  {C.MUTED}Running Python: {p.name}{C.RESET}")
    subprocess.run(["python", str(p)], stdout=None, stderr=None)
    return ""

def _run_java(p):
    """Compiles and runs Java files. Supports GUI windows."""
    with Spinner(f"Compiling {p.name}"):
        res = subprocess.run(["javac", str(p)], capture_output=True, text=True)
        if res.returncode != 0: return f"{C.ERROR}Java Error:\n{res.stderr}{C.RESET}"
    
    print(f"  {C.PURPLE}Launching JVM...{C.RESET}")
    # Run without capturing to allow GUI windows to spawn correctly
    subprocess.run(["java", p.stem], stdout=None, stderr=None)
    return f"  {C.MUTED}--- Process finished ---{C.RESET}"

def _run_cpp(p):
    """Compiles and runs C++ files."""
    out = p.stem + (".exe" if platform.system() == "Windows" else "")
    with Spinner(f"Compiling {p.name}"):
        res = subprocess.run(["g++", str(p), "-o", out], capture_output=True, text=True)
        if res.returncode != 0: return f"{C.ERROR}C++ Error:\n{res.stderr}{C.RESET}"
    
    exec_cmd = [f"./{out}" if platform.system() != "Windows" else out]
    subprocess.run(exec_cmd, stdout=None, stderr=None)
    return f"  {C.MUTED}--- Process finished ---{C.RESET}"

def _run_rust(p):
    """Compiles and runs Rust files."""
    with Spinner(f"Compiling Rust {p.name}"):
        res = subprocess.run(["rustc", str(p)], capture_output=True, text=True)
        if res.returncode != 0: return f"{C.ERROR}Rust Error:\n{res.stderr}{C.RESET}"
    
    exec_cmd = ["./" + p.stem if platform.system() != "Windows" else p.stem + ".exe"]
    subprocess.run(exec_cmd, stdout=None, stderr=None)
    return ""

def _run_cuda(p):
    """Compiles and runs CUDA files using NVCC."""
    out = p.stem + (".exe" if platform.system() == "Windows" else "")
    with Spinner(f"Building CUDA {p.name}"):
        res = subprocess.run(["nvcc", str(p), "-o", out], capture_output=True, text=True)
        if res.returncode != 0: return f"{C.ERROR}CUDA Error:\n{res.stderr}{C.RESET}"
    
    subprocess.run([str(Path(out).absolute())], stdout=None, stderr=None)
    return ""

def _run_arduino(p):
    """Handles Arduino upload with COM port selection."""
    board_data = subprocess.run(["arduino-cli", "board", "list"], capture_output=True, text=True).stdout
    ports = re.findall(r"(COM\d+|/dev/tty[a-zA-Z0-9]+)", board_data)
    if not ports: return f"{C.ERROR}No board found.{C.RESET}"
    
    print(f"  {C.HEADING}Connected Ports:{C.RESET}")
    for i, port in enumerate(ports): print(f"  [{i}] {port}")
    
    try:
        idx = int(input(f"  {C.CYAN}Select Index: {C.RESET}"))
        selected_port = ports[idx]
    except: return f"{C.ERROR}Invalid input.{C.RESET}"
    
    fqbn = input(f"  {C.CYAN}Enter FQBN: {C.RESET}").strip()
    with Spinner("Uploading"):
        subprocess.run(["arduino-cli", "compile", "--upload", "-p", selected_port, "--fqbn", fqbn, str(p)])
    return "Upload complete."

def _has_nvidia():
    """Check for NVIDIA GPU presence."""
    return shutil.which("nvidia-smi") is not None

def on_startup(console):
    """Initialize extension."""
    print(f"  {C.SUCCESS}Runner-Engine v3.1 online (GUI-Support enabled).{C.RESET}")