import json
from checks.base import BaseScanner


class WindowsUpdateCheck(BaseScanner):

    def run(self):
        # this is the title line shown at the top of the result card in the GUI
        print("Checking Windows Update settings")

        # windows stores its automatic update settings in several possible registry locations
        # we check them in priority order:
        #   location 1: HKLM\...\WindowsUpdate\AU — used when group policy has configured updates centrally
        #               NoAutoUpdate = 1 means updates are explicitly disabled by an admin
        #               AUOptions controls how updates are handled:
        #                 2 = notify only (download and install must be done manually)
        #                 3 = auto-download but prompt to install
        #                 4 = fully automatic (download and install without user input)
        #   location 2: HKLM\...\Auto Update — the equivalent key for non-policy home machines
        #   location 3: if neither registry key exists, check if the windows update service is running at all
        powershell_command = """
        $groupPolicyUpdateSettings = Get-ItemProperty -Path "HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate\\AU" -ErrorAction SilentlyContinue

        if ($groupPolicyUpdateSettings) {
            @{
                NoAutoUpdate = $groupPolicyUpdateSettings.NoAutoUpdate
                AUOptions = $groupPolicyUpdateSettings.AUOptions
            } | ConvertTo-Json
        } else {
            $localUpdateSettings = Get-ItemProperty -Path "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\WindowsUpdate\\Auto Update" -ErrorAction SilentlyContinue
            if ($localUpdateSettings) {
                @{
                    NoAutoUpdate = $localUpdateSettings.AUOptions -eq 1
                    AUOptions = $localUpdateSettings.AUOptions
                } | ConvertTo-Json
            } else {
                $windowsUpdateService = Get-Service -Name wuauserv -ErrorAction SilentlyContinue
                if ($windowsUpdateService) {
                    @{
                        ServiceStatus = $windowsUpdateService.Status
                        ServiceStartType = $windowsUpdateService.StartType
                    } | ConvertTo-Json
                } else {
                    "NO_UPDATE_INFO"
                }
            }
        }
        """

        powershell_raw_output, powershell_ran_successfully = self.run_powershell(powershell_command)

        if powershell_ran_successfully and powershell_raw_output and powershell_raw_output != "NO_UPDATE_INFO":
            try:
                parsed_update_settings = json.loads(powershell_raw_output)

                if 'NoAutoUpdate' in parsed_update_settings:
                    # we found one of the two registry keys that control automatic update behaviour
                    automatic_updates_are_disabled = parsed_update_settings.get('NoAutoUpdate', 0)
                    auto_update_mode_value         = parsed_update_settings.get('AUOptions', 4)

                    if automatic_updates_are_disabled == 1 or automatic_updates_are_disabled is True:
                        # the registry explicitly says "do not install updates automatically"
                        print("Status: FAIL")
                        print("SCORE_LINE: FAIL:windows_update")
                        print("Update Status: Automatic updates are disabled")
                        print("Windows is not updating itself automatically.")
                        print("Risk: Security vulnerabilities are discovered regularly. Without updates, attackers can exploit known weaknesses in your system.")
                        print("How to fix:")
                        print("  1. Open Settings > Windows Update")
                        print("  2. Click 'Advanced options'")
                        print("  3. Turn on 'Receive updates for other Microsoft products' and ensure automatic updates are enabled")

                    elif auto_update_mode_value in (3, 4):
                        # AUOptions 3 = download automatically then ask to install
                        # AUOptions 4 = download and install completely automatically — best option
                        print("Status: PASS")
                        print("SCORE_LINE: PASS:windows_update")
                        print("Update Status: Automatic updates are enabled")
                        print("Windows is keeping itself up to date automatically. Security patches will be installed without you needing to do anything.")

                    elif auto_update_mode_value == 2:
                        # AUOptions 2 = only notify the user, they must manually start the download and install
                        # this is risky because many people dismiss or ignore the notifications
                        print("Status: WARN")
                        print("SCORE_LINE: WARN:windows_update")
                        print("Update Status: Set to notify only - updates are NOT installed automatically")
                        print("Risk: If you dismiss or ignore update notifications, your system could remain vulnerable for a long time.")
                        print("How to fix:")
                        print("  1. Open Settings > Windows Update > Advanced options")
                        print("  2. Set 'Choose how updates are installed' to 'Automatic'")

                    else:
                        # we found the registry key but the value is something we do not recognise
                        # safer to warn than to assume everything is fine
                        print("Status: WARN")
                        print("SCORE_LINE: WARN:windows_update")
                        print("Update Status: Could not confirm automatic updates are on")
                        print("How to fix:")
                        print("  1. Open Settings > Windows Update > Advanced options")
                        print("  2. Make sure automatic updates are turned on")

                elif 'ServiceStatus' in parsed_update_settings:
                    # neither registry key was found so we checked the windows update service instead
                    windows_update_service_status     = parsed_update_settings.get('ServiceStatus', 'Unknown')
                    windows_update_service_start_type = parsed_update_settings.get('ServiceStartType', 'Unknown')

                    if windows_update_service_status == "Running" and windows_update_service_start_type in ("Automatic", "Manual"):
                        # the service is running and will start on boot — updates can happen
                        print("Status: PASS")
                        print("SCORE_LINE: PASS:windows_update")
                        print(f"Update Service: Running ({windows_update_service_start_type})")
                        print("Windows Update service is active and can install security patches.")
                    else:
                        # the service is stopped or disabled — windows cannot check for updates at all
                        print("Status: FAIL")
                        print("SCORE_LINE: FAIL:windows_update")
                        print(f"Update Service: {windows_update_service_status} ({windows_update_service_start_type})")
                        print("The Windows Update service is not running. Your computer cannot receive security patches.")
                        print("Risk: Known vulnerabilities in Windows will remain unpatched, making your system an easy target.")
                        print("How to fix:")
                        print("  1. Press Windows + R, type 'services.msc' and press Enter")
                        print("  2. Find 'Windows Update' in the list")
                        print("  3. Right-click it and select 'Start'")
                        print("  4. Also set 'Startup type' to 'Automatic'")

                else:
                    # the json came back but neither expected key was present
                    print("Status: WARN")
                    print("SCORE_LINE: WARN:windows_update")
                    print("Could not determine automatic update status.")
                    print("How to fix:")
                    print("  1. Open Settings > Windows Update")
                    print("  2. Click 'Advanced options' and confirm automatic updates are enabled")

            except Exception as parsing_error:
                print("Status: ERROR")
                print("SCORE_LINE: ERROR:windows_update")
                print(f"Could not parse update data: {str(parsing_error)}")
                print("How to fix:")
                print("  1. Open Settings > Windows Update")
                print("  2. Check your update settings manually")
        else:
            # powershell failed entirely or returned NO_UPDATE_INFO
            print("Status: WARN")
            print("SCORE_LINE: WARN:windows_update")
            print("Could not retrieve Windows Update information.")
            print("How to fix:")
            print("  1. Right-click this program and select 'Run as administrator'")
            print("  2. Then run the scan again")

    def fix(self):
        # write AUOptions=4 (fully automatic) and NoAutoUpdate=0 to the local update registry key
        # also ensure the wuauserv service is running and set to start automatically
        powershell_command = """
        $path = "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\WindowsUpdate\\Auto Update"
        if (!(Test-Path $path)) { New-Item -Path $path -Force | Out-Null }
        Set-ItemProperty -Path $path -Name AUOptions      -Value 4 -Type DWord -Force
        Set-ItemProperty -Path $path -Name NoAutoUpdate   -Value 0 -Type DWord -Force
        Set-Service  -Name wuauserv -StartupType Automatic -ErrorAction SilentlyContinue
        Start-Service -Name wuauserv                       -ErrorAction SilentlyContinue
        """
        output, success = self.run_powershell(powershell_command)
        if success:
            print("FIX_RESULT: SUCCESS")
            print("FIX_MESSAGE: Automatic Windows updates have been enabled and the Windows Update service has been started. Your computer will now receive security patches automatically.")
        else:
            print("FIX_RESULT: FAIL")
            print(f"FIX_MESSAGE: Could not enable automatic updates. {output.strip()}")
