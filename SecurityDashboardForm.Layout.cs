// SecurityDashboardForm.Layout.cs
// builds the main scrollable content area, the progress bar strip, and the placeholder message
// the content area is where result cards appear one by one as each check finishes

namespace DissertationGUI
{
    public partial class SecurityDashboardForm
    {
        // ── main content area ──────────────────────────────────────────────────────────
        // the grey scrollable panel in the centre of the window where result cards are stacked

        private void BuildContent()
        {
            // mainContentPanel is a wrapper that fills all remaining space after the sidebar and header
            // the slight grey colour makes white and tinted result cards stand out more clearly
            mainContentPanel = new Panel
            {
                Dock      = DockStyle.Fill,
                BackColor = Color.LightGray,  // light grey background
                Padding   = new Padding(20, 16, 20, 16),
            };

            // cardsPanel is a flow panel that stacks result cards vertically from top to bottom
            // AutoScroll = true means a scrollbar appears automatically if the cards overflow the visible area
            cardsPanel = new FlowLayoutPanel
            {
                Dock          = DockStyle.Fill,
                AutoScroll    = true,
                FlowDirection = FlowDirection.TopDown,  // new cards go below the previous ones
                WrapContents  = false,
                BackColor     = Color.LightGray,
            };

            // whenever the user resizes the window, stretch every existing result card to fill the new width
            // subtracting 4 pixels accounts for the scrollbar so cards do not end up hidden behind it
            cardsPanel.Resize += (s, e) =>
            {
                foreach (Control resultCard in cardsPanel.Controls)
                    resultCard.Width = cardsPanel.ClientSize.Width - 4;
            };

            mainContentPanel.Controls.Add(cardsPanel);
        }

        // ── progress bar area ──────────────────────────────────────────────────────────
        // a thin strip shown just below the header only while a full scan is running
        // it holds a green progress bar on the left and a "X / 8 checks complete" counter on the right

        private void BuildProgressArea()
        {
            // the progress panel is hidden by default and only made visible when a full scan starts
            progressPanel = new Panel
            {
                Height    = 30,
                Dock      = DockStyle.Top,
                BackColor = Color.DarkBlue,  // slightly darker blue than the header
                Visible   = false,
            };

            // the green progress bar that fills from left to right as each check completes
            // ProgressBarStyle.Continuous gives a smooth fill instead of the segmented windows default style
            scanProgressBar = new ProgressBar
            {
                Height  = 10,
                Minimum = 0,
                Maximum = 100,
                Value   = 0,
                Style   = ProgressBarStyle.Continuous,
            };
            progressPanel.Controls.Add(scanProgressBar);

            // the "X / 8 checks complete" counter label shown to the right of the progress bar
            progressCountLabel = new Label
            {
                Text      = "",
                ForeColor = Color.LightBlue,  // light blue text that is readable on the dark strip
                Font      = new Font("Helvetica", 10),
                AutoSize  = true,
                BackColor = Color.Transparent,
            };
            progressPanel.Controls.Add(progressCountLabel);

            // whenever the progress panel is resized (because the window was resized),
            // recalculate the position of the bar and label so they stay properly aligned
            progressPanel.Resize += (s, e) =>
            {
                int panelHeight = progressPanel.ClientSize.Height;
                int panelWidth  = progressPanel.ClientSize.Width;

                // vertically centre the count label within the progress strip
                progressCountLabel.Top  = (panelHeight - progressCountLabel.Height) / 2;
                // push the count label 22 pixels from the right edge
                progressCountLabel.Left = panelWidth - progressCountLabel.Width - 22;

                // vertically centre the progress bar too
                scanProgressBar.Top   = (panelHeight - scanProgressBar.Height) / 2;
                scanProgressBar.Left  = 22;  // 22 pixels from the left edge
                // the bar fills all the space between its left position and the label, with a 44px gap total
                scanProgressBar.Width = Math.Max(50, progressCountLabel.Left - 44);
            };
        }

        // shows a friendly "press Start Scan to begin" message before the user has run any scan
        // also called every time the user switches to a different scan type in the sidebar
        private void ShowPlaceholder()
        {
            cardsPanel.Controls.Clear();  // remove any result cards left over from the previous scan

            var readyToScanPromptLabel = new Label
            {
                Text      = $"Press 'Start Scan' to begin: {chosenScanTypeName}",
                ForeColor = Color.Gray,  // muted grey so it does not look like a result card
                Font      = new Font("Helvetica", 11),
                Height    = 80,
                Dock      = DockStyle.Top,
                TextAlign = ContentAlignment.MiddleCenter,
                BackColor = Color.Transparent,
                Width     = cardsPanel.ClientSize.Width - 4,
            };
            cardsPanel.Controls.Add(readyToScanPromptLabel);
        }
    }
}
