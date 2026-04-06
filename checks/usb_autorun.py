import json
from checks.base import BaseScanner


class USBAutorunCheck(BaseScanner):

    def run(self):
        # this is the title line shown at the top of the result card in the GUI
        print("Checking USB Autorun settings")

        # windows stores autorun/autoplay settings in three different registry locations
        # depending on how they were configured (group policy vs settings app vs nothing):
        #
        #   HKLM (machine-wide policy) — set by an administrator, applies to all users, takes highest priority
        #   HKCU (per-user policy)     — set by the user via group policy tools, lower priority than HKLM
        #   AutoplayHandlers           — set by the Windows Settings > AutoPlay toggle (most common on home PCs)
        #
        # NoDriveTypeAutoRun is a bitmask — each bit controls one type of drive:
        #   255 (0xFF) = all bits set = all drive types are blocked from autorunning
        #   145        = covers removable drives (USB sticks) specifically
        #   anything lower = USB sticks and other drives may autorun
        powershell_command = """
        $machinePolicyAutorunKey = Get-ItemProperty -Path "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\Explorer" -ErrorAction SilentlyContinue
        $userPolicyAutorunKey    = Get-ItemProperty -Path "HKCU:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\Explorer" -ErrorAction SilentlyContinue

        # this key is set when the user turns off AutoPlay via Windows Settings
        # (Settings > Bluetooth & devices > AutoPlay) — it is separate from the group policy keys above
        $autoplaySettingsKey = Get-ItemProperty -Path "HKCU:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Explorer\\AutoplayHandlers" -ErrorAction SilentlyContinue

        @{
            HKLM_NoDriveTypeAutoRun = if ($machinePolicyAutorunKey) { $machinePolicyAutorunKey.NoDriveTypeAutoRun } else { $null }
            HKCU_NoDriveTypeAutoRun = if ($userPolicyAutorunKey)    { $userPolicyAutorunKey.NoDriveTypeAutoRun }    else { $null }
            DisableAutoplay         = if ($autoplaySettingsKey)     { $autoplaySettingsKey.DisableAutoplay }         else { $null }
        } | ConvertTo-Json
        """

        powershell_raw_output, powershell_ran_successfully = self.run_powershell(powershell_command)

        if powershell_ran_successfully and powershell_raw_output:
            try:
                parsed_autorun_settings = json.loads(powershell_raw_output)

                machine_wide_autorun_policy_value = parsed_autorun_settings.get('HKLM_NoDriveTypeAutoRun')
                per_user_autorun_policy_value     = parsed_autorun_settings.get('HKCU_NoDriveTypeAutoRun')
                autoplay_is_disabled_in_settings  = parsed_autorun_settings.get('DisableAutoplay')

                # use the machine-wide (HKLM) policy first because it takes priority
                # if it is not set, fall back to the per-user (HKCU) policy
                if machine_wide_autorun_policy_value is not None:
                    effective_autorun_policy_value = machine_wide_autorun_policy_value
                else:
                    effective_autorun_policy_value = per_user_autorun_policy_value

                if autoplay_is_disabled_in_settings == 1:
                    # the user turned off autoplay in Settings > Bluetooth & devices > AutoPlay
                    # this is the most common way home users disable it and it is fully effective
                    print("Status: PASS")
                    print("SCORE_LINE: PASS:usb_autorun")
                    print("USB Autorun: Disabled via Windows AutoPlay Settings")
                    print("AutoPlay is turned off. Plugging in a USB drive will not automatically run any programs.")

                elif effective_autorun_policy_value is None:
                    # no registry setting was found at all — windows may or may not autorun depending on defaults
                    print("Status: WARN")
                    print("SCORE_LINE: WARN:usb_autorun")
                    print("USB Autorun: No explicit policy is set")
                    print("Risk: Depending on your Windows version, plugging in a USB drive could automatically run programs on it without your knowledge.")
                    print("How to fix:")
                    print("  1. Open 'Settings' > 'Bluetooth & devices' on the left hand side")
                    print("  2. Click 'AutoPlay'")
                    print("  3. Turn off 'Use AutoPlay for all media and devices'")

                elif effective_autorun_policy_value == 255:
                    # 255 = 0xFF = every single bit is set = every possible drive type is blocked
                    print("Status: PASS")
                    print("SCORE_LINE: PASS:usb_autorun")
                    print("USB Autorun: Fully disabled for all drive types")
                    print("Plugging in a USB drive will never automatically run any programs. This protects you from USB-based attacks.")

                elif effective_autorun_policy_value >= 145:
                    # 145 covers removable USB drives specifically, but not every possible drive type
                    print("Status: WARN")
                    print("SCORE_LINE: WARN:usb_autorun")
                    print("USB Autorun: Partially disabled (removable drives are covered, but not all drive types)")
                    print("Risk: Certain types of drives (e.g. network drives) could still trigger autorun.")
                    print("How to fix:")
                    print("  1. Open 'Settings' > 'Bluetooth & devices' on the left hand side")
                    print("  2. Click 'AutoPlay'")
                    print("  3. Turn off 'Use AutoPlay for all media and devices'")

                else:
                    # any value below 145 means removable USB sticks are not properly blocked
                    print("Status: FAIL")
                    print("SCORE_LINE: FAIL:usb_autorun")
                    print(f"USB Autorun: Enabled (value: {effective_autorun_policy_value})")
                    print("Plugging in a USB stick could automatically run whatever program is on it.")
                    print("Risk: This is a common attack method. A malicious USB drive left in a car park or sent in the post could compromise your computer the moment you plug it in.")
                    print("How to fix:")
                    print("  1. Open 'Settings' > 'Bluetooth & devices' on the left hand side")
                    print("  2. Click 'AutoPlay'")
                    print("  3. Turn off 'Use AutoPlay for all media and devices'")

            except Exception as parsing_error:
                print("Status: ERROR")
                print("SCORE_LINE: ERROR:usb_autorun")
                print(f"Could not parse autorun data: {str(parsing_error)}")
                print("How to fix:")
                print("  1. Open 'Settings' > 'Bluetooth & devices' on the left hand side")
                print("  2. Click 'AutoPlay'")
                print("  2. Check your AutoPlay settings manually")
        else:
            # powershell failed completely or returned nothing
            print("Status: ERROR")
            print("SCORE_LINE: ERROR:usb_autorun")
            print("Could not retrieve USB autorun information.")
            print("How to fix:")
            print("  1. Right-click this program and select 'Run as administrator'")
            print("  2. Then run the scan again")

    def fix(self):
        # write DisableAutoplay=1 to the AutoplayHandlers key, which is the same registry value
        # that the Windows Settings > AutoPlay toggle writes when the user turns it off
        powershell_command = """
        $path = "HKCU:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Explorer\\AutoplayHandlers"
        if (!(Test-Path $path)) { New-Item -Path $path -Force | Out-Null }
        Set-ItemProperty -Path $path -Name DisableAutoplay -Value 1 -Type DWord -Force
        """
        output, success = self.run_powershell(powershell_command)
        if success:
            print("FIX_RESULT: SUCCESS")
            print("FIX_MESSAGE: AutoPlay has been disabled. USB drives and removable media will no longer run programs automatically when plugged in.")
        else:
            print("FIX_RESULT: FAIL")
            print(f"FIX_MESSAGE: Could not disable AutoPlay. {output.strip()}")
