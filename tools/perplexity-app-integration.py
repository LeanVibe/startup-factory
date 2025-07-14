#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Perplexity App Integration for MVP Orchestrator
Uses macOS Automator to search in Perplexity app instead of API calls
"""

import subprocess
import time
import os
from pathlib import Path
from typing import Optional, Tuple


class PerplexityAppManager:
    """Manages searches through the Perplexity macOS app"""
    
    def __init__(self, script_path: Optional[str] = None):
        if script_path is None:
            script_path = Path(__file__).parent / "perplexity-automator.scpt"
        
        self.script_path = Path(script_path)
        self.cost_per_search = 0.0  # Free when using the app
        
    def is_perplexity_installed(self) -> bool:
        """Check if Perplexity app is installed"""
        try:
            result = subprocess.run([
                "osascript", "-e",
                'tell application "Finder" to exists application file "Perplexity" of folder "Applications" of startup disk'
            ], capture_output=True, text=True, timeout=10)
            return result.stdout.strip() == "true"
        except Exception:
            return False
    
    def search_in_app(self, query: str) -> Tuple[str, float]:
        """
        Launch Perplexity app and perform search
        Returns (result_message, cost)
        """
        if not self.is_perplexity_installed():
            raise RuntimeError("Perplexity app is not installed. Please install from App Store.")
        
        try:
            # Run the AppleScript
            result = subprocess.run([
                "osascript", str(self.script_path), query
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                raise RuntimeError(f"AppleScript failed: {result.stderr}")
            
            # Since we can't automatically extract results from the app,
            # we return instructions for the user
            result_message = f"""
✅ Perplexity app opened with search: "{query}"

📋 NEXT STEPS:
1. Review the search results in the Perplexity app
2. Copy the relevant information
3. Paste it back into this script when prompted

