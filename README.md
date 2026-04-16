# <p align="center"> WinSecurityAudit </p>

[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows-blue?logo=windows)](https://github.com/karamx/WinSecurityAudit)
[![.NET](https://img.shields.io/badge/.NET-10.0-purple?logo=dotnet)](https://dotnet.microsoft.com/)
[![Python](https://img.shields.io/badge/Python-3.x-yellow?logo=python&logoColor=white)](https://www.python.org/)

A Windows desktop application that audits your system's security configuration across 8 key areas, assigns a security score, and offers one-click automated fixes. Built as a BSc Computing dissertation project (COMP6013).

The project is split into two layers:

* **Frontend** — C# Windows Forms (.NET 10.0) dashboard that renders results, scores, and fix controls.
* **Backend** — Python engine (`dissertation.py` + `checks/`) that executes PowerShell queries against live Windows APIs and returns structured output.

## Architecture

```
WinSecurityAudit/
├── SecurityDashboardForm.*.cs   # C# GUI (partial classes per concern)
├── Program.cs                   # Entry point + backend extraction
├── DissertationGUI.csproj       # .NET 10 project file
├── app.manifest                 # UAC elevation manifest
├── dissertation.py              # Python backend entry point
└── checks/
    ├── base.py                  # BaseScanner (PowerShell helper)
    ├── antivirus.py
    ├── firewall.py
    ├── password.py
    ├── windows_update.py
    ├── uac.py
    ├── usb_autorun.py
    ├── smartscreen.py
    └── services.py
```

The compiled Python backend (`dissertation.exe`) is embedded as a resource inside the C# binary — no Python installation is required on the target machine.

## Getting Started

### Requirements

- **OS**: Windows 10 or Windows 11 (x64)
- **Runtime**: .NET 10.0 Runtime (or use the self-contained published build — no install needed)
- **Privileges**: Administrator — required for PowerShell security queries and automated fixes

### Running the Application

Download the latest release and run `DissertationGUI.exe`. Windows will prompt for administrator access via UAC — this is required for the security checks to work.

### Building from Source

**Prerequisites**

- [.NET 10.0 SDK](https://dotnet.microsoft.com/download)
- [Python 3.x](https://www.python.org/) + [PyInstaller](https://pyinstaller.org/) (to rebuild the backend)

**1. Compile the Python backend**

```bash
pyinstaller --onefile --noconsole dissertation.py
```

This produces `dist/dissertation.exe`. Copy it to the project root before building the C# project.

**2. Build and publish the C# frontend**

```bash
dotnet publish -c Release -r win-x64 --self-contained true
```

The output in `bin/Release/net10.0-windows/win-x64/publish/` is a single self-contained executable.

## Security Checks

Each check queries live Windows configuration via PowerShell and returns a `PASS`, `FAIL`, or `ERROR` result that contributes to the overall security score.

| Check | What it inspects | Auto-fix |
|---|---|---|
| **Antivirus** | Registered AV products via SecurityCenter2 + Windows Defender real-time protection status | ✅ Re-enables Defender real-time monitoring |
| **Firewall** | Domain, Private, and Public firewall profile states | ✅ Enables all firewall profiles |
| **Password** | Password expiry, complexity, and account lockout policy | ✅ Applies recommended password policy |
| **Windows Update** | Pending updates and automatic update configuration | ✅ Triggers Windows Update |
| **User Account Control** | UAC registry settings and notification level | ✅ Restores UAC to recommended level |
| **USB Autorun** | Autoplay and autorun registry policy | ✅ Disables USB autorun/autoplay |
| **SmartScreen** | Windows SmartScreen enforcement level | ✅ Enables SmartScreen enforcement |
| **Unnecessary Services** | Detects high-risk services that are running but not needed (Remote Registry, Telnet, etc.) | ✅ Stops and disables flagged services |

### Running a check from the command line

The Python backend can also be called directly without the GUI:

```bash
# Full scan (all 8 checks)
python dissertation.py

# Single check
python dissertation.py "Antivirus"
python dissertation.py "Firewall"
python dissertation.py "Windows Update"
python dissertation.py "User Account Control"

# Apply a fix
python dissertation.py "Fix:Firewall"
python dissertation.py "Fix:USB Autorun"
```

Each check prints structured output that the C# GUI reads line-by-line:

```
Checking Antivirus status
Status: PASS
SCORE_LINE: PASS:antivirus
Active Antivirus: Windows Defender
All Detected: Windows Defender (Active)
Your computer is protected. Windows Defender is actively scanning for threats.
```

## Scoring

The dashboard calculates a score out of 100 based on the results of all 8 checks:

- **PASS** — check passed, full points awarded
- **FAIL** — check failed, zero points, fix available
- **ERROR** — check could not run (typically missing admin privileges)

<details>
<summary><strong>Roadmap / Implementation Status</strong></summary>

### Security Checks

- [x] Antivirus detection (SecurityCenter2 + Defender + service keyword fallback)
- [x] Firewall profile status (Domain / Private / Public)
- [x] Password policy (expiry, complexity, lockout)
- [x] Windows Update (pending updates + auto-update config)
- [x] User Account Control (UAC registry level)
- [x] USB Autorun / Autoplay policy
- [x] Windows SmartScreen enforcement
- [x] Unnecessary / high-risk services

### Automated Fixes

- [x] Re-enable Windows Defender real-time protection
- [x] Enable all firewall profiles
- [x] Apply recommended password policy
- [x] Trigger Windows Update
- [x] Restore UAC to recommended level
- [x] Disable USB autorun/autoplay
- [x] Enable SmartScreen enforcement
- [x] Stop and disable unnecessary services

### GUI Features

- [x] Sidebar with individual check navigation
- [x] Live progress bar during scan
- [x] Per-check result cards with PASS/FAIL/ERROR state
- [x] Overall security score display
- [x] One-click fix buttons per failed check
- [ ] Scan history / previous results comparison
- [ ] Export report to PDF
- [ ] Scheduled automatic scans
- [ ] Custom check configuration

</details>

## Contributing

Contributions are welcome. Please open an issue first to discuss what you would like to change.

## Requirements Summary

| Component | Version |
|---|---|
| Windows | 10 / 11 (x64) |
| .NET SDK | 10.0+ |
| Python | 3.9+ |
| PyInstaller | Latest |
| Privileges | Administrator |

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
