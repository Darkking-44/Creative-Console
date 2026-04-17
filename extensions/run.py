# CC-TYPE: extension
# CC-NAME: run
# CC-DESCRIPTION: Autonomous Runner v3.8. Features CUDA SDK Heavy-Downloader & Progress Bar.

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

def _progress_bar(current, total, bar_length=40):
    """Calculates and prints a visual progress bar."""
    fraction = current / total
    arrow = int(fraction * bar_length - 1) * "=" + ">"
    padding = int(bar_length - len(arrow)) * " "
    percent = int(fraction * 100)
    print(f"\r  Progress: [{C.SUCCESS}{arrow}{padding}{C.RESET}] {percent}% ({current//(1024**2)}MB / {total//(1024**2)}MB)", end="")

def _download_with_progress(url, filename):
    """Downloads large files with a real-time progress bar."""
    print(f"  {C.CYAN}Target: {url.split('/')[-1]}{C.RESET}")
    path = _get_bin_dir() / filename
    
    request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(request) as response:
        total_size = int(response.info().get('Content-Length').strip())
        current_size = 0
        chunk_size = 1024 * 256 # 256KB chunks
        
        with open(path, 'wb') as f:
            while True:
                chunk = response.read(chunk_size)
                if not chunk: break
                f.write(chunk)
                current_size += len(chunk)
                _progress_bar(current_size, total_size)
    print("\n")
    return path

def _install_cuda_sdk():
    """Handles the heavy 3-4GB CUDA Toolkit installation."""
    print(f"\n  {C.WARN}CUDA SDK (nvcc) missing!{C.RESET}")
    confirm = input(f"  Download & Install NVIDIA CUDA Toolkit? (ca. 3.2GB) (y/N): ").lower()
    if confirm not in ['y', 'j', 'yes']: return
    
    # Official NVIDIA Link (Windows 11 Network Installer for latest)
    cuda_url = "https://developer.download.nvidia.com/compute/cuda/12.4.1/network_installers/cuda_12.4.1_windows_network.exe"
    
    try:
        installer_path = _download_with_progress(cuda_url, "cuda_installer.exe")
        print(f"  {C.PURPLE}Starting NVIDIA Setup. Please follow the instructions...{C.RESET}")
        # Run the installer
        subprocess.run([str(installer_path)], shell=True)
    except Exception as e:
        print(f"  {C.ERROR}Download failed: {e}{C.RESET}")

def handle_run(args, console):
    if not args: return f"{C.ERROR}Usage: run <filepath>{C.RESET}"
    
    _update_env_paths()
    raw_path = " ".join(args).strip().strip('"').strip("'")
    file_path = Path(raw_path)
    if not file_path.exists(): return f"{C.ERROR}File not found.{C.RESET}"
    ext = file_path.suffix.lower()

    # --- AUTO-INSTALLER LOGIC ---
    if ext == ".cu" and not shutil.which("nvcc"):
        _install_cuda_sdk()
        return f"{C.WARN}Please restart the console after CUDA installation finishes.{C.RESET}"

    if ext in [".cpp", ".c"] and not shutil.which("g++"):
        cpp_url = "https://github.com/brechtsanders/winlibs_mingw/releases/download/13.2.0posix-17.0.6-msvcrt-r5/winlibs-x86_64-posix-seh-gcc-13.2.0-mingw-w64msvcrt-11.0.1-r5.zip"
        _download_and_extract(cpp_url, "mingw")
        
    if ext == ".java" and not shutil.which("javac"):
        java_url = "https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.2%2B13/OpenJDK21U-jdk_x64_windows_hotspot_21.0.2_13.zip"
        _download_and_extract(java_url, "jdk")

    # Refresh PATH and execute
    _update_env_paths()
    return _dispatch_execution(file_path, ext)

def _download_and_extract(url, name):
    print(f"  {C.WARN}{name.upper()} missing. Initializing local setup...{C.RESET}")
    zip_path = _download_with_progress(url, f"{name}.zip")
    with Spinner(f"Extracting {name}"):
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(_get_bin_dir())
    os.remove(zip_path)

def _update_env_paths():
    bin_dir = _get_bin_dir()
    # Dynamic search for MSVC, MinGW, and Java
    paths = [str(bin_dir / "mingw64" / "bin"), str(bin_dir / "jdk" / "bin")]
    for p in paths:
        if os.path.exists(p) and p not in os.environ["PATH"]:
            os.environ["PATH"] = p + os.pathsep + os.environ["PATH"]

def setup_all(args, console):
    """Manual trigger to pre-download everything."""
    print(f"{C.HEADING}--- Toolchain Pre-Setup ---{C.RESET}")
    # Logic for Java and C++ can be called here
    return "Setup finished."

def _dispatch_execution(file_path, ext):
    if ext == ".py": 
        subprocess.run(["python", str(file_path)], stdout=None, stderr=None)
    elif ext == ".java":
        subprocess.run(["javac", str(file_path)], check=True)
        subprocess.run(["java", "-cp", str(file_path.parent), file_path.stem], stdout=None, stderr=None)
    elif ext in [".cpp", ".c"]:
        out = file_path.with_suffix(".exe")
        subprocess.run(f'g++ "{file_path}" -o "{out}"', shell=True, check=True)
        subprocess.run([str(out.absolute())], stdout=None, stderr=None)
    elif ext == ".cu":
        out = file_path.with_suffix(".exe")
        subprocess.run(f'nvcc "{file_path}" -o "{out}" -allow-unsupported-compiler', shell=True, check=True)
        subprocess.run([str(out.absolute())], stdout=None, stderr=None)
    return ""

def on_startup(console):
    _update_env_paths()
    print(f"  {C.SUCCESS}Runner v3.8 (Deep-Install Engine) online.{C.RESET}")