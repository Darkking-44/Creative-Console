# CC-TYPE: extension
# CC-NAME: run
# CC-DESCRIPTION: Autonomous Runner v3.8.8. Fixes NVCC German Regex Bug & Auto-Downloads OpenCL Headers.

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
    return {"run": {"handler": handle_run, "description": "Smart runner with autonomous toolchains."}}

def _get_bin_dir():
    d = feat_data_dir() / "bin"
    if not d.exists(): d.mkdir(parents=True, exist_ok=True)
    return d

def _get_vcvars_path():
    if platform.system() != "Windows": return None
    vswhere = r"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
    if os.path.exists(vswhere):
        try:
            res = subprocess.run([vswhere, "-latest", "-property", "installationPath"], capture_output=True, text=True, errors='replace')
            install_path = res.stdout.strip()
            if install_path:
                vcvars = Path(install_path) / "VC" / "Auxiliary" / "Build" / "vcvarsall.bat"
                if vcvars.exists(): return str(vcvars)
        except: pass
    return None

def _update_env_paths_internal():
    bin_dir = _get_bin_dir()
    extra_paths = [
        str(bin_dir / "w64devkit" / "bin"),
        str(bin_dir / "jdk" / "bin")
    ]
    for p in extra_paths:
        if os.path.exists(p) and p not in os.environ["PATH"]:
            os.environ["PATH"] = p + os.pathsep + os.environ["PATH"]

def _download_with_progress(url, filename):
    path = _get_bin_dir() / filename
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req) as resp:
            total = int(resp.info().get('Content-Length').strip())
            current = 0
            with open(path, 'wb') as f:
                while chunk := resp.read(1024 * 512):
                    f.write(chunk)
                    current += len(chunk)
                    print(f"\r  Downloading: {int(current/total*100)}%", end="")
        print("\n")
        return path
    except Exception as e:
        print(f"\n  {C.ERROR}Download failed: {e}{C.RESET}")
        return None

def _ensure_opencl_headers():
    """Downloads official Khronos OpenCL headers for portable C++ compilation."""
    h_dir = _get_bin_dir() / "OpenCL-Headers-main"
    if not h_dir.exists():
        print(f"  {C.WARN}OpenCL Headers missing. Downloading Khronos SDK...{C.RESET}")
        url = "https://github.com/KhronosGroup/OpenCL-Headers/archive/refs/heads/main.zip"
        zip_p = _download_with_progress(url, "cl_headers.zip")
        if zip_p:
            with Spinner("Extracting OpenCL Headers"):
                with zipfile.ZipFile(zip_p, 'r') as z:
                    z.extractall(_get_bin_dir())
            os.remove(zip_p)
    return str(h_dir)

def handle_run(args, console):
    if not args: return f"{C.ERROR}Usage: run <filepath>{C.RESET}"
    _update_env_paths_internal()
    
    file_path = Path(" ".join(args).strip().strip('"').strip("'"))
    if not file_path.exists(): return f"{C.ERROR}File not found.{C.RESET}"
    ext = file_path.suffix.lower()

    if ext in [".cpp", ".c", ".cl"]:
        if not shutil.which("g++"):
            url = "https://github.com/skeeto/w64devkit/releases/download/v1.19.0/w64devkit-1.19.0.zip"
            print(f"  {C.WARN}W64DEVKIT setup starting. This happens only once!{C.RESET}")
            zip_p = _download_with_progress(url, "w64devkit.zip")
            if zip_p:
                with Spinner("Extracting Toolchain"):
                    with zipfile.ZipFile(zip_p, 'r') as z:
                        z.extractall(_get_bin_dir())
                os.remove(zip_p)
        _ensure_opencl_headers() # Always ensure headers exist for C++
        
    _update_env_paths_internal()
    return _execute(file_path, ext)

def _execute(p, ext):
    if ext == ".py": 
        subprocess.run(["python", str(p)], stdout=None, stderr=None)
    
    elif ext == ".java":
        subprocess.run(["javac", str(p)], check=True)
        subprocess.run(["java", "-cp", str(p.parent), p.stem], stdout=None, stderr=None)
    
    elif ext in [".cpp", ".c"]:
        out = p.with_suffix(".exe")
        headers = _ensure_opencl_headers()
        opencl_dll = r"C:\Windows\System32\OpenCL.dll"
        
        cmd = f'g++ "{p}" -o "{out}" -I"{headers}"'
        if os.path.exists(opencl_dll):
            cmd += f' "{opencl_dll}"' # Direct linking to system OpenCL driver
            
        with Spinner("Compiling C++ / OpenCL"):
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, errors='replace')
        if res.returncode != 0: return f"{C.ERROR}C++ Error:{C.RESET}\n{res.stderr}"
        subprocess.run([str(out.absolute())], stdout=None, stderr=None)
    
    elif ext == ".cu":
        out = p.with_suffix(".exe")
        vcvars = _get_vcvars_path()
        bat_file = p.with_suffix(".build.bat")
        
        try:
            with open(bat_file, "w", encoding="utf-8") as f:
                f.write("@echo off\n")
                f.write("set VSLANG=1033\n") # FIX: Force MSVC to English so NVCC understands "for x64"
                f.write("chcp 65001 >nul\n")
                if vcvars:
                    f.write(f'call "{vcvars}" x64 >nul 2>&1\n')
                f.write(f'nvcc -m64 "{p}" -o "{out}" -allow-unsupported-compiler\n')
            
            with Spinner("Compiling CUDA (GPU)"):
                res = subprocess.run([str(bat_file)], capture_output=True, text=True, encoding='utf-8', errors='replace')
            
            if res.returncode != 0:
                return f"{C.ERROR}CUDA Compilation Error:{C.RESET}\n{res.stderr}\n{res.stdout}"
        
        finally:
            if bat_file.exists(): bat_file.unlink()

        subprocess.run([str(out.absolute())], stdout=None, stderr=None)
    
    return ""

def on_startup(console):
    _update_env_paths_internal()
    print(f"  {C.SUCCESS}Runner v3.8.8 (The Masterpiece) ready.{C.RESET}")