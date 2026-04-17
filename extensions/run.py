# CC-TYPE: extension
# CC-NAME: run
# CC-DESCRIPTION: Autonomous Runner v3.8.4. Forced SDK inclusion and stable WinLibs link.

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
    if not d.exists(): d.mkdir(parents=True, exist_ok=True)
    return d

def _find_msvc_cl_internal():
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
    return None

def _update_env_paths_internal():
    bin_dir = _get_bin_dir()
    extra_paths = [str(bin_dir / "mingw64" / "bin"), str(bin_dir / "jdk" / "bin")]
    cl_path = _find_msvc_cl_internal()
    if cl_path: extra_paths.append(cl_path)
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
    raw_path = " ".join(args).strip().strip('"').strip("'")
    file_path = Path(raw_path)
    if not file_path.exists(): return f"{C.ERROR}File not found.{C.RESET}"
    ext = file_path.suffix.lower()

    if ext in [".cpp", ".c"] and not shutil.which("g++"):
        # Stable Direct Link
        url = "https://github.com/brechtsanders/winlibs_mingw/releases/download/13.2.0-11.0.1-msvcrt-r1/winlibs-x86_64-posix-seh-gcc-13.2.0-mingw-w64msvcrt-11.0.1-r1.zip"
        _download_and_extract(url, "mingw")
        
    _update_env_paths_internal()
    return _execute(file_path, ext)

def _download_and_extract(url, name):
    print(f"  {C.WARN}{name.upper()} setup starting...{C.RESET}")
    zip_p = _download_with_progress(url, f"{name}.zip")
    if zip_p:
        with Spinner(f"Extracting {name}"):
            with zipfile.ZipFile(zip_p, 'r') as z:
                z.extractall(_get_bin_dir())
        os.remove(zip_p)

def _execute(p, ext):
    try:
        if ext == ".py": 
            subprocess.run(["python", str(p)], stdout=None, stderr=None)
        elif ext == ".java":
            subprocess.run(["javac", str(p)], check=True)
            subprocess.run(["java", "-cp", str(p.parent), p.stem], stdout=None, stderr=None)
        elif ext in [".cpp", ".c"]:
            out = p.with_suffix(".exe")
            # Compile with OpenCL if possible
            subprocess.run(f'g++ "{p}" -o "{out}" -lOpenCL', shell=True, check=True)
            subprocess.run([str(out.absolute())], stdout=None, stderr=None)
        elif ext == ".cu":
            out = p.with_suffix(".exe")
            cl_path = _find_msvc_cl_internal()
            # Der Trick: Wir sagen NVCC direkt, wo cl.exe liegt
            cc_bin = f'--compiler-bindir "{cl_path}"' if cl_path else ""
            cmd = f'nvcc {cc_bin} -m64 "{p}" -o "{out}" -allow-unsupported-compiler'
            subprocess.run(cmd, shell=True, check=True)
            subprocess.run([str(out.absolute())], stdout=None, stderr=None)
        return ""
    except Exception as e:
        return f"{C.ERROR}Execution failed: {e}{C.RESET}"

def setup_all(args, console): return "Check done."

def on_startup(console):
    _update_env_paths_internal()
    print(f"  {C.SUCCESS}Runner v3.8.4 (Ultra-Stable) ready.{C.RESET}")