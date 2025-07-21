import sys
import subprocess
import os
import platform
import argparse
import shutil
import venv
import tempfile

def create_and_setup_venv(venv_path):
    """Create and set up a virtual environment with required packages."""
    print(f"[+] Creating virtual environment at {venv_path}...")
    # Create virtual environment
    venv.create(venv_path, with_pip=True, clear=True)

    # Determine the Python executable in the virtual environment
    if platform.system().lower() == "windows":
        python_exec = os.path.join(venv_path, "Scripts", "python.exe")
        pip_exec = os.path.join(venv_path, "Scripts", "pip.exe")
    else:
        python_exec = os.path.join(venv_path, "bin", "python")
        pip_exec = os.path.join(venv_path, "bin", "pip")

    if not os.path.isfile(python_exec):
        print(f"[X] Failed to find Python executable in virtual environment: {python_exec}")
        sys.exit(1)

    # Upgrade pip
    print("[+] Upgrading pip in virtual environment...")
    subprocess.run([python_exec, "-m", "pip", "install", "--upgrade", "pip"], check=True)

    # Install required packages
    packages = ["pyinstaller", "pexpect", "requests", "pyyaml"]
    if platform.system().lower() == "windows":
        packages.append("pywin32")

    print(f"[+] Installing packages: {', '.join(packages)}")
    subprocess.run([pip_exec, "install"] + packages, check=True)

    print(f"[✓] Virtual environment set up successfully at {venv_path}")
    return python_exec

def compile_python_script(script_name, target_os, target_arch, venv_python):
    """Compile the script using PyInstaller in the virtual environment."""
    # Validate the target OS
    if target_os.lower() not in ["windows", "linux", "darwin"]:
        print("[X] Unsupported OS type. Only 'windows', 'linux', and 'darwin' are supported.")
        sys.exit(1)

    # Validate the architecture
    if target_arch.lower() not in ["x86", "x64"]:
        print("[X] Unsupported architecture. Only 'x86' and 'x64' are supported.")
        sys.exit(1)

    # Check OS and architecture compatibility
    if target_os.lower() == "darwin" and target_arch.lower() == "x86":
        print("[X] Darwin does not support x86 architecture in this context.")
        sys.exit(1)

    # Warn about cross-compilation for Windows on non-Windows
    current_system = platform.system().lower()
    if target_os.lower() == "windows" and current_system != "windows":
        print("[!] Warning: Cross-compiling for Windows on a non-Windows system. Ensure 'pywin32' dependencies are handled correctly.")

    # Warn about Python 3.13 compatibility
    python_version = sys.version_info
    if python_version.major == 3 and python_version.minor >= 13:
        print("[!] Warning: Python 3.13 may have compatibility issues with some PyInstaller versions. Using virtual environment to mitigate.")

    # Check host architecture
    host_arch = "x64" if platform.architecture()[0] == "64bit" else "x86"
    if target_arch.lower() != host_arch.lower():
        print(f"[!] Warning: Compiling for {target_arch} on a {host_arch} system may require cross-compilation setup.")

    # Set path separator for the target OS
    path_separator = ";" if target_os.lower() == "windows" else ":"

    # Define paths to YAML files (relative to the script directory)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_yaml = os.path.join(script_dir, "config.yaml")
    detector_yaml = os.path.join(script_dir, "detector.yaml")

    # Verify YAML files exist
    for yaml_file in [config_yaml, detector_yaml]:
        if not os.path.isfile(yaml_file):
            print(f"[X] YAML file not found: {yaml_file}")
            sys.exit(1)

    # Clean previous build directories
    for dir_name in ["dist", "build"]:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"[+] Cleaned directory: {dir_name}")

    # Build the PyInstaller command
    pyinstaller_command = [
        venv_python,
        "-m",
        "PyInstaller",
        "--onefile",  # Create a single standalone executable
        "--clean",  # Clean cache to avoid build issues
        "--add-data", f"{config_yaml}{path_separator}.",  # Include config.yaml
        "--add-data", f"{detector_yaml}{path_separator}.",  # Include detector.yaml
        "--distpath", "dist",  # Output directory
        "--workpath", "build",  # Work directory
        "--specpath", "build",  # Spec file directory
        "--hidden-import", "pexpect",  # Essential for Linux/Darwin
        "--hidden-import", "requests",
        "--hidden-import", "platform",
        "--hidden-import", "os",
        "--hidden-import", "datetime",
        "--hidden-import", "subprocess",
        "--hidden-import", "yaml",  # Required for YAML loading
        "--hidden-import", "tarfile",  # Required for Linux/Darwin extraction
        "--hidden-import", "zipfile",  # Required for Windows extraction
        "--hidden-import", "base64",
        "--hidden-import", "re",
    ]

    # Add Windows-specific hidden imports
    if target_os.lower() == "windows":
        pyinstaller_command.extend([
            "--hidden-import", "win32api",
            "--hidden-import", "win32con",
        ])

    # Add the script name
    pyinstaller_command.append(script_name)

    # Print the command for debugging
    print("Running command:", " ".join(pyinstaller_command))

    try:
        # Run the PyInstaller command
        subprocess.run(pyinstaller_command, check=True)
        print(f"[✓] Compilation complete for {target_os} ({target_arch}). Executable created in the 'dist' directory.")
    except subprocess.CalledProcessError as e:
        print(f"[X] Compilation failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[X] Unexpected error during compilation: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Compile main.py for the specified operating system and architecture using a virtual environment."
    )
    parser.add_argument(
        "--operating-system",
        "-os",
        required=True,
        choices=["windows", "linux", "darwin"],
        help="Target operating system (windows, linux, or darwin)"
    )
    parser.add_argument(
        "--architecture",
        "-a",
        required=True,
        choices=["x86", "x64"],
        help="Target architecture (x86 or x64)"
    )

    # Parse arguments
    args = parser.parse_args()

    # Verify script exists
    script_name = "main.py"
    if not os.path.isfile(script_name):
        print(f"[X] Script not found: {script_name}")
        sys.exit(1)

    # Create virtual environment in a temporary directory
    venv_path = os.path.join(tempfile.gettempdir(), "vscode_compile_venv")
    python_exec = create_and_setup_venv(venv_path)

    # Compile the script
    compile_python_script(script_name, args.operating_system, args.architecture, python_exec)