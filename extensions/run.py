# CC-TYPE: extension
# CC-NAME: run
# CC-DESCRIPTION: Autonomous Runner v3.8.7. Fixes Unicode crashes and forces x64 VCVARS.

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
                # Switched to vcvarsall.bat (more reliable)
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

def handle_run(args, console):
    if not args: return f"{C.ERROR}Usage: run <filepath>{C.RESET}"
    _update_env_paths_internal()
    
    file_path = Path(" ".join(args).strip().strip('"').strip("'"))
    if not file_path.exists(): return f"{C.ERROR}File not found.{C.RESET}"
    ext = file_path.suffix.lower()

    if ext in [".cpp", ".c", ".cl"] and not shutil.which("g++"):
        url = "https://github.com/skeeto/w64devkit/releases/download/v1.19.0/w64devkit-1.19.0.zip"
        _download_and_extract(url, "w64devkit")
        
    _update_env_paths_internal()
    return _execute(file_path, ext)

def _download_and_extract(url, name):
    print(f"  {C.WARN}{name.upper()} setup starting. This happens only once!{C.RESET}")
    zip_p = _download_with_progress(url, f"{name}.zip")
    if zip_p:
        with Spinner(f"Extracting {name}"):
            with zipfile.ZipFile(zip_p, 'r') as z:
                z.extractall(_get_bin_dir())
        os.remove(zip_p)

def _execute(p, ext):
    if ext == ".py": 
        subprocess.run(["python", str(p)], stdout=None, stderr=None)
    
    elif ext == ".java":
        subprocess.run(["javac", str(p)], check=True)
        subprocess.run(["java", "-cp", str(p.parent), p.stem], stdout=None, stderr=None)
    
    elif ext in [".cpp", ".c"]:
        out = p.with_suffix(".exe")
        with Spinner("Compiling C++"):
            res = subprocess.run(f'g++ "{p}" -o "{out}" -lOpenCL', shell=True, capture_output=True, text=True, errors='replace')
        if res.returncode != 0: return f"{C.ERROR}C++ Error:{C.RESET}\n{res.stderr}"
        subprocess.run([str(out.absolute())], stdout=None, stderr=None)
    
    elif ext == ".cu":
        out = p.with_suffix(".exe")
        vcvars = _get_vcvars_path()
        bat_file = p.with_suffix(".build.bat")
        
        try:
            with open(bat_file, "w", encoding="utf-8") as f:
                f.write("@echo off\n")
                f.write("chcp 65001 >nul\n") # Force Windows CMD to use UTF-8 (Fixes the crash)
                if vcvars:
                    f.write(f'call "{vcvars}" x64 >nul\n') # Safely load 64-bit environment
                f.write(f'nvcc -m64 "{p}" -o "{out}" -allow-unsupported-compiler\n')
            
            with Spinner("Compiling CUDA (GPU)"):
                # Use utf-8 encoding and replace errors so python never crashes again
                res = subprocess.run([str(bat_file)], capture_output=True, text=True, encoding='utf-8', errors='replace')
            
            if res.returncode != 0:
                return f"{C.ERROR}CUDA Compilation Error:{C.RESET}\n{res.stderr}\n{res.stdout}"
        
        finally:
            if bat_file.exists(): bat_file.unlink()

        subprocess.run([str(out.absolute())], stdout=None, stderr=None)
    
    return ""

def on_startup(console):
    _update_env_paths_internal()
    print(f"  {C.SUCCESS}Runner v3.8.7 (Encoding & x64 Fix) ready.{C.RESET}")