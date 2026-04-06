// SecurityDashboardForm.Sidebar.cs
// builds the dark navigation panel on the left side of the window
// each item in the sidebar represents one scan option the user can choose
// clicking an item highlights it in blue and updates the scan type shown in the header

namespace DissertationGUI
{
    public partial class SecurityDashboardForm
    {
        // ── sidebar panel ──────────────────────────────────────────────────────────────
        // the dark panel docked to the left lets users pick which check (or all checks) to run

        private void BuildSidebar()
        {
            sidebarPanel = new Panel
            {
                BackColor = Color.DarkBlue,  // dark navy background
                Width     = 260,
                Dock      = DockStyle.Left,
            };

            // these are the names of all the available scan types shown in the sidebar
            // "Full Scan" runs every check at once — the others each run only one specific check
            // the names must exactly match the keys in the dissertation.py checks dictionary
            string[] availableScanOptionNames =
            {
                "Full Scan", "Windows Update", "Password", "Antivirus",
                "Firewall", "Unnecessary Services",
                "USB Autorun", "User Account Control", "SmartScreen"
            };

            // create one clickable row in the sidebar for each scan option name
            foreach (string scanOptionName in availableScanOptionNames)
                AddSidebarItem(scanOptionName);
        }

        // creates one clickable label row inside the sidebar for a given scan option name
        private void AddSidebarItem(string scanOptionName)
        {
            var sidebarRowLabel = new Label
            {
                Text      = "  " + scanOptionName,  // two leading spaces give a small left indent
                ForeColor = Color.Gray,  // grey text when the item is not selected
                Font      = new Font("Helvetica", 12),
                Height    = 62,
                Dock      = DockStyle.Top,
                TextAlign = ContentAlignment.MiddleLeft,
                BackColor = Color.DarkBlue,
                Cursor    = Cursors.Hand,  // pointer cursor so the user knows each row is clickable
            };

            // slightly lighten the row background when the cursor moves over it
            // this gives visual feedback that the row is interactive
            sidebarRowLabel.MouseEnter += (s, e) =>
            {
                if (sidebarRowLabel != currentlyHighlightedSidebarLabel)
                    sidebarRowLabel.BackColor = Color.Navy;
            };

            // restore the default dark background when the cursor leaves the row
            sidebarRowLabel.MouseLeave += (s, e) =>
            {
                if (sidebarRowLabel != currentlyHighlightedSidebarLabel)
                    sidebarRowLabel.BackColor = Color.DarkBlue;
            };

            sidebarRowLabel.Click += SidebarItem_Click;

            sidebarPanel.Controls.Add(sidebarRowLabel);

            // SetChildIndex(0) keeps items in the order they were added
            // without this, DockStyle.Top would stack them in reverse order (last added at the top)
            sidebarPanel.Controls.SetChildIndex(sidebarRowLabel, 0);

            // "Full Scan" is pre-selected and highlighted when the app first opens
            if (scanOptionName == "Full Scan")
                SetActiveLabel(sidebarRowLabel);
        }

        // visually marks the given sidebar label as the currently selected item
        // first it resets the previously selected item back to its normal appearance
        // then it applies the blue background, white bold text, and a bright accent bar to the new selection
        private void SetActiveLabel(Label theLabelToHighlightAsActive)
        {
            // reset the previously highlighted item back to its unselected appearance first
            if (currentlyHighlightedSidebarLabel != null)
            {
                currentlyHighlightedSidebarLabel.BackColor = Color.DarkBlue;
                currentlyHighlightedSidebarLabel.ForeColor = Color.Gray;
                currentlyHighlightedSidebarLabel.Font      = new Font("Helvetica", 12);

                // remove the thin blue accent bar that was drawn on its left edge when it was selected
                // we stored it in the label's Tag property when we created it so we can find it again
                if (currentlyHighlightedSidebarLabel.Tag is Panel previousAccentBarToRemove)
                {
                    sidebarPanel.Controls.Remove(previousAccentBarToRemove);
                    previousAccentBarToRemove.Dispose();  // release the memory the old accent bar was using
                    currentlyHighlightedSidebarLabel.Tag = null;
                }
            }

            // apply the selected highlight style to the newly chosen item
            currentlyHighlightedSidebarLabel              = theLabelToHighlightAsActive;
            theLabelToHighlightAsActive.BackColor = Color.DarkBlue;  // blue highlight
            theLabelToHighlightAsActive.ForeColor = Color.White;
            theLabelToHighlightAsActive.Font      = new Font("Helvetica", 12, FontStyle.Bold);

            // draw a narrow 3-pixel bright blue bar along the very left edge of the selected row
            // this is a common UI pattern (used in VS Code, Slack etc) to show which item is active
            var blueAccentBarOnLeftEdge = new Panel
            {
                Width     = 3,
                Height    = theLabelToHighlightAsActive.Height,
                BackColor = Color.Blue,  // bright blue
                Location  = new Point(theLabelToHighlightAsActive.Left, theLabelToHighlightAsActive.Top),
            };
            blueAccentBarOnLeftEdge.BringToFront();

            // store the accent bar in the label's Tag property so we can find and remove it
            // the next time a different item is selected
            theLabelToHighlightAsActive.Tag = blueAccentBarOnLeftEdge;
            sidebarPanel.Controls.Add(blueAccentBarOnLeftEdge);
        }

        // called every time the user clicks any item in the sidebar
        // it highlights the clicked item, updates the chosen scan type, and resets the content area
        private void SidebarItem_Click(object sender, EventArgs e)
        {
            var theLabelThatWasClicked = (Label)sender;
            SetActiveLabel(theLabelThatWasClicked);

            // Trim() removes the two leading spaces we added when creating the label text
            chosenScanTypeName = theLabelThatWasClicked.Text.Trim();
            titleLabel.Text    = chosenScanTypeName;

            // clear any previous scan results and show the "ready to scan" placeholder message
            ShowPlaceholder();
        }
    }
}
