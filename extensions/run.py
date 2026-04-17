# CC-TYPE: extension
# CC-NAME: run
# CC-DESCRIPTION: Portable Runner Engine. Auto-installs standalone compilers into local data dir.

import os
import subprocess
import shutil
import platform
import zipfile
import urllib.request
from pathlib import Path
from ui import C, Spinner
from utils import feat_data_dir

def provides_commands():
    return {
        "run": {
            "handler": handle_run,
            "description": "Smart runner with auto-installing portable toolchain."
        }
    }

def _get_bin_dir():
    """Returns the local directory where all compilers are stored."""
    d = feat_data_dir() / "bin"
    d.mkdir(parents=True, exist_ok=True)
    return d

def _update_env_path():
    """Adds local bin directories to the current process PATH."""
    bin_dir = _get_bin_dir()
    # Add various subfolders to path (e.g. mingw64/bin)
    paths_to_add = [
        str(bin_dir / "mingw64" / "bin"),
        str(bin_dir / "jdk" / "bin"),
        str(bin_dir / "arduino-cli")
    ]
    for p in paths_to_add:
        if p not in os.environ["PATH"] and os.path.exists(p):
            os.environ["PATH"] = p + os.pathsep + os.environ["PATH"]

def _download_and_extract(url, target_name):
    """Downloads a zip and extracts it to the local bin dir."""
    bin_dir = _get_bin_dir()
    zip_path = bin_dir / f"{target_name}.zip"
    
    print(f"  {C.CYAN}Downloading {target_name} package...{C.RESET}")
    urllib.request.urlretrieve(url, zip_path)
    
    print(f"  {C.CYAN}Extracting files...{C.RESET}")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(bin_dir)
    
    os.remove(zip_path)
    print(f"  {C.SUCCESS}✓ {target_name} installed locally.{C.RESET}")

def _ensure_compiler(ext):
    """Checks if compiler exists locally or on system; installs locally if missing."""
    _update_env_path()
    
    if ext in [".cpp", ".c"] and not shutil.which("g++"):
        print(f"  {C.WARN}C++ Compiler missing.{C.RESET}")
        # Link to a portable MinGW build
        url = "https://github.com/niXman/mingw-builds-binaries/releases/download/13.1.0-rt_v11-rev1/x86_64-13.1.0-release-posix-seh-msvcrt-rt_v11-rev1.7z"
        print(f"  {C.ERROR}Please install MinGW manually to {feat_data_dir()}/bin/mingw64 or use system compiler.{C.RESET}")
        # Note: 7z extraction in Python is complex without extra libs, usually we prompt or use simple zips.
    
    elif ext == ".java" and not shutil.which("javac"):
        print(f"  {C.WARN}Java JDK missing. Installing portable version...{C.RESET}")
        # Example URL for a portable JDK zip
        url = "https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.2%2B13/OpenJDK21U-jdk_x64_windows_hotspot_21.0.2_13.zip"
        _download_and_extract(url, "jdk")

def handle_run(args, console):
    if not args:
        return f"{C.ERROR}Usage: run <filepath>{C.RESET}"

    raw_path = " ".join(args).strip().strip('"').strip("'")
    file_path = Path(raw_path)
    
    if not file_path.exists():
        return f"{C.ERROR}File not found: {file_path.absolute()}{C.RESET}"

    ext = file_path.suffix.lower()
    _ensure_compiler(ext)
    _update_env_path() # Refresh path after potential install

    if ext == ".py": return _run_py(file_path)
    if ext in [".cpp", ".c"]: return _run_cpp(file_path)
    if ext == ".java": return _run_java(file_path)
    if ext == ".cu": return _run_cuda(file_path)
    
    return f"{C.ERROR}Extension {ext} not supported.{C.RESET}"

def _run_java(p):
    with Spinner("Compiling Java"):
        res = subprocess.run(["javac", str(p)], capture_output=True, text=True, encoding='utf-8')
    if res.returncode != 0: return f"{C.ERROR}Java Error:{C.RESET}\n{res.stderr}"
    
    subprocess.run(["java", "-cp", str(p.parent), p.stem], stdout=None, stderr=None)
    return ""

def _run_cpp(p):
    out = p.with_suffix(".exe")
    with Spinner("Compiling C++"):
        # We use shell=True to catch the locally added MinGW in PATH
        res = subprocess.run(f'g++ "{p}" -o "{out}"', shell=True, capture_output=True, text=True, encoding='utf-8')
    if res.returncode != 0: return f"{C.ERROR}C++ Error:{C.RESET}\n{res.stderr}"
    
    subprocess.run([str(out)], stdout=None, stderr=None)
    return ""

def _run_cuda(p):
    out = p.with_suffix(".exe")
    # For CUDA, we must allow unsupported compilers to bypass the VS version check
    cmd = f'nvcc "{p}" -o "{out}" -allow-unsupported-compiler'
    with Spinner("Compiling CUDA"):
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
    
    if res.returncode != 0:
        return f"{C.ERROR}CUDA Error:{C.RESET}\n{res.stderr}\n{res.stdout}"
    
    subprocess.run([str(out.absolute())], stdout=None, stderr=None)
    return ""

def _run_py(p):
    subprocess.run(["python", str(p)], stdout=None, stderr=None)
    return ""

def on_startup(console):
    _update_env_path()
    print(f"  {C.SUCCESS}Runner-Engine v3.4 (Portable Toolchain) ready.{C.RESET}")