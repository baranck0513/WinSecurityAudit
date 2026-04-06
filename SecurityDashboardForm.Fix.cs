// SecurityDashboardForm.Fix.cs
// handles the automated fix logic triggered by the "Auto Fix" button on result cards
// shows the user a clear confirmation dialog before making any changes,
// then launches dissertation.py with a "Fix:CheckName" argument and displays the outcome

using System.Diagnostics;

namespace DissertationGUI
{
    public partial class SecurityDashboardForm
    {
        // maps each scoring category key (as it appears after "SCORE_LINE: STATUS:" in Python output)
        // to the exact check name that dissertation.py expects after the "Fix:" prefix
        private static readonly Dictionary<string, string> FixArgumentByCategory = new Dictionary<string, string>()
        {
            ["firewall"]       = "Firewall",
            ["windows_update"] = "Windows Update",
            ["uac"]            = "User Account Control",
            ["usb_autorun"]    = "USB Autorun",
            ["smartscreen"]    = "SmartScreen",
            ["services"]       = "Unnecessary Services",
            ["antivirus"]      = "Antivirus",
            ["password"]       = "Password",
        };

        // the confirmation message shown to the user before each fix is applied
        // each message explains exactly what will change and flags any important side effects
        // the user must click Yes before a single change is made to their system
        private static readonly Dictionary<string, string> FixConfirmationMessageByCategory = new Dictionary<string, string>()
        {
            ["firewall"] =
                "This will enable Windows Firewall for all network profiles\n" +
                "(Domain, Private, and Public).\n\n" +
                "Do you want to apply this fix?",

            ["windows_update"] =
                "This will enable automatic Windows updates and start\n" +
                "the Windows Update service.\n\n" +
                "Do you want to apply this fix?",

            ["uac"] =
                "This will enable User Account Control (UAC) and set it\n" +
                "to 'Always Notify' with secure desktop protection.\n\n" +
                "⚠  A system restart will be required for this change\n" +
                "    to take full effect.\n\n" +
                "Do you want to apply this fix?",

            ["usb_autorun"] =
                "This will disable AutoPlay so USB drives and removable\n" +
                "media cannot run programs automatically when plugged in.\n\n" +
                "Do you want to apply this fix?",

            ["smartscreen"] =
                "This will set Windows SmartScreen to 'Block' mode.\n" +
                "Unrecognised files and apps downloaded from the internet\n" +
                "will be blocked before they can run.\n\n" +
                "Do you want to apply this fix?",

            ["services"] =
                "This will stop and disable the following risky services:\n" +
                "  •  Remote Registry\n" +
                "  •  Telnet\n" +
                "  •  FTP Service (IIS)\n" +
                "  •  World Wide Web Publishing Service (IIS)\n" +
                "  •  Windows Remote Management\n\n" +
                "⚠  Remote Desktop Services will NOT be changed to avoid\n" +
                "    disconnecting your current session. Disable it manually\n" +
                "    via services.msc if you do not need it.\n\n" +
                "Do you want to apply this fix?",

            ["antivirus"] =
                "This will re-enable Windows Defender real-time protection.\n\n" +
                "⚠  If you use third-party antivirus software, it cannot\n" +
                "    be re-enabled automatically. Please open it manually.\n\n" +
                "Do you want to apply this fix?",

            ["password"] =
                "A password cannot be set automatically for security reasons.\n\n" +
                "Clicking Yes will open the Windows Sign-in settings page\n" +
                "where you can set a password or PIN manually.\n\n" +
                "Do you want to open Sign-in settings?",
        };

