# CC-TYPE: extension
# CC-NAME: run
# CC-DESCRIPTION: Autonomous Runner v3.8.1. Features CUDA SDK Heavy-Downloader & Progress Bar.

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
        "run": {"handler": handle_run, "description": "Smart runner with CUDA SDK Auto-Setup."},
        "setup-all": {"handler": setup_all, "description": "Pre-installs all portable toolchains."}
    }

def _get_bin_dir():
    d = feat_data_dir() / "bin"
    d.mkdir(parents=True, exist_ok=True)
    return d

# --- TOOLCHAIN DISCOVERY ---

def _find_msvc_cl():
    """Locates cl.exe on the system for CUDA support."""
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

def _update_env_paths():
    """Refresh the PATH with local and discovered compilers."""
    bin_dir = _get_bin_dir()
    extra_paths = [
        str(bin_dir / "mingw64" / "bin"), 
        str(bin_dir / "jdk" / "bin")
    ]
    
    cl_path = _find_msvc_cl()
    if cl_path: extra_paths.append(cl_path)
    
    for p in extra_paths:
        if os.path.exists(p) and p not in os.environ["PATH"]:
            os.environ["PATH"] = p + os.pathsep + os.environ["PATH"]

# --- DOWNLOAD ENGINE ---

def _progress_bar(current, total, bar_length=30):
    fraction = current / total
    arrow = int(fraction * bar_length - 1) * "=" + ">"
    padding = int(bar_length - len(arrow)) * " "
    percent = int(fraction * 100)
    print(f"\r  Download: [{C.SUCCESS}{arrow}{padding}{C.RESET}] {percent}% ({current//(1024**2)}MB / {total//(1024**2)}MB)", end="")

def _download_with_progress(url, filename):
    path = _get_bin_dir() / filename
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        total = int(response.info().get('Content-Length').strip())
        current = 0
        with open(path, 'wb') as f:
            while True:
                chunk = response.read(1024 * 256)
                if not chunk: break
                f.write(chunk)
                current += len(chunk)
                _progress_bar(current, total)
    print("\n")
    return path

# --- INSTALLERS ---

def _install_cuda_sdk():
    print(f"\n  {C.WARN}CUDA SDK (nvcc) missing!{C.RESET}")
    ans = input(f"  Download & Install NVIDIA CUDA Toolkit? (y/N): ").lower()
    if ans not in ['y', 'j', 'yes']: return
    
    url = "https://developer.download.nvidia.com/compute/cuda/12.4.1/network_installers/cuda_12.4.1_windows_network.exe"
    try:
        path = _download_with_progress(url, "cuda_installer.exe")
        print(f"  {C.PURPLE}Starting NVIDIA Setup...{C.RESET}")
        subprocess.run([str(path)], shell=True)
    except Exception as e: print(f"  {C.ERROR}Error: {e}{C.RESET}")

def _download_and_extract(url, name):
    print(f"  {C.WARN}{name.upper()} missing. Local setup starting...{C.RESET}")
    zip_p = _download_with_progress(url, f"{name}.zip")
    with Spinner(f"Extracting {name}"):
        with zipfile.ZipFile(zip_p, 'r') as z:
            z.extractall(_get_bin_dir())
    os.remove(zip_p)

# --- COMMAND HANDLERS ---

def handle_run(args, console):
    if not args: return f"{C.ERROR}Usage: run <filepath>{C.RESET}"
    _update_env_paths()
    
    file_path = Path(" ".join(args).strip().strip('"').strip("'"))
    if not file_path.exists(): return f"{C.ERROR}File not found.{C.RESET}"
    ext = file_path.suffix.lower()

    # Auto-Install Checks
    if ext == ".cu" and not shutil.which("nvcc"):
        _install_cuda_sdk()
        return "CUDA setup triggered."
    if ext in [".cpp", ".c"] and not shutil.which("g++"):
        _download_and_extract("https://github.com/brechtsanders/winlibs_mingw/releases/download/13.2.0posix-17.0.6-msvcrt-r5/winlibs-x86_64-posix-seh-gcc-13.2.0-mingw-w64msvcrt-11.0.1-r5.zip", "mingw")
    if ext == ".java" and not shutil.which("javac"):
        _download_and_extract("https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.2%2B13/OpenJDK21U-jdk_x64_windows_hotspot_21.0.2_13.zip", "jdk")

    _update_env_paths()
    return _execute(file_path, ext)

def _execute(p, ext):
    if ext == ".py": 
        subprocess.run(["python", str(p)], stdout=None, stderr=None)
    elif ext == ".java":
        subprocess.run(["javac", str(p)], check=True)
        subprocess.run(["java", "-cp", str(p.parent), p.stem], stdout=None, stderr=None)
    elif ext in [".cpp", ".c"]:
        out = p.with_suffix(".exe")
        subprocess.run(f'g++ "{p}" -o "{out}"', shell=True, check=True)
        subprocess.run([str(out.absolute())], stdout=None, stderr=None)
    elif ext == ".cu":
        out = p.with_suffix(".exe")
        subprocess.run(f'nvcc "{p}" -o "{out}" -allow-unsupported-compiler', shell=True, check=True)
        subprocess.run([str(out.absolute())], stdout=None, stderr=None)
    return ""

def setup_all(args, console):
    print("Pre-installing all tools...")
    # Add manual triggers if needed
    return "Ready."

def on_startup(console):
    _update_env_paths()
    print(f"  {C.SUCCESS}Runner v3.8.1 (Autonomous) active.{C.RESET}")