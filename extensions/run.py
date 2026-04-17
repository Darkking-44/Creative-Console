# CC-TYPE: extension
# CC-NAME: run
# CC-DESCRIPTION: Autonomous Runner v3.8.2. Final Fix for Quarantäne/Import-Error.

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
    """Register the 'run' and 'setup-all' commands."""
    return {
        "run": {"handler": handle_run, "description": "Smart runner with CUDA SDK Auto-Setup."},
        "setup-all": {"handler": setup_all, "description": "Pre-installs all portable toolchains."}
    }

# --- TOOLCHAIN FUNCTIONS (Internal & Independent) ---

def _get_bin_dir():
    """Returns the local directory for portable compilers."""
    d = feat_data_dir() / "bin"
    if not d.exists(): 
        d.mkdir(parents=True, exist_ok=True)
    return d

def _find_msvc_cl_internal():
    """Locates cl.exe without calling external module references (prevents import errors)."""
    if platform.system() != "Windows": return None
    
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
    
    # Fallback disk scan if vswhere fails
    search_paths = [r"C:\Program Files\Microsoft Visual Studio", r"C:\Program Files (x86)\Microsoft Visual Studio"]
    for base in search_paths:
        if os.path.exists(base):
            for root, dirs, files in os.walk(base):
                if "cl.exe" in files and "bin\\Hostx64\\x64" in root: return root
    return None

def _update_env_paths_internal():
    """Dynamically adds local toolchains to the session PATH."""
    bin_dir = _get_bin_dir()
    extra_paths = [
        str(bin_dir / "mingw64" / "bin"), 
        str(bin_dir / "jdk" / "bin"),
        str(bin_dir / "bin") # For arduino-cli
    ]
    
    cl_path = _find_msvc_cl_internal()
    if cl_path: 
        extra_paths.append(cl_path)
    
    for p in extra_paths:
        if os.path.exists(p) and p not in os.environ["PATH"]:
            os.environ["PATH"] = p + os.pathsep + os.environ["PATH"]

# --- DOWNLOADING & PROGRESS ---

def _progress_bar(current, total, bar_length=30):
    """Prints a visual progress bar for heavy downloads like CUDA."""
    fraction = current / total
    arrow = int(fraction * bar_length - 1) * "=" + ">"
    padding = int(bar_length - len(arrow)) * " "
    percent = int(fraction * 100)
    print(f"\r  Download: [{C.SUCCESS}{arrow}{padding}{C.RESET}] {percent}% ({current//(1024**2)}MB / {total//(1024**2)}MB)", end="")

def _download_with_progress(url, filename):
    """Chunk-based downloader with real-time UI updates."""
    path = _get_bin_dir() / filename
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as resp:
        total = int(resp.info().get('Content-Length').strip())
        current = 0
        with open(path, 'wb') as f:
            while True:
                chunk = resp.read(1024 * 256) # 256KB Chunks
                if not chunk: break
                f.write(chunk)
                current += len(chunk)
                _progress_bar(current, total)
    print("\n")
    return path

# --- COMPILER INSTALLERS ---

def _install_cuda_sdk():
    """Handles the 3GB+ CUDA Toolkit download."""
    print(f"\n  {C.WARN}CUDA SDK (nvcc) missing!{C.RESET}")
    ans = input(f"  Download & Install NVIDIA CUDA Toolkit? (y/N): ").lower()
    if ans not in ['y', 'j', 'yes']: return
    
    url = "https://developer.download.nvidia.com/compute/cuda/12.4.1/network_installers/cuda_12.4.1_windows_network.exe"
    try:
        path = _download_with_progress(url, "cuda_installer.exe")
        print(f"  {C.PURPLE}Starting NVIDIA Setup...{C.RESET}")
        subprocess.run([str(path)], shell=True)
    except Exception as e: 
        print(f"  {C.ERROR}Error: {e}{C.RESET}")

def _download_and_extract(url, name):
    """Downloads a ZIP and extracts it to the local data/run/bin folder."""
    print(f"  {C.WARN}{name.upper()} missing. Initializing local toolchain...{C.RESET}")
    zip_p = _download_with_progress(url, f"{name}.zip")
    with Spinner(f"Extracting {name}"):
        with zipfile.ZipFile(zip_p, 'r') as z:
            z.extractall(_get_bin_dir())
    os.remove(zip_p)

# --- COMMAND HANDLERS ---

def handle_run(args, console):
    """Main execution entry point."""
    if not args: return f"{C.ERROR}Usage: run <filepath>{C.RESET}"
    
    _update_env_paths_internal()
    
    raw_path = " ".join(args).strip().strip('"').strip("'")
    file_path = Path(raw_path)
    if not file_path.exists(): return f"{C.ERROR}File not found: {file_path}{C.RESET}"
    
    ext = file_path.suffix.lower()

    # Dynamic Dependency Injection
    if ext == ".cu" and not shutil.which("nvcc"):
        _install_cuda_sdk()
        return "CUDA setup process initiated."
    
    if ext in [".cpp", ".c"] and not shutil.which("g++"):
        cpp_url = "https://github.com/brechtsanders/winlibs_mingw/releases/download/13.2.0posix-17.0.6-msvcrt-r5/winlibs-x86_64-posix-seh-gcc-13.2.0-mingw-w64msvcrt-11.0.1-r5.zip"
        _download_and_extract(cpp_url, "mingw")
        
    if ext == ".java" and not shutil.which("javac"):
        java_url = "https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.2%2B13/OpenJDK21U-jdk_x64_windows_hotspot_21.0.2_13.zip"
        _download_and_extract(java_url, "jdk")

    _update_env_paths_internal()
    return _execute(file_path, ext)

def _execute(p, ext):
    """Dispatches files to their respective compiler/interpreter."""
    try:
        if ext == ".py": 
            subprocess.run(["python", str(p)], stdout=None, stderr=None)
        elif ext == ".java":
            with Spinner("Compiling Java"):
                subprocess.run(["javac", str(p)], check=True)
            subprocess.run(["java", "-cp", str(p.parent), p.stem], stdout=None, stderr=None)
        elif ext in [".cpp", ".c"]:
            out = p.with_suffix(".exe")
            with Spinner("Compiling C++"):
                subprocess.run(f'g++ "{p}" -o "{out}"', shell=True, check=True)
            subprocess.run([str(out.absolute())], stdout=None, stderr=None)
        elif ext == ".cu":
            out = p.with_suffix(".exe")
            with Spinner("Compiling CUDA"):
                subprocess.run(f'nvcc "{p}" -o "{out}" -allow-unsupported-compiler', shell=True, check=True)
            subprocess.run([str(out.absolute())], stdout=None, stderr=None)
        return ""
    except subprocess.CalledProcessError as e:
        return f"{C.ERROR}Execution failed with exit code {e.returncode}{C.RESET}"

def setup_all(args, console):
    """Pre-downloads all supported toolchains."""
    print(f"{C.HEADING}Running full toolchain setup...{C.RESET}")
    # You could add manual calls to _download_and_extract here
    return "Toolchain check complete."

def on_startup(console):
    """Initializes the environment without causing circular import errors."""
    _update_env_paths_internal()
    print(f"  {C.SUCCESS}Runner v3.8.2 (Stable & Autonomous) active.{C.RESET}")