        // called when the user clicks the "Auto Fix" button on a result card
        //   category      — the scoring key e.g. "firewall" or "uac"
        //   fixButton     — the button that was clicked, so we can update its state
        //   resultPanel   — the panel below the button where we display the outcome message
        private async void RunFix(string category, Button fixButton, Panel resultPanel)
        {
            // guard: both dictionaries must have an entry for this category
            if (!FixConfirmationMessageByCategory.TryGetValue(category, out string? confirmationMessage))
            {
                return;
            }
            if (!FixArgumentByCategory.TryGetValue(category, out string? fixArgument))
            {
                return;
            }

            // ── step 1: show the confirmation dialog ────────────────────────────────────
            // default button is "No" so the user has to actively choose Yes — prevents accidental fixes
            var userChoice = MessageBox.Show(
                confirmationMessage,
                "Confirm Automated Fix",
                MessageBoxButtons.YesNo,
                MessageBoxIcon.Question,
                MessageBoxDefaultButton.Button2
            );

            if (userChoice != DialogResult.Yes)
            {
                return;
            }

            // ── step 2: lock the button and show a "Fixing..." state ─────────────────────
            fixButton.Enabled   = false;
            fixButton.Text      = "Fixing...";
            fixButton.BackColor = Color.Gray;  // grey while in progress

            // clear any result from a previous attempt on this card
            resultPanel.Controls.Clear();
            resultPanel.Visible = true;

            string fixResult  = "FAIL";
            string fixMessage = "An unexpected error occurred.";

            try
            {
                // ── step 3: launch the backend with the Fix: argument ────────────────────
                // same published-vs-dev logic as Scan.cs:
                //   published exe  → call the extracted dissertation.exe directly
                //   dotnet run     → fall back to "python -u dissertation.py"
                bool isPublishedMode = !string.IsNullOrEmpty(Program.BackendExePath);

                var fixLaunchSettings = new ProcessStartInfo
                {
                    FileName               = isPublishedMode ? Program.BackendExePath : "python",
                    Arguments              = isPublishedMode ? $"\"Fix:{fixArgument}\""
                                                             : $"-u dissertation.py \"Fix:{fixArgument}\"",
                    RedirectStandardOutput = true,
                    RedirectStandardError  = true,
                    UseShellExecute        = false,
                    CreateNoWindow         = true,
                };

                await Task.Run(() =>
                {
                    var fixProcess = Process.Start(fixLaunchSettings);
                    if (fixProcess == null) return;

                    // drain stderr so its buffer never fills and blocks the process
                    fixProcess.ErrorDataReceived += (s, args) => { };
                    fixProcess.BeginErrorReadLine();

                    // read the two output lines: FIX_RESULT and FIX_MESSAGE
                    string? outputLine;
                    while ((outputLine = fixProcess.StandardOutput.ReadLine()) != null)
                    {
                        string trimmed = outputLine.Trim();
                        if (trimmed.StartsWith("FIX_RESULT:"))
                            fixResult = trimmed.Substring("FIX_RESULT:".Length).Trim();
                        else if (trimmed.StartsWith("FIX_MESSAGE:"))
                            fixMessage = trimmed.Substring("FIX_MESSAGE:".Length).Trim();
                    }

                    fixProcess.WaitForExit();
                });
            }
            catch (Exception ex)
            {
                fixResult  = "FAIL";
                fixMessage = "Could not launch the fix: " + ex.Message;
            }

            // ── step 4: update the button and show the outcome message ───────────────────
            Color  resultColor;
            string resultIcon;

            switch (fixResult)
            {
                case "SUCCESS":
                    resultColor         = Color.DarkGreen;
                    resultIcon          = "✓  ";
                    fixButton.Text      = "Fix Applied";
                    fixButton.BackColor = Color.DarkGreen;
                    break;

                case "MANUAL":
                    resultColor         = Color.Blue;
                    resultIcon          = "ℹ  ";
                    fixButton.Text      = "Settings Opened";
                    fixButton.BackColor = Color.Blue;
                    break;

                default:  // FAIL
                    resultColor         = Color.DarkRed;
                    resultIcon          = "✗  ";
                    fixButton.Text      = "⚙  Auto Fix";   // restore so user can retry
                    fixButton.BackColor = Color.Blue;
                    fixButton.Enabled   = true;
                    break;
            }

            resultPanel.Controls.Add(new Label
            {
                Text        = resultIcon + fixMessage,
                ForeColor   = resultColor,
                Font        = new Font("Helvetica", 10),
                AutoSize    = true,
                MaximumSize = new Size(860, 0),  // wrap long messages instead of going off-screen
                BackColor   = Color.Transparent,
                Margin      = new Padding(0),
            });
        }
    }
}
