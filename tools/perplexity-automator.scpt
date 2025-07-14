-- Perplexity App Search Automator Script
-- This AppleScript opens Perplexity app and performs a search
-- Usage: osascript perplexity-automator.scpt "your search query"

on run argv
    set searchQuery to item 1 of argv
    
    -- Check if Perplexity is installed
    try
        tell application "Finder"
            if not (exists application file "Perplexity" of folder "Applications" of startup disk) then
                display dialog "Perplexity app not found. Please install it from the App Store." buttons {"OK"} default button "OK"
                return
            end if
        end tell
    on error
        display dialog "Error checking for Perplexity app." buttons {"OK"} default button "OK"
        return
    end try
    
    -- Open Perplexity app
    try
        tell application "Perplexity"
            activate
            delay 2 -- Wait for app to fully load
        end tell
    on error
        display dialog "Failed to open Perplexity app." buttons {"OK"} default button "OK"
        return
    end try
    
    -- Send the search query
    try
        tell application "System Events"
            tell process "Perplexity"
                -- Wait for the app to be ready
                delay 1
                
                -- Click in the search field and type the query
                -- Note: This may need adjustment based on the app's UI
                key code 53 -- Press Escape to ensure we're in the right state
                delay 0.5
                
                -- Type the search query
                keystroke searchQuery
                delay 0.5
                
                -- Press Enter to submit the search
                key code 36 -- Enter key
            end tell
        end tell
    on error errorMessage
        display dialog "Error interacting with Perplexity: " & errorMessage buttons {"OK"} default button "OK"
    end try
    
end run