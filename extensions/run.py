# CC-TYPE: extension
# CC-NAME: run
# CC-DESCRIPTION: Global Runner v3.3 - Smart Path Discovery and Auto-Installer.

import os
import subprocess
import shutil
import platform
import re
from pathlib import Path
from ui import C, Spinner

def provides_commands():
    """Registers the 'run' command to the console."""
    return {
        "run": {
            "handler": handle_run,
            "description": "Smart compiler & runner. Auto-detects paths for CUDA, Java, C++."
        }
    }

def _smart_path_discovery():
    """
    Scans default installation directories on Windows to find compilers 
    and adds them to the current process PATH dynamically.
    """
    if platform.system() != "Windows":
        return

    # 1. Search for CUDA (nvcc)
    if not shutil.which("nvcc"):
        base_cuda = Path(r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA")
        if base_cuda.exists():
            # Find the highest version folder (e.g., v12.4)
            versions = sorted([d for d in base_cuda.iterdir() if d.is_dir()], reverse=True)
            if versions:
                bin_path = versions[0] / "bin"
                if bin_path.exists():
                    os.environ["PATH"] += os.pathsep + str(bin_path)

    # 2. Search for MSVC (cl.exe - critical for CUDA)
    if not shutil.which("cl.exe"):
        vs_paths = [
            r"C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC",
            r"C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\VC\Tools\MSVC",
            r"C:\Program Files\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC"
        ]
        for v_path in vs_paths:
            p = Path(v_path)
            if p.exists():
                versions = sorted([d for d in p.iterdir() if d.is_dir()], reverse=True)
                if versions:
                    # Target x64 compiler binary
                    cl_bin = versions[0] / "bin" / "Hostx64" / "x64"
                    if cl_bin.exists():
                        os.environ["PATH"] += os.pathsep + str(cl_bin)
                        break

    # 3. Search for MinGW/G++ (C++)
    if not shutil.which("g++"):
        mingw_paths = [r"C:\msys64\mingw64\bin", r"C:\MinGW\bin"]
        for m in mingw_paths:
            if os.path.exists(m):
                os.environ["PATH"] += os.pathsep + m
                break

def handle_run(args, console):
    """Main execution entry point."""
    if not args:
        return f"{C.ERROR}Usage: run <filepath>{C.RESET}"

    # Auto-discover paths before execution
    _smart_path_discovery()

    # Clean path from quotes and whitespace
    raw_path = " ".join(args).strip().strip('"').strip("'")
    file_path = Path(raw_path)
    
    if not file_path.exists():
        return f"{C.ERROR}File not found: {file_path.absolute()}{C.RESET}"

    ext = file_path.suffix.lower()
    
    # Auto-Installer Checks
    if ext in [".cpp", ".c"] and not shutil.which("g++"):
        _install_tool("g++")
    elif ext == ".java" and not shutil.which("javac"):
        _install_tool("java")
    elif ext == ".cu":
        if not shutil.which("nvcc"):
            if _has_nvidia(): _install_tool("cuda")
            else: return f"{C.ERROR}No NVIDIA GPU found for CUDA.{C.RESET}"
        elif not shutil.which("cl.exe"):
            _install_tool("msvc") # Asks to install VS Build Tools
            return f"{C.WARN}Status: MSVC (cl.exe) not found. Required for CUDA.{C.RESET}"

    # Route to execution handlers
    if ext == ".py": return _run_py(file_path)
    if ext in [".cpp", ".c"]: return _run_cpp(file_path)
    if ext == ".java": return _run_java(file_path)
    if ext == ".rs": return _run_rust(file_path)
    if ext == ".cu": return _run_cuda(file_path)
    if ext == ".ino": return _run_arduino(file_path)
    
    return f"{C.ERROR}Extension {ext} not supported.{C.RESET}"

def _install_tool(tool):
    """Triggers os-specific browser downloads or terminal commands."""
    print(f"  {C.WARN}Status: {tool.upper()} missing. Launching installer...{C.RESET}")
    urls = {
        "java": "https://aws.amazon.com/corretto/",
        "g++": "https://www.msys2.org/",
        "cuda": "https://developer.nvidia.com/cuda-downloads",
        "msvc": "https://visualstudio.microsoft.com/visual-cpp-build-tools/",
        "rust": "https://rustup.rs",
        "arduino": "https://arduino.github.io/arduino-cli/latest/installation/"
    }
    if tool in urls:
        subprocess.run(f"start {urls[tool]}", shell=True)
    print(f"  {C.SUCCESS}Action: Complete installation and restart the console.{C.RESET}")

def _run_cuda(p):
    """Compiles and runs CUDA files with NVCC."""
    out = p.stem + ".exe"
    with Spinner(f"Compiling CUDA: {p.name}"):
        # shell=True ensures we use the patched PATH for nvcc and cl.exe
        res = subprocess.run(f'nvcc "{p}" -o "{out}"', shell=True, capture_output=True, text=True)
    
    if res.returncode != 0:
        return f"{C.ERROR}CUDA Error:{C.RESET}\n{res.stderr}\n{res.stdout}"
    
    print(f"  {C.PURPLE}Executing GPU Binary...{C.RESET}")
    subprocess.run([str(Path(out).absolute())], stdout=None, stderr=None)
    return f"  {C.MUTED}--- CUDA Process finished ---{C.RESET}"

def _run_py(p):
    print(f"  {C.MUTED}Running Python: {p.name}{C.RESET}")
    subprocess.run(["python", str(p)], stdout=None, stderr=None)
    return ""

def _run_java(p):
    with Spinner(f"Compiling {p.name}"):
        res = subprocess.run(["javac", str(p)], capture_output=True, text=True)
        if res.returncode != 0: return f"{C.ERROR}Java Error:{C.RESET}\n{res.stderr}"
    print(f"  {C.PURPLE}Launching JVM...{C.RESET}")
    subprocess.run(["java", p.stem], stdout=None, stderr=None)
    return f"  {C.MUTED}--- Process finished ---{C.RESET}"

def _run_cpp(p):
    out = p.stem + (".exe" if platform.system() == "Windows" else "")
    with Spinner(f"Compiling {p.name}"):
        res = subprocess.run(f'g++ "{p}" -o "{out}"', shell=True, capture_output=True, text=True)
        if res.returncode != 0: return f"{C.ERROR}C++ Error:{C.RESET}\n{res.stderr}"
    subprocess.run([f"./{out}" if platform.system() != "Windows" else out], stdout=None, stderr=None)
    return f"  {C.MUTED}--- Process finished ---{C.RESET}"

def _run_rust(p):
    with Spinner(f"Compiling Rust {p.name}"):
        res = subprocess.run(["rustc", str(p)], capture_output=True, text=True)
        if res.returncode != 0: return f"{C.ERROR}Rust Error:{C.RESET}\n{res.stderr}"
    exec_cmd = ["./" + p.stem if platform.system() != "Windows" else p.stem + ".exe"]
    subprocess.run(exec_cmd, stdout=None, stderr=None)
    return ""

def _run_arduino(p):
    board_data = subprocess.run(["arduino-cli", "board", "list"], capture_output=True, text=True).stdout
    ports = re.findall(r"(COM\d+|/dev/tty[a-zA-Z0-9]+)", board_data)
    if not ports: return f"{C.ERROR}No board detected.{C.RESET}"
    for i, port in enumerate(ports): print(f"  [{i}] {port}")
    try:
        idx = int(input(f"  {C.CYAN}Select Port Index: {C.RESET}"))
        port = ports[idx]
        fqbn = input(f"  {C.CYAN}Enter FQBN: {C.RESET}").strip()
        with Spinner("Uploading"):
            subprocess.run(["arduino-cli", "compile", "--upload", "-p", port, "--fqbn", fqbn, str(p)])
        return "Upload success."
    except: return f"{C.ERROR}Failed to process selection.{C.RESET}"

def _has_nvidia():
    """Detects NVIDIA hardware."""
    return shutil.which("nvidia-smi") is not None

def on_startup(console):
    """Greets the user on load."""
    print(f"  {C.SUCCESS}Runner-Engine v3.3 (Global-Discovery) active.{C.RESET}")