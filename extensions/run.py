# CC-TYPE:        extension
# CC-NAME:        run
# CC-VERSION:     E0.1
# CC-DESCRIPTION: Universal runner for Python, C/C++, Java, Rust, CUDA, Arduino, EXE, MSI.
#                 Features live output streaming, OpenCL auto-detection, and built-in help.
# CC-REQUIREMENTS: none

import os
import subprocess
import shutil
import platform
import re
import threading
import sys
from pathlib import Path
from ui import C, Spinner

VERSION = "E0.1"


# ---------------------------------------------------------------------------
# Help text
# ---------------------------------------------------------------------------

HELP_TEXT = f"""
{C.HEADING}── RUN EXTENSION v{VERSION} ──{C.RESET}

{C.CYAN}Usage:{C.RESET}
  run <filepath>         Compile (if needed) and execute a file.
  run help               Show this help.

{C.CYAN}Supported file types:{C.RESET}

  {C.SUCCESS}.py{C.RESET}      Python script          — executed directly with the system Python.
  {C.SUCCESS}.c{C.RESET}       C source               — compiled with g++, then executed.
  {C.SUCCESS}.cpp{C.RESET}     C++ source             — compiled with g++, then executed.
                         OpenCL headers/libs are detected and linked automatically.
  {C.SUCCESS}.java{C.RESET}    Java source            — compiled with javac, run with java.
                         GUI applications are fully supported.
  {C.SUCCESS}.rs{C.RESET}      Rust source            — compiled with rustc, then executed.
  {C.SUCCESS}.cu{C.RESET}      CUDA source            — compiled with nvcc (requires NVIDIA GPU).
                         cl.exe (MSVC) is located automatically via vswhere on Windows.
  {C.SUCCESS}.ino{C.RESET}     Arduino sketch         — compiled and uploaded via arduino-cli.
  {C.SUCCESS}.exe{C.RESET}     Windows executable     — executed directly.
  {C.SUCCESS}.msi{C.RESET}     Windows installer      — launched via msiexec.

{C.CYAN}Features:{C.RESET}
  • Live output streaming  — stdout/stderr printed as the program runs.
  • Missing toolchain?     — installer or download page opens automatically.
  • OpenCL projects        — -I / -L / -lOpenCL flags added without any config.
  • CUDA on Windows        — cl.exe located automatically via vswhere.
  • Paths with spaces      — wrap in quotes: run "C:\\path with spaces\\file.cpp"

{C.CYAN}Examples:{C.RESET}
  run script.py
  run main.cpp
  run "C:\\Users\\me\\Desktop\\shader.cu"
  run setup.msi
"""


# ---------------------------------------------------------------------------
# Command registration
# ---------------------------------------------------------------------------

def provides_commands():
    """Register the 'run' command with the extension host."""
    return {
        "run": {
            "handler": handle_run,
            "description": "Compile and run source files. Type 'run help' for details."
        }
    }


# ---------------------------------------------------------------------------
# Main dispatcher
# ---------------------------------------------------------------------------

def handle_run(args, console):
    """
    Resolve the file path, ensure the required toolchain is present, then
    compile and/or execute the file with live output streaming.

    Args:
        args (list[str]): Command arguments — first token is the file path,
                          or 'help' to print usage information.
        console: The active console instance (unused, required by interface).

    Returns:
        str: Final status message, or empty string if output was streamed live.
    """
    if not args or args[0].lower() == "help":
        print(HELP_TEXT)
        return ""

    raw_path = " ".join(args).strip().strip('"').strip("'")
    file_path = Path(raw_path)

    if not file_path.exists():
        return f"{C.ERROR}File not found: {file_path.absolute()}{C.RESET}"

    ext = file_path.suffix.lower()

    if not _ensure_toolchain(ext):
        return (
            f"{C.WARN}Toolchain not ready. "
            f"Follow the installer instructions and restart the console.{C.RESET}"
        )

    dispatch = {
        ".py":   _run_py,
        ".c":    _run_cpp,
        ".cpp":  _run_cpp,
        ".java": _run_java,
        ".rs":   _run_rust,
        ".cu":   _run_cuda,
        ".ino":  _run_arduino,
        ".exe":  _run_exe,
        ".msi":  _run_msi,
    }

    handler = dispatch.get(ext)
    if handler is None:
        return (
            f"{C.ERROR}Unsupported extension: '{ext}'.{C.RESET}\n"
            f"  Type 'run help' to see all supported file types."
        )

    return handler(file_path)


