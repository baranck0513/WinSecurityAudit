// SecurityDashboardForm.Score.cs
// defines how much each security check contributes to the overall score
// and calculates the final 0-100 score after a full scan finishes
// a higher weight means that check has a bigger impact on the final number

namespace DissertationGUI
{
    public partial class SecurityDashboardForm
    {
        // ── how much each check category is worth ─────────────────────────────────────
        // the key is the category name that appears in the SCORE_LINE output from the python checks
        // the value is how many "points" this category is worth relative to all the others
        // critical checks (antivirus, firewall) get higher weights because failing them is the most dangerous
        // lower-risk checks (usb_autorun, services) get lower weights because the threat is more narrow
        private static readonly Dictionary<string, double> SecurityCheckWeightByCategory = new Dictionary<string, double>()
        {
            ["antivirus"]      = 3.0,   // critical  — no antivirus means malware can run completely undetected
            ["firewall"]       = 3.0,   // critical  — blocks unauthorised inbound connections from outside the machine
            ["windows_update"] = 2.5,   // important — regular patches close known vulnerabilities before attackers use them
            ["password"]       = 2.0,   // moderate  — weak or missing passwords are one of the most exploited entry points
            ["uac"]            = 1.5,   // moderate  — stops programs from making silent admin-level changes
            ["smartscreen"]    = 1.5,   // moderate  — blocks malicious downloads and unrecognised applications
            ["usb_autorun"]    = 1.0,   // low       — reduces the risk of malware spreading via USB drives
            ["services"]       = 1.0,   // low       — unnecessary services widen the network attack surface
        };

        // ── score calculation ─────────────────────────────────────────────────────────
        // reads all the SCORE_LINE entries that the python checks printed to stdout
        // calculates a weighted percentage score from 0 to 100
        // then updates the score label in the header with the result and a colour-coded rating
        private void UpdateScore(string fullScanOutputText)
        {
            // step 1: go through every line of the full scan output and collect SCORE_LINE entries
            // each SCORE_LINE tells us the result (PASS/WARN/FAIL) for one specific check category
            var eachCheckStatusAndWeight = new Dictionary<string, (string status, double weight)>();

            foreach (string singleOutputLine in fullScanOutputText.Split('\n'))
            {
                string lineWithoutWhitespace = singleOutputLine.Trim();

                // skip any line that is not a SCORE_LINE — only scoring lines are relevant here
                if (!lineWithoutWhitespace.StartsWith("SCORE_LINE:"))
                {
                    continue;
                }

                // the expected format from python is: SCORE_LINE:STATUS:category
                // e.g. SCORE_LINE:PASS:antivirus   or   SCORE_LINE:FAIL:firewall
                string[] scoreParts        = lineWithoutWhitespace.Substring("SCORE_LINE:".Length).Trim().Split(':');
                string   thisCheckStatus   = scoreParts[0].Trim().ToUpper();
                string   thisCheckCategory = scoreParts.Length > 1 ? scoreParts[1].Trim().ToLower() : "unknown";

                // look up the weight for this category in our table
                // if the category is not in the table (e.g. a future new check), fall back to weight 1.0
                if (!SecurityCheckWeightByCategory.TryGetValue(thisCheckCategory, out double thisCheckWeight))
                {
                    thisCheckWeight = 1.0;
                }

                // only record the first result for each category — ignore duplicate lines if any exist
                if (!eachCheckStatusAndWeight.ContainsKey(thisCheckCategory))
                {
                    eachCheckStatusAndWeight[thisCheckCategory] = (thisCheckStatus, thisCheckWeight);
                }
            }

            // if we found no SCORE_LINE entries at all, there is nothing to calculate so bail out early
            if (eachCheckStatusAndWeight.Count == 0)
            {
                return;
            }

            // step 2: calculate the weighted score using the results we collected
            // scoring rules:
            //   PASS  = earns the full weight for that category   (1.0 × weight)
            //   WARN  = earns half the weight for that category   (0.5 × weight)
            //   FAIL or ERROR = earns nothing                     (0.0 × weight)
            double totalWeightedPointsEarned = 0;
            double sumOfAllCheckWeights      = 0;

            foreach (var singleCheckResult in eachCheckStatusAndWeight.Values)
            {
                double pointsEarnedForThisStatus = singleCheckResult.status switch
                {
                    "PASS" => 1.0,
                    "WARN" => 0.5,
                    _      => 0.0,  // FAIL, ERROR, or anything unexpected earns zero points
                };
                totalWeightedPointsEarned += pointsEarnedForThisStatus * singleCheckResult.weight;
                sumOfAllCheckWeights      += singleCheckResult.weight;
            }

            // divide points earned by the maximum possible points to get a 0-100 percentage
            int overallSecurityScore = (int)Math.Round(totalWeightedPointsEarned / sumOfAllCheckWeights * 100);

            // step 3: pick a colour and a rating label based on how good the score is
            Color  colorForTheScoreLabel;
            string ratingLabel;

            if (overallSecurityScore >= 85)
            {
                colorForTheScoreLabel = Color.Lime;
                ratingLabel           = "Excellent";
            }
            else if (overallSecurityScore >= 65)
            {
                colorForTheScoreLabel = Color.Yellow;
                ratingLabel           = "Good";
            }
            else if (overallSecurityScore >= 40)
            {
                colorForTheScoreLabel = Color.DarkOrange;
                ratingLabel           = "Fair";
            }
            else
            {
                colorForTheScoreLabel = Color.Red;
                ratingLabel           = "Poor";
            }

            // step 4: update the score label in the header with the final result
            scoreLabel.ForeColor = colorForTheScoreLabel;
            scoreLabel.Text      = $"Score: {overallSecurityScore}/100 ({ratingLabel})";
            // reposition the label so it always sits neatly to the left of the Start Scan button
            scoreLabel.Left      = startScanButton.Left - scoreLabel.Width - 20;
        }
    }
}
