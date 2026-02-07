-- DisplayToggle.applescript
-- Compile with: osacompile -o DisplayToggle.app DisplayToggle.applescript
-- Or create via Automator > Application > Run AppleScript

on run
    set scriptPath to (POSIX path of (path to home folder)) & "clawd/projects/display-toggle/display-toggle.sh"
    
    try
        set result to do shell script scriptPath
        display notification result with title "Display Toggle"
    on error errMsg
        display notification errMsg with title "Display Toggle Error"
    end try
end run