# ---------------------------------------------------------------------------
# Live output streaming
# ---------------------------------------------------------------------------

def _pipe_stream(stream, prefix=""):
    """Read *stream* line by line and write each line to stdout immediately."""
    for line in iter(stream.readline, ""):
        sys.stdout.write(prefix + line)
        sys.stdout.flush()
    stream.close()


def _run_live(cmd, cwd=None, env=None):
    """
    Execute *cmd* and stream stdout + stderr to the terminal in real time.

    Both streams are forwarded concurrently via threads so neither blocks
    the other — important for programs that interleave stdout and stderr.

    Args:
        cmd (list[str]): Command and arguments.
        cwd (str | None): Working directory for the subprocess.
        env (dict | None): Environment for the subprocess.

    Returns:
        int: The process return code.
    """
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=cwd,
        env=env or os.environ,
    )

    t_out = threading.Thread(target=_pipe_stream, args=(proc.stdout,), daemon=True)
    t_err = threading.Thread(target=_pipe_stream, args=(proc.stderr,), daemon=True)
    t_out.start()
    t_err.start()
    t_out.join()
    t_err.join()
    proc.wait()
    return proc.returncode


# ---------------------------------------------------------------------------
# Toolchain management
# ---------------------------------------------------------------------------

# Common MSYS2 installation prefixes on Windows.
_MSYS2_PREFIXES = [
    r"C:\msys64\ucrt64\bin",
    r"C:\msys64\mingw64\bin",
    r"C:\msys64\mingw32\bin",
    r"C:\msys2\ucrt64\bin",
    r"C:\msys2\mingw64\bin",
]


def _find_binary(name):
    """
    Locate a binary by name, checking PATH then known MSYS2 locations.

    If found in an MSYS2 prefix, that prefix is injected into os.environ["PATH"]
    so the binary is immediately usable by subsequent subprocess calls.

    Args:
        name (str): Binary name without extension (e.g. 'g++').

    Returns:
        str | None: Absolute path to the binary, or None if not found.
    """
    found = shutil.which(name)
    if found:
        return found

    if platform.system() == "Windows":
        for prefix in _MSYS2_PREFIXES:
            candidate = Path(prefix) / (name + ".exe")
            if candidate.exists():
                os.environ["PATH"] = prefix + os.pathsep + os.environ.get("PATH", "")
                return str(candidate)

    return None


def _ensure_toolchain(ext):
    """
    Verify that the toolchain for *ext* is installed; open the installer if not.

    Args:
        ext (str): File extension with leading dot (e.g. '.cpp').

    Returns:
        bool: True if the toolchain is ready, False if the user must install first.
    """
    checks = {
        ".c":    ("g++",         "g++"),
        ".cpp":  ("g++",         "g++"),
        ".java": ("javac",       "java"),
        ".rs":   ("rustc",       "rust"),
        ".cu":   ("nvcc",        "cuda"),
        ".ino":  ("arduino-cli", "arduino"),
    }

    entry = checks.get(ext)
    if entry is None:
        return True  # .py / .exe / .msi require no compilation toolchain.

    binary, tool_key = entry

    if _find_binary(binary):
        return True

    if tool_key == "cuda" and not _has_nvidia_gpu():
        return True  # Let _run_cuda surface the missing-GPU error.

    _install_tool(tool_key)
    return False


