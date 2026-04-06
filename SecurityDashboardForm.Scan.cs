// SecurityDashboardForm.Scan.cs
// handles the "Start Scan" button click
// launches dissertation.py as a child process and streams its stdout line by line
// each result card is rendered immediately when that check's blank-line boundary arrives
// so the user sees cards appearing one by one instead of waiting for everything to finish

using System.Diagnostics;

namespace DissertationGUI
{
    public partial class SecurityDashboardForm
    {
        // called when the user clicks the green "Start Scan" button
        // async void is acceptable here because this is a UI event handler — it is never awaited by a caller
        // using async/await means the UI thread stays free to repaint and respond to resize events
        // while the actual reading of python's output happens on a background thread
        private async void StartScanButton_Click(object sender, EventArgs e)
        {
            // clear any cards from a previous scan and reset the display to a blank state
            cardsPanel.Controls.Clear();
            scoreLabel.Text         = "";
            startScanButton.Enabled = false;
            startScanButton.Text    = "Scanning...";

            bool userSelectedFullScan          = chosenScanTypeName == "Full Scan";
            int  totalNumberOfChecksInFullScan  = 8;   // how many individual checks dissertation.py runs in a Full Scan
            int  numberOfChecksCompleted        = 0;

            // only show the progress bar for Full Scan — individual checks finish too quickly for a bar to be useful
            if (userSelectedFullScan)
            {
                scanProgressBar.Value   = 0;
                progressCountLabel.Text = $"0 / {totalNumberOfChecksInFullScan} checks complete";
                progressPanel.Visible   = true;
            }

            // decide whether to call the extracted backend exe (published mode) or python directly (dev mode)
            // Program.BackendExePath is set at startup by ExtractBackendExe() in Program.cs:
            //   published exe  → BackendExePath = "C:\Users\...\AppData\Local\Temp\DissertationBackend\dissertation.exe"
            //   dotnet run     → BackendExePath = ""  (resource not embedded, fall back to python)
            bool isPublishedMode = !string.IsNullOrEmpty(Program.BackendExePath);

            // in published mode the extracted exe is called directly with the scan type as the only argument
            // in dev mode python is called with -u (unbuffered) so each print() flushes immediately to C#
            // without -u python would buffer internally and the progress bar would jump from 0% to 100% at the end
            var pythonLaunchSettings = new ProcessStartInfo
            {
                FileName               = isPublishedMode ? Program.BackendExePath : "python",
                Arguments              = isPublishedMode ? $"\"{chosenScanTypeName}\""
                                                         : $"-u dissertation.py \"{chosenScanTypeName}\"",
                RedirectStandardOutput = true,   // we read stdout ourselves line by line
                RedirectStandardError  = true,   // we also capture stderr so python errors appear in the UI
                UseShellExecute        = false,   // required whenever we redirect output streams
                CreateNoWindow         = true,    // run silently without a visible terminal window
            };

            // linesForCurrentCheck collects the output lines that belong to the check currently being processed
            // when a blank line arrives (dissertation.py prints one after every check), we flush these into a card
            var linesForCurrentCheck        = new List<string>();
            var fullOutputFromPythonProcess = new System.Text.StringBuilder();
            var stderrOutputCollector       = new System.Text.StringBuilder();
            bool failedToStartPythonProcess = false;

            try
            {
                // Task.Run moves the blocking stdout-read loop off the UI thread
                // without this, the window would freeze and turn white during the scan
                await Task.Run(() =>
                {
                    var runningPythonProcess = Process.Start(pythonLaunchSettings);
                    if (runningPythonProcess == null)
                    {
                        failedToStartPythonProcess = true;
                        return;
                    }

                    // read stderr on a separate async thread to stop its buffer from filling up
                    // a full stderr buffer would block the python process before stdout finishes
                    runningPythonProcess.ErrorDataReceived += (s2, args) =>
                    {
                        if (args.Data != null) stderrOutputCollector.AppendLine(args.Data);
                    };
                    runningPythonProcess.BeginErrorReadLine();

                    // read stdout one line at a time — this works because we launched python with -u
                    // so each print() flushes immediately rather than waiting for an internal buffer to fill
                    // dissertation.py prints a blank line after every check which we use as the card boundary
                    string rawOutputLine;
                    while ((rawOutputLine = runningPythonProcess.StandardOutput.ReadLine()) != null)
                    {
                        string currentLineWithoutTrailingWhitespace = rawOutputLine.TrimEnd();
                        fullOutputFromPythonProcess.AppendLine(currentLineWithoutTrailingWhitespace);

                        // Invoke marshals the UI update back to the main (UI) thread
                        // winforms controls can only be safely touched from the thread that created them
                        // blocking = Invoke waits for the UI update to finish before reading the next line
                        this.Invoke((Action)(() =>
                        {
                            if (string.IsNullOrEmpty(currentLineWithoutTrailingWhitespace) && linesForCurrentCheck.Count > 0)
                            {
                                // a blank line signals that one check has completely finished
                                // build its card right now and add it to the panel so the user can see it immediately
                                var newlyBuiltResultCard = BuildCard(new List<string>(linesForCurrentCheck));
                                cardsPanel.Controls.Add(newlyBuiltResultCard);
                                newlyBuiltResultCard.Width = cardsPanel.ClientSize.Width - 4;
                                // scroll down so the newest card is always visible to the user
                                cardsPanel.ScrollControlIntoView(newlyBuiltResultCard);
                                linesForCurrentCheck.Clear();

                                if (userSelectedFullScan)
                                {
                                    numberOfChecksCompleted++;
                                    // cap at 100 so the ProgressBar never receives an out-of-range value
                                    // if a python check accidentally emits an extra blank line,
                                    // numberOfChecksCompleted could exceed totalNumberOfChecksInFullScan
                                    // and the raw percentage would be > 100, which crashes the ProgressBar
                                    int progressBarPercentage = Math.Min(
                                        (int)(numberOfChecksCompleted * 100.0 / totalNumberOfChecksInFullScan), 100);

                                    // windows ProgressBar has a built-in animation that lags behind the real value
                                    // setting value to percentage+1 then immediately back to percentage forces an instant repaint
                                    // without this trick the bar might still show 50% when it should already show 75%
                                    scanProgressBar.Value   = Math.Min(progressBarPercentage + 1, 100);
                                    scanProgressBar.Value   = progressBarPercentage;
                                    progressCountLabel.Text = $"{Math.Min(numberOfChecksCompleted, totalNumberOfChecksInFullScan)} / {totalNumberOfChecksInFullScan} checks complete";
                                }
                            }
                            else if (!string.IsNullOrEmpty(currentLineWithoutTrailingWhitespace))
                            {
                                // a non-blank line belongs to the check currently being processed — accumulate it
                                linesForCurrentCheck.Add(currentLineWithoutTrailingWhitespace);
                            }
                        }));
                    }

                    runningPythonProcess.WaitForExit();
                });

                if (failedToStartPythonProcess)
                {
                    ShowTextCard("Could not start the Python scanner.", Color.Red);
                    return;
                }

                // safety net: if the very last check's lines never got flushed by a trailing blank line, flush them now
                if (linesForCurrentCheck.Count > 0)
                {
                    var newlyBuiltResultCard = BuildCard(new List<string>(linesForCurrentCheck));
                    cardsPanel.Controls.Add(newlyBuiltResultCard);
                    newlyBuiltResultCard.Width = cardsPanel.ClientSize.Width - 4;
                }

                // if python wrote anything to stderr (e.g. a syntax error or import failure), show it in the UI
                string stderrErrorOutput = stderrOutputCollector.ToString();
                if (!string.IsNullOrWhiteSpace(stderrErrorOutput))
                {
                    ShowTextCard("Warning: " + stderrErrorOutput, Color.Red);
                }

                if (fullOutputFromPythonProcess.Length == 0)
                {
                    ShowTextCard("No output received from the scanner.", Color.Red);
                }

                if (userSelectedFullScan)
                {
                    // force the bar to 100% and update the label in case the numbers are slightly off
                    scanProgressBar.Value   = 100;
                    progressCountLabel.Text = $"{totalNumberOfChecksInFullScan} / {totalNumberOfChecksInFullScan} checks complete";

                    // calculate and display the overall weighted security score
                    UpdateScore(fullOutputFromPythonProcess.ToString());

                    // wait 1.5 seconds so the user can see the completed bar before we hide the progress strip
                    await Task.Delay(1500);
                    progressPanel.Visible = false;
                }
            }
            catch (Exception unexpectedError)
            {
                ShowTextCard("Error launching scanner: " + unexpectedError.Message, Color.Red);
            }
            finally
            {
                // always re-enable the start button when we are done, even if something went wrong
                startScanButton.Enabled = true;
                startScanButton.Text    = "Start Scan";
            }
        }
    }
}
