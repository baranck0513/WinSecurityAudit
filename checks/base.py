import subprocess


# this is the parent class that every individual security check inherits from
# it provides one shared helper method: run_powershell()
# every check file (antivirus, firewall, password etc) extends this class
# so they all get the run_powershell method for free without copying the code
class BaseScanner:

    def run_powershell(self, powershell_command):
        # runs a powershell command and returns a tuple of (output_text, did_it_succeed)
        # subprocess.run to launch powershell as a completely separate process
        # capture_output=True means I capture both stdout and stderr instead of letting them print to the screen
        # text=True means the output comes back as a normal python string instead of raw bytes
        # timeout=30 means if the command takes longer than 30 seconds I stop waiting and return an error
        try:
            # CREATE_NO_WINDOW prevents a console window being allocated for the child process
            # STARTUPINFO with STARTF_USESHOWWINDOW + SW_HIDE is a second layer of suppression —
            # necessary because dissertation.exe is a windowed (console=False) PyInstaller app,
            # and on Windows a windowed parent launching a console child can still produce a
            # visible window unless both flags are applied together
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            completed_process = subprocess.run(
                ["powershell", "-NonInteractive", "-NoProfile", "-WindowStyle", "Hidden",
                 "-Command", powershell_command],
                capture_output=True,
                text=True,
                timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW,
                startupinfo=startupinfo,
            )
            # strip() removes any extra whitespace, spaces, or newlines from the start and end of the output
            # returncode == 0 means the powershell command finished without errors
            # (0 = success in almost all command-line programs)
            return completed_process.stdout.strip(), completed_process.returncode == 0

        except Exception as error_that_occurred:
            # if anything goes wrong — e.g. powershell is not found, or the timeout fires —
            # return a descriptive error message and False to signal it did not succeed
            return f"Error: {str(error_that_occurred)}", False