def _install_tool(tool):
    """
    Open the OS-specific installer or download page for a missing tool.

    On Windows, 'start' is a shell built-in and must be run via shell=True
    as a plain string — passing it as a list causes [WinError 2].

    Args:
        tool (str): One of: 'java', 'g++', 'rust', 'cuda', 'arduino'.
    """
    print(f"  {C.WARN}⚠{C.RESET} '{tool}' not found — launching installer…")
    is_win = platform.system() == "Windows"

    installers = {
        "java":    {True:  "start https://aws.amazon.com/corretto/",
                    False: "sudo apt install -y default-jdk"},
        "g++":     {True:  "start https://www.msys2.org/",
                    False: "sudo apt install -y build-essential"},
        "rust":    {True:  "start https://rustup.rs",
                    False: "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"},
        "cuda":    {True:  "start https://developer.nvidia.com/cuda-downloads",
                    False: "xdg-open https://developer.nvidia.com/cuda-downloads"},
        "arduino": {True:  "start https://arduino.github.io/arduino-cli/latest/installation/",
                    False: "curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh"},
    }

    cmd = installers.get(tool, {}).get(is_win)
    if cmd:
        subprocess.run(cmd, shell=True)

    print(
        f"  {C.SUCCESS}→{C.RESET} Follow the installer instructions, then restart the console.\n"
        f"  {C.MUTED}  MSYS2 tip: pacman -S mingw-w64-ucrt-x86_64-gcc{C.RESET}"
    )


# ---------------------------------------------------------------------------
# OpenCL helpers
# ---------------------------------------------------------------------------

_CUDA_VERSIONS = [
    "v12.8", "v12.7", "v12.6", "v12.5", "v12.4",
    "v12.3", "v12.2", "v12.1", "v12.0", "v11.8",
]
_CUDA_ROOT = r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA"

_OPENCL_INCLUDE_DIRS = (
    [rf"{_CUDA_ROOT}\{v}\include"  for v in _CUDA_VERSIONS] +
    [r"C:\Program Files (x86)\Intel\OpenCL SDK\include",
     r"C:\Program Files\Intel\OpenCL SDK\include",
     r"C:\Program Files\OCL_SDK_Light\include"]
)
_OPENCL_LIB_DIRS = (
    [rf"{_CUDA_ROOT}\{v}\lib\x64"  for v in _CUDA_VERSIONS] +
    [r"C:\Program Files (x86)\Intel\OpenCL SDK\lib\x64",
     r"C:\Program Files\Intel\OpenCL SDK\lib\x64",
     r"C:\Program Files\OCL_SDK_Light\lib\x86_64"]
)


def _find_opencl_flags():
    """
    Scan known SDK locations for OpenCL headers and libraries.

    Returns:
        tuple[list, list] | None: (include_flags, lib_flags) or None if not found.
    """
    inc_flag = lib_flag = None

    for d in _OPENCL_INCLUDE_DIRS:
        if (Path(d) / "CL" / "cl.h").exists():
            inc_flag = f"-I{d}"
            break

    for d in _OPENCL_LIB_DIRS:
        if (Path(d) / "OpenCL.lib").exists() or (Path(d) / "libOpenCL.a").exists():
            lib_flag = f"-L{d}"
            break

    return ([inc_flag], [lib_flag, "-lOpenCL"]) if inc_flag and lib_flag else None


def _is_opencl_source(path):
    """Return True if the source file contains an OpenCL include directive."""
    try:
        return "CL/cl" in path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Language runners
# ---------------------------------------------------------------------------

def _run_py(path):
    """Execute a Python script with live output streaming."""
    print(f"  {C.MUTED}Running Python: {path.name}{C.RESET}\n")
    _run_live(["python", str(path)])
    return f"  {C.MUTED}--- Process finished ---{C.RESET}"


