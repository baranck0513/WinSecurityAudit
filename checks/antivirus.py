import json
from checks.base import BaseScanner


class AntivirusCheck(BaseScanner):

    def run(self):
        # this is the title line shown at the top of the result card in the GUI
        print("Checking Antivirus status")

        # this powershell command tries three approaches to find antivirus software:
        # approach 1: query windows security center (root/SecurityCenter2) for any registered antivirus products
        #             this works for third-party antivirus tools like Norton, Kaspersky, Avast etc
        # approach 2: if security center returns nothing, fall back to querying windows defender directly
        #             using Get-MpComputerStatus which gives us AntivirusEnabled and RealTimeProtectionEnabled
        # approach 3: if both above fail, dynamically query all running windows services and filter by
        #             antivirus-related keywords in the service display name or description —
        #             this works with any AV product without needing to know its name in advance
        # the final Write-Output at the bottom guarantees the script always produces at least one line of output
        # so the python side never receives an empty response regardless of what happens above
        powershell_command = """
        $finalOutput = $null
        try { $antivirusProducts = Get-CimInstance -Namespace root/SecurityCenter2 -ClassName AntivirusProduct -ErrorAction Stop } catch { $antivirusProducts = $null }
        try { $defender = Get-MpComputerStatus -ErrorAction Stop } catch { $defender = $null }
        if ($antivirusProducts -and @($antivirusProducts).Count -gt 0) {
            $results = @($antivirusProducts) | ForEach-Object {
                $p = $_
                try {
                    # SecurityCenter2 on Windows 11 can cache a stale active productState for Windows
                    # Defender even after real-time protection is turned off. Cross-check with
                    # Get-MpComputerStatus and force the productState to the disabled value (266240)
                    # when Defender's real-time protection is confirmed off by the authoritative source.
                    if ($p.displayName -like "*Defender*" -and $defender -and -not $defender.RealTimeProtectionEnabled) {
                        [PSCustomObject]@{ displayName = $p.displayName; productState = 266240 }
                    } else {
                        [PSCustomObject]@{ displayName = $p.displayName; productState = $p.productState }
                    }
                } catch {
                    [PSCustomObject]@{ displayName = $p.displayName; productState = 0 }
                }
            }
            if ($results) {
                $finalOutput = $results | ConvertTo-Json
            }
        } elseif ($defender) {
            $finalOutput = @{
                displayName = "Windows Defender"
                AntivirusEnabled = $defender.AntivirusEnabled
                RealTimeProtectionEnabled = $defender.RealTimeProtectionEnabled
            } | ConvertTo-Json
        }
        if (-not $finalOutput) {
            # fallback: SecurityCenter2 and Defender both unavailable or returned nothing
            # dynamically query every running Windows service and filter by keywords that
            # antivirus software typically uses in its display name or description —
            # includes major brand names so products like Kaspersky are caught even if they
            # do not match the generic keyword patterns
            $avKeywords = "kaspersky|avast|avira|bitdefender|malwarebyte|sophos|eset|mcafee|norton|antivir|anti-malware|antimalware|endpoint.{0,20}protect|threat.{0,20}protect|malware.{0,20}protect"
            try {
                $matchingServices = @(Get-CimInstance -ClassName Win32_Service -ErrorAction SilentlyContinue |
                    Where-Object {
                        $_.State -eq "Running" -and (
                            $_.DisplayName  -match $avKeywords -or
                            $_.Description -match $avKeywords
                        )
                    })
            } catch {
                $matchingServices = @()
            }
            if ($matchingServices.Count -gt 0) {
                $firstMatch = $matchingServices[0]
                $finalOutput = @{ displayName = $firstMatch.DisplayName; AntivirusEnabled = $true; RealTimeProtectionEnabled = $true } | ConvertTo-Json
            }
        }
        if ($finalOutput) {
            Write-Output $finalOutput
        } else {
            Write-Output "NO_AV_FOUND"
        }
        """

        powershell_raw_output, powershell_ran_successfully = self.run_powershell(powershell_command)

        if powershell_ran_successfully and powershell_raw_output and powershell_raw_output != "NO_AV_FOUND":
            try:
                # parse the json that powershell returned into a python dictionary or list
                parsed_json_data = json.loads(powershell_raw_output)

                # when only one antivirus product is found, powershell returns a single dict instead of a list
                # wrapping it in a list means the for loop below always works the same way regardless
                if isinstance(parsed_json_data, dict):
                    parsed_json_data = [parsed_json_data]

                # we track all detected products and which one (if any) is currently active
                list_of_all_detected_antivirus_products = []
                name_of_active_antivirus = None

                for antivirus_entry in parsed_json_data:
                    if 'displayName' in antivirus_entry:
                        antivirus_product_name = antivirus_entry['displayName']

                        if 'productState' in antivirus_entry:
                            # productState is a windows security center numeric code stored as 0xSSRR00 in hex
                            # the first hex digit indicates the product state:
                            #   0x6xxxx (>= 393216) = active and protecting
                            #   0x4xxxx or 0x5xxxx  = disabled, expired, or inactive
                            # the old threshold of 200000 was wrong — all defender states exceed it
                            antivirus_is_currently_active = antivirus_entry['productState'] > 393215
                            if antivirus_is_currently_active:
                                activity_label = "Active"
                            else:
                                activity_label = "Inactive"
                            list_of_all_detected_antivirus_products.append(
                                f"{antivirus_product_name} ({activity_label})"
                            )
                            if antivirus_is_currently_active:
                                name_of_active_antivirus = antivirus_product_name
                        else:
                            # this branch handles the windows defender fallback format
                            # which uses separate boolean fields instead of the productState code
                            if antivirus_entry.get('AntivirusEnabled') and antivirus_entry.get('RealTimeProtectionEnabled'):
                                name_of_active_antivirus = antivirus_product_name
                                list_of_all_detected_antivirus_products.append(f"{antivirus_product_name} (Active)")
                            else:
                                list_of_all_detected_antivirus_products.append(f"{antivirus_product_name} (Inactive)")

                if name_of_active_antivirus:
                    # at least one antivirus product is active and protecting the machine right now
                    print("Status: PASS")
                    print("SCORE_LINE: PASS:antivirus")
                    print(f"Active Antivirus: {name_of_active_antivirus}")
                    print(f"All Detected: {', '.join(list_of_all_detected_antivirus_products)}")
                    print(f"Your computer is protected. {name_of_active_antivirus} is actively scanning for threats.")
                else:
                    # antivirus software was found but none of them are actually turned on
                    print("Status: FAIL")
                    print("SCORE_LINE: FAIL:antivirus")
                    print("Active Antivirus: None")
                    if list_of_all_detected_antivirus_products:
                        detected_products_text = ', '.join(list_of_all_detected_antivirus_products)
                    else:
                        detected_products_text = 'None'
                    print(f"Detected Products: {detected_products_text}")
                    print("Your computer has no active antivirus protection.")
                    print("Risk: Malware and viruses can steal your files, passwords, and banking details.")
                    print("How to fix:")
                    print("  1. Open the Start Menu and search for 'Windows Security'")
                    print("  2. Click 'Virus & threat protection'")
                    print("  3. Turn on 'Real-time protection'")

            except Exception as parsing_error:
                # the json powershell returned was in an unexpected format we could not handle
                print("Status: ERROR")
                print("SCORE_LINE: ERROR:antivirus")
                print(f"Could not parse antivirus data: {str(parsing_error)}")
                print("How to fix:")
                print("  1. Open Windows Security from the Start Menu")
                print("  2. Click 'Virus & threat protection' to check your antivirus status manually")
        else:
            # powershell failed to run at all, or returned nothing, or returned NO_AV_FOUND
            print("Status: ERROR")
            print("SCORE_LINE: ERROR:antivirus")
            if powershell_raw_output:
                debug_out = repr(powershell_raw_output[:300])
            else:
                debug_out = "EMPTY"
            print(f"Debug: PS_OK={powershell_ran_successfully}, Output={debug_out}")
            print("How to fix:")
            print("  1. Right-click this program and select 'Run as administrator'")
            print("  2. Then run the scan again")

    def fix(self):
        # re-enable Windows Defender real-time monitoring via Set-MpPreference
        # this only works for Windows Defender — third-party antivirus products cannot be
        # controlled this way and must be re-enabled through their own applications
        powershell_command = "Set-MpPreference -DisableRealtimeMonitoring $false -ErrorAction SilentlyContinue"
        output, success = self.run_powershell(powershell_command)
        if success:
            print("FIX_RESULT: SUCCESS")
            print("FIX_MESSAGE: Windows Defender real-time protection has been re-enabled. If you use third-party antivirus software, please re-enable it through its own application.")
        else:
            print("FIX_RESULT: FAIL")
            print(f"FIX_MESSAGE: Could not enable Windows Defender. {output.strip()}")
