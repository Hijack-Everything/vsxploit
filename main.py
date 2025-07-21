import os
import platform
import requests
import tarfile
import zipfile
import tempfile
import base64
import yaml
import time
import re
from datetime import datetime
import sys

# Windows-specific imports
if platform.system() == "Windows":
    import subprocess
# Linux/Darwin-specific imports
else:
    import pexpect

# === Load YAMLs ===
def load_yaml(filename):
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(__file__)
    filepath = os.path.join(base_path, filename)
    with open(filepath, 'r') as file:
        return yaml.safe_load(file)

config = load_yaml("config.yaml")
detectors = load_yaml("detector.yaml")

# === Debugging Setup ===
def debug_print(message):
    if config.get("debug", False):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[DEBUG] {timestamp} - {message}")

# === Platform-Specific VSCode CLI Path Resolution ===
def get_platform_download_path():
    system = platform.system()
    machine = platform.machine().lower()
    bitness = platform.architecture()[0]
    debug_print(f"Resolving platform download path: {system} {machine} {bitness}")

    if system == "Windows":
        return "cli-win32-x64"
    elif system == "Linux":
        if machine in ["x86_64", "amd64"]:
            return "cli-alpine-x64"
        elif machine in ["arm64", "aarch64"]:
            return "cli-alpine-arm64" if "64" in bitness else "cli-linux-armhf"
        elif machine in ["armv7l", "armv8l"]:
            return "cli-linux-armhf"
        else:
            raise Exception(f"Unsupported Linux architecture: {machine}")
    elif system == "Darwin":
        return "cli-darwin-arm64" if "arm" in machine else "cli-darwin-x64"
    else:
        raise Exception(f"Unsupported OS: {system}")

def get_paths(commit_id):
    system = platform.system()
    debug_print(f"Resolving paths for commit {commit_id} on {system}")

    if system == "Windows":
        base_dir = os.path.expanduser(config["extracted_path"])
        cli_bin = os.path.join(base_dir, config["extracted_bin"] + ".exe")
        archive_path = os.path.join(tempfile.gettempdir(), f"vscode-cli-{commit_id}.zip")
    elif system in ["Linux", "Darwin"]:
        if system == "Linux":
            base_dir = os.path.expanduser(config["extracted_path"])
        else:  # Darwin
            base_dir = os.path.expanduser("~/Library/Application Support/vscode-server")
        cli_bin = os.path.join(base_dir, config["extracted_bin"])
        archive_path = os.path.join(tempfile.gettempdir(), f"vscode-cli-{commit_id}.tar.gz")
    else:
        raise Exception("Unsupported OS for path setup")
    return base_dir, cli_bin, archive_path

# === ANSI Code Remover ===
def strip_ansi_codes(text):
    ansi_escape = re.compile(
        r'(?:\x1B[@-Z\\-_]|\x1B\[0?[0-9;]*[a-zA-Z]|\x1B\][^\a]*(\a|\x1B\\)|\x1B[P^_].*?\x1B\\)'
    )
    return ansi_escape.sub('', text)

# === VSCode CLI Downloader & Extractor ===
def download_vscode_server(commit_id, quality="stable"):
    platform_path = get_platform_download_path()
    base_dir, cli_bin, archive_path = get_paths(commit_id)

    debug_print(f"Checking if VSCode CLI exists at {cli_bin}")
    if os.path.isfile(cli_bin):
        print(f"[✓] VSCode CLI already exists at {cli_bin}")
        return cli_bin

    os.makedirs(base_dir, exist_ok=True)
    url = config["download_url_format"].format(
        commit_id=commit_id,
        platform_path=platform_path,
        quality=quality
    )

    debug_print(f"Starting download from URL: {url}")
    print(f"[+] Downloading CLI from: {url}")
    with requests.get(url, stream=True, timeout=30) as r:
        r.raise_for_status()
        with open(archive_path, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
    print(f"[+] Saved archive to {archive_path}")
    debug_print(f"File downloaded to: {archive_path}")

    debug_print(f"Starting extraction to {base_dir}")
    print(f"[+] Extracting archive to {base_dir}")
    if platform.system() == "Windows":
        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
            zip_ref.extractall(base_dir)
    else:  # Linux or Darwin
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(path=base_dir)

    if not os.path.isfile(cli_bin):
        raise FileNotFoundError(f"[!] Extraction failed: {cli_bin} not found")

    if platform.system() != "Windows":
        os.chmod(cli_bin, 0o755)
    print(f"[✓] VSCode CLI ready at {cli_bin}")
    debug_print(f"VSCode CLI extracted to: {cli_bin}")
    return cli_bin

# === GitHub Updater ===
def update_github_file(message, token, repo_owner, repo_name, branch, target_file):
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{target_file}?ref={branch}"
    debug_print(f"Fetching file from GitHub: {url}")
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"[!] GitHub GET failed: {response.status_code}")
        return

    sha = response.json()["sha"]
    old_content = base64.b64decode(response.json()["content"]).decode(errors='ignore')
    new_content = old_content + f"\n{message.strip()}\n"
    b64_content = base64.b64encode(new_content.encode()).decode()

    data = {
        "message": f"Auto-detected: {message.strip()}",
        "content": b64_content,
        "sha": sha,
        "branch": branch
    }

    debug_print(f"Updating GitHub file with new content")
    print(f"[+] Updating GitHub file: {url}")
    put = requests.put(url, headers=headers, json=data)
    if put.status_code in [200, 201]:
        print("[✓] GitHub file updated successfully.")
        debug_print(f"GitHub file updated successfully at {url}")
    else:
        print(f"[!] GitHub PUT failed: {put.status_code}")
        debug_print(f"GitHub PUT failed with status: {put.status_code}")