def _run_cpp(path):
    """
    Compile a C/C++ file with g++ and stream execution output live.
    OpenCL includes and linker flags are injected automatically when needed.
    """
    binary = path.parent / (path.stem + (".exe" if platform.system() == "Windows" else ""))
    extra_flags = []

    if _is_opencl_source(path):
        opencl = _find_opencl_flags()
        if opencl is None:
            return (
                f"{C.ERROR}OpenCL header 'CL/cl.h' not found.\n"
                f"  Download CUDA Toolkit: https://developer.nvidia.com/cuda-downloads\n"
                f"  Or lightweight OCL-SDK: https://github.com/GPUOpen-LibrariesAndSDKs/OCL-SDK/releases{C.RESET}"
            )
        inc_flags, lib_flags = opencl
        extra_flags = inc_flags + lib_flags
        print(f"  {C.MUTED}OpenCL SDK detected — flags added automatically.{C.RESET}")

    with Spinner(f"Compiling {path.name}"):
        result = subprocess.run(
            ["g++", str(path), "-o", str(binary)] + extra_flags,
            capture_output=True, text=True
        )

    if result.returncode != 0:
        return f"{C.ERROR}Compilation failed:\n{result.stderr}{C.RESET}"

    print(f"\n  {C.MUTED}Running {binary.name}…{C.RESET}\n")
    _run_live([str(binary.absolute())])
    return f"  {C.MUTED}--- Process finished ---{C.RESET}"


def _run_java(path):
    """
    Compile a Java source file and stream JVM output live.
    The .class file is placed next to the source so java can always find it.
    """
    out_dir = path.parent

    with Spinner(f"Compiling {path.name}"):
        result = subprocess.run(
            ["javac", "-d", str(out_dir), str(path)],
            capture_output=True, text=True
        )

    if result.returncode != 0:
        return f"{C.ERROR}Compilation failed:\n{result.stderr}{C.RESET}"

    print(f"\n  {C.MUTED}Launching JVM…{C.RESET}\n")
    _run_live(["java", path.stem], cwd=str(out_dir))
    return f"  {C.MUTED}--- Process finished ---{C.RESET}"


def _run_rust(path):
    """Compile a Rust source file and stream execution output live."""
    with Spinner(f"Compiling {path.name}"):
        result = subprocess.run(["rustc", str(path)], capture_output=True, text=True)

    if result.returncode != 0:
        return f"{C.ERROR}Compilation failed:\n{result.stderr}{C.RESET}"

    binary = path.stem + (".exe" if platform.system() == "Windows" else "")
    exec_cmd = [binary] if platform.system() == "Windows" else [f"./{binary}"]
    print(f"\n  {C.MUTED}Running {binary}…{C.RESET}\n")
    _run_live(exec_cmd)
    return f"  {C.MUTED}--- Process finished ---{C.RESET}"


def _run_cuda(path):
    """
    Compile a CUDA source file with nvcc and stream execution output live.
    On Windows, cl.exe is located automatically via vswhere if not in PATH.
    """
    if not _has_nvidia_gpu():
        return f"{C.ERROR}No NVIDIA GPU detected — CUDA is unavailable.{C.RESET}"

    env = _prepare_cuda_env()
    if env is None:
        return (
            f"{C.ERROR}nvcc requires Microsoft's cl.exe, which was not found.\n"
            f"  Install 'Desktop development with C++' from Visual Studio Build Tools:\n"
            f"  https://aka.ms/vs/17/release/vs_BuildTools.exe{C.RESET}"
        )

    binary = path.parent / (path.stem + (".exe" if platform.system() == "Windows" else ""))

    with Spinner(f"Building CUDA binary from {path.name}"):
        result = subprocess.run(
            ["nvcc", str(path), "-o", str(binary)],
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            env=env,
        )

    compiler_output = "\n".join(filter(None, [result.stdout.strip(), result.stderr.strip()]))

    if result.returncode != 0:
        detail = compiler_output or "(nvcc produced no output)"
        return f"{C.ERROR}CUDA compilation failed:\n{detail}{C.RESET}"

    print(f"\n  {C.MUTED}Running {binary.name}…{C.RESET}\n")
    _run_live([str(binary.absolute())], env=env)
    return f"  {C.MUTED}--- Process finished ---{C.RESET}"


