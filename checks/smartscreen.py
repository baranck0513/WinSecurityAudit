import json
from checks.base import BaseScanner


class SmartScreenCheck(BaseScanner):

    def run(self):
        # this is the title line shown at the top of the result card in the GUI
        print("Checking Windows SmartScreen status")

        # SmartScreen is a windows feature that checks downloaded files and apps against
        # a database of known malware before letting them run — it acts as a second line of
        # defence after antivirus, specifically targeting files from the internet
        #
        # it is stored in two different registry locations:
        #   location 1 (user-facing setting):
        #     HKLM\...\Explorer key, value SmartScreenEnabled
        #     set through Windows Security > App & browser control
        #     possible values: "Block" (strongest), "Warn" (default), "Off" (disabled)
        #
        #   location 2 (group policy override):
        #     HKLM\...\Policies\Windows\System key
        #     set by an administrator and takes priority over the user-facing setting
        #     EnableSmartScreen = 0 means it is force-disabled by policy
        #     ShellSmartScreenLevel controls the level ("Block" or "Warn") when enabled by policy
        powershell_command = """
        $smartscreenResult = @{
            AppSetting     = $null
            PolicyEnabled  = $null
            PolicyLevel    = $null
        }

        $explorerRegistryKey = Get-ItemProperty -Path "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Explorer" `
                               -ErrorAction SilentlyContinue
        if ($explorerRegistryKey -and $explorerRegistryKey.PSObject.Properties['SmartScreenEnabled']) {
            $smartscreenResult.AppSetting = $explorerRegistryKey.SmartScreenEnabled
        }

        $groupPolicyRegistryKey = Get-ItemProperty -Path "HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\System" `
                                  -ErrorAction SilentlyContinue
        if ($groupPolicyRegistryKey) {
            if ($groupPolicyRegistryKey.PSObject.Properties['EnableSmartScreen']) {
                $smartscreenResult.PolicyEnabled = $groupPolicyRegistryKey.EnableSmartScreen
            }
            if ($groupPolicyRegistryKey.PSObject.Properties['ShellSmartScreenLevel']) {
                $smartscreenResult.PolicyLevel = $groupPolicyRegistryKey.ShellSmartScreenLevel
            }
        }

        $smartscreenResult | ConvertTo-Json
        """

        powershell_raw_output, powershell_ran_successfully = self.run_powershell(powershell_command)

        if powershell_ran_successfully and powershell_raw_output:
            try:
                parsed_smartscreen_data = json.loads(powershell_raw_output)

                group_policy_smartscreen_enabled_value = parsed_smartscreen_data.get('PolicyEnabled')
                group_policy_smartscreen_level         = parsed_smartscreen_data.get('PolicyLevel')
                explorer_registry_smartscreen_setting  = parsed_smartscreen_data.get('AppSetting')

                if group_policy_smartscreen_enabled_value is not None:
                    # a group policy key was found — this overrides whatever the user has set
                    if str(group_policy_smartscreen_enabled_value) == "0":
                        # an administrator has force-disabled SmartScreen via group policy
                        self._print_fail("Disabled via Group Policy")
                        return

                    # group policy has SmartScreen turned on — now check what level it enforces
                    # if no level is specified in the policy, treat it as "warn" (the safer assumption)
                    enforced_smartscreen_level = str(group_policy_smartscreen_level).strip().lower() if group_policy_smartscreen_level else "warn"
                    if enforced_smartscreen_level == "block":
                        self._print_pass("Block — enforced via Group Policy")
                    else:
                        self._print_warn("Warn — enforced via Group Policy")
                    return

                # no group policy key found — fall back to the user-facing explorer registry setting
                if explorer_registry_smartscreen_setting is not None:
                    user_facing_smartscreen_setting = str(explorer_registry_smartscreen_setting).strip().lower()
                    if user_facing_smartscreen_setting == "block":
                        # strongest setting — unrecognised files are blocked outright, not just warned about
                        self._print_pass("Block (strongest protection)")
                    elif user_facing_smartscreen_setting == "warn":
                        # default windows setting — warns the user but still allows them to proceed
                        self._print_warn("Warn (default Windows setting)")
                    elif user_facing_smartscreen_setting == "off":
                        # the user has manually turned SmartScreen off in Windows Security settings
                        self._print_fail("Disabled by user")
                    else:
                        # the registry contains a value we do not recognise — treat it conservatively
                        self._print_warn(f"Unknown value: {explorer_registry_smartscreen_setting}")
                else:
                    # the key is completely absent — windows default behaviour is to warn (not block)
                    self._print_warn("Windows default (Warn)")

            except Exception as parsing_error:
                print("Status: ERROR")
                print("SCORE_LINE: ERROR:smartscreen")
                print(f"Could not parse SmartScreen data: {str(parsing_error)}")
                print("How to fix:")
                print("  1. Open Windows Security from the Start Menu")
                print("  2. Click 'App & browser control' and check the settings manually")
        else:
            # powershell failed completely or returned nothing
            print("Status: ERROR")
            print("SCORE_LINE: ERROR:smartscreen")
            print("Could not retrieve SmartScreen status.")
            print("How to fix:")
            print("  1. Right-click this program and select 'Run as administrator'")
            print("  2. Then run the scan again")

    # --- helper methods used by run() to keep the print statements consistent ---
    # these avoid repeating the same four or five lines every time we want to output a result

    def _print_pass(self, detail_message):
        # call this when SmartScreen is enabled at the "Block" level — the strongest protection
        print("Status: PASS")
        print("SCORE_LINE: PASS:smartscreen")
        print(f"SmartScreen: Enabled — {detail_message}")
        print("SmartScreen is set to block unrecognised apps and files downloaded from the internet.")
        print("This protects you from accidentally running malware or phishing files.")

    def _print_warn(self, detail_message):
        # call this when SmartScreen is in Warn mode — still on but allows the user to bypass the warning
        print("Status: WARN")
        print("SCORE_LINE: WARN:smartscreen")
        print(f"SmartScreen: Warn mode — {detail_message}")
        print("SmartScreen will warn you about unrecognised files but still lets you bypass the warning.")
        print("Risk: You could accidentally allow a malicious file through by clicking 'Run Anyway'.")
        print("How to fix:")
        print("  1. Open Windows Security from the Start Menu")
        print("  2. Click 'App & browser control'")
        print("  3. Under 'Check apps and files', select 'Block'")

    def _print_fail(self, detail_message):
        # call this when SmartScreen is completely disabled — no protection at all
        print("Status: FAIL")
        print("SCORE_LINE: FAIL:smartscreen")
        print(f"SmartScreen: Disabled — {detail_message}")
        print("SmartScreen is turned off. Files and apps downloaded from the internet will not be checked.")
        print("Risk: You could unknowingly run malware downloaded from websites or email attachments.")
        print("How to fix:")
        print("  1. Open Windows Security from the Start Menu")
        print("  2. Click 'App & browser control'")
        print("  3. Under 'Check apps and files', select 'Warn' or 'Block'")

    def fix(self):
        # write SmartScreenEnabled="Block" to the Explorer registry key
        # this is the same value that Windows Security > App & browser control writes
        # when the user selects "Block" for "Check apps and files"
        powershell_command = (
            'Set-ItemProperty '
            '-Path "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Explorer" '
            '-Name SmartScreenEnabled -Value "Block" -Type String -Force'
        )
        output, success = self.run_powershell(powershell_command)
        if success:
            print("FIX_RESULT: SUCCESS")
            print("FIX_MESSAGE: Windows SmartScreen has been set to 'Block' mode. Unrecognised files and apps downloaded from the internet will now be blocked before they can run.")
        else:
            print("FIX_RESULT: FAIL")
            print(f"FIX_MESSAGE: Could not configure SmartScreen. {output.strip()}")