💡 TIP: Use Cmd+A to select all, then Cmd+C to copy the results
"""
            
            return result_message, self.cost_per_search
            
        except subprocess.TimeoutExpired:
            raise RuntimeError("AppleScript timed out. Please try again.")
        except Exception as e:
            raise RuntimeError(f"Failed to search in Perplexity app: {e}")
    
    def get_user_input_after_search(self, query: str) -> str:
        """
        Get user input after they've reviewed the Perplexity app results
        """
        print(f"\n📱 Perplexity app search completed for: {query}")
        print("Please review the results in the Perplexity app and copy the relevant information.")
        print("\nPress Enter when you're ready to paste the results...")
        input()
        
        print("\n📝 Please paste the search results below:")
        print("(Press Enter on an empty line to finish)")
        
        lines = []
        while True:
            line = input()
            if line == "":
                break
            lines.append(line)
        
        return "\n".join(lines)


def create_automator_workflow():
    """Create a proper Automator workflow file"""
    workflow_content = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>AMApplicationBuild</key>
    <string>523</string>
    <key>AMApplicationVersion</key>
    <string>2.10</string>
    <key>AMDocumentVersion</key>
    <string>2</string>
    <key>actions</key>
    <array>
        <dict>
            <key>action</key>
            <dict>
                <key>AMAccepts</key>
                <dict>
                    <key>Container</key>
                    <string>List</string>
                    <key>Optional</key>
                    <true/>
                    <key>Types</key>
                    <array>
                        <string>com.apple.applescript.object</string>
                    </array>
                </dict>
                <key>AMActionVersion</key>
                <string>1.0.2</string>
                <key>AMApplication</key>
                <array>
                    <string>Automator</string>
                </array>
                <key>AMParameterProperties</key>
                <dict>
                    <key>source</key>
                    <dict/>
                </dict>
                <key>AMProvides</key>
                <dict>
                    <key>Container</key>
                    <string>List</string>
                    <key>Types</key>
                    <array>
                        <string>com.apple.applescript.object</string>
                    </array>
                </dict>
                <key>ActionBundlePath</key>
                <string>/System/Library/Automator/Run AppleScript.action</string>
                <key>ActionName</key>
                <string>Run AppleScript</string>
                <key>ActionParameters</key>
                <dict>
                    <key>source</key>
                    <string>-- Read the search query from input
on run {input, parameters}
    set searchQuery to item 1 of input as string
    
    -- Open Perplexity app
    tell application "Perplexity- Ask Anything"
        activate
        delay 2
    end tell
    
    -- Send the search query
    tell application "System Events"
        tell process "Perplexity- Ask Anything"
            delay 1
            keystroke searchQuery
            delay 0.5
            key code 36 -- Enter
        end tell
    end tell
    
    return input
end run</string>
                </dict>
                <key>BundleIdentifier</key>
                <string>com.apple.Automator.RunScript</string>
                <key>CFBundleVersion</key>
                <string>1.0.2</string>
                <key>CanShowSelectedItemsWhenRun</key>
                <false/>
                <key>CanShowWhenRun</key>
                <true/>
                <key>Category</key>
                <array>
                    <string>AMCategoryUtilities</string>
                </array>
                <key>Class Name</key>
                <string>RunScriptAction</string>
                <key>InputUUID</key>
                <string>A5C5C8C5-7B8A-4A5F-8F7E-1234567890AB</string>
                <key>Keywords</key>
                <array>
                    <string>Run</string>
                </array>
                <key>OutputUUID</key>
                <string>B6D6D9D6-8C9B-5B6F-9F8E-2345678901BC</string>
                <key>UUID</key>
                <string>C7E7E0E7-9D0C-6C7F-0F9E-3456789012CD</string>
                <key>UnlocalizedApplications</key>
                <array>
                    <string>Automator</string>
                </array>
                <key>arguments</key>
                <dict>
                    <key>0</key>
                    <dict>
                        <key>default value</key>
                        <string>-- Read the search query from input
on run {input, parameters}
    set searchQuery to item 1 of input as string
    
    -- Open Perplexity app
    tell application "Perplexity- Ask Anything"
        activate
        delay 2
    end tell
    
    -- Send the search query
    tell application "System Events"
        tell process "Perplexity- Ask Anything"
            delay 1
            keystroke searchQuery
            delay 0.5
            key code 36 -- Enter
        end tell
    end tell
    
    return input
end run</string>
                        <key>name</key>
                        <string>source</string>
                        <key>required</key>
                        <string>0</string>
                        <key>type</key>
                        <string>0</string>
                        <key>uuid</key>
                        <string>0</string>
                    </dict>
                </dict>
                <key>conversionLabel</key>
                <integer>0</integer>
                <key>isViewVisible</key>
                <true/>
                <key>location</key>
                <string>449.000000:316.000000</string>
                <key>nibPath</key>
                <string>/System/Library/Automator/Run AppleScript.action/Contents/Resources/Base.lproj/main.nib</string>
            </dict>
        </dict>
    </array>
    <key>connectors</key>
    <dict/>
    <key>workflowMetaData</key>
    <dict>
        <key>workflowTypeIdentifier</key>
        <string>com.apple.Automator.application</string>
    </dict>
</dict>
</plist>'''
    
    workflow_path = Path(__file__).parent / "PerplexitySearch.workflow"
    workflow_path.mkdir(exist_ok=True)
    
    contents_path = workflow_path / "Contents"
    contents_path.mkdir(exist_ok=True)
    
    with open(contents_path / "document.wflow", "w") as f:
        f.write(workflow_content)
    
    return workflow_path


# Example usage and testing
if __name__ == "__main__":
    manager = PerplexityAppManager()
    
    # Test if Perplexity is installed
    if manager.is_perplexity_installed():
        print("✅ Perplexity app is installed")
        
        # Test search
        try:
            query = "AI trends in 2024"
            result, cost = manager.search_in_app(query)
            print(result)
            
            # Get user input after search
            user_results = manager.get_user_input_after_search(query)
            print(f"\n📊 User provided results ({len(user_results)} characters):")
            print(user_results[:200] + "..." if len(user_results) > 200 else user_results)
            
        except Exception as e:
            print(f"❌ Error: {e}")
    else:
        print("❌ Perplexity app is not installed")
        print("Please install from the App Store: https://apps.apple.com/app/perplexity-ask-anything/id1668000334")