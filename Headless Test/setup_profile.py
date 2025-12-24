"""
Setup Profile Script
====================
Run this ONCE to create a Chrome profile with your HeyGen login.

How to use:
1. Run this script: python setup_profile.py
2. Chrome will open - log into HeyGen
3. Close Chrome when done
4. Your session is now saved in 'chrome_profile/' folder
"""

import os
from playwright.sync_api import sync_playwright

# Profile folder path (same directory as this script)
PROFILE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chrome_profile")

def setup_profile():
    """Launch Chrome for manual HeyGen login and persist the profile."""
    print("=" * 50)
    print("HEYGEN PROFILE SETUP")
    print("=" * 50)
    print(f"\nProfile will be saved to: {PROFILE_DIR}")
    print("\nOpening Chrome... Please log into HeyGen.")
    print("Close the browser when you're done logging in.\n")
    
    # Create profile directory if it doesn't exist
    os.makedirs(PROFILE_DIR, exist_ok=True)
    
    browser_channel = os.getenv("HEYGEN_BROWSER_CHANNEL", "chrome").strip().lower()
    if browser_channel in {"", "chromium", "none"}:
        browser_channel = None

    with sync_playwright() as p:
        # Launch browser with persistent context (saves profile)
        try:
            context = p.chromium.launch_persistent_context(
                user_data_dir=PROFILE_DIR,
                headless=False,  # Must be visible for manual login
                channel=browser_channel,
                args=[
                    "--start-maximized",
                    "--disable-blink-features=AutomationControlled",
                ],
                ignore_default_args=["--enable-automation"],
            )
        except Exception as exc:
            if browser_channel:
                print(f"⚠️ Could not launch channel '{browser_channel}': {exc}")
                print("   Falling back to bundled Chromium...")
                context = p.chromium.launch_persistent_context(
                    user_data_dir=PROFILE_DIR,
                    headless=False,
                    args=[
                        "--start-maximized",
                        "--disable-blink-features=AutomationControlled",
                    ],
                    ignore_default_args=["--enable-automation"],
                )
            else:
                raise
        
        # Open HeyGen
        page = context.new_page()
        page.goto("https://app.heygen.com/")
        
        print("✅ Chrome opened with HeyGen")
        print("👉 Please log in to your HeyGen account")
        print("👉 Close the browser window when done")
        print("\nWaiting for you to close the browser...")
        
        # Wait for user to close the browser
        try:
            page.wait_for_event("close", timeout=0)
        except:
            pass
        
        context.close()
    
    print("\n✅ Profile saved successfully!")
    print(f"📁 Location: {PROFILE_DIR}")
    print("\nYou can now run test_headless.py to test headless mode.")

if __name__ == "__main__":
    setup_profile()
