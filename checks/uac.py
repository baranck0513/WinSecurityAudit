import json
from checks.base import BaseScanner


class UACCheck(BaseScanner):

    def run(self):
        # this is the title line shown at the top of the result card in the GUI
        print("Checking UAC settings")

        # UAC (User Account Control) stops programs from silently making admin-level changes to windows
        # we read three registry values that together tell us exactly how UAC is configured:
        #
        #   EnableLUA:
        #     1 = UAC is active (any level)
        #     0 = UAC is completely switched off — any program can do anything without asking
        #
        #   ConsentPromptBehaviorAdmin — controls when and how UAC asks for permission:
        #     0 = elevate silently without ever prompting (UAC is essentially off even if EnableLUA=1)
        #     1 = prompt for password on a secure desktop (very strong)
        #     2 = always notify with a secure desktop dialog (strongest)
        #     5 = only prompt for apps windows does not recognise (default on most machines)
        #
        #   PromptOnSecureDesktop:
        #     1 = UAC dialog appears on a separate isolated desktop that other programs cannot interact with
        #     0 = UAC dialog appears on the normal desktop — other programs could click "yes" on your behalf
        powershell_command = """
        $uacRegistryValues = Get-ItemProperty -Path "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System" -ErrorAction SilentlyContinue

        if ($uacRegistryValues) {
            @{
                EnableLUA = $uacRegistryValues.EnableLUA
                ConsentPromptBehaviorAdmin = $uacRegistryValues.ConsentPromptBehaviorAdmin
                PromptOnSecureDesktop = $uacRegistryValues.PromptOnSecureDesktop
            } | ConvertTo-Json
        } else {
            "NO_UAC_INFO"
        }
        """

        powershell_raw_output, powershell_ran_successfully = self.run_powershell(powershell_command)

        if powershell_ran_successfully and powershell_raw_output and powershell_raw_output != "NO_UAC_INFO":
            try:
                parsed_uac_settings = json.loads(powershell_raw_output)

                uac_is_enabled                 = parsed_uac_settings.get('EnableLUA', 0)
                consent_prompt_behaviour_level = parsed_uac_settings.get('ConsentPromptBehaviorAdmin', 5)
                secure_desktop_is_enabled      = parsed_uac_settings.get('PromptOnSecureDesktop', 1)

                if uac_is_enabled == 0:
                    # UAC is completely turned off — nothing on the machine will ever ask permission
                    print("Status: FAIL")
                    print("SCORE_LINE: FAIL:uac")
                    print("UAC Status: Completely disabled")
                    print("User Account Control (UAC) is turned off.")
                    print("Risk: Any program you run (including malware) can silently make changes to your system, install software, or modify critical settings without asking you first.")
                    print("How to fix:")
                    print("  1. Open the Start Menu and search for 'UAC'")
                    print("  2. Click 'Change User Account Control settings'")
                    print("  3. Move the slider to at least the second level from the top")
                    print("  4. Click OK and restart your computer")

                elif consent_prompt_behaviour_level in (1, 2) and secure_desktop_is_enabled == 1:
                    # strictest setting — always asks AND uses a secure isolated desktop to prevent tampering
                    print("Status: PASS")
                    print("SCORE_LINE: PASS:uac")
                    print("UAC Level: Always notify (Maximum)")
                    print("UAC will always ask for your permission before any program makes changes to your computer.")

                elif consent_prompt_behaviour_level == 5 and secure_desktop_is_enabled == 1:
                    # windows default — only asks for apps it does not recognise or trust
                    # a malware disguised as a trusted windows process could slip through this
                    print("Status: WARN")
                    print("SCORE_LINE: WARN:uac")
                    print("UAC Level: Default - only notifies for unknown apps")
                    print("UAC is on but set to the default level, which only asks for permission for apps it does not recognise.")
                    print("Risk: A malicious program disguised as a trusted Windows application could make system changes without alerting you.")
                    print("How to fix:")
                    print("  1. Open the Start Menu and search for 'UAC'")
                    print("  2. Click 'Change User Account Control settings'")
                    print("  3. Move the slider to 'Always notify' (the top position)")

                elif consent_prompt_behaviour_level == 5 and secure_desktop_is_enabled == 0:
                    # UAC prompts do appear but on the normal desktop — other programs could interact with them
                    print("Status: WARN")
                    print("SCORE_LINE: WARN:uac")
                    print("UAC Level: Notifies but without secure desktop")
                    print("Risk: Without the secure desktop, other programs could intercept the UAC prompt and click 'Yes' on your behalf.")
                    print("How to fix:")
                    print("  1. Open the Start Menu and search for 'UAC'")
                    print("  2. Move the slider to 'Always notify' (top position) and click OK")

                elif consent_prompt_behaviour_level == 0:
                    # consent_prompt = 0 means never ask — functionally the same as turning UAC off
                    print("Status: FAIL")
                    print("SCORE_LINE: FAIL:uac")
                    print("UAC Level: Never notify - effectively disabled")
                    print("Risk: Programs on your computer can make any changes, install anything, or modify system files without ever asking you.")
                    print("How to fix:")
                    print("  1. Open the Start Menu and search for 'UAC'")
                    print("  2. Click 'Change User Account Control settings'")
                    print("  3. Move the slider to at least the second level from the top and click OK")

                else:
                    # some non-standard combination of registry values that does not fit any known pattern
                    print("Status: WARN")
                    print("SCORE_LINE: WARN:uac")
                    print("UAC Level: Non-standard configuration detected")
                    print("How to fix:")
                    print("  1. Open the Start Menu and search for 'UAC'")
                    print("  2. Click 'Change User Account Control settings'")
                    print("  3. Move the slider to 'Always notify' (top position) and click OK")

            except Exception as parsing_error:
                print("Status: ERROR")
                print("SCORE_LINE: ERROR:uac")
                print(f"Could not parse UAC data: {str(parsing_error)}")
                print("How to fix:")
                print("  1. Open the Start Menu and search for 'UAC'")
                print("  2. Check 'Change User Account Control settings' manually")
        else:
            # powershell failed or returned NO_UAC_INFO — cannot determine the UAC state
            print("Status: ERROR")
            print("SCORE_LINE: ERROR:uac")
            print("Could not retrieve UAC information.")
            print("How to fix:")
            print("  1. Right-click this program and select 'Run as administrator'")
            print("  2. Then run the scan again")

    def fix(self):
        # set all three UAC registry values to their most secure state:
        #   EnableLUA = 1               → UAC is active
        #   ConsentPromptBehaviorAdmin = 2 → Always Notify (strongest prompt level)
        #   PromptOnSecureDesktop = 1   → prompt appears on isolated secure desktop
        powershell_command = """
        $path = "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System"
        Set-ItemProperty -Path $path -Name EnableLUA                  -Value 1 -Type DWord -Force
        Set-ItemProperty -Path $path -Name ConsentPromptBehaviorAdmin -Value 2 -Type DWord -Force
        Set-ItemProperty -Path $path -Name PromptOnSecureDesktop      -Value 1 -Type DWord -Force
        """
        output, success = self.run_powershell(powershell_command)
        if success:
            print("FIX_RESULT: SUCCESS")
            print("FIX_MESSAGE: UAC has been enabled and set to 'Always Notify' with secure desktop protection. Please restart your computer for the change to take full effect.")
        else:
            print("FIX_RESULT: FAIL")
            print(f"FIX_MESSAGE: Could not configure UAC. {output.strip()}")
