// DissertationGUI — windows security dashboard
// this file is the entry point of the application and the shell of the main form
// the actual UI logic is split across separate partial-class files — search "SecurityDashboardForm." to find them
// using partial class lets us keep each section of code in its own file without splitting the class itself

namespace DissertationGUI
{
    // the program entry point — this is the very first thing that runs when the app starts
    // [STAThread] is required by windows forms because all UI controls must live on a single-threaded apartment thread
    internal static class Program
    {
        // full path to the dissertation backend executable that Scan.cs and Fix.cs use to launch checks and fixes
        // when running as a published single-file exe this points to the extracted copy in the user's temp folder
        // when running via "dotnet run" during development this stays empty and the code falls back to "python dissertation.py"
        internal static string BackendExePath
        {
            get;
            private set;
        } = "";

        [STAThread]
        static void Main()
        {
            // extract the embedded dissertation.exe to a temp folder before the window opens
            // this must happen before Application.Run so the path is ready the moment the user clicks Start Scan
            BackendExePath = ExtractBackendExe();

            // ApplicationConfiguration.Initialize() sets up high-DPI awareness and visual styles automatically
            ApplicationConfiguration.Initialize();
            // Application.Run creates the window and hands control to the windows message loop
            // the message loop processes mouse clicks, repaints, and all other events until the window closes
            Application.Run(new SecurityDashboardForm());
        }

        // extracts the embedded dissertation.exe from the published bundle to the user's temp folder
        // returns the full path to the extracted file so Scan.cs and Fix.cs can call it directly
        // if the resource is not embedded (e.g. running via "dotnet run" during development) returns ""
        // so the callers can fall back to the original "python dissertation.py" workflow
        private static string ExtractBackendExe()
        {
            var assembly       = System.Reflection.Assembly.GetExecutingAssembly();
            var resourceStream = assembly.GetManifestResourceStream("dissertation.exe");

            // resource not found — app is running in development mode, no extraction needed
            if (resourceStream == null)
            {
                return "";
            }

            string targetDirectory = Path.Combine(Path.GetTempPath(), "DissertationBackend");
            string targetFilePath  = Path.Combine(targetDirectory, "dissertation.exe");

            Directory.CreateDirectory(targetDirectory);

            // always overwrite so a newer published version replaces any older extracted copy
            using (resourceStream)
            using (var fileStream = File.Create(targetFilePath))
                resourceStream.CopyTo(fileStream);

            return targetFilePath;
        }
    }

    // the main dashboard window class
    // this file only holds field declarations and the constructor
    // every Build* method lives in its own partial-class file to keep each concern separate
    public partial class SecurityDashboardForm : Form
    {
        // ── the four main layout panels that make up the window 
        private Panel           sidebarPanel;        // the dark nav panel on the left where scan types are listed
        private Panel           headerPanel;         // the blue bar across the top of the window
        private Panel           mainContentPanel;    // the grey area in the centre that holds all result cards
        private FlowLayoutPanel cardsPanel;          // a scrollable flow panel inside mainContentPanel that stacks each card vertically

        //  controls that live inside the header panel 
        private Label  titleLabel;       // shows the name of the currently selected scan e.g. "Full Scan"
        private Label  scoreLabel;       // shows the overall security score after a full scan e.g. "Score: 72/100 (Good)"
        private Button startScanButton;  // the green button the user clicks to start the scan

        // tracks which sidebar label is currently highlighted in blue
        // starts as null because no item has been clicked yet when the window first opens
        private Label currentlyHighlightedSidebarLabel = null;

        // stores the name of the scan type the user has chosen from the sidebar
        // defaults to "Full Scan" so the app is ready to scan everything immediately on startup
        private string chosenScanTypeName = "Full Scan";

        //  progress bar controls shown below the header during a full scan 
        private Panel       progressPanel;       // the thin dark strip that contains the bar and the counter label
        private ProgressBar scanProgressBar;     // the green bar that fills up as each check completes
        private Label       progressCountLabel;  // the "X / 8 checks complete" text label shown on the right

        // constructor — sets up the window and wires all sections together 
        public SecurityDashboardForm()
        {
            // basic window appearance settings
            Text        = "Dissertation Project";
            Width       = 1440;
            Height      = 1080;
            MinimumSize = new Size(900, 600);  // prevents the window from being shrunk so small the UI breaks
            BackColor   = Color.White;
            Font        = new Font("Helvetica", 11);  // base font — individual controls can override this

            // each Build* method lives in its own partial-class file and creates one section of the UI
            BuildSidebar();       // SecurityDashboardForm.Sidebar.cs — left nav panel
            BuildHeader();        // SecurityDashboardForm.Header.cs  — top blue bar
            BuildProgressArea();  // SecurityDashboardForm.Layout.cs  — progress strip below header
            BuildContent();       // SecurityDashboardForm.Layout.cs  — main scrollable card area

            // the order we add panels to Controls matters for DockStyle layering
            // winforms docks from the last-added panel inward, so:
            //   mainContentPanel (Fill) is added first — it fills all remaining space
            //   progressPanel (Top)     sits above mainContentPanel
            //   headerPanel (Top)       sits above progressPanel
            //   sidebarPanel (Left)     takes a column on the left side of all the above
            Controls.Add(mainContentPanel);
            Controls.Add(progressPanel);
            Controls.Add(headerPanel);
            Controls.Add(sidebarPanel);

            // show a friendly "press Start Scan to begin" message before the user has run anything
            ShowPlaceholder();
        }
    }
}
