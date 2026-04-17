# CC-TYPE: extension
# CC-NAME: run
# CC-DESCRIPTION: Portable Runner v3.6. Auto-installs MSVC for CUDA and portable JDK for Java.

import os
import subprocess
import shutil
import platform
import re
import zipfile
import urllib.request
from pathlib import Path
from ui import C, Spinner
from utils import feat_data_dir

def provides_commands():
    return {
        "run": {
            "handler": handle_run,
            "description": "Smart runner with auto-detecting portable toolchain and VS-Auto-Setup."
        }
    }

# --- TOOLCHAIN MANAGEMENT ---

def _get_bin_dir():
    d = feat_data_dir() / "bin"
    d.mkdir(parents=True, exist_ok=True)
    return d

def _find_msvc_cl():
    """Searches for cl.exe using vswhere or manual disk scan."""
    vswhere = r"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
    if os.path.exists(vswhere):
        try:
            res = subprocess.run([vswhere, "-latest", "-products", "*", "-requires", "Microsoft.VisualStudio.Component.VC.Tools.x86.x64", "-property", "installationPath"], capture_output=True, text=True)
            install_path = res.stdout.strip()
            if install_path:
                msvc_base = Path(install_path) / "VC/Tools/MSVC"
                if msvc_base.exists():
                    versions = sorted([d for d in msvc_base.iterdir() if d.is_dir()], reverse=True)
                    if versions:
                        cl_bin = versions[0] / "bin/Hostx64/x64"
                        if cl_bin.exists(): return str(cl_bin)
        except: pass
    
    # Fallback disk scan
    for base in [r"C:\Program Files\Microsoft Visual Studio", r"C:\Program Files (x86)\Microsoft Visual Studio"]:
        if os.path.exists(base):
            for root, dirs, files in os.walk(base):
                if "cl.exe" in files and "bin\\Hostx64\\x64" in root: return root
    return None

def _install_msvc_silently():
    """Downloads and triggers a minimal VS Build Tools installation."""
    print(f"  {C.WARN}Missing: MSVC Compiler (cl.exe) is required for CUDA.{C.RESET}")
    print(f"  {C.CYAN}Starting background installation of C++ Build Tools...{C.RESET}")
    
    url = "https://aka.ms/vs/17/release/vs_buildtools.exe"
    installer = feat_data_dir() / "vs_installer.exe"
    
    try:
        with Spinner("Downloading MSVC Installer"):
            urllib.request.urlretrieve(url, installer)
        
        print(f"  {C.PURPLE}UAC Prompt may appear. Please allow to install C++ components.{C.RESET}")
        # Minimal installation: VC Tools + Windows SDK
        cmd = f'"{installer}" --add Microsoft.VisualStudio.Workload.VCTools --add Microsoft.VisualStudio.Component.Windows11SDK.22621 --passive --norestart --wait'
        subprocess.run(cmd, shell=True)
        print(f"  {C.SUCCESS}✓ Installer started. Re-run 'run' after completion.{C.RESET}")
    except Exception as e:
        print(f"  {C.ERROR}Auto-Install failed: {e}{C.RESET}")

def _update_env():
    """Injects all discovered/portable paths into the current session."""
    bin_dir = _get_bin_dir()
    extra_paths = [
        str(bin_dir / "jdk" / "bin"),
        str(bin_dir / "mingw64" / "bin"),
        str(bin_dir / "arduino-cli")
    ]
    
    cl_path = _find_msvc_cl()
    if cl_path: extra_paths.append(cl_path)
    
    for p in extra_paths:
        if p not in os.environ["PATH"] and os.path.exists(p):
            os.environ["PATH"] = p + os.pathsep + os.environ["PATH"]

# --- EXECUTION ENGINE ---

def handle_run(args, console):
    if not args: return f"{C.ERROR}Usage: run <filepath>{C.RESET}"
    
    _update_env()
    
    raw_path = " ".join(args).strip().strip('"').strip("'")
    file_path = Path(raw_path)
    if not file_path.exists(): return f"{C.ERROR}File not found.{C.RESET}"

    ext = file_path.suffix.lower()

    # Portable Dependency Check
    if ext == ".java" and not shutil.which("javac"):
        print(f"  {C.WARN}JDK missing. Installing portable Java...{C.RESET}")
        url = "https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.2%2B13/OpenJDK21U-jdk_x64_windows_hotspot_21.0.2_13.zip"
        _portable_download(url, "jdk")
    
    if ext == ".cu":
        if not _find_msvc_cl():
            _install_msvc_silently()
            return f"{C.WARN}Status: MSVC installation triggered.{C.RESET}"
        if not shutil.which("nvcc"):
            return f"{C.ERROR}CUDA Toolkit (nvcc) not found in PATH.{C.RESET}"

    # Routing
    if ext == ".py": return _run_py(file_path)
    if ext == ".java": return _run_java(file_path)
    if ext in [".cpp", ".c"]: return _run_cpp(file_path)
    if ext == ".cu": return _run_cuda(file_path)
    
    return f"{C.ERROR}Extension {ext} not supported.{C.RESET}"

def _portable_download(url, name):
    bin_dir = _get_bin_dir()
    zip_p = bin_dir / f"{name}.zip"
    with Spinner(f"Downloading {name}"):
        urllib.request.urlretrieve(url, zip_p)
    with zipfile.ZipFile(zip_p, 'r') as z:
        z.extractall(bin_dir)
    os.remove(zip_p)
    _update_env()

# --- RUNNERS ---

def _run_cuda(p):
    out = p.with_suffix(".exe")
    # Using -allow-unsupported-compiler to bypass VS version mismatch
    cmd = f'nvcc "{p}" -o "{out}" -allow-unsupported-compiler'
    with Spinner("Compiling CUDA"):
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
    
    if res.returncode != 0:
        return f"{C.ERROR}CUDA Build Failed:{C.RESET}\n{res.stderr}"
    
    print(f"  {C.PURPLE}Running GPU Process...{C.RESET}")
    subprocess.run([str(out.absolute())], stdout=None, stderr=None)
    return ""

def _run_java(p):
    with Spinner("Compiling Java"):
        res = subprocess.run(["javac", str(p)], capture_output=True, text=True, encoding='utf-8')
    if res.returncode != 0: return f"{C.ERROR}Java Error:{C.RESET}\n{res.stderr}"
    
    print(f"  {C.PURPLE}Launching GUI/App...{C.RESET}")
    subprocess.run(["java", "-cp", str(p.parent), p.stem], stdout=None, stderr=None)
    return ""

def _run_cpp(p):
    out = p.with_suffix(".exe")
    with Spinner("Compiling C++"):
        res = subprocess.run(f'g++ "{p}" -o "{out}"', shell=True, capture_output=True, text=True, encoding='utf-8')
    if res.returncode != 0: return f"{C.ERROR}C++ Error:{C.RESET}\n{res.stderr}"
    
    subprocess.run([str(out.absolute())], stdout=None, stderr=None)
    return ""

def _run_py(p):
    subprocess.run(["python", str(p)], stdout=None, stderr=None)
    return ""

def on_startup(console):
    _update_env()
    print(f"  {C.SUCCESS}Runner-Engine v3.6 (Universal & Portable) online.{C.RESET}")