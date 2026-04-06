import json
from checks.base import BaseScanner


class PasswordCheck(BaseScanner):

    def run(self):
        # this is the title line shown at the top of the result card in the GUI
        print("Checking user password/PIN status")

        # this powershell command reads account information for the currently logged-in windows user
        # $env:USERNAME gives us the name of whoever is logged in right now
        # PasswordRequired = True means the account is configured to need a password to log in
        # PasswordLastSet tells us when the password was last changed ("Never" if it has never been set)
        # PasswordNeverExpires tells us whether the password is set to expire or stay valid forever
        powershell_command = """
        $currentUser = $env:USERNAME
        $user = Get-LocalUser -Name $currentUser -ErrorAction SilentlyContinue

        if ($user) {
            $passwordLastSet = $user.PasswordLastSet
            @{
                Username = $currentUser
                PasswordRequired = $user.PasswordRequired
                PasswordLastSet = if ($passwordLastSet) { $passwordLastSet.ToString() } else { "Never" }
                PasswordNeverExpires = $user.PasswordNeverExpires
                Enabled = $user.Enabled
            } | ConvertTo-Json
        } else {
            "USER_NOT_FOUND"
        }
        """

        powershell_raw_output, powershell_ran_successfully = self.run_powershell(powershell_command)

        if powershell_ran_successfully and powershell_raw_output and powershell_raw_output != "USER_NOT_FOUND":
            try:
                parsed_user_data = json.loads(powershell_raw_output)

                current_windows_username   = parsed_user_data.get('Username', 'Unknown')
                account_requires_a_password = parsed_user_data.get('PasswordRequired', False)
                date_password_was_last_set  = parsed_user_data.get('PasswordLastSet', 'Never')

                if account_requires_a_password and date_password_was_last_set != "Never":
                    # the account has a password and it has been configured at least once — this is the safe state
                    print("Status: PASS")
                    print("SCORE_LINE: PASS:password")
                    print(f"Username: {current_windows_username}")
                    print("Password Status: Password is set")
                    print("Your account is protected with a password. Anyone who picks up your computer cannot log in without it.")

                elif account_requires_a_password and date_password_was_last_set == "Never":
                    # the account policy says a password is required but one has never actually been set
                    print("Status: WARN")
                    print("SCORE_LINE: WARN:password")
                    print(f"Username: {current_windows_username}")
                    print("Password Status: Password is required but has never been set")
                    print("Risk: Your account may be accessible without a password.")
                    print("How to fix:")
                    print("  1. Open Settings > Accounts > Sign-in options")
                    print("  2. Under 'Password', click 'Add' and create a strong password")

                else:
                    # the account has no password requirement at all — anyone with physical access can log straight in
                    print("Status: FAIL")
                    print("SCORE_LINE: FAIL:password")
                    print(f"Username: {current_windows_username}")
                    print("Password Status: No password set")
                    print("Your account has no password. Anyone with physical access to your computer can log in and access all your files.")
                    print("How to fix:")
                    print("  1. Open Settings > Accounts > Sign-in options")
                    print("  2. Under 'Password', click 'Add'")
                    print("  3. Create a strong password (mix of letters, numbers, and symbols)")

            except Exception as parsing_error:
                # the json could not be parsed — return an error so the user knows to check manually
                print("Status: ERROR")
                print("SCORE_LINE: ERROR:password")
                print(f"Could not parse user data: {str(parsing_error)}")
                print("How to fix:")
                print("  1. Open Settings > Accounts > Sign-in options")
                print("  2. Check your password and PIN settings manually")
        else:
            # powershell failed, returned nothing, or could not find the user account
            print("Status: ERROR")
            print("SCORE_LINE: ERROR:password")
            print("Could not retrieve user account information.")
            print("How to fix:")
            print("  1. Right-click this program and select 'Run as administrator'")
            print("  2. Then run the scan again")

    def fix(self):
        # a password cannot be set programmatically without knowing what the user wants it to be
        # setting a password silently would itself be a security risk
        # instead, open the Windows Sign-in settings page so the user can set one manually
        self.run_powershell("Start-Process 'ms-settings:signinoptions'")
        print("FIX_RESULT: MANUAL")
        print("FIX_MESSAGE: Your Windows Sign-in settings page has been opened. Please set a password or PIN manually to protect your account from unauthorised access.")
