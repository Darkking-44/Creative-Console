# CC-TYPE: extension
# CC-NAME: run
# CC-DESCRIPTION: Autonomous Runner v3.7. Auto-installs Portable G++, JDK, and MSVC.

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
    return {"run": {"handler": handle_run, "description": "Autonomous compiler & runner."}}

def _get_bin_dir():
    d = feat_data_dir() / "bin"
    d.mkdir(parents=True, exist_ok=True)
    return d

def _update_env():
    """Injects all portable toolchains into the current session PATH."""
    bin_dir = _get_bin_dir()
    # Path to the extracted MinGW and JDK
    extra_paths = [
        str(bin_dir / "mingw64" / "bin"),
        str(bin_dir / "jdk" / "bin"),
        str(bin_dir / "bin") # for arduino-cli
    ]
    
    # Also look for MSVC for CUDA
    from run import _find_msvc_cl # Self-reference or move function
    cl = _find_msvc_cl()
    if cl: extra_paths.append(cl)

    for p in extra_paths:
        if p not in os.environ["PATH"] and os.path.exists(p):
            os.environ["PATH"] = p + os.pathsep + os.environ["PATH"]

def _auto_install_cpp():
    """Downloads a portable MinGW-w64 build (WinLibs) if g++ is missing."""
    bin_dir = _get_bin_dir()
    # Direct link to a portable ZIP of GCC 13.2.0 (WinLibs)
    url = "https://github.com/brechtsanders/winlibs_mingw/releases/download/13.2.0posix-17.0.6-msvcrt-r5/winlibs-x86_64-posix-seh-gcc-13.2.0-mingw-w64msvcrt-11.0.1-r5.zip"
    zip_path = bin_dir / "mingw.zip"
    
    print(f"  {C.WARN}Status: C++ Compiler missing. Downloading portable MinGW...{C.RESET}")
    with Spinner("Downloading Toolchain (approx. 140MB)"):
        urllib.request.urlretrieve(url, zip_path)
    
    with Spinner("Extracting Compiler"):
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(bin_dir)
    
    os.remove(zip_path)
    print(f"  {C.SUCCESS}✓ C++ Compiler installed locally in {bin_dir}{C.RESET}")

def handle_run(args, console):
    if not args: return f"{C.ERROR}Usage: run <filepath>{C.RESET}"
    
    _update_env()
    raw_path = " ".join(args).strip().strip('"').strip("'")
    file_path = Path(raw_path)
    if not file_path.exists(): return f"{C.ERROR}File not found.{C.RESET}"
    ext = file_path.suffix.lower()

    # --- AUTO-INSTALL LOGIC ---
    if ext in [".cpp", ".c", ".cl"] and not shutil.which("g++"):
        _auto_install_cpp()
        _update_env()

    if ext == ".java" and not shutil.which("javac"):
        print(f"  {C.WARN}Status: Java JDK missing. Installing...{C.RESET}")
        url = "https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.2%2B13/OpenJDK21U-jdk_x64_windows_hotspot_21.0.2_13.zip"
        _portable_download(url, "jdk")
        _update_env()

    # --- ROUTING ---
    if ext == ".py": return _run_py(file_path)
    if ext == ".java": return _run_java(file_path)
    if ext in [".cpp", ".c", ".cl"]: return _run_cpp(file_path) # Handles .cl too
    if ext == ".cu": return _run_cuda(file_path)
    
    return f"{C.ERROR}Extension {ext} not supported.{C.RESET}"

# --- HELPER FUNCTIONS ---

def _portable_download(url, name):
    bin_dir = _get_bin_dir()
    zip_p = bin_dir / f"{name}.zip"
    with Spinner(f"Downloading {name}"):
        urllib.request.urlretrieve(url, zip_p)
    with zipfile.ZipFile(zip_p, 'r') as z:
        z.extractall(bin_dir)
    os.remove(zip_p)

def _find_msvc_cl():
    vswhere = r"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
    if os.path.exists(vswhere):
        try:
            res = subprocess.run([vswhere, "-latest", "-property", "installationPath"], capture_output=True, text=True)
            install_path = res.stdout.strip()
            if install_path:
                msvc_base = Path(install_path) / "VC/Tools/MSVC"
                if msvc_base.exists():
                    versions = sorted([d for d in msvc_base.iterdir() if d.is_dir()], reverse=True)
                    if versions:
                        cl_bin = versions[0] / "bin/Hostx64/x64"
                        if cl_bin.exists(): return str(cl_bin)
        except: pass
    return None

# --- RUNNERS ---

def _run_cpp(p):
    out = p.with_suffix(".exe")
    # Add -lOpenCL if it's an OpenCL host or file
    flags = "-lOpenCL" if p.suffix == ".cl" or "OpenCL" in p.name else ""
    with Spinner(f"Compiling {p.name}"):
        res = subprocess.run(f'g++ "{p}" -o "{out}" {flags}', shell=True, capture_output=True, text=True, encoding='utf-8')
    if res.returncode != 0: return f"{C.ERROR}Compile Error:{C.RESET}\n{res.stderr}"
    
    subprocess.run([str(out.absolute())], stdout=None, stderr=None)
    return ""

def _run_cuda(p):
    out = p.with_suffix(".exe")
    # If nvcc is still not found, we can't auto-download CUDA (it's 4GB+ and needs drivers)
    if not shutil.which("nvcc"):
        return f"{C.ERROR}CUDA Toolkit (nvcc) required. Please install NVIDIA CUDA SDK.{C.RESET}"
    
    with Spinner("Compiling CUDA"):
        res = subprocess.run(f'nvcc "{p}" -o "{out}" -allow-unsupported-compiler', shell=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if res.returncode != 0: return f"{C.ERROR}CUDA Error:{C.RESET}\n{res.stderr}"
    
    subprocess.run([str(out.absolute())], stdout=None, stderr=None)
    return ""

def _run_java(p):
    with Spinner("Compiling Java"):
        subprocess.run(["javac", str(p)], check=True)
    subprocess.run(["java", "-cp", str(p.parent), p.stem], stdout=None, stderr=None)
    return ""

def _run_py(p):
    subprocess.run(["python", str(p)], stdout=None, stderr=None)
    return ""

def on_startup(console):
    _update_env()
    print(f"  {C.SUCCESS}Runner-Engine v3.7 (Autonomous) active.{C.RESET}")