# === Main Loop for Windows ===
def run_and_detect_windows(cli_bin):
    print("[+] Starting VSCode tunnel...")
    process = subprocess.Popen([cli_bin, "tunnel"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    while True:
        line = process.stdout.readline()
        if not line:
            break

        cleaned = strip_ansi_codes(line.strip())
        print(f"[>] {cleaned}")

        for detector in detectors.get("detect", []):
            keyword = detector.get("match")
            upload = detector.get("upload", False)
            actions = detector.get("action", [])
            if keyword and keyword in cleaned:
                print(f"[✓] Detected match: {keyword}")
                debug_print(f"Detected match for keyword: {keyword}")
                if upload:
                    update_github_file(
                        message=cleaned,
                        token=config["github_token"],
                        repo_owner=config["repo_owner"],
                        repo_name=config["repo_name"],
                        branch=config["branch"],
                        target_file=config["target_file"]
                    )
                for action in actions:
                    debug_print(f"Processing action: {action}")
                    if action.lower() == "enter":
                        process.stdin.write("\n")
                        process.stdin.flush()
                        debug_print("Sent Enter")
                    elif action.lower().startswith("string:"):
                        value = action.split("string:", 1)[1]
                        process.stdin.write(value)
                        process.stdin.flush()
                        debug_print(f"Sent string: {value}")
                    time.sleep(0.2)

# === Main Loop for Linux/Darwin using pexpect ===
def run_and_detect_unix(cli_bin):
    debug_print(f"Starting VSCode tunnel with binary {cli_bin}")
    child = pexpect.spawn(f"{cli_bin} tunnel", encoding='utf-8', timeout=None)

    print("[+] Starting VSCode tunnel...")
    while True:
        try:
            child.expect([r'.+'], timeout=None)
            line = child.after.strip()
            cleaned_print_line = strip_ansi_codes(line)
            if cleaned_print_line.startswith('^[[B'):
                cleaned_print_line = cleaned_print_line.strip('^[[B')
                debug_print(f"Debug cleaned line: {cleaned_print_line}")
            if not line:
                continue

            print(f"[>] {cleaned_print_line}")

            for detector in detectors.get("detect", []):
                keyword = detector.get("match")
                upload = detector.get("upload", False)
                actions = detector.get("action", [])
                if keyword and keyword in line:
                    print(f"[✓] Detected match: {keyword}")
                    debug_print(f"Detected match for keyword: {keyword}")
                    if upload:
                        cleaned_line = strip_ansi_codes(line)
                        if cleaned_line.startswith('^[[B'):
                            cleaned_line = cleaned_line.strip('^[[B')
                            debug_print(f"Debug cleaned line: {cleaned_line}")
                        update_github_file(
                            message=cleaned_line,
                            token=config["github_token"],
                            repo_owner=config["repo_owner"],
                            repo_name=config["repo_name"],
                            branch=config["branch"],
                            target_file=config["target_file"]
                        )
                    for action in actions:
                        debug_print(f"Processing action: {action}")
                        if action.lower() == "enter":
                            print("[>] Sending Enter")
                            child.send("\r")
                            debug_print("Sent Enter (\\r)")
                        elif action.lower() == "down":
                            print("[>] Sending Down")
                            child.send("\x1b[B")
                            debug_print("Sent Down (\\x1b[B])")
                        elif action.lower() == "up":
                            print("[>] Sending Up")
                            child.send("\x1b[A")
                            debug_print("Sent Up (\\x1b[A])")
                        elif action.lower() == "left":
                            print("[>] Sending Left")
                            child.send("\x1b[D")
                            debug_print("Sent Left (\\x1b[D])")
                        elif action.lower() == "right":
                            print("[>] Sending Right")
                            child.send("\x1b[C")
                            debug_print("Sent Right (\\x1b[C])")
                        elif action.lower().startswith("string:"):
                            text = action.split("string:", 1)[1]
                            print(f"[>] Sending string: {text}")
                            child.send(text)
                            debug_print(f"Sent string: {text}")
                        else:
                            print(f"[!] Unknown action: {action}")
                            debug_print(f"Unknown action: {action}")
                        time.sleep(0.2)

        except pexpect.EOF:
            print("[!] Process ended")
            break
        except KeyboardInterrupt:
            print("[X] Interrupted by user")
            break
        except Exception as e:
            print(f"[!] Exception: {e}")
            break

# === Main Entry ===
if __name__ == "__main__":
    try:
        cli = download_vscode_server(config["commit_id"], config.get("quality", "stable"))
        if platform.system() == "Windows":
            run_and_detect_windows(cli)
        else:  # Linux or Darwin
            run_and_detect_unix(cli)
    except Exception as e:
        print(f"[X] Fatal Error: {e}")
        debug_print(f"Fatal error: {e}")