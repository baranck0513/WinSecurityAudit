import sys

# import each individual security check class from the checks/ folder
# each file in checks/ handles one specific area of windows security
# they all inherit from BaseScanner which provides the run_powershell() helper
from checks.antivirus      import AntivirusCheck
from checks.firewall       import FirewallCheck
from checks.password       import PasswordCheck
from checks.windows_update import WindowsUpdateCheck
from checks.uac            import UACCheck
from checks.usb_autorun    import USBAutorunCheck
from checks.smartscreen    import SmartScreenCheck
from checks.services       import ServicesCheck


def run_scan(scan_type="Full Scan"):
    # this dictionary maps each scan name (as shown in the GUI sidebar) to its check object
    # the key must match exactly what the C# application passes as a command-line argument
    # e.g. when the user clicks "Antivirus" in the sidebar, C# runs: python dissertation.py "Antivirus"
    all_available_checks = {
        "Antivirus":             AntivirusCheck(),
        "Firewall":              FirewallCheck(),
        "Password":              PasswordCheck(),
        "Windows Update":        WindowsUpdateCheck(),
        "User Account Control":  UACCheck(),
        "USB Autorun":           USBAutorunCheck(),
        "SmartScreen":           SmartScreenCheck(),
        "Unnecessary Services":  ServicesCheck(),
    }

    if scan_type == "Full Scan":
        # run every single check one after another in the order they appear in the dictionary
        for individual_check in all_available_checks.values():
            individual_check.run()
            # the blank print() here is critical — the C# GUI reads the output line by line
            # and uses this empty line as the signal that one check has finished
            # when C# sees this blank line it immediately renders that check's card and advances the progress bar
            # without this blank line the cards would not appear until the very end of the scan
            print()

    elif scan_type in all_available_checks:
        # the user picked one specific check from the sidebar — only run that one
        all_available_checks[scan_type].run()

    elif scan_type.startswith("Fix:"):
        # the C# GUI sent a fix request for one specific check
        # the format is "Fix:CheckName" e.g. "Fix:Firewall" or "Fix:User Account Control"
        # strip the "Fix:" prefix to get the check name, then call its fix() method
        fix_target = scan_type[4:].strip()
        if fix_target in all_available_checks:
            all_available_checks[fix_target].fix()
        else:
            print("FIX_RESULT: FAIL")
            print(f"FIX_MESSAGE: Unknown check '{fix_target}'. Could not apply fix.")

    else:
        # this should not happen in normal use since the GUI only sends valid scan type names
        # but if someone runs this script from the terminal with a typo, this message explains the problem
        print(f"Unknown scan type: {scan_type}")


if __name__ == "__main__":
    # sys.argv is the list of command-line arguments passed to this script
    # sys.argv[0] is always the script name itself (dissertation.py)
    # sys.argv[1] is the first real argument — the C# app sends the selected scan type here
    # if no argument is provided (e.g. running directly from the terminal), we default to Full Scan
    if len(sys.argv) > 1:
        chosen_scan_type = sys.argv[1]
    else:
        chosen_scan_type = "Full Scan"
    run_scan(chosen_scan_type)
