# WinSecurityAudit

[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%2011-blue?logo=windows)](https://github.com/baranck0513/WinSecurityAudit)
[![.NET](https://img.shields.io/badge/.NET-10.0-purple?logo=dotnet)](https://dotnet.microsoft.com/)
[![Python](https://img.shields.io/badge/Python-3.9%2B-yellow?logo=python&logoColor=white)](https://www.python.org/)

A Windows security posture auditing tool. It runs 8 configuration checks against a live Windows 11 host, maps the results to the **five Cyber Essentials control areas**, produces a score out of 100, and offers one-click remediation for every failed check.

Built as a final-year dissertation project and since extended.

![WinSecurityAudit dashboard](docs/screenshot-dashboard.png)

---

## Why this exists

Small organisations pursuing Cyber Essentials certification have to evidence a set of basic Windows configuration controls. In practice this is usually done by hand, per machine, against a checklist. This tool automates the assessment and the remediation for the Windows-host portion of that work.

## Cyber Essentials coverage

Each check maps to one of the five Cyber Essentials technical control areas. All five areas are covered.

| Cyber Essentials control | Checks in this tool |
|---|---|
| **Firewalls** | Firewall profile status (Domain / Private / Public) |
| **Secure configuration** | UAC level, USB autorun/autoplay policy, unnecessary high-risk services |
| **Security update management** | Windows Update pending updates + automatic update configuration |
| **User access control** | Password expiry, complexity and account lockout policy; UAC notification level |
| **Malware protection** | Registered antivirus products, Defender real-time protection, SmartScreen enforcement |

> **Scope note:** this tool assesses the Windows host configuration only. It is an aid to self-assessment, not a substitute for a Cyber Essentials assessment, and it does not cover the network-boundary, mobile-device or third-party-software elements of the scheme.

## Architecture

Two layers:

* **Frontend** — C# Windows Forms (.NET 10.0) dashboard rendering results, scores and remediation controls.
* **Backend** — Python engine (`winaudit.py` + `checks/`) that executes PowerShell queries against live Windows APIs and returns structured output.

```
WinSecurityAudit/
├── SecurityDashboardForm.*.cs   # C# GUI (partial classes, one per concern)
├── Program.cs                   # Entry point + backend extraction
├── WinSecurityAudit.csproj      # .NET 10 project file
├── app.manifest                 # UAC elevation manifest
├── winaudit.py                  # Python backend entry point
├── requirements.txt             # Python dependencies
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

The compiled Python backend is embedded as a resource inside the C# binary, so no Python installation is required on the target machine.

## Security considerations

This tool requires Administrator privileges and modifies system security policy. That warrants stating its own threat model explicitly:

* **Elevation** — the application requests elevation via `app.manifest`. All PowerShell queries and every remediation action run in that elevated context.
* **Backend extraction** — the embedded Python backend is written to disk before execution. It is extracted to a per-user temporary directory that is not writable by unprivileged users, to avoid a privileged-file-overwrite path.
* **Remediation is not reversible in-app** — applied fixes change registry values and service states. There is currently no rollback. See Known limitations.
* **No network activity** — the tool makes no outbound connections. All checks are local.

Please report security issues by opening an issue on this repository.

## Getting started

### Requirements

| Component | Version |
|---|---|
| Windows | 11 (x64) |
| .NET Runtime | 10.0+ (not needed for the self-contained release build) |
| Python | 3.9+ (only to rebuild the backend) |
| Privileges | Administrator |

### Running

Download the latest build from [Releases](https://github.com/baranck0513/WinSecurityAudit/releases) and run `WinSecurityAudit.exe`. Windows will prompt for Administrator access via UAC; the checks cannot run without it.

### Building from source

**1. Compile the Python backend**

```bash
pip install -r requirements.txt
pyinstaller --onefile --noconsole winaudit.py
```

This produces `dist/winaudit.exe`. Copy it to the project root before building the C# project.

**2. Build and publish the C# frontend**

```bash
dotnet publish -c Release -r win-x64 --self-contained true
```

The output in `bin/Release/net10.0-windows/win-x64/publish/` is a single self-contained executable.

## Checks and remediation

Each check queries live Windows configuration via PowerShell and returns `PASS`, `FAIL` or `ERROR`.

| Check | What it inspects | Remediation |
|---|---|---|
| **Antivirus** | Registered AV products via SecurityCenter2 + Defender real-time protection status | Re-enables Defender real-time monitoring |
| **Firewall** | Domain, Private and Public firewall profile states | Enables all firewall profiles |
| **Password policy** | Password expiry, complexity, account lockout policy | Applies recommended password policy |
| **Windows Update** | Pending updates + automatic update configuration | Triggers Windows Update |
| **User Account Control** | UAC registry settings and notification level | Restores UAC to recommended level |
| **USB autorun** | Autoplay and autorun registry policy | Disables USB autorun/autoplay |
| **SmartScreen** | SmartScreen enforcement level | Enables SmartScreen enforcement |
| **Unnecessary services** | High-risk services running without need (Remote Registry, Telnet, and similar) | Stops and disables flagged services |

## Command-line usage

The backend runs independently of the GUI, which makes it usable in scripted or multi-host scenarios.

```bash
# Full scan (all 8 checks)
python winaudit.py

# Single check
python winaudit.py "Firewall"

# Apply a remediation
python winaudit.py "Fix:Firewall"
```

Output is line-structured and parsed by the GUI:

```
Checking Antivirus status
Status: PASS
SCORE_LINE: PASS:antivirus
Active Antivirus: Windows Defender
```

## Scoring

The dashboard scores out of 100 across the 8 checks:

* **PASS** — full points awarded
* **FAIL** — zero points, remediation offered
* **ERROR** — check could not run, typically because of missing Administrator privileges

## Known limitations

Stated deliberately, because they shape what this tool should and should not be used for.

* **Line-structured stdout instead of JSON.** The GUI parses the backend's output line by line. This is brittle and makes the backend hard to consume programmatically. JSON output is the correct design and is the next planned change.
* **No automated tests.** For a tool that modifies security policy with elevated privileges, this is the most significant gap.
* **Three-layer architecture.** C# → embedded Python → PowerShell adds indirection that the problem does not strictly require. The split was driven by the dissertation brief; a single PowerShell module, or a pure C# implementation, would be simpler to deploy and maintain.
* **No rollback.** Remediation actions cannot currently be reverted from within the application.
* **Single-host only.** There is no fleet or multi-machine mode.

## Roadmap

* [ ] JSON output from the backend
* [ ] Unit tests for check parsing and scoring logic
* [ ] CI pipeline (build + test on push)
* [ ] Exportable audit report (PDF / HTML)
* [ ] Rollback for applied remediations
* [ ] Scan history and drift comparison
* [ ] Multi-host scanning

## License

MIT. See [LICENSE](LICENSE).
