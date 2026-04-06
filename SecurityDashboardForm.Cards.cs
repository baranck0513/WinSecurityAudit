// SecurityDashboardForm.Cards.cs
// builds the coloured result cards that appear in the main content area after a scan
// each card shows one security check's result including its status badge, risk explanation, and fix steps

namespace DissertationGUI
{
    public partial class SecurityDashboardForm
    {
        // builds a single result card from the list of output lines produced by one python check
        // outputLinesFromOneCheck is the exact text the python script printed, split into individual lines
        private Panel BuildCard(List<string> outputLinesFromOneCheck)
        {
            // ── step 1: figure out the result status of this check ───────────────────────────
            // scan the lines until we find the first one that contains "Status:" to get the result
            string checkResultStatus = "UNKNOWN";
            foreach (string line in outputLinesFromOneCheck)
            {
                if (line.Contains("Status: PASS"))  { checkResultStatus = "PASS";  break; }
                if (line.Contains("Status: FAIL"))  { checkResultStatus = "FAIL";  break; }
                if (line.Contains("Status: WARN"))  { checkResultStatus = "WARN";  break; }
                if (line.Contains("Status: ERROR")) { checkResultStatus = "ERROR"; break; }
            }

            // ── step 2: choose a colour scheme and badge text based on the status ─────────────
            // each status gets its own colour so the user can scan the results at a glance
            Color  leftBarColor;         // the thick vertical strip on the left edge of the card
            Color  statusTextColor;      // the colour of the PASS / FAIL / etc badge text
            Color  cardBackgroundColor;  // the background colour of the card itself
            Color  borderColor;          // the 1px outer border — lighter version of the left bar colour
            string statusBadgeText;      // the icon and word shown in the top-right of the card header

            switch (checkResultStatus)
            {
                case "PASS":
                    leftBarColor        = Color.Green;
                    statusTextColor     = Color.DarkGreen;
                    cardBackgroundColor = Color.White;
                    borderColor         = Color.LightGreen;
                    statusBadgeText     = "✓ PASS";
                    break;

                case "FAIL":
                    leftBarColor        = Color.Red;
                    statusTextColor     = Color.DarkRed;
                    cardBackgroundColor = Color.White;
                    borderColor         = Color.Pink;
                    statusBadgeText     = "✗ FAIL";
                    break;

                case "WARN":
                    leftBarColor        = Color.Orange;
                    statusTextColor     = Color.DarkOrange;
                    cardBackgroundColor = Color.White;
                    borderColor         = Color.LightYellow;
                    statusBadgeText     = "⚠ WARNING";
                    break;

                default:  // ERROR or UNKNOWN
                    leftBarColor        = Color.Purple;
                    statusTextColor     = Color.Purple;
                    cardBackgroundColor = Color.White;
                    borderColor         = Color.LightGray;
                    statusBadgeText     = "? ERROR";
                    break;
            }

            // ── step 3: the outer wrapper panel that creates the 1px coloured border 
            // the trick: the wrapper's BackColor is set to borderColor, and it has Padding=1 on all sides
            // so 1px of the wrapper's background shows through the padding and looks exactly like a border
            var outerBorderWrapperPanel = new Panel
            {
                BackColor = borderColor,
                Padding   = new Padding(1),
                Margin    = new Padding(0, 0, 0, 16),  // 16px gap below each card so they do not look cramped
            };

            // ── step 4: the inner card panel that holds all the visible content
            // AutoSizeMode.GrowAndShrink means the panel automatically gets taller as we add labels
            var innerCardPanel = new Panel
            {
                BackColor    = cardBackgroundColor,
                AutoSize     = true,
                AutoSizeMode = AutoSizeMode.GrowAndShrink,
            };
            outerBorderWrapperPanel.Controls.Add(innerCardPanel);

            // when the outer wrapper is resized (because the window width changed),
            // stretch the inner card to fill the wrapper's interior completely
            outerBorderWrapperPanel.Resize += (s, e) =>
            {
                innerCardPanel.Width = Math.Max(0, outerBorderWrapperPanel.ClientSize.Width);
            };

            // when the inner card grows taller as we add labels to it,
            // update the wrapper height to match — the +2 accounts for the 1px top and 1px bottom border
            innerCardPanel.SizeChanged += (s, e) =>
            {
                outerBorderWrapperPanel.Height = innerCardPanel.Height + 2;
            };

            // ── step 5: the coloured vertical strip on the left edge of every card
            // docking it to the left means it always stretches to the full height of the card automatically
            innerCardPanel.Controls.Add(new Panel
            {
                Width     = 6,
                Dock      = DockStyle.Left,
                BackColor = leftBarColor,
            });

            // ── step 6: the flow panel that holds all the text labels inside the card 
            // FlowDirection.TopDown stacks each new label below the previous one automatically
            var cardContentFlowPanel = new FlowLayoutPanel
            {
                FlowDirection = FlowDirection.TopDown,
                WrapContents  = false,
                BackColor     = Color.Transparent,
                Padding       = new Padding(16, 12, 16, 14),  // inner padding so text does not touch the edges
                AutoSize      = true,
                AutoSizeMode  = AutoSizeMode.GrowAndShrink,
                Dock          = DockStyle.Fill,
            };
            innerCardPanel.Controls.Add(cardContentFlowPanel);

            // ── step 7: the title row at the top of the card
            // a horizontal flow panel containing the check name on the left and the status badge on the right
            var titleRowWithNameAndBadge = new FlowLayoutPanel
            {
                FlowDirection = FlowDirection.LeftToRight,
                WrapContents  = false,
                BackColor     = Color.Transparent,
                AutoSize      = true,
                Margin        = new Padding(0, 0, 0, 0),
            };

            // the check name e.g. "Checking Antivirus status" — always the first line of python output
            titleRowWithNameAndBadge.Controls.Add(new Label
            {
                Text      = outputLinesFromOneCheck[0],
                ForeColor = Color.DarkBlue,
                Font      = new Font("Helvetica", 13, FontStyle.Bold),
                AutoSize  = true,
                Margin    = new Padding(0, 0, 12, 0),
                BackColor = Color.Transparent,
            });

            // the status badge e.g. "✓ PASS" or "✗ FAIL" — shown to the right of the check name
            titleRowWithNameAndBadge.Controls.Add(new Label
            {
                Text      = statusBadgeText,
                ForeColor = statusTextColor,
                Font      = new Font("Helvetica", 12, FontStyle.Bold),
                AutoSize  = true,
                Margin    = new Padding(0, 2, 0, 0),
                BackColor = Color.Transparent,
            });

            cardContentFlowPanel.Controls.Add(titleRowWithNameAndBadge);

            // ── step 8: a thin horizontal line separating the title from the detail text 
            // width=4000 ensures it always stretches across the full card — the flow panel clips it
            cardContentFlowPanel.Controls.Add(new Panel
            {
                Height    = 1,
                Width     = 4000,
                BackColor = borderColor,  // matches the card border for a subtle consistent look
                Margin    = new Padding(0, 8, 0, 10),
            });

            // ── step 9: the detail lines — description text, risk explanation, and fix steps 
            // we track whether we have entered the "How to fix:" section so fix steps get a different colour
            bool currentlyInsideFixInstructions = false;

            foreach (string rawLine in outputLinesFromOneCheck)
            {
                string lineWithoutLeadingOrTrailingSpaces = rawLine.Trim();

                // skip blank lines and lines that were already displayed in the title row above
                if (string.IsNullOrWhiteSpace(lineWithoutLeadingOrTrailingSpaces)) continue;
                if (lineWithoutLeadingOrTrailingSpaces.StartsWith("SCORE_LINE:"))  continue;  // internal scoring marker only
                if (lineWithoutLeadingOrTrailingSpaces.StartsWith("Checking "))    continue;  // already shown in title
                if (lineWithoutLeadingOrTrailingSpaces.Contains("Status: "))       continue;  // already shown in badge

                if (lineWithoutLeadingOrTrailingSpaces == "How to fix:")
                {
                    // this line marks the start of the numbered fix instructions section
                    currentlyInsideFixInstructions = true;
                    cardContentFlowPanel.Controls.Add(new Label
                    {
                        Text      = "How to fix:",
                        ForeColor = Color.Blue,  // blue heading for the fix section
                        Font      = new Font("Helvetica", 11, FontStyle.Bold),
                        AutoSize  = true,
                        Margin    = new Padding(0, 8, 0, 4),
                        BackColor = Color.Transparent,
                    });
                    continue;
                }

                // pick a colour for this line based on what kind of content it is
                Color colorForThisLineOfText;

                if (lineWithoutLeadingOrTrailingSpaces.StartsWith("Risk:"))
                {
                    // risk lines get an amber/brown colour and a warning icon prepended
                    colorForThisLineOfText                 = Color.Brown;
                    lineWithoutLeadingOrTrailingSpaces     = "⚠  Risk: " + lineWithoutLeadingOrTrailingSpaces.Substring(5).Trim();
                }
                else if (currentlyInsideFixInstructions)
                {
                    // numbered fix steps (e.g. "1. Open Settings > ...") get a dark blue colour
                    colorForThisLineOfText = Color.Navy;
                }
                else
                {
                    // all other detail lines (general description text) get a near-black colour for readability
                    colorForThisLineOfText = Color.Black;
                }

                cardContentFlowPanel.Controls.Add(new Label
                {
                    Text        = lineWithoutLeadingOrTrailingSpaces,
                    ForeColor   = colorForThisLineOfText,
                    Font        = new Font("Helvetica", 11),
                    AutoSize    = true,
                    MaximumSize = new Size(880, 0),  // caps the label width so long lines wrap instead of going off screen
                    Margin      = new Padding(0, 2, 0, 2),
                    BackColor   = Color.Transparent,
                });
            }

            // ── step 10: extract the scoring category so we know which fix to call ─────────
            // the SCORE_LINE format is: SCORE_LINE: STATUS:category  e.g. SCORE_LINE: FAIL:firewall
            string checkCategory = "";
            foreach (string line in outputLinesFromOneCheck)
            {
                string trimmed = line.Trim();
                if (trimmed.StartsWith("SCORE_LINE:"))
                {
                    string[] parts = trimmed.Substring("SCORE_LINE:".Length).Trim().Split(':');
                    if (parts.Length > 1)
                        checkCategory = parts[1].Trim().ToLower();
                    break;
                }
            }

            // ── step 11: add the "Auto Fix" button row to FAIL and WARN cards ────────────
            // PASS and ERROR cards do not get a fix button:
            //   PASS  — nothing to fix
            //   ERROR — the issue is likely a missing permission, not a configurable setting
            if ((checkResultStatus == "FAIL" || checkResultStatus == "WARN") && !string.IsNullOrEmpty(checkCategory))
            {
                // thin separator line above the button row to visually separate it from the detail text
                cardContentFlowPanel.Controls.Add(new Panel
                {
                    Height    = 1,
                    Width     = 4000,
                    BackColor = borderColor,
                    Margin    = new Padding(0, 10, 0, 10),
                });

                // the blue "Auto Fix" button — clicking it triggers the confirmation dialog in Fix.cs
                var fixButton = new Button
                {
                    Text      = "Auto Fix",
                    Width     = 120,
                    Height    = 32,
                    BackColor = Color.Blue,
                    ForeColor = Color.White,
                    Font      = new Font("Helvetica", 10, FontStyle.Bold),
                    FlatStyle = FlatStyle.Flat,
                    Cursor    = Cursors.Hand,
                    Margin    = new Padding(0, 0, 0, 4),
                };
                fixButton.FlatAppearance.BorderSize = 0;

                // the panel below the button that shows the fix outcome (success / fail / manual)
                // it starts hidden and is made visible only after a fix attempt
                var fixResultPanel = new Panel
                {
                    AutoSize     = true,
                    AutoSizeMode = AutoSizeMode.GrowAndShrink,
                    BackColor    = Color.Transparent,
                    Visible      = false,
                    Margin       = new Padding(0, 4, 0, 0),
                };

                // capture category in a local variable so the lambda closure holds the right value
                string capturedCategory = checkCategory;
                fixButton.Click += (s, e) => RunFix(capturedCategory, fixButton, fixResultPanel);

                cardContentFlowPanel.Controls.Add(fixButton);
                cardContentFlowPanel.Controls.Add(fixResultPanel);
            }

            return outerBorderWrapperPanel;
        }

        // displays a plain text message as a single label in the cards area
        // used for error messages like "Could not start the Python scanner"
        private void ShowTextCard(string textMessageToDisplay, Color textColor)
        {
            var simpleTextLabel = new Label
            {
                Text      = textMessageToDisplay,
                ForeColor = textColor,
                Font      = new Font("Helvetica", 11),
                AutoSize  = true,
                Margin    = new Padding(0, 4, 0, 4),
                BackColor = Color.Transparent,
                Width     = cardsPanel.ClientSize.Width - 4,
            };
            cardsPanel.Controls.Add(simpleTextLabel);
        }
    }
}