def _run_arduino(path):
    """Compile and upload an Arduino sketch after prompting for port and FQBN."""
    board_data = subprocess.run(
        ["arduino-cli", "board", "list"], capture_output=True, text=True
    ).stdout
    ports = re.findall(r"(COM\d+|/dev/tty[a-zA-Z0-9]+)", board_data)

    if not ports:
        return f"{C.ERROR}No Arduino board detected.{C.RESET}"

    print(f"  {C.HEADING}Detected ports:{C.RESET}")
    for idx, port in enumerate(ports):
        print(f"    [{idx}] {port}")

    try:
        selection = int(input(f"  {C.CYAN}Select port index: {C.RESET}"))
        selected_port = ports[selection]
    except (ValueError, IndexError):
        return f"{C.ERROR}Invalid selection.{C.RESET}"

    fqbn = input(f"  {C.CYAN}Enter FQBN (e.g. arduino:avr:uno): {C.RESET}").strip()

    with Spinner("Compiling and uploading"):
        subprocess.run([
            "arduino-cli", "compile", "--upload",
            "-p", selected_port, "--fqbn", fqbn, str(path)
        ])

    return "  Upload complete."


def _run_exe(path):
    """Execute a Windows .exe binary directly with live output streaming."""
    if platform.system() != "Windows":
        return f"{C.ERROR}.exe files can only be run on Windows.{C.RESET}"
    print(f"  {C.MUTED}Launching {path.name}…{C.RESET}\n")
    _run_live([str(path.absolute())])
    return f"  {C.MUTED}--- Process finished ---{C.RESET}"


def _run_msi(path):
    """
    Launch a Windows .msi installer via msiexec with the full installer UI.

    msiexec is called without /quiet so the user sees every installation step.
    """
    if platform.system() != "Windows":
        return f"{C.ERROR}.msi files can only be run on Windows.{C.RESET}"
    print(f"  {C.MUTED}Launching installer: {path.name}…{C.RESET}")
    subprocess.run(["msiexec", "/i", str(path.absolute())])
    return f"  {C.MUTED}--- Installer closed ---{C.RESET}"


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _has_nvidia_gpu():
    """Return True if nvidia-smi is present, indicating an NVIDIA GPU."""
    return shutil.which("nvidia-smi") is not None


def _prepare_cuda_env():
    """
    Return an environment dict with cl.exe in PATH for nvcc on Windows.

    On non-Windows systems the current environment is returned unchanged.
    On Windows, vswhere is used to locate the latest MSVC toolchain if
    cl.exe is not already in PATH.

    Returns:
        dict | None: Updated os.environ copy, or None if cl.exe cannot be found.
    """
    env = os.environ.copy()

    if platform.system() != "Windows":
        return env

    if shutil.which("cl.exe"):
        return env

    vswhere = r"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
    if not Path(vswhere).exists():
        return None

    try:
        result = subprocess.run(
            [vswhere, "-latest", "-products", "*",
             "-requires", "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
             "-property", "installationPath"],
            capture_output=True, text=True
        )
        vs_root = result.stdout.strip()
        if not vs_root:
            return None

        vc_tools_root = Path(vs_root) / "VC" / "Tools" / "MSVC"
        for ver_dir in sorted(vc_tools_root.iterdir(), reverse=True):
            cl = ver_dir / "bin" / "HostX64" / "x64" / "cl.exe"
            if cl.exists():
                env["PATH"] = str(cl.parent) + os.pathsep + env.get("PATH", "")
                return env
    except Exception:
        pass

    return None


# ---------------------------------------------------------------------------
# Lifecycle hooks
# ---------------------------------------------------------------------------

def on_startup(console):
    """Print a confirmation message when this extension is loaded."""
    print(f"  {C.SUCCESS}✓{C.RESET} Run Extension v{VERSION} active.")
