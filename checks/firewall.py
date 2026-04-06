import json
from checks.base import BaseScanner


class FirewallCheck(BaseScanner):

    def run(self):
        # this is the title line shown at the top of the result card in the GUI
        print("Checking Firewall status")

        # Get-NetFirewallProfile returns one entry per network profile
        # windows has three network profiles: Domain (work/school), Private (home), and Public (cafes/airports)
        # ideally the firewall should be ON for all three
        # I only need the Name and whether each profile is Enabled or not
        powershell_command = "Get-NetFirewallProfile | Select-Object Name, Enabled | ConvertTo-Json"
        powershell_raw_output, powershell_ran_successfully = self.run_powershell(powershell_command)

        if powershell_ran_successfully and powershell_raw_output:
            try:
                # parse the json list of firewall profiles powershell returned
                parsed_firewall_profiles = json.loads(powershell_raw_output)

                # if only one profile exists (unusual but possible), powershell returns a dict not a list
                # wrapping it in a list keeps the loop below consistent
                if isinstance(parsed_firewall_profiles, dict):
                    parsed_firewall_profiles = [parsed_firewall_profiles]

                # split all profiles into two buckets based on whether the firewall is on or off for each
                list_of_enabled_profiles  = []
                list_of_disabled_profiles = []

                for firewall_profile in parsed_firewall_profiles:
                    profile_name = firewall_profile.get('Name', 'Unknown')
                    if firewall_profile.get('Enabled', False):
                        list_of_enabled_profiles.append(profile_name)
                    else:
                        list_of_disabled_profiles.append(profile_name)

                if len(list_of_enabled_profiles) == len(parsed_firewall_profiles):
                    # every single network profile has the firewall switched on — best case
                    print("Status: PASS")
                    print("SCORE_LINE: PASS:firewall")
                    print("Firewall Status: All profiles enabled")
                    print(f"Enabled Profiles: {', '.join(list_of_enabled_profiles)}")
                    print("Your firewall is blocking unauthorised network traffic.")

                elif len(list_of_enabled_profiles) > 0:
                    # some profiles are on but at least one is off — partial protection
                    print("Status: WARN")
                    print("SCORE_LINE: WARN:firewall")
                    print("Firewall Status: Partially enabled")
                    print(f"Enabled: {', '.join(list_of_enabled_profiles)}")
                    print(f"Disabled: {', '.join(list_of_disabled_profiles)}")
                    print(f"Your firewall is not active on all network profiles ({', '.join(list_of_disabled_profiles)}).")
                    print("Risk: When connecting to public Wi-Fi (e.g. restaurants, airports), your computer may be exposed to attacks from other devices on the same network.")
                    print("How to fix:")
                    print("  1. Open the Start Menu and search for 'Windows Defender Firewall'")
                    print("  2. Click 'Turn Windows Defender Firewall on or off' on the left hand side")
                    print(f"  3. Make sure firewall is ON for all profiles, especially: {', '.join(list_of_disabled_profiles)}")

                else:
                    # every single network profile has the firewall switched off — worst case
                    print("Status: FAIL")
                    print("SCORE_LINE: FAIL:firewall")
                    print("Firewall Status: All profiles disabled")
                    print(f"Disabled Profiles: {', '.join(list_of_disabled_profiles)}")
                    print("Your firewall is completely disabled.")
                    print("Risk: Hackers and malicious software on your network can connect to your computer without any barrier.")
                    print("How to fix:")
                    print("  1. Open the Start Menu and search for 'Windows Defender Firewall'")
                    print("  2. Click 'Turn Windows Defender Firewall on or off'")
                    print("  3. Turn it ON for both Private and Public networks")

            except Exception as parsing_error:
                # the json came back but could not be parsed — probably an unexpected format
                print("Status: ERROR")
                print("SCORE_LINE: ERROR:firewall")
                print(f"Could not parse firewall data: {str(parsing_error)}")
                print("How to fix:")
                print("  1. Open the Start Menu and search for 'Windows Defender Firewall'")
                print("  2. Check the status of each network profile manually")
        else:
            # powershell failed to run or returned nothing at all
            print("Status: ERROR")
            print("SCORE_LINE: ERROR:firewall")
            print("Could not retrieve firewall status.")
            print("How to fix:")
            print("  1. Right-click this program and select 'Run as administrator'")
            print("  2. Then run the scan again")

    def fix(self):
        # enable Windows Firewall for all three network profiles in a single command
        powershell_command = "Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled True"
        output, success = self.run_powershell(powershell_command)
        if success:
            print("FIX_RESULT: SUCCESS")
            print("FIX_MESSAGE: Windows Firewall has been enabled for all network profiles (Domain, Private, and Public). Your computer is now protected against unauthorised network connections.")
        else:
            print("FIX_RESULT: FAIL")
            print(f"FIX_MESSAGE: Could not enable the firewall. {output.strip()}")
