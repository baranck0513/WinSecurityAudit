// SecurityDashboardForm.Header.cs
// builds the dark-blue bar that runs across the top of the window
// it holds three things: the scan type title on the left, the security score in the middle,
// and the green "Start Scan" button pinned to the right

namespace DissertationGUI
{
    public partial class SecurityDashboardForm
    {
        // ── header panel ───────────────────────────────────────────────────────────────
        // the dark-blue bar at the top showing which scan is selected, the score, and the button

        private void BuildHeader()
        {
            headerPanel = new Panel
            {
                BackColor = Color.DarkBlue,  // dark blue background
                Height    = 68,
                Dock      = DockStyle.Top,
            };

            // the title label on the left shows which scan type is currently selected in the sidebar
            // it updates every time the user clicks a different sidebar item
            titleLabel = new Label
            {
                Text      = chosenScanTypeName,  // starts as "Full Scan" which is the default selection
                ForeColor = Color.White,
                Font      = new Font("Helvetica", 17, FontStyle.Bold),
                AutoSize  = true,
                Location  = new Point(22, 18),
                BackColor = Color.Transparent,
            };
            headerPanel.Controls.Add(titleLabel);

            // the green "Start Scan" button on the right — clicking it launches the python scanner process
            // Anchor keeps it pinned to the top-right corner when the window is resized
            startScanButton = new Button
            {
                Text      = "Start Scan",
                Width     = 140,
                Height    = 38,
                BackColor = Color.DarkGreen,
                ForeColor = Color.White,
                Font      = new Font("Helvetica", 11, FontStyle.Bold),
                FlatStyle = FlatStyle.Flat,
                Cursor    = Cursors.Hand,
                Anchor    = AnchorStyles.Top | AnchorStyles.Right,
            };
            startScanButton.FlatAppearance.BorderSize = 0;  // remove the default button border for a clean flat look
            startScanButton.Location = new Point(headerPanel.Width - startScanButton.Width - 18, 15);
            startScanButton.Click   += StartScanButton_Click;  // the click handler lives in SecurityDashboardForm.Scan.cs
            headerPanel.Controls.Add(startScanButton);

            // the score label sits between the title and the button
            // it starts empty and gets filled in by UpdateScore() in SecurityDashboardForm.Score.cs
            // after a full scan finishes — e.g. "Score: 72/100 (Good)"
            scoreLabel = new Label
            {
                Text      = "",
                ForeColor = Color.White,
                Font      = new Font("Helvetica", 13, FontStyle.Bold),
                AutoSize  = true,
                Anchor    = AnchorStyles.Top | AnchorStyles.Right,
                Location  = new Point(headerPanel.Width - 340, 23),
                BackColor = Color.Transparent,
            };
            headerPanel.Controls.Add(scoreLabel);

            // whenever the window is resized, keep the button pinned to the right edge
            // and reposition the score label so it always sits just to the left of the button
            headerPanel.Resize += (s, e) =>
            {
                startScanButton.Left = headerPanel.Width - startScanButton.Width - 18;
                scoreLabel.Left      = startScanButton.Left - scoreLabel.Width - 20;
            };
        }
    }
}
