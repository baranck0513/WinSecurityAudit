import json
from checks.base import BaseScanner


class ServicesCheck(BaseScanner):

    # this list defines which windows services we consider risky or unnecessary for a typical home or office user
    # each entry is a tuple of three things:
    #   1. the service's internal registry name (used to query it via powershell)
    #   2. the human-readable display name (shown to the user in the result card)
    #   3. a short explanation of why this service is a security risk
    # these services all open network access points that most users do not need
    RISKY_SERVICES_TO_CHECK = [
        ("TermService",    "Remote Desktop Services",         "Allows remote desktop connections"),
        ("RemoteRegistry", "Remote Registry",                 "Allows remote editing of registry"),
        ("Telnet",         "Telnet",                          "Unencrypted remote access"),
        ("FTPSVC",         "FTP Service (IIS)",               "Unencrypted file transfer"),
        ("W3SVC",          "World Wide Web Publishing (IIS)", "Web server"),
        ("WinRM",          "Windows Remote Management",       "Remote management"),
        ("mrxsmb10",       "SMBv1 Protocol",                  "Ransomware attack vector (WannaCry/NotPetya)"),
    ]

    def run(self):
        # this is the title line shown at the top of the result card in the GUI
        print("Checking Unnecessary/Risky Services")

        # this powershell script loops through each service name in our list and reports its state
        # Status tells us if the service is currently Running, Stopped, or in some other state
        # StartType tells us if windows is set to start it automatically when the computer boots
        # if a service is not installed at all, we store "NotInstalled" so we can skip it cleanly
        powershell_command = """
        $serviceNamesToCheck  = @("TermService", "RemoteRegistry", "Telnet", "FTPSVC", "W3SVC", "WinRM", "mrxsmb10")
        $serviceStatusResults = @{}
        foreach ($serviceName in $serviceNamesToCheck) {
            $foundService = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
            if ($foundService) {
                $serviceStatusResults[$serviceName] = @{ Status = $foundService.Status.ToString(); StartType = $foundService.StartType.ToString() }
            } else {
                $serviceStatusResults[$serviceName] = @{ Status = "NotInstalled"; StartType = "N/A" }
            }
        }
        $serviceStatusResults | ConvertTo-Json
        """

        powershell_raw_output, powershell_ran_successfully = self.run_powershell(powershell_command)

        if powershell_ran_successfully and powershell_raw_output:
            try:
                parsed_services_data = json.loads(powershell_raw_output)

                # we separate our findings into two groups:
                # group 1: services actively running right now (more urgent — immediate exposure)
                # group 2: services installed but currently stopped (less urgent — may start on next reboot)
                list_of_currently_running_risky_services     = []
                list_of_installed_but_stopped_risky_services = []

                for service_registry_name, service_friendly_name, why_this_service_is_risky in self.RISKY_SERVICES_TO_CHECK:
                    this_service_data = parsed_services_data.get(service_registry_name)
                    if not this_service_data:
                        continue

                    service_current_status = this_service_data.get('Status', 'Unknown')
                    service_start_type     = this_service_data.get('StartType', 'Unknown')

                    if service_current_status == "NotInstalled":
                        # this service does not exist on this machine — nothing to report
                        continue

                    elif service_current_status == "Running":
                        # the service is actively running right now — most urgent case
                        list_of_currently_running_risky_services.append(
                            f"{service_friendly_name} (Running/{service_start_type}) - {why_this_service_is_risky}"
                        )

                    elif service_start_type == "Automatic":
                        # the service is stopped now but will auto-start on the next reboot — worth flagging
                        list_of_installed_but_stopped_risky_services.append(
                            f"{service_friendly_name} (Stopped but set to Automatic) - {why_this_service_is_risky}"
                        )

                    else:
                        # the service is installed and stopped, and is not set to auto-start — relatively safe
                        list_of_installed_but_stopped_risky_services.append(
                            f"{service_friendly_name} (Stopped/{service_start_type}) - OK"
                        )

                if list_of_currently_running_risky_services:
                    # at least one risky service is actively running — this is the most serious outcome
                    print("Status: FAIL")
                    print("SCORE_LINE: FAIL:services")
                    print(f"The following risky services are currently active ({len(list_of_currently_running_risky_services)} found):")
                    for risky_service_description in list_of_currently_running_risky_services:
                        print(f"  [RUNNING] {risky_service_description}")
                    for stopped_service_description in list_of_installed_but_stopped_risky_services:
                        print(f"  [WARNING] {stopped_service_description}")
                    print("Risk: These services open network access points on your computer that you likely do not need.")
                    print("Each one is a potential entry point for attackers, especially on public or shared networks.")
                    print("How to fix:")
                    print("  1. Press Windows + R, type 'services.msc' and press Enter")
                    print("  2. Find each service listed above")
                    print("  3. Right-click it > Properties > Set 'Startup type' to 'Disabled' > Click 'Stop'")

                elif list_of_installed_but_stopped_risky_services and any("Automatic" in s for s in list_of_installed_but_stopped_risky_services):
                    # nothing running now but something is set to auto-start on next boot
                    print("Status: WARN")
                    print("SCORE_LINE: WARN:services")
                    print("No risky services are running right now, but the following are set to start automatically:")
                    for stopped_service_description in list_of_installed_but_stopped_risky_services:
                        print(f"  {stopped_service_description}")
                    print("Risk: These services will activate on next reboot and could expose your computer to the network.")
                    print("How to fix:")
                    print("  1. Press Windows + R, type 'services.msc' and press Enter")
                    print("  2. Find each service listed above")
                    print("  3. Right-click > Properties > Set 'Startup type' to 'Disabled'")

                else:
                    # none of the risky services are running or set to auto-start — machine is clean
                    print("Status: PASS")
                    print("SCORE_LINE: PASS:services")
                    print("No unnecessary or risky services are running.")
                    print("Your computer is not exposing any unnecessary network access points.")

            except Exception as parsing_error:
                print("Status: ERROR")
                print("SCORE_LINE: ERROR:services")
                print(f"Could not parse services data: {str(parsing_error)}")
                print("How to fix:")
                print("  1. Press Windows + R, type 'services.msc' and press Enter")
                print("  2. Check the status of the services listed above manually")
        else:
            # powershell failed completely or returned nothing
            print("Status: ERROR")
            print("SCORE_LINE: ERROR:services")
            print("Could not retrieve services information.")
            print("How to fix:")
            print("  1. Right-click this program and select 'Run as administrator'")
            print("  2. Then run the scan again")

    def fix(self):
        # stop and disable every risky service except TermService (Remote Desktop)
        # TermService is deliberately excluded: stopping it would immediately disconnect
        # any user who is connected via Remote Desktop, including the user running this fix
        powershell_command = """
        $servicesToDisable = @("RemoteRegistry", "Telnet", "FTPSVC", "W3SVC", "WinRM")
        foreach ($svcName in $servicesToDisable) {
            $svc = Get-Service -Name $svcName -ErrorAction SilentlyContinue
            if ($svc) {
                if ($svc.Status -eq "Running") {
                    Stop-Service -Name $svcName -Force -ErrorAction SilentlyContinue
                }
                Set-Service -Name $svcName -StartupType Disabled -ErrorAction SilentlyContinue
            }
        }
        """
        output, success = self.run_powershell(powershell_command)
        if success:
            print("FIX_RESULT: SUCCESS")
            print("FIX_MESSAGE: Risky services (Remote Registry, Telnet, FTP, Web Publishing, Windows Remote Management) have been stopped and disabled. Remote Desktop Services was not changed — disable it manually via services.msc if you do not need it.")
        else:
            print("FIX_RESULT: FAIL")
            print(f"FIX_MESSAGE: Could not disable services. {output.strip()}")
