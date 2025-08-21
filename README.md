# VSXPloit
**Weaponized VS Code Tunnel in both *vscode-cli* and *vscode-server* for Red Team Covert Operations** • *Inspired by APT Tactics*

## 🎯 Overview

**VSXPloit** is a red team tool that automates and extends a technique first seen in real-world attacks, where **Advanced Persistent Threats (APTs)** abused Visual Studio Code’s `code tunnel` feature to gain remote access into developer environments.

Where APTs used it for persistence and command-and-control (C2), **VSXPloit enhances this tactic** for red teamers by:

> 🚫 Eliminating the need for C2 infrastructure  
> ✅ Using **Microsoft’s own infrastructure (VS Code Tunnel)**  
> 📤 Leveraging **GitHub as a stealth exfiltration vector**

## 📚 Threat Research Inspiration

This framework is directly inspired by threat intelligence research from:

- 🛡 **Fortinet** – [APT group abusing VS Code tunnel in stealth attacks (2023)](https://www.fortinet.com/blog/threat-research)
- 🧠 **Cyble** – [APT29-style infrastructure using code tunnel for lateral movement](https://cyble.com/blog)
- 🔍 **SentinelOne** – [Case study of VS Code abuse in developer-targeted espionage](https://www.sentinelone.com/labs)

> These reports revealed that **code-server**, `code tunnel`, and other developer tools are being used as covert backdoors.  
> **VSXPloit** turns that real-world TTP into a red team-ready framework with reproducible automation and operational stealth.

## 🛰️ Infrastructure Overview

VSXPloit leverages **official Microsoft and GitHub services** for its entire operation flow — no external command-and-control infrastructure is needed.

### 🔧 Operational Architecture

<img width="2306" height="752" alt="vscode-c2-design drawio (1)" src="https://github.com/user-attachments/assets/d2001e33-e5ce-492e-8e84-887d98a93d65" />

**Key Points:**
- VS Code CLI connects to Microsoft’s own tunnel infrastructure.
- All session data is autonomously uploaded to a private GitHub repo (no DNS callbacks or sockets).
- This replicates real-world APT stealth techniques but in a controlled red team context.

📌 *This diagram demonstrates how red teams can operate without traditional implants or infrastructure — fully leveraging trusted platforms already whitelisted in most networks.*


## 🚨 Why VSXPloit?

| Feature | APTs (Observed) | VSXPloit (Red Team Enhancement) |
|--------|------------------|------------------------------|
| VS Code Tunnel Access | ✅ Used for backdoor sessions | ✅ Automated and scripted |
| Persistence via CLI | ✅ Manual reconnection | ✅ Autonomous tunnel setup |
| C2 | Self-hosted, DNS, or web shell | ❌ None — uses **GitHub** for uploads |
| Evasion | No Details | ✅ 100% Microsoft infrastructure |
| Payload Delivery | Manual | ✅ Compiled one-file binary |


## 🧨 Key Capabilities

✅ **Tunnel Automation**  
Launches the `code tunnel` command, detects prompts, and completes interaction flow autonomously.

✅ **Exfiltration via GitHub**  
Session info like login links, tunnel IDs, and machine names are pushed via commits to a private GitHub repo — no outbound beaconing or foreign infra.

✅ **Fully Configurable Logic**  
Behavior is driven by `config.yaml` and `detector.yaml` — no need to recompile.

✅ **Cross-Platform**  
Works on Windows, Linux, and macOS (Darwin) — same tunnel logic, CLI binaries from Microsoft.

✅ **Single Executable Build**  
Create a single `.exe` or ELF payload via `PyInstaller` with included build script.

## Directory Structure

```
VSXPloit/
├── config.yaml          # Configuration file with commit ID, GitHub repo info, and download settings
├── detector.yaml        # Detection rules and automated interaction instructions for the VSCode tunnel
├── main.py              # Core script to download, extract, run VSCode CLI tunnel, detect outputs, and upload logs
├── compile.py           # Script to set up a virtual environment and compile main.py into a standalone executable
├── requirements.txt     # Python dependencies required for development and packaging
├── README.md            # Project documentation and usage instructions
└── dist/                # Output folder where the compiled executable is generated after build
```

## ⚙️ Setup Instructions

### 1. Clone

```bash
git clone https://github.com/Hijack-Everything/vsxploit.git
cd vsxploit
```

### 2. Install Dependencies

```bash
python3 -m venv venv
source venv/bin/activate      # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure

Edit the following files:

#### `config.yaml`

```yaml
commit_id: "2901c5ac6db8a986a5666c3af51ff804d05af0d4"  # <- Current VS Code version
github_token: "ghp_xxx"
repo_owner: "YourGitHub"
repo_name: "loot"
branch: "main"
target_file: "README.md"
download_url_format: "https://update.code.visualstudio.com/commit:{commit_id}/{platform_path}/{quality}" #Here commit_id can be found from vscode ui-> help ->about -> commit_id
extracted_path: "~/.vscode-server"  # Windows: ~\\.vscode-server
extracted_bin: "code"
quality: "stable"
debug: false
```

> 🔎 **Note**: The `commit_id` is **also the VS Code version**. This is how Microsoft’s CLI tunnel binaries are structured. An example config.yaml can be found in the vsxploit/ directory.

#### `detector.yaml`

```yaml
detect:
  - match: "login"
    upload: true
    action: ["down", "enter"]
  - match: "What would you like to call this machine?"
    upload: true
    action: ["string:kali", "enter"]
  - match: "Open this link in your browser"
    upload: true
```
> 🔎 **Note**: The original detector.yaml **verified as of 22-07-2025** can be found in vsxploit/ directory. The file detector.yaml does not contains any secrets hence can be publicly shared and updated.


## 🛠️ Compile to Single Executable

Use the included compiler to generate a standalone `.exe` or Linux binary:

```bash
python compile.py --operating-system windows --architecture x64
```
```bash
python compile.py --operating-system linux --architecture x64
```
#### Supported Platforms:

- OS: `windows`, `linux`, `darwin`
- Arch: `x86`, `x64`

Output will be placed in `dist/`.


## 🔍 Sample Output

```bash
[+] Starting VSCode tunnel...
[>] What would you like to call this machine?
[✓] Detected match: What would you like to call this machine?
[>] Sending string: kali
[+] Updating GitHub file...
[✓] GitHub file updated successfully.
```

## 🧠 Credits & Threat Attribution

VSXPloit is heavily inspired by incident response and threat intelligence research from:

- **Fortinet**
- **Cyble**
- **SentinelOne**

> These vendors documented the abuse of `code tunnel` by APTs, showing how trusted developer tooling can become a covert channel.  
> VSXPloit transforms that TTP into a **red team-ready**, reproducible framework — **no C2 needed**.


## ⚠️ Legal & Ethical Disclaimer

**VSXPloit is intended solely for use in authorized penetration testing, red teaming, and adversary simulation.**

Unauthorized use is strictly prohibited and may violate computer crime laws including the **CFAA**, **UK Computer Misuse Act**, and local regulations.


## 👤 Author

- **Suman Chakraborty (aka Sumz)**
- Offensive Security Researcher | Red Teamer
- [Website](https://sumz.co.in) | [Linkedin](https://www.linkedin.com/in/suman-chakraborty-b857901b1) | [Email](me@sumz.co.in